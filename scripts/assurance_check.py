#!/usr/bin/env python3
"""
Assurance check — evidence package with method-strength labels and renewal triggers.

Adapted from the ORPHEUS provable-assurance model (DEF CON 34 / MalSkills_Lab).
Each claim declares a validation method; the reported status may never exceed the
method's strength (no-labeling-up):

    proof          -> proven    (mechanically decidable)
    policy-as-code -> checked   (deterministic rule sweep)
    evidence       -> attested  (human/agent attestation, decays with cadence)

Claims:
    frontmatter_integrity  (proof)          every SKILL.md passes quick_validate rules
    link_integrity         (proof)          no broken relative .md links anywhere
    hygiene_markers        (checked)        no placeholder markers / workstation paths
    routing_wiring         (checked)        every references/*.md is linked from its parent SKILL.md
    catalog_alignment      (checked)        every skill dir is registered in CATALOG.md; CATALOG links resolve; README commands exist
    content_currency       (evidence)       per-category attestation dates vs renewal cadence (from .assurance/claims.yaml)

The evidence package (.assurance/evidence-package.json) records the sha256 of
every audited file. On the next run, files whose hash changed generate renewal
triggers on the claims their path falls under. Two runs on an unchanged tree
produce byte-identical packages except `generated_at`.

Usage:
    python scripts/assurance_check.py                  # run, write package, print summary
    python scripts/assurance_check.py --no-write       # evaluate only
    python scripts/assurance_check.py --json           # print the package to stdout
    python scripts/assurance_check.py --strict         # exit 1 on failed OR stale claims
    python scripts/assurance_check.py --claims PATH    # custom claims catalog

Exit codes:
    0  no failed claims (stale/unverified are informational)
    1  failed claims (--strict also fails on stale)
    2  argument error
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from quick_validate import validate_skill  # noqa: E402
from sweep_skills import (  # noqa: E402
    _MD_LINK_RE,
    _PLACEHOLDER_RE,
    _WORKSTATION_PATH_RE,
    _WORKSTATION_PATH_ALLOWLIST,
)

PACKAGE_VERSION = 1

# Method -> strongest status it may report (no-labeling-up).
METHOD_CAP = {
    "proof": "proven",
    "policy-as-code": "checked",
    "evidence": "attested",
}

STATUS_RANK = {"failed": 0, "unverified": 0, "stale": 1, "attested": 2, "checked": 3, "proven": 4}

# Default attestation dates + renewal cadence per category. Override/extend in
# .assurance/claims.yaml (cadence_days / last_verified maps).
DEFAULT_CADENCE_DAYS = 180
CLAIMS_YAML_DEFAULT = r"""# Attestation catalog — last verified dates and renewal cadence per category.
# "attested" claims go stale when (today - last_verified) exceeds cadence_days
# or when files in the category change after the attestation date.
content_currency:
  cadence_days:
    default: 180
    ai: 60                 # tool versions churn in days
    offensive-tools: 120
  last_verified:
    coding: 2026-11-07
    offensive-coding: 2026-11-08
    offensive-ctf: 2026-11-07
    offensive-tools: 2026-11-14   # partial: network/wireless/shells clusters pending
    ai: 2026-11-14
    behaviours: 2026-11-08
    coding-behaviours: 2026-11-08
    knowledge-offensive: 2026-11-14
    # knowledge, harness-dev, hardware, offensive-hardware, mcp: no attestation -> unverified
"""

# Claims whose scope a changed file invalidates. First matching pattern wins.
CLAIM_FILE_SCOPES = [
    ("frontmatter_integrity", ["**/SKILL.md"]),
    ("routing_wiring", ["**/SKILL.md", "**/references/*.md"]),
    ("link_integrity", ["**/*.md"]),
    ("hygiene_markers", ["**/*.md"]),
    ("catalog_alignment", ["CATALOG.md", "README.md", "**/SKILL.md"]),
]


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _rel(root: pathlib.Path, p: pathlib.Path) -> str:
    return p.relative_to(root).as_posix()


def _skip_path(root: pathlib.Path, path: pathlib.Path) -> bool:
    """Skip VCS, generated, and hidden dirs — any dot-prefixed path segment (.git, .assurance, .venv, .pytest_cache)."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    return any(segment.startswith(".") for segment in parts[:-1])


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_skill_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(d.parent for d in root.rglob("SKILL.md") if d.is_file())


