# ruff: noqa: BLE001
"""Holographic Intake System.
==========================

Automatic ingestion of new files into the holographic memory hypercube.

Connects to:
- SemanticFileWatcher (file monitoring)
- HomeostaticMonitor (change detection)
- HolographicEncoder (coordinate generation)
- SQLiteBackend (persistence)

When new files are detected, they are:
1. Flagged for review (intake queue)
2. Checked for duplicates (content hash)
3. Processed with holographic coordinates
4. Synced to SQLite for fast queries

Usage:
    intake = get_holographic_intake()
    intake.add_watch("/path/to/transcripts")
    intake.start()  # Background monitoring

    # Manual processing
    intake.process_queue()
"""

from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

from whitemagic.config.paths import DATA_DIR, DB_PATH, MEMORY_DIR
from whitemagic.utils.core import parse_datetime
from whitemagic.utils.fast_json import dumps_str as _json_dumps
from whitemagic.utils.fast_json import loads as _json_loads
from whitemagic.core.memory.db_manager import safe_connect

logger = logging.getLogger(__name__)

# Singleton
_intake_instance: HolographicIntake | None = None
_intake_lock = threading.RLock()


class IntakeStatus(Enum):
    """Status of a file in the intake queue."""

    PENDING = auto()  # Awaiting processing
    PROCESSING = auto()  # Currently being processed
    COMPLETED = auto()  # Successfully ingested
    DUPLICATE = auto()  # Already exists in memory
    SKIPPED = auto()  # Manually skipped
    ERROR = auto()  # Processing failed


@dataclass
class IntakeItem:
    """An item in the intake queue."""

    path: str
    detected_at: str
    status: IntakeStatus = IntakeStatus.PENDING
    content_hash: str | None = None
    file_type: str = "unknown"
    size_bytes: int = 0
    error_message: str | None = None
    memory_id: str | None = None  # ID after ingestion

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "path": self.path,
            "detected_at": self.detected_at,
            "status": self.status.name,
            "content_hash": self.content_hash,
            "file_type": self.file_type,
            "size_bytes": self.size_bytes,
            "error_message": self.error_message,
            "memory_id": self.memory_id,
        }


