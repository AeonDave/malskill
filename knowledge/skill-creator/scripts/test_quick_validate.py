import tempfile
import unittest
from pathlib import Path

from quick_validate import validate_skill


VALID = """---
name: demo-skill
description: A useful demo skill.
compatibility: Python 3
metadata:
  author: test
---
# Demo
"""


class QuickValidateTypesTests(unittest.TestCase):
    def validate(self, frontmatter):
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(frontmatter, encoding="utf-8")
            return validate_skill(skill)

    def test_valid_frontmatter(self):
        ok, _ = self.validate(VALID)
        self.assertTrue(ok)

    def test_required_and_compatibility_values_must_be_strings(self):
        for field, value in (("name", "null"), ("description", "false"),
                             ("compatibility", "[]")):
            text = VALID.replace(f"{field}: " + ("demo-skill" if field == "name" else
                                                   "A useful demo skill." if field == "description" else ""),
                                 f"{field}: {value}")
            ok, message = self.validate(text)
            self.assertFalse(ok, (field, message))

    def test_metadata_must_be_string_map(self):
        for value in ("null", "[]", "{author: [test]}", "{author: null}"):
            ok, message = self.validate(VALID.replace("author: test", f"author: {value}"))
            self.assertFalse(ok, message)

    def test_compatibility_must_not_be_empty(self):
        ok, message = self.validate(VALID.replace("compatibility: Python 3", "compatibility: '  '") )
        self.assertFalse(ok, message)

    def test_non_string_mapping_key_is_reported(self):
        ok, message = self.validate(VALID.replace("metadata:\n  author: test", "123: value\nmetadata:\n  author: test"))
        self.assertFalse(ok, message)

    def test_closing_delimiter_must_be_a_line(self):
        ok, message = self.validate(VALID.replace("---\n# Demo", "---extra\n# Demo"))
        self.assertFalse(ok, message)


if __name__ == "__main__":
    unittest.main()
