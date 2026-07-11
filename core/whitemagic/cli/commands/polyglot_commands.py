# ruff: noqa: BLE001
# mypy: disable-error-code=no-untyped-def
"""Polyglot CLI Commands — runtime detection, install, compile, and seed.

Provides `wm polyglot` subcommands:
  status   — detect runtimes, show bridge status, report versions
  install  — auto-install missing runtimes via package managers
  compile  — auto-compile bridges (cargo build, mix deps.get, etc.)
  seed     — full setup: detect → install → compile → verify
  update   — check for newer runtime versions
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

# ── Runtime definitions ──────────────────────────────────────────────

# core/whitemagic/cli/commands/ → core/ → repo root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_POLYGLOT_DIR = _PROJECT_ROOT / "polyglot"
# Bridges shipped inside the Python package (available in pip-installed environments)
_PACKAGE_BRIDGES = Path(__file__).resolve().parent.parent.parent / "polyglot_bridges"


@dataclass
class RuntimeInfo:
    """Info about a polyglot runtime."""

    name: str
    binary: str
    min_version: str
    bridge_path: str | None = None
    bridge_role: str = ""
    install_url: str = ""
    # Per-platform install commands
    install_cmds: dict[str, list[str]] = field(default_factory=dict)
    # Version check command (returns version string on stdout)
    version_args: list[str] = field(default_factory=lambda: ["--version"])
    # Parse version from stdout (first line, split by space, take last token)
    version_parse: str = "first_line_last_token"
    detected_version: str | None = None
    available: bool = False


_RUNTIMES: list[RuntimeInfo] = [
    RuntimeInfo(
        name="Rust",
        binary="rustc",
        min_version="1.75.0",
        bridge_path="core/whitemagic-rust",
        bridge_role="Galaxy Core Engine (PyO3, SIMD HRR, evolution bridge)",
        install_url="https://rustup.rs",
        install_cmds={
            "linux": ["sh", "-c", "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"],
            "macos": ["sh", "-c", "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"],
        },
        version_args=["--version"],
        version_parse=r"regex:rustc\s+(\S+)",
    ),
    RuntimeInfo(
        name="Zig",
        binary="zig",
        min_version="0.16.0",
        bridge_path="polyglot/bridges/zig/trn_gate.zig",
        bridge_role="TRN Hard Gate — three-level galaxy access filtering",
        install_url="https://ziglang.org/download/",
        install_cmds={
            "linux": ["sh", "-c", "snap install zig --classic"],
            "macos": ["sh", "-c", "brew install zig"],
        },
        version_args=["version"],
        version_parse="first_line",
    ),
    RuntimeInfo(
        name="Julia",
        binary="julia",
        min_version="1.10.0",
        bridge_path="polyglot/bridges/julia",
        bridge_role="Neuromodulation + Yield curve analysis",
        install_url="https://julialang.org/downloads/",
        install_cmds={
            "linux": ["sh", "-c", "curl -fsSL https://install.julialang.org | sh -s -- --yes"],
            "macos": ["sh", "-c", "curl -fsSL https://install.julialang.org | sh -s -- --yes"],
        },
        version_args=["--version"],
        version_parse="first_line_last_token",
    ),
    RuntimeInfo(
        name="Elixir",
        binary="elixir",
        min_version="1.14.0",
        bridge_path="polyglot/bridges/elixir",
        bridge_role="Ripple tagging + Actor-model hypothesis evaluation",
        install_url="https://elixir-lang.org/install.html",
        install_cmds={
            "linux": ["sh", "-c", "wget https://elixir-lang.org/install.sh && sh install.sh"],
            "macos": ["sh", "-c", "brew install elixir"],
        },
        version_args=["--version"],
        version_parse=r"regex:Elixir\s+(\S+)",
    ),
    RuntimeInfo(
        name="Haskell (GHC)",
        binary="ghc",
        min_version="9.6.0",
        bridge_path="polyglot/bridges/haskell",
        bridge_role="Replay simulation — type-safe memory replay",
        install_url="https://www.haskell.org/ghcup/",
        install_cmds={
            "linux": ["sh", "-c", "curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh"],
            "macos": ["sh", "-c", "brew install ghc cabal-install"],
        },
        version_args=["--version"],
        version_parse=r"regex:\b(\d+\.\d+\.\d+)",
    ),
    RuntimeInfo(
        name="Koka",
        binary="koka",
        min_version="3.1.0",
        bridge_path="polyglot/bridges/koka/disinhibition.kk",
        bridge_role="Disinhibition — sleep/wake state machine for galaxy gating",
        install_url="https://github.com/koka-lang/koka/releases",
        install_cmds={
            "linux": ["sh", "-c", "curl -sSL https://github.com/koka-lang/koka/releases/latest/download/koka-linux-x86_64.tar.gz | tar xz -C /tmp && sudo mv /tmp/koka-* /usr/local/bin/"],
            "macos": ["sh", "-c", "brew install koka"],
        },
        version_args=["--version"],
        version_parse=r"regex:v?(\d+\.\d+\.\d+)",
    ),
    RuntimeInfo(
        name="Go",
        binary="go",
        min_version="1.21.0",
        bridge_path="polyglot/whitemagic-go",
        bridge_role="Galaxy transfer — gRPC streaming, QUIC P2P",
        install_url="https://go.dev/dl/",
        install_cmds={
            "linux": ["sh", "-c", "wget -qO- https://go.dev/dl/go1.25.0.linux-amd64.tar.gz | sudo tar -xz -C /usr/local"],
            "macos": ["sh", "-c", "brew install go"],
        },
        version_args=["version"],
        version_parse=r"regex:go(\S+)",
    ),
]


# ── Bridge definitions (Python-side modules that use the runtimes) ──

_BRIDGES = [
    {"name": "Rust (evolution)", "runtime": "Rust", "module": "whitemagic.core.evolution._rust_bridge", "binary_path": "polyglot/whitemagic-rs/target/release/examples/evolution_bridge"},
    {"name": "Haskell (replay)", "runtime": "Haskell (GHC)", "module": "whitemagic.core.memory.replay_simulation", "source": "polyglot/bridges/haskell/replay_sim.hs"},
    {"name": "Julia (neuro)", "runtime": "Julia", "module": "whitemagic.core.memory.neuromodulation", "source": "polyglot/bridges/julia/neuromodulation.jl"},
    {"name": "Elixir (ripple)", "runtime": "Elixir", "module": "whitemagic.core.memory.ripple_tagging", "source": "polyglot/bridges/elixir/ripple_tagging.exs"},
    {"name": "Zig (TRN gate)", "runtime": "Zig", "module": "whitemagic.core.memory.thalamic_hard_gate", "source": "polyglot/bridges/zig/trn_gate.zig"},
    {"name": "Koka (disinhibition)", "runtime": "Koka", "module": "whitemagic.core.memory.disinhibition", "source": "polyglot/bridges/koka/disinhibition.kk"},
    {"name": "Elixir (actor)", "runtime": "Elixir", "module": "whitemagic.core.evolution._elixir_actor_bridge", "source": "polyglot/bridges/elixir/actor_bridge.exs"},
    {"name": "Julia (yield)", "runtime": "Julia", "module": "whitemagic.core.evolution._julia_yield_bridge", "source": "polyglot/bridges/julia/yield_bridge.jl"},
]


# ── Helpers ──────────────────────────────────────────────────────────

def _detect_runtime(rt: RuntimeInfo) -> None:
    """Detect if a runtime is available and get its version."""
    binary = shutil.which(rt.binary)
    if binary is None:
        rt.available = False
        rt.detected_version = None
        return
    rt.available = True
    try:
        result = subprocess.run(
            [binary] + rt.version_args,
            capture_output=True, text=True, timeout=10,
        )
        output = (result.stdout or result.stderr or "").strip()
        rt.detected_version = _parse_version(output, rt.version_parse)
    except Exception:
        rt.detected_version = "unknown"


def _parse_version(output: str, method: str) -> str | None:
    """Parse version string from command output."""
    if not output:
        return None
    first_line = output.split("\n")[0].strip()
    if method == "first_line":
        return first_line
    if method == "first_line_last_token":
        tokens = first_line.split()
        return tokens[-1] if tokens else None
    if method.startswith("regex:"):
        import re
        pattern = method[6:]
        m = re.search(pattern, output)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    return first_line


def _version_ge(v1: str, v2: str) -> bool:
    """Check if version v1 >= v2. Handles partial versions like '1.17'."""
    try:
        parts1 = [int(x) for x in v1.split(".") if x.isdigit()]
        parts2 = [int(x) for x in v2.split(".") if x.isdigit()]
        # Pad to same length
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)
        return parts1 >= parts2
    except (ValueError, IndexError):
        return False


def _resolve_bridge_source(source: str) -> Path | None:
    """Find a bridge source file — checks repo root first, then package-included copies."""
    if not source:
        return None
    # 1. Check repo root (git clone / development)
    repo_path = _PROJECT_ROOT / source
    if repo_path.exists():
        return repo_path
    # 2. Check package-included bridges (pip install)
    filename = Path(source).name
    subdir = Path(source).parent.name  # e.g. "zig", "koka", "julia", "elixir", "haskell"
    pkg_path = _PACKAGE_BRIDGES / subdir / filename
    if pkg_path.exists():
        return pkg_path
    return None


def _detect_bridge_status(bridge: dict[str, Any]) -> dict[str, Any]:
    """Check if a bridge's source/binary exists and its runtime is available."""
    status: dict[str, Any] = {"name": bridge["name"], "runtime": bridge["runtime"]}
    # Check source file exists (repo or package)
    source = bridge.get("source")
    binary_path = bridge.get("binary_path")
    if source:
        resolved = _resolve_bridge_source(source)
        status["source_exists"] = resolved is not None
        status["source_path"] = source
        if resolved:
            status["source_resolved"] = str(resolved)
    if binary_path:
        full_path = _PROJECT_ROOT / binary_path
        status["binary_exists"] = full_path.exists()
        status["binary_path"] = binary_path
    # Check runtime availability
    rt_name = bridge["runtime"]
    rt = next((r for r in _RUNTIMES if r.name == rt_name), None)
    if rt:
        status["runtime_available"] = rt.available
        status["runtime_version"] = rt.detected_version
        status["runtime_min"] = rt.min_version
        if rt.available and rt.detected_version:
            status["version_ok"] = _version_ge(rt.detected_version, rt.min_version)
        else:
            status["version_ok"] = False
    # Determine overall status
    if source and not status.get("source_exists", False):
        if binary_path and not status.get("binary_exists", False):
            status["status"] = "missing_source"
        else:
            status["status"] = "missing_source"
    elif binary_path and not status.get("binary_exists", False):
        status["status"] = "needs_compile"
    elif not status.get("runtime_available", False):
        status["status"] = "missing_runtime"
    elif not status.get("version_ok", False):
        status["status"] = "version_too_old"
    else:
        status["status"] = "ready"
    return status


