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
    link_integrity         (proof)          simple relative [label](path.md) links outside fences resolve
    hygiene_markers        (checked)        no placeholder markers / workstation paths
    routing_wiring         (checked)        every references/*.md is linked from its parent SKILL.md
    catalog_alignment      (checked)        every category is registered in CATALOG.md; CATALOG links resolve; README commands exist
    content_currency       (evidence)       per-category attestation dates vs renewal cadence (from .assurance/claims.yaml)

Link checks support the simple [label](path.md) form with an optional #fragment.
Angle-bracket destinations, link titles, and reference-style links are not checked.

The evidence package (.assurance/evidence-package.json) records the sha256 of
audited markdown and root Python scripts/tests. Scoped markdown and validator
dependencies generate renewal triggers; other tooling hashes record provenance
only. Content attestations require a date and reviewed
category digest in the catalog. Missing digests remain unverified; mismatches
remain stale until a real review updates the attestation.

Usage:
    python scripts/assurance_check.py                  # run, write package, print summary
    python scripts/assurance_check.py --no-write       # evaluate only
    python scripts/assurance_check.py --json           # write package and print JSON only
    python scripts/assurance_check.py --strict         # exit 1 on failed, stale, or unverified claims
    python scripts/assurance_check.py --claims PATH    # custom claims catalog

Exit codes:
    0  no failed claims (stale/unverified are informational)
    1  failed claims (--strict also fails on stale/unverified)
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

PACKAGE_VERSION = 2

# Method -> strongest status it may report (no-labeling-up).
METHOD_CAP = {
    "proof": "proven",
    "policy-as-code": "checked",
    "evidence": "attested",
}

STATUS_RANK = {"failed": 0, "unverified": 0, "stale": 1, "attested": 2, "checked": 3, "proven": 4}

DEFAULT_CADENCE_DAYS = 180

# Claims whose scope a changed file touches. Each matching claim is included.
CLAIM_FILE_SCOPES = [
    ("frontmatter_integrity", ["**/SKILL.md", "scripts/quick_validate.py", "scripts/assurance_check.py"]),
    ("routing_wiring", ["**/SKILL.md", "**/references/*.md", "scripts/assurance_check.py"]),
    ("link_integrity", ["*.md", "scripts/sweep_skills.py", "scripts/assurance_check.py"]),
    ("hygiene_markers", ["*.md", "scripts/sweep_skills.py", "scripts/assurance_check.py"]),
    ("catalog_alignment", ["CATALOG.md", "README.md", "**/SKILL.md",
                           "scripts/sweep_skills.py", "scripts/assurance_check.py"]),
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
    return sorted(d.parent for d in root.rglob("SKILL.md")
                  if d.is_file() and not _skip_path(root, d))


def _iter_category_dirs(root: pathlib.Path) -> list[str]:
    cats = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and not d.name.startswith(".") and d.name not in ("assets", "tests", "scripts", "docs"):
            if any(p.is_file() and not _skip_path(root, p) for p in d.rglob("SKILL.md")):
                cats.append(d.name)
    return cats


def _load_claims_catalog(path: pathlib.Path | None) -> dict:
    if path is None:
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("PyYAML is required to read the claims catalog") from exc
    try:
        catalog = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Cannot read claims catalog: {exc}") from exc
    if not isinstance(catalog, dict):
        raise ValueError("Claims catalog must be a YAML mapping")
    cc = catalog.get("content_currency", {})
    if not isinstance(cc, dict):
        raise ValueError("content_currency must be a mapping")
    for key in ("cadence_days", "last_verified", "verified_digest"):
        entries = cc.get(key, {})
        if not isinstance(entries, dict) or any(not isinstance(k, str) for k in entries):
            raise ValueError(f"content_currency.{key} must map category names to values")
    for category, days in cc.get("cadence_days", {}).items():
        if type(days) is not int or days <= 0:
            raise ValueError(f"cadence_days.{category} must be a positive integer")
    for category, value in cc.get("last_verified", {}).items():
        _attestation_date(value, category)
    for category, value in cc.get("verified_digest", {}).items():
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"verified_digest.{category} must be a lowercase SHA-256 digest")
    return catalog


def _attestation_date(value: object, category: str) -> datetime.date:
    """Accept ISO dates or timestamps, including same-day review renewals."""
    try:
        timestamp = datetime.datetime.fromisoformat(str(value))
        now = datetime.datetime.now(timestamp.tzinfo)
        if timestamp > now:
            raise ValueError("future attestation")
        return timestamp.date()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"last_verified.{category} must be a non-future ISO date or timestamp") from exc


def _md_text_and_links(text: str) -> list[str]:
    """Return simple [label](path.md[#fragment]) targets outside fences."""
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
    """proof — simple [label](path.md[#fragment]) targets outside fences resolve."""
    broken = []
    for md in sorted(root.rglob("*.md")):
        if _skip_path(root, md):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            broken.append(f"{_rel(root, md)}: unreadable ({exc})")
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
        except OSError as exc:
            hits.append(f"{_rel(root, md)}: unreadable ({exc})")
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
    for skill_dir in _iter_skill_dirs(root):
        skill_md = skill_dir / "SKILL.md"
        refs_dir = skill_dir / "references"
        if not refs_dir.is_dir():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        for ref in sorted(refs_dir.rglob("*.md")):
            if _skip_path(root, ref):
                continue
            if ref.relative_to(skill_dir).as_posix() not in text:
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



