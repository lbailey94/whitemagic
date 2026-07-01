#!/usr/bin/env python3
# ruff: noqa: E402
# mypy: disable-error-code=no-untyped-def
"""WhiteMagic CLI - Complete Implementation
Phase 1: Core Commands for Production Readiness

**SHIP_SURFACE**: 🎯 Core Tier - Essential runtime component
"""

import logging
import os
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import click

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)

try:
    from whitemagic import __version__
except ImportError:
    __version__ = "unknown"

from whitemagic.cli.boot import bootstrap_env_from_argv, register_all_commands

bootstrap_env_from_argv(sys.argv)


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--state-root",
    help="Override WM_STATE_ROOT for this run (recommended for tests/containers).",
)
@click.option(
    "--base-dir",
    help="(Deprecated) Alias for --state-root.",
)
@click.option(
    "--db-path",
    help="Override WM_DB_PATH for this run (SQLite DB file path).",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit full tool envelopes as JSON (AI-friendly).",
)
@click.option("--now", help="ISO timestamp override for deterministic tool runs.")
@click.option(
    "--silent-init",
    is_flag=True,
    help="Set WM_SILENT_INIT=1 to suppress noisy initialization logs.",
)
@click.pass_context
def main(
    ctx,
    state_root: str | None,
    base_dir: str | None,
    db_path: str | None,
    json_output: bool,
    now: str | None,
    silent_init: bool,
):
    """WhiteMagic CLI - AI Memory & Context Management"""
    effective_state_root = state_root or base_dir

    if json_output or silent_init:
        os.environ.setdefault("WM_SILENT_INIT", "1")

    if effective_state_root:
        os.environ.setdefault("WM_STATE_ROOT", effective_state_root)
    if db_path:
        os.environ.setdefault("WM_DB_PATH", db_path)

    ctx.ensure_object(dict)
    ctx.obj["state_root"] = effective_state_root
    ctx.obj["json_output"] = bool(json_output)
    ctx.obj["now"] = now

    # Non-blocking update check (cached 24h, opt-out via WM_NO_UPDATE_CHECK=1)
    if not json_output:
        try:
            from whitemagic.core.update_checker import check_for_update

            update_msg = check_for_update()
            if update_msg:
                click.echo(update_msg, err=True)
        except (ImportError, ModuleNotFoundError):
            pass


from whitemagic.cli.commands.diagnostics_commands import status_command

_memory = None


def get_memory():  # type: ignore[return]
    """Get or create memory instance (respects WM_STATE_ROOT)."""
    global _memory
    if _memory is None:
        try:
            from whitemagic.core.memory.unified import get_unified_memory

            _memory = get_unified_memory()
        except ImportError:
            pass
    return _memory


# Register all plugins and extensions
register_all_commands(main, get_memory, status_command, _json_dumps)

if __name__ == "__main__":
    main()
