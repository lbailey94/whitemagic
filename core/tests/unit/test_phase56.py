# ruff: noqa: BLE001
"""Tests for Phase 5-6 — mesh CLI, install script, PWA daemon transport."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestMeshCommands:
    """Test mesh command registration."""

    def test_mesh_commands_importable(self):
        from whitemagic.cli.commands.mesh_commands import _register_mesh_commands
        assert callable(_register_mesh_commands)

    def test_mesh_status(self):
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()
        assert guard.privacy_status == "local_only"

    def test_mesh_enable_disable(self):
        from whitemagic.core.consciousness.network_guard import get_network_guard
        guard = get_network_guard()
        guard.set_mode("mesh_enabled")
        assert guard.privacy_status == "mesh_enabled"
        guard.set_mode("local_only")
        assert guard.privacy_status == "local_only"


class TestInstallScript:
    """Test install script exists."""

    def test_install_script_exists(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        install_script = repo_root / "scripts" / "install.sh"
        assert install_script.exists(), f"install.sh not found at {install_script}"

    def test_install_script_executable(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        install_script = repo_root / "scripts" / "install.sh"
        assert os.access(install_script, os.X_OK), "install.sh should be executable"

    def test_install_script_content(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        install_script = repo_root / "scripts" / "install.sh"
        content = install_script.read_text()
        assert "whitemagic" in content.lower()
        assert "daemon" in content.lower()
        assert "pip install" in content


class TestPWADaemonTransport:
    """Test PWA daemon transport file exists."""

    def test_daemon_transport_exists(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        transport_file = repo_root / "sdk" / "typescript" / "src" / "daemon_transport.ts"
        assert transport_file.exists(), f"daemon_transport.ts not found at {transport_file}"

    def test_daemon_transport_content(self):
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        transport_file = repo_root / "sdk" / "typescript" / "src" / "daemon_transport.ts"
        content = transport_file.read_text()
        assert "DaemonTransport" in content
        assert "WebSocket" in content
        assert "callTool" in content
        assert "createSession" in content
        assert "localhost" in content
