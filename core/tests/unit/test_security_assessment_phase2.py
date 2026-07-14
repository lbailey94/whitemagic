"""Tests for Security Capabilities Assessment Phase 2: Engagement Token Enforcement.

Covers:
  - Expanded RED_OPS_TOOL_PATTERNS (foundry_*, http_probe_*, echidna_*, formal_verify_*)
  - Handler-level defense-in-depth token validation
  - Middleware enforcement for newly added offensive tools
  - Scope matching for HTTPProbe and FoundryBridge targets
"""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_sec_phase2_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── Expanded RED_OPS_TOOL_PATTERNS ──────────────────────────────────────


class TestExpandedRedOpsPatterns:
    """Test that foundry, http_probe, echidna, formal_verify are now red-ops."""

    def test_foundry_build_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("foundry_build") is True

    def test_foundry_test_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("foundry_test") is True

    def test_foundry_test_json_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("foundry_test_json") is True

    def test_http_probe_get_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_get") is True

    def test_http_probe_post_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_post") is True

    def test_http_probe_xss_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_xss") is True

    def test_http_probe_sqli_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_sqli") is True

    def test_http_probe_idor_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_idor") is True

    def test_http_probe_ssrf_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("http_probe_ssrf") is True

    def test_api_state_machine_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("api_state_machine") is True

    def test_echidna_fuzz_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("echidna_fuzz") is True

    def test_formal_verify_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("formal_verify") is True

    def test_poc_generate_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("poc_generate") is True

    def test_poc_verify_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("poc_verify") is True

    def test_abi_parse_is_not_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("abi_parse") is False

    def test_vuln_search_is_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        # vuln_search matches the pre-existing vuln_* pattern
        assert is_red_ops_tool("vuln_search") is True

    def test_contest_format_is_not_red_ops(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool
        assert is_red_ops_tool("contest_format") is False

    def test_requires_engagement_token_for_foundry(self):
        from whitemagic.security.engagement_tokens import requires_engagement_token
        assert requires_engagement_token("foundry_build") is True
        assert requires_engagement_token("foundry_test") is True

    def test_requires_engagement_token_for_http_probe(self):
        from whitemagic.security.engagement_tokens import requires_engagement_token
        assert requires_engagement_token("http_probe_get") is True
        assert requires_engagement_token("http_probe_xss") is True

    def test_requires_engagement_token_for_echidna(self):
        from whitemagic.security.engagement_tokens import requires_engagement_token
        assert requires_engagement_token("echidna_fuzz") is True

    def test_requires_engagement_token_for_formal_verify(self):
        from whitemagic.security.engagement_tokens import requires_engagement_token
        assert requires_engagement_token("formal_verify") is True


# ─── Handler-Level Defense-in-Depth ──────────────────────────────────────


class TestHandlerLevelTokenEnforcement:
    """Test that offensive handlers check engagement tokens."""

    def test_foundry_build_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_foundry_build(project_dir="/tmp")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_foundry_test_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_test

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_foundry_test(project_dir="/tmp")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_http_probe_get_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_http_probe_get

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_http_probe_get(url="http://example.com")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_http_probe_xss_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_http_probe_xss

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_http_probe_xss(url="http://example.com", param="q")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_echidna_fuzz_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_echidna_fuzz

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_echidna_fuzz(contract_file="test.sol", contract_name="Test")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_formal_verify_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_formal_verify

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_formal_verify(project_dir=".")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_poc_generate_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_poc_generate

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_poc_generate(template_name="poc_reentrancy")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_poc_verify_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_poc_verify

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_poc_verify(template_name="poc_reentrancy")
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_api_state_machine_blocks_under_violet_without_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_api_state_machine

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_api_state_machine(base_url="http://example.com", sequences=[])
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)


# ─── Handler Passes With Valid Token ─────────────────────────────────────


