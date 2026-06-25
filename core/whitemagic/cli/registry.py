"""CLI command registration registry.

Provides a plugin-style registration system for optional CLI commands,
reducing tight coupling between boot.py and command modules.
"""

from collections.abc import Callable
from typing import TypeVar

import click

T = TypeVar("T")


class CommandRegistry:
    """Registry for optional CLI commands with lazy loading."""

    def __init__(self):
        self._registrations: dict[str, Callable] = {}

    def register(self, name: str, import_path: str, func_name: str | None = None) -> Callable:
        """Register an optional command for lazy loading.

        Args:
            name: Command name
            import_path: Module import path
            func_name: Function name in module (defaults to module's CLI group)
        """
        def decorator(func: Callable) -> Callable:
            def loader():
                try:
                    module = __import__(import_path, fromlist=[func_name] if func_name else None)
                    if func_name:
                        return getattr(module, func_name)
                    return module
                except ImportError:
                    return None

            self._registrations[name] = loader
            return func

        return decorator

    def load(self, name: str) -> T | None:
        """Load a registered command."""
        loader = self._registrations.get(name)
        if loader:
            return loader()
        return None

    def all_names(self) -> list[str]:
        """Get all registered command names."""
        return list(self._registrations.keys())


# Global registry instance
_registry = CommandRegistry()


def register_optional_command(name: str, import_path: str, func_name: str | None = None) -> Callable:
    """Decorator to register an optional CLI command."""
    return _registry.register(name, import_path, func_name)


def get_optional_command(name: str) -> T | None:
    """Get an optional command by name."""
    return _registry.load(name)


def list_optional_commands() -> list[str]:
    """List all registered optional commands."""
    return _registry.all_names()


def register_optional(
    main_group: click.Group,
    name: str,
    import_path: str,
    func_name: str | None = None,
    *,
    cli_name: str | None = None,
    warn_on_fail: bool = False,
) -> bool:
    """Register an optional CLI command group with graceful degradation.

    Replaces the try/except ImportError boilerplate in boot.py.

    Args:
        main_group: Click group to add the command to
        name: Internal name for logging
        import_path: Dotted module path to import
        func_name: Attribute name in module (defaults to module itself)
        cli_name: Override CLI command name (defaults to auto from the command)
        warn_on_fail: If True, print a warning on ImportError
    Returns:
        True if registered, False if import failed
    """
    try:
        module = __import__(import_path, fromlist=[func_name] if func_name else None)
        cmd = getattr(module, func_name) if func_name else module
        if cli_name:
            main_group.add_command(cmd, name=cli_name)
        else:
            main_group.add_command(cmd)
        return True
    except (ImportError, ModuleNotFoundError) as e:
        if warn_on_fail:
            try:
                from rich.console import Console
                Console().print(f"[yellow]Warning: Failed to load {name}: {e}[/yellow]")
            except ImportError:
                click.echo(f"Warning: Failed to load {name}: {e}", err=True)
        return False
