"""File locking utilities with cross-platform fallbacks."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union

try:  # POSIX platforms
    import fcntl  # type: ignore[attr-defined]

    HAS_FCNTL = True
except ImportError:  # pragma: no cover - Windows specific branch
    fcntl = None
    HAS_FCNTL = False

try:  # Windows fallback
    import msvcrt  # type: ignore[attr-defined]

    HAS_MSVCRT = True
except ImportError:  # pragma: no cover - non-Windows platforms
    msvcrt = None
    HAS_MSVCRT = False


@contextmanager
def file_lock(filepath: Union[str, Path], timeout: float = 5.0) -> Generator[None, None, None]:
    """
    Context manager providing an advisory lock on ``filepath``.

    Uses ``fcntl`` on POSIX and ``msvcrt`` on Windows. If neither backend
    exists, the context still yields so callers proceed rather than crash.
    """
    filepath = Path(filepath)
    lock_file = filepath.parent / f".{filepath.name}.lock"

    if HAS_FCNTL:
        lock_file.touch(exist_ok=True)
        fd = None
        try:
            fd = os.open(lock_file, os.O_RDWR | os.O_CREAT)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            if fd is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
        return

    if HAS_MSVCRT:  # pragma: no cover - Windows only
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch(exist_ok=True)
        file_handle = open(lock_file, "a+")
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                file_handle.close()
        return

    # No locking backend available (very rare platform) - degrade gracefully.
    yield


def atomic_write(filepath: Union[str, Path], content: str) -> None:
    """
    Write ``content`` to ``filepath`` atomically via write-then-replace.
    """
    filepath = Path(filepath)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f".{filepath.name}.tmp",
        text=True,
    )
    try:
        os.write(temp_fd, content.encode("utf-8"))
        os.close(temp_fd)
        os.replace(temp_path, filepath)  # overwrite-safe on all major OSes
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
