"""Regression tests for scripts/assurance_check.py."""
import contextlib
import datetime
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from assurance_check import (  # noqa: E402
    build_package,
    check_frontmatter_integrity,
    check_link_integrity,
    check_routing_wiring,
    main,
)

_SKILL_TEMPLATE = (
    "---\n"
    "name: {name}\n"
    'description: "Fixture skill for assurance regression tests."\n'
    "---\n\n"
    "# {name}\n"
    "{body}"
)


def _make_skill(root: Path, category: str, name: str, body: str = "Body.\n") -> Path:
    skill_dir = root / category / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        _SKILL_TEMPLATE.format(name=name, body=body), encoding="utf-8"
    )
    return skill_dir


def _make_catalog(root: Path, verified: str | None = None, *, with_digest: bool = True) -> Path:
    path = root / "claims.yaml"
    verified = verified or (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    text = f"content_currency:\n  last_verified:\n    cat: '{verified}'\n"
    if with_digest:
        digest = build_package(root, None, None)["category_digests"]["cat"]
        text += f"  verified_digest:\n    cat: '{digest}'\n"
    path.write_text(text, encoding="utf-8")
    return path


def _currency(package: dict) -> dict:
    return next(claim for claim in package["claims"] if claim["claim_id"] == "content_currency")


class AssuranceCheckTests(unittest.TestCase):
    def test_clean_tree_is_proven(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            self.assertEqual(check_frontmatter_integrity(root)["status"], "proven")
            self.assertEqual(check_link_integrity(root)["status"], "proven")

    def test_broken_relative_link_fails_link_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha", body="See [gone](references/missing.md).\n")
            result = check_link_integrity(root)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("missing.md" in exc for exc in result["exceptions"]))

    def test_unwired_reference_fails_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = _make_skill(root, "cat", "alpha")
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "deep.md").write_text("# Deep\n", encoding="utf-8")
            result = check_routing_wiring(root)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("deep.md" in exc for exc in result["exceptions"]))

    def test_wired_reference_passes_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = _make_skill(
                root, "cat", "alpha", body="Load references/deep.md when triaging.\n"
            )
            (skill_dir / "references").mkdir()
            (skill_dir / "references" / "deep.md").write_text("# Deep\n", encoding="utf-8")
            self.assertEqual(check_routing_wiring(root)["status"], "checked")

    def test_renewal_trigger_fires_on_changed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_md = _make_skill(root, "cat", "alpha") / "SKILL.md"
            baseline = build_package(root, None, None)
            self.assertEqual(baseline["renewal_triggers_active"], [])

            skill_md.write_text(
                skill_md.read_text(encoding="utf-8") + "\nAdded line.\n", encoding="utf-8"
            )
            second = build_package(root, None, baseline)
            triggered = {t["claim_id"] for t in second["renewal_triggers_active"]}
            self.assertIn("link_integrity", triggered)

    def test_status_never_exceeds_method_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            package = build_package(root, None, None)
            caps = {"proof": "proven", "policy-as-code": "checked", "evidence": "attested"}
            rank = {"failed": 0, "unverified": 0, "stale": 1, "attested": 2, "checked": 3, "proven": 4}
            for claim in package["claims"]:
                self.assertLessEqual(
                    rank[claim["status"]], rank[caps[claim["method"]]],
                    f"{claim['claim_id']} labeled up past {claim['method']} cap",
                )


    def test_hidden_dirs_excluded_from_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            cache = root / ".pytest_cache"
            cache.mkdir()
            (cache / "README.md").write_text("# cache\n", encoding="utf-8")
            package = build_package(root, None, None)
            self.assertIn("cat/alpha/SKILL.md", package["files"])
            self.assertNotIn(".pytest_cache/README.md", package["files"])

    def test_hidden_skills_excluded_from_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            hidden = _make_skill(root, ".cache", "bad")
            (hidden / "SKILL.md").write_text("invalid", encoding="utf-8")
            (hidden / "references").mkdir()
            (hidden / "references" / "orphan.md").write_text("hidden", encoding="utf-8")
            self.assertEqual(check_frontmatter_integrity(root)["status"], "proven")
            self.assertEqual(check_routing_wiring(root)["status"], "checked")

    def test_reference_basename_does_not_satisfy_another_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_skill(root, "cat", "alpha", "Load references/a/deep.md when needed.\n")
            for folder in ("a", "b"):
                refs = skill / "references" / folder
                refs.mkdir(parents=True)
                (refs / "deep.md").write_text("Deep", encoding="utf-8")
            result = check_routing_wiring(root)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(len(result["exceptions"]), 1)
            self.assertIn("references/b/deep.md", result["exceptions"][0])

    def test_added_deleted_and_root_files_trigger_renewal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_skill(root, "cat", "alpha")
            baseline = build_package(root, None, None)
            for path in (skill / "new.md", root / "README.md"):
                with self.subTest(path=path.name):
                    path.write_text("New", encoding="utf-8")
                    second = build_package(root, None, baseline)
                    triggers = {t["claim_id"]: t for t in second["renewal_triggers_active"]}
                    self.assertIn(path.relative_to(root).as_posix(), triggers["link_integrity"]["files"])
                    path.unlink()
                    third = build_package(root, None, second)
                    self.assertIn("link_integrity", {t["claim_id"] for t in third["renewal_triggers_active"]})

    def test_content_stays_stale_until_attestation_renewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root)
            baseline = build_package(root, catalog, None)
            self.assertEqual(_currency(baseline)["status"], "attested")
            (skill / "new.md").write_text("New content", encoding="utf-8")
            changed = build_package(root, catalog, baseline)
            unchanged = build_package(root, catalog, changed)
            self.assertEqual(_currency(changed)["status"], "stale")
            self.assertEqual(_currency(unchanged)["status"], "stale")
            self.assertIn("content_currency", {t["claim_id"] for t in unchanged["renewal_triggers_active"]})
            _make_catalog(root, datetime.datetime.now(datetime.timezone.utc).isoformat())
            renewed = build_package(root, catalog, unchanged)
            self.assertEqual(_currency(renewed)["status"], "attested")
            self.assertNotIn("content_currency", {t["claim_id"] for t in renewed["renewal_triggers_active"]})

    def test_unchanged_packages_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root)
            first = build_package(root, catalog, None)
            second = build_package(root, catalog, first)
            first.pop("generated_at")
            second.pop("generated_at")
            self.assertEqual(first, second)

    def test_historical_date_does_not_attest_first_or_subsequent_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root, with_digest=False)
            (skill / "SKILL.md").write_text(
                _SKILL_TEMPLATE.format(name="alpha", body="Unreviewed edits"), encoding="utf-8"
            )
            first = build_package(root, catalog, None)
            second = build_package(root, catalog, first)
            self.assertEqual(_currency(first)["status"], "unverified")
            self.assertEqual(_currency(second)["status"], "unverified")

    def test_reviewed_digest_detects_change_even_without_previous_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root)
            (skill / "new.md").write_text("Unreviewed", encoding="utf-8")
            self.assertEqual(_currency(build_package(root, catalog, None))["status"], "stale")

    def test_matching_digest_does_not_override_expired_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            old_date = (datetime.date.today() - datetime.timedelta(days=181)).isoformat()
            catalog = _make_catalog(root, old_date)
            result = _currency(build_package(root, catalog, None))
            self.assertEqual(result["status"], "stale")
            self.assertIn("cadence 180d", result["exceptions"][0])

    def test_missing_catalog_never_fabricates_attestation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "coding", "alpha")
            package = build_package(root, None, None)
            self.assertEqual(_currency(package)["status"], "unverified")
            self.assertEqual(_currency(package)["evidence"], [])
            with self.assertRaises(ValueError):
                build_package(root, root / "missing.yaml", None)

    def test_invalid_claims_catalog_fails_explicitly(self):
        cases = [
            "[not, a, mapping]", "content_currency: []", "content_currency: [",
            "content_currency:\n  last_verified: []",
            "content_currency:\n  cadence_days:\n    default: -1",
            "content_currency:\n  cadence_days:\n    default: true",
            "content_currency:\n  last_verified:\n    cat: invalid",
            "content_currency:\n  last_verified:\n    cat: 2999-01-01",
            "content_currency:\n  verified_digest:\n    cat: not-a-digest",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "claims.yaml"
            for text in cases:
                with self.subTest(text=text):
                    catalog.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        build_package(root, catalog, None)

    def test_root_tooling_change_does_not_invalidate_content_currency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root)
            baseline = build_package(root, catalog, None)
            (root / "README.md").write_text("Repository docs", encoding="utf-8")
            package = build_package(root, catalog, baseline)
            self.assertEqual(_currency(package)["status"], "attested")
            self.assertNotIn("content_currency", {t["claim_id"] for t in package["renewal_triggers_active"]})

    def test_validator_changes_trigger_only_dependent_structural_claims(self):
        dependencies = {
            "scripts/quick_validate.py": {"frontmatter_integrity"},
            "scripts/sweep_skills.py": {"link_integrity", "hygiene_markers", "catalog_alignment"},
            "scripts/assurance_check.py": {
                "frontmatter_integrity", "link_integrity", "hygiene_markers",
                "routing_wiring", "catalog_alignment",
            },
            "scripts/unrelated.py": set(),
            "tests/test_assurance_check.py": set(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            catalog = _make_catalog(root)
            (root / "CATALOG.md").write_text("`cat`", encoding="utf-8")
            for relative_path, expected in dependencies.items():
                with self.subTest(path=relative_path):
                    path = root / relative_path
                    path.parent.mkdir(exist_ok=True)
                    path.write_text("# Original\n", encoding="utf-8")
                    baseline = build_package(root, catalog, None)
                    path.write_text("# Changed\n", encoding="utf-8")
                    package = build_package(root, catalog, baseline)
                    self.assertNotEqual(package["files"][relative_path], baseline["files"][relative_path])
                    self.assertEqual({t["claim_id"] for t in package["renewal_triggers_active"]}, expected)
                    self.assertEqual(_currency(package)["status"], "attested")

    def test_json_stdout_is_parseable_and_no_write_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            _make_catalog(root)
            original_catalog = (root / "claims.yaml").read_bytes()
            (root / "CATALOG.md").write_text("`cat`", encoding="utf-8")
            with patch("assurance_check._repo_root", return_value=root):
                for no_write in (True, False):
                    with self.subTest(no_write=no_write):
                        stdout = io.StringIO()
                        args = ["--claims", "claims.yaml", "--json"]
                        if no_write:
                            args.append("--no-write")
                        with contextlib.redirect_stdout(stdout):
                            self.assertEqual(main(args), 0)
                        self.assertIn("claims", json.loads(stdout.getvalue()))
                        self.assertEqual((root / ".assurance/evidence-package.json").exists(), not no_write)
                        self.assertEqual((root / "claims.yaml").read_bytes(), original_catalog)

    def test_strict_fails_unverified_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_skill(root, "cat", "alpha")
            (root / "claims.yaml").write_text("{}", encoding="utf-8")
            (root / "CATALOG.md").write_text("`cat`", encoding="utf-8")
            with patch("assurance_check._repo_root", return_value=root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--claims", "claims.yaml", "--no-write"]), 0)
                self.assertEqual(main(["--claims", "claims.yaml", "--no-write", "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
