# ruff: noqa: BLE001
"""Koka Bridge - Python interface to Koka binaries.

Provides high-level Python API for all Koka runtime binaries.
"""

import json
import logging
import os
import queue
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)

_DEFAULT_KOKA_BRIDGE_TIMEOUT_S = 5.0


@dataclass
class KokaProcess:
    """KokaProcess: koka process.
    
    Value object: equality and repr are field-based."""
    name: str
    proc: subprocess.Popen

    def _readline_with_timeout(self, timeout: float = _DEFAULT_KOKA_BRIDGE_TIMEOUT_S) -> str | None:
        result_queue: queue.Queue[str | None] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                stdout = self.proc.stdout
                if stdout is not None:
                    line = stdout.readline()
                    result_queue.put(line)
                else:
                    result_queue.put(None)
            except Exception as e:
                logger.debug("Operation failed: %s", e)
                result_queue.put(None)

        thread = threading.Thread(target=_reader, name=f"koka-bridge-{self.name}", daemon=True)
        thread.start()

        try:
            return result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def send(self, cmd: dict, timeout: float = _DEFAULT_KOKA_BRIDGE_TIMEOUT_S) -> dict:
        """Send command and receive response."""
        stdin = self.proc.stdin
        if stdin is not None:
            stdin.write(json.dumps(cmd) + "\n")
            stdin.flush()
        else:
            raise RuntimeError(f"Koka process {self.name} has no stdin")

        response = self._readline_with_timeout(timeout=timeout)
        if not response:
            raise TimeoutError(f"Koka bridge timed out waiting for response from {self.name}")
        return cast(dict[str, object], json.loads(response))

    def close(self):
        """
        Perform the close operation.
        """
        try:
            self.send({"op": "quit"}, timeout=1.0)
        except Exception as e:
            logger.debug("Operation failed: %s", e)
            pass
        try:
            self.proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.proc.kill()


