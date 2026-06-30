"""Singleton decorator and registry for test isolation.

This module provides a decorator to register singleton instances and a
centralized reset mechanism for test isolation. Replaces manual conftest
tracking of singleton module-level variables.
"""

# ruff: noqa: BLE001
import functools
import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Global registry of singleton wrappers and module-level vars.
# Format: list of (wrapper_fn | None, module_name | None, var_name | None)
_SINGLETON_REGISTRY: list[tuple[Any, str | None, str | None]] = []
_REGISTRY_LOCK = threading.Lock()


def singleton(var_name: str | None = None) -> Callable[[F], F]:
    """Decorator to register a function as a singleton getter.

    Usage:
        @singleton()
        def get_my_singleton():
            if not hasattr(get_my_singleton, "_instance"):
                get_my_singleton._instance = MyClass()
            return get_my_singleton._instance

    Or with explicit variable name for registry tracking:
        @singleton("_my_instance")
        def get_my_singleton():
            ...

    The decorator tracks the singleton instance in the global registry
    for automated test cleanup via reset_all_singletons().
    """

    def decorator(func: F) -> F:
        """
        Perform the decorator operation.

        Args:
            func: Parameter description.

        Returns:
            F
        """
        module_name = func.__module__
        tracked_var = var_name or f"_{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Perform the wrapper operation.

            Returns:
                Any
            """
            from typing import cast

            w = cast(Any, wrapper)
            if not hasattr(w, "_instance"):
                w._instance = func(*args, **kwargs)
            return w._instance

        # Register wrapper reference AND module var for complete reset coverage
        with _REGISTRY_LOCK:
            _SINGLETON_REGISTRY.append((wrapper, module_name, tracked_var))

        from typing import cast

        return cast(F, wrapper)

    return decorator


def register_singleton(module_name: str, var_name: str, instance: Any) -> None:
    """Manually register a module-level singleton variable in the registry.

    Use this for existing singletons that don't use the @singleton decorator.

    Args:
        module_name: Full module name (e.g., "whitemagic.core.memory.unified")
        var_name: Module-level variable name (e.g., "_unified_memory")
        instance: The singleton instance
    """
    with _REGISTRY_LOCK:
        _SINGLETON_REGISTRY.append((None, module_name, var_name))


def reset_all_singletons() -> None:
    """Reset all registered singletons to None.

    Clears both:
    - @singleton decorator wrapper._instance attributes
    - Module-level variables tracked via register_singleton()

    Should be called in test fixtures to ensure test isolation.
    """
    import importlib

    with _REGISTRY_LOCK:
        for wrapper_fn, module_name, var_name in _SINGLETON_REGISTRY:
            # 1. Clear the decorator's cached _instance
            if wrapper_fn is not None and hasattr(wrapper_fn, "_instance"):
                try:
                    delattr(wrapper_fn, "_instance")
                except AttributeError:
                    pass  # Attribute already absent — harmless
                except Exception as e:
                    logger.debug(
                        "Unexpected error clearing singleton %s: %s",
                        wrapper_fn,
                        e,
                        exc_info=True,
                    )

            # 2. Clear the module-level variable
            if module_name and var_name:
                try:
                    mod = importlib.import_module(module_name)
                    if hasattr(mod, var_name):
                        setattr(mod, var_name, None)
                except (ImportError, ModuleNotFoundError):
                    pass


def get_registered_singletons() -> list[tuple[Any, str | None, str | None]]:
    """Get a copy of the current singleton registry.

    Useful for debugging and testing.

    Returns:
        List of (wrapper_fn, module_name, var_name) tuples
    """
    with _REGISTRY_LOCK:
        return list(_SINGLETON_REGISTRY)
