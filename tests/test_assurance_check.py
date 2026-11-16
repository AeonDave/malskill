"""Regression tests for scripts/assurance_check.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from assurance_check import (  # noqa: E402
    build_package,
    check_frontmatter_integrity,
    check_link_integrity,
    check_routing_wiring,
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
            rank = {"failed": 0, "stale": 1, "attested": 2, "checked": 3, "proven": 4}
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


if __name__ == "__main__":
    unittest.main()
