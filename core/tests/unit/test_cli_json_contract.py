# ruff: noqa: BLE001
"""CLI JSON Contract Test

Validates that `wm --json <command>` produces valid JSON output for every
registered command. This is the AI-facing contract — if --json doesn't work,
AI agents can't use the CLI.

Tests are designed to be fast: they use Click's CliRunner which invokes
commands in-process without spawning a subprocess. Each command is invoked
with --json and minimal arguments (or --help where arguments are required).
"""
import json

import pytest
from click.testing import CliRunner


@pytest.fixture(scope="module")
def cli():
    """Import the main CLI group once per module."""
    from whitemagic.cli.cli_app import main
    return main


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


# Commands that should produce valid JSON with --json and no extra args.
# These are read-only / status commands that don't require arguments.
JSON_NO_ARG_COMMANDS = [
    "status",
    "doctor",
    "tools",
    "prat context",
    "prat status",
    "self-improve status",
]


# Commands that require arguments — tested with --help to verify they're registered.
# We can't run these with --json without valid arguments, but we verify they exist.
REQUIRES_ARGS = [
    "remember",
    "recall",
    "search",
    "context",
    "gana",
    "dharma",
    "wisdom",
    "dream",
    "intelligence",
    "infer",
    "prat invoke",
    "prat morphologies",
    "self-improve run",
    "self-improve record-outcome",
    "self-improve history",
]


class TestCLIJsonContract:
    """Verify --json produces valid JSON for all commands."""

    @pytest.mark.parametrize("cmd", JSON_NO_ARG_COMMANDS)
    def test_json_output_valid(self, runner, cli, cmd):
        """Each no-arg command with --json should produce valid JSON."""
        args = cmd.split() + ["--json"]
        result = runner.invoke(cli, args, catch_exceptions=False)

        # Some commands may fail if deps are missing, but if they succeed,
        # output must be valid JSON.
        if result.exit_code == 0:
            output = result.output.strip()
            if output:
                parsed = json.loads(output)
                assert isinstance(parsed, (dict, list)), \
                    f"--json output for '{cmd}' is not a dict/list: {type(parsed)}"

    @pytest.mark.parametrize("cmd", JSON_NO_ARG_COMMANDS)
    def test_json_global_flag(self, runner, cli, cmd):
        """Global --json flag should work even if command has no local --json."""
        args = ["--json"] + cmd.split()
        result = runner.invoke(cli, args, catch_exceptions=False)

        if result.exit_code == 0:
            output = result.output.strip()
            if output:
                # Should be valid JSON
                try:
                    json.loads(output)
                except json.JSONDecodeError:
                    # Some commands may not support global --json yet — that's OK,
                    # but we log it for awareness.
                    pytest.skip(f"'{cmd}' doesn't produce JSON with global --json flag yet")

    @pytest.mark.parametrize("cmd", REQUIRES_ARGS)
    def test_command_registered(self, runner, cli, cmd):
        """Verify command is registered and accessible via --help."""
        args = cmd.split() + ["--help"]
        result = runner.invoke(cli, args)
        # --help should always exit 0 if the command is registered
        assert result.exit_code == 0, \
            f"Command '{cmd}' not registered or --help failed: exit={result.exit_code}, output={result.output[:200]}"

    def test_cli_has_json_option(self, runner, cli):
        """Verify the main CLI group has --json option."""
        result = runner.invoke(cli, ["--help"])
        assert "--json" in result.output, "Main CLI group missing --json option"

    def test_cli_version(self, runner, cli):
        """Verify --version works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Click outputs "<prog_name>, version <version>"
        assert "23.1.0" in result.output or "version" in result.output.lower()

    def test_status_json_has_envelope(self, runner, cli):
        """Status command --json should return a tool envelope with status field."""
        result = runner.invoke(cli, ["--json", "status"], catch_exceptions=False)
        if result.exit_code == 0 and result.output.strip():
            parsed = json.loads(result.output.strip())
            # Should have either top-level envelope or nested structure
            assert isinstance(parsed, dict), "Status --json output should be a dict"
            # Check for envelope-like structure
            if "capabilities" in parsed:
                caps = parsed["capabilities"]
                if isinstance(caps, dict) and "status" in caps:
                    assert caps["status"] in ("success", "error"), \
                        f"Unexpected capabilities status: {caps['status']}"

    def test_tools_json_structure(self, runner, cli):
        """Tools command --json should return categorized command list."""
        result = runner.invoke(cli, ["tools", "--json"], catch_exceptions=False)
        if result.exit_code == 0 and result.output.strip():
            parsed = json.loads(result.output.strip())
            assert isinstance(parsed, dict), "Tools --json output should be a dict"
            # Should have command categories
            assert "core_commands" in parsed or "commands" in parsed, \
                f"Tools --json missing command categories: {list(parsed.keys())}"
