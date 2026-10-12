#!/usr/bin/env python3
"""Summarize Ashura v5 diagnostic logs as a privacy-limited CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
from pathlib import Path


CSV_FIELDS = (
    "sample", "build", "ubr", "arch", "probe_version", "schema", "ubr_status",
    "collected_utc", "ldr_entries", "ldr_all_sane", "ldr_truncation_reported",
    "ldr_outcome", "shadow_named_exports", "shadow_names_inspected", "shadow_outcome",
    "module_seen_count",
    "module_missing_count", "module_ok_count", "module_error_count",
    "module_skipped_count", "module_fault_count", "module_not_run_count",
    "prefinal_outcome", "prefinal_module_errors", "prefinal_module_skips",
    "prefinal_fault", "prefinal_log_error", "prefinal_stdout_error", "exit_code",
    "final_stdout_result", "collector_exe_sha256", "ntdll_file_sha256",
    "raw_log_basename", "raw_log_sha256",
)

EXPECTED_MODULES = frozenset({
    "capability", "tls_sig", "pp8", "horizon", "shadow", "ldr", "gadgets", "ssn",
})
MODULE_STATUSES = {
    "ok": "module_ok_count",
    "error": "module_error_count",
    "skipped": "module_skipped_count",
    "fault": "module_fault_count",
    "not_run": "module_not_run_count",
}
UNKNOWN = "unknown"
IDENTITY_REQUIRED = ("build", "ubr", "arch", "v", "schema", "ubr_status", "collected_utc")
PAIR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
UINT_RE = re.compile(r"\d+\Z")
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")
SAFE_LOG_BASENAME_RE = re.compile(
    r"ashura_survey_\d+_\d+_\d{8}T\d{9}Z_\d+_\d+_x64\.log\Z"
)
PREFINAL_OUTCOMES = frozenset({"ok", "incomplete"})


class LogError(ValueError):
    """A malformed or unsupported survey record."""


def _pairs(text: str, context: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for match in PAIR_RE.finditer(text):
        key, value = match.groups()
        if key in pairs:
            raise LogError(f"{context}: duplicate {key} field")
        pairs[key] = value
    # Reject tokens that look like malformed key/value records; ignore ordinary labels.
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*=", text) and not pairs:
        raise LogError(f"{context}: malformed fields")
    return pairs


def _required(pairs: dict[str, str], key: str, context: str) -> str:
    value = pairs.get(key)
    if value is None or value == "":
        raise LogError(f"{context}: missing {key}")
    return value


def _uint(value: str, context: str) -> int:
    if not UINT_RE.fullmatch(value):
        raise LogError(f"{context}: expected an unsigned integer")
    return int(value)


def _sample_id(index: int) -> str:
    """Excel-style letters: A..Z, AA, AB, ..."""
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def summarize_log(path: Path, sample: str) -> dict[str, str]:
    source = f"sample {sample}"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LogError(f"{source}: unable to read log") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LogError(f"{source}: log is not UTF-8") from exc

    identity: dict[str, str] | None = None
    ldr_end_count: int | None = None
    ldr_outcome: str | None = None
    ldr_entry_sanity: dict[int, int] = {}
    ldr_truncated: int | None = None
    shadow: dict[str, str] | None = None
    module_outcomes: dict[str, str] = {}
    prefinal: dict[str, str] | None = None

    for line_number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        context = f"{source}, line {line_number}"
        if line.startswith("identity "):
            if identity is not None:
                raise LogError(f"{context}: duplicate identity record")
            identity = _pairs(line[len("identity "):], context)
        elif line.startswith("ldr end "):
            values = _pairs(line[len("ldr end "):], context)
            count = _uint(_required(values, "entries", context), context)
            outcome = _required(values, "outcome", context)
            if outcome not in {"ok", "error"}:
                raise LogError(f"{context}: unsupported ldr outcome")
            if ldr_end_count is not None:
                raise LogError(f"{context}: duplicate ldr end record")
            ldr_end_count = count
            ldr_outcome = outcome
        elif line.startswith("ldr entry="):
            values = _pairs(line[len("ldr "):], context)
            index = _uint(_required(values, "entry", context), context)
            sane = _uint(_required(values, "sane", context), context)
            if sane not in (0, 1):
                raise LogError(f"{context}: sane must be 0 or 1")
            if index in ldr_entry_sanity:
                raise LogError(f"{context}: duplicate ldr entry index")
            ldr_entry_sanity[index] = sane
        elif line.startswith("ldr truncated="):
            values = _pairs(line[len("ldr "):], context)
            value = _uint(_required(values, "truncated", context), context)
            if value not in (0, 1):
                raise LogError(f"{context}: truncated must be 0 or 1")
            if ldr_truncated is not None:
                raise LogError(f"{context}: duplicate ldr truncation record")
            ldr_truncated = value
        elif line.startswith("shadow exports="):
            if shadow is not None:
                raise LogError(f"{context}: duplicate shadow record")
            shadow = _pairs(line[len("shadow "):], context)
        elif line.startswith("module "):
            match = re.fullmatch(r"module ([A-Za-z0-9_]+) outcome=([^\s]+)", line)
            if not match:
                raise LogError(f"{context}: malformed module record")
            name, status = match.groups()
            if name not in EXPECTED_MODULES:
                raise LogError(f"{context}: unexpected module name")
            if name in module_outcomes:
                raise LogError(f"{context}: duplicate module record")
            if status not in MODULE_STATUSES:
                raise LogError(f"{context}: unsupported module status")
            module_outcomes[name] = status
        elif line.startswith("survey prefinal "):
            if prefinal is not None:
                raise LogError(f"{context}: duplicate prefinal record")
            prefinal = _pairs(line[len("survey prefinal "):], context)

    if identity is None:
        raise LogError(f"{source}: missing identity record")
    missing = [key for key in IDENTITY_REQUIRED if key not in identity]
    if missing:
        raise LogError(f"{source}: identity missing {', '.join(missing)}")
    if identity["v"] != "5" or identity["schema"] != "5" or identity["arch"] != "x64":
        raise LogError(f"{source}: unsupported identity (requires v=5 schema=5 arch=x64)")
    build = _required(identity, "build", source)
    ubr = _required(identity, "ubr", source)
    if not UINT_RE.fullmatch(build) or not UINT_RE.fullmatch(ubr):
        raise LogError(f"{source}: build and ubr must be unsigned integers")
    if not TIME_RE.fullmatch(identity["collected_utc"]):
        raise LogError(f"{source}: invalid collected_utc")
    if not UINT_RE.fullmatch(identity["ubr_status"]):
        raise LogError(f"{source}: invalid ubr_status")
    if ldr_end_count is not None and any(index >= ldr_end_count for index in ldr_entry_sanity):
        raise LogError(f"{source}: ldr entry index exceeds reported entry count")

    row = {field: UNKNOWN for field in CSV_FIELDS}
    row.update({
        "sample": sample,
        "build": build,
        "ubr": ubr,
        "arch": "x64",
        "probe_version": "5",
        "schema": "5",
        "ubr_status": identity["ubr_status"],
        "collected_utc": identity["collected_utc"],
        "raw_log_basename": path.name if SAFE_LOG_BASENAME_RE.fullmatch(path.name) else UNKNOWN,
        "raw_log_sha256": hashlib.sha256(raw).hexdigest(),
        "module_seen_count": str(len(module_outcomes)),
        "module_missing_count": str(len(EXPECTED_MODULES - module_outcomes.keys())),
    })
    if ldr_end_count is not None:
        row["ldr_entries"] = str(ldr_end_count)
        row["ldr_outcome"] = ldr_outcome or UNKNOWN
        if len(ldr_entry_sanity) == ldr_end_count:
            row["ldr_all_sane"] = str(int(all(ldr_entry_sanity.values())))
    if ldr_truncated is not None:
        row["ldr_truncation_reported"] = str(ldr_truncated)
    if shadow is not None:
        for key, field in (("exports", "shadow_named_exports"), ("scanned", "shadow_names_inspected")):
            value = _required(shadow, key, source)
            row[field] = str(_uint(value, source))
    if module_outcomes:
        for status, field in MODULE_STATUSES.items():
            row[field] = str(sum(value == status for value in module_outcomes.values()))
    row["shadow_outcome"] = module_outcomes.get("shadow", UNKNOWN)
    if prefinal is not None:
        expected = {
            "outcome": "prefinal_outcome",
            "module_errors": "prefinal_module_errors",
            "module_skips": "prefinal_module_skips",
            "fault": "prefinal_fault",
            "log_error": "prefinal_log_error",
            "stdout_error": "prefinal_stdout_error",
        }
        for key, field in expected.items():
            value = _required(prefinal, key, source)
            if key == "outcome" and value not in PREFINAL_OUTCOMES:
                raise LogError(f"{source}: unsupported prefinal outcome")
            if key != "outcome":
                _uint(value, source)
            row[field] = value
    # Collector and final-closure fields are absent from these raw logs; never infer them.
    return row


def summarize_directory(log_dir: Path) -> list[dict[str, str]]:
    paths = sorted(log_dir.glob("*.log"), key=lambda item: (item.name.casefold(), item.name))
    if not paths:
        raise LogError("no .log files found")
    return [summarize_log(path, _sample_id(index)) for index, path in enumerate(paths, 1)]


def render_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_dir", type=Path, help="directory containing raw survey .log files")
    args = parser.parse_args(argv)
    if not args.log_dir.is_dir():
        parser.error("log_dir must be an existing directory")
    try:
        rows = summarize_directory(args.log_dir)
    except (OSError, LogError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render_csv(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
