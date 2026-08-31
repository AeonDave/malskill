#!/usr/bin/env python3
"""Heuristic static linter for MCP 2026-07-28 server source and docs.

Regex-based and intentionally limited: it flags suspicious legacy terms and
common stateless-core omissions. Every finding is a review hint, never proof of
a bug or conformance. Point it at server code, not this skill's reference docs
(which discuss deprecated features on purpose).

Usage:
  python check_mcp_conformance.py <file-or-dir> [--format text|json] [--strict]

Exit code: 1 if any error-level finding (or any finding with --strict), else 0.
"""
import argparse
import json
import os
import re
import sys

TEXT_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".cs", ".rs",
            ".java", ".rb", ".php", ".md", ".json", ".yaml", ".yml", ".toml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
             "dist", "build", ".mypy_cache", ".pytest_cache"}

# (rule_id, severity, regex, message)
LINE_RULES = [
    ("mcp-session-id", "warn", re.compile(r"Mcp-Session-Id", re.I),
     "modern 2026-07-28 servers ignore this legacy header; isolate any compatibility behavior"),
    ("last-event-id", "warn", re.compile(r"Last-Event-ID", re.I),
     "modern 2026-07-28 streams are not resumable; isolate any legacy compatibility behavior"),
    ("tasks-list", "error", re.compile(r"tasks/list"),
     "no official tasks/list method exists; expose a custom admin list tool, labelled as custom"),
    ("initialized-notif", "warn", re.compile(r"notifications/initialized"),
     "the initialize handshake is legacy-only; keep it in a compatibility adapter"),
    ("resources-subscribe", "warn", re.compile(r"resources/(?:un)?subscribe"),
     "resources/subscribe was removed; use subscriptions/listen"),
    ("include-context", "warn", re.compile(
        r"includeContext.{0,40}(?:thisServer|allServers)|"
        r"(?:thisServer|allServers).{0,40}includeContext", re.I),
     "includeContext thisServer/allServers is deprecated; omit it or use none"),
    ("http-sse", "warn", re.compile(r"HTTP\+SSE", re.I),
     "HTTP+SSE transport is deprecated; use Streamable HTTP"),
    ("initialize", "info", re.compile(r"(?<![A-Za-z_])initialize(?![A-Za-z_])"),
     "initialize handshake is legacy in modern MCP; carry version/capabilities in per-request _meta"),
]

SENSITIVE_XHDR = re.compile(
    r"x-mcp-header.{0,80}?(password|secret|token|api[_-]?key|authorization|bearer)",
    re.I | re.S)
LIST_METHOD = re.compile(
    r"tools/list|prompts/list|resources/list|resources/read|resources/templates/list")
SERVER_MARKER = re.compile(
    r"tools/(?:call|list)|prompts/(?:get|list)|resources/(?:read|list|templates/list)|server/discover")


class Finding:
    __slots__ = ("path", "line", "severity", "rule", "message")

    def __init__(self, path, line, severity, rule, message):
        self.path = path
        self.line = line
        self.severity = severity
        self.rule = rule
        self.message = message


def iter_files(root):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in TEXT_EXT:
                yield os.path.join(dirpath, name)


def scan_file(path, findings, flags):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return
    for idx, line in enumerate(text.splitlines(), 1):
        for rule_id, sev, rx, msg in LINE_RULES:
            if rx.search(line):
                findings.append(Finding(path, idx, sev, rule_id, msg))
    if SENSITIVE_XHDR.search(text):
        findings.append(Finding(path, 0, "warn", "sensitive-x-mcp-header",
                        "x-mcp-header near a sensitive field; never mirror secrets/PII into headers"))
    if LIST_METHOD.search(text) and "ttlMs" not in text:
        findings.append(Finding(path, 0, "warn", "cache-metadata",
                        "list/read handler present but no ttlMs/cacheScope found in this file"))
    if "tools/call" in text and "resultType" not in text:
        findings.append(Finding(path, 0, "warn", "result-type",
                        "tools/call handling present but no resultType; every result must carry resultType"))
    if SERVER_MARKER.search(text):
        flags["is_server"] = True
    if "server/discover" in text:
        flags["has_discover"] = True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Heuristic MCP 2026-07-28 source scanner.")
    ap.add_argument("path", help="File or directory to scan.")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--strict", action="store_true",
                    help="Exit nonzero on any finding, not only errors.")
    args = ap.parse_args(argv)
    if not os.path.exists(args.path):
        print(f"error: path does not exist: {args.path}", file=sys.stderr)
        return 2

    findings = []
    flags = {"is_server": False, "has_discover": False}
    for path in iter_files(args.path):
        scan_file(path, findings, flags)
    if flags["is_server"] and not flags["has_discover"]:
        findings.append(Finding(args.path, 0, "warn", "discover-missing",
                        "server exposes MCP methods but no server/discover found; servers MUST implement it"))

    findings.sort(key=lambda f: (f.path, f.line, f.rule))
    if args.format == "json":
        print(json.dumps([{"path": f.path, "line": f.line, "severity": f.severity,
                           "rule": f.rule, "message": f.message} for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: [{f.severity}] {f.rule}: {f.message}")
        errors = sum(1 for f in findings if f.severity == "error")
        print(f"\n{len(findings)} finding(s), {errors} error(s)")

    has_error = any(f.severity == "error" for f in findings)
    return 1 if (has_error or (args.strict and findings)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
