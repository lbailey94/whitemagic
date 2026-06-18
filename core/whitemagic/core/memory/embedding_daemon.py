# ruff: noqa: BLE001
"""Incremental Embedding Daemon - Background Memory Embedding Pipeline (v16).
============================================================================
Continuously processes memories without embeddings in the background.
Uses Rust acceleration when available, falls back to Python.

Design:
  - Background daemon thread (non-blocking)
  - Incremental batch processing (configurable batch size)
  - Periodic polling for new unembedded memories
  - Rust EmbeddingEngine acceleration when available
  - Observability integration (Prometheus metrics)
  - Graceful shutdown on system stop

Usage:
    from whitemagic.core.memory.embedding_daemon import get_embedding_daemon

    daemon = get_embedding_daemon()
    daemon.start()  # Starts background processing

    # Check status
    stats = daemon.get_stats()

    daemon.stop()  # Graceful shutdown
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Configuration defaults
DEFAULT_BATCH_SIZE = 100  # Memories per batch
DEFAULT_POLL_INTERVAL = 60.0  # Seconds between polls
DEFAULT_MAX_PER_RUN = 1000  # Max memories per daemon cycle


@dataclass
class EmbeddingDaemonStats:
    """Statistics for the embedding daemon."""
    started_at: datetime | None = None
    last_run: datetime | None = None
    total_runs: int = 0
    total_embedded: int = 0
    total_failed: int = 0
    current_rate: float = 0.0  # embeddings/sec
    last_batch_size: int = 0
    pending_memories: int = 0
    is_running: bool = False
    rust_available: bool = False


class EmbeddingDaemon:
    """Background daemon for incremental memory embedding.

    Features:
    - Non-blocking background thread
    - Rust acceleration when available
    - Incremental batch processing
    - Prometheus metrics integration
    - Graceful shutdown
    """

    _instance: EmbeddingDaemon | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> EmbeddingDaemon:
        """Singleton pattern for global daemon."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        max_per_run: int = DEFAULT_MAX_PER_RUN,
        on_batch_complete: Callable[[dict], None] | None = None,
    ):
        # Only init once (singleton)
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_per_run = max_per_run
        self.on_batch_complete = on_batch_complete

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stats = EmbeddingDaemonStats()
        self._rust_engine = None
        self._python_engine = None
        self._initialized = True

        # Check Rust availability
        self._check_rust_availability()

    def _check_rust_availability(self) -> None:
        """Check if Rust embedding engine is available."""
        try:
            import whitemagic_rust
            model_path = self._get_model_path()
            if model_path:
                self._rust_engine = whitemagic_rust.EmbeddingEngine(model_path)
                # Verify dimension matches Python model (BGE-small = 384)
                test_emb = self._rust_engine.generate_embedding("test")
                rust_dim = len(test_emb)
                from whitemagic.core.memory.embeddings import EMBEDDING_DIM
                if rust_dim == EMBEDDING_DIM:
                    self._stats.rust_available = True
                    logger.info(f"EmbeddingDaemon: Rust acceleration enabled ({rust_dim} dims)")
                else:
                    logger.warning(
                        f"EmbeddingDaemon: Rust dimension mismatch ({rust_dim} vs {EMBEDDING_DIM}), "
                        f"using Python fallback"
                    )
                    self._rust_engine = None
                    self._stats.rust_available = False
        except Exception as e:
            logger.debug(f"Rust embedding not available: {e}")
            self._stats.rust_available = False

    def _get_model_path(self) -> str | None:
        """Get path to embedding model."""
        try:
            import os
            from pathlib import Path
            # Check common model locations (HF cache can be under WM_ROOT or home)
            hf_home = os.getenv("HF_HOME")
            cache_home = os.getenv("XDG_CACHE_HOME")
            model_dirs = []
            if hf_home:
                model_dirs.append(Path(hf_home) / "hub")
            if cache_home:
                model_dirs.append(Path(cache_home) / "huggingface" / "hub")
            model_dirs.extend([
                Path.home() / ".cache" / "huggingface" / "hub",
                Path("/models"),
                Path.cwd() / "models",
            ])
            model_name = "BAAI/bge-small-en-v1.5"
            for base in model_dirs:
                # Look for the model in various locations (HuggingFace cache format)
                model_path = base / f"models--{model_name.replace('/', '--')}" / "snapshots"
                if model_path.exists():
                    # Find the actual snapshot directory
                    snapshots = list(model_path.iterdir())
                    if snapshots:
                        return str(snapshots[0])
        except OSError as e:
            logger.debug(f"Model path resolution failed: {e}")
        return None

    def _get_db(self) -> sqlite3.Connection | None:
        """Get database connection."""
        try:
            from whitemagic.config.paths import DB_PATH
            if not DB_PATH.exists():
                return None
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except Exception as e:
            logger.error(f"DB connection failed: {e}")
            return None

    def _get_python_engine(self) -> Any:
        """Get Python embedding engine (lazy load)."""
        if self._python_engine is None:
            try:
                from whitemagic.core.memory.embeddings import get_embedding_engine
                self._python_engine = get_embedding_engine()
            except Exception as e:
                logger.error(f"Python embedding engine load failed: {e}")
        return self._python_engine

    def start(self) -> None:
        """Start the embedding daemon in background thread."""
        if self._running:
            logger.warning("EmbeddingDaemon already running")
            return

        self._running = True
        self._stop_event.clear()
        self._stats.is_running = True
        self._stats.started_at = datetime.now()

        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="EmbeddingDaemon"
        )
        self._thread.start()
        logger.info(f"EmbeddingDaemon started (batch_size={self.batch_size}, poll={self.poll_interval}s)")

    def stop(self) -> None:
        """Stop the embedding daemon gracefully."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()
        self._stats.is_running = False

        if self._thread:
            self._thread.join(timeout=10.0)

        logger.info(f"EmbeddingDaemon stopped (total_embedded={self._stats.total_embedded})")

    def _run_loop(self) -> None:
        """Main daemon loop."""
        while self._running and not self._stop_event.is_set():
            try:
                # Process one batch cycle
                result = self._process_cycle()

                # Update stats
                self._stats.last_run = datetime.now()
                self._stats.total_runs += 1
                self._stats.total_embedded += result.get("embedded", 0)
                self._stats.total_failed += result.get("failed", 0)
                self._stats.last_batch_size = result.get("embedded", 0)
                self._stats.current_rate = result.get("rate", 0.0)

                # Callback
                if self.on_batch_complete:
                    try:
                        self.on_batch_complete(result)
                    except Exception as e:
                        logger.error(f"on_batch_complete callback error: {e}")

                # Record metrics
                self._record_metrics(result)

            except Exception as e:
                logger.error(f"EmbeddingDaemon cycle error: {e}")

            # Wait for next poll or stop signal
            self._stop_event.wait(self.poll_interval)

    def _process_cycle(self) -> dict:
        """Process one cycle of embedding."""
        t0 = time.perf_counter()
        result = {
            "embedded": 0,
            "failed": 0,
            "pending": 0,
            "rate": 0.0,
            "engine": "rust" if self._stats.rust_available else "python",
        }

        db = self._get_db()
        if db is None:
            return result

        try:
            # Find memories without embeddings
            pending = self._find_unembedded(db, limit=self.max_per_run)
            result["pending"] = len(pending)
            self._stats.pending_memories = len(pending)

            if not pending:
                return result

            # Process in batches
            total_embedded = 0
            total_failed = 0

            for i in range(0, len(pending), self.batch_size):
                batch = pending[i:i + self.batch_size]
                embedded, failed = self._process_batch(db, batch)
                total_embedded += embedded
                total_failed += failed

            result["embedded"] = total_embedded
            result["failed"] = total_failed

            elapsed = time.perf_counter() - t0
            if elapsed > 0 and total_embedded > 0:
                result["rate"] = total_embedded / elapsed

            logger.info(
                f"EmbeddingDaemon cycle: embedded={total_embedded}, "
                f"failed={total_failed}, rate={result['rate']:.1f}/sec"
            )

        finally:
            db.close()

        return result

    def _find_unembedded(self, db: sqlite3.Connection, limit: int) -> list[tuple[str, str]]:
        """Find memories without embeddings.

        Returns list of (memory_id, text) tuples.
        """
        from whitemagic.core.memory.embeddings import MODEL_NAME

        sql = """
            SELECT id, COALESCE(title, '') || ' ' || COALESCE(content, '') as text
            FROM memories
            WHERE memory_type != 'quarantined'
              AND id NOT IN (SELECT memory_id FROM memory_embeddings WHERE model = ?)
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """

        rows = db.execute(sql, (MODEL_NAME, limit)).fetchall()
        return [(row[0], row[1].strip()) for row in rows if row[1].strip()]

    def _process_batch(self, db: sqlite3.Connection, batch: list[tuple[str, str]]) -> tuple[int, int]:
        """Process a batch of memories.

        Returns (embedded_count, failed_count).
        """
        if not batch:
            return 0, 0

        ids, texts = zip(*batch)

        try:
            # Generate embeddings
            if self._stats.rust_available and self._rust_engine:
                embeddings = self._rust_engine.generate_embeddings_flat(list(texts))
                # Rust returns (flat_vec, n_texts, dimension) tuple
                if isinstance(embeddings, tuple) and len(embeddings) == 3:
                    flat_vec, n, dim = embeddings
                    # Reshape flat vector to list of embeddings
                    embeddings = [flat_vec[i*dim:(i+1)*dim] for i in range(n)]
                else:
                    return 0, len(batch)
            else:
                # Fall back to Python
                engine = self._get_python_engine()
                if engine is None or not engine.available():
                    return 0, len(batch)
                embeddings = engine.encode_batch(list(texts))

            if embeddings is None or len(embeddings) == 0:
                return 0, len(batch)

            # Handle different return types
            if hasattr(embeddings, 'shape'):
                # numpy array
                embeddings = [embeddings[i].tolist() for i in range(embeddings.shape[0])]
            elif isinstance(embeddings, list) and len(embeddings) > 0:
                if hasattr(embeddings[0], 'tolist'):
                    # list of numpy arrays
                    embeddings = [e.tolist() for e in embeddings]

            # Store embeddings
            import struct

            from whitemagic.core.memory.embeddings import MODEL_NAME

            embedded = 0
            failed = 0

            for mid, emb in zip(ids, embeddings):
                try:
                    packed = struct.pack(f"{len(emb)}f", *emb)
                    db.execute(
                        "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?, ?, ?)",
                        (mid, packed, MODEL_NAME)
                    )
                    embedded += 1
                except (sqlite3.Error, struct.error) as e:
                    logger.debug(f"Embedding insert failed for {mid}: {e}")
                    failed += 1

            db.commit()
            return embedded, failed

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            return 0, len(batch)

    def _record_metrics(self, result: dict) -> None:
        """Record metrics to Prometheus if available."""
        try:
            from prometheus_client import REGISTRY, Counter, Histogram

            # Get or create metrics
            try:
                embedded_counter = REGISTRY._names_to_collectors['embedding_daemon_embedded_total']
            except KeyError:
                embedded_counter = Counter(
                    'embedding_daemon_embedded_total',
                    'Total memories embedded by daemon',
                    ['engine']
                )

            try:
                rate_histogram = REGISTRY._names_to_collectors['embedding_daemon_rate']
            except KeyError:
                rate_histogram = Histogram(
                    'embedding_daemon_rate',
                    'Embedding rate (embeddings/sec)',
                    ['engine']
                )

            embedded_counter.labels(engine=result["engine"]).inc(result["embedded"])
            if result["rate"] > 0:
                rate_histogram.labels(engine=result["engine"]).observe(result["rate"])

        except ImportError:
            pass  # prometheus_client not installed
        except Exception as e:
            logger.debug(f"Metrics recording failed: {e}")

    def get_stats(self) -> dict:
        """Get daemon statistics."""
        return {
            "is_running": self._stats.is_running,
            "started_at": self._stats.started_at.isoformat() if self._stats.started_at else None,
            "last_run": self._stats.last_run.isoformat() if self._stats.last_run else None,
            "total_runs": self._stats.total_runs,
            "total_embedded": self._stats.total_embedded,
            "total_failed": self._stats.total_failed,
            "current_rate": self._stats.current_rate,
            "last_batch_size": self._stats.last_batch_size,
            "pending_memories": self._stats.pending_memories,
            "rust_available": self._stats.rust_available,
            "batch_size": self.batch_size,
            "poll_interval": self.poll_interval,
        }

    def process_now(self, limit: int = 1000) -> dict:
        """Process embeddings immediately (blocking).

        Useful for initial indexing or manual triggers.
        """
        return self._process_cycle()


def get_embedding_daemon(
    batch_size: int = DEFAULT_BATCH_SIZE,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    **kwargs,
) -> EmbeddingDaemon:
    """Get the global embedding daemon instance."""
    return EmbeddingDaemon(batch_size=batch_size, poll_interval=poll_interval, **kwargs)


# Integration with system startup
def start_embedding_daemon() -> EmbeddingDaemon:
    """Start the embedding daemon on system startup."""
    daemon = get_embedding_daemon()
    daemon.start()
    return daemon


def stop_embedding_daemon() -> None:
    """Stop the embedding daemon on system shutdown."""
    daemon = get_embedding_daemon()
    daemon.stop()
