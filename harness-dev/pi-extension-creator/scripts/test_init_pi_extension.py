from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("init_pi_extension.py")
SPEC = importlib.util.spec_from_file_location("init_pi_extension", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InitPiExtensionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="pi-extension-test-"))
        self.template = self.root / "template"
        self.template.mkdir()
        (self.template / "package.json").write_text('{"name":"pi-extension-template"}\n', encoding="utf-8")
        (self.template / "src").mkdir()
        (self.template / "src" / "index.ts").write_text("pi-extension-template\n", encoding="utf-8")

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.root)

    def test_force_preserves_unrelated_files_and_substitutes_tokens(self) -> None:
        target = self.root / "target"
        target.mkdir()
        keep = target / "keep.txt"
        keep.write_text("keep", encoding="utf-8")

        MODULE.copy_template(self.template, target, "@scope/test", force=True)

        self.assertEqual(keep.read_text(encoding="utf-8"), "keep")
        self.assertIn('@scope/test', (target / "package.json").read_text(encoding="utf-8"))
        self.assertEqual((target / "src" / "index.ts").read_text(encoding="utf-8"), "@scope/test\n")

    def test_existing_target_requires_force(self) -> None:
        target = self.root / "target"
        target.mkdir()
        with self.assertRaises(FileExistsError):
            MODULE.copy_template(self.template, target, "test", force=False)

    def test_rejects_template_containment(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.copy_template(self.template, self.template, "test", force=True)
        with self.assertRaises(ValueError):
            MODULE.copy_template(self.template, self.template.parent, "test", force=True)

    def test_rejects_existing_collision_and_non_directory_parent_before_writing(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "package.json").mkdir()
        with self.assertRaises(ValueError):
            MODULE.copy_template(self.template, target, "test", force=True)

        target = self.root / "target-parent-file"
        target.mkdir()
        (target / "src").write_text("sentinel", encoding="utf-8")
        with self.assertRaises(ValueError):
            MODULE.copy_template(self.template, target, "test", force=True)
        self.assertEqual((target / "src").read_text(encoding="utf-8"), "sentinel")

    def test_rejects_parent_symlink_without_external_mutation(self) -> None:
        target = self.root / "target-link"
        outside = self.root / "outside"
        target.mkdir()
        outside.mkdir()
        try:
            (target / "src").symlink_to(outside, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("directory symlinks are unavailable")

        with self.assertRaises(ValueError):
            MODULE.copy_template(self.template, target, "test", force=True)
        self.assertFalse((outside / "index.ts").exists())


if __name__ == "__main__":
    unittest.main()
