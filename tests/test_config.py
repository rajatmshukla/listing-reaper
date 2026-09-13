"""Tests for configuration file loading, schema validation, and parameter checks."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reaper.config import (
    Config,
    ConfigError,
    load_config,
    render_regex_error,
    validate_rule_config,
)


class TestConfigValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _write_config(self, data: dict) -> Path:
        file_path = self.tmp_path / "test_config.json"
        file_path.write_text(json.dumps(data), encoding="utf-8")
        return file_path

    def test_valid_config_loading(self) -> None:
        valid_data = {
            "version": 1,
            "target_count": 5,
            "max_rounds": 2,
            "round_page_size": 10,
            "pacing_seconds": 0.0,
            "dedupe_by": ["title", "company"],
            "rules": [
                {
                    "rule_id": "require_description",
                    "min_chars": 50,
                },
                {
                    "rule_id": "exclude_seniority",
                    "terms": ["lead", "principal"],
                },
            ],
        }
        path = self._write_config(valid_data)
        config = load_config(path)
        self.assertEqual(config.version, 1)
        self.assertEqual(config.target_count, 5)
        self.assertEqual(config.max_rounds, 2)
        self.assertEqual(len(config.rules), 2)
        self.assertEqual(config.rules[0].params["min_chars"], 50)

    def test_unknown_top_level_key(self) -> None:
        data = {
            "version": 1,
            "invalid_key_xyz": "foo",
            "rules": [],
        }
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_config(path)
        self.assertIn("invalid_key_xyz", str(ctx.exception))
        self.assertIn("Unknown top-level configuration key", str(ctx.exception))

    def test_unknown_rule_id(self) -> None:
        data = {
            "version": 1,
            "rules": [
                {"rule_id": "non_existent_rule_xyz"},
            ],
        }
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_config(path)
        self.assertIn("non_existent_rule_xyz", str(ctx.exception))
        self.assertIn("require_description", str(ctx.exception))

    def test_missing_required_param(self) -> None:
        # 'exclude_title_patterns' requires 'patterns'
        data = {
            "version": 1,
            "rules": [
                {"rule_id": "exclude_title_patterns"},
            ],
        }
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_config(path)
        self.assertIn("exclude_title_patterns", str(ctx.exception))
        self.assertIn("patterns", str(ctx.exception))

    def test_unknown_param_on_known_rule_typo(self) -> None:
        # Typo: min_char instead of min_chars
        data = {
            "version": 1,
            "rules": [
                {
                    "rule_id": "require_description",
                    "min_char": 50,
                },
            ],
        }
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_config(path)
        self.assertIn("Unknown parameter 'min_char'", str(ctx.exception))
        self.assertIn("require_description", str(ctx.exception))

    def test_uncompilable_regex(self) -> None:
        data = {
            "version": 1,
            "rules": [
                {
                    "rule_id": "exclude_title_patterns",
                    "patterns": ["([unclosed_bracket"],
                },
            ],
        }
        path = self._write_config(data)
        with self.assertRaises(ConfigError) as ctx:
            load_config(path)
        err_msg = str(ctx.exception)
        self.assertIn("uncompilable regular expression", err_msg)
        self.assertIn("([unclosed_bracket", err_msg)
        self.assertIn("exclude_title_patterns", err_msg)

    def test_config_describe(self) -> None:
        config = Config(
            version=1,
            target_count=3,
            max_rounds=2,
            round_page_size=5,
            rules=[
                validate_rule_config(
                    {"rule_id": "require_description", "min_chars": 40}
                )
            ],
        )
        desc = config.describe()
        self.assertIn("Configuration (version 1)", desc)
        self.assertIn("Target count:     3", desc)
        self.assertIn("require_description", desc)
        self.assertIn("min_chars: 40", desc)


if __name__ == "__main__":
    unittest.main()
