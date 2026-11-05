import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "coding-behaviours/testing-reliability/scripts/find_polluter.py"


class FindPolluterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="polluter test ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "test files").mkdir()

    def create_test(self, name, code):
        (self.root / "test files" / name).write_text(code, encoding="utf-8")

    def run_finder(self, *extra):
        command = f'"{Path(sys.executable).as_posix()}" {{test}}'
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", str(self.root), "--watch", "pollution",
             "--tests", "test files/*.py", "--command", command, *extra],
            text=True, capture_output=True, check=False,
        )

    def test_finds_polluter_with_spaces_in_test_path(self):
        self.create_test("create file.py", "from pathlib import Path\nPath('pollution').touch()\n")
        result = self.run_finder()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FOUND POLLUTER", result.stdout)
        self.assertIn("create file.py", result.stdout)

    def test_failed_test_is_inconclusive_and_reports_output(self):
        self.create_test("fail.py", "import sys\nprint('failure detail')\nsys.exit(7)\n")
        self.create_test("later.py", "print('later')\n")
        result = self.run_finder()
        self.assertEqual(result.returncode, 2)
        self.assertIn("failure detail", result.stdout)
        self.assertIn("exit 7", result.stdout)
        self.assertIn("later.py", result.stdout)
        self.assertIn("Inconclusive", result.stdout)

    def test_stop_on_failure_preserves_exit_and_output(self):
        self.create_test("fail.py", "import sys\nprint('failure detail')\nsys.exit(7)\n")
        self.create_test("later.py", "print('later')\n")
        result = self.run_finder("--stop-on-fail")
        self.assertEqual(result.returncode, 7)
        self.assertIn("failure detail", result.stdout)
        self.assertNotIn("later.py", result.stdout)

    def test_preexisting_watched_path_rejected(self):
        self.create_test("clean.py", "pass\n")
        (self.root / "pollution").touch()
        result = self.run_finder()
        self.assertEqual(result.returncode, 2)
        self.assertIn("clean baseline required", result.stdout)

    def test_clean_success(self):
        self.create_test("clean.py", "pass\n")
        result = self.run_finder()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No polluter found", result.stdout)


if __name__ == "__main__":
    unittest.main()