class KokaRuntime:
    """Unified interface to all Koka binaries."""

    def __init__(self, koka_dir: str = "./whitemagic-koka"):
        self.koka_dir = koka_dir
        self.processes: dict[str, KokaProcess] = {}

    def start_unified_runtime(self) -> KokaProcess:
        """Start unified runtime v3."""
        proc = subprocess.Popen(
            [f"{self.koka_dir}/unified_runtime_v3"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        koka_proc = KokaProcess("unified_runtime_v3", proc)
        # Read startup message with timeout
        startup = koka_proc._readline_with_timeout(timeout=2.0)
        if not startup:
            proc.kill()
            raise TimeoutError("unified_runtime_v3 startup timed out")
        self.processes["unified"] = koka_proc
        return koka_proc

    def start_ring_buffer(self) -> KokaProcess:
        """Start ring buffer."""
        proc = subprocess.Popen(
            [f"{self.koka_dir}/ring_buffer"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        koka_proc = KokaProcess("ring_buffer", proc)
        startup = koka_proc._readline_with_timeout(timeout=2.0)
        if not startup:
            proc.kill()
            raise TimeoutError("ring_buffer startup timed out")
        self.processes["ring_buffer"] = koka_proc
        return koka_proc

    def start_rust_bridge(self) -> KokaProcess:
        """Start rust bridge."""
        proc = subprocess.Popen(
            [f"{self.koka_dir}/rust_bridge"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        koka_proc = KokaProcess("rust_bridge", proc)
        startup = koka_proc._readline_with_timeout(timeout=2.0)
        if not startup:
            proc.kill()
            raise TimeoutError("rust_bridge startup timed out")
        self.processes["rust_bridge"] = koka_proc
        return koka_proc

    def batch_write_embeddings(self, embeddings: list[list[float]], ids: list[int]) -> dict:
        """Batch write embeddings via ring buffer."""
        if "ring_buffer" not in self.processes:
            self.start_ring_buffer()

        rb = self.processes["ring_buffer"]
        return rb.send({
            "op": "batch_write",
            "count": len(embeddings)
        })

    def emit_event(self, source: str, event_type: str) -> dict:
        """Emit event via effect runtime."""
        if "unified" not in self.processes:
            self.start_unified_runtime()

        return self.processes["unified"].send({
            "op": "emit",
            "source": source,
            "event": event_type
        })

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity via rust bridge."""
        if "rust_bridge" not in self.processes:
            self.start_rust_bridge()

        result = self.processes["rust_bridge"].send({
            "op": "cosine",
            "a": a,
            "b": b
        })
        res = result.get("cosine_sim", 0.0)
        return float(res)

    def start_batch_ipc(self) -> KokaProcess | None:
        """Start batch IPC runtime for transactions."""
        # Check if binary exists
        binary_path = f"{self.koka_dir}/batch_ipc"
        if not os.path.exists(binary_path):
            logger.warning(f"Koka batch_ipc binary not found at {binary_path}")
            return None

        # Mirror the batch client: unbuffered stdio and a short startup handshake.
        cmd = ["stdbuf", "-o0", "-i0", binary_path]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1 # Line buffered
        )
        koka_proc = KokaProcess("batch_ipc", proc)
        startup = koka_proc._readline_with_timeout(timeout=5.0)
        if not startup or ("started" not in startup and "batch_ipc" not in startup):
            proc.kill()
            logger.warning("batch_ipc startup failed or timed out — using Python-only transactions")
            return None
        self.processes["batch_ipc"] = koka_proc
        return koka_proc

    def begin_transaction(self) -> str:
        """Begin a Koka-managed transaction."""
        if "batch_ipc" not in self.processes:
            if not self.start_batch_ipc():
                return ""
        try:
            res = self.processes["batch_ipc"].send({"op": "begin_tx"}, timeout=2.0)
            tx_id = res.get("tx_id", "")
            return str(tx_id)
        except Exception as e:
            logger.debug(f"Koka begin_tx failed: {e}")
            return ""

    def commit_transaction(self, tx_id: str) -> bool:
        """Commit a Koka-managed transaction."""
        if not tx_id or "batch_ipc" not in self.processes:
            return False
        try:
            res = self.processes["batch_ipc"].send({"op": "commit_tx", "tx_id": tx_id}, timeout=2.0)
            committed = res.get("committed", False)
            return bool(committed)
        except Exception as e:
            logger.debug(f"Koka commit_tx failed: {e}")
            return False

    def rollback_transaction(self, tx_id: str) -> bool:
        """Rollback a Koka-managed transaction."""
        if not tx_id or "batch_ipc" not in self.processes:
            return False
        try:
            res = self.processes["batch_ipc"].send({"op": "rollback_tx", "tx_id": tx_id}, timeout=2.0)
            rolled_back = res.get("rolled_back", False)
            return bool(rolled_back)
        except Exception as e:
            logger.debug(f"Koka rollback_tx failed: {e}")
            return False


async def koka_health_check() -> dict:
    """Async health check for V21 validation suite."""
    runtime = get_koka_runtime()
    try:
        # Check if basic binaries exist
        import os
        koka_dir = runtime.koka_dir
        binaries = ["unified_runtime_v3", "ring_buffer", "rust_bridge"]
        missing = [b for b in binaries if not os.path.exists(f"{koka_dir}/{b}")]

        if missing:
            return {
                "status": "partial",
                "missing_binaries": missing,
                "message": f"Koka binaries missing: {missing}"
            }

        return {
            "status": "success",
            "message": "Koka runtime binaries present"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

_koka_runtime = None
_koka_lock = threading.Lock()


def get_koka_runtime() -> KokaRuntime:
    """Get the global KokaRuntime singleton."""
    global _koka_runtime
    if _koka_runtime is None:
        with _koka_lock:
            if _koka_runtime is None:
                # Use absolute path relative to this file's location
                bridge_file = Path(__file__).resolve()
                project_root = bridge_file.parent.parent.parent.parent
                koka_dir = project_root / "whitemagic-koka"
                _koka_runtime = KokaRuntime(str(koka_dir))
    return _koka_runtime
