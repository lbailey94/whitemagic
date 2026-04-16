#!/usr/bin/env python3
"""
WhiteMagic Omega Test — Comprehensive project health check.

Runs all test categories in sequence with rich progress bars and a
final summary report. A single command to verify the entire system.

Usage:
    python scripts/omega_test.py            # Full run
    python scripts/omega_test.py --quick    # Skip slow/network tests
    python scripts/omega_test.py --json     # Output JSON report
    python scripts/omega_test.py --ci       # CI mode (exit 1 on failure)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ensure core is on PYTHONPATH
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import (
        BarColumn, MofNCompleteColumn, Progress,
        SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn,
    )
    from rich.table import Table
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SuiteResult:
    name: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_s: float = 0.0
    status: str = "pending"   # pending | running | ok | fail | skip

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def icon(self) -> str:
        return {"ok": "✅", "fail": "❌", "skip": "⏭️", "running": "🔄", "pending": "⏳"}.get(self.status, "❓")


# ──────────────────────────────────────────────────────────────────────────────
# Individual test suites
# ──────────────────────────────────────────────────────────────────────────────

def suite_import_health() -> SuiteResult:
    """Verify core modules can be imported without error."""
    result = SuiteResult("Import Health")
    modules = [
        "whitemagic",
        "whitemagic.config",
        "whitemagic.tools.unified_api",
        "whitemagic.tools.manifest",
        "whitemagic.core.memory.manager",
        "whitemagic.security",
        "whitemagic.cli.cli_app",
        "whitemagic.grimoire.core",
        "whitemagic.gardens",
        "whitemagic.run_mcp",
    ]
    t0 = time.monotonic()
    for mod in modules:
        try:
            __import__(mod)
            result.passed += 1
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"{mod}: {exc}")
    result.duration_s = time.monotonic() - t0
    result.status = "ok" if result.failed == 0 else "fail"
    return result


def suite_path_hygiene() -> SuiteResult:
    """Run the path hygiene checker."""
    result = SuiteResult("Path Hygiene")
    hygiene_script = REPO_ROOT / "scripts" / "verification" / "check_path_hygiene.py"
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(hygiene_script)],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        )
        if proc.returncode == 0:
            result.passed = 1
            result.status = "ok"
        else:
            result.failed = 1
            result.status = "fail"
            result.errors.append(proc.stdout[-500:] or proc.stderr[-500:])
    except FileNotFoundError:
        result.skipped = 1
        result.status = "skip"
        result.errors.append("check_path_hygiene.py not found")
    except subprocess.TimeoutExpired:
        result.failed = 1
        result.status = "fail"
        result.errors.append("Timeout exceeded (30s)")
    result.duration_s = time.monotonic() - t0
    return result


def suite_tool_registry() -> SuiteResult:
    """Verify the tool registry loads and all tools are registered."""
    result = SuiteResult("Tool Registry")
    t0 = time.monotonic()
    try:
        from whitemagic.tools.tool_surface import get_callable_tool_definitions
        tool_defs = get_callable_tool_definitions()
        count = len(list(tool_defs))
        if count > 0:
            result.passed = count
            result.status = "ok"
        else:
            result.failed = 1
            result.status = "fail"
            result.errors.append("No tools registered!")
    except Exception as exc:
        result.failed = 1
        result.status = "fail"
        result.errors.append(str(exc))
    result.duration_s = time.monotonic() - t0
    return result


def suite_mcp_boot() -> SuiteResult:
    """Verify MCP server can initialize without crashing."""
    result = SuiteResult("MCP Server Boot")
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, '.'); "
             "from whitemagic.run_mcp import lifecycle, register_resources, register_tools; "
             "lifecycle.startup(); register_resources(); register_tools(); print('OK')"],
            capture_output=True, text=True, timeout=20,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT),
                 "WM_SILENT_INIT": "1", "WM_MCP_LITE": "1"},
        )
        if "OK" in proc.stdout or proc.returncode == 0:
            result.passed = 1
            result.status = "ok"
        else:
            result.failed = 1
            result.status = "fail"
            result.errors.append((proc.stderr or proc.stdout)[-600:])
    except subprocess.TimeoutExpired:
        result.failed = 1
        result.status = "fail"
        result.errors.append("MCP boot timed out (20s)")
    except Exception as exc:
        result.failed = 1
        result.status = "fail"
        result.errors.append(str(exc))
    result.duration_s = time.monotonic() - t0
    return result


def suite_rust_bridge() -> SuiteResult:
    """Check Rust bridge availability."""
    result = SuiteResult("Rust Bridge")
    t0 = time.monotonic()
    try:
        import importlib.util
        spec = importlib.util.find_spec("whitemagic_rust")
        if spec is not None:
            import whitemagic_rust  # noqa: F401
            result.passed = 1
            result.status = "ok"
        else:
            result.skipped = 1
            result.status = "skip"
            result.errors.append("whitemagic_rust not built — run: cd whitemagic-rust && maturin develop")
    except Exception as exc:
        result.skipped = 1
        result.status = "skip"
        result.errors.append(f"Bridge import error: {exc}")
    result.duration_s = time.monotonic() - t0
    return result


def suite_unit_tests(quick: bool = False) -> SuiteResult:
    """Run the pytest unit test suite."""
    result = SuiteResult("Unit Tests")
    t0 = time.monotonic()
    cmd = [
        sys.executable, "-m", "pytest", "tests/unit/", "-q", "--tb=no",
        "--no-header", "-x" if quick else "",
    ]
    cmd = [c for c in cmd if c]  # strip empty flags
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT),
                 "WM_SILENT_INIT": "1", "WM_STATE_ROOT": "/tmp/wm_omega_test"},
        )
        # Parse pytest summary line: "X passed, Y failed, Z skipped"
        for line in (proc.stdout + proc.stderr).splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                import re
                nums = {m[1]: int(m[0]) for m in re.findall(r"(\d+) (passed|failed|skipped|error)", line)}
                result.passed = nums.get("passed", 0)
                result.failed = nums.get("failed", 0) + nums.get("error", 0)
                result.skipped = nums.get("skipped", 0)
                break
        result.status = "ok" if result.failed == 0 else "fail"
        if proc.returncode != 0 and result.failed == 0:
            result.failed = 1
            result.status = "fail"
            result.errors.append(proc.stdout[-400:])
    except subprocess.TimeoutExpired:
        result.failed = 1
        result.status = "fail"
        result.errors.append("Unit tests timed out (120s)")
    except Exception as exc:
        result.failed = 1
        result.status = "fail"
        result.errors.append(str(exc))
    result.duration_s = time.monotonic() - t0
    return result


def suite_integration_tests(quick: bool = False) -> SuiteResult:
    """Run the pytest integration test suite."""
    result = SuiteResult("Integration Tests")
    if quick:
        result.skipped = 1
        result.status = "skip"
        result.errors.append("Skipped in --quick mode")
        return result
    t0 = time.monotonic()
    cmd = [sys.executable, "-m", "pytest", "tests/integration/", "-q", "--tb=no", "--no-header"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT),
                 "WM_SILENT_INIT": "1", "WM_STATE_ROOT": "/tmp/wm_omega_test"},
        )
        for line in (proc.stdout + proc.stderr).splitlines():
            if "passed" in line or "failed" in line:
                import re
                nums = {m[1]: int(m[0]) for m in re.findall(r"(\d+) (passed|failed|skipped|error)", line)}
                result.passed = nums.get("passed", 0)
                result.failed = nums.get("failed", 0) + nums.get("error", 0)
                result.skipped = nums.get("skipped", 0)
                break
        result.status = "ok" if result.failed == 0 else "fail"
    except subprocess.TimeoutExpired:
        result.failed = 1
        result.status = "fail"
        result.errors.append("Integration tests timed out (180s)")
    except Exception as exc:
        result.failed = 1
        result.status = "fail"
        result.errors.append(str(exc))
    result.duration_s = time.monotonic() - t0
    return result


def suite_ship_check() -> SuiteResult:
    """Run the ship surface hygiene check."""
    result = SuiteResult("Ship Surface Check")
    t0 = time.monotonic()
    ship_script = REPO_ROOT / "scripts" / "check_ship.py"
    try:
        proc = subprocess.run(
            [sys.executable, str(ship_script)],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT), "WM_SILENT_INIT": "1"},
        )
        if proc.returncode == 0:
            result.passed = 1
            result.status = "ok"
        else:
            result.failed = 1
            result.status = "fail"
            result.errors.append(proc.stdout[-400:] or proc.stderr[-400:])
    except FileNotFoundError:
        result.skipped = 1
        result.status = "skip"
    except subprocess.TimeoutExpired:
        result.failed = 1
        result.status = "fail"
        result.errors.append("Timeout (120s)")
    result.duration_s = time.monotonic() - t0
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Rich rendering
# ──────────────────────────────────────────────────────────────────────────────

def render_results_table(results: list[SuiteResult], total_s: float) -> Table:
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan",
                  title="[bold]WhiteMagic Omega Test — Results[/bold]", expand=True)
    table.add_column("Suite", style="white", no_wrap=True)
    table.add_column("Status", justify="center", width=6)
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Time", justify="right", style="dim")

    total_p = total_f = total_s_count = 0
    for r in results:
        status_color = {"ok": "green", "fail": "red", "skip": "yellow",
                        "pending": "dim", "running": "cyan"}.get(r.status, "white")
        table.add_row(
            r.name,
            f"[{status_color}]{r.icon}[/{status_color}]",
            str(r.passed) if r.passed else "[dim]—[/dim]",
            f"[red]{r.failed}[/red]" if r.failed else "[dim]—[/dim]",
            str(r.skipped) if r.skipped else "[dim]—[/dim]",
            f"{r.duration_s:.1f}s",
        )
        total_p += r.passed
        total_f += r.failed
        total_s_count += r.skipped

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]", "",
        f"[bold green]{total_p}[/bold green]",
        f"[bold red]{total_f}[/bold red]" if total_f else "[dim]0[/dim]",
        str(total_s_count) if total_s_count else "[dim]0[/dim]",
        f"[bold]{total_s:.1f}s[/bold]",
    )
    return table


def print_errors(results: list[SuiteResult], console: "Console") -> None:
    for r in results:
        if r.errors and r.status == "fail":
            console.print(f"\n[bold red]❌ {r.name} — Errors:[/bold red]")
            for e in r.errors[:3]:
                console.print(f"   [dim]{e[:200]}[/dim]")


# ──────────────────────────────────────────────────────────────────────────────
# Main runner
# ──────────────────────────────────────────────────────────────────────────────

SUITES = [
    ("Import Health",        suite_import_health),
    ("Path Hygiene",         suite_path_hygiene),
    ("Tool Registry",        suite_tool_registry),
    ("MCP Server Boot",      suite_mcp_boot),
    ("Rust Bridge",          suite_rust_bridge),
    ("Unit Tests",           suite_unit_tests),
    ("Integration Tests",    suite_integration_tests),
    ("Ship Surface Check",   suite_ship_check),
]


def run_plain(quick: bool) -> tuple[list[SuiteResult], float]:
    """Plain text runner (fallback when rich not available)."""
    results = []
    t_total = time.monotonic()
    for name, fn in SUITES:
        print(f"  ▸ {name} ...", end="", flush=True)
        kwargs: dict = {}
        if fn.__code__.co_varnames[:fn.__code__.co_argcount]:
            kwargs = {"quick": quick} if "quick" in fn.__code__.co_varnames else {}
        r = fn(**kwargs)  # type: ignore[call-arg]
        results.append(r)
        print(f"  {r.icon}  ({r.duration_s:.1f}s)")
    return results, time.monotonic() - t_total


def run_rich(quick: bool) -> tuple[list[SuiteResult], float]:
    """Rich TUI runner with live progress bars."""
    console = Console()
    results: list[SuiteResult] = []
    t_total = time.monotonic()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold white]{task.description:<26}"),
        BarColumn(bar_width=32),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        for name, fn in SUITES:
            task = progress.add_task(name, total=1)
            progress.update(task, description=f"[cyan]{name}[/cyan]")
            kwargs: dict = {}
            if "quick" in fn.__code__.co_varnames:
                kwargs = {"quick": quick}
            r: SuiteResult = fn(**kwargs)  # type: ignore[call-arg]
            r.name = name
            results.append(r)
            color = {"ok": "green", "fail": "red", "skip": "yellow"}.get(r.status, "white")
            progress.update(task, completed=1,
                            description=f"[{color}]{r.icon} {name}[/{color}]")

    elapsed = time.monotonic() - t_total
    console.print()
    console.print(render_results_table(results, elapsed))
    print_errors(results, console)
    return results, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description="WhiteMagic Omega Test Runner")
    parser.add_argument("--quick", action="store_true", help="Skip slow tests (integration, network)")
    parser.add_argument("--json", action="store_true", help="Output JSON report to stdout")
    parser.add_argument("--ci", action="store_true", help="Exit with code 1 on any failure")
    args = parser.parse_args()

    if args.json or not HAS_RICH:
        if not args.json:
            print("WhiteMagic Omega Test (plain mode — install 'rich' for TUI)")
            print("─" * 48)
        results, elapsed = run_plain(args.quick)
    else:
        from rich.console import Console
        Console().print(Panel.fit(
            "[bold cyan]WhiteMagic Omega Test[/bold cyan]\n"
            "[dim]Comprehensive project health verification[/dim]",
            border_style="cyan",
        ))
        results, elapsed = run_rich(args.quick)

    failed_count = sum(r.failed for r in results)

    if args.json:
        report = {
            "total_duration_s": round(elapsed, 2),
            "passed": sum(r.passed for r in results),
            "failed": failed_count,
            "skipped": sum(r.skipped for r in results),
            "suites": [
                {"name": r.name, "status": r.status,
                 "passed": r.passed, "failed": r.failed, "skipped": r.skipped,
                 "duration_s": round(r.duration_s, 2), "errors": r.errors}
                for r in results
            ],
        }
        print(json.dumps(report, indent=2))

    if not args.json:
        overall = "✅ ALL SYSTEMS GO" if failed_count == 0 else f"❌ {failed_count} failure(s) detected"
        print(f"\n{overall}  ({elapsed:.1f}s total)\n")

    if args.ci and failed_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
