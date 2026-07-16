"""Python bridge to Rust shared-memory ring buffers.

Provides send/recv operations for inter-trigram communication from
Python code (e.g., MCP dispatch → trigram threads). Prefers Rust PyO3
bindings when available, falls back to pure Python mmap implementation.

Usage::

    from whitemagic.inference.ring_buffer_bridge import RingBufferBridge

    # Producer side
    with RingBufferBridge("qian_to_li", create=True) as rb:
        rb.send_json({"prompt": "hello", "max_tokens": 64})

    # Consumer side
    with RingBufferBridge("qian_to_li") as rb:
        msg = rb.recv_json()
"""

from __future__ import annotations

import json
import logging
import mmap
import os
import struct
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SHM_DIR = os.environ.get("WM_TRIGRAM_SHM_DIR", "/dev/shm")
DEFAULT_CAPACITY = int(os.environ.get("WM_TRIGRAM_RB_CAP", str(1024 * 1024)))
HEADER_SIZE = 64
MAGIC = 0x574D5F52420001  # "WM_RB" + 0001

# Header layout (must match Rust ring_buffer.rs):
#   offset 0:  magic (u64, 8 bytes)
#   offset 8:  capacity (u64, 8 bytes)
#   offset 16: element_size (u64, 8 bytes)
#   offset 24: write_pos (u64, 8 bytes) — atomic
#   offset 32: read_pos (u64, 8 bytes) — atomic
#   offset 40: padding (24 bytes)