def _category_of(rel_path: str) -> str:
    return rel_path.split("/", 1)[0]


def _iter_category_dirs(root: pathlib.Path) -> list[str]:
    cats = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and d.name not in ("assets", "tests", "scripts", "docs"):
            if any(d.rglob("SKILL.md")):
                cats.append(d.name)
    return cats


def _load_claims_catalog(path: pathlib.Path | None) -> dict:
    if path is None or not path.exists():
        try:
            import yaml
            return yaml.safe_load(CLAIMS_YAML_DEFAULT)
        except ImportError:
            return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _md_text_and_links(text: str) -> list[str]:
    """Return relative .md link targets found in a markdown text (non-fenced)."""
    links = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _MD_LINK_RE.finditer(line):
            links.append(m.group(1))
    return links


def check_frontmatter_integrity(root: pathlib.Path) -> dict:
    """proof — every SKILL.md passes the quick_validate rules."""
    skill_dirs = _iter_skill_dirs(root)
    evidence, failures = [], []
    for d in skill_dirs:
        valid, message = validate_skill(d)
        rel = _rel(root, d)
        if valid:
            evidence.append(f"{rel}: {message}")
        else:
            failures.append(f"{rel}: {message}")
    status = "proven" if not failures else "failed"
    return {"claim_id": "frontmatter_integrity", "method": "proof", "status": status,
            "evidence": evidence[:20], "exceptions": failures}


