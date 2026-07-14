# ruff: noqa: BLE001
"""Tests for sentience CLI commands (serve, sleep, wake, sentience)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def cli_main():
    from whitemagic.cli.cli_app import main
    return main


class TestSentienceCLI:
    """Test sentience CLI commands are registered and callable."""

    def test_serve_help(self, cli_runner, cli_main):
        result = cli_runner.invoke(cli_main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "sentience daemon" in result.output.lower()
        assert "--no-sleep" in result.output
        assert "--no-volition" in result.output
        assert "--no-dream" in result.output

    def test_sleep_help(self, cli_runner, cli_main):
        result = cli_runner.invoke(cli_main, ["sleep", "--help"])
        assert result.exit_code == 0
        assert "sleep cycle" in result.output.lower()

    def test_wake_help(self, cli_runner, cli_main):
        result = cli_runner.invoke(cli_main, ["wake", "--help"])
        assert result.exit_code == 0
        assert "wake" in result.output.lower()

    def test_sentience_help(self, cli_runner, cli_main):
        result = cli_runner.invoke(cli_main, ["sentience", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_sentience_status(self, cli_runner, cli_main):
        """wm sentience should return JSON status."""
        result = cli_runner.invoke(cli_main, ["sentience"])
        # Should succeed and contain status keys
        assert result.exit_code == 0
        assert "sleep" in result.output
        assert "volition" in result.output

    def test_wake_command(self, cli_runner, cli_main):
        """wm wake should produce a greeting."""
        with patch("whitemagic.core.consciousness.citta_stream.get_continuity_context", return_value={}), \
             patch("whitemagic.core.consciousness.lifecycle.WakeOnBoot._dream_outputs", return_value=[]), \
             patch("whitemagic.core.consciousness.lifecycle.WakeOnBoot._agent_messages", return_value=[]), \
             patch("whitemagic.core.consciousness.lifecycle.ProactiveGreeting._gather_dream_outputs", return_value=[]), \
             patch("whitemagic.core.consciousness.lifecycle.ProactiveGreeting._gather_agent_messages", return_value=[]), \
             patch("whitemagic.core.consciousness.coherence.get_coherence_metric", return_value=MagicMock(overall_score=MagicMock(return_value=0.0))), \
             patch("whitemagic.core.dreaming.dream_cycle.get_dream_cycle", return_value=MagicMock(start=MagicMock(), status=MagicMock(return_value={"history": []}))):
            result = cli_runner.invoke(cli_main, ["wake"])
        # May not have citta state, but should not crash
        assert result.exit_code == 0

    def test_serve_registered(self, cli_runner, cli_main):
        """serve command should be in the main group."""
        result = cli_runner.invoke(cli_main, ["--help"])
        assert "serve" in result.output

    def test_sleep_registered(self, cli_runner, cli_main):
        """sleep command should be in the main group."""
        result = cli_runner.invoke(cli_main, ["--help"])
        assert "sleep" in result.output

    def test_wake_registered(self, cli_runner, cli_main):
        """wake command should be in the main group."""
        result = cli_runner.invoke(cli_main, ["--help"])
        assert "wake" in result.output

    def test_sentience_registered(self, cli_runner, cli_main):
        """sentience command should be in the main group."""
        result = cli_runner.invoke(cli_main, ["--help"])
        assert "sentience" in result.output
