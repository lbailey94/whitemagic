"""Go Mesh Bridge — Build and launch the Go mesh daemon from Python.

Usage:
    from whitemagic.mesh.go_bridge import build_mesh, start_mesh_daemon
    binary = build_mesh()  # Compiles the Go binary
    proc = start_mesh_daemon(binary)  # Starts as subprocess
    # ... mesh runs in background ...
    proc.terminate()
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MESH_AUX_DIR = Path(__file__).parents[2] / "mesh_aux"
GO_CMD = Path("go")


def build_mesh(go_cmd: str | Path | None = None) -> Path | None:
    """Build the Go mesh binary.

    Returns the path to the compiled binary, or None if Go is unavailable.
    """
    go = Path(go_cmd) if go_cmd else GO_CMD
    try:
        result = subprocess.run(
            [str(go), "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("Go not available: %s", result.stderr.strip())
            return None
    except FileNotFoundError:
        logger.warning("Go compiler not found in PATH")
        return None

    mesh_dir = MESH_AUX_DIR
    if not mesh_dir.exists():
        logger.error("mesh_aux directory not found: %s", mesh_dir)
        return None

    output = mesh_dir / "cmd" / "mesh_aux" / "mesh_daemon"
    logger.info("Building Go mesh daemon...")
    build = subprocess.run(
        [str(go), "build", "-o", str(output), "./cmd/mesh_aux"],
        cwd=str(mesh_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        logger.error("Go build failed:\n%s", build.stderr)
        return None

    logger.info("Go mesh daemon built: %s", output)
    return output


def start_mesh_daemon(
    binary: Path | None = None,
    redis_url: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[Any] | None:
    """Start the Go mesh daemon as a subprocess.

    Args:
        binary: Path to compiled mesh binary (builds if None).
        redis_url: Optional Redis URL for pub/sub bridge.
        env: Additional environment variables.

    Returns:
        subprocess.Popen instance, or None if start failed.
    """
    if binary is None:
        binary = build_mesh()
        if binary is None:
            return None

    if not binary.exists():
        logger.error("Mesh binary not found: %s", binary)
        return None

    run_env = {**os.environ}
    if redis_url:
        run_env["REDIS_URL"] = redis_url
    if env:
        run_env.update(env)

    logger.info("Starting Go mesh daemon: %s", binary)
    try:
        proc = subprocess.Popen(
            [str(binary)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=run_env,
        )
        return proc
    except OSError as e:
        logger.error("Failed to start mesh daemon: %s", e)
        return None


def is_mesh_running(proc: subprocess.Popen[Any] | None) -> bool:
    """Check if the mesh daemon process is still running."""
    return proc is not None and proc.poll() is None
