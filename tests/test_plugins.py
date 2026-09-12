from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from reaper.plugins import PluginError, load_plugins, resolve_plugin_entries
from reaper.rules import REGISTRY


class TestPlugins(unittest.TestCase):
    def setUp(self) -> None:
        self._initial_keys = set(REGISTRY.keys())

    def tearDown(self) -> None:
        added = set(REGISTRY.keys()) - self._initial_keys
        for k in added:
            REGISTRY.pop(k, None)

    def test_load_plugin_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            plugin_file = Path(tmp_dir) / "custom_test_plugin.py"
            plugin_content = (
                "from reaper.rules import RuleSpec, register_rule\n"
                "from reaper.model import Verdict\n"
                "def eval_fn(l, p, c=None):\n"
                "    return Verdict('plug_test', 'keep', 'ok')\n"
                "register_rule(RuleSpec('plug_test', 'test summary', {}, eval_fn))\n"
            )
            plugin_file.write_text(plugin_content, encoding="utf-8")

            loaded = load_plugins([str(plugin_file)])
            self.assertEqual(loaded, ["custom_test_plugin"])
            self.assertIn("plug_test", REGISTRY)

    def test_load_plugin_nonexistent_fails_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            good_file = Path(tmp_dir) / "good_plugin.py"
            good_file.write_text(
                "from reaper.rules import RuleSpec, register_rule\n"
                "from reaper.model import Verdict\n"
                "register_rule(RuleSpec('good_rule', 'good', {}, lambda l, p, c: Verdict('good_rule', 'keep', 'ok')))\n",
                encoding="utf-8",
            )
            with self.assertRaises(PluginError) as ctx:
                load_plugins([str(good_file), "non_existent_module_xyz_123"])

            self.assertIn("non_existent_module_xyz_123", str(ctx.exception))
            # Verify rollback: good_rule was not retained in REGISTRY
            self.assertNotIn("good_rule", REGISTRY)

    def test_resolve_plugin_entries(self) -> None:
        old_env = os.environ.get("REAPER_PLUGINS")
        try:
            os.environ["REAPER_PLUGINS"] = "mod_a, mod_b"
            entries = resolve_plugin_entries("mod_c, mod_a")
            self.assertEqual(entries, ["mod_a", "mod_b", "mod_c"])
        finally:
            if old_env is None:
                os.environ.pop("REAPER_PLUGINS", None)
            else:
                os.environ["REAPER_PLUGINS"] = old_env


if __name__ == "__main__":
    unittest.main()
