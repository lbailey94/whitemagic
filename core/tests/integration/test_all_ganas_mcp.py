#!/usr/bin/env python3
"""Comprehensive MCP test: exercise one representative tool from each of the 28 Ganas.

Produces a structured JSON report suitable for reviewing in Windsurf or
feeding into the Karma Ledger for audit.

Usage:
    pytest tests/integration/test_all_ganas_mcp.py -v --tb=short
    # Or run directly for a standalone JSON report:
    python tests/integration/test_all_ganas_mcp.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest

# Skip entire module if mcp SDK not installed
try:
    import anyio
    import mcp.types as types
    from mcp.shared.message import SessionMessage

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

pytestmark = pytest.mark.skipif(not HAS_MCP, reason="mcp SDK not installed")


# ── Environment ─────────────────────────────────────────────────────────

# _mcp_env fixture removed in v22.2.2; the conftest.py
# `mcp_test_env` fixture (scope=module) provides the
# same isolation. Request it explicitly via this autouse wrapper.
@pytest.fixture(scope="module", autouse=True)
def _mcp_env(mcp_test_env):
    """Activate mcp_test_env for this module."""
    yield mcp_test_env

# ── MCP Client ──────────────────────────────────────────────────────────


class _MCPClient:
    def __init__(self, tx: Any, rx: Any) -> None:
        self._tx = tx
        self._rx = rx
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def request(
        self, method: str, params: dict | None = None, *, timeout: float = 30.0
    ) -> dict:
        req_id = self._next_id()
        raw: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            raw["params"] = params
        msg = types.JSONRPCMessage.model_validate(raw)
        await self._tx.send(SessionMessage(msg))

        async def _wait() -> dict:
            while True:
                session_msg = await self._rx.receive()
                data = json.loads(
                    session_msg.message.model_dump_json(
                        by_alias=True, exclude_none=True
                    )
                )
                if "id" in data:
                    return data

        return await asyncio.wait_for(_wait(), timeout=timeout)

    async def notify(self, method: str, params: dict | None = None) -> None:
        raw: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            raw["params"] = params
        msg = types.JSONRPCMessage.model_validate(raw)
        await self._tx.send(SessionMessage(msg))

    async def initialize(self) -> dict:
        resp = await self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "all-ganas-test", "version": "1.0.0"},
            },
        )
        await self.notify("notifications/initialized")
        return resp


@asynccontextmanager
async def mcp_session() -> AsyncGenerator[_MCPClient, None]:
    from whitemagic.run_mcp_lean import server

    to_server_tx, to_server_rx = anyio.create_memory_object_stream(16)
    from_server_tx, from_server_rx = anyio.create_memory_object_stream(16)

    server_task = asyncio.create_task(
        server.run(to_server_rx, from_server_tx, server.create_initialization_options())
    )
    client = _MCPClient(to_server_tx, from_server_rx)
    try:
        await client.initialize()
        yield client
    finally:
        await to_server_tx.aclose()
        server_task.cancel()
        try:
            await server_task
        except (asyncio.CancelledError, Exception):
            pass


# ── Gana test matrix ────────────────────────────────────────────────────
# One representative (gana, nested_tool, args) per Gana.
# Args are deliberately minimal; we test envelope + latency + basic correctness.

GANA_TESTS: list[tuple[str, str, dict]] = [
    ("gana_horn", "session_bootstrap", {"mode": "standard"}),
    (
        "gana_neck",
        "create_memory",
        {"title": "All-gana test", "content": "test memory", "tags": ["test"]},
    ),
    ("gana_heart", "get_session_context", {}),
    ("gana_tail", "token_report", {}),
    ("gana_dipper", "homeostasis", {}),
    ("gana_willow", "grimoire_list", {}),
    ("gana_room", "security.monitor_status", {}),
    ("gana_void", "galaxy.status", {}),
    ("gana_root", "health_report", {}),
    ("gana_chariot", "kg.status", {}),
    ("gana_net", "prompt.list", {}),
    ("gana_stomach", "task.list", {}),
    ("gana_ghost", "capabilities", {}),
    ("gana_girl", "agent.list", {}),
    ("gana_mound", "view_hologram", {}),
    ("gana_wings", "mesh.status", {}),
    ("gana_abundance", "ilp.status", {}),
    ("gana_encampment", "broker.status", {}),
    ("gana_winnowing_basket", "memory_search", {"query": "test"}),
    ("gana_extended_net", "pattern_search", {"query": "test"}),
    ("gana_star", "forge.status", {}),
    ("gana_wall", "vote.list", {}),
    ("gana_three_stars", "think", {"topic": "testing"}),
    ("gana_hairy_head", "salience.spotlight", {}),
    ("gana_straddling_legs", "get_dharma_guidance", {}),
    ("gana_ox", "swarm.status", {}),
    ("gana_roof", "shelter.status", {}),
    ("gana_turtle_beak", "edge_stats", {}),
]


# ── Tests ───────────────────────────────────────────────────────────────


class TestAllGanas:
    """Exercise one tool per Gana and verify structured envelope responses."""

    @pytest.mark.parametrize("gana,tool,args", GANA_TESTS)
    async def test_gana(self, gana: str, tool: str, args: dict):
        async with mcp_session() as client:
            start = time.monotonic()
            response = await client.request(
                "tools/call",
                {
                    "name": gana,
                    "arguments": {"tool": tool, "args": args},
                },
                timeout=45.0,
            )
            elapsed = time.monotonic() - start

            assert "result" in response, f"{gana}/{tool}: no result key"
            content = response["result"].get("content", [])
            assert len(content) > 0, f"{gana}/{tool}: empty content"

            text = content[0].get("text", "")
            assert text, f"{gana}/{tool}: no text content"

            # Attempt JSON parse; if it fails, the envelope may be plain text
            try:
                data = json.loads(text)
                status = data.get("status", "unknown")
            except json.JSONDecodeError:
                data = {"raw_text": text[:200]}
                status = "unparsed"

            # We accept success or error — both prove the tool executed and
            # returned a response (rather than crashing the server).
            assert status in {"success", "error", "unparsed"}, (
                f"{gana}/{tool}: unexpected status {status}"
            )

            # Attach timing for manual review
            print(f"\n  {gana}/{tool}: {status} in {elapsed:.2f}s", end="")


# ── Standalone runner ───────────────────────────────────────────────────


async def _run_standalone() -> dict:
    """Run all Gana tests and produce a JSON report."""
    state_dir = Path(tempfile.mkdtemp(prefix="wm_all_ganas_"))
    os.environ["WM_SILENT_INIT"] = "1"
    os.environ["WM_STATE_ROOT"] = str(state_dir)

    from whitemagic.run_mcp_lean import server

    to_server_tx, to_server_rx = anyio.create_memory_object_stream(16)
    from_server_tx, from_server_rx = anyio.create_memory_object_stream(16)
    server_task = asyncio.create_task(
        server.run(to_server_rx, from_server_tx, server.create_initialization_options())
    )
    client = _MCPClient(to_server_tx, from_server_rx)
    await client.initialize()

    results: list[dict] = []
    for gana, tool, args in GANA_TESTS:
        start = time.monotonic()
        try:
            response = await client.request(
                "tools/call",
                {
                    "name": gana,
                    "arguments": {"tool": tool, "args": args},
                },
                timeout=45.0,
            )
            elapsed = time.monotonic() - start
            content = response["result"].get("content", [{}])
            text = content[0].get("text", "") if content else ""
            try:
                data = json.loads(text)
                status = data.get("status", "unknown")
                error_code = data.get("error_code")
            except json.JSONDecodeError:
                data = {"raw_text": text[:200]}
                status = "unparsed"
                error_code = None
            results.append(
                {
                    "gana": gana,
                    "tool": tool,
                    "status": status,
                    "error_code": error_code,
                    "latency_sec": round(elapsed, 3),
                    "has_result": "result" in response,
                    "has_content": len(content) > 0,
                }
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            results.append(
                {
                    "gana": gana,
                    "tool": tool,
                    "status": "crashed",
                    "error_code": type(exc).__name__,
                    "latency_sec": round(elapsed, 3),
                    "has_result": False,
                    "has_content": False,
                }
            )

    await to_server_tx.aclose()
    server_task.cancel()
    try:
        await server_task
    except (asyncio.CancelledError, Exception):
        pass
    shutil.rmtree(state_dir, ignore_errors=True)

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r["status"] == "success"),
        "error": sum(1 for r in results if r["status"] == "error"),
        "unparsed": sum(1 for r in results if r["status"] == "unparsed"),
        "crashed": sum(1 for r in results if r["status"] == "crashed"),
        "avg_latency_sec": round(
            sum(r["latency_sec"] for r in results) / len(results), 3
        ),
        "results": results,
    }
    return summary


if __name__ == "__main__":
    import logging

    # Suppress startup warnings from leaking into JSON output
    logging.getLogger("whitemagic").setLevel(logging.CRITICAL)
    logging.getLogger("wm_mcp").setLevel(logging.CRITICAL)
    summary = asyncio.run(_run_standalone())
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["crashed"] == 0 else 1)
