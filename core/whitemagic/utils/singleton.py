"""Thread-safe singleton pattern — replaces 9 duplicate __new__ implementations.

Usage:
    @threadsafe_singleton
    class MyClass:
        def __init__(self):
            # Called once on first instantiation
            ...

The decorator handles:
- Thread-safe instance creation (double-checked locking)
- Preventing re-initialization on subsequent calls
- Setting `_initialized = False` before first `__init__`
"""

from __future__ import annotations

import threading
from typing import Any, TypeVar

T = TypeVar("T")


def threadsafe_singleton(cls: type[T]) -> type[T]:  # noqa: UP047  # TypeVar-based generics (not yet PEP 695)
    """Decorator that makes a class a thread-safe singleton.

    Replaces the boilerplate:
        _instance = None
        _lock = threading.RLock()
        def __new__(cls):
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                return cls._instance
    """
    original_new = cls.__new__
    original_init = cls.__init__
    cls._lock = threading.RLock()
    cls._instance = None  # type: ignore[attr-defined]

    def _new(newcls: Any, *args: Any, **kwargs: Any) -> Any:
        if newcls._instance is None:
            with newcls._lock:
                if newcls._instance is None:
                    newcls._instance = original_new(newcls)
                    newcls._instance._initialized = False
        return newcls._instance

    def _init(self: Any, *args: Any, **kwargs: Any) -> None:
        if getattr(self, "_initialized", False):
            return
        original_init(self, *args, **kwargs)
        self._initialized = True

    cls.__new__ = _new  # type: ignore[method-assign]
    cls.__init__ = _init  # type: ignore[method-assign]
    return cls
