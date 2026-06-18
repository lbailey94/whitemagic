# ruff: noqa: BLE001
"""Julia ZMQ Bridge - Persistent Server Client.

Eliminates 3.7s JIT startup penalty by connecting to a running Julia server.
"""

import json
import logging
import os
import subprocess
import time
from typing import Any

import zmq

logger = logging.getLogger(__name__)

class JuliaZMQClient:
    """Client for Julia persistent ZMQ server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port
        self._context: Any | None = None
        self._socket: Any | None = None
        self._server_process: subprocess.Popen | None = None

    def connect(self) -> bool:
        """Connect to Julia server, starting it if needed."""
        # Try to connect to existing server
        try:
            zmq_any: Any = zmq
            self._context = zmq_any.Context()
            self._socket = self._context.socket(zmq_any.REQ)
            self._socket.setsockopt(zmq_any.RCVTIMEO, 5000)  # 5s timeout
            self._socket.connect(f"tcp://{self.host}:{self.port}")

            # Test with health check
            response = self._send_request({"method": "health"})
            if response.get("status") == "success":
                logger.info(f"🚀 Connected to Julia server v{response.get('version', 'unknown')}")
                return True

        except Exception as e:
            logger.debug(f"Could not connect to existing Julia server: {e}")

        # Start new server
        return self._start_server()

    def _start_server(self) -> bool:
        """Start Julia persistent server."""
        try:
            # Use absolute path for server script
            server_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                         "../../../whitemagic-julia/src/persistent_server.jl"))

            if not os.path.exists(server_path):
                # Try fallback location in SD card archives
                server_path = "/media/lucas/SD_CARD/WHITEMAGIC/archives/whitemagic-clean-BACKUP-20250407/whitemagic-julia/src/persistent_server.jl"
                if not os.path.exists(server_path):
                    logger.error(f"Julia server not found at {server_path}")
                    return False

            env = os.environ.copy()
            env["JULIA_SERVER_PORT"] = str(self.port)

            # Find julia executable
            julia_cmd = "julia"
            if os.path.exists("/usr/bin/julia"):
                julia_cmd = "/usr/bin/julia"
            elif os.path.exists("/snap/bin/julia"):
                julia_cmd = "/snap/bin/julia"

            # Start server process
            logger.info(f"Starting Julia server with command: {julia_cmd} {server_path}")
            self._server_process = subprocess.Popen(
                [julia_cmd, server_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to start (increased to 8s)
            time.sleep(8.0)

            # Try to connect
            zmq_any: Any = zmq
            self._context = zmq_any.Context()
            self._socket = self._context.socket(zmq_any.REQ)
            self._socket.setsockopt(zmq_any.RCVTIMEO, 15000)  # 15s timeout for startup
            self._socket.connect(f"tcp://{self.host}:{self.port}")

            response = self._send_request({"method": "health"})
            if response.get("status") == "success":
                logger.info(f"🚀 Started Julia server v{response.get('version', 'unknown')}")
                return True
            else:
                logger.error(f"Julia server health check failed: {response}")
                return False

        except FileNotFoundError:
            logger.error("Julia not found in PATH. Install Julia from julialang.org")
            return False
        except Exception as e:
            logger.error("Failed to start Julia server: %s", e, exc_info=True)
            return False

    def _send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send request to Julia server."""
        if not self._socket:
            raise RuntimeError("Not connected to Julia server")

        self._socket.send_string(json.dumps(request))
        response = self._socket.recv_string()
        result = json.loads(response)
        if not isinstance(result, dict):
            return {"status": "error", "message": "Invalid response from Julia server"}
        return result

    def rrf_fuse(self, lists: list[list[str]], weights: list[float], k: int = 60) -> list[str]:
        """RRF fusion via Julia."""
        response = self._send_request({
            "method": "rrf_fuse",
            "params": {"lists": lists, "weights": weights, "k": k}
        })

        if response.get("status") == "success":
            res = response.get("result", [])
            return list(res) if isinstance(res, (list, tuple)) else []
        else:
            raise RuntimeError(f"RRF fuse failed: {response.get('error')}")

    def pagerank(self, edges: list[tuple], weights: list[float],
                 damping: float = 0.85) -> dict[str, float]:
        """PageRank via Julia."""
        edge_list = [[src, dst] for src, dst in edges]
        response = self._send_request({
            "method": "pagerank",
            "params": {"edges": edge_list, "weights": weights, "damping": damping}
        })

        if response.get("status") == "success":
            res = response.get("result", {})
            return dict(res) if isinstance(res, dict) else {}
        else:
            raise RuntimeError(f"PageRank failed: {response.get('error')}")

    def walk_scoring(self, seed: str, edges: list[tuple],
                     node_scores: dict[str, float], max_depth: int = 5) -> dict[str, float]:
        """Graph walk scoring via Julia."""
        edge_list = [[src, dst] for src, dst in edges]
        response = self._send_request({
            "method": "walk_scoring",
            "params": {
                "seed": seed,
                "edges": edge_list,
                "node_scores": node_scores,
                "max_depth": max_depth
            }
        })

        if response.get("status") == "success":
            res = response.get("result", {})
            return dict(res) if isinstance(res, dict) else {}
        else:
            raise RuntimeError(f"Walk scoring failed: {response.get('error')}")

    def close(self):
        """Close connection and cleanup."""
        if self._socket:
            self._socket.close()
        if self._context:
            self._context.destroy()
        if self._server_process:
            self._server_process.terminate()
            self._server_process.wait(timeout=5)

# Global client
_julia_client: JuliaZMQClient | None = None

def get_julia_client() -> JuliaZMQClient | None:
    """Get global Julia ZMQ client."""
    global _julia_client
    if _julia_client is None:
        _julia_client = JuliaZMQClient()
        if not _julia_client.connect():
            _julia_client = None
    return _julia_client
