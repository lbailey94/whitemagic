"""AgentDojo benchmark driver with WhiteMagic Dharma defense.

Runs AgentDojo scenarios through WhiteMagic's policy gate and reports
aggregate utility / security metrics. Supports subset evaluation for
rapid iteration.

Usage:
    # List available tasks and models (no API keys needed)
    python -m whitemagic.benchmarks.agentdojo_driver --list

    # Run first 5 tasks with WhiteMagic defense
    python -m whitemagic.benchmarks.agentdojo_driver \
        --suite v1 --domain workspace \
        --model GPT_4O_MINI_2024_07_18 \
        --defense whitemagic_dharma \
        --tasks user_task_0 user_task_1 user_task_2 user_task_3 user_task_4

    # Run all tasks with both defenses for comparison
    python -m whitemagic.benchmarks.agentdojo_driver \
        --suite v1 --domain workspace \
        --model GPT_4O_MINI_2024_07_18 \
        --defense whitemagic_dharma none \
        --all-tasks

    # Dry-run: show what would be executed without calling APIs
    python -m whitemagic.benchmarks.agentdojo_driver \
        --suite v1 --domain workspace --all-tasks --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Any

from agentdojo.agent_pipeline import agent_pipeline
from agentdojo.models import ModelsEnum
from agentdojo.scripts.benchmark import benchmark_suite
from agentdojo.task_suite import get_suite
from dotenv import load_dotenv

# Register WhiteMagic defense as a side-effect before importing AgentDojo CLI
import whitemagic.benchmarks.agentdojo_defense as _  # noqa: F401

logger = logging.getLogger(__name__)


def _ensure_defense_registered() -> None:
    """Make sure WhiteMagic defense is in AgentDojo's registry."""
    if "whitemagic_dharma" not in agent_pipeline.DEFENSES:
        agent_pipeline.DEFENSES.append("whitemagic_dharma")


def list_suites_and_models() -> None:
    """Print available suites, domains, tasks, and models."""
    print("=" * 60)
    print("AgentDojo + WhiteMagic — Available Configuration")
    print("=" * 60)

    # Models
    print("\nModels:")
    for m in ModelsEnum:
        print(f"  {m.name:40s} -> {m.value}")

    # Suites
    print("\nSuites / Domains / Tasks:")
    for version in ("v1", "v2"):
        for domain in ("workspace", "banking", "travel", "shopping"):
            try:
                suite = get_suite(version, domain)
                user_tasks = list(suite.user_tasks.keys())
                injection_tasks = list(suite.injection_tasks.keys())
                print(
                    f"  {version:4s} / {domain:10s} — "
                    f"{len(user_tasks)} user tasks, "
                    f"{len(injection_tasks)} injection tasks"
                )
                print(
                    f"         User tasks:     "
                    f"{', '.join(user_tasks[:5])}"
                    f"{'...' if len(user_tasks) > 5 else ''}"
                )
                print(
                    f"         Injection tasks: "
                    f"{', '.join(injection_tasks[:5])}"
                    f"{'...' if len(injection_tasks) > 5 else ''}"
                )
            except Exception as exc:
                print(f"  {version:4s} / {domain:10s} — unavailable ({exc})")

    print("\nDefenses:")
    for d in agent_pipeline.DEFENSES:
        marker = "  <- WhiteMagic" if d == "whitemagic_dharma" else ""
        print(f"  {d}{marker}")

    print("\n" + "=" * 60)