def check_link_integrity(root: pathlib.Path) -> dict:
    """proof — no broken relative .md links in any markdown file."""
    broken = []
    for md in sorted(root.rglob("*.md")):
        if _skip_path(root, md):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for target in _md_text_and_links(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{_rel(root, md)} -> {target}")
    status = "proven" if not broken else "failed"
    return {"claim_id": "link_integrity", "method": "proof", "status": status,
            "evidence": [], "exceptions": broken}


def check_hygiene_markers(root: pathlib.Path) -> dict:
    """checked — no placeholder markers or workstation-path leaks."""
    hits = []
    for md in sorted(root.rglob("*.md")):
        if _skip_path(root, md):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = _rel(root, md)
        for m in _PLACEHOLDER_RE.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            hits.append(f"{rel}:{line_no} placeholder {m.group(0)}")
        for m in _WORKSTATION_PATH_RE.finditer(text):
            hit = m.group(0)
            if hit.lower().replace("/", "\\") in _WORKSTATION_PATH_ALLOWLIST or hit.lower() in _WORKSTATION_PATH_ALLOWLIST:
                continue
            hits.append(f"{rel} workstation-path {hit}")
    status = "checked" if not hits else "failed"
    return {"claim_id": "hygiene_markers", "method": "policy-as-code", "status": status,
            "evidence": [], "exceptions": hits}


def check_routing_wiring(root: pathlib.Path) -> dict:
    """checked — every references/*.md file is mentioned in its parent SKILL.md."""
    unwired = []
    for skill_md in sorted(root.rglob("SKILL.md")):
        skill_dir = skill_md.parent
        refs_dir = skill_dir / "references"
        if not refs_dir.is_dir():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        for ref in sorted(refs_dir.rglob("*.md")):
            if ref.name not in text:
                unwired.append(f"{_rel(root, ref)} not referenced from {_rel(root, skill_md)}")
    status = "checked" if not unwired else "failed"
    return {"claim_id": "routing_wiring", "method": "policy-as-code", "status": status,
            "evidence": [], "exceptions": unwired}


def check_catalog_alignment(root: pathlib.Path) -> dict:
    """checked — every category registered in CATALOG.md; CATALOG links resolve; README commands exist."""
    catalog = root / "CATALOG.md"
    readme = root / "README.md"
    exceptions = []
    catalog_text = catalog.read_text(encoding="utf-8") if catalog.exists() else ""

    # Category-level registration (CATALOG uses an examples table, not per-skill listing)
    for cat in _iter_category_dirs(root):
        if f"`{cat}`" not in catalog_text and f"{cat}/" not in catalog_text:
            exceptions.append(f"category '{cat}' not represented in CATALOG.md")

    # CATALOG.md links must resolve
    for target in _md_text_and_links(catalog_text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (catalog.parent / target).exists():
            exceptions.append(f"CATALOG.md broken link: {target}")

    # README documented commands must exist: `python scripts/<name>.py`
    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"python scripts/(\w+)(?:\.py)?", readme_text):
            script = root / "scripts" / f"{m.group(1)}.py"
            if not script.exists():
                exceptions.append(f"README documents missing script: scripts/{m.group(1)}.py")

    status = "checked" if not exceptions else "failed"
    return {"claim_id": "catalog_alignment", "method": "policy-as-code", "status": status,
            "evidence": [], "exceptions": exceptions}



def check_content_currency(root: pathlib.Path, catalog: dict) -> dict:
    """attested — per-category attestation dates vs renewal cadence (evidence, decays)."""
    cc = (catalog or {}).get("content_currency", {})
    cadence = {"default": DEFAULT_CADENCE_DAYS}
    cadence.update(cc.get("cadence_days", {}) or {})
    last_verified = cc.get("last_verified", {}) or {}

    today = datetime.date.today()
    evidence, exceptions = [], []
    any_stale = False
    unverified_categories = []

    for cat in _iter_category_dirs(root):
        if cat not in last_verified:
            unverified_categories.append(cat)
            continue
        try:
            verified = datetime.date.fromisoformat(str(last_verified[cat]))
        except ValueError:
            unverified_categories.append(cat)
            continue
        days = (today - verified).days
        limit = cadence.get(cat, cadence.get("default", DEFAULT_CADENCE_DAYS))
        if days > limit:
            any_stale = True
            exceptions.append(f"{cat}: attested {verified} ({days} days ago, cadence {limit}d) — re-verify online")
        else:
            evidence.append(f"{cat}: attested {verified} ({days} days ago, cadence {limit}d)")

    if unverified_categories:
        exceptions.append("unverified categories (no attestation): " + ", ".join(unverified_categories))
    status = "stale" if (any_stale or unverified_categories) else "attested"
    return {"claim_id": "content_currency", "method": "evidence", "status": status,
            "evidence": evidence, "exceptions": exceptions,
            "unverified_categories": unverified_categories}


def _scoped_claims(rel_path: str) -> list[str]:
    claim_ids = []
    for claim_id, patterns in CLAIM_FILE_SCOPES:
        for pattern in patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                claim_ids.append(claim_id)
                break
    return claim_ids


def _collect_files(root: pathlib.Path) -> dict[str, str]:
    files: dict[str, str] = {}
    patterns = ["**/*.md"]
    seen = set()
    for pattern in patterns:
        for f in sorted(root.glob(pattern)):
            if not f.is_file() or _skip_path(root, f):
                continue
            rel = _rel(root, f)
            if rel in seen:
                continue
            seen.add(rel)
            files[rel] = _sha256(f.read_bytes())
    for f in sorted((root / "scripts").glob("*.py")):
        files[_rel(root, f)] = _sha256(f.read_bytes())
    for f in sorted((root / "tests").glob("*.py")):
        files[_rel(root, f)] = _sha256(f.read_bytes())
    return files


def _load_previous(path: pathlib.Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("package_version") == PACKAGE_VERSION else None
    except (OSError, json.JSONDecodeError):
        return None


def build_package(root: pathlib.Path, claims_catalog_path: pathlib.Path | None,
                  previous: dict | None) -> dict:
    catalog = _load_claims_catalog(claims_catalog_path)

    claims = [
        check_frontmatter_integrity(root),
        check_link_integrity(root),
        check_hygiene_markers(root),
        check_routing_wiring(root),
        check_catalog_alignment(root),
    ]
    currency = check_content_currency(root, catalog)
    claims.append({k: v for k, v in currency.items() if k != "unverified_categories"})

    files = _collect_files(root)

    # Renewal triggers: files changed since the previous package invalidate the
    # claims whose scope covers them. Evidence claims additionally go stale when
    # their attestation window closes (handled inside check_content_currency).
    renewal = []
    if previous and previous.get("files"):
        prev_files = previous["files"]
        changed = sorted(
            [f for f, h in files.items() if prev_files.get(f) not in (None, h)]
            + [f for f in prev_files if f not in files]
        )
        invalidated: dict[str, list[str]] = {}
        for f in changed:
            for claim_id in _scoped_claims(f):
                invalidated.setdefault(claim_id, []).append(f)
        for claim in claims:
            touched = invalidated.get(claim["claim_id"])
            if touched and claim["status"] not in ("failed",):
                renewal.append({"claim_id": claim["claim_id"],
                                "reason": f"{len(touched)} file(s) changed since previous audit",
                                "files": touched[:10]})
        cat_changes = {f.split("/", 1)[0] for f in changed if "/" in f}
        cat_changes.update({f for f in changed if "/" not in f and f.endswith(".md")})
        if cat_changes:
            renewal.append({"claim_id": "content_currency",
                            "reason": f"content changed in: {', '.join(sorted(cat_changes))} — re-verify online",
                            "files": []})

    # No-labeling-up: a status may not exceed its method's cap.
    for claim in claims:
        cap = METHOD_CAP.get(claim["method"], "proven")
        if STATUS_RANK.get(claim["status"], 0) > STATUS_RANK.get(cap, 0):
            claim["status"] = cap

    unverified_categories = currency.get("unverified_categories", [])
    unverified = [{"scope": c, "reason": "no attestation recorded"} for c in unverified_categories]

    summary = {}
    for claim in claims:
        summary[claim["status"]] = summary.get(claim["status"], 0) + 1
    for u in unverified:
        summary["unverified"] = summary.get("unverified", 0) + 1

    return {
        "package_version": PACKAGE_VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "claims": claims,
        "unverified": unverified,
        "files": files,
        "renewal_triggers_active": renewal,
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence package with claims, method labels, and renewal triggers.")
    parser.add_argument("--package", default=".assurance/evidence-package.json",
                        help="evidence package path (default: .assurance/evidence-package.json)")
    parser.add_argument("--claims", default=".assurance/claims.yaml",
                        help="attestation catalog path (default: .assurance/claims.yaml)")
    parser.add_argument("--no-write", action="store_true", help="evaluate without writing the package")
    parser.add_argument("--json", action="store_true", help="print the full package to stdout")
    parser.add_argument("--strict", action="store_true", help="exit 1 on stale claims too")
    args = parser.parse_args(argv)

    root = _repo_root()
    package_path = root / args.package
    claims_path = root / args.claims if not pathlib.Path(args.claims).is_absolute() else pathlib.Path(args.claims)

    previous = _load_previous(package_path)
    package = build_package(root, claims_path if claims_path.exists() else None, previous)

    package["baseline"] = previous is None

    if args.json or args.no_write:
        print(json.dumps(package, indent=2, sort_keys=True))
    else:
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"evidence package written: {args.package}")

    print("claims:")
    for claim in package["claims"]:
        print(f"  [{claim['status']:>9}] {claim['claim_id']} ({claim['method']})")
        for exc in claim.get("exceptions", [])[:6]:
            print(f"      ! {exc}")
        if len(claim.get("exceptions", [])) > 6:
            print(f"      ! … and {len(claim['exceptions']) - 6} more")
    for trigger in package["renewal_triggers_active"]:
        print(f"  [renewal ] {trigger['claim_id']}: {trigger['reason']}")
    for u in package["unverified"]:
        print(f"  [unverif.] {u['scope']}: {u['reason']}")

    failed = package["summary"].get("failed", 0)
    stale = package["summary"].get("stale", 0)
    if failed:
        return 1
    if args.strict and stale:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
