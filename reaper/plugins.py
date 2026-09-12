from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

from reaper.rules import REGISTRY


class PluginError(Exception):
    """Raised when a plugin module cannot be imported or raises during import."""

    def __init__(self, entry: str, message: str) -> None:
        super().__init__(f"Plugin '{entry}' failed to load: {message}")
        self.entry = entry
        self.message = message


def resolve_plugin_entries(cli_plugins: str | None = None) -> list[str]:
    """Resolve plugin entries from CLI option and REAPER_PLUGINS environment variable.

    Both sources accept a comma-separated list of dotted module paths or .py file paths.
    Entries are returned in order, preserving uniqueness.
    """
    entries: list[str] = []

    def _append_from_str(val: str) -> None:
        for part in val.split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in entries:
                entries.append(cleaned)

    env_val = os.environ.get("REAPER_PLUGINS", "").strip()
    if env_val:
        _append_from_str(env_val)

    if cli_plugins:
        _append_from_str(cli_plugins)

    return entries


def load_plugins(entries: list[str]) -> list[str]:
    """Load plugin modules from a list of module paths or file paths.

    Each entry must be either:
      - A path to a .py file (e.g. 'examples/custom_rule_example.py')
      - A dotted module path (e.g. 'my_rules.custom')

    Returns:
        list[str]: The names of the successfully loaded modules.

    Raises:
        PluginError: If any plugin fails to load or raises an exception during execution.
        In case of an error, any changes made to REGISTRY and sys.modules during the call
        are rolled back so that no partially loaded plugin state remains.
    """
    if not entries:
        return []

    # Flatten any comma-separated entries
    flat_entries: list[str] = []
    for entry in entries:
        for part in str(entry).split(","):
            cleaned = part.strip()
            if cleaned and cleaned not in flat_entries:
                flat_entries.append(cleaned)

    if not flat_entries:
        return []

    registry_snapshot = dict(REGISTRY)
    modules_snapshot = dict(sys.modules)
    loaded_names: list[str] = []

    for entry in flat_entries:
        try:
            if entry.endswith(".py") or entry.endswith(".pyw") or "/" in entry or "\\" in entry:
                file_path = Path(entry).resolve()
                if not file_path.is_file():
                    raise FileNotFoundError(f"Plugin file not found: '{entry}'")

                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load module specification from '{entry}'")

                mod = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = mod
                spec.loader.exec_module(mod)
                loaded_names.append(module_name)
            else:
                mod = importlib.import_module(entry)
                loaded_names.append(mod.__name__)
        except Exception as err:
            # Rollback REGISTRY and sys.modules to prevent partial plugin state
            REGISTRY.clear()
            REGISTRY.update(registry_snapshot)
            for mod_name in list(sys.modules):
                if mod_name not in modules_snapshot:
                    sys.modules.pop(mod_name, None)
            raise PluginError(entry, str(err)) from err

    return loaded_names
