"""Selection rules, tree routing and the captured-output contract."""

import contextlib
import importlib.util
import io
import json
import os
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_selector.py"
SPEC = importlib.util.spec_from_file_location("skill_selector", SCRIPT)
selector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = selector
SPEC.loader.exec_module(selector)


def catalog(*paths):
    return [{"name": path.rsplit("/", 1)[-1] if path != "." else "root-skill", "path": path} for path in paths]


class TreeTests(unittest.TestCase):
    def test_branches_first_and_sorted_independently_of_catalog_order(self):
        paths = ("z-skill", "offensive-tools/windows/z-tool", "ai/a-skill", "a-skill", "offensive-tools/a-tool")
        expected = ["ai", "offensive-tools", "a-skill", "z-skill"]
        for records in (catalog(*paths), list(reversed(catalog(*paths)))):
            root = selector.build_tree(records)
            self.assertEqual([entry.node.name for entry in root.entries()], expected)
            tools = root.children["offensive-tools"]
            self.assertEqual([entry.node.name for entry in tools.entries()], ["windows", "a-tool"])
            self.assertEqual(root.skill_paths(), set(paths))

    def test_directory_with_own_skill_has_separate_leaf_and_descendants(self):
        root = selector.build_tree(catalog("offensive-coding/bof-dev", "offensive-coding/bof-dev/c-bof", "offensive-coding/bof-dev/cpp-bof"))
        branch = root.children["offensive-coding"].children["bof-dev"]
        entries = branch.entries()
        self.assertTrue(branch.is_branch)
        self.assertEqual(entries[0].label, "(this skill) bof-dev")
        self.assertFalse(entries[0].is_branch)
        self.assertEqual(entries[0].skill_paths(), {"offensive-coding/bof-dev"})
        self.assertEqual(len(branch.skill_paths()), 3)

    def test_own_skill_leaf_stays_after_child_folders(self):
        root = selector.build_tree(catalog(".", "category/skill", "own", "own/child/deeper"))
        self.assertEqual([entry.node.name for entry in root.entries()], ["category", "own", "Skills"])
        entries = root.children["own"].entries()
        self.assertTrue(entries[0].is_branch)
        self.assertTrue(entries[1].own)

    def test_root_skill_and_solitary_skill_folder_are_selectable(self):
        root = selector.build_tree(catalog(".", "standalone"))
        self.assertEqual(root.skill_paths(), {".", "standalone"})
        self.assertTrue(root.entries()[0].own)
        self.assertFalse(root.entries()[1].is_branch)
        model = selector.SelectorModel(root)
        model.handle("toggle")
        model.handle("down")
        model.handle("enter")
        self.assertEqual(model.selected_paths(), [".", "standalone"])

    def test_category_colors_inherit_and_do_not_depend_on_catalog_order(self):
        root = selector.build_tree(catalog("behaviours/example/deeper/skill", "standalone"))
        node = root.children["behaviours"].children["example"].children["deeper"].children["skill"]
        self.assertEqual(node.category, "behaviours")
        self.assertEqual(selector.category_color(node.category), selector.CATEGORY_COLORS["behaviours"])
        self.assertEqual(root.children["standalone"].category, "standalone")
        self.assertEqual(selector.category_color("custom-category"), selector.category_color("custom-category"))

    def test_paths_are_normalized_without_filesystem_access(self):
        root = selector.build_tree([{"name": "skill", "path": "coding\\nested/./skill/"}])
        self.assertEqual(root.skill_paths(), {"coding/nested/skill"})

    def test_invalid_catalogs_are_rejected(self):
        invalid = ({}, [], [None], [{"name": "a"}], [{"name": "", "path": "a"}],
                   catalog("/absolute"), catalog("../escape"), catalog("C:\\absolute"),
                   catalog("coding/skill\n"), catalog("same", "./same"))
        for records in invalid:
            with self.subTest(records=records), self.assertRaises(ValueError):
                selector.build_tree(records)


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.model = selector.SelectorModel(selector.build_tree(catalog(
            "coding/z", "coding/nested/a", "coding/nested/b", "knowledge/creator")))

    def test_tri_state_and_recursive_toggle(self):
        branch = self.model.root.children["coding"]
        paths = branch.skill_paths()
        self.assertEqual(selector.checkbox(paths, self.model.selected), "[ ]")
        self.model.toggle({"coding/nested/a"})
        self.assertEqual(selector.checkbox(paths, self.model.selected), "[.]")
        self.model.toggle(paths)
        self.assertEqual(self.model.selected, set())
        self.model.toggle(paths)
        self.assertEqual(selector.checkbox(paths, self.model.selected), "[x]")
        self.assertEqual(self.model.selected, set(paths))
        self.model.toggle(paths)
        self.assertEqual(self.model.selected, set())

    def test_space_on_partial_branch_clears_own_and_descendants_only(self):
        self.model.selected.update({"coding/nested/a", "knowledge/creator"})
        self.model.handle("toggle")
        self.assertEqual(self.model.selected, {"knowledge/creator"})

    def test_all_key_targets_current_folder_and_partial_clear(self):
        self.model.handle("enter")
        self.model.handle("right")
        self.assertEqual(self.model.view.node.path, "coding/nested")
        self.model.handle("toggle")
        self.model.handle("all")
        self.assertFalse(self.model.selected)
        self.model.handle("all")
        self.assertEqual(self.model.selected, {"coding/nested/a", "coding/nested/b"})

    def test_parent_navigation_preserves_focus_scroll_and_selection(self):
        model = selector.SelectorModel(selector.build_tree(catalog(
            "coding/z", "coding/nested/a", "coding/nested/b", "coding/other/c")))
        model.handle("enter")
        model.handle("down")
        model.viewport(1)
        parent = model.view
        model.handle("right")
        model.handle("toggle")
        model.handle("back")
        self.assertIs(model.view, parent)
        self.assertEqual(model.view.cursor, 1)
        self.assertEqual(model.view.scroll, 1)
        self.assertEqual(model.selected, {"coding/other/c"})
        model.handle("back")
        self.assertEqual(model.view.node.path, ".")
        self.assertEqual(selector.checkbox(model.focused.skill_paths(), model.selected), "[.]")

    def test_continue_requires_selection_and_cancel_never_accepts(self):
        self.assertIsNone(self.model.handle("continue"))
        self.model.handle("toggle")
        self.assertEqual(self.model.handle("continue"), "continue")
        self.assertEqual(self.model.handle("cancel"), "cancel")

    def test_page_movement_and_bounds(self):
        model = selector.SelectorModel(selector.build_tree(catalog(*(f"skill-{index:03}" for index in range(100)))))
        model.handle("page_down", 12)
        self.assertEqual(model.view.cursor, 12)
        visible, offset = model.viewport(12)
        self.assertEqual((len(visible), offset), (12, 1))
        model.handle("end")
        visible, offset = model.viewport(12)
        self.assertEqual((len(visible), offset), (12, 88))
        model.handle("down")
        self.assertEqual(model.view.cursor, 99)
        model.handle("home")
        model.handle("up")
        self.assertEqual(model.view.cursor, 0)