def check_content_currency(root: pathlib.Path, catalog: dict, files: dict | None = None) -> dict:
    """attested — per-category attestation dates vs renewal cadence (evidence, decays)."""
    cc = (catalog or {}).get("content_currency", {})
    cadence = {"default": DEFAULT_CADENCE_DAYS}
    cadence.update(cc.get("cadence_days", {}) or {})
    last_verified = cc.get("last_verified", {}) or {}
    verified_digests = cc.get("verified_digest", {}) or {}

    today = datetime.date.today()
    evidence, exceptions = [], []
    any_stale = False
    unverified_categories = []
    category_digests = {}
    changed_categories = []
    files = _collect_files(root) if files is None else files

    for cat in _iter_category_dirs(root):
        digest = _sha256(json.dumps({p: h for p, h in files.items()
                                    if p.startswith(cat + "/")}, sort_keys=True).encode())
        category_digests[cat] = digest
        if cat not in last_verified or cat not in verified_digests:
            unverified_categories.append(cat)
            continue
        verified = _attestation_date(last_verified[cat], cat)
        if verified_digests[cat] != digest:
            any_stale = True
            changed_categories.append(cat)
            exceptions.append(f"{cat}: content differs from reviewed digest — re-verify online")
            continue
        days = (today - verified).days
        limit = cadence.get(cat, cadence.get("default", DEFAULT_CADENCE_DAYS))
        if days > limit:
            any_stale = True
            exceptions.append(f"{cat}: attested {verified} ({days} days ago, cadence {limit}d) — re-verify online")
        else:
            evidence.append(f"{cat}: attested {verified} ({days} days ago, cadence {limit}d)")

    if unverified_categories:
        exceptions.append("unverified categories (missing date or reviewed digest): " + ", ".join(unverified_categories))
    status = "stale" if any_stale else "unverified" if unverified_categories else "attested"
    return {"claim_id": "content_currency", "method": "evidence", "status": status,
            "evidence": evidence, "exceptions": exceptions,
            "unverified_categories": unverified_categories,
            "category_digests": category_digests,
            "changed_categories": changed_categories}


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
    files = _collect_files(root)
    currency = check_content_currency(root, catalog, files)
    claims.append({k: v for k, v in currency.items()
                   if k not in ("unverified_categories", "category_digests", "changed_categories")})

    # Renewal triggers: files changed since the previous package invalidate the
    # claims whose scope covers them. Evidence claims additionally go stale when
    # their attestation window closes (handled inside check_content_currency).
    renewal = []
    if previous is not None and "files" in previous:
        prev_files = previous["files"]
        changed = sorted(
            [f for f, h in files.items() if prev_files.get(f) != h]
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
    if currency["changed_categories"]:
        renewal.append({"claim_id": "content_currency",
                        "reason": f"content changed in: {', '.join(currency['changed_categories'])} — re-verify online",
                        "files": []})

    # No-labeling-up: a status may not exceed its method's cap.
    for claim in claims:
        cap = METHOD_CAP.get(claim["method"], "proven")
        if STATUS_RANK.get(claim["status"], 0) > STATUS_RANK.get(cap, 0):
            claim["status"] = cap

    unverified_categories = currency.get("unverified_categories", [])
    unverified = [{"scope": c, "reason": "missing attestation date or reviewed digest"}
                  for c in unverified_categories]

    summary = {}
    for claim in claims:
        summary[claim["status"]] = summary.get(claim["status"], 0) + 1
    return {
        "package_version": PACKAGE_VERSION,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "claims": claims,
        "unverified": unverified,
        "files": files,
        "category_digests": currency["category_digests"],
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
    parser.add_argument("--strict", action="store_true", help="exit 1 on stale or unverified claims too")
    args = parser.parse_args(argv)

    root = _repo_root()
    package_path = root / args.package
    claims_path = root / args.claims if not pathlib.Path(args.claims).is_absolute() else pathlib.Path(args.claims)

    previous = _load_previous(package_path)
    try:
        package = build_package(root, claims_path, previous)
    except ValueError as exc:
        parser.error(str(exc))

    package["baseline"] = previous is None

    if not args.no_write:
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_text(json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not args.json:
            print(f"evidence package written: {args.package}")

    if args.json:
        print(json.dumps(package, indent=2, sort_keys=True))
    else:
        _print_summary(package)

    failed = package["summary"].get("failed", 0)
    unresolved = package["summary"].get("stale", 0) + package["summary"].get("unverified", 0)
    return 1 if failed or (args.strict and unresolved) else 0


def _print_summary(package: dict) -> None:
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


if __name__ == "__main__":
    sys.exit(main())
