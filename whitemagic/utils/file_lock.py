"""File locking utilities for thread-safe file operations."""
import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union


@contextmanager
def file_lock(filepath: Union[str, Path], timeout: float = 5.0) -> Generator[None, None, None]:
    """
    Context manager for file-based locking.
    
    Uses fcntl for advisory file locking to prevent concurrent modifications.
    
    Args:
        filepath: Path to file to lock
        timeout: Timeout in seconds (not implemented, uses blocking)
    
    Yields:
        None
    
    Example:
        >>> with file_lock("metadata.json"):
        ...     # Safe to read/write metadata.json
        ...     pass
    """
    filepath = Path(filepath)
    lock_file = filepath.parent / f".{filepath.name}.lock"
    
    # Create lock file if it doesn't exist
    lock_file.touch(exist_ok=True)
    
    fd = None
    try:
        fd = os.open(lock_file, os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)  # Exclusive lock
        yield
    finally:
        if fd is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)  # Release lock
            os.close(fd)


def atomic_write(filepath: Union[str, Path], content: str) -> None:
    """
    Write file atomically using write-then-rename pattern.
    
    Args:
        filepath: Destination path
        content: Content to write
    
    Example:
        >>> atomic_write("metadata.json", json.dumps(data))
    """
    filepath = Path(filepath)
    
    # Write to temporary file in same directory
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f".{filepath.name}.tmp",
        text=True
    )
    
    try:
        # Write content
        os.write(temp_fd, content.encode('utf-8'))
        os.close(temp_fd)
        
        # Atomic rename (POSIX guarantees atomicity)
        os.rename(temp_path, filepath)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
