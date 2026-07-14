# ruff: noqa: BLE001
"""
Unified FFI Bridge Utilities
Provides common functionality for loading and managing foreign language libraries.
"""

import ctypes
import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def find_library(
    lib_name: str,
    base_path: Path | None = None,
    env_var: str | None = None,
    search_paths: list[str] | None = None,
) -> str | None:
    """
    Locate a compiled shared library.

    Args:
        lib_name: Name of the library (e.g., 'libwhitemagic.so')
        base_path: Base directory to search from
        env_var: Environment variable to check for library path
        search_paths: Additional search paths relative to base_path

    Returns:
        Path to the library if found, None otherwise
    """
    if env_var:
        env_path = os.environ.get(env_var, "")
        if env_path and os.path.isfile(env_path):
            return env_path

    # Determine base path
    if base_path is None:
        base_path = Path(__file__).resolve().parent.parent.parent.parent

    # Build search candidates
    candidates = []
    if search_paths:
        for rel_path in search_paths:
            candidates.append(str(base_path / rel_path))

    # Common library names
    extensions = [".so", ".dylib", ".dll"]
    for ext in extensions:
        candidates.append(str(base_path / (lib_name + ext)))
        candidates.append(str(base_path / "zig-out" / "lib" / (lib_name + ext)))

    # Search for first match
    for path in candidates:
        if path and os.path.isfile(path):
            return path

    return None


class LibraryLoader:
    """
    Thread-safe library loader with lazy initialization and fallback support.
    """

    def __init__(
        self,
        lib_name: str,
        base_path: Path | None = None,
        env_var: str | None = None,
        search_paths: list[str] | None = None,
        setup_function: Callable[[Any], None] | None = None,
    ):
        """
        Initialize the library loader.

        Args:
            lib_name: Name of the library to load
            base_path: Base directory to search from
            env_var: Environment variable for library path
            search_paths: Additional search paths
            setup_function: Optional function to call after loading to set up FFI signatures
        """
        self.lib_name = lib_name
        self.base_path = base_path
        self.env_var = env_var
        self.search_paths = search_paths or []
        self.setup_function = setup_function

        self._lib: Any | None = None
        self._lock = threading.RLock()
        self._available = False

    def _find_library(self) -> str | None:
        """Find the library using configured search paths."""
        return find_library(
            self.lib_name,
            self.base_path,
            self.env_var,
            self.search_paths,
        )

    def load(self) -> Any | None:
        """
        Load the library (lazy initialization).

        Returns:
            Loaded library or None if not available
        """
        if self._lib is not None:
            return self._lib

        with self._lock:
            if self._lib is not None:
                return self._lib

            path = self._find_library()
            if not path:
                logger.debug("Library %s not found", self.lib_name)
                self._available = False
                return None

            try:
                lib = ctypes.CDLL(path)
                if self.setup_function:
                    self.setup_function(lib)
                self._lib = lib
                self._available = True
                logger.info("Library %s loaded from: %s", self.lib_name, path)
                return lib
            except Exception as e:
                logger.warning(
                    "Failed to load library %s: %s", self.lib_name, e, exc_info=True
                )
                self._available = False
                return None

    @property
    def available(self) -> bool:
        """Check if library is available."""
        if self._lib is None:
            self.load()
        return self._available

    @property
    def lib(self) -> Any | None:
        """Get the loaded library."""
        return self.load()


def create_string_buffer(text: str) -> ctypes.Array:
    """Create a ctypes string buffer from text."""
    return ctypes.create_string_buffer(text.encode("utf-8"))


def create_output_buffer(size: int) -> ctypes.Array:
    """Create an output buffer of specified size."""
    return (ctypes.c_ubyte * size)()


def parse_null_separated_output(buffer: bytes, max_items: int = 100) -> list[str]:
    """
    Parse null-separated strings from a buffer.

    Args:
        buffer: Raw bytes from FFI call
        max_items: Maximum number of items to return

    Returns:
        List of parsed strings
    """
    result = []
    for item_bytes in buffer.split(b"\x00"):
        if not item_bytes:
            continue
        try:
            item = item_bytes.decode("utf-8", errors="replace").strip()
            if item:
                result.append(item)
                if len(result) >= max_items:
                    break
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            continue
    return result
