import csv
import hashlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.summarize_windows_survey import (
    CSV_FIELDS,
    LogError,
    render_csv,
    summarize_directory,
    summarize_log,
)


IDENTITY = (
    "identity v=5 schema=5 major=10 minor=0 build=19045 ubr=6456 "
    "ubr_status=0 arch=x64 host=private-host.example host_status=ok "
    "collected_utc=2026-10-09T00:04:08.042Z pid=4060 seq=0"
)
MODULES = (
    "module capability outcome=ok",
    "module tls_sig outcome=ok",
    "module pp8 outcome=ok",
    "module horizon outcome=ok",
    "module shadow outcome=ok",
    "module ldr outcome=ok",
    "module gadgets outcome=ok",
    "module ssn outcome=ok",
)


def write_log(directory: Path, name: str, lines: list[str]) -> Path:
    path = directory / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class SurveySummaryTests(unittest.TestCase):
    def test_duplicate_builds_are_preserved_in_deterministic_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_log(directory, "z.log", [IDENTITY, *MODULES])
            write_log(directory, "a.log", [IDENTITY, *MODULES])

            rows = summarize_directory(directory)

        self.assertEqual([row["sample"] for row in rows], ["A", "B"])
        self.assertEqual([row["build"] for row in rows], ["19045", "19045"])
        self.assertEqual([row["raw_log_basename"] for row in rows], ["unknown", "unknown"])
        self.assertEqual([row["module_ok_count"] for row in rows], ["8", "8"])

    def test_identity_is_required_unique_and_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = write_log(directory, "missing.log", MODULES)
            with self.assertRaisesRegex(LogError, "missing identity"):
                summarize_log(path, "A")

            path = write_log(directory, "duplicate.log", [IDENTITY, IDENTITY])
            with self.assertRaisesRegex(LogError, "duplicate identity"):
                summarize_log(path, "A")

            path = write_log(directory, "bad.log", [IDENTITY.replace("v=5", "v=4")])
            with self.assertRaisesRegex(LogError, "unsupported identity"):
                summarize_log(path, "A")

            path = write_log(directory, "duplicate-key.log", [IDENTITY.replace("v=5", "v=5 v=5")])
            with self.assertRaisesRegex(LogError, "duplicate v field"):
                summarize_log(path, "A")

    def test_partial_module_records_remain_distinct_from_zero_or_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            partial = write_log(directory, "partial.log", [IDENTITY, "module capability outcome=ok"])
            row = summarize_log(partial, "A")

            no_modules = write_log(directory, "none.log", [IDENTITY])
            empty_row = summarize_log(no_modules, "B")

        self.assertEqual(row["module_seen_count"], "1")
        self.assertEqual(row["module_missing_count"], "7")
        self.assertEqual(row["module_ok_count"], "1")
        self.assertEqual(row["module_error_count"], "0")
        self.assertEqual(empty_row["module_seen_count"], "0")
        self.assertEqual(empty_row["module_missing_count"], "8")
        self.assertEqual(empty_row["module_ok_count"], "unknown")
        self.assertEqual(empty_row["module_error_count"], "unknown")

    def test_prefinal_is_not_treated_as_final_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_log(Path(temporary), "prefinal.log", [
                IDENTITY,
                "survey prefinal outcome=ok module_errors=0 module_skips=0 fault=0 log_error=0 stdout_error=0",
            ])
            row = summarize_log(path, "A")

        self.assertEqual(row["prefinal_outcome"], "ok")
        self.assertEqual(row["prefinal_module_errors"], "0")
        self.assertEqual(row["exit_code"], "unknown")
        self.assertEqual(row["final_stdout_result"], "unknown")
        self.assertEqual(row["collector_exe_sha256"], "unknown")
        self.assertEqual(row["ntdll_file_sha256"], "unknown")

    def test_csv_contains_only_whitelisted_diagnostics_and_hashes_exact_bytes(self):
        private_address = "0x7ffdfedcba987654"
        private_scan_value = "SIG_PRIVATE_0123456789ABCDEF"
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = write_log(directory, "ashura_survey_1_2_20261009T000408042Z_3_4_x64.log", [
                IDENTITY,
                f"ldr entry=0 base={private_address} full_len=99 base_len=5 sane=1 name_utf8=ok",
                "ldr end entries=1 outcome=ok",
                "ldr truncated=0",
                "shadow begin",
                "shadow open status=ok",
                "shadow map status=ok",
                "shadow text_readable=1",
                "shadow exports=2434 scanned=1109 RtlGetVersion=1 private=" + private_scan_value,
                "shadow end outcome=ok",
                *MODULES,
            ])
            raw = source.read_bytes()
            rows = summarize_directory(directory)
            output = render_csv(rows)
            parsed = next(csv.DictReader(io.StringIO(output)))

        self.assertEqual(tuple(parsed), CSV_FIELDS)
        self.assertEqual(parsed["raw_log_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(parsed["ldr_entries"], "1")
        self.assertEqual(parsed["ldr_all_sane"], "1")
        self.assertEqual(parsed["ldr_truncation_reported"], "0")
        self.assertEqual(parsed["ldr_outcome"], "ok")
        self.assertEqual(parsed["shadow_named_exports"], "2434")
        self.assertEqual(parsed["shadow_names_inspected"], "1109")
        self.assertEqual(parsed["shadow_outcome"], "ok")
        self.assertEqual(parsed["raw_log_basename"], source.name)
        self.assertNotIn("private-host", output)
        self.assertNotIn("host=", output)
        self.assertNotIn(private_address, output)
        self.assertNotIn(private_scan_value, output)

    def test_unsafe_log_basename_is_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            unsafe = write_log(directory, "private-host.log", [IDENTITY])
            row = summarize_log(unsafe, "A")
            safe = write_log(
                directory,
                "ashura_survey_12_34_20261009T000408042Z_5_6_x64.log",
                [IDENTITY],
            )
            safe_row = summarize_log(safe, "B")

        self.assertEqual(row["raw_log_basename"], "unknown")
        self.assertEqual(safe_row["raw_log_basename"], safe.name)

    def test_partial_ldr_entries_do_not_claim_all_sane(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            partial = write_log(directory, "partial.log", [
                IDENTITY,
                "ldr entry=0 base=0x1000 sane=1",
                "ldr end entries=2 outcome=ok",
            ])
            partial_row = summarize_log(partial, "A")
            complete = write_log(directory, "complete.log", [
                IDENTITY,
                "ldr entry=0 base=0x1000 sane=1",
                "ldr entry=1 base=0x2000 sane=1",
                "ldr end entries=2 outcome=ok",
            ])
            complete_row = summarize_log(complete, "B")

        self.assertEqual(partial_row["ldr_entries"], "2")
        self.assertEqual(partial_row["ldr_all_sane"], "unknown")
        self.assertEqual(complete_row["ldr_all_sane"], "1")

    def test_ldr_end_outcome_is_validated(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_log(Path(temporary), "bad-ldr-outcome.log", [
                IDENTITY,
                "ldr end entries=0 outcome=maybe",
            ])
            with self.assertRaisesRegex(LogError, "unsupported ldr outcome"):
                summarize_log(path, "A")

    def test_unknown_module_name_or_status_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = write_log(directory, "module.log", [IDENTITY, "module unknown outcome=ok"])
            with self.assertRaisesRegex(LogError, "unexpected module name"):
                summarize_log(path, "A")
            path = write_log(directory, "status.log", [IDENTITY, "module capability outcome=maybe"])
            with self.assertRaisesRegex(LogError, "unsupported module status"):
                summarize_log(path, "A")

    def test_duplicate_ldr_entry_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_log(Path(temporary), "duplicate-ldr.log", [
                IDENTITY,
                "ldr entry=0 base=0x1000 sane=1",
                "ldr entry=0 base=0x2000 sane=1",
            ])
            with self.assertRaisesRegex(LogError, "duplicate ldr entry index"):
                summarize_log(path, "A")

    def test_missing_shallow_diagnostics_are_unknown_and_no_logs_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path = write_log(directory, "bare.log", [IDENTITY])
            row = summarize_log(path, "A")
            self.assertEqual(row["ldr_entries"], "unknown")
            self.assertEqual(row["ldr_all_sane"], "unknown")
            self.assertEqual(row["ldr_truncation_reported"], "unknown")
            self.assertEqual(row["shadow_names_inspected"], "unknown")
            directory.joinpath("bare.log").unlink()
            with self.assertRaisesRegex(LogError, "no .log files"):
                summarize_directory(directory)


if __name__ == "__main__":
    unittest.main()
