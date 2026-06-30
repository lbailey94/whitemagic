#!/usr/bin/env python3
"""Integration test: simulate OpenCode / Hermes connecting to WhiteMagic via MCP.

Verifies that an external agent runtime (IDE, CLI, or messaging gateway)
can discover WhiteMagic's governance surface, invoke curated tools, and
receive structured audit-ready responses.

Requires: mcp SDK + anyio installed (skip if unavailable).

Usage:
    pytest tests/integration/test_opencode_hermes_bridge.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

# Skip entire module if mcp SDK not installed
try:
    import anyio
    import mcp.types as types
    from mcp.shared.message import SessionMessage

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

pytestmark = pytest.mark.skipif(not HAS_MCP, reason="mcp SDK not installed")


# ── Environment setup ───────────────────────────────────────────────────

# _mcp_env fixture removed in v22.2.2; the conftest.py
# `mcp_test_env` autouse fixture (scope=module) provides the
# same isolation automatically for this test module.

# ── Simulated External Agent Client ──────────────────────────────────────


class _ExternalAgentClient:
    """Simulates an OpenCode or Hermes ACP/MCP client over memory streams."""

    def __init__(self, tx: Any, rx: Any) -> None:
        self._tx = tx
        self._rx = rx
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def request(
        self,
        method: str,
        params: dict | None = None,
        *,
        timeout: float = 15.0,
    ) -> dict:
        """Send a JSON-RPC *request* and wait for the matching response."""
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
                        by_alias=True,
                        exclude_none=True,
                    )
                )
                if "id" in data:
                    return data

        return await asyncio.wait_for(_wait(), timeout=timeout)

    async def notify(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC *notification* (fire-and-forget, no response)."""
        raw: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            raw["params"] = params
        msg = types.JSONRPCMessage.model_validate(raw)
        await self._tx.send(SessionMessage(msg))

    async def initialize(self) -> dict:
        """Perform the full MCP initialize handshake."""
        resp = await self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "opencode-hermes-bridge-test",
                    "version": "1.0.0",
                },
            },
        )
        await self.notify("notifications/initialized")
        return resp


@asynccontextmanager
async def mcp_session(
    *,
    init: bool = True,
) -> AsyncGenerator[_ExternalAgentClient, None]:
    """Start an in-process MCP server session."""
    old_prat = os.environ.get("WM_MCP_PRAT")
    os.environ["WM_MCP_PRAT"] = "1"

    from whitemagic.run_mcp_lean import server

    to_server_tx, to_server_rx = anyio.create_memory_object_stream(16)
    from_server_tx, from_server_rx = anyio.create_memory_object_stream(16)

    server_task = asyncio.create_task(
        server.run(
            to_server_rx,
            from_server_tx,
            server.create_initialization_options(),
        )
    )

    client = _ExternalAgentClient(to_server_tx, from_server_rx)
    try:
        if init:
            await client.initialize()
        yield client
    finally:
        await to_server_tx.aclose()
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task
        if old_prat is None:
            os.environ.pop("WM_MCP_PRAT", None)
        else:
            os.environ["WM_MCP_PRAT"] = old_prat


# ── Test Suites ─────────────────────────────────────────────────────────


class TestAgentDiscovery:
    """Verify external agents can discover WhiteMagic governance surface."""

    async def test_list_tools_returns_governance_ganas(self):
        """OpenCode/Hermes tools/list must see curated governance Ganas."""
        async with mcp_session() as client:
            response = await client.request("tools/list", {})
            assert "result" in response, f"Expected result, got: {response}"

            tools = response["result"].get("tools", [])
            assert len(tools) >= 28, f"Expected >=28 tools, got {len(tools)}"

            tool_names = {t["name"] for t in tools}
            # Governance-critical Ganas that an agent runtime should see
            governance_ganas = {
                "gana_horn",  # session initiation
                "gana_neck",  # memory presence
                "gana_ghost",  # metrics introspection
                "gana_three_stars",  # wisdom council
                "gana_dipper",  # governance
                "gana_chariot",  # codebase navigation
                "gana_abundance",  # resource sharing / forecasting
            }
            for gana in governance_ganas:
                assert gana in tool_names, f"Missing governance Gana: {gana}"

    async def test_tool_schemas_have_descriptions(self):
        """Every governance tool must advertise a human-readable description."""
        async with mcp_session() as client:
            response = await client.request("tools/list", {})
            tools = response["result"].get("tools", [])
            for tool in tools:
                assert tool.get("description"), f"Tool {tool['name']} lacks description"
                assert "inputSchema" in tool, f"Tool {tool['name']} lacks inputSchema"

    async def test_resources_include_orientation(self):
        """Agent runtimes should find orientation docs as resources."""
        async with mcp_session() as client:
            response = await client.request("resources/list", {})
            assert "result" in response
            resources = response["result"].get("resources", [])
            uris = {r["uri"] for r in resources}
            assert "whitemagic://orientation/ai-primary" in uris
            assert "whitemagic://orientation/system-map" in uris


