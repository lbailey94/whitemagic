"""Lazy Group implementation for Click CLI.

Provides lazy-loaded command groups to avoid importing heavy dependencies
at CLI startup time. This enables faster CLI help and better error messages
when optional dependencies are missing.
"""

from collections.abc import Callable
from typing import Any

import click


class LazyGroup(click.Group):
    """Click group that defers subcommand loading until first invocation.

    This dramatically improves CLI startup time by avoiding imports for
    commands that aren't being used.

    Usage:
        @main.group(cls=LazyGroup, invoke_without_command=True)
        def rust():
            \"\"\"Rust bridge commands (requires whitemagic-rust)\"\"\"
            from .cli_rust import register_rust_commands
            return register_rust_commands(main)
    """

    def __init__(self, loader: Callable[[], Any] | None = None, **kwargs):
        self._loader = loader
        self._loaded = False
        super().__init__(**kwargs)

    def get_command(self, ctx, cmd_name):
        """Get a command, triggering lazy load if needed."""
        if not self._loaded and self._loader:
            self._load_commands()
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        """List commands, triggering lazy load if needed."""
        if not self._loaded and self._loader:
            self._load_commands()
        return super().list_commands(ctx)

    def _load_commands(self) -> None:
        """Execute the loader to register subcommands."""
        if self._loaded:
            return

        if self._loader:
            try:
                result = self._loader()
                # Loader can return None or the group itself
                if result is not None and result is not self:
                    # If loader returns a different object, copy its commands
                    if hasattr(result, 'commands'):
                        for name, cmd in result.commands.items():
                            self.add_command(cmd, name=name)
            except ImportError as e:
                # Graceful degradation - add a placeholder command that shows error
                self.add_command(_create_missing_dep_command(str(e)))

        self._loaded = True


class LazyCommand(click.Command):
    """Click command that defers loading until first invocation.

    Useful for individual commands that have heavy dependencies.
    """

    def __init__(self, loader: Callable[[], click.Command] | None = None, **kwargs):
        self._loader = loader
        self._loaded_command: click.Command | None = None
        super().__init__(**kwargs)

    def invoke(self, ctx):
        """Invoke the command, loading if needed."""
        if not self._loaded_command and self._loader:
            try:
                self._loaded_command = self._loader()
                # Copy parameters and callback
                self.params = self._loaded_command.params
                self.callback = self._loaded_command.callback
            except ImportError as e:
                # Replace callback with error handler
                self.callback = _make_missing_dep_callback(str(e))

        return super().invoke(ctx)


def _create_missing_dep_command(error_msg: str) -> click.Command:
    """Create a CLI command that informs the user about a missing optional dependency.

    This is the intended runtime behavior when an extra (e.g. 'mcp', 'api') is
    not installed — not a development stub.
    """
    @click.command(name="unavailable")
    @click.pass_context
    def unavailable_cmd(ctx):
        """Click command that prints a missing-dependency error and exits with code 1."""
        click.echo("ERROR: This command requires additional dependencies.", err=True)
        click.echo(f"Details: {error_msg}", err=True)
        click.echo("Install with: pip install whitemagic[<extra>]", err=True)
        ctx.exit(1)

    return unavailable_cmd


def _make_missing_dep_callback(error_msg: str) -> Callable:
    """Create a callback function that shows missing dependency error."""
    def callback(*args, **kwargs):
        """Print a missing-dependency error to stderr and raise ClickException."""
        click.echo("ERROR: This command requires additional dependencies.", err=True)
        click.echo(f"Details: {error_msg}", err=True)
        click.echo("Install with: pip install whitemagic[<extra>]", err=True)
        raise click.ClickException("Missing dependencies")

    return callback


def optional_command(name: str, extra: str | None = None):
    """Decorator for commands with optional dependencies.

    Args:
        name: Command name
        extra: Extra name for pip install (e.g., 'tui', 'rust')

    Usage:
        @optional_command('galaxy', extra='tui')
        def galaxy_cmd():
            from whitemagic.interfaces.tui import GalaxyTUI
            app = GalaxyTUI()
            app.run()
    """
    def decorator(func: Callable) -> click.Command:
        """Wrap func in a Click command that converts ImportError into a friendly hint."""
        @click.command(name=name)
        @click.pass_context
        def wrapper(ctx, *args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ImportError as e:
                click.echo(f"ERROR: This command requires 'whitemagic[{extra}]'", err=True)
                click.echo(f"Install: pip install whitemagic[{extra}]", err=True)
                if extra:
                    click.echo(f"Missing: {e}", err=True)
                ctx.exit(1)

        # Copy function metadata
        wrapper.__doc__ = func.__doc__
        wrapper.__name__ = func.__name__

        return wrapper

    return decorator
