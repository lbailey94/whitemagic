"""Unit tests for cross-AI galaxy sharing protocol (P4.4)."""

import pytest

from whitemagic.core.memory.galaxy_sharing import (
    PROTOCOL_VERSION,
    create_galaxy_package,
    receive_galaxy_package,
    verify_galaxy_package,
)
from whitemagic.core.memory.unified import reset_singleton, get_unified_memory


@pytest.fixture
def um():
    reset_singleton()
    instance = get_unified_memory()
    yield instance
    reset_singleton()


def _make_test_snapshot():
    return {
        "galaxy_meta": {
            "galaxy": "test_share",
            "memory_count": 2,
            "association_count": 1,
            "snapshot_at": "2026-07-12T13:00:00",
            "format": "snapshot_v1",
        },
        "memories": [
            {
                "id": "mem-1",
                "title": "Test Memory 1",
                "content": "content one",
                "importance": 0.8,
                "memory_type": "LONG_TERM",
                "tags": ["test"],
                "galaxy": "test_share",
                "emotional_valence": 0.5,
                "metadata": {},
                "coords": None,
            },
            {
                "id": "mem-2",
                "title": "Test Memory 2",
                "content": "content two",
                "importance": 0.6,
                "memory_type": "SHORT_TERM",
                "tags": [],
                "galaxy": "test_share",
                "emotional_valence": 0.0,
                "metadata": {},
                "coords": None,
            },
        ],
        "associations": [
            {"source_id": "mem-1", "target_id": "mem-2", "strength": 0.7},
        ],
    }


class TestCreateGalaxyPackage:
    """Test package creation."""

    def test_create_package_structure(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot, source_instance="test/instance")
        assert "manifest" in pkg
        assert "snapshot" in pkg
        assert pkg["manifest"]["format"] == PROTOCOL_VERSION
        assert pkg["manifest"]["source_ai"] == "whitemagic"
        assert pkg["manifest"]["source_instance"] == "test/instance"
        assert pkg["manifest"]["galaxy"] == "test_share"
        assert "content_hash" in pkg["manifest"]
        assert pkg["manifest"]["content_hash"].startswith("sha256:")
        assert pkg["manifest"]["memory_count"] == 2
        assert pkg["manifest"]["association_count"] == 1

    def test_create_package_with_custom_trust(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot, trust_level="quarantined")
        assert pkg["manifest"]["trust_level"] == "quarantined"

    def test_create_package_with_custom_capabilities(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot, capabilities=["search", "recall"])
        assert pkg["manifest"]["capabilities"] == ["search", "recall"]

    def test_create_package_default_capabilities(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        assert "search" in pkg["manifest"]["capabilities"]
        assert "restore" in pkg["manifest"]["capabilities"]


class TestVerifyGalaxyPackage:
    """Test package verification."""

    def test_verify_valid_package(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        result = verify_galaxy_package(pkg)
        assert result["valid"] is True
        assert result["memory_count"] == 2
        assert result["trust_level"] == "verified"

    def test_verify_missing_manifest(self):
        result = verify_galaxy_package({"snapshot": {}})
        assert result["valid"] is False
        assert "manifest" in result["error"]

    def test_verify_missing_snapshot(self):
        result = verify_galaxy_package({"manifest": {}})
        assert result["valid"] is False
        assert "snapshot" in result["error"]

    def test_verify_wrong_format(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        pkg["manifest"]["format"] = "wrong_format"
        result = verify_galaxy_package(pkg)
        assert result["valid"] is False
        assert "Unsupported format" in result["error"]

    def test_verify_hash_mismatch(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        pkg["manifest"]["content_hash"] = "sha256:wronghash"
        result = verify_galaxy_package(pkg)
        assert result["valid"] is False
        assert "hash mismatch" in result["error"].lower()

    def test_verify_missing_manifest_fields(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        del pkg["manifest"]["source_ai"]
        result = verify_galaxy_package(pkg)
        assert result["valid"] is False
        assert "source_ai" in str(result["error"])

    def test_verify_tampered_snapshot(self):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        pkg["snapshot"]["memories"].append({"id": "fake", "content": "tampered"})
        result = verify_galaxy_package(pkg)
        assert result["valid"] is False
        assert "hash mismatch" in result["error"].lower()


class TestReceiveGalaxyPackage:
    """Test package receiving."""

    def test_receive_valid_package(self, um):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        result = receive_galaxy_package(pkg, target_galaxy="test_receive")
        assert result["status"] == "success"
        assert result["import"]["memories_restored"] == 2
        assert result["import"]["associations_restored"] == 1
        assert result["quarantined"] is False

    def test_receive_quarantine_mode(self, um):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot, trust_level="unverified")
        result = receive_galaxy_package(pkg, quarantine=True)
        assert result["status"] == "success"
        assert result["quarantined"] is True
        assert "quarantine/" in result["import"]["galaxy"]

    def test_receive_invalid_package(self, um):
        result = receive_galaxy_package({"manifest": {}, "snapshot": {}})
        assert result["status"] == "error"
        assert "verification failed" in result["error"]

    def test_receive_tampered_package(self, um):
        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        pkg["snapshot"]["galaxy_meta"]["memory_count"] = 999
        result = receive_galaxy_package(pkg)
        assert result["status"] == "error"
        assert "hash mismatch" in result["error"].lower()


class TestHandlerIntegration:
    """Test MCP tool handlers."""

    def test_handle_galaxy_package(self, um):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_package

        um.store("package test content", galaxy="pkg_test")
        result = handle_galaxy_package(galaxy="pkg_test")
        assert result["status"] == "success"
        assert "manifest" in result
        assert "package" in result
        assert result["manifest"]["format"] == PROTOCOL_VERSION

    def test_handle_galaxy_receive(self, um):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_receive

        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot)
        result = handle_galaxy_receive(package=pkg, target_galaxy="handler_recv")
        assert result["status"] == "success"
        assert result["import"]["memories_restored"] == 2

    def test_handle_galaxy_receive_missing_package(self):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_receive

        result = handle_galaxy_receive()
        assert result["status"] == "error"

    def test_handle_galaxy_receive_quarantine(self, um):
        from whitemagic.tools.handlers.galaxy import handle_galaxy_receive

        snapshot = _make_test_snapshot()
        pkg = create_galaxy_package(snapshot, trust_level="quarantined")
        result = handle_galaxy_receive(package=pkg, quarantine=True)
        assert result["status"] == "success"
        assert result["quarantined"] is True