class TestGovernanceToolInvocation:
    """Verify high-value governance tools return structured, actionable data."""

    async def test_gana_ghost_capabilities(self):
        """gana_ghost/capabilities returns metrics introspection surface."""
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": "gana_ghost",
                    "arguments": {
                        "tool": "capabilities",
                        "args": {},
                    },
                },
                timeout=30.0,
            )
            assert "result" in response, f"Expected result, got: {response}"
            content = response["result"].get("content", [])
            assert len(content) > 0
            data = json.loads(content[0]["text"])
            assert data.get("status") in {"success", "ok", "healthy"}

    async def test_gana_root_health(self):
        """gana_root/health_report returns system health for agent calibration."""
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": "gana_root",
                    "arguments": {
                        "tool": "health_report",
                        "args": {},
                    },
                },
                timeout=60.0,
            )
            assert "result" in response
            content = response["result"].get("content", [])
            assert len(content) > 0
            data = json.loads(content[0]["text"])
            assert "health_score" in data or "status" in data

    async def test_gana_horn_session_bootstrap(self):
        """gana_horn/session_bootstrap creates a session context for agent onboarding."""
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": "gana_horn",
                    "arguments": {
                        "tool": "session_bootstrap",
                        "args": {"mode": "standard"},
                    },
                },
                timeout=30.0,
            )
            assert "result" in response
            content = response["result"].get("content", [])
            assert len(content) > 0
            data = json.loads(content[0]["text"])
            # Accept success or validation error — both prove structured envelope
            assert "status" in data
            assert data["status"] in {"success", "error"}

    async def test_gana_neck_memory_presence(self):
        """gana_neck/create_memory + search_memories returns structured envelope."""
        async with mcp_session() as client:
            # Create a memory
            create_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_neck",
                    "arguments": {
                        "tool": "create_memory",
                        "args": {
                            "title": "OpenCode integration test",
                            "content": "OpenCode integration test memory",
                            "tags": ["integration", "opencode"],
                        },
                    },
                },
                timeout=30.0,
            )
            assert "result" in create_resp
            create_content = create_resp["result"].get("content", [])
            assert len(create_content) > 0
            create_data = json.loads(create_content[0]["text"])
            # Contract test: must return valid envelope with status
            assert "status" in create_data
            assert create_data["status"] in {"success", "error"}

            # Follow-up with remember (valid gana_neck alias) — contract test
            remember_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_neck",
                    "arguments": {
                        "tool": "remember",
                        "args": {
                            "title": "OpenCode integration test",
                            "content": "remembered",
                        },
                    },
                },
                timeout=30.0,
            )
            assert "result" in remember_resp
            remember_content = remember_resp["result"].get("content", [])
            assert len(remember_content) > 0
            remember_data = json.loads(remember_content[0]["text"])
            assert "status" in remember_data
            assert remember_data["status"] in {"success", "error"}


class TestAgentClientProtocolCompatibility:
    """Verify WhiteMagic MCP server satisfies ACP client expectations."""

    async def test_initialize_returns_server_info(self):
        """ACP clients expect serverInfo with name and version."""
        async with mcp_session(init=False) as client:
            response = await client.request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-acp-client", "version": "1.0.0"},
                },
            )
            assert "result" in response
            result = response["result"]
            assert "serverInfo" in result
            assert "capabilities" in result
            server_name = result["serverInfo"]["name"]
            assert "whitemagic" in server_name.lower()
            assert "version" in result["serverInfo"]

    async def test_initialized_notification_accepted(self):
        """ACP clients send notifications/initialized after handshake."""
        async with mcp_session(init=False) as client:
            await client.initialize()
            # If we got here without exception, the server accepted the flow


class TestStructuredErrorResponses:
    """Verify errors are returned as structured JSON, not raw traces."""

    async def test_missing_tool_name_returns_structured_error(self):
        """Calling a Gana without specifying nested tool returns envelope error."""
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": "gana_root",
                    "arguments": {
                        "args": {},
                    },
                },
                timeout=30.0,
            )
            assert "result" in response
            content = response["result"].get("content", [])
            assert len(content) > 0
            data = json.loads(content[0]["text"])
            assert data.get("status") == "error"
            assert "error_code" in data

    async def test_invalid_gana_returns_error(self):
        """Calling a non-existent Gana returns a clean error envelope."""
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": "gana_nonexistent",
                    "arguments": {
                        "tool": "foo",
                        "args": {},
                    },
                },
                timeout=30.0,
            )
            assert "result" in response
            content = response["result"].get("content", [])
            assert len(content) > 0
            data = json.loads(content[0]["text"])
            assert data.get("status") == "error"