def run_single_configuration(
    suite_version: str,
    domain: str,
    model: ModelsEnum,
    defense: str | None,
    tasks: tuple[str, ...] | None,
    logdir: Path,
    force_rerun: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run one benchmark configuration and return metrics."""
    _ensure_defense_registered()
    suite = get_suite(suite_version, domain)

    defense_label = defense or "none"
    config_label = (
        f"{suite_version}/{domain} | "
        f"{model.name} | "
        f"defense={defense_label}"
    )
    if dry_run:
        print(f"[DRY RUN] Would execute: {config_label}")
        task_list = list(tasks) if tasks else list(suite.user_tasks.keys())
        return {
            "config": config_label,
            "tasks": task_list,
            "dry_run": True,
            "utility_rate": None,
            "security_rate": None,
        }

    print(f"\nRunning: {config_label}")
    print(f"Tasks: {tasks or 'ALL'}")
    print(f"Log dir: {logdir}")

    results = benchmark_suite(
        suite=suite,
        model=model,
        logdir=logdir,
        force_rerun=force_rerun,
        benchmark_version=suite_version,
        user_tasks=tasks,
        defense=defense,
    )

    # Aggregate
    utility = results.get("utility_results", {})
    security = results.get("security_results", {})

    utility_pass = sum(1 for v in utility.values() if v)
    utility_total = len(utility)
    security_pass = sum(1 for v in security.values() if v)
    security_total = len(security)

    utility_rate = utility_pass / utility_total if utility_total else 0.0
    security_rate = security_pass / security_total if security_total else 0.0

    summary = {
        "config": config_label,
        "utility_pass": utility_pass,
        "utility_total": utility_total,
        "utility_rate": utility_rate,
        "security_pass": security_pass,
        "security_total": security_total,
        "security_rate": security_rate,
        "logdir": str(logdir),
    }

    print(f"  Utility:   {utility_pass}/{utility_total} ({utility_rate:.1%})")
    print(f"  Security:  {security_pass}/{security_total} ({security_rate:.1%})")

    return summary


def run_comparison(
    suite_version: str,
    domain: str,
    model: ModelsEnum,
    defenses: list[str],
    tasks: tuple[str, ...] | None,
    logdir: Path,
    force_rerun: bool = True,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Run the same tasks against multiple defenses and return summaries."""
    summaries: list[dict[str, Any]] = []
    for defense in defenses:
        defense_label = defense or "none"
        log_name = f"{suite_version}_{domain}_{model.name}_{defense_label}"
        config_logdir = logdir / log_name
        config_logdir.mkdir(parents=True, exist_ok=True)
        summary = run_single_configuration(
            suite_version=suite_version,
            domain=domain,
            model=model,
            defense=defense,
            tasks=tasks,
            logdir=config_logdir,
            force_rerun=force_rerun,
            dry_run=dry_run,
        )
        summaries.append(summary)
    return summaries


def print_comparison_table(summaries: list[dict[str, Any]]) -> None:
    """Print a formatted comparison of defense results."""
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Config':50s} {'Utility':>8s} {'Security':>8s}")
    print("-" * 70)
    for s in summaries:
        if s.get("dry_run"):
            print(f"{s['config']:50s} {'(dry)':>8s} {'(dry)':>8s}")
            continue
        util = f"{s['utility_pass']}/{s['utility_total']} ({s['utility_rate']:.0%})"
        sec = f"{s['security_pass']}/{s['security_total']} ({s['security_rate']:.0%})"
        print(f"{s['config']:50s} {util:>8s} {sec:>8s}")
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AgentDojo benchmark driver with WhiteMagic Dharma defense",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list
  %(prog)s --suite v1 --domain workspace --model GPT_4O_MINI_2024_07_18 \
      --defense whitemagic_dharma --all-tasks
  %(prog)s --suite v1 --domain workspace --model GPT_4O_MINI_2024_07_18 \
      --defense whitemagic_dharma none --all-tasks
  %(prog)s --suite v1 --domain workspace --all-tasks --dry-run
        """,
    )
    parser.add_argument(
        "--suite", default="v1", help="Benchmark suite version (default: v1)"
    )
    parser.add_argument(
        "--domain", default="workspace", help="Task domain (default: workspace)"
    )
    parser.add_argument(
        "--model",
        default="GPT_4O_MINI_2024_07_18",
        help=(
            "Model enum name "
            "(default: GPT_4O_MINI_2024_07_18)"
        ),
    )
    parser.add_argument(
        "--defense",
        nargs="+",
        default=["whitemagic_dharma"],
        help=(
            "Defense(s) to evaluate. Use 'none' for baseline. "
            "(default: whitemagic_dharma)"
        ),
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        default=None,
        help=(
            "Specific user task IDs to run. "
            "If omitted, uses --all-tasks or --task-limit."
        ),
    )
    parser.add_argument(
        "--all-tasks",
        action="store_true",
        help="Run all user tasks in the suite.",
    )
    parser.add_argument(
        "--task-limit",
        type=int,
        default=5,
        help=(
            "Number of tasks to run when --tasks "
            "is not specified (default: 5)"
        ),
    )
    parser.add_argument(
        "--logdir",
        type=Path,
        default=Path("/tmp/agentdojo_wm"),
        help="Base log directory (default: /tmp/agentdojo_wm).",
    )
    parser.add_argument(
        "--force-rerun",
        action="store_true",
        default=True,
        help="Force rerun even if logs exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be run without calling APIs.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_",
        help="List available suites, tasks, models, and defenses.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write results to JSON file.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-result output.",
    )

    args = parser.parse_args(argv)

    if args.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.list_:
        list_suites_and_models()
        return 0

    # Resolve model enum
    try:
        model = ModelsEnum[args.model]
    except KeyError:
        print(f"Unknown model: {args.model}", file=sys.stderr)
        print("Run with --list to see available models", file=sys.stderr)
        return 1

    # Resolve tasks
    if args.tasks:
        tasks: tuple[str, ...] | None = tuple(args.tasks)
    elif args.all_tasks:
        suite = get_suite(args.suite, args.domain)
        tasks = tuple(suite.user_tasks.keys())
    else:
        suite = get_suite(args.suite, args.domain)
        all_tasks = list(suite.user_tasks.keys())
        tasks = tuple(all_tasks[: args.task_limit])

    if not args.dry_run:
        if not load_dotenv(".env"):
            warnings.warn("No .env file found — API keys may need to be set manually")

    summaries = run_comparison(
        suite_version=args.suite,
        domain=args.domain,
        model=model,
        defenses=args.defense,
        tasks=tasks,
        logdir=args.logdir,
        force_rerun=args.force_rerun,
        dry_run=args.dry_run,
    )

    print_comparison_table(summaries)

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(summaries, fh, indent=2, default=str)
        print(f"\nResults written to {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
