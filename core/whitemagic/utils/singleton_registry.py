"""Singleton Registry — Automatic singleton tracking and reset for tests.

This module provides a centralized registry for singleton instances,
allowing automatic reset between tests without manual bookkeeping.

Usage:
    from whitemagic.utils.singleton_registry import register_singleton, reset_all_singletons

    # In your singleton getter:
    def get_my_singleton():
        return register_singleton("my_module.MySingleton", lambda: MySingleton())

    # In conftest.py:
    @pytest.fixture(autouse=True)
    def reset_singletons():
        yield
        reset_all_singletons()
"""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class SingletonRegistry:
    """Centralized registry for singleton instances.

    Tracks singleton instances by name and provides a reset mechanism
    for test isolation. New singletons are automatically included in
    test resets without manual bookkeeping.
    """

    _instances: dict[str, Any] = {}
    _factories: dict[str, Callable[[], Any]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[[], Any]) -> Any:
        """Register a singleton factory and return the instance.

        Args:
            name: Unique identifier for the singleton (e.g., "module.ClassName")
            factory: Callable that creates the singleton instance

        Returns:
            The singleton instance (cached or newly created)
        """
        if name in cls._instances:
            return cls._instances[name]

        cls._factories[name] = factory

        # Create and cache instance
        instance = factory()
        cls._instances[name] = instance
        logger.debug("Registered singleton: %s", name)
        return instance

    @classmethod
    def reset(cls, name: str) -> None:
        """Reset a specific singleton by clearing its cached instance.

        Args:
            name: The singleton identifier
        """
        if name in cls._instances:
            del cls._instances[name]
            logger.debug("Reset singleton: %s", name)

    @classmethod
    def reset_all(cls) -> None:
        """Reset all registered singletons.

        Clears all cached instances, forcing them to be recreated on next access.
        """
        count = len(cls._instances)
        cls._instances.clear()
        logger.debug("Reset all %s singletons", count)

    @classmethod
    def get_registered_names(cls) -> list[str]:
        """Get list of all registered singleton names.

        Returns:
            List of singleton identifiers
        """
        return list(cls._factories.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a singleton is registered.

        Args:
            name: The singleton identifier

        Returns:
            True if registered, False otherwise
        """
        return name in cls._factories


def register_singleton(name: str, factory: Callable[[], Any]) -> Any:
    """Convenience function to register a singleton.

    Args:
        name: Unique identifier for the singleton
        factory: Callable that creates the singleton instance

    Returns:
        The singleton instance
    """
    return SingletonRegistry.register(name, factory)


def reset_singleton(name: str) -> None:
    """Convenience function to reset a specific singleton.

    Args:
        name: The singleton identifier
    """
    SingletonRegistry.reset(name)


def reset_all_singletons() -> None:
    """Convenience function to reset all registered singletons."""
    SingletonRegistry.reset_all()


def get_registered_singletons() -> list[str]:
    """Get list of all registered singleton names.

    Returns:
        List of singleton identifiers
    """
    return SingletonRegistry.get_registered_names()
