"""Tests for Violet ↔ MandalaOS integration gap fixes.

Covers:
  Gap 1: Violet shelter template in SHELTER_TEMPLATES
  Gap 2: mw_engagement_token middleware blocks red-ops without token
  Gap 2b: EngagementToken nonce, roe_hash, replay detection
  Gap 3: PoC pipeline governance strict under violet profile
  Gap 4: ops_class auto-classification in mw_karma_effects
  Gap 5: mw_model_signing blocks unsigned models under violet profile
"""

import os
import tempfile

# Set WM_STATE_ROOT to temp dir to avoid loading production DB
_tmp = tempfile.mkdtemp(prefix="wm_test_violet_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


# ─── Gap 1: Violet Shelter Template ─────────────────────────────────────


class TestVioletShelterTemplate:
    """Test that the violet shelter template exists with correct config."""

    def test_violet_template_exists(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        assert "violet" in SHELTER_TEMPLATES

    def test_violet_template_has_dharma_profile(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        tmpl = SHELTER_TEMPLATES["violet"]
        assert tmpl["dharma_profile"] == "violet"

    def test_violet_template_has_network_capabilities(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        caps = SHELTER_TEMPLATES["violet"]["capabilities"]
        assert "network_read" in caps
        assert "network_write" in caps

    def test_violet_template_has_description(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        desc = SHELTER_TEMPLATES["violet"]["description"]
        assert "purple-team" in desc.lower() or "violet" in desc.lower()

    def test_violet_template_limits_are_reasonable(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        limits = SHELTER_TEMPLATES["violet"]["limits"]
        assert limits["timeout_s"] > 0
        assert limits["max_memory_mb"] > 0

    def test_mandala_templates_lists_violet(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        all_templates = list(SHELTER_TEMPLATES.keys())
        assert "violet" in all_templates
        # Ensure we didn't lose existing templates
        assert "research" in all_templates
        assert "sandbox" in all_templates
        assert "secure" in all_templates


# ─── Gap 2b: Enhanced EngagementToken ───────────────────────────────────


class TestEngagementTokenEnhancements:
    """Test nonce, roe_hash, and helper functions on EngagementToken."""

    def test_issue_token_has_nonce(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager(storage_dir=None)
        result = mgr.issue(
            scope=["10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=5,
        )
        token = result["token"]
        assert "nonce" in token
        assert len(token["nonce"]) > 0

    def test_issue_token_with_roe_hash(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager(storage_dir=None)
        result = mgr.issue(
            scope=["10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=5,
            roe_hash="abc123",
        )
        token = result["token"]
        assert token["roe_hash"] == "abc123"

    def test_token_hash_includes_nonce(self):
        """Verify that tokens with different nonces have different hashes."""
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager(storage_dir=None)
        r1 = mgr.issue(scope=["*"], tools=["*"], issuer="t", duration_minutes=5)
        r2 = mgr.issue(scope=["*"], tools=["*"], issuer="t", duration_minutes=5)
        assert r1["token"]["token_hash"] != r2["token"]["token_hash"]

    def test_validate_with_nonce_succeeds(self):
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager(storage_dir=None)
        result = mgr.issue(
            scope=["10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=5,
        )
        token_id = result["token"]["token_id"]
        v = mgr.validate(token_id=token_id, tool="nmap_scan", target="10.0.0.1")
        assert v["valid"] is True

    def test_short_lived_token(self):
        """Test 30-second TTL token (ROE Gate pattern)."""
        from whitemagic.security.engagement_tokens import EngagementTokenManager

        mgr = EngagementTokenManager(storage_dir=None)
        result = mgr.issue(
            scope=["*"],
            tools=["*"],
            issuer="test",
            duration_minutes=0.5,  # 30 seconds
            max_uses=1,  # single-use
        )
        token_id = result["token"]["token_id"]
        v = mgr.validate(token_id=token_id, tool="red_exploit", target="10.0.0.1")
        assert v["valid"] is True
        # Single-use: second validation should fail
        v2 = mgr.validate(token_id=token_id, tool="red_exploit", target="10.0.0.1")
        assert v2["valid"] is False

    def test_is_red_ops_tool(self):
        from whitemagic.security.engagement_tokens import is_red_ops_tool

        assert is_red_ops_tool("red_exploit") is True
        assert is_red_ops_tool("pentest_scan") is True
        assert is_red_ops_tool("fuzz_web") is True
        assert is_red_ops_tool("nmap_port_scan") is True
        assert is_red_ops_tool("memory.store") is False
        assert is_red_ops_tool("gnosis") is False

    def test_is_blue_ops_tool(self):
        from whitemagic.security.engagement_tokens import is_blue_ops_tool

        assert is_blue_ops_tool("blue_defend") is True
        assert is_blue_ops_tool("scan_network") is True
        assert is_blue_ops_tool("detect_anomaly") is True
        assert is_blue_ops_tool("red_exploit") is False

    def test_classify_ops(self):
        from whitemagic.security.engagement_tokens import classify_ops

        assert classify_ops("red_exploit") == "red-ops"
        assert classify_ops("blue_defend") == "blue-ops"
        assert classify_ops("memory.store") == ""

    def test_requires_engagement_token(self):
        from whitemagic.security.engagement_tokens import requires_engagement_token

        assert requires_engagement_token("red_exploit") is True
        assert requires_engagement_token("nmap_scan") is True
        assert requires_engagement_token("blue_defend") is False
        assert requires_engagement_token("memory.store") is False


# ─── Gap 2: Engagement Token Middleware ─────────────────────────────────


class TestEngagementTokenMiddleware:
    """Test mw_engagement_token middleware behavior."""

    def test_middleware_passes_non_violet_profile(self):
        """Under non-violet profile, middleware should pass through."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")
            ctx = DispatchContext(tool_name="red_exploit", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == [True]
            assert result["status"] == "success"
        finally:
            engine.set_profile(original_profile)

    def test_middleware_passes_non_red_ops_tool(self):
        """Non-red-ops tools should pass even under violet profile."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="memory.store", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            mw_engagement_token(ctx, next_fn)
            assert called == [True]
        finally:
            engine.set_profile(original_profile)

    def test_middleware_blocks_red_ops_without_token(self):
        """Red-ops tools under violet profile without token should be blocked."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(tool_name="red_exploit", kwargs={})
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []  # next_fn should NOT be called
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_required"
        finally:
            engine.set_profile(original_profile)

    def test_middleware_passes_with_valid_token(self):
        """Red-ops tools with valid token should pass."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            token_result = mgr.issue(
                scope=["10.0.0.*"],
                tools=["red_*"],
                issuer="test",
                duration_minutes=5,
            )
            token_id = token_result["token"]["token_id"]

            ctx = DispatchContext(
                tool_name="red_exploit",
                kwargs={"_engagement_token_id": token_id, "target": "10.0.0.1"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == [True]
            assert result["status"] == "success"
            assert ctx.meta.get("ops_class") == "red-ops"
        finally:
            engine.set_profile(original_profile)

    def test_middleware_blocks_with_invalid_token(self):
        """Red-ops tools with invalid token should be blocked."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(
                tool_name="red_exploit",
                kwargs={"_engagement_token_id": "evt_nonexistent"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_engagement_token(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
            assert result["error_code"] == "engagement_token_invalid"
        finally:
            engine.set_profile(original_profile)


# ─── Gap 3: PoC Pipeline Governance ─────────────────────────────────────


class TestPoCPipelineGovernance:
    """Test that PoC pipeline governance is strict under violet profile."""

    def test_governance_strict_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.security.poc_pipeline import _check_governance

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            # Without WM_POC_AUTO_APPROVE, should be False under violet
            old = os.environ.pop("WM_POC_AUTO_APPROVE", None)
            old_approved = os.environ.pop("WM_POC_APPROVED", None)
            try:
                result = _check_governance("example.com", "bounty")
                assert result is False
            finally:
                if old:
                    os.environ["WM_POC_AUTO_APPROVE"] = old
                if old_approved:
                    os.environ["WM_POC_APPROVED"] = old_approved
        finally:
            engine.set_profile(original_profile)

    def test_governance_permissive_under_default(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.security.poc_pipeline import _check_governance

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")
            old = os.environ.pop("WM_POC_AUTO_APPROVE", None)
            old_approved = os.environ.pop("WM_POC_APPROVED", None)
            try:
                result = _check_governance("example.com", "bounty")
                assert result is True
            finally:
                if old:
                    os.environ["WM_POC_AUTO_APPROVE"] = old
                if old_approved:
                    os.environ["WM_POC_APPROVED"] = old_approved
        finally:
            engine.set_profile(original_profile)

    def test_governance_passes_with_auto_approve(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.security.poc_pipeline import _check_governance

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            old = os.environ.get("WM_POC_AUTO_APPROVE", "")
            os.environ["WM_POC_AUTO_APPROVE"] = "1"
            try:
                result = _check_governance("example.com", "bounty")
                assert result is True
            finally:
                if old:
                    os.environ["WM_POC_AUTO_APPROVE"] = old
                else:
                    os.environ.pop("WM_POC_AUTO_APPROVE", None)
        finally:
            engine.set_profile(original_profile)

    def test_governance_passes_with_approved_target(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.security.poc_pipeline import _check_governance

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            old = os.environ.get("WM_POC_APPROVED", "")
            os.environ["WM_POC_APPROVED"] = "approved-target.com"
            try:
                result = _check_governance("approved-target.com", "bounty")
                assert result is True
            finally:
                if old:
                    os.environ["WM_POC_APPROVED"] = old
                else:
                    os.environ.pop("WM_POC_APPROVED", None)
        finally:
            engine.set_profile(original_profile)


# ─── Gap 4: ops_class Auto-Classification ───────────────────────────────


class TestOpsClassClassification:
    """Test that ops_class is auto-classified and passed to karma ledger."""

    def test_classify_red_ops(self):
        from whitemagic.security.engagement_tokens import classify_ops

        assert classify_ops("red_exploit") == "red-ops"
        assert classify_ops("pentest_web") == "red-ops"
        assert classify_ops("fuzz_api") == "red-ops"

    def test_classify_blue_ops(self):
        from whitemagic.security.engagement_tokens import classify_ops

        assert classify_ops("blue_defend") == "blue-ops"
        assert classify_ops("scan_network") == "blue-ops"
        assert classify_ops("detect_anomaly") == "blue-ops"

    def test_classify_normal(self):
        from whitemagic.security.engagement_tokens import classify_ops

        assert classify_ops("memory.store") == ""
        assert classify_ops("gnosis") == ""
        assert classify_ops("galaxy.overview") == ""

    def test_middleware_sets_ops_class_in_meta(self):
        """When engagement_token middleware validates, it sets ops_class in meta."""
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.engagement_tokens import get_token_manager
        from whitemagic.tools.middleware import DispatchContext, mw_engagement_token

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            mgr = get_token_manager()
            token_result = mgr.issue(
                scope=["10.0.0.*"],
                tools=["red_*"],
                issuer="test",
                duration_minutes=5,
            )
            token_id = token_result["token"]["token_id"]

            ctx = DispatchContext(
                tool_name="red_exploit",
                kwargs={"_engagement_token_id": token_id, "target": "10.0.0.1"},
            )

            def next_fn(c):
                return {"status": "success"}

            mw_engagement_token(ctx, next_fn)
            assert ctx.meta.get("ops_class") == "red-ops"
        finally:
            engine.set_profile(original_profile)


# ─── Gap 5: Model Signing Enforcement ───────────────────────────────────


class TestModelSigningEnforcement:
    """Test mw_model_signing middleware blocks unsigned models under violet."""

    def test_model_signing_passes_non_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_model_signing

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")
            ctx = DispatchContext(
                tool_name="llama_generate",
                kwargs={"model": "qwen3-4b"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            mw_model_signing(ctx, next_fn)
            assert called == [True]
        finally:
            engine.set_profile(original_profile)

    def test_model_signing_passes_non_model_tool(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_model_signing

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(
                tool_name="memory.store",
                kwargs={"model": "qwen3-4b"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            mw_model_signing(ctx, next_fn)
            assert called == [True]
        finally:
            engine.set_profile(original_profile)

    def test_model_signing_blocks_unsigned_under_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.tools.middleware import DispatchContext, mw_model_signing

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            ctx = DispatchContext(
                tool_name="llama_generate",
                kwargs={"model": "unsigned-model-test"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_model_signing(ctx, next_fn)
            assert called == []  # blocked
            assert result["status"] == "error"
            assert result["error_code"] == "model_signing_violation"
        finally:
            engine.set_profile(original_profile)

    def test_model_signing_passes_verified_model(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.model_signing import get_model_registry
        from whitemagic.tools.middleware import DispatchContext, mw_model_signing

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            # Register a model as verified
            registry = get_model_registry()
            registry.register_model(
                model_name="verified-test-model",
                sha256="abc123",
                trust="verified",
            )

            ctx = DispatchContext(
                tool_name="llama_generate",
                kwargs={"model": "verified-test-model"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            mw_model_signing(ctx, next_fn)
            assert called == [True]
        finally:
            engine.set_profile(original_profile)

    def test_model_signing_blocks_blocked_model(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.security.model_signing import get_model_registry
        from whitemagic.tools.middleware import DispatchContext, mw_model_signing

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("violet")
            registry = get_model_registry()
            registry.register_model(
                model_name="blocked-test-model",
                sha256="bad123",
                trust="blocked",
            )

            ctx = DispatchContext(
                tool_name="llama_generate",
                kwargs={"model": "blocked-test-model"},
            )
            called = []

            def next_fn(c):
                called.append(True)
                return {"status": "success"}

            result = mw_model_signing(ctx, next_fn)
            assert called == []
            assert result["status"] == "error"
        finally:
            engine.set_profile(original_profile)


# ─── Pipeline Integration ────────────────────────────────────────────────


class TestPipelineIntegration:
    """Test that the new middlewares are wired into the dispatch pipeline."""

    def test_pipeline_includes_engagement_token(self):
        from whitemagic.tools.dispatch_table import _pipeline

        names = _pipeline.describe()
        assert "engagement_token" in names

    def test_pipeline_includes_model_signing(self):
        from whitemagic.tools.dispatch_table import _pipeline

        names = _pipeline.describe()
        assert "model_signing" in names

    def test_pipeline_order_engagement_before_governor(self):
        from whitemagic.tools.dispatch_table import _pipeline

        names = _pipeline.describe()
        eng_idx = names.index("engagement_token")
        gov_idx = names.index("governor")
        assert eng_idx < gov_idx, "engagement_token should run before governor"

    def test_pipeline_order_model_signing_before_cognitive(self):
        from whitemagic.tools.dispatch_table import _pipeline

        names = _pipeline.describe()
        ms_idx = names.index("model_signing")
        cog_idx = names.index("cognitive_mode")
        assert ms_idx < cog_idx, "model_signing should run before cognitive_mode"


# ─── MCP Tool Definitions ───────────────────────────────────────────────


class TestVioletSecurityToolDefs:
    """Test that violet security tool definitions are registered."""

    def test_engagement_issue_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "engagement.issue" in names

    def test_engagement_validate_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "engagement.validate" in names

    def test_engagement_revoke_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "engagement.revoke" in names

    def test_engagement_list_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "engagement.list" in names

    def test_engagement_status_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "engagement.status" in names

    def test_model_register_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "model.register" in names

    def test_model_verify_tool_def_exists(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        names = [t.name for t in tools]
        assert "model.verify" in names

    def test_engagement_issue_has_roe_hash_in_schema(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        issue_tool = next(t for t in tools if t.name == "engagement.issue")
        props = issue_tool.input_schema.get("properties", {})
        assert "roe_hash" in props

    def test_engagement_issue_duration_is_number(self):
        from whitemagic.tools.tool_catalog import collect_authored_tool_definitions

        tools = collect_authored_tool_definitions()
        issue_tool = next(t for t in tools if t.name == "engagement.issue")
        props = issue_tool.input_schema.get("properties", {})
        assert props["duration_minutes"]["type"] == "number"


# ─── Handler roe_hash Passthrough ────────────────────────────────────────


class TestEngagementHandlerRoeHash:
    """Test that handle_engagement_issue passes roe_hash through."""

    def test_handler_passes_roe_hash(self):
        from whitemagic.tools.handlers.violet_security import handle_engagement_issue

        result = handle_engagement_issue(
            scope=["10.0.0.*"],
            tools=["nmap_*"],
            issuer="test",
            duration_minutes=5,
            roe_hash="test_roe_hash_123",
        )
        assert result["status"] == "success"
        assert result["token"]["roe_hash"] == "test_roe_hash_123"

    def test_handler_passes_float_duration(self):
        from whitemagic.tools.handlers.violet_security import handle_engagement_issue

        result = handle_engagement_issue(
            scope=["*"],
            tools=["*"],
            issuer="test",
            duration_minutes=0.5,
        )
        assert result["status"] == "success"
        # 0.5 minutes = 30 seconds
        remaining = result["token"]["remaining_s"]
        assert remaining <= 30.0

    def test_handler_validates_via_mcp(self):
        from whitemagic.tools.handlers.violet_security import (
            handle_engagement_issue,
            handle_engagement_validate,
        )

        issue_result = handle_engagement_issue(
            scope=["10.0.0.*"],
            tools=["red_*"],
            issuer="test",
            duration_minutes=5,
        )
        token_id = issue_result["token"]["token_id"]

        validate_result = handle_engagement_validate(
            token_id=token_id,
            tool="red_exploit",
            target="10.0.0.1",
        )
        assert validate_result["valid"] is True

    def test_handler_revoke_via_mcp(self):
        from whitemagic.tools.handlers.violet_security import (
            handle_engagement_issue,
            handle_engagement_revoke,
        )

        issue_result = handle_engagement_issue(
            scope=["*"],
            tools=["*"],
            issuer="test",
            duration_minutes=5,
        )
        token_id = issue_result["token"]["token_id"]

        revoke_result = handle_engagement_revoke(token_id=token_id)
        assert revoke_result["status"] == "success"


# ─── Violet Profile Auto-Activation ──────────────────────────────────────


class TestVioletProfileAutoActivation:
    """Test that creating a violet shelter auto-activates violet Dharma profile."""

    def test_violet_shelter_activates_violet_profile(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.shelter.manager import ShelterManager

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")
            assert engine.get_profile() == "default"

            mgr = ShelterManager()
            result = mgr.create(
                name="test_violet_auto",
                template="violet",
            )
            assert result["status"] == "ok"
            assert engine.get_profile() == "violet"
        finally:
            engine.set_profile(original_profile)

    def test_non_violet_shelter_does_not_activate_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.shelter.manager import ShelterManager

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")
            assert engine.get_profile() == "default"

            mgr = ShelterManager()
            result = mgr.create(
                name="test_research_no_violet",
                template="research",
            )
            assert result["status"] == "ok"
            assert engine.get_profile() == "default"
        finally:
            engine.set_profile(original_profile)

    def test_violet_dharma_profile_param_activates_violet(self):
        from whitemagic.dharma.rules import get_rules_engine
        from whitemagic.shelter.manager import ShelterManager

        engine = get_rules_engine()
        original_profile = engine.get_profile()
        try:
            engine.set_profile("default")

            mgr = ShelterManager()
            result = mgr.create(
                name="test_violet_explicit",
                dharma_profile="violet",
            )
            assert result["status"] == "ok"
            assert engine.get_profile() == "violet"
        finally:
            engine.set_profile(original_profile)
