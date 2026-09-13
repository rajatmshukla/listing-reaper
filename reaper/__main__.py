"""Command-line interface and entry point for listing-reaper.

Owns CLI argument parsing, subcommand routing, terminal output dispatch, and process exit codes.
Does not own filtering algorithms, simulation logic, scoring math, or persistence rules.
Called from the shell via python -m reaper or by invoking main(). Public entry points
exported: main and build_parser.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

import datetime
from reaper.config import ConfigError, load_config
from reaper.engine import Reaper
from reaper.plugins import PluginError, load_plugins, resolve_plugin_entries
from reaper.report import (
    render_explain,
    render_json,
    render_reap_summary,
    render_rules_catalog,
    render_simulation,
)
from reaper.simulator import simulate
from reaper.sources import FixtureSource
from reaper.tracker import StateError, Tracker
from reaper.workflow import run_workflow


def _exit_with_error(msg: str, code: int) -> NoReturn:
    """Print error message to stderr and terminate process with exit code."""
    sys.stderr.write(f"Error: {msg}\n")
    sys.exit(code)


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the end-to-end job search workflow command."""
    config_file = args.config
    if not config_file:
        if Path("examples/workflow.example.json").exists():
            config_file = "examples/workflow.example.json"
        elif Path("config.json").exists():
            config_file = "config.json"
        else:
            _exit_with_error("No configuration file specified (pass --config <path>).", 2)

    try:
        config = load_config(config_file)
    except (ConfigError, FileNotFoundError) as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Config error: {err}", 2)

    formats = [args.format] if args.format else None

    try:
        result = run_workflow(
            fixtures=args.fixtures,
            config=config,
            state_path=args.state,
            out_dir=args.out,
            formats=formats,
            target_count=args.target,
            limit=args.limit,
            since_days=args.since_days,
            no_track=args.no_track,
            dry_run=args.dry_run,
            explain_scores=args.explain_scores,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, ValueError) as err:
        _exit_with_error(str(err), 4)
    except StateError as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Workflow error: {err}", 2)

    print(result.summary)
    return 0 if result.shortlist else 3


