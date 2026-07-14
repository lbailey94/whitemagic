# ruff: noqa: BLE001
"""Tests for WASM Compute Verification (v24.3 §4.2)."""
from __future__ import annotations

import pytest

from whitemagic.security.wasm_verifier import (
    VERIFIABLE_TOOLS,
    VerificationRequest,
)


@pytest.fixture
def verifier(tmp_path, monkeypatch):
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    import importlib

    import whitemagic.config.paths as paths_mod
    importlib.reload(paths_mod)
    import whitemagic.security.wasm_verifier as wv_mod
    importlib.reload(wv_mod)
    return wv_mod.WasmVerifier()


class TestWasmVerifier:
    def test_checksum_verify_deterministic(self, verifier):
        """Same inputs produce same checksum."""
        inputs = {"query": "test", "limit": 10}
        outputs = {"status": "success", "results": []}

        req = VerificationRequest(
            tool_name="memory_search",
            inputs=inputs,
            outputs=outputs,
        )
        # First call — no cache, falls to replay (permissive)
        verifier.verify(req)
        # Update cache
        verifier._update_checksum_cache(req)

        # Second call with same inputs/outputs — should match
        result2 = verifier.verify(req)
        assert result2.verified
        assert result2.method == "checksum"

    def test_verification_detects_mismatch(self, verifier):
        """Tampered outputs are flagged."""
        inputs = {"query": "test"}
        outputs = {"status": "success", "results": ["a", "b"]}

        req = VerificationRequest(
            tool_name="memory_search",
            inputs=inputs,
            outputs=outputs,
        )
        verifier._update_checksum_cache(req)

        # Tamper with outputs
        tampered_req = VerificationRequest(
            tool_name="memory_search",
            inputs=inputs,
            outputs={"status": "success", "results": ["a", "b", "c"]},
        )
        verifier.verify(tampered_req)
        # Checksum should fail, replay may or may not match
        # The key is that checksum method detects the mismatch
        checksum_result = verifier._checksum_verify(tampered_req)
        assert not checksum_result.verified
        assert "mismatch" in checksum_result.details.lower()

    def test_non_verifiable_tool_skipped(self, verifier):
        req = VerificationRequest(
            tool_name="bounty.create",
            inputs={"amount": 10},
            outputs={"status": "ok"},
        )
        result = verifier.verify(req)
        assert result.verified
        assert result.method == "skipped"

    def test_replay_verify_runs_without_crash(self, verifier):
        """Replay verification runs without crashing, returns a result."""
        req = VerificationRequest(
            tool_name="memory_search",
            inputs={"query": "test"},
            outputs={"status": "success"},
        )
        result = verifier._replay_verify(req)
        assert hasattr(result, 'verified')
        assert hasattr(result, 'method')
        assert result.method == "replay"
        # Replay may or may not match depending on whether the tool actually runs
        # The key is it doesn't crash and returns a result with confidence

    def test_hash_dict_is_deterministic(self, verifier):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert verifier._hash_dict(d1) == verifier._hash_dict(d2)

    def test_hash_dict_filters_internal_keys(self, verifier):
        d1 = {"_internal": "x", "data": "y"}
        d2 = {"data": "y"}
        assert verifier._hash_dict(d1) == verifier._hash_dict(d2)

    def test_checksum_cache_updates(self, verifier):
        inputs = {"q": "test"}
        outputs = {"status": "ok"}
        req = VerificationRequest(
            tool_name="gnosis",
            inputs=inputs,
            outputs=outputs,
        )
        assert len(verifier._checksum_cache) == 0
        verifier._update_checksum_cache(req)
        assert len(verifier._checksum_cache) == 1

    def test_get_status(self, verifier):
        status = verifier.get_status()
        assert "verifiable_tools" in status
        assert "memory_search" in status["verifiable_tools"]
        assert "checksum_cache_size" in status

    def test_verifiable_tools_are_read_only(self):
        """Verifiable tools should all be pure/read tools."""
        for tool in VERIFIABLE_TOOLS:
            # None of these should be write/destructive tools
            assert "create" not in tool or tool == "galaxy.list"
            assert "delete" not in tool
            assert "destroy" not in tool
            assert "write" not in tool