class TestHandlerPassesWithValidToken:
    """Test that offensive handlers proceed with a valid token under violet."""

    def test_foundry_build_passes_with_valid_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            tok = mgr.issue(scope=["*"], tools=["foundry_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]
            result = handle_foundry_build(project_dir="/tmp", _engagement_token_id=token_id)
            # Will fail because forge isn't installed, but should NOT be engagement_token_required
            assert result.get("error_code") != "engagement_token_required"
            assert result.get("error_code") != "engagement_token_invalid"
        finally:
            engine.set_profile(original)

    def test_http_probe_get_passes_with_valid_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.handlers.security_tools import handle_http_probe_get

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            tok = mgr.issue(scope=["http://example.com"], tools=["http_probe_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]
            # We can't actually make HTTP calls in tests, but the token check should pass
            # The handler will try to make a request and fail, but not with token error
            result = handle_http_probe_get(url="http://example.com", _engagement_token_id=token_id)
            assert result.get("error_code") != "engagement_token_required"
            assert result.get("error_code") != "engagement_token_invalid"
        finally:
            engine.set_profile(original)

    def test_handler_blocks_with_invalid_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_foundry_build(
                project_dir="/tmp",
                _engagement_token_id="evt_nonexistent",
            )
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_invalid"
        finally:
            engine.set_profile(original)

    def test_handler_blocks_with_wrong_tool_scope(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            # Token only authorizes http_probe_*, not foundry_*
            tok = mgr.issue(scope=["*"], tools=["http_probe_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]
            result = handle_foundry_build(
                project_dir="/tmp",
                _engagement_token_id=token_id,
            )
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_invalid"
            assert "not authorized" in result["message"]
        finally:
            engine.set_profile(original)

    def test_handler_blocks_with_wrong_target_scope(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.handlers.security_tools import handle_http_probe_get

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            # Token scope is 10.0.0.*, but we're targeting example.com
            tok = mgr.issue(scope=["10.0.0.*"], tools=["http_probe_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]
            result = handle_http_probe_get(
                url="http://example.com",
                _engagement_token_id=token_id,
            )
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_invalid"
            assert "outside" in result["message"]
        finally:
            engine.set_profile(original)


# ─── Non-Violet Profile Pass-Through ─────────────────────────────────────


class TestNonVioletPassThrough:
    """Test that offensive handlers proceed without token under non-violet."""

    def test_foundry_build_passes_without_token_default(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_foundry_build

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_foundry_build(project_dir="/tmp")
            # Will fail because forge isn't installed, but not with token error
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_http_probe_get_passes_without_token_default(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_http_probe_get

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_http_probe_get(url="http://example.com")
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_echidna_fuzz_passes_without_token_default(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_echidna_fuzz

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("default")
            result = handle_echidna_fuzz(contract_file="test.sol", contract_name="Test")
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)


# ─── Middleware Enforcement for New Tools ────────────────────────────────


class TestMiddlewareEnforcementNewTools:
    """Test that mw_engagement_token blocks new offensive tools under violet."""

    def test_middleware_blocks_foundry_build_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="foundry_build", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_middleware_blocks_http_probe_get_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="http_probe_get", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_middleware_blocks_echidna_fuzz_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="echidna_fuzz", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_middleware_blocks_formal_verify_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="formal_verify", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_middleware_passes_foundry_with_valid_token(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            tok = mgr.issue(scope=["*"], tools=["foundry_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]

            ctx = DispatchContext(
                tool_name="foundry_build",
                kwargs={"_engagement_token_id": token_id},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == [True]
            assert result["status"] == "success"
        finally:
            engine.set_profile(original)

    def test_middleware_passes_http_probe_with_valid_token_and_scope(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            tok = mgr.issue(scope=["http://target.com"], tools=["http_probe_*"], issuer="test", duration_minutes=5)
            token_id = tok["token"]["token_id"]

            ctx = DispatchContext(
                tool_name="http_probe_get",
                kwargs={"_engagement_token_id": token_id, "url": "http://target.com"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == [True]
        finally:
            engine.set_profile(original)


# ─── Non-Offensive Handlers Not Affected ─────────────────────────────────


class TestNonOffensiveHandlersUnaffected:
    """Test that non-offensive security handlers don't require tokens."""

    def test_abi_parse_no_token_check(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_abi_parse

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            # Should not raise engagement_token_required
            result = handle_abi_parse(abi_json="[]")
            # Will get an empty result but NOT a token error
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_vuln_search_no_token_check(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_vuln_search

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_vuln_search(query="reentrancy")
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_contest_status_no_token_check(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_contest_status

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_contest_status()
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_security_status_no_token_check(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_security_status

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_security_status()
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_slither_scan_no_token_check(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_slither_scan

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_slither_scan(project_dir=".")
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_echidna_status_no_token_check(self):
        """echidna_status is a status check, not an offensive action."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_echidna_status

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_echidna_status()
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)

    def test_formal_verify_status_no_token_check(self):
        """formal_verify_status is a status check, not an offensive action."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.handlers.security_tools import handle_formal_verify_status

        engine = get_rules_engine()
        original = engine.get_profile()
        try:
            engine.set_profile("violet")
            result = handle_formal_verify_status()
            assert result.get("error_code") != "engagement_token_required"
        finally:
            engine.set_profile(original)
