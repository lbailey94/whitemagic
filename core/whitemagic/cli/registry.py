"""CLI command registration registry.

Provides a plugin-style registration system for optional CLI commands,
reducing tight coupling between boot.py and command modules.
"""

from collections.abc import Callable
from typing import TypeVar

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
