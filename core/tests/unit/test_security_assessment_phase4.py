"""Tests for Security Capabilities Assessment Phase 4: Shelter Integration.

Covers:
  - create_for_offensive() factory method
  - Shelter capabilities derived from engagement token scope
  - shelter_id parameter on offensive handlers
  - Fallback when shelter_id is not found
"""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase4_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── create_for_offensive Factory ────────────────────────────────────────


class TestCreateForOffensive:
    """Test the create_for_offensive factory method."""

    def test_creates_shelter_from_valid_token(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(
            scope=["10.0.0.*", "*.example.com"],
            tools=["http_probe_*", "foundry_*"],
            issuer="test",
            duration_minutes=10,
        )
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id, name="test_offensive_1")
        assert result["status"] == "ok"
        assert result["dharma_profile"] == "violet"
        assert result["template"] == "violet"
        assert result["engagement_token_id"] == token_id

        # Network allow should match token scope
        caps = result["capabilities"]
        assert "10.0.0.*" in caps["network_allow"]
        assert "*.example.com" in caps["network_allow"]
        assert caps["network"] == "filtered"

        # Tools allow should include token tool patterns
        assert "http_probe_*" in caps["tools_allow"]
        assert "foundry_*" in caps["tools_allow"]

        # Cleanup
        shelter_mgr = get_shelter_manager()
        shelter_mgr.destroy("test_offensive_1")

    def test_auto_generates_shelter_name(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id)
        assert result["status"] == "ok"
        assert result["name"].startswith("offensive_")

        # Cleanup
        shelter_mgr = get_shelter_manager()
        shelter_mgr.destroy(result["name"])

    def test_rejects_nonexistent_token(self):
        from whitemagic.shelter.manager import create_for_offensive

        result = create_for_offensive("evt_nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["reason"]

    def test_rejects_revoked_token(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive

        mgr = get_token_manager()
        tok = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
        token_id = tok["token"]["token_id"]
        mgr.revoke(token_id)

        result = create_for_offensive(token_id)
        assert result["status"] == "error"
        assert "no longer valid" in result["reason"]

    def test_shelter_has_violet_dharma_profile(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            mgr = get_token_manager()
            tok = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]

            result = create_for_offensive(token_id, name="test_violet_profile")
            assert result["status"] == "ok"
            assert result["dharma_profile"] == "violet"
            # Creating a violet shelter should auto-activate violet profile
            assert engine.get_profile() == "violet"

            get_shelter_manager().destroy("test_violet_profile")
        finally:
            engine.set_profile(original)

    def test_shelter_capabilities_include_filesystem(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id, name="test_caps_fs")
        assert result["status"] == "ok"
        caps = result["capabilities"]
        assert "/tmp" in caps["filesystem_read"]
        assert "/tmp" in caps["filesystem_write"]

        get_shelter_manager().destroy("test_caps_fs")


# ─── Handler shelter_id Support ──────────────────────────────────────────


class TestHandlerShelterId:
    """Test that offensive handlers accept and use shelter_id parameter."""

    def test_foundry_build_with_nonexistent_shelter_falls_through(self):
        """If shelter_id doesn't exist, handler should proceed normally."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_foundry_build(
                project_dir="/tmp",
                shelter_id="nonexistent_shelter",
            )
            # Should proceed normally (forge not installed, but not a token error)
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_http_probe_get_with_nonexistent_shelter_falls_through(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_http_probe_get

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_http_probe_get(
                url="http://example.com",
                shelter_id="nonexistent_shelter",
            )
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_echidna_fuzz_with_nonexistent_shelter_falls_through(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_echidna_fuzz

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_echidna_fuzz(
                contract_file="test.sol",
                contract_name="Test",
                shelter_id="nonexistent_shelter",
            )
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_poc_verify_with_nonexistent_shelter_falls_through(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_poc_verify

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_poc_verify(
                template_name="poc_reentrancy",
                shelter_id="nonexistent_shelter",
            )
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_offensive_handler_without_shelter_id_works_normally(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_foundry_build(project_dir="/tmp")
            # No shelter_id, should work normally
            assert "success" in result or "status" in result
        finally:
            engine.set_profile(original)


# ─── Shelter Network Filtering from Token Scope ──────────────────────────


class TestShelterNetworkFiltering:
    """Test that shelter network_allow is derived from token scope."""

    def test_network_allow_matches_token_scope(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(
            scope=["192.168.1.*", "10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=5,
        )
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id, name="test_net_filter")
        assert result["status"] == "ok"
        caps = result["capabilities"]
        assert "192.168.1.*" in caps["network_allow"]
        assert "10.0.0.*" in caps["network_allow"]
        assert caps["network"] == "filtered"

        get_shelter_manager().destroy("test_net_filter")

    def test_wildcard_scope_transfers_to_shelter(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(scope=["*"], tools=["*"], issuer="test", duration_minutes=5)
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id, name="test_wildcard_scope")
        assert result["status"] == "ok"
        caps = result["capabilities"]
        assert "*" in caps["network_allow"]

        get_shelter_manager().destroy("test_wildcard_scope")

    def test_tools_allow_matches_token_tools(self):
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager

        mgr = get_token_manager()
        tok = mgr.issue(
            scope=["*"],
            tools=["foundry_*", "echidna_*"],
            issuer="test",
            duration_minutes=5,
        )
        token_id = tok["token"]["token_id"]

        result = create_for_offensive(token_id, name="test_tools_allow")
        assert result["status"] == "ok"
        caps = result["capabilities"]
        assert "foundry_*" in caps["tools_allow"]
        assert "echidna_*" in caps["tools_allow"]

        get_shelter_manager().destroy("test_tools_allow")


# ─── Integration: Token + Shelter + Handler ──────────────────────────────


class TestTokenShelterHandlerIntegration:
    """Integration test: issue token → create shelter → call handler with shelter_id."""

    def test_full_flow_violet_profile(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            # 1. Issue token
            mgr = get_token_manager()
            tok = mgr.issue(
                scope=["*"],
                tools=["foundry_*"],
                issuer="test",
                duration_minutes=10,
            )
            token_id = tok["token"]["token_id"]

            # 2. Create offensive shelter
            shelter_result = create_for_offensive(token_id, name="test_integration")
            assert shelter_result["status"] == "ok"
            shelter_id = shelter_result["name"]

            # 3. Call handler with token + shelter_id
            result = handle_foundry_build(
                project_dir="/tmp",
                _engagement_token_id=token_id,
                shelter_id=shelter_id,
            )
            # Should not be a token error (token is valid)
            assert result.get("error_code") != "engagement_token_required"
            assert result.get("error_code") != "engagement_token_invalid"

            # Cleanup
            get_shelter_manager().destroy(shelter_id)
        finally:
            engine.set_profile(original)

    def test_handler_blocks_without_token_even_with_shelter(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.shelter.manager import create_for_offensive, get_shelter_manager
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            # Create shelter with token
            mgr = get_token_manager()
            tok = mgr.issue(scope=["*"], tools=["foundry_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]
            shelter_result = create_for_offensive(token_id, name="test_no_token_with_shelter")
            shelter_id = shelter_result["name"]

            # Call handler WITH shelter but WITHOUT token
            result = handle_foundry_build(
                project_dir="/tmp",
                shelter_id=shelter_id,
            )
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"

            get_shelter_manager().destroy(shelter_id)
        finally:
            engine.set_profile(original)