def _get_platform() -> str:
    """Get platform identifier for install commands."""
    system = platform.system().lower()
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return "linux"


# ── CLI Commands ─────────────────────────────────────────────────────

@click.group(name="polyglot")
def polyglot_group() -> None:
    """Polyglot runtime management — detect, install, compile, and seed bridges."""


@polyglot_group.command(name="status")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
def polyglot_status(json_output: bool) -> None:
    """Show runtime versions and bridge readiness."""
    # Detect all runtimes
    for rt in _RUNTIMES:
        _detect_runtime(rt)

    # Check all bridges
    bridge_statuses = [_detect_bridge_status(b) for b in _BRIDGES]

    ready = sum(1 for b in bridge_statuses if b["status"] == "ready")
    total = len(bridge_statuses)

    if json_output:
        import json
        output = {
            "runtimes": [
                {
                    "name": rt.name,
                    "available": rt.available,
                    "version": rt.detected_version,
                    "min_version": rt.min_version,
                    "binary": rt.binary,
                    "bridge_role": rt.bridge_role,
                }
                for rt in _RUNTIMES
            ],
            "bridges": bridge_statuses,
            "summary": {
                "ready": ready,
                "total": total,
                "health_score": round(ready / total, 2) if total else 0,
            },
        }
        click.echo(json.dumps(output, indent=2))
        return

    click.echo("\n🌐 WhiteMagic Polyglot Status")
    click.echo("=" * 50)

    click.echo("\n📋 Runtimes:")
    for rt in _RUNTIMES:
        if rt.available:
            version_ok = rt.detected_version and _version_ge(rt.detected_version, rt.min_version)
            icon = "✅" if version_ok else "⚠️"
            ver = rt.detected_version or "unknown"
            click.echo(f"  {icon} {rt.name:16s} v{ver}  (min: v{rt.min_version})")
        else:
            click.echo(f"  ❌ {rt.name:16s} not installed  (min: v{rt.min_version})")
            click.echo(f"     Install: {rt.install_url}")

    click.echo(f"\n🔌 Bridges ({ready}/{total} ready):")
    status_icons = {
        "ready": "✅",
        "needs_compile": "🔧",
        "missing_runtime": "❌",
        "missing_source": "❓",
        "version_too_old": "⚠️",
    }
    status_labels = {
        "ready": "ready",
        "needs_compile": "needs compile",
        "missing_runtime": "runtime missing",
        "missing_source": "source missing",
        "version_too_old": "runtime too old",
    }
    for b in bridge_statuses:
        icon = status_icons.get(b["status"], "❓")
        label = status_labels.get(b["status"], b["status"])
        click.echo(f"  {icon} {b['name']:24s} {label}")

    click.echo(f"\n📊 Health Score: {ready}/{total} ({ready/total*100:.0f}%)")

    if ready < total:
        click.echo("\n💡 Run 'wm polyglot seed' to install missing runtimes and compile bridges.")
    else:
        click.echo("\n✨ All polyglot bridges ready!")


