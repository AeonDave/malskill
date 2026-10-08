"""Bash installer regression checks against isolated skill catalogs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


REPOSITORY = Path(__file__).resolve().parents[1]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if os.name == "nt" and GIT_BASH.exists() else shutil.which("bash")


@unittest.skipUnless(BASH, "Bash is unavailable")
class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="malskill bash test ")
        self.root = Path(self.temporary.name)
        self.installer = self.root / "installer"
        self.installer.mkdir()
        shutil.copy2(REPOSITORY / "install.sh", self.installer / "install.sh")
        helpers = self.installer / "scripts"
        helpers.mkdir(parents=True)
        for name in ("quick_validate.py", "package_skill.py"):
            shutil.copy2(REPOSITORY / "scripts" / name, helpers / name)
        self.selector = self.installer / "scripts/skill_selector.py"
        self.selector.write_text(
            "import json, os, pathlib, sys\n"
            "records = json.loads(pathlib.Path(sys.argv[sys.argv.index('--skills-file') + 1]).read_text(encoding='utf-8'))\n"
            "assert all(set(record) == {'name', 'path'} for record in records)\n"
            "if os.environ.get('SELECTOR_CANCEL'): sys.exit(1)\n"
            "for path in json.loads(os.environ['SELECTOR_PATHS']): print(path)\n",
            encoding="utf-8",
        )
        self.source = self.root / "source"
        self.source.mkdir()
        for path in ("solo", "category/nested/alpha", "category/beta"):
            self.skill(path)
        self.destination = self.root / "output"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def skill(self, relative: str) -> Path:
        path = self.source if relative == "." else self.source / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {path.name}\ndescription: Test the isolated installer fixture.\n---\n\n# Fixture\n",
            encoding="utf-8",
        )
        (path / "payload.txt").write_text(relative, encoding="utf-8")
        return path

    def run_installer(self, *arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(environment or {})
        return subprocess.run(
            [BASH, (self.installer / "install.sh").as_posix(), "--source", self.source.as_posix(),
             "--destination", self.destination.as_posix(), *arguments],
            cwd=self.installer, env=env, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL, capture_output=True, timeout=45,
        )

    def require_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_formats_and_layouts(self) -> None:
        for format_name in ("folder", "skill", "zip"):
            for layout in ("flat", "group"):
                with self.subTest(format=format_name, layout=layout):
                    self.destination = self.root / (format_name + "-" + layout)
                    self.require_success(self.run_installer("--all", "--format", format_name, "--layout", layout))
                    for path in ("solo", "category/nested/alpha", "category/beta"):
                        relative = Path(path) if layout == "group" else Path(path).name
                        target = self.destination / relative
                        if format_name == "folder":
                            self.assertTrue((target / "SKILL.md").is_file())
                            self.assertEqual((target / "payload.txt").read_text(encoding="utf-8"), path)
                        else:
                            archive = target.with_suffix("." + format_name)
                            with zipfile.ZipFile(archive) as bundle:
                                self.assertIn(Path(path).name + "/SKILL.md", bundle.namelist())

    def test_root_skill_is_discovered(self) -> None:
        self.skill(".")
        self.require_success(self.run_installer("--skills", ".", "--format", "folder", "--layout", "group"))
        self.assertTrue((self.destination / self.source.name / "SKILL.md").is_file())

    def test_root_skill_target_collision_fails_before_writes(self) -> None:
        self.skill(".")
        self.skill(self.source.name)
        for format_name in ("folder", "skill", "zip"):
            with self.subTest(format=format_name):
                result = self.run_installer("--all", "--format", format_name, "--layout", "group")
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("would collide", result.stderr)
                self.assertFalse(self.destination.exists())
                self.assertTrue((self.source / "SKILL.md").is_file())
                self.assertTrue((self.source / self.source.name / "SKILL.md").is_file())

    def test_selector_mapping_with_spaces_and_unicode(self) -> None:
        self.skill("category/café/gamma")
        self.require_success(self.run_installer(
            "--format", "folder", "--layout", "group",
            environment={"SELECTOR_PATHS": json.dumps(["category/nested/alpha", "category/café/gamma", "solo"])},
        ))
        self.assertTrue((self.destination / "category/nested/alpha/SKILL.md").is_file())
        self.assertTrue((self.destination / "solo/SKILL.md").is_file())
        self.assertTrue((self.destination / "category/café/gamma/SKILL.md").is_file())
        self.assertFalse((self.destination / "category/beta").exists())

    def test_cancel_and_unknown_selector_result_do_not_install(self) -> None:
        for env in ({"SELECTOR_CANCEL": "1"}, {"SELECTOR_PATHS": '["missing"]'}):
            result = self.run_installer("--format", "folder", "--layout", "flat", environment=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.destination.exists())

    def test_invalid_and_ambiguous_refs_fail_before_writes(self) -> None:
        self.skill("other/beta")
        for reference in ("missing", "beta", "category/beta,missing"):
            result = self.run_installer("--skills", reference, "--format", "folder", "--layout", "group")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(self.destination.exists())

    def test_duplicate_names_rejected_flat_and_allowed_grouped(self) -> None:
        self.skill("other/solo")
        result = self.run_installer("--all", "--format", "folder", "--layout", "flat")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.destination.exists())
        self.require_success(self.run_installer("--all", "--format", "folder", "--layout", "group"))
        self.assertTrue((self.destination / "other/solo/SKILL.md").is_file())

    def test_source_overlap_preserves_selected_and_unselected_sources(self) -> None:
        self.skill("other/solo")
        for destination, reference, layout in (
            (self.source, "solo", "flat"),
            (self.source, "other/solo", "flat"),
            (self.source, "category/beta", "group"),
            (self.source / "solo/generated", "solo", "flat"),
        ):
            with self.subTest(destination=destination, reference=reference):
                self.destination = destination
                result = self.run_installer("--skills", reference, "--format", "folder", "--layout", layout)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("overlaps source skill", result.stderr)
                self.assertTrue((self.source / "solo/SKILL.md").is_file())
                self.assertTrue((self.source / "other/solo/SKILL.md").is_file())
                self.assertFalse((self.source / "solo/generated").exists())

    def test_overwrite_removes_stale_installed_files(self) -> None:
        arguments = ("--skills", "solo", "--format", "folder", "--layout", "flat")
        self.require_success(self.run_installer(*arguments))
        stale = self.destination / "solo/stale.txt"
        stale.write_text("old", encoding="utf-8")
        self.require_success(self.run_installer(*arguments))
        self.assertFalse(stale.exists())

    def test_packaging_failure_preserves_existing_archive(self) -> None:
        arguments = ("--skills", "solo", "--format", "zip", "--layout", "flat")
        self.require_success(self.run_installer(*arguments))
        archive = self.destination / "solo.zip"
        previous = archive.read_bytes()
        packager = self.installer / "scripts/package_skill.py"
        packager.write_text("raise SystemExit(1)\n", encoding="utf-8")
        self.assertNotEqual(self.run_installer(*arguments).returncode, 0)
        self.assertEqual(archive.read_bytes(), previous)

    def test_missing_option_value(self) -> None:
        result = self.run_installer("--skills")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing value", result.stderr)


if __name__ == "__main__":
    unittest.main()