class RingBufferBridge:
    """Python bridge to a shared-memory SPSC ring buffer.

    Wraps the Rust RingBuffer via PyO3 when available, or falls back
    to a pure Python mmap implementation with the same wire format.

    Supports variable-length messages with 4-byte LE length prefix.
    """

    def __init__(
        self,
        name: str,
        create: bool = False,
        capacity: int = DEFAULT_CAPACITY,
    ) -> None:
        self._name = name
        self._shm_path = Path(SHM_DIR) / f"wm_trigram_{name}"
        self._use_rust = self._check_rust()
        self._rb: Any = None
        self._mmap: mmap.mmap | None = None
        self._fd: int | None = None
        self._capacity: int = capacity
        self._lock: threading.Lock = threading.Lock()

        if self._use_rust:
            try:
                import whitemagic_rs

                wmi = whitemagic_rs.inference
                if create:
                    self._rb = wmi.ring_buffer_create(name, capacity)
                else:
                    self._rb = wmi.ring_buffer_open(name)
                logger.debug("RingBufferBridge '%s': using Rust backend", name)
            except Exception as e:
                logger.debug("Rust ring buffer unavailable, falling back to Python: %s", e)
                self._use_rust = False

        if not self._use_rust:
            if create:
                self._create_python_rb(capacity)
            else:
                self._open_python_rb()

    def _check_rust(self) -> bool:
        try:
            import whitemagic_rs

            wmi = whitemagic_rs.inference
            return hasattr(wmi, "ring_buffer_create")
        except (ImportError, AttributeError):
            return False

    def _create_python_rb(self, capacity: int) -> None:
        """Create a new shared memory ring buffer using Python mmap."""
        if self._shm_path.exists():
            raise FileExistsError(f"Ring buffer already exists: {self._shm_path}")

        total_size = HEADER_SIZE + capacity
        fd = os.open(str(self._shm_path), os.O_CREAT | os.O_RDWR, 0o666)
        os.ftruncate(fd, total_size)

        self._mmap = mmap.mmap(fd, total_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        self._fd = fd
        self._capacity = capacity

        # Initialize header
        struct.pack_into("<Q", self._mmap, 0, MAGIC)
        struct.pack_into("<Q", self._mmap, 8, capacity)
        struct.pack_into("<Q", self._mmap, 16, 0)  # element_size = 0 (variable)
        struct.pack_into("<Q", self._mmap, 24, 0)  # write_pos
        struct.pack_into("<Q", self._mmap, 32, 0)  # read_pos

        logger.debug("RingBufferBridge '%s': created Python mmap (%d bytes)", self._name, total_size)

    def _open_python_rb(self) -> None:
        """Open an existing shared memory ring buffer using Python mmap."""
        if not self._shm_path.exists():
            raise FileNotFoundError(f"Ring buffer not found: {self._shm_path}")

        # Read header to get capacity
        with open(self._shm_path, "rb") as f:
            header = f.read(HEADER_SIZE)

        magic = struct.unpack_from("<Q", header, 0)[0]
        if magic != MAGIC:
            raise ValueError(f"Invalid magic number in ring buffer: {magic:#x}")

        capacity = struct.unpack_from("<Q", header, 8)[0]
        total_size = HEADER_SIZE + capacity

        fd = os.open(str(self._shm_path), os.O_RDWR)
        self._mmap = mmap.mmap(fd, total_size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE)
        self._fd = fd
        self._capacity = capacity

        logger.debug("RingBufferBridge '%s': opened Python mmap (%d bytes)", self._name, total_size)

    def send(self, data: bytes) -> bool:
        """Send raw bytes through the ring buffer.

        Args:
            data: Bytes to send.

        Returns:
            True if sent, False if buffer is full.
        """
        if self._use_rust and self._rb is not None:
            return self._rb.try_write(data)

        return self._python_try_write(data)

    def recv(self) -> bytes | None:
        """Receive raw bytes from the ring buffer.

        Returns:
            Bytes if a message was available, None if empty.
        """
        if self._use_rust and self._rb is not None:
            result = self._rb.try_read()
            if result is not None:
                return bytes(result)
            return None

        return self._python_try_read()

    def send_str(self, msg: str) -> bool:
        """Send a UTF-8 string message."""
        return self.send(msg.encode("utf-8"))

    def recv_str(self) -> str | None:
        """Receive a UTF-8 string message."""
        data = self.recv()
        if data is not None:
            return data.decode("utf-8")
        return None

    def send_json(self, obj: dict[str, Any]) -> bool:
        """Send a JSON-serializable dict."""
        return self.send_str(json.dumps(obj))

    def recv_json(self) -> dict[str, Any] | None:
        """Receive a JSON dict."""
        text = self.recv_str()
        if text is not None:
            return json.loads(text)
        return None

    def fill_level(self) -> float:
        """Return fill level as a fraction (0.0 to 1.0)."""
        if self._use_rust and self._rb is not None:
            return self._rb.fill_level()

        if self._mmap is None:
            return 0.0

        write_pos = struct.unpack_from("<Q", self._mmap, 24)[0]
        read_pos = struct.unpack_from("<Q", self._mmap, 32)[0]
        cap = self._capacity

        if write_pos >= read_pos:
            used = write_pos - read_pos
        else:
            used = cap - read_pos + write_pos

        return used / cap if cap > 0 else 0.0

    def available(self) -> int:
        """Return number of bytes available to read."""
        if self._use_rust and self._rb is not None:
            return self._rb.available()

        if self._mmap is None:
            return 0

        write_pos = struct.unpack_from("<Q", self._mmap, 24)[0]
        read_pos = struct.unpack_from("<Q", self._mmap, 32)[0]
        cap = self._capacity

        if write_pos >= read_pos:
            return write_pos - read_pos
        return cap - read_pos + write_pos

    @property
    def name(self) -> str:
        """Buffer name."""
        return self._name

    @property
    def is_rust_backend(self) -> bool:
        """True if using Rust PyO3 backend."""
        return self._use_rust

    def _python_try_write(self, data: bytes) -> bool:
        """Write variable-length data using Python mmap."""
        if self._mmap is None:
            return False

        cap = self._capacity
        msg_len = 4 + len(data)
        if msg_len > cap:
            return False

        with self._lock:
            write_pos = struct.unpack_from("<Q", self._mmap, 24)[0]
            read_pos = struct.unpack_from("<Q", self._mmap, 32)[0]

            if write_pos >= read_pos:
                available = cap - (write_pos - read_pos)
            else:
                available = read_pos - write_pos

            if available <= msg_len:
                return False

            # Write length prefix
            len_bytes = struct.pack("<I", len(data))
            for i, byte in enumerate(len_bytes):
                self._mmap[HEADER_SIZE + (write_pos + i) % cap] = byte

            # Write data
            for i, byte in enumerate(data):
                self._mmap[HEADER_SIZE + (write_pos + 4 + i) % cap] = byte

            # Update write position
            new_write_pos = (write_pos + msg_len) % cap
            struct.pack_into("<Q", self._mmap, 24, new_write_pos)

        return True

    def _python_try_read(self) -> bytes | None:
        """Read variable-length data using Python mmap."""
        if self._mmap is None:
            return None

        cap = self._capacity

        with self._lock:
            write_pos = struct.unpack_from("<Q", self._mmap, 24)[0]
            read_pos = struct.unpack_from("<Q", self._mmap, 32)[0]

            if write_pos == read_pos:
                return None

            # Read length prefix
            len_bytes = bytes(
                self._mmap[HEADER_SIZE + (read_pos + i) % cap] for i in range(4)
            )
            msg_len = struct.unpack("<I", len_bytes)[0]
            total_len = 4 + msg_len

            # Read data
            data = bytes(
                self._mmap[HEADER_SIZE + (read_pos + 4 + i) % cap] for i in range(msg_len)
            )

            # Update read position
            new_read_pos = (read_pos + total_len) % cap
            struct.pack_into("<Q", self._mmap, 32, new_read_pos)

        return data

    def close(self) -> None:
        """Close the ring buffer and release resources."""
        if self._use_rust and self._rb is not None:
            try:
                self._rb.close()
            except Exception:
                pass
            self._rb = None
        else:
            if self._mmap is not None:
                self._mmap.close()
                self._mmap = None
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None

    def __enter__(self) -> RingBufferBridge:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()
