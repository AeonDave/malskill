import sys
import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "scripts"))

from validate_all import _parse_args


class ValidateAllTests(unittest.TestCase):
    def test_cli_discovers_its_repository_from_another_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="malskill-validator-") as temporary:
            root = Path(temporary)
            repository = root / "repository"
            scripts = repository / "scripts"
            scripts.mkdir(parents=True)
            for name in ("validate_all.py", "quick_validate.py"):
                shutil.copy2(REPOSITORY / "scripts" / name, scripts / name)
            skill = repository / "knowledge" / "demo-skill"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: A valid fixture.\n---\n", encoding="utf-8"
            )
            outside = root / "outside"
            outside.mkdir()
            for excluded in (repository / ".import", repository / "vendor", outside):
                excluded.mkdir(exist_ok=True)
                (excluded / "SKILL.md").write_text("Invalid fixture.\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(scripts / "validate_all.py"), "--exclude", "vendor"],
                cwd=outside, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("TOTAL=1  PASSED=1  WARNED=0  FAILED=0", result.stdout)

    def test_explicit_skill_dirs_and_excludes(self):
        root, excludes, skills = _parse_args(
            ["ignored-root", "--exclude", "vendor", "--skill-dir", "knowledge/skill-creator"]
        )
        self.assertEqual(root, (Path.cwd() / "ignored-root").resolve())
        self.assertEqual(excludes, {".import", "vendor"})
        self.assertEqual(skills, [(Path.cwd() / "knowledge/skill-creator").resolve()])


if __name__ == "__main__":
    unittest.main()
