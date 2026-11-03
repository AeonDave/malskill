import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from check_mcp_conformance import main, scan_file


class CacheMetadataTests(unittest.TestCase):
    def findings(self, text):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "server.py"
            path.write_text(text, encoding="utf-8")
            result = []
            scan_file(str(path), result, {"is_server": False, "has_discover": False})
            return [item for item in result if item.rule == "cache-metadata"]

    def test_missing_each_cache_field_is_reported(self):
        self.assertIn("ttlMs", self.findings("tools/list\n")[0].message)
        self.assertIn("cacheScope", self.findings("tools/list\nttlMs\n")[0].message)

    def test_both_cache_fields_satisfy_heuristic(self):
        self.assertEqual([], self.findings("tools/list\nttlMs\ncacheScope\n"))

    def test_discovery_requires_both_cache_fields(self):
        for fields, missing in (("", "ttlMs"), ("ttlMs", "cacheScope")):
            with self.subTest(fields=fields):
                found = self.findings("server/discover\n" + fields)
                self.assertEqual(1, len(found))
                self.assertIn(missing, found[0].message)


class ScannerCliTests(unittest.TestCase):
    def test_missing_path_is_usage_error(self):
        with tempfile.TemporaryDirectory() as temp:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                status = main([str(Path(temp) / "missing")])
            self.assertEqual(2, status)
            self.assertIn("path does not exist", err.getvalue())

    def test_clean_raw_handler_and_strict_missing_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "server.py"
            path.write_text("server/discover\ntools/call\nresultType\nttlMs\ncacheScope\n")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(0, main([str(path), "--format", "json", "--strict"]))
            self.assertEqual([], json.loads(out.getvalue()))
            path.write_text("server/discover\n")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(1, main([str(path), "--format", "json", "--strict"]))
            self.assertIn("cache-metadata", [f["rule"] for f in json.loads(out.getvalue())])

    def test_unreadable_input_is_reported_as_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "server.py"
            path.write_text("server/discover\n")
            with patch("builtins.open", side_effect=PermissionError("denied")):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    status = main([str(path), "--format", "json"])
            self.assertEqual(1, status)
            self.assertEqual("read-error", json.loads(out.getvalue())[0]["rule"])


if __name__ == "__main__":
    unittest.main()
