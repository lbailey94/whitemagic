# ruff: noqa: BLE001
"""WhiteMagic interop CLI — auto-configure external AI agents for collaboration.

Detects installed AI agents (Hermes, Gemini CLI, OpenCode, Claude Code, etc.)
and writes their MCP configuration to connect to WhiteMagic as a shared
consciousness substrate. Also manages the agent registry and Sangha chat
channels for inter-agent collaboration.

Commands:
    wm interop scan       — Detect installed AI agents
    wm interop connect    — Configure an agent to use WhiteMagic MCP
    wm interop agents     — List registered agents
    wm interop chat       — Read/send Sangha chat messages
    wm interop channels   — List active Sangha channels
    wm interop status     — Show interop status (agents, channels, broker)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)

# Known agent configurations — how to detect and configure each
KNOWN_AGENTS: dict[str, dict[str, Any]] = {
    "hermes": {
        "display_name": "Hermes",
        "binary_names": ["hermes"],
        "config_paths": [
            "~/.hermes/config.json",
            "~/.config/hermes/config.json",
        ],
        "config_format": "json",
        "mcp_key": "mcpServers",
        "description": "Hermes AI coding agent",
    },
    "gemini-cli": {
        "display_name": "Gemini CLI",
        "binary_names": ["gemini"],
        "config_paths": [
            "~/.gemini/config.json",
            "~/.config/gemini-cli/config.json",
        ],
        "config_format": "json",
        "mcp_key": "mcpServers",
        "description": "Google Gemini CLI agent",
    },
    "opencode": {
        "display_name": "OpenCode",
        "binary_names": ["opencode"],
        "config_paths": [
            "~/.opencode/config.json",
            "~/.config/opencode/config.json",
            "./opencode.json",
        ],
        "config_format": "json",
        "mcp_key": "mcpServers",
        "description": "OpenCode AI coding agent",
    },
    "claude-code": {
        "display_name": "Claude Code",
        "binary_names": ["claude"],
        "config_paths": [
            "~/.claude-code/config.json",
            "~/.config/claude-code/config.json",
        ],
        "config_format": "json",
        "mcp_key": "mcpServers",
        "description": "Anthropic Claude Code agent",
    },
    "cascade": {
        "display_name": "Cascade (Windsurf)",
        "binary_names": ["windsurf"],
        "config_paths": [
            "~/.codeium/windsurf/windsurf/config.json",
        ],
        "config_format": "json",
        "mcp_key": "mcpServers",
        "description": "Codeium Cascade IDE agent",
    },
    "aider": {
        "display_name": "Aider",
        "binary_names": ["aider"],
        "config_paths": [
            "~/.aider.conf.yml",
        ],
        "config_format": "yaml",
        "mcp_key": "mcp_servers",
        "description": "Aider AI pair programmer",
    },
}


def _register_interop_commands(cli: click.Group) -> None:
    """Register interop commands with the CLI group."""

    @cli.group()
    def interop() -> None:
        """Inter-agent collaboration and MCP auto-configuration."""
        pass

    @interop.command()
    def scan() -> None:
        """Detect installed AI agents on this system."""
        click.echo("🌐 WhiteMagic Interop — Agent Scan")
        click.echo("=" * 50)
        click.echo()

        found = 0
        for agent_id, info in KNOWN_AGENTS.items():
            binary = None
            for bin_name in info["binary_names"]:
                binary = shutil.which(bin_name)
                if binary:
                    break

            config_path = None
            for cp in info["config_paths"]:
                expanded = os.path.expanduser(cp)
                if os.path.exists(expanded):
                    config_path = expanded
                    break

            status_parts = []
            if binary:
                status_parts.append(f"binary: {binary}")
            if config_path:
                status_parts.append(f"config: {config_path}")

            if status_parts:
                click.echo(f"  ✅ {info['display_name']:20s} {' | '.join(status_parts)}")
                found += 1
            else:
                click.echo(f"  ⬜ {info['display_name']:20s} not found")

        click.echo()
        click.echo(f"Found {found} agent(s).")
        if found > 0:
            click.echo()
            click.echo("Run 'wm interop connect <agent>' to configure MCP.")
        else:
            click.echo("No agents found. Install an agent to enable interop.")

    @interop.command()
    @click.argument("agent_name", required=False)
    @click.option("--all", "connect_all", is_flag=True, help="Connect all detected agents")
    def connect(agent_name: str | None, connect_all: bool) -> None:
        """Configure an agent to use WhiteMagic MCP server."""
        if connect_all:
            # Connect all detected agents
            connected = []
            for agent_id, info in KNOWN_AGENTS.items():
                if _detect_agent(info):
                    if _write_mcp_config(agent_id, info):
                        _register_in_wm_registry(agent_id, info)
                        connected.append(info["display_name"])
            if connected:
                click.echo(f"✅ Configured {len(connected)} agent(s): {', '.join(connected)}")
            else:
                click.echo("No agents detected. Run 'wm interop scan' first.")
            return

        if not agent_name:
            click.echo("Usage: wm interop connect <agent_name>")
            click.echo("Available agents: " + ", ".join(KNOWN_AGENTS.keys()))
            click.echo("Or use --all to connect all detected agents.")
            return

        agent_id = agent_name.lower().replace(" ", "-")
        if agent_id not in KNOWN_AGENTS:
            click.echo(f"Unknown agent: {agent_name}")
            click.echo("Available: " + ", ".join(KNOWN_AGENTS.keys()))
            return

        info = KNOWN_AGENTS[agent_id]
        if not _detect_agent(info):
            click.echo(f"❌ {info['display_name']} not detected on this system")
            click.echo("   Install it first, then run this command again.")
            return

        if _write_mcp_config(agent_id, info):
            click.echo(f"✅ {info['display_name']} configured to use WhiteMagic MCP")
            click.echo()
            click.echo("   The agent now has access to:")
            click.echo("     • 490 WhiteMagic tools (memory, search, governance, dream cycle)")
            click.echo("     • Session memory (conversation turns auto-recorded)")
            click.echo("     • Citta stream (consciousness continuity)")
            click.echo("     • Sangha chat (inter-agent messaging)")
            click.echo("     • Agent registry (collaboration, heartbeats)")
            click.echo()
            click.echo("   Restart the agent to activate the MCP server.")

            # Also register in WhiteMagic's agent registry
            _register_in_wm_registry(agent_id, info)
        else:
            click.echo(f"❌ Failed to configure {info['display_name']}")

    @interop.command()
    @click.option("--active", is_flag=True, help="Show only active agents")
    def agents(active: bool) -> None:
        """List registered agents in WhiteMagic's registry."""
        try:
            from whitemagic.tools.handlers.agent_registry import _all_agents, _is_active
            all_agents = _all_agents()

            if active:
                all_agents = [a for a in all_agents if _is_active(a)]

            if not all_agents:
                click.echo("No agents registered.")
                click.echo("Run 'wm interop connect <agent>' to register an agent.")
                return

            click.echo(f"Registered Agents ({len(all_agents)}):")
            click.echo("-" * 60)
            for a in all_agents:
                status = "🟢 active" if _is_active(a) else "🔴 stale"
                caps = ", ".join(a.get("capabilities", [])[:4])
                click.echo(
                    f"  {a.get('name', 'unknown'):20s} {status:12s} "
                    f"caps: {caps or 'none'}"
                )
        except Exception as e:
            click.echo(f"Error: {e}")

    @interop.command()
    @click.option("--channel", "-c", default="general", help="Channel name")
    @click.option("--limit", "-n", default=10, help="Number of messages")
    @click.option("--send", "-s", help="Send a message instead of reading")
    @click.option("--sender", help="Sender ID (default: user)")
    def chat(channel: str, limit: int, send: str | None, sender: str | None) -> None:
        """Read or send Sangha chat messages."""
        try:
            if send:
                from whitemagic.gardens.sangha.chat import get_chat
                chat = get_chat()
                msg = chat.send_message(
                    sender_id=sender or "user",
                    content=send,
                    channel=channel,
                )
                click.echo(f"✅ Sent to #{channel} (id={msg.id})")
            else:
                from whitemagic.gardens.sangha.chat import get_chat
                chat = get_chat()
                messages = chat.read_messages(channel=channel, limit=limit)

                if not messages:
                    click.echo(f"No messages in #{channel}")
                    return

                click.echo(f"#{channel} ({len(messages)} messages):")
                click.echo("-" * 60)
                for m in messages:
                    time_str = m.timestamp.strftime("%H:%M:%S") if m.timestamp else "?"
                    click.echo(f"  [{time_str}] {m.sender_id}: {m.content[:80]}")
        except Exception as e:
            click.echo(f"Error: {e}")

    @interop.command()
    def channels() -> None:
        """List active Sangha chat channels."""
        try:
            from whitemagic.gardens.sangha.chat import get_chat
            chat = get_chat()
            channels = getattr(chat, "channels", None)
            if channels:
                click.echo(f"Active channels: {', '.join(channels)}")
            else:
                click.echo("No active channels. Send a message with 'wm interop chat -c <channel> -s <msg>'")
        except Exception as e:
            click.echo(f"Error: {e}")

    @interop.command()
    def status() -> None:
        """Show full interop status."""
        click.echo("🌐 WhiteMagic Interop Status")
        click.echo("=" * 50)
        click.echo()

        # Agent registry
        try:
            from whitemagic.tools.handlers.agent_registry import _all_agents, _is_active
            agents = _all_agents()
            active = [a for a in agents if _is_active(a)]
            click.echo(f"Agent Registry: {len(active)} active / {len(agents)} total")
        except Exception:
            click.echo("Agent Registry: unavailable")

        # Sangha chat
        try:
            from whitemagic.gardens.sangha.chat import get_chat
            chat = get_chat()
            channels = getattr(chat, "channels", None)
            click.echo(f"Sangha Chat:    {len(channels) if channels else 0} channels")
        except Exception:
            click.echo("Sangha Chat:    unavailable")

        # Broker
        try:
            from whitemagic.tools.handlers.broker import _resolve_redis_url
            redis_url = _resolve_redis_url()
            if redis_url:
                click.echo(f"Broker:         Redis configured ({redis_url[:20]}...)")
            else:
                click.echo("Broker:         not configured (set REDIS_URL for pub/sub)")
        except Exception:
            click.echo("Broker:         unavailable")

        # Daemon
        try:
            from whitemagic.core.consciousness.daemon import get_daemon
            d = get_daemon()
            click.echo(f"Daemon:         {'running' if d.is_running else 'stopped'}")
        except Exception:
            click.echo("Daemon:         unavailable")

        # Gateway
        try:
            from whitemagic.mesh.cognitive_client import CognitiveClient
            client = CognitiveClient()
            if client.connect():
                click.echo("Gateway:        connected")
                client.close()
            else:
                click.echo("Gateway:        not running")
        except Exception:
            click.echo("Gateway:        unavailable")

        # MCP server
        click.echo()
        click.echo("MCP Server Config:")
        click.echo("  Add to your agent's config:")
        click.echo(json.dumps(_mcp_server_config(), indent=2))


