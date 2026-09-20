import tempfile
import unittest
from pathlib import Path

from check_mcp_conformance import scan_file


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


if __name__ == "__main__":
    unittest.main()
