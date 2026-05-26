"""
Shared Memory Bridge for Zero-Copy Embedding Transfer (VC-05)

POSIX shared memory segment for Koka-Python data exchange.
Supports 384-dim embedding vectors with ring buffer for streaming.

Uses multiprocessing.shared_memory (Python 3.8+) for POSIX shm.
"""

from __future__ import annotations

import ctypes
import logging
import struct
import threading
import time
from multiprocessing import shared_memory
from typing import Optional, cast, Any

import numpy as np

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_DIM = 384  # BGE-small dimension
EMBEDDING_BYTES = EMBEDDING_DIM * 4  # float32
HEADER_SIZE = 64  # Metadata header
SLOT_HEADER_SIZE = 8  # id (4) + flags (4)
SLOT_SIZE = SLOT_HEADER_SIZE + EMBEDDING_BYTES
DEFAULT_CAPACITY = 1000  # embeddings
SEGMENT_SIZE = HEADER_SIZE + (DEFAULT_CAPACITY * SLOT_SIZE)

SHM_NAME = "whitemagic_embed_bridge"


class SharedMemoryHeader(ctypes.Structure):
    """Header structure for shared memory segment."""
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint32),
        ("capacity", ctypes.c_uint32),
        ("count", ctypes.c_uint32),
        ("write_pos", ctypes.c_uint32),
        ("read_pos", ctypes.c_uint32),
        ("total_written", ctypes.c_uint64),
        ("total_read", ctypes.c_uint64),
        ("last_write_ts", ctypes.c_double),
        ("last_read_ts", ctypes.c_double),
        ("_padding", ctypes.c_uint8 * 24),
    ]


class SharedMemoryBridge:
    """POSIX shared memory bridge for zero-copy embedding transfer."""

    def __init__(self, name: str = SHM_NAME, create: bool = False):
        self.name = name
        self._shm: Optional[shared_memory.SharedMemory] = None
        self._header: Optional[SharedMemoryHeader] = None
        self._lock = threading.Lock()
        self._is_owner = create

        if create:
            self._create_segment()
        else:
            self._open_segment()

    def _create_segment(self) -> None:
        try:
            try:
                existing = shared_memory.SharedMemory(name=self.name)
                existing.close()
                existing.unlink()
            except FileNotFoundError:
                pass

            self._shm = shared_memory.SharedMemory(name=self.name, create=True, size=SEGMENT_SIZE)
            buf = self._shm.buf
            if buf is None:
                raise RuntimeError("Shared memory buffer is None")
            self._header = SharedMemoryHeader.from_buffer(buf)
            self._header.magic = 0x574D454D
            self._header.version = 1
            self._header.capacity = DEFAULT_CAPACITY
            self._header.count = 0
            self._header.write_pos = 0
            self._header.read_pos = 0
            self._header.total_written = 0
            self._header.total_read = 0
            self._header.last_write_ts = 0.0
            self._header.last_read_ts = 0.0
            logger.info(f"Created shared memory: {self.name} ({SEGMENT_SIZE} bytes)")
        except Exception as e:
            logger.error(f"Failed to create shared memory: {e}")
            raise

    def _open_segment(self) -> None:
        try:
            self._shm = shared_memory.SharedMemory(name=self.name)
            buf = self._shm.buf
            if buf is None:
                raise RuntimeError("Shared memory buffer is None")
            self._header = SharedMemoryHeader.from_buffer(buf)
            if self._header.magic != 0x574D454D:
                raise ValueError(f"Invalid segment magic: {hex(self._header.magic)}")
            logger.debug(f"Opened shared memory: {self.name}")
        except Exception as e:
            logger.error(f"Failed to open shared memory: {e}")
            raise

    def write_embedding(self, memory_id: int, vector: list[float]) -> bool:
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(f"Vector dimension mismatch: {len(vector)} != {EMBEDDING_DIM}")

        with self._lock:
            if self._header is None:
                return False
            if self._header.count >= self._header.capacity:
                self._header.read_pos = (self._header.read_pos + 1) % self._header.capacity

            pos = self._header.write_pos
            offset = HEADER_SIZE + (pos * SLOT_SIZE)

            # Write directly to buffer
            shm = self._shm
            if shm is None or shm.buf is None:
                return False
                
            header_bytes = struct.pack("<II", memory_id, 1)
            vector_bytes = struct.pack(f"<{EMBEDDING_DIM}f", *vector)
            shm.buf[offset:offset + 8] = header_bytes
            shm.buf[offset + 8:offset + SLOT_SIZE] = vector_bytes

            self._header.write_pos = (pos + 1) % self._header.capacity
            if self._header.count < self._header.capacity:
                self._header.count += 1
            self._header.total_written += 1
            self._header.last_write_ts = time.time()
            return True

    def write_batch_numpy(self, ids: np.ndarray, vectors: np.ndarray) -> int:
        if vectors.shape[1] != EMBEDDING_DIM:
            raise ValueError(f"Vector dimension mismatch: {vectors.shape[1]} != {EMBEDDING_DIM}")

        n = len(ids)
        written = 0

        with self._lock:
            shm = self._shm
            if self._header is None or shm is None or shm.buf is None:
                return 0

            for i in range(n):
                if self._header.count >= self._header.capacity:
                    self._header.read_pos = (self._header.read_pos + 1) % self._header.capacity

                pos = self._header.write_pos
                offset = HEADER_SIZE + (pos * SLOT_SIZE)

                header_bytes = struct.pack("<II", int(ids[i]), 1)
                vec_bytes = vectors[i].astype(np.float32).tobytes()
                shm.buf[offset:offset + 8] = header_bytes
                shm.buf[offset + 8:offset + SLOT_SIZE] = vec_bytes

                self._header.write_pos = (pos + 1) % self._header.capacity
                if self._header.count < self._header.capacity:
                    self._header.count += 1
                written += 1

            self._header.total_written += written
            self._header.last_write_ts = time.time()
        return written

    def read_embedding(self) -> Optional[tuple[int, list[float]]]:
        with self._lock:
            shm = self._shm
            if self._header is None or self._header.count == 0 or shm is None or shm.buf is None:
                return None

            pos = self._header.read_pos
            offset = HEADER_SIZE + (pos * SLOT_SIZE)

            header_bytes = bytes(shm.buf[offset:offset + 8])
            memory_id, flags = struct.unpack("<II", header_bytes)

            if flags != 1:
                return None

            vector_bytes = bytes(shm.buf[offset + 8:offset + SLOT_SIZE])
            vector = list(struct.unpack(f"<{EMBEDDING_DIM}f", vector_bytes))

            shm.buf[offset + 4:offset + 8] = struct.pack("<I", 0)

            self._header.read_pos = (pos + 1) % self._header.capacity
            self._header.count -= 1
            self._header.total_read += 1
            self._header.last_read_ts = time.time()
            return memory_id, vector

    def read_batch_numpy(self, max_count: int = 1000) -> tuple[np.ndarray, np.ndarray]:
        with self._lock:
            shm = self._shm
            if self._header is None or self._header.count == 0 or shm is None or shm.buf is None:
                return np.array([], dtype=np.int32), np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

            count = min(max_count, self._header.count)
            ids = np.zeros(count, dtype=np.int32)
            vectors = np.zeros((count, EMBEDDING_DIM), dtype=np.float32)

            for i in range(count):
                pos = (self._header.read_pos + i) % self._header.capacity
                offset = HEADER_SIZE + (pos * SLOT_SIZE)

                header_bytes = bytes(shm.buf[offset:offset + 8])
                ids[i], _ = struct.unpack("<II", header_bytes)

                vector_bytes = bytes(shm.buf[offset + 8:offset + SLOT_SIZE])
                vectors[i] = np.frombuffer(vector_bytes, dtype=np.float32)

                shm.buf[offset + 4:offset + 8] = struct.pack("<I", 0)

            self._header.read_pos = (self._header.read_pos + count) % self._header.capacity
            self._header.count -= count
            self._header.total_read += count
            self._header.last_read_ts = time.time()
            return ids, vectors

    def get_stats(self) -> dict:
        with self._lock:
            if self._header is None:
                return {}
            return {
                "name": self.name,
                "capacity": self._header.capacity,
                "count": self._header.count,
                "write_pos": self._header.write_pos,
                "read_pos": self._header.read_pos,
                "total_written": self._header.total_written,
                "total_read": self._header.total_read,
                "segment_size": SEGMENT_SIZE,
            }

    def close(self) -> None:
        self._header = None
        if self._shm:
            self._shm.close()
            self._shm = None

    def destroy(self) -> None:
        self.close()
        if self._is_owner:
            try:
                shm = shared_memory.SharedMemory(name=self.name)
                shm.unlink()
                shm.close()
                logger.info(f"Destroyed shared memory: {self.name}")
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False