def _detect_agent(info: dict[str, Any]) -> bool:
    """Check if an agent is installed on this system."""
    for bin_name in info["binary_names"]:
        if shutil.which(bin_name):
            return True
    for cp in info["config_paths"]:
        if os.path.exists(os.path.expanduser(cp)):
            return True
    return False


def _mcp_server_config() -> dict[str, Any]:
    """Generate the MCP server config for WhiteMagic."""
    wm_path = shutil.which("wm")
    if not wm_path:
        # Fallback: use python -m
        wm_path = "python -m whitemagic.cli.cli_app"
        return {
            "whitemagic": {
                "command": "python",
                "args": ["-m", "whitemagic.cli.cli_app", "mcp", "serve"],
            }
        }
    return {
        "whitemagic": {
            "command": wm_path,
            "args": ["mcp", "serve"],
        }
    }


def _write_mcp_config(agent_id: str, info: dict[str, Any]) -> bool:
    """Write MCP server config to an agent's configuration file."""
    mcp_config = _mcp_server_config()

    # Find the config file
    config_path = None
    for cp in info["config_paths"]:
        expanded = os.path.expanduser(cp)
        p = Path(expanded)
        if p.exists():
            config_path = p
            break

    if config_path is None:
        # Create at first path
        config_path = Path(os.path.expanduser(info["config_paths"][0]))
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("{}")
    elif config_path.suffix == ".yml":
        # YAML config (aider) — append mcp_servers section
        existing = config_path.read_text()
        if "whitemagic" not in existing:
            yaml_section = "\n# WhiteMagic MCP server\nmcp_servers:\n"
            for name, cfg in mcp_config.items():
                yaml_section += f"  {name}:\n"
                yaml_section += f"    command: {cfg['command']}\n"
                yaml_section += f"    args: {json.dumps(cfg['args'])}\n"
            config_path.write_text(existing + yaml_section)
        return True

    # JSON config
    try:
        existing = json.loads(config_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        existing = {}

    mcp_key = info.get("mcp_key", "mcpServers")
    if mcp_key not in existing:
        existing[mcp_key] = {}

    existing[mcp_key].update(mcp_config)
    config_path.write_text(json.dumps(existing, indent=2))
    return True


def _register_in_wm_registry(agent_id: str, info: dict[str, Any]) -> None:
    """Register the external agent in WhiteMagic's agent registry."""
    try:
        from whitemagic.tools.handlers.agent_registry import handle_agent_register
        handle_agent_register(
            name=info["display_name"],
            agent_id=f"external-{agent_id}",
            capabilities=["mcp", "interop", "external"],
            metadata={
                "type": "external",
                "agent_id": agent_id,
                "description": info.get("description", ""),
            },
        )
    except Exception as e:
        logger.warning("Failed to register agent in WM registry: %s", e)
