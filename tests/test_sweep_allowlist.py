"""Regression tests for workstation-path filtering in sweep_skills."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sweep_skills import sweep  # noqa: E402


class SweepAllowlistTests(unittest.TestCase):
    def run_sweep(self, text):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fixture.md").write_text(text, encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                result = sweep(root, ctf_check=False, top=1)
            self.assertEqual(result, 0)
            return output.getvalue()

    def test_known_non_workstation_paths_are_suppressed(self):
        output = self.run_sweep(
            "\n".join(
                [
                    "/home/default",
                    "/home/papercut/worker",
                    "/home/ctf/challenge",
                    "/home/user/data",
                    r"C:\Users\PUBLIC\Temp",
                    r"c:/users/Default/AppData",
                    r"C:\Users\All Users\Shared",
                    r"C:\Users\All Users",
                    r"C:\Users\Administrator\Desktop",
                    r"C:\Users\DefaultUser0\NTUSER.DAT",
                    r"C:\Users\User\Downloads",
                ]
            )
        )

        self.assertIn("workstation_paths = 0", output)

    def test_nearby_and_personal_paths_are_reported(self):
        paths = (
            "/home/ctfuser",
            "/home/user123",
            "/home/papercut2",
            "/home/alexander",
            r"C:\Users\Publicity\Desktop",
            r"C:\Users\Example\Documents",
            r"C:\Users\All Users2\Desktop",
            r"C:\Users\All Users-old\Desktop",
        )
        output = self.run_sweep("\n".join(paths))

        self.assertIn(f"workstation_paths = {len(paths)}", output)
        expected_hits = (
            "/home/ctfuser",
            "/home/user123",
            "/home/papercut2",
            "/home/alexander",
            r"C:\Users\Publicity",
            r"C:\Users\Example",
            r"C:\Users\All",
        )
        for hit in expected_hits:
            self.assertIn(f":: {hit}", output)


if __name__ == "__main__":
    unittest.main()