@polyglot_group.command(name="install")
@click.option("--runtime", "-r", help="Install specific runtime (e.g., zig, koka).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
def polyglot_install(runtime: str | None, yes: bool) -> None:
    """Install missing polyglot runtimes."""
    plat = _get_platform()
    to_install = _RUNTIMES if runtime is None else [r for r in _RUNTIMES if r.name.lower() == runtime.lower()]

    if not to_install:
        click.echo(f"⚠️  Unknown runtime: {runtime}")
        click.echo(f"   Available: {', '.join(r.name for r in _RUNTIMES)}")
        return

    # Detect what's already installed
    need_install = []
    for rt in to_install:
        _detect_runtime(rt)
        if rt.available and rt.detected_version and _version_ge(rt.detected_version, rt.min_version):
            click.echo(f"  ✅ {rt.name} already installed (v{rt.detected_version})")
        else:
            need_install.append(rt)

    if not need_install:
        click.echo("\n✅ All requested runtimes already installed.")
        return

    click.echo(f"\n📦 Runtimes to install: {', '.join(rt.name for rt in need_install)}")
    if not yes:
        if not click.confirm("Proceed with installation?"):
            return

    for rt in need_install:
        cmds = rt.install_cmds.get(plat)
        if not cmds:
            click.echo(f"\n⚠️  No auto-install for {rt.name} on {plat}")
            click.echo(f"   Manual install: {rt.install_url}")
            continue

        click.echo(f"\n📦 Installing {rt.name}...")
        click.echo(f"   Running: {' '.join(cmds)}")
        try:
            result = subprocess.run(cmds, shell=False, timeout=300)
            if result.returncode == 0:
                click.echo(f"   ✅ {rt.name} installed successfully")
            else:
                click.echo(f"   ❌ {rt.name} install failed (exit code {result.returncode})")
                click.echo(f"   Manual install: {rt.install_url}")
        except subprocess.TimeoutExpired:
            click.echo(f"   ❌ {rt.name} install timed out (5min)")
        except Exception as e:
            click.echo(f"   ❌ {rt.name} install error: {e}")
            click.echo(f"   Manual install: {rt.install_url}")

    click.echo("\n💡 Run 'wm polyglot compile' to build bridge artifacts.")


@polyglot_group.command(name="compile")
@click.option("--bridge", "-b", help="Compile specific bridge (e.g., rust, elixir).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
def polyglot_compile(bridge: str | None, yes: bool) -> None:
    """Compile polyglot bridge artifacts."""
    compile_tasks = _get_compile_tasks()
    if bridge:
        compile_tasks = [t for t in compile_tasks if bridge.lower() in t["name"].lower()]

    if not compile_tasks:
        click.echo(f"⚠️  No compile tasks found for: {bridge}")
        return

    # Check runtimes are available for compilation
    for task in compile_tasks:
        rt_name = task["runtime"]
        rt = next((r for r in _RUNTIMES if r.name == rt_name), None)
        if rt:
            _detect_runtime(rt)
            if not rt.available:
                click.echo(f"  ❌ {task['name']}: {rt_name} not installed")
                task["skip"] = True
            else:
                task["skip"] = False
        else:
            task["skip"] = False

    tasks_to_run = [t for t in compile_tasks if not t.get("skip")]
    if not tasks_to_run:
        click.echo("\n❌ No tasks to run — install missing runtimes first.")
        return

    click.echo(f"\n🔧 Compile tasks ({len(tasks_to_run)}):")
    for t in tasks_to_run:
        click.echo(f"  • {t['name']}: {' '.join(t['cmd'])}")
    if not yes:
        if not click.confirm("Proceed?"):
            return

    for task in tasks_to_run:
        click.echo(f"\n🔧 Compiling {task['name']}...")
        try:
            result = subprocess.run(
                task["cmd"],
                cwd=str(_PROJECT_ROOT / task.get("cwd", "")),
                shell=False,
                timeout=task.get("timeout", 300),
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                click.echo(f"   ✅ {task['name']} compiled successfully")
                if result.stdout:
                    for line in result.stdout.strip().split("\n")[-3:]:
                        click.echo(f"      {line}")
            else:
                click.echo(f"   ❌ {task['name']} compile failed")
                if result.stderr:
                    click.echo(f"      {result.stderr[:300]}")
        except subprocess.TimeoutExpired:
            click.echo(f"   ❌ {task['name']} compile timed out")
        except Exception as e:
            click.echo(f"   ❌ {task['name']} compile error: {e}")

    click.echo("\n💡 Run 'wm polyglot status' to verify bridges are ready.")


@polyglot_group.command(name="seed")
@click.option("--yes", "-y", is_flag=True, help="Skip all confirmation prompts.")
def polyglot_seed(yes: bool) -> None:
    """Full polyglot setup: detect → install → compile → verify."""
    click.echo("\n🌱 WhiteMagic Polyglot Seed")
    click.echo("=" * 50)

    # Step 1: Detect
    click.echo("\nStep 1/4: Detecting runtimes...")
    for rt in _RUNTIMES:
        _detect_runtime(rt)
        if rt.available:
            version_ok = rt.detected_version and _version_ge(rt.detected_version, rt.min_version)
            icon = "✅" if version_ok else "⚠️"
            click.echo(f"  {icon} {rt.name:16s} v{rt.detected_version}")
        else:
            click.echo(f"  ❌ {rt.name:16s} not installed")

    # Step 2: Install missing
    need_install = [rt for rt in _RUNTIMES if not rt.available or
                    (rt.detected_version and not _version_ge(rt.detected_version, rt.min_version))]

    if need_install:
        click.echo(f"\nStep 2/4: Installing {len(need_install)} missing runtimes...")
        if not yes:
            if not click.confirm(f"Install {', '.join(rt.name for rt in need_install)}?"):
                click.echo("Skipping installation. Bridges will use Python fallbacks.")
                need_install = []
        if need_install:
            _do_install(need_install, yes=yes)
            # Re-detect after install
            for rt in need_install:
                _detect_runtime(rt)
    else:
        click.echo("\nStep 2/4: All runtimes already installed ✅")

    # Step 3: Compile bridges
    click.echo("\nStep 3/4: Compiling bridges...")
    compile_tasks = _get_compile_tasks()
    runnable = []
    for task in compile_tasks:
        rt_name = task["runtime"]
        rt = next((r for r in _RUNTIMES if r.name == rt_name), None)
        if rt and rt.available:
            runnable.append(task)
        else:
            click.echo(f"  ⏭️  {task['name']}: skipped (runtime not available)")

    if runnable:
        if not yes:
            if not click.confirm(f"Compile {len(runnable)} bridges?"):
                click.echo("Skipping compilation.")
                runnable = []
        if runnable:
            _do_compile(runnable, yes=yes)
    else:
        click.echo("  No bridges to compile (all runtimes missing or already compiled).")

    # Step 4: Verify
    click.echo("\nStep 4/4: Verifying bridges...")
    bridge_statuses = [_detect_bridge_status(b) for b in _BRIDGES]
    ready = sum(1 for b in bridge_statuses if b["status"] == "ready")
    total = len(bridge_statuses)

    status_icons = {"ready": "✅", "needs_compile": "🔧", "missing_runtime": "❌", "missing_source": "❓", "version_too_old": "⚠️"}
    for b in bridge_statuses:
        icon = status_icons.get(b["status"], "❓")
        click.echo(f"  {icon} {b['name']:24s} {b['status']}")

    click.echo(f"\n📊 Result: {ready}/{total} bridges ready ({ready/total*100:.0f}%)")
    if ready == total:
        click.echo("✨ All polyglot bridges operational!")
    elif ready > 0:
        click.echo("💡 Some bridges ready. Others will use Python fallbacks.")
    else:
        click.echo("⚠️  No bridges ready. System will use Python fallbacks only.")
        click.echo("   Install runtimes manually and run 'wm polyglot seed' again.")


@polyglot_group.command(name="update")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
def polyglot_update(yes: bool) -> None:
    """Check for and apply runtime updates."""
    click.echo("\n🔄 WhiteMagic Polyglot Update Check")
    click.echo("=" * 50)

    updates_available = []
    for rt in _RUNTIMES:
        _detect_runtime(rt)
        if rt.available:
            click.echo(f"  {rt.name:16s} v{rt.detected_version} (min: v{rt.min_version})")
            # Check if we can update via the runtime's own updater
            updater = _get_runtime_updater(rt)
            if updater:
                updates_available.append((rt, updater))
        else:
            click.echo(f"  {rt.name:16s} not installed")

    if not updates_available:
        click.echo("\n✅ All installed runtimes are up to date.")
        return

    click.echo(f"\n🔄 Can check for updates: {', '.join(rt.name for rt, _ in updates_available)}")
    if not yes:
        if not click.confirm("Check for updates?"):
            return

    for rt, updater in updates_available:
        click.echo(f"\n🔄 Checking {rt.name}...")
        try:
            result = subprocess.run(updater, shell=False, timeout=120, capture_output=True, text=True)
            output = (result.stdout + result.stderr).strip()
            if result.returncode == 0:
                click.echo(f"   ✅ {rt.name} update check complete")
                if output:
                    for line in output.split("\n")[-3:]:
                        click.echo(f"      {line}")
            else:
                click.echo(f"   ⚠️  {rt.name} update check returned: {output[:200]}")
        except Exception as e:
            click.echo(f"   ⚠️  {rt.name} update check failed: {e}")


# ── Internal helpers ─────────────────────────────────────────────────

def _get_compile_tasks() -> list[dict[str, Any]]:
    """Get list of bridge compilation tasks."""
    return [
        {
            "name": "Rust (evolution bridge)",
            "runtime": "Rust",
            "cmd": ["cargo", "build", "--release"],
            "cwd": "core/whitemagic-rust",
            "timeout": 600,
        },
        {
            "name": "Elixir (mix deps)",
            "runtime": "Elixir",
            "cmd": ["mix", "deps.get"],
            "cwd": "polyglot/elixir",
            "timeout": 120,
        },
        {
            "name": "Elixir (mix compile)",
            "runtime": "Elixir",
            "cmd": ["mix", "compile"],
            "cwd": "polyglot/elixir",
            "timeout": 120,
        },
        {
            "name": "Haskell (cabal build)",
            "runtime": "Haskell (GHC)",
            "cmd": ["runhaskell", "-e", "return ()"],
            "cwd": "polyglot/bridges/haskell",
            "timeout": 60,
        },
        # Zig, Koka, Julia are interpreted/JIT — no compile needed
    ]


def _get_runtime_updater(rt: RuntimeInfo) -> list[str] | None:
    """Get update command for a runtime, if it has one."""
    updaters = {
        "Rust": ["rustup", "update"],
        "Haskell (GHC)": ["ghcup", "upgrade"],
    }
    return updaters.get(rt.name)


def _do_install(runtimes: list[RuntimeInfo], yes: bool = False) -> None:
    """Install runtimes."""
    plat = _get_platform()
    for rt in runtimes:
        cmds = rt.install_cmds.get(plat)
        if not cmds:
            click.echo(f"  ⚠️  No auto-install for {rt.name} on {plat}")
            click.echo(f"     Manual: {rt.install_url}")
            continue
        click.echo(f"\n  📦 Installing {rt.name}...")
        try:
            result = subprocess.run(cmds, shell=False, timeout=300)
            if result.returncode == 0:
                click.echo(f"  ✅ {rt.name} installed")
            else:
                click.echo(f"  ❌ {rt.name} failed (exit {result.returncode})")
                click.echo(f"     Manual: {rt.install_url}")
        except Exception as e:
            click.echo(f"  ❌ {rt.name} error: {e}")
            click.echo(f"     Manual: {rt.install_url}")


def _do_compile(tasks: list[dict[str, Any]], yes: bool = False) -> None:
    """Compile bridge artifacts."""
    for task in tasks:
        click.echo(f"\n  🔧 {task['name']}...")
        try:
            result = subprocess.run(
                task["cmd"],
                cwd=str(_PROJECT_ROOT / task.get("cwd", "")),
                shell=False,
                timeout=task.get("timeout", 300),
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                click.echo(f"  ✅ {task['name']} done")
            else:
                click.echo(f"  ❌ {task['name']} failed")
                if result.stderr:
                    click.echo(f"     {result.stderr[:200]}")
        except Exception as e:
            click.echo(f"  ❌ {task['name']} error: {e}")


@polyglot_group.command(name="fetch")
@click.option("--dest", "-d", help="Destination directory (default: ~/.whitemagic/polyglot_bridges).")
def polyglot_fetch(dest: str | None) -> None:
    """Download polyglot bridge sources from GitHub (for pip-installed users)."""
    import urllib.request

    click.echo("\n📥 Fetching polyglot bridge sources...")

    from whitemagic.config.paths import WM_ROOT

    dest_dir = Path(dest) if dest else WM_ROOT / "polyglot_bridges"
    dest_dir.mkdir(parents=True, exist_ok=True)

    base_url = "https://raw.githubusercontent.com/lbailey94/whitemagic/main/polyglot/bridges"
    files = [
        ("zig/trn_gate.zig", "zig"),
        ("koka/bridge.kk", "koka"),
        ("koka/cascade_bridge.kk", "koka"),
        ("koka/disinhibition.kk", "koka"),
        ("julia/bridge.jl", "julia"),
        ("julia/neuromodulation.jl", "julia"),
        ("julia/yield_bridge.jl", "julia"),
        ("elixir/bridge.exs", "elixir"),
        ("elixir/ripple_tagging.exs", "elixir"),
        ("elixir/actor_bridge.exs", "elixir"),
        ("haskell/bridge.hs", "haskell"),
        ("haskell/cascade_bridge.hs", "haskell"),
        ("haskell/replay_sim.hs", "haskell"),
    ]

    downloaded = 0
    failed = 0
    for filepath, subdir in files:
        url = f"{base_url}/{filepath}"
        filename = Path(filepath).name
        target = dest_dir / subdir / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            urllib.request.urlretrieve(url, target)
            click.echo(f"  ✅ {subdir}/{filename}")
            downloaded += 1
        except Exception as e:
            click.echo(f"  ❌ {subdir}/{filename}: {e}")
            failed += 1

    click.echo(f"\n📊 Downloaded {downloaded}/{len(files)} bridge sources to {dest_dir}")
    if failed > 0:
        click.echo("   Some downloads failed. Check your network connection.")
    click.echo("\n💡 Run 'wm polyglot status' to verify bridges are detected.")


def register_polyglot_commands(main_group: click.Group) -> None:
    """Register polyglot commands onto the main CLI group."""
    main_group.add_command(polyglot_group)
