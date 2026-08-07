#!/usr/bin/env python3
"""WhiteMagic v4 — Python MCP Shell

Thin Python MCP server that delegates all logic to the Rust core via PyO3.
Provides MCP protocol I/O over stdio, with optional ONNX embedding fallback
and HuggingFace tokenizer integration.

Usage:
    python whitemagic_v4_server.py [--store PATH]

Environment variables:
    WM_STORE_PATH    Path to LMDB store (default: ~/.local/share/whitemagic/lmdb)
    WM_LOG_LEVEL     Log level: trace, debug, info, warn, error (default: info)

The Rust extension module `whitemagic_v4` must be built and importable:
    cargo build --release --features python -p wm-mcp
    # The resulting .so/.pyd must be on PYTHONPATH or installed
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("whitemagic_v4")


def default_store_path() -> Path:
    """Get the default LMDB store path."""
    env = os.environ.get("WM_STORE_PATH")
    if env:
        return Path(env)

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "whitemagic" / "lmdb"

    home = os.environ.get("HOME", ".")
    return Path(home) / ".local" / "share" / "whitemagic" / "lmdb"


def try_import_rust() -> Any:
    """Try to import the Rust extension module."""
    try:
        import whitemagic_v4
        return whitemagic_v4
    except ImportError:
        # Try loading from the build directory
        build_dir = Path(__file__).parent.parent / "target" / "release"
        if build_dir.exists():
            sys.path.insert(0, str(build_dir))
        try:
            import whitemagic_v4
            return whitemagic_v4
        except ImportError as e:
            logger.error(
                "Cannot import whitemagic_v4 Rust extension. "
                "Build with: cargo build --release --features python -p wm-mcp"
            )
            raise ImportError(
                f"whitemagic_v4 not found. Build the Rust extension first.\n{e}"
            ) from e


class McpServer:
    """Python MCP server wrapping the Rust core via PyO3."""

    def __init__(self, store_path: Path) -> None:
        rust_module = try_import_rust()
        self._server = rust_module.Server(str(store_path))
        self._store_path = store_path
        logger.info("WhiteMagic v4 server initialized, store: %s", store_path)

    def handle_request(self, json_request: str) -> str:
        """Handle a single JSON-RPC request string."""
        return self._server.handle_request(json_request)

    def status(self) -> dict:
        """Get server status as a dict."""
        return json.loads(self._server.status())

    def brain_wave(self) -> str:
        """Get current brain-wave state."""
        return self._server.brain_wave()

    def tool_count(self) -> int:
        """Get number of registered tools."""
        return self._server.tool_count()

    def run_stdio(self) -> None:
        """Run the MCP server on stdin/stdout (JSON-RPC over stdio)."""
        logger.info("Starting MCP stdio loop (brain_wave=%s, tools=%d)",
                     self.brain_wave(), self.tool_count())

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                response = self.handle_request(line)
                print(response, flush=True)
            except Exception as e:
                logger.error("Error handling request: %s", e)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}",
                    },
                }
                print(json.dumps(error_response), flush=True)

        logger.info("MCP stdio loop ended (EOF)")


def try_init_onnx() -> Optional[Any]:
    """Try to initialize ONNX embedding model for fallback embeddings."""
    try:
        import importlib.util
        if importlib.util.find_spec("numpy") is None:
            logger.debug("numpy not available for ONNX embeddings")
            return None
        # Try fastembed or onnxruntime
        try:
            from fastembed import TextEmbedding
            model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("ONNX embeddings available via fastembed")
            return model
        except ImportError:
            pass
        logger.debug("ONNX embeddings not available (install fastembed or onnxruntime)")
    except ImportError:
        logger.debug("numpy not available for ONNX embeddings")
    return None


def try_init_tokenizer() -> Optional[Any]:
    """Try to initialize HuggingFace tokenizer."""
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        logger.info("HuggingFace tokenizer available")
        return tokenizer
    except ImportError:
        logger.debug("HuggingFace tokenizer not available (install transformers)")
    except Exception as e:
        logger.debug("HuggingFace tokenizer init failed: %s", e)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="WhiteMagic v4 MCP Server (Python shell)"
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=default_store_path(),
        help="Path to LMDB store directory",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("WM_LOG_LEVEL", "info"),
        choices=["trace", "debug", "info", "warn", "error"],
        help="Log level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,  # stdout is for JSON-RPC
    )

    # Ensure store directory exists
    args.store.mkdir(parents=True, exist_ok=True)

    # Initialize optional Python ecosystem integrations
    # These are logged but not yet wired into the MCP protocol
    _onnx_model = try_init_onnx()
    _tokenizer = try_init_tokenizer()

    # Start the MCP server
    server = McpServer(args.store)
    server.run_stdio()


if __name__ == "__main__":
    main()
