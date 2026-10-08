#!/usr/bin/env python3
"""Keyboard tree selector. The supplied catalog is the sole source of skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


CATEGORY_COLORS = {
    "offensive-tools": 36,
    "offensive-techniques": 33,
    "offensive-roles": 35,
    "offensive-coding": 31,
    "offensive-hardware": 32,
    "offensive-ctf": 34,
    "behaviours": 96,
    "knowledge": 95,
    "coding": 94,
    "ai": 93,
    "hardware": 92,
}
FALLBACK_COLORS = (36, 33, 35, 32, 34, 96, 95, 94, 93, 92)
KEYS = {
    " ": "toggle", "\r": "enter", "\n": "enter", "\t": "down",
    "\x08": "back", "\x7f": "back", "\x03": "cancel", "\x04": "cancel",
    "\x1b": "cancel", "a": "all", "c": "continue", "q": "cancel",
}
WINDOWS_KEYS = {
    "H": "up", "P": "down", "K": "back", "M": "right",
    "G": "home", "O": "end", "I": "page_up", "Q": "page_down",
}
CSI_KEYS = {"A": "up", "B": "down", "C": "right", "D": "back", "H": "home", "F": "end"}
TILDE_KEYS = {"1": "home", "2": None, "3": None, "4": "end", "5": "page_up", "6": "page_down", "7": "home", "8": "end"}


def normalize_path(value: str) -> str:
    """Accept source-relative paths only and use portable slash separators."""
    if not value or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Skill paths must be nonempty and contain no control characters.")
    value = value.replace("\\", "/")
    if value.startswith("/") or ":" in value:
        raise ValueError("Skill paths must be relative to the source directory.")
    parts = [part for part in value.split("/") if part and part != "."]
    if ".." in parts:
        raise ValueError("Skill paths cannot contain parent directory traversal.")
    return "/".join(parts) or "."


@dataclass(eq=False)
class Node:
    name: str
    path: str
    parent: Node | None = field(default=None, repr=False)
    skill_name: str | None = None
    children: dict[str, Node] = field(default_factory=dict)

    @property
    def is_branch(self) -> bool:
        return bool(self.children)

    def skill_paths(self) -> frozenset[str]:
        paths = {self.path} if self.skill_name is not None else set()
        for child in self.children.values():
            paths.update(child.skill_paths())
        return frozenset(paths)

    def entries(self) -> list[Entry]:
        entries = [Entry(child) for child in self.children.values()]
        if self.skill_name is not None:
            entries.append(Entry(self, own=True))
        entries.sort(key=lambda entry: (not entry.is_branch, not entry.own, entry.node.name.casefold(), entry.node.name))
        return entries

    @property
    def category(self) -> str:
        node = self
        while node.parent is not None and node.parent.parent is not None:
            node = node.parent
        return node.name if node.parent is not None else (node.skill_name or node.name)


@dataclass(frozen=True)
class Entry:
    node: Node
    own: bool = False

    @property
    def is_branch(self) -> bool:
        return self.node.is_branch and not self.own

    @property
    def label(self) -> str:
        if self.own:
            return "(this skill) " + (self.node.skill_name or self.node.name)
        return self.node.name + "/" if self.is_branch else (self.node.skill_name or self.node.name)

    def skill_paths(self) -> frozenset[str]:
        return frozenset((self.node.path,)) if self.own else self.node.skill_paths()


def build_tree(records: object) -> Node:
    if not isinstance(records, list):
        raise ValueError("The skill catalog must be a JSON array.")
    root = Node("Skills", ".")
    seen = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str) or not isinstance(record.get("path"), str):
            raise ValueError("Every catalog entry requires string name and path fields.")
        name = record["name"]
        if not name.strip() or any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError("Skill names must be nonempty and contain no control characters.")
        path = normalize_path(record["path"])
        if path in seen:
            raise ValueError("Duplicate skill path: " + path)
        seen.add(path)
        node = root
        if path != ".":
            parts = path.split("/")
            for index, part in enumerate(parts):
                if part not in node.children:
                    node.children[part] = Node(part, "/".join(parts[:index + 1]), node)
                node = node.children[part]
        node.skill_name = name
    if not seen:
        raise ValueError("No skills are available in the supplied catalog.")
    return root


def category_color(category: str) -> int:
    if category in CATEGORY_COLORS:
        return CATEGORY_COLORS[category]
    digest = hashlib.sha256(category.encode("utf-8")).digest()
    return FALLBACK_COLORS[int.from_bytes(digest[:4], "big") % len(FALLBACK_COLORS)]


def checkbox(paths: Iterable[str], selected: set[str]) -> str:
    paths = frozenset(paths)
    chosen = paths.intersection(selected)
    return "[x]" if paths and chosen == paths else "[.]" if chosen else "[ ]"


@dataclass
class View:
    node: Node
    cursor: int = 0
    scroll: int = 0


class SelectorModel:
    def __init__(self, root: Node):
        self.root = root
        self.selected: set[str] = set()
        self.views = [View(root)]

    @property
    def view(self) -> View:
        return self.views[-1]

    @property
    def entries(self) -> list[Entry]:
        return self.view.node.entries()

    @property
    def focused(self) -> Entry:
        return self.entries[self.view.cursor]

    def toggle(self, paths: Iterable[str]) -> None:
        paths = frozenset(paths)
        if self.selected.intersection(paths):
            self.selected.difference_update(paths)
        else:
            self.selected.update(paths)

    def viewport(self, rows: int) -> tuple[list[Entry], int]:
        rows = max(1, rows)
        view = self.view
        entries = self.entries
        view.cursor = min(view.cursor, len(entries) - 1)
        view.scroll = min(view.scroll, max(0, len(entries) - rows))
        if view.cursor < view.scroll:
            view.scroll = view.cursor
        elif view.cursor >= view.scroll + rows:
            view.scroll = view.cursor - rows + 1
        return entries[view.scroll:view.scroll + rows], view.scroll

    def handle(self, key: str | None, page_size: int = 10) -> str | None:
        if key == "cancel":
            return "cancel"
        if key == "continue":
            return "continue" if self.selected else None
        if key == "all":
            self.toggle(self.view.node.skill_paths())
        elif key == "toggle":
            self.toggle(self.focused.skill_paths())
        elif key in ("enter", "right"):
            entry = self.focused
            if entry.is_branch:
                self.views.append(View(entry.node))
            elif key == "enter":
                self.toggle(entry.skill_paths())
        elif key == "back":
            if len(self.views) > 1:
                self.views.pop()
        elif key == "home":
            self.view.cursor = 0
        elif key == "end":
            self.view.cursor = len(self.entries) - 1
        elif key in ("up", "down", "page_up", "page_down"):
            distance = max(1, page_size) if key.startswith("page_") else 1
            if key in ("up", "page_up"):
                distance = -distance
            self.view.cursor = max(0, min(len(self.entries) - 1, self.view.cursor + distance))
        return None

    def selected_paths(self) -> list[str]:
        return sorted(self.selected, key=lambda path: (path.casefold(), path))


def decode_key(value: str, windows_extended: bool = False) -> str | None:
    if windows_extended:
        return WINDOWS_KEYS.get(value)
    if value in KEYS:
        return KEYS[value]
    if len(value) == 1:
        return KEYS.get(value.lower())
    match = re.fullmatch(r"\x1b(?:\[[\d;]*|O)([ABCDHF])", value)
    if match:
        return CSI_KEYS[match.group(1)]
    match = re.fullmatch(r"\x1b\[(\d+)(?:;\d+)*~", value)
    return TILDE_KEYS.get(match.group(1)) if match else None


def fit_text(value: str, width: int) -> str:
    """Clip by terminal cells and keep control characters out of the frame."""
    width = max(0, width)
    output = []
    used = 0
    for char in value:
        if unicodedata.category(char).startswith("C"):
            continue
        cells = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in "WF" else 1
        if used + cells > width:
            break
        output.append(char)
        used += cells
    return "".join(output)


def body_rows(height: int) -> int:
    overhead = 5 if height >= 8 else 3 if height >= 4 else 1 if height >= 2 else 0
    return max(1, height - overhead)


def render_lines(model: SelectorModel, width: int, height: int, title: str, color: bool = False) -> list[str]:
    width, height = max(1, width), max(1, height)
    # Leave the final column free so terminals never wrap a full-width row.
    width = max(1, width - 1)
    entries, offset = model.viewport(body_rows(height))
    breadcrumb = "Skills" + (" / " + model.view.node.path.replace("/", " / ") if model.view.node is not model.root else "")
    count = f"{len(model.selected)} / {len(model.root.skill_paths())} selected"
    position = f"{offset + 1}-{offset + len(entries)} / {len(model.entries)}"
    if height >= 8:
        lines = [fit_text(title, width), fit_text(breadcrumb, width), fit_text(count + "  |  " + position, width)]
    elif height >= 4:
        lines = [fit_text(breadcrumb, width), fit_text(count + "  |  " + position, width)]
    elif height >= 2:
        lines = [fit_text(count, width)]
    else:
        lines = []
    for index, entry in enumerate(entries, offset):
        focused = index == model.view.cursor
        marker = ">" if focused else " "
        branch = "+" if entry.is_branch else " "
        line = fit_text(f"{marker} {checkbox(entry.skill_paths(), model.selected)} {branch} {entry.label}", width)
        if color:
            style = f"\x1b[{category_color(entry.node.category)}m" + ("\x1b[7m" if focused else "")
            line = style + line + "\x1b[0m"
        lines.append(line)
    if height >= 8:
        lines.extend((fit_text("Space toggle | Enter/Right open | Left/Backspace back | A all here", width),
                      fit_text("C continue | Q/Esc cancel | Up/Down/Home/End/PgUp/PgDn move", width)))
    elif height >= 4:
        lines.append(fit_text("Space toggle | Enter open | Left back | A all | C continue | Q cancel", width))
    return lines[:height]


class TerminalError(RuntimeError):
    pass


class Terminal:
    """Use the controlling terminal independently of captured stdout/stdin."""

    def __init__(self):
        self.stream = None
        self.fd = None
        self.input_stream = None
        self.old_mode = None
        self.old_termios = None
        self.started = False
        self.cursor_visible = True

    def __enter__(self):
        try:
            if os.name == "nt":
                self._open_windows()
            else:
                self._open_posix()
            self.started = True
            self.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")
            return self
        except BaseException as error:
            self.__exit__(None, None, None)
            if not isinstance(error, (OSError, ValueError, TerminalError)):
                raise
            raise TerminalError("Interactive skill selection requires an attached terminal. Use --all or --skills in the installer.") from error

    def _open_posix(self):
        import termios
        import tty

        self.fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        if not os.isatty(self.fd):
            raise TerminalError("No controlling terminal.")
        self.old_termios = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)

    def _open_windows(self):
        import ctypes
        import msvcrt
        from ctypes import wintypes

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.GetConsoleWindow.restype = wintypes.HWND
        # Hidden consoles can expose CONIN$/CONOUT$ without an interactive surface.
        if not self.kernel.GetConsoleWindow():
            raise TerminalError("No attached console window.")
        self.kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.GetConsoleMode.restype = wintypes.BOOL
        self.kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.SetConsoleMode.restype = wintypes.BOOL
        self.stream = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        self.input_stream = open("CONIN$", "r", encoding="utf-8")
        self.handle = msvcrt.get_osfhandle(self.stream.fileno())
        mode = wintypes.DWORD()
        input_mode = wintypes.DWORD()
        if not self.kernel.GetConsoleMode(self.handle, ctypes.byref(mode)) or not self.kernel.GetConsoleMode(msvcrt.get_osfhandle(self.input_stream.fileno()), ctypes.byref(input_mode)):
            raise TerminalError("No attached console.")
        self.old_mode = mode.value
        if not self.kernel.SetConsoleMode(self.handle, mode.value | 0x0001 | 0x0004):
            raise TerminalError("The console does not support terminal escape sequences.")

        class CursorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("visible", wintypes.BOOL)]

        self.kernel.GetConsoleCursorInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(CursorInfo)]
        info = CursorInfo()
        if self.kernel.GetConsoleCursorInfo(self.handle, ctypes.byref(info)):
            self.cursor_visible = bool(info.visible)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.started:
                cursor = "\x1b[?25h" if self.cursor_visible else "\x1b[?25l"
                self.write("\x1b[0m" + cursor + "\x1b[?1049l")
        finally:
            if os.name == "nt":
                if self.old_mode is not None:
                    self.kernel.SetConsoleMode(self.handle, self.old_mode)
                if self.input_stream is not None:
                    self.input_stream.close()
                if self.stream is not None:
                    self.stream.close()
            elif self.fd is not None:
                try:
                    if self.old_termios is not None:
                        import termios
                        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_termios)
                finally:
                    os.close(self.fd)

    def write(self, value: str) -> None:
        if self.stream is not None:
            self.stream.write(value)
            self.stream.flush()
        elif self.fd is not None:
            data = value.encode("utf-8")
            while data:
                data = data[os.write(self.fd, data):]

    def size(self) -> tuple[int, int]:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Coord(ctypes.Structure):
                _fields_ = [("x", wintypes.SHORT), ("y", wintypes.SHORT)]

            class Rect(ctypes.Structure):
                _fields_ = [("left", wintypes.SHORT), ("top", wintypes.SHORT), ("right", wintypes.SHORT), ("bottom", wintypes.SHORT)]

            class BufferInfo(ctypes.Structure):
                _fields_ = [("size", Coord), ("cursor", Coord), ("attributes", wintypes.WORD), ("window", Rect), ("maximum", Coord)]

            self.kernel.GetConsoleScreenBufferInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(BufferInfo)]
            info = BufferInfo()
            if self.kernel.GetConsoleScreenBufferInfo(self.handle, ctypes.byref(info)):
                return max(1, info.window.right - info.window.left + 1), max(1, info.window.bottom - info.window.top + 1)
        else:
            try:
                size = os.get_terminal_size(self.fd)
                return max(1, size.columns), max(1, size.lines)
            except OSError:
                pass
        return 80, 24

    def draw(self, lines: list[str]) -> None:
        self.write("\x1b[H" + "\r\n".join("\x1b[2K" + line for line in lines) + "\x1b[J")

    def read_key(self) -> str | None:
        if os.name == "nt":
            import msvcrt

            deadline = time.monotonic() + 0.1
            while not msvcrt.kbhit():
                if time.monotonic() >= deadline:
                    return None
                time.sleep(0.01)
            value = msvcrt.getwch()
            if value in ("\x00", "\xe0"):
                return decode_key(msvcrt.getwch(), windows_extended=True)
            return decode_key(value)

        import select

        if not select.select([self.fd], [], [], 0.1)[0]:
            return None
        value = os.read(self.fd, 1)
        if not value:
            return "cancel"
        if value == b"\x1b":
            while len(value) < 32 and select.select([self.fd], [], [], 0.035)[0]:
                value += os.read(self.fd, 1)
                if len(value) > 2 and (65 <= value[-1] <= 90 or 97 <= value[-1] <= 122 or value[-1] == 126):
                    break
        return decode_key(value.decode("ascii", errors="ignore"))


def run_selector(root: Node, title: str, terminal_factory: Callable = Terminal) -> list[str] | None:
    model = SelectorModel(root)
    with terminal_factory() as terminal:
        dirty = True
        dimensions = None
        while True:
            current_size = terminal.size()
            if dirty or current_size != dimensions:
                dimensions = current_size
                terminal.draw(render_lines(model, *dimensions, title, color=True))
                dirty = False
            key = terminal.read_key()
            if key is None:
                continue
            action = model.handle(key, body_rows(dimensions[1]))
            if action == "cancel":
                return None
            if action == "continue":
                return model.selected_paths()
            dirty = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-file", required=True, type=Path, help="JSON catalog produced by the installer")
    parser.add_argument("--title", default="malskill - Choose skills")
    args = parser.parse_args(argv)
    try:
        with args.skills_file.open(encoding="utf-8-sig") as stream:
            root = build_tree(json.load(stream))
        paths = run_selector(root, args.title)
    except KeyboardInterrupt:
        paths = None
    except (OSError, ValueError, TerminalError) as error:
        print("Skill selector: " + str(error), file=sys.stderr)
        return 2
    if not paths:
        print("Selection cancelled.", file=sys.stderr)
        return 1
    # Captured output is a UTF-8/LF protocol, including under Windows shells.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.write("".join(path + "\n" for path in paths))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