class HolographicIntake:
    """Automatic ingestion system for the holographic memory hypercube.

    Monitors configured directories for new files and processes them
    into the memory system with holographic coordinates.
    """

    # Supported text file types for memory ingestion
    SUPPORTED_TYPES = {
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".py": "python",
        ".ts": "typescript",
        ".js": "javascript",
        ".html": "html",
    }

    @staticmethod
    def _get_media_chain() -> Any:
        """Lazy-load the multimodal processor chain."""
        try:
            from whitemagic.core.intake.media_processor import get_processor_chain

            return get_processor_chain()
        except (ImportError, ModuleNotFoundError):
            return None

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            state_dir = DATA_DIR / "intake"
            self.config_path = state_dir / "intake_config.json"
        else:
            self.config_path = config_path
        state_dir = self.config_path.parent
        self.queue_path = state_dir / "intake_queue.json"
        state_dir.mkdir(parents=True, exist_ok=True)

        self._queue: dict[str, IntakeItem] = {}  # path -> IntakeItem
        self._known_hashes: set[str] = set()  # Content hashes already in memory
        self._watch_dirs: list[str] = []
        self._running = False
        self._thread: threading.Thread | None = None

        self._load_config()
        self._load_queue()
        self._load_known_hashes()

    def _load_config(self) -> None:
        """Load configuration."""
        if self.config_path.exists():
            try:
                data = _json_loads(self.config_path.read_text())
                self._watch_dirs = data.get("watch_dirs", [])
            except Exception as e:
                logger.warning("Failed to load intake config: %s", e, exc_info=True)

    def _save_config(self) -> None:
        """Save configuration."""
        data = {
            "version": "1.0",
            "updated": datetime.now(UTC).isoformat(),
            "watch_dirs": self._watch_dirs,
        }
        self.config_path.write_text(_json_dumps(data, indent=2))

    def _load_queue(self) -> None:
        """Load intake queue from disk."""
        if self.queue_path.exists():
            try:
                data = _json_loads(self.queue_path.read_text())
                for item_data in data.get("queue", []):
                    item = IntakeItem(
                        path=item_data["path"],
                        detected_at=item_data["detected_at"],
                        status=IntakeStatus[item_data["status"]],
                        content_hash=item_data.get("content_hash"),
                        file_type=item_data.get("file_type", "unknown"),
                        size_bytes=item_data.get("size_bytes", 0),
                        error_message=item_data.get("error_message"),
                        memory_id=item_data.get("memory_id"),
                    )
                    self._queue[item.path] = item
            except Exception as e:
                logger.warning("Failed to load intake queue: %s", e, exc_info=True)

    def _save_queue(self) -> None:
        """Save intake queue to disk."""
        data = {
            "version": "1.0",
            "updated": datetime.now(UTC).isoformat(),
            "queue": [item.to_dict() for item in self._queue.values()],
        }
        self.queue_path.write_text(_json_dumps(data, indent=2))

    def _load_known_hashes(self) -> None:
        """Load content hashes from existing memories."""
        try:
            metadata_path = MEMORY_DIR / "metadata.json"
            if metadata_path.exists():
                data = _json_loads(metadata_path.read_text())
                for mem in data.get("memory_index", []):
                    if "content_hash" in mem:
                        self._known_hashes.add(mem["content_hash"])

            # Also check SQLite
            try:

                if DB_PATH.exists():
                    conn = safe_connect(str(DB_PATH))
                    rows = conn.execute("SELECT content FROM memories").fetchall()
                    for row in rows:
                        if row[0]:
                            h = hashlib.sha256(row[0].encode()).hexdigest()[:16]
                            self._known_hashes.add(h)
                    conn.close()
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                pass

            logger.info("Loaded %s known content hashes", len(self._known_hashes))
        except Exception as e:
            logger.warning("Failed to load known hashes: %s", e, exc_info=True)

    def _compute_hash(self, path: Path) -> str:
        """Compute content hash for a file."""
        try:
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            return ""

    def add_watch(self, path: str) -> bool:
        """Add a directory to watch for new files."""
        abs_path = str(Path(path).resolve())
        if not Path(abs_path).is_dir():
            return False

        if abs_path not in self._watch_dirs:
            self._watch_dirs.append(abs_path)
            self._save_config()
            logger.info("Added watch: %s", abs_path, exc_info=True)
        return True

    def remove_watch(self, path: str) -> bool:
        """Remove a directory from watching."""
        abs_path = str(Path(path).resolve())
        if abs_path in self._watch_dirs:
            self._watch_dirs.remove(abs_path)
            self._save_config()
            return True
        return False

    def list_watches(self) -> list[str]:
        """List watched directories."""
        return self._watch_dirs.copy()

    def scan_directory(self, path: str) -> list[IntakeItem]:
        """Scan a directory for new files not in memory."""
        new_items: list[IntakeItem] = []
        dir_path = Path(path)

        if not dir_path.is_dir():
            return new_items

        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            media_chain = self._get_media_chain()
            media_exts = media_chain.supported_extensions() if media_chain else set()
            if ext not in self.SUPPORTED_TYPES and ext not in media_exts:
                continue

            # Skip if already in queue
            path_str = str(file_path)
            if path_str in self._queue:
                continue

            # Compute hash
            content_hash = self._compute_hash(file_path)

            if content_hash in self._known_hashes:
                continue

            # Create intake item
            item = IntakeItem(
                path=path_str,
                detected_at=datetime.now(UTC).isoformat(),
                content_hash=content_hash,
                file_type=self.SUPPORTED_TYPES.get(file_path.suffix.lower(), "unknown"),
                size_bytes=file_path.stat().st_size,
            )

            self._queue[path_str] = item
            new_items.append(item)

        if new_items:
            self._save_queue()
            logger.info("Found {len(new_items)} new files in %s", path, exc_info=True)

        return new_items

    def scan_all(self) -> list[IntakeItem]:
        """Scan all watched directories."""
        all_new = []
        for watch_dir in self._watch_dirs:
            all_new.extend(self.scan_directory(watch_dir))
        return all_new

    def process_item(self, path: str) -> bool:
        """Process a single item from the queue."""
        if path not in self._queue:
            return False

        item = self._queue[path]
        if item.status != IntakeStatus.PENDING:
            return False

        item.status = IntakeStatus.PROCESSING

        try:
            from whitemagic.core.intelligence.hologram.encoder import CoordinateEncoder
            from whitemagic.core.memory.sqlite_backend import SQLiteBackend
            from whitemagic.core.memory.unified_types import Memory, MemoryType

            file_path = Path(path)
            if not file_path.exists():
                item.status = IntakeStatus.ERROR
                item.error_message = "File not found"
                self._save_queue()
                return False

            media_chain = self._get_media_chain()
            media_result = None
            if media_chain and file_path.suffix.lower() not in self.SUPPORTED_TYPES:
                media_result = media_chain.process(file_path)

            if media_result:
                content = media_result.text
                extra_tags = {media_result.media_type, "multimodal"}
                extra_metadata = media_result.metadata
                holo_bias = media_result.holographic_bias
            else:
                # Standard text file reading
                content = file_path.read_text(encoding="utf-8", errors="ignore")[:10000]
                extra_tags = set()
                extra_metadata = {}
                holo_bias = {}

            # Generate holographic coordinates
            encoder = CoordinateEncoder()
            encode_input: dict[str, Any] = {
                "content": content,
                "title": file_path.stem,
                "tags": [item.file_type],
                "memory_type": "long_term",
                "created": item.detected_at,
            }
            coords = encoder.encode(encode_input)

            # Create memory
            memory_id = hashlib.sha256(
                f"{path}:{item.detected_at}".encode()
            ).hexdigest()[:16]
            base_tags = {item.file_type, "auto-ingested"}
            base_tags.update(extra_tags)
            mem_metadata: dict[str, Any] = {
                "source_path": path,
                "holographic_coordinates": coords,
            }
            mem_metadata.update(extra_metadata)
            if holo_bias:
                mem_metadata["holographic_bias"] = holo_bias

            memory = Memory(
                id=memory_id,
                content=content,
                memory_type=MemoryType.LONG_TERM,
                title=file_path.stem,
                created_at=parse_datetime(item.detected_at.replace("Z", "+00:00")),
                accessed_at=datetime.now(),
                access_count=1,
                tags=base_tags,
                associations={},
                emotional_valence=0.0,
                importance=getattr(coords, "w", 0.5),
                metadata=mem_metadata,
            )

            backend = SQLiteBackend(DB_PATH)
            backend.store(memory)
            backend.store_coords(memory_id, coords.x, coords.y, coords.z, coords.w)  # type: ignore[union-attr, call-arg]

            # Update item
            item.status = IntakeStatus.COMPLETED
            item.memory_id = memory_id
            if item.content_hash is not None:
                self._known_hashes.add(item.content_hash)

            logger.info("Ingested: %s -> %s", file_path.name, memory_id, exc_info=True)
            self._save_queue()
            return True

        except Exception as e:
            item.status = IntakeStatus.ERROR
            item.error_message = str(e)
            logger.error("Failed to process %s: %s", path, e, exc_info=True)
            self._save_queue()
            return False

    def process_queue(self, limit: int = 50) -> dict[str, int]:
        """Process pending items in the queue."""
        stats = {"processed": 0, "errors": 0, "skipped": 0}

        pending = [
            p for p, item in self._queue.items() if item.status == IntakeStatus.PENDING
        ]

        for path in pending[:limit]:
            if self.process_item(path):
                stats["processed"] += 1
            else:
                stats["errors"] += 1

        return stats

    def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics."""
        stats = {status.name: 0 for status in IntakeStatus}
        for item in self._queue.values():
            stats[item.status.name] += 1
        return stats

    def get_pending(self) -> list[IntakeItem]:
        """Get pending items."""
        return [
            item for item in self._queue.values() if item.status == IntakeStatus.PENDING
        ]

    def clear_completed(self) -> int:
        """Remove completed items from queue."""
        to_remove = [
            p
            for p, item in self._queue.items()
            if item.status == IntakeStatus.COMPLETED
        ]
        for path in to_remove:
            del self._queue[path]
        self._save_queue()
        return len(to_remove)

    def skip_item(self, path: str) -> bool:
        """Skip an item (don't process it)."""
        if path in self._queue:
            self._queue[path].status = IntakeStatus.SKIPPED
            self._save_queue()
            return True
        return False

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        import time

        while self._running:
            try:
                # Scan for new files
                new_items = self.scan_all()
                if new_items:
                    logger.info("Detected %s new files for ingestion", len(new_items))

                # Sleep for 5 minutes
                for _ in range(300):
                    if not self._running:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error("Monitor loop error: %s", e, exc_info=True)
                time.sleep(60)

    def start(self) -> bool:
        """Start background monitoring."""
        if self._running:
            return False

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Holographic intake monitoring started")
        return True

    def stop(self) -> bool:
        """Stop background monitoring."""
        if not self._running:
            return False

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Holographic intake monitoring stopped")
        return True

    def is_running(self) -> bool:
        """Check if monitoring is active."""
        return self._running


def get_holographic_intake() -> HolographicIntake:
    """Get singleton intake instance."""
    global _intake_instance
    with _intake_lock:
        if _intake_instance is None:
            _intake_instance = HolographicIntake()
        return _intake_instance


# CLI interface
if __name__ == "__main__":
    import sys

    intake = get_holographic_intake()

    if len(sys.argv) < 2:
        logger.info("Usage: python holographic_intake.py <command> [args]")
        logger.info("Commands:")
        logger.info("  scan <path>     - Scan directory for new files")
        logger.info("  process         - Process pending items")
        logger.info("  status          - Show queue status")
        logger.info("  watch <path>    - Add watch directory")
        logger.info("  start           - Start background monitoring")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "scan" and len(sys.argv) > 2:
        items = intake.scan_directory(sys.argv[2])
        logger.info("Found %s new files", len(items))
        for item in items[:10]:
            logger.info("  %s", item.path)

    elif cmd == "process":
        stats = intake.process_queue()
        logger.info("Processed: %s, Errors: %s", stats["processed"], stats["errors"])

    elif cmd == "status":
        stats = intake.get_queue_stats()
        logger.info("Queue Status:")
        for status, count in stats.items():
            if count > 0:
                logger.info("  %s: %s", status, count)

    elif cmd == "watch" and len(sys.argv) > 2:
        if intake.add_watch(sys.argv[2]):
            logger.info("Added watch: %s", sys.argv[2])
        else:
            logger.info("Failed to add watch")

    elif cmd == "start":
        intake.start()
        logger.info("Monitoring started. Press Ctrl+C to stop.")
        try:
            while True:
                import time

                time.sleep(1)
        except KeyboardInterrupt:
            intake.stop()
            logger.info("\nStopped.")