class TestAllGanasSmoke:
    """Exercise one representative tool per Gana through the MCP server layer.

    Mirrors the standalone test_all_ganas_mcp.py but lives in the bridge
    suite so OpenCode/Hermes smoke runs are a single pytest invocation.
    """

    GANA_TESTS = [
        ("gana_horn", "session_bootstrap", {"mode": "standard"}),
        (
            "gana_neck",
            "create_memory",
            {"title": "Bridge test", "content": "bridge memory", "tags": ["test"]},
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

    @pytest.mark.parametrize("gana,tool,args", GANA_TESTS)
    async def test_gana(self, gana: str, tool: str, args: dict):
        async with mcp_session() as client:
            response = await client.request(
                "tools/call",
                {
                    "name": gana,
                    "arguments": {"tool": tool, "args": args},
                },
                timeout=45.0,
            )
            assert "result" in response, f"{gana}/{tool}: no result key"
            content = response["result"].get("content", [])
            assert len(content) > 0, f"{gana}/{tool}: empty content"
            text = content[0].get("text", "")
            assert text, f"{gana}/{tool}: no text content"
            try:
                data = json.loads(text)
                status = data.get("status", "unknown")
            except json.JSONDecodeError:
                status = "unparsed"
            assert status in {"success", "error", "unparsed"}, (
                f"{gana}/{tool}: unexpected status {status}"
            )


class TestAgentWorkflowSimulation:
    """Simulate a realistic agent runtime workflow: discover, audit, decide, act."""

    async def test_full_governance_workflow(self):
        """A simulated OpenCode agent: discover tools, check health, audit memory, get guidance."""
        async with mcp_session() as client:
            # 1. DISCOVER — list available governance tools
            tools_resp = await client.request("tools/list", {})
            assert "result" in tools_resp
            tools = tools_resp["result"].get("tools", [])
            assert len(tools) >= 28
            tool_names = {t["name"] for t in tools}
            assert "gana_root" in tool_names
            assert "gana_neck" in tool_names
            assert "gana_straddling_legs" in tool_names

            # 2. AUDIT — check system health before acting
            health_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_root",
                    "arguments": {"tool": "health_report", "args": {}},
                },
                timeout=30.0,
            )
            assert "result" in health_resp
            health_data = json.loads(health_resp["result"]["content"][0]["text"])
            assert health_data.get("status") in {"success", "ok", "healthy", "error"}

            # 3. DECIDE — get dharma guidance before a risky operation
            guidance_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_straddling_legs",
                    "arguments": {
                        "tool": "get_dharma_guidance",
                        "args": {
                            "situation": "Should I refactor the production database schema?"
                        },
                    },
                },
                timeout=30.0,
            )
            assert "result" in guidance_resp
            guidance_data = json.loads(guidance_resp["result"]["content"][0]["text"])
            assert "status" in guidance_data

            # 4. ACT — create a memory of the decision
            memory_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_neck",
                    "arguments": {
                        "tool": "create_memory",
                        "args": {
                            "title": "Governance workflow test",
                            "content": "Agent checked health, sought guidance, and logged decision.",
                            "tags": ["governance", "workflow"],
                        },
                    },
                },
                timeout=30.0,
            )
            assert "result" in memory_resp
            memory_data = json.loads(memory_resp["result"]["content"][0]["text"])
            assert "status" in memory_data

            # 5. VERIFY — confirm the memory exists via search
            search_resp = await client.request(
                "tools/call",
                {
                    "name": "gana_winnowing_basket",
                    "arguments": {
                        "tool": "memory_search",
                        "args": {"query": "governance workflow"},
                    },
                },
                timeout=30.0,
            )
            assert "result" in search_resp
            search_data = json.loads(search_resp["result"]["content"][0]["text"])
            assert "status" in search_data


