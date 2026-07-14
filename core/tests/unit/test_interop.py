# ruff: noqa: BLE001
"""Tests for wm interop commands — agent detection, MCP config, registry."""

from __future__ import annotations

import json
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestInteropCommands:
    """Test interop command registration and functionality."""

    def test_interop_commands_importable(self):
        from whitemagic.cli.commands.interop_commands import _register_interop_commands
        assert callable(_register_interop_commands)

    def test_known_agents_defined(self):
        from whitemagic.cli.commands.interop_commands import KNOWN_AGENTS
        assert "hermes" in KNOWN_AGENTS
        assert "gemini-cli" in KNOWN_AGENTS
        assert "opencode" in KNOWN_AGENTS
        assert "claude-code" in KNOWN_AGENTS
        assert "cascade" in KNOWN_AGENTS

    def test_known_agents_have_required_fields(self):
        from whitemagic.cli.commands.interop_commands import KNOWN_AGENTS
        for agent_id, info in KNOWN_AGENTS.items():
            assert "display_name" in info, f"{agent_id} missing display_name"
            assert "binary_names" in info, f"{agent_id} missing binary_names"
            assert "config_paths" in info, f"{agent_id} missing config_paths"
            assert "config_format" in info, f"{agent_id} missing config_format"
            assert "mcp_key" in info, f"{agent_id} missing mcp_key"

    def test_detect_agent_not_installed(self):
        from whitemagic.cli.commands.interop_commands import _detect_agent
        # An agent that's definitely not installed
        info = {
            "binary_names": ["nonexistent_agent_xyz"],
            "config_paths": ["~/.nonexistent_agent_xyz/config.json"],
        }
        assert _detect_agent(info) is False

    def test_mcp_server_config(self):
        from whitemagic.cli.commands.interop_commands import _mcp_server_config
        config = _mcp_server_config()
        assert "whitemagic" in config
        assert "command" in config["whitemagic"]
        assert "args" in config["whitemagic"]

    def test_write_mcp_config_json(self, tmp_path):
        from whitemagic.cli.commands.interop_commands import _write_mcp_config
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"existing": "value"}))

        info = {
            "config_paths": [str(config_file)],
            "config_format": "json",
            "mcp_key": "mcpServers",
        }
        result = _write_mcp_config("test-agent", info)
        assert result is True

        data = json.loads(config_file.read_text())
        assert "mcpServers" in data
        assert "whitemagic" in data["mcpServers"]
        assert data["existing"] == "value"  # existing config preserved

    def test_write_mcp_config_creates_new(self, tmp_path):
        from whitemagic.cli.commands.interop_commands import _write_mcp_config
        config_file = tmp_path / "new_config.json"
        info = {
            "config_paths": [str(config_file)],
            "config_format": "json",
            "mcp_key": "mcpServers",
        }
        result = _write_mcp_config("test-agent", info)
        assert result is True
        assert config_file.exists()

        data = json.loads(config_file.read_text())
        assert "mcpServers" in data
        assert "whitemagic" in data["mcpServers"]

    def test_register_in_wm_registry(self):
        from whitemagic.cli.commands.interop_commands import _register_in_wm_registry
        info = {
            "display_name": "Test Agent",
            "description": "Test",
        }
        _register_in_wm_registry("test-agent", info)

        # Verify it was registered
        from whitemagic.tools.handlers.agent_registry import _load_agent
        agent = _load_agent("external-test-agent")
        assert agent is not None
        assert agent["name"] == "Test Agent"


class TestAgentRegistryIntegration:
    """Test that the agent registry works for interop."""

    def test_register_and_list(self):
        from whitemagic.tools.handlers.agent_registry import (
            handle_agent_list,
            handle_agent_register,
        )
        result = handle_agent_register(
            name="Interop Test",
            agent_id="interop-test-1",
            capabilities=["mcp", "coding"],
        )
        assert result["status"] == "success"

        listing = handle_agent_list()
        assert listing["status"] == "success"
        ids = [a["id"] for a in listing["agents"]]
        assert "interop-test-1" in ids

    def test_heartbeat(self):
        from whitemagic.tools.handlers.agent_registry import (
            handle_agent_heartbeat,
            handle_agent_register,
        )
        handle_agent_register(
            name="Heartbeat Test",
            agent_id="hb-test-1",
        )
        result = handle_agent_heartbeat(agent_id="hb-test-1")
        assert result["status"] == "success"
        assert result["heartbeat_count"] == 1

    def test_deregister(self):
        from whitemagic.tools.handlers.agent_registry import (
            handle_agent_deregister,
            handle_agent_register,
        )
        handle_agent_register(
            name="Dereg Test",
            agent_id="dereg-test-1",
        )
        result = handle_agent_deregister(agent_id="dereg-test-1")
        assert result["status"] == "success"