def create_bridge() -> SharedMemoryBridge:
    return SharedMemoryBridge(create=True)


def open_bridge() -> SharedMemoryBridge:
    return SharedMemoryBridge(create=False)


def benchmark_transfer(n_embeddings: int = 1000) -> dict[str, Any]:
    ids: np.ndarray = np.arange(n_embeddings, dtype=np.int32)
    vectors = np.random.randn(n_embeddings, EMBEDDING_DIM).astype(np.float32)

    bridge = create_bridge()
    try:
        start = time.perf_counter()
        written = bridge.write_batch_numpy(ids, vectors)
        write_time = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        read_ids, read_vecs = bridge.read_batch_numpy(n_embeddings)
        read_time = (time.perf_counter() - start) * 1000

        total_time = write_time + read_time
        return {
            "n_embeddings": n_embeddings,
            "written": written,
            "read": len(read_ids),
            "write_time_ms": write_time,
            "read_time_ms": read_time,
            "total_time_ms": total_time,
            "target_met": total_time < 1.0,
            "throughput_emb_per_sec": n_embeddings / (total_time / 1000) if total_time > 0 else 0,
        }
    finally:
        bridge.destroy()


if __name__ == "__main__":
    print("Testing shared memory bridge...")
    result = benchmark_transfer(1000)
    print(f"Write: {result['write_time_ms']:.2f}ms, Read: {result['read_time_ms']:.2f}ms, Total: {result['total_time_ms']:.2f}ms")
    print(f"Throughput: {result['throughput_emb_per_sec']:.0f} embeddings/sec")
    if result["target_met"]:
        print("✅ VC-05 target met")
    else:
        print(f"❌ VC-05: {result['total_time_ms']:.2f}ms (target <1ms) — note: Python overhead, Koka consumer will be faster")