def cmd_track(args: argparse.Namespace) -> int:
    """Update the tracking status of an existing listing in the state file."""
    state_path = Path(args.state)
    if not state_path.exists():
        _exit_with_error(f"State file not found: '{args.state}'", 2)

    try:
        tracker = Tracker.load(state_path)
    except StateError as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Failed to read state file '{args.state}': {err}", 2)

    today = datetime.date.today().isoformat()
    try:
        key, old_status, new_status = tracker.update_by_id(
            listing_id=args.id,
            status=args.status,
            date=today,
        )
    except KeyError:
        _exit_with_error(f"Listing ID '{args.id}' not found in state file '{args.state}'.", 2)
    except ValueError as err:
        _exit_with_error(str(err), 2)

    try:
        tracker.save(state_path)
    except Exception as err:
        _exit_with_error(f"Failed to save state file '{args.state}': {err}", 2)

    print(f"Updated listing '{args.id}': status changed from '{old_status}' to '{new_status}' (key: {key}).")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a JSON configuration file and report active rules and field mappings."""
    try:
        config = load_config(args.config)
        print(f"Valid configuration: '{args.config}'")
        if config.field_map:
            print(f"Field map ({len(config.field_map)} mapping(s)):")
            for src, dst in sorted(config.field_map.items()):
                print(f"  {src} -> {dst}")
        print(f"Active rules ({len(config.rules)} configured):")
        for idx, rule in enumerate(config.rules, start=1):
            print(f"  {idx}. {rule.rule_id}")
        return 0
    except ConfigError as err:
        _exit_with_error(f"Configuration invalid: {err}", 2)
    except FileNotFoundError as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Unexpected configuration error: {err}", 2)


def cmd_config_describe(args: argparse.Namespace) -> int:
    """Print a human-readable description of configuration settings and field mappings."""
    config_file = args.config
    if not config_file:
        if Path("examples/workflow.example.json").exists():
            config_file = "examples/workflow.example.json"
        elif Path("config.json").exists():
            config_file = "config.json"
        else:
            _exit_with_error("No configuration file specified (pass --config <path>).", 2)

    try:
        config = load_config(config_file)
        print(config.describe())
        return 0
    except (ConfigError, FileNotFoundError) as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Config error: {err}", 2)


def cmd_rules(_args: argparse.Namespace) -> int:
    """Print the catalog of registered filter rules and their parameters."""
    print(render_rules_catalog())
    return 0


def cmd_reap(args: argparse.Namespace) -> int:
    """Filter fixture listings through configured rules and output reap summaries."""
    # 1. Load config
    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Config error: {err}", 2)

    # 2. Load fixture
    try:
        source = FixtureSource(args.fixtures, field_map=config.field_map)
    except (FileNotFoundError, ValueError) as err:
        _exit_with_error(str(err), 4)
    except Exception as err:
        _exit_with_error(f"Fixture read error: {err}", 4)

    if not source.listings:
        msg = f"Fixture '{args.fixtures}' contains no valid records."
        if source.errors:
            msg += f" Encountered {len(source.errors)} error(s), e.g. {source.errors[0][2]}"
        _exit_with_error(msg, 4)

    if source.errors:
        sys.stderr.write(
            f"Fixture notice: {len(source.errors)} malformed record(s) encountered in '{args.fixtures}':\n"
        )
        for err_file, line_no, msg in source.errors:
            sys.stderr.write(f"  - Line {line_no}: {msg}\n")

    # 3. Reap
    reaper = Reaper(config)
    report = reaper.reap_many(source.listings)

    # 4. Output handling
    if args.json == "-":
        print(render_json(report))
    else:
        if args.json:
            out_path = Path(args.json)
            out_path.write_text(render_json(report), encoding="utf-8")
        print(render_reap_summary(report))

    # Exit code: 3 if nothing kept, else 0
    return 0 if report.kept else 3


def cmd_explain(args: argparse.Namespace) -> int:
    """Evaluate and print a step-by-step rule trace for a specific listing ID."""
    # 1. Load config
    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Config error: {err}", 2)

    # 2. Load fixture
    try:
        source = FixtureSource(args.fixtures, field_map=config.field_map)
    except (FileNotFoundError, ValueError) as err:
        _exit_with_error(str(err), 4)
    except Exception as err:
        _exit_with_error(f"Fixture read error: {err}", 4)

    if not source.listings:
        _exit_with_error(f"Fixture '{args.fixtures}' contains no valid records.", 4)

    # 3. Find listing
    target_listing = None
    for listing in source.listings:
        if listing.id == args.id:
            target_listing = listing
            break

    if target_listing is None:
        _exit_with_error(f"Listing ID '{args.id}' not found in fixture '{args.fixtures}'.", 2)

    reaper = Reaper(config)
    verdict, traces = reaper.reap(target_listing)
    print(render_explain(target_listing, traces, verdict))
    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Simulate an offline hunt across paginated fixture listings."""
    # 1. Load config
    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as err:
        _exit_with_error(str(err), 2)
    except Exception as err:
        _exit_with_error(f"Config error: {err}", 2)

    # CLI parameter overrides
    if args.target is not None:
        config.target_count = args.target
    if args.rounds is not None:
        config.max_rounds = args.rounds
    if args.page_size is not None:
        config.round_page_size = args.page_size
    if args.pacing is not None:
        config.pacing_seconds = args.pacing

    # 2. Load fixture
    try:
        source = FixtureSource(args.fixtures, seed=args.seed, field_map=config.field_map)
    except (FileNotFoundError, ValueError) as err:
        _exit_with_error(str(err), 4)
    except Exception as err:
        _exit_with_error(f"Fixture read error: {err}", 4)

    if not source.listings:
        _exit_with_error(f"Fixture '{args.fixtures}' contains no valid records.", 4)

    # 3. Handle seen set
    seen_keys: set[str] = set()
    if args.seen:
        seen_path = Path(args.seen)
        if seen_path.exists():
            content = seen_path.read_text(encoding="utf-8")
            seen_keys = {line.strip() for line in content.splitlines() if line.strip()}

    # 4. Run simulation
    result = simulate(config, source, seen_keys=seen_keys)

    # 5. Persist seen file if requested
    if args.seen:
        seen_path = Path(args.seen)
        seen_path.write_text("\n".join(sorted(result.seen_keys)) + "\n", encoding="utf-8")

    # 6. Render output
    if args.json == "-":
        print(render_json(result))
    else:
        if args.json:
            Path(args.json).write_text(render_json(result), encoding="utf-8")
        print(render_simulation(result))

    return 0 if result.kept else 3


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="reaper",
        description="Offline job listing filter engine with explainable kill log and simulation harness.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run", help="Run the end-to-end job search workflow.")
    p_run.add_argument("--fixtures", nargs="+", action="extend", required=True, help="Path(s) to fixture files (.jsonl or .csv).")
    p_run.add_argument("--config", default=None, help="Path to JSON configuration file (default: examples/workflow.example.json).")
    p_run.add_argument("--out-dir", "--out", dest="out", default=None, help="Output directory for reports (default: out).")
    p_run.add_argument("--format", default=None, choices=["md", "markdown", "csv", "json"], help="Output format.")
    p_run.add_argument("--target", type=int, default=None, help="Target count of shortlisted listings.")
    p_run.add_argument("--limit", type=int, default=None, help="Cap shortlist size independently of target count.")
    p_run.add_argument("--since-days", type=int, default=None, help="Filter listings posted within N days.")
    p_run.add_argument("--seen-file", "--state", dest="state", default="state/seen.json", help="Path to state tracking file (default: state/seen.json).")
    p_run.add_argument("--no-track", action="store_true", help="Do not record shortlisted listings in state file.")
    p_run.add_argument("--dry-run", action="store_true", help="Do not write report files or update state file.")
    p_run.add_argument("--explain-scores", action="store_true", help="Print component breakdown for each kept listing.")
    p_run.add_argument("--overwrite", action="store_true", help="Overwrite report files even if shortlist is empty.")
    p_run.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # track
    p_track = subparsers.add_parser("track", help="Update the status of an already-shortlisted listing.")
    p_track.add_argument("--seen-file", "--state", dest="state", required=True, help="Path to state tracking JSON file.")
    p_track.add_argument("--id", required=True, help="Listing ID to update.")
    p_track.add_argument("--status", required=True, choices=["shortlisted", "applied", "skipped", "rejected"], help="New status.")
    p_track.add_argument("--fixtures", default=None, help="Optional fixture file.")
    p_track.add_argument("--config", default=None, help="Optional configuration file.")
    p_track.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # reap
    p_reap = subparsers.add_parser("reap", help="Reap listings from a fixture file using configured rules.")
    p_reap.add_argument("--fixtures", required=True, help="Path to fixtures file (.jsonl or .csv).")
    p_reap.add_argument("--config", required=True, help="Path to JSON configuration file.")
    p_reap.add_argument("--json", dest="json", default=None, help="Output path for JSON report (use '-' for stdout).")
    p_reap.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # explain
    p_explain = subparsers.add_parser("explain", help="Explain the rule evaluation trace for a specific listing.")
    p_explain.add_argument("--fixtures", required=True, help="Path to fixtures file (.jsonl or .csv).")
    p_explain.add_argument("--config", required=True, help="Path to JSON configuration file.")
    p_explain.add_argument("--id", required=True, help="Listing ID to explain.")
    p_explain.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # simulate
    p_sim = subparsers.add_parser("simulate", help="Simulate an offline hunt across fixture pages.")
    p_sim.add_argument("--fixtures", required=True, help="Path to fixtures file (.jsonl or .csv).")
    p_sim.add_argument("--config", required=True, help="Path to JSON configuration file.")
    p_sim.add_argument("--target", type=int, default=None, help="Target count of kept listings.")
    p_sim.add_argument("--rounds", type=int, default=None, help="Maximum number of rounds to simulate.")
    p_sim.add_argument("--page-size", type=int, default=None, help="Number of listings per round page.")
    p_sim.add_argument("--pacing", type=float, default=None, help="Pacing delay in seconds between rounds.")
    p_sim.add_argument("--seen", default=None, help="Path to file recording seen listing keys.")
    p_sim.add_argument("--json", dest="json", default=None, help="Output path for JSON result (use '-' for stdout).")
    p_sim.add_argument("--seed", type=int, default=None, help="Random seed for reproducible shuffling.")
    p_sim.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # rules
    p_rules = subparsers.add_parser("rules", help="Display all registered filter rules, their summaries, and parameters.")
    p_rules.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate a JSON configuration file schema and parameters.")
    p_val.add_argument("--config", required=True, help="Path to JSON configuration file.")
    p_val.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    # config-describe
    p_desc = subparsers.add_parser("config-describe", help="Display configuration description and field mapping.")
    p_desc.add_argument("--config", default=None, help="Path to JSON configuration file.")
    p_desc.add_argument("--plugins", default=None, help="Comma-separated list of plugin modules or .py files to load.")

    return parser


def main() -> None:
    """Parse command-line arguments, load plugins, and run the requested subcommand."""
    parser = build_parser()
    args = parser.parse_args()

    plugin_entries = resolve_plugin_entries(getattr(args, "plugins", None))
    if plugin_entries:
        try:
            load_plugins(plugin_entries)
        except PluginError as err:
            _exit_with_error(f"Plugin '{err.entry}' failed to load: {err.message}", 2)

    handlers = {
        "run": cmd_run,
        "track": cmd_track,
        "reap": cmd_reap,
        "explain": cmd_explain,
        "simulate": cmd_simulate,
        "rules": cmd_rules,
        "validate": cmd_validate,
        "config-describe": cmd_config_describe,
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(2)

    sys.exit(handler(args))


if __name__ == "__main__":
    main()
