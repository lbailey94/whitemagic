"""File locking - cross-platform."""
import os, tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

@contextmanager
def file_lock(filepath: Union[str, Path], timeout: float = 5.0) -> Generator[None, None, None]:
    if not HAS_FCNTL:
        yield
        return
    filepath = Path(filepath)
    lock_file = filepath.parent / f".{filepath.name}.lock"
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

def atomic_write(filepath: Union[str, Path], content: str) -> None:
    filepath = Path(filepath)
    temp_fd, temp_path = tempfile.mkstemp(dir=filepath.parent, prefix=f".{filepath.name}.tmp", text=True)
    try:
        os.write(temp_fd, content.encode('utf-8'))
        os.close(temp_fd)
        os.rename(temp_path, filepath)
    except Exception:
        try: os.unlink(temp_path)
        except OSError: pass
        raise
