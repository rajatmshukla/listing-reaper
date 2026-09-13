"""Package root and public API surface for listing-reaper.

Owns top-level symbol re-exports for configuration, data models, rule registration,
engine execution, and simulation. Does not implement filtering logic or CLI parsing.
Callers import core interfaces directly from the package namespace. Public exports:
Config, ConfigError, FixtureSource, Listing, ListingError, ParamSpec, PluginError,
ReapReport, Reaper, RuleSpec, RuleTrace, SimulationResult, Source, Verdict, load_config,
load_plugins, register_rule, simulate, and REGISTRY.
"""
from __future__ import annotations

from reaper.config import Config, ConfigError, load_config
from reaper.engine import Reaper
from reaper.model import Listing, ListingError, ReapReport, RuleTrace, Verdict
from reaper.plugins import PluginError, load_plugins
from reaper.rules import REGISTRY, ParamSpec, RuleSpec, register_rule
from reaper.simulator import SimulationResult, simulate
from reaper.sources import FixtureSource, Source

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Config",
    "ConfigError",
    "FixtureSource",
    "Listing",
    "ListingError",
    "ParamSpec",
    "PluginError",
    "ReapReport",
    "Reaper",
    "RuleSpec",
    "RuleTrace",
    "SimulationResult",
    "Source",
    "Verdict",
    "load_config",
    "load_plugins",
    "register_rule",
    "simulate",
    "REGISTRY",
]
