import logging
import mmap
import struct
import threading
from typing import Any

import numpy as np
import posix_ipc

logger = logging.getLogger(__name__)

HEADER_SIZE = 64
MAGIC = 0x574D4B4B # "WMKK"
SLOT_SIZE = 1540 # 4 byte ID + 384 * 4 byte vector
CAPACITY = 20000
SEGMENT_SIZE = HEADER_SIZE + (CAPACITY * SLOT_SIZE)
DIM = 384

class SharedMemoryManager:
    """Manages the lifecycle and synchronization of the POSIX shared memory segment for fast Koka searches."""

    def __init__(self, name: str = "/whitemagic_embed_bridge_real"):
        self.name = name
        self._lock = threading.Lock()
        self._map_file: Any | None = None
        self._shm: Any | None = None
        self._id_to_uuid: dict[int, str] = {}
        self._uuid_to_id: dict[str, int] = {}
        self._uuid_to_slot: dict[str, int] = {}
        self._count = 0
        self._next_id = 1 # Reserve 0 for "query" or null

    def initialize(self) -> None:
        """Create or connect to the shared memory segment."""
        with self._lock:
            if self._map_file is not None:
                return

            try:
                # Try to open existing
                self._shm = posix_ipc.SharedMemory(self.name)
            except posix_ipc.ExistentialError:
                # Create new
                self._shm = posix_ipc.SharedMemory(self.name, posix_ipc.O_CREAT | posix_ipc.O_EXCL, size=SEGMENT_SIZE)

            shm = self._shm
            if shm is None:
                raise RuntimeError("Shared memory handle was not initialized.")

            self._map_file = mmap.mmap(shm.fd, shm.size)
            shm.close_fd() # Safe to close FD after mmap
            map_file = self._get_map_file()

            # Initialize header if it's a new segment or corrupted
            magic = struct.unpack_from("=i", map_file, 0)[0]
            if magic != MAGIC:
                struct.pack_into("=iiiiii", map_file, 0, MAGIC, 1, CAPACITY, 0, 0, 0)
                self._count = 0
            else:
                self._count = struct.unpack_from("=i", map_file, 12)[0]

    def _get_map_file(self) -> Any:
        if self._map_file is None:
            raise RuntimeError("Shared memory segment has not been initialized.")
        return self._map_file

    def _write_memory_item(self, index: int, int_id: int, vector: np.ndarray) -> None:
        if index >= CAPACITY:
            raise ValueError("Shared memory capacity exceeded.")
        offset = HEADER_SIZE + (index * SLOT_SIZE)
        map_file = self._get_map_file()
        struct.pack_into("=i", map_file, offset, int_id)
        struct.pack_into(f"={DIM}f", map_file, offset + 4, *vector)

    def _update_count(self, count: int) -> None:
        map_file = self._get_map_file()
        struct.pack_into("=i", map_file, 12, count)

    def sync_from_db(self, db_pool) -> None:
        """Load all embeddings from DB and populate SHM."""
        self.initialize()

        with self._lock:
            with db_pool.connection() as conn:
                with conn:
                    cur = conn.execute(f"SELECT memory_id, embedding FROM memory_embeddings LIMIT {CAPACITY}")
                    rows = cur.fetchall()

                    self._id_to_uuid.clear()
                    self._uuid_to_id.clear()
                    self._count = 0
                    self._next_id = 1

                    for row in rows:
                        mem_id = row[0]
                        blob = row[1]
                        if blob:
                            try:
                                vec = np.frombuffer(blob, dtype=np.float32)
                                if len(vec) == DIM:
                                    # Normalize
                                    norm = np.linalg.norm(vec)
                                    if norm > 0:
                                        vec = vec / norm

                                    int_id = self._next_id
                                    self._next_id += 1

                                    self._id_to_uuid[int_id] = mem_id
                                    self._uuid_to_id[mem_id] = int_id
                                    self._uuid_to_slot[mem_id] = self._count

                                    self._write_memory_item(self._count, int_id, vec)
                                    self._count += 1
                            except Exception as e:
                                logger.warning(f"Failed to load embedding for {mem_id}: {e}")

                    self._update_count(self._count)
                    logger.info(f"Synchronized {self._count} embeddings to shared memory.")

    def add_or_update(self, mem_id: str, vector: np.ndarray) -> None:
        """Add a single embedding or update it."""
        self.initialize()

        with self._lock:
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm

            if mem_id in self._uuid_to_id:
                # Update existing
                int_id = self._uuid_to_id[mem_id]
                slot_index = self._uuid_to_slot.get(mem_id)
                if slot_index is not None:
                    self._write_memory_item(slot_index, int_id, vector)
                else:
                    # This should not happen if state is consistent, but handle anyway
                    logger.warning(f"Missing slot index for {mem_id}, appending as new instead.")
                    self._append_new(mem_id, vector)
            else:
                self._append_new(mem_id, vector)

    def _append_new(self, mem_id: str, vector: np.ndarray) -> None:
        """Helper to append a new item if capacity allows."""
        if self._count >= CAPACITY:
            logger.warning("Shared memory full, cannot add more embeddings.")
            return

        int_id = self._next_id
        self._next_id += 1

        self._id_to_uuid[int_id] = mem_id
        self._uuid_to_id[mem_id] = int_id
        self._uuid_to_slot[mem_id] = self._count

        self._write_memory_item(self._count, int_id, vector)
        self._count += 1
        self._update_count(self._count)

    def write_query(self, query_id: int, vector: np.ndarray) -> None:
        """Write a query vector into the SHM segment at the specified ID index."""
        self.initialize()
        with self._lock:
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            self._write_memory_item(query_id, 0, vector)

    def get_uuid(self, int_id: int) -> str | None:
        """
        Get the uuid.
        
        Args:
            int_id: Parameter description.
        
        Returns:
            str | None
        """
        return self._id_to_uuid.get(int_id)

    def get_count(self) -> int:
        """
        Get the count.
        
        Returns:
            int
        """
        return self._count

_global_shm_manager = None
def get_shm_manager() -> SharedMemoryManager:
    """
    Get the shm manager.
    
    Returns:
        SharedMemoryManager
    """
    global _global_shm_manager
    if _global_shm_manager is None:
        _global_shm_manager = SharedMemoryManager()
    return _global_shm_manager