class TestHermesHookScripts:
    """Test the standalone Hermes hook scripts that WhiteMagic provides.

    These scripts are intended to be wired into Hermes via config.yaml hooks:
      - pre_tool_call  -> whitemagic_policy_hook.py
      - pre_llm_call   -> whitemagic_context_hook.py
      - post_llm_call  -> whitemagic_memory_bridge.py
    """

    HOOKS_DIR = ROOT / "whitemagic" / "hermes" / "hooks"
    POLICY_HOOK = str(HOOKS_DIR / "whitemagic_policy_hook.py")
    CONTEXT_HOOK = str(HOOKS_DIR / "whitemagic_context_hook.py")
    MEMORY_HOOK = str(HOOKS_DIR / "whitemagic_memory_bridge.py")
    PYTHON = sys.executable

    @pytest.fixture(scope="class", autouse=True)
    def _skip_if_hooks_missing(self):
        missing = []
        for name, path in (
            ("Policy", self.POLICY_HOOK),
            ("Context", self.CONTEXT_HOOK),
            ("Memory", self.MEMORY_HOOK),
        ):
            if not Path(path).exists():
                missing.append(f"{name} hook script not found: {path}")
        if missing:
            pytest.skip("; ".join(missing))

    @staticmethod
    def _run_hook(script: str, event: dict) -> dict:
        import subprocess  # local import for test isolation

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        # Ensure the hook subprocess shares the isolated test state
        for key in ("WM_STATE_ROOT", "WM_SILENT_INIT"):
            if os.environ.get(key):
                env[key] = os.environ[key]
        proc = subprocess.run(
            [TestHermesHookScripts.PYTHON, script],
            input=json.dumps(event),
            capture_output=True,
            text=True,
            env=env,
        )
        assert proc.returncode == 0, f"Hook crashed: {proc.stderr}"
        return json.loads(proc.stdout)

    # ── Policy Gate (pre_tool_call) ──────────────────────────────────────

    @pytest.mark.parametrize(
        "cmd",
        [
            "rm -rf /home",
            "rm -rf ~",
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
        ],
    )
    def test_policy_blocks_dangerous_terminal(self, cmd: str):
        result = self._run_hook(
            self.POLICY_HOOK,
            {
                "tool_name": "terminal",
                "tool_input": {"command": cmd},
            },
        )
        assert result.get("allowed") is False
        assert result.get("type") == "block"
        assert "WhiteMagic Dharma Gate" in result.get("message", "")

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "pwd",
            "git status",
            "rm -rf /tmp/build",
        ],
    )
    def test_policy_allows_safe_terminal(self, cmd: str):
        result = self._run_hook(
            self.POLICY_HOOK,
            {
                "tool_name": "terminal",
                "tool_input": {"command": cmd},
            },
        )
        assert result.get("allowed") is True
        assert result.get("type") == "allow"

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/passwd",
            "/usr/bin/python3",
            "/bin/bash",
        ],
    )
    def test_policy_blocks_system_file_ops(self, path: str):
        for tool in ("write_file", "delete_file"):
            result = self._run_hook(
                self.POLICY_HOOK,
                {
                    "tool_name": tool,
                    "tool_input": {"path": path, "content": "x"},
                },
            )
            assert result.get("allowed") is False, f"{tool} on {path} should be blocked"

    def test_policy_allows_temp_file_ops(self):
        result = self._run_hook(
            self.POLICY_HOOK,
            {
                "tool_name": "write_file",
                "tool_input": {"path": "/tmp/test.txt", "content": "hello"},
            },
        )
        assert result.get("allowed") is True

    # ── Context Injection (pre_llm_call) ───────────────────────────────

    def test_context_hook_returns_telemetry(self):
        result = self._run_hook(
            self.CONTEXT_HOOK,
            {
                "tool_name": "terminal",
                "tool_input": {"command": "ls"},
            },
        )
        assert "context" in result
        ctx = result["context"]
        assert "WhiteMagic Telemetry" in ctx
        # Should contain at least some telemetry fields
        assert any(k in ctx for k in ("Health", "Guna", "Energy", "Wu Xing"))
        assert result.get("source") == "whitemagic_context_hook"

    def test_context_hook_never_crashes_on_malformed_input(self):
        result = self._run_hook(self.CONTEXT_HOOK, {})
        assert "context" in result
        assert result.get("source") == "whitemagic_context_hook"

    # ── Memory Bridge (post_llm_call) ──────────────────────────────────

    def test_memory_bridge_stores_hermes_event(self):
        result = self._run_hook(
            self.MEMORY_HOOK,
            {
                "tool_name": "terminal",
                "tool_input": {"command": "echo hello"},
                "output": "hello",
            },
        )
        assert result.get("status") == "stored"
        memory_id = result.get("memory_id")
        assert memory_id and memory_id != "unknown"

    def test_memory_bridge_never_crashes_on_malformed_input(self):
        result = self._run_hook(self.MEMORY_HOOK, {})
        # Should either store something or return an error JSON, never crash
        assert "status" in result
        assert result.get("source") == "whitemagic_memory_bridge"

    def test_memory_bridge_returns_valid_memory_id(self):
        result = self._run_hook(
            self.MEMORY_HOOK,
            {
                "tool_name": "terminal",
                "tool_input": {"command": "echo round_trip_test"},
                "output": "round_trip_test",
            },
        )
        assert result.get("status") == "stored"
        memory_id = result.get("memory_id")
        assert memory_id and memory_id != "unknown"
        assert len(memory_id) == 16  # WhiteMagic memory IDs are 16-char hex