class TerminalContractTests(unittest.TestCase):
    def test_key_decoding(self):
        expected = {" ": "toggle", "C": "continue", "q": "cancel", "\x1b": "cancel", "\x7f": "back",
                    "\x1b[A": "up", "\x1b[6~": "page_down", "\x1b[5~": "page_up",
                    "\x1bOH": "home", "\x1b[1;5F": "end", "\r": "enter"}
        for raw, key in expected.items():
            self.assertEqual(selector.decode_key(raw), key)
        self.assertEqual(selector.decode_key("Q", windows_extended=True), "page_down")
        self.assertEqual(selector.decode_key("Q"), "cancel")
        self.assertIsNone(selector.decode_key("z"))

    def test_frames_fit_small_and_resized_terminals(self):
        model = selector.SelectorModel(selector.build_tree(catalog(*(f"very-long-skill-{index:03}" for index in range(340)))))
        model.handle("end")
        for width, height in ((80, 24), (12, 8), (3, 4), (1, 1), (100, 40), (20, 5)):
            with self.subTest(width=width, height=height):
                lines = selector.render_lines(model, width, height, "Choose skills")
                self.assertLessEqual(len(lines), height)
                self.assertTrue(all(len(line) <= max(1, width - 1) for line in lines))
                self.assertTrue(any(">" in line for line in lines))
        self.assertEqual(selector.fit_text("abc\x1b\nXYZ", 5), "abcXY")
        self.assertEqual(selector.fit_text("界界", 3), "界")

    def test_run_loop_accepts_and_cancels_with_terminal_cleanup(self):
        class FakeTerminal:
            def __init__(self, keys):
                self.keys = iter(keys)
                self.closed = False
                self.frames = []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.closed = True
            def size(self):
                return 80, 24
            def draw(self, lines):
                self.frames.append(lines)
            def read_key(self):
                return next(self.keys)

        root = selector.build_tree(catalog("skill"))
        terminal = FakeTerminal(["toggle", "continue"])
        self.assertEqual(selector.run_selector(root, "Title", lambda: terminal), ["skill"])
        self.assertTrue(terminal.closed)
        terminal = FakeTerminal(["toggle", "cancel"])
        self.assertIsNone(selector.run_selector(root, "Title", lambda: terminal))
        self.assertTrue(terminal.closed)
        terminal = FakeTerminal(["toggle"])
        with self.assertRaises(StopIteration):
            selector.run_selector(root, "Title", lambda: terminal)
        self.assertTrue(terminal.closed)

    def test_cli_stdout_contains_only_paths_or_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "catalog.json"
            filename.write_text(json.dumps(catalog("coding/skill", "standalone")), encoding="utf-8-sig")
            for paths, expected_code, expected_output in ((["coding/skill", "standalone"], 0, "coding/skill\nstandalone\n"),
                                                         (None, 1, ""), ([], 1, "")):
                stdout, stderr = io.StringIO(), io.StringIO()
                with patch.object(selector, "run_selector", return_value=paths), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = selector.main(["--skills-file", str(filename)])
                self.assertEqual(result, expected_code)
                self.assertEqual(stdout.getvalue(), expected_output)
                self.assertNotIn("\x1b", stdout.getvalue())
            with patch.object(selector, "run_selector", side_effect=selector.TerminalError("attached terminal required")), contextlib.redirect_stdout(stdout := io.StringIO()), contextlib.redirect_stderr(stderr := io.StringIO()):
                result = selector.main(["--skills-file", str(filename)])
            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("attached terminal required", stderr.getvalue())

    def test_actual_cli_without_terminal_fails_promptly_without_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "catalog.json"
            filename.write_text(json.dumps(catalog("skill")), encoding="utf-8")
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            result = subprocess.run([sys.executable, str(SCRIPT), "--skills-file", str(filename)],
                                    capture_output=True, text=True, timeout=5, **options)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("attached terminal", result.stderr)

    def test_actual_stdout_protocol_is_utf8_and_lf_only(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "catalog.json"
            filename.write_text(json.dumps(catalog("coding/caf\u00e9", "standalone")), encoding="utf-8")
            code = ("import sys; sys.path.insert(0, sys.argv[1]); import skill_selector; "
                    "skill_selector.run_selector = lambda root, title: sorted(root.skill_paths()); "
                    "sys.exit(skill_selector.main(['--skills-file', sys.argv[2]]))")
            result = subprocess.run([sys.executable, "-c", code, str(SCRIPT.parent), str(filename)],
                                    capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "coding/caf\u00e9\nstandalone\n".encode("utf-8"))
        self.assertNotIn(b"\r", result.stdout)
        self.assertEqual(result.stderr, b"")

    @unittest.skipIf(os.name == "nt", "POSIX controlling-terminal integration")
    def test_posix_terminal_with_captured_stdout_and_raw_mode_restoration(self):
        import fcntl
        import pty
        import struct
        import termios

        def attach_terminal():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        master, slave = pty.openpty()
        original_mode = termios.tcgetattr(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 12, 60, 0, 0))
        process = None
        try:
            with tempfile.TemporaryDirectory() as directory:
                filename = Path(directory) / "catalog.json"
                filename.write_text(json.dumps(catalog("coding/own", "coding/own/child", "standalone")), encoding="utf-8")
                process = subprocess.Popen([sys.executable, str(SCRIPT), "--skills-file", str(filename)],
                                           stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           preexec_fn=attach_terminal)
                visible = b""
                deadline = time.monotonic() + 5
                while b"Choose skills" not in visible and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        visible += os.read(master, 8192)
                self.assertIn(b"Choose skills", visible)
                # Own leaf -> partial branch -> clear -> select full branch -> accept.
                os.write(master, b"\r\r \x1b[D  c")
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0)
                self.assertEqual(stdout, b"coding/own\ncoding/own/child\n")
                self.assertEqual(stderr, b"")
                self.assertEqual(termios.tcgetattr(slave), original_mode)
                while select.select([master], [], [], 0)[0]:
                    visible += os.read(master, 8192)
                self.assertIn(b"[.]", visible)
                self.assertIn(b"\x1b[?25h\x1b[?1049l", visible)
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    unittest.main()
