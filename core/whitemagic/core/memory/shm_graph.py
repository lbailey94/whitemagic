import logging
import mmap
import struct
import threading

import posix_ipc  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# SHM Layout for Graph Topology:
# Header: 64 bytes
# [0:4] MAGIC (0x47525048) "GRPH"
# [4:8] Version (1)
# [8:12] Capacity Edges
# [12:16] Count Edges
# ... reserved ...

# Edge Slot: 16 bytes
# [0:4] Source ID (int32 mapped)
# [4:8] Target ID (int32 mapped)
# [8:12] Weight / Strength (float32)
# [12:16] Edge Type Enum (int32)

MAGIC = 0x47525048
HEADER_SIZE = 64
SLOT_SIZE = 16
CAPACITY_EDGES = 3_000_000
SEGMENT_SIZE = HEADER_SIZE + (CAPACITY_EDGES * SLOT_SIZE)

class SHMGraphTopology:
    """SHMGraphTopology: shm graph topology."""
    def __init__(self, name: str = "/whitemagic_graph_bridge"):
        self.name = name
        self._lock = threading.Lock()
        self._map_file: mmap.mmap | None = None
        self._shm: posix_ipc.SharedMemory | None = None
        self._count = 0
        self.uuid_to_id: dict[str, int] = {}
        self.id_to_uuid: dict[int, str] = {}
        self._next_id = 1

    def _get_or_create_id(self, uuid_str: str) -> int:
        if uuid_str not in self.uuid_to_id:
            self.uuid_to_id[uuid_str] = self._next_id
            self.id_to_uuid[self._next_id] = uuid_str
            self._next_id += 1
        return int(self.uuid_to_id[uuid_str])

    def initialize(self) -> None:

        """
        Perform the initialize operation.
        
        Returns:
            None
        """
        with self._lock:
            if self._map_file is not None:
                return
            try:
                shm = posix_ipc.SharedMemory(self.name)
                self._shm = shm
            except posix_ipc.ExistentialError:
                shm = posix_ipc.SharedMemory(self.name, posix_ipc.O_CREAT | posix_ipc.O_EXCL, size=SEGMENT_SIZE)
                self._shm = shm

            if self._shm is None:
                logger.error("Failed to initialize shared memory")
                return

            self._map_file = mmap.mmap(self._shm.fd, self._shm.size)

            if self._map_file is None:
                return

            magic = struct.unpack_from("=i", self._map_file, 0)[0]
            if self._map_file is None:
                return
            with self._lock:
                if self._map_file is None:
                    return
                if magic != MAGIC:
                    struct.pack_into("=iiii", self._map_file, 0, MAGIC, 1, CAPACITY_EDGES, 0)
                    self._count = 0
                else:
                    self._count = struct.unpack_from("=i", self._map_file, 12)[0]

    def sync_from_db(self, db_pool) -> None:
        """Load topology from DB."""
        self.initialize()
        with self._lock:
            # Re-check map file after lock acquisition
            mmap_file = self._map_file
            if mmap_file is None:
                logger.error("Map file not initialized for sync")
                return

            with db_pool.connection() as conn:
                with conn:
                    # Let's get all edges
                    cur = conn.execute("SELECT source_id, target_id, strength FROM associations")
                    rows = cur.fetchall()

                    self._count = 0
                    self.uuid_to_id.clear()
                    self.id_to_uuid.clear()
                    self._next_id = 1

                    for row in rows:
                        src_id = self._get_or_create_id(row[0])
                        tgt_id = self._get_or_create_id(row[1])

                        weight = row[2] or 1.0
                        offset = HEADER_SIZE + (self._count * SLOT_SIZE)
                        struct.pack_into("=iifi", mmap_file, offset, src_id, tgt_id, float(weight), 0)
                        self._count += 1
                        if self._count >= CAPACITY_EDGES:
                            logger.warning("SHM Graph Capacity reached!")
                            break

                    struct.pack_into("=i", mmap_file, 12, self._count)
                    logger.info(f"Synchronized {self._count} graph edges to SHM.")

_global_shm_graph = None
def get_shm_graph() -> SHMGraphTopology:
    """
    Get the shm graph.
    
    Returns:
        SHMGraphTopology
    """
    global _global_shm_graph
    if _global_shm_graph is None:
        _global_shm_graph = SHMGraphTopology()
    return _global_shm_graph
