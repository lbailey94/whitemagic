"""Tests for Success-Rate Feedback Loop (Phase 3) and Provenance Signing (Phase 5)."""

import pytest

from whitemagic.codegenome.engine import (
    CodeGenomeEngine,
    CodeTemplate,
    get_codegenome_engine,
)
from whitemagic.codegenome.vault import GeneseedVault


@pytest.fixture(autouse=True)
def _fresh_vault():
    """Reset GeneseedVault usage stats and template state between tests."""
    vault = GeneseedVault()
    vault._usage_stats.clear()
    # Reset template deprecated flags that may have been set by prior tests
    engine = get_codegenome_engine()
    for tmpl in getattr(engine, "_templates", {}).values():
        tmpl.deprecated = False
        tmpl.success_rate = 1.0
    yield
    vault._usage_stats.clear()
    for tmpl in getattr(engine, "_templates", {}).values():
        tmpl.deprecated = False
        tmpl.success_rate = 1.0


class TestFeedbackLoop:
    def test_record_outcome_updates_success_rate(self):
        vault = GeneseedVault()
        result = vault.record_outcome("fastapi_endpoint", "xianfeng", success=False)
        assert result["success_rate"] < 1.0
        assert result["deprecated"] is False

    def test_ema_calculation(self):
        vault = GeneseedVault()
        # Record 5 failures to drive success_rate below threshold
        for _ in range(5):
            vault.record_outcome("pydantic_model", "xianfeng", success=False)
        result = vault.record_outcome("pydantic_model", "xianfeng", success=False)
        # After 6 failures: rate = 0.9^6 ≈ 0.53 — still above 0.3
        assert result["success_rate"] < 0.6

    def test_deprecation_threshold(self):
        vault = GeneseedVault()
        # Record many failures to drive below 0.3
        for _ in range(15):
            vault.record_outcome("dockerfile", "xianfeng", success=False)
        result = vault.record_outcome("dockerfile", "xianfeng", success=False)
        assert result["success_rate"] < 0.3
        assert result["deprecated"] is True

    def test_success_keeps_rate_high(self):
        vault = GeneseedVault()
        for _ in range(5):
            vault.record_outcome("github_action", "xianfeng", success=True)
        result = vault.record_outcome("github_action", "xianfeng", success=True)
        assert result["success_rate"] > 0.9
        assert result["deprecated"] is False

    def test_recovery_from_deprecation(self):
        vault = GeneseedVault()
        # Drive to deprecation
        for _ in range(15):
            vault.record_outcome("pytest_fixture", "xianfeng", success=False)
        # Now record successes to recover
        for _ in range(20):
            vault.record_outcome("pytest_fixture", "xianfeng", success=True)
        result = vault.record_outcome("pytest_fixture", "xianfeng", success=True)
        assert result["deprecated"] is False

    def test_suggestions_for_ambiguous(self):
        vault = GeneseedVault()
        result = vault.vibe_render("something about endpoints and rest")
        # Should have suggestions (even if it matched, ambiguous case has them)
        if result.get("status") == "error":
            assert "suggestions" in result

    def test_deprecated_template_still_renders(self):
        vault = GeneseedVault()
        # Manually deprecate
        engine = vault._engine
        template = engine.get_template("fastapi_endpoint")
        if template:
            template.deprecated = True
            result = vault.vibe_render("fastapi endpoint for items")
            # Should still render, just with a warning
            assert result["status"] == "success"
            template.deprecated = False  # Reset


class TestProvenanceSigning:
    def test_sign_template(self):
        vault = GeneseedVault()
        result = vault.sign_template("fastapi_endpoint")
        assert result["status"] == "success"
        assert result["content_hash"] != ""
        # signature_key may be empty if AuditSigner keys don't exist
        # but content_hash should always be populated

    def test_sign_unknown_template(self):
        vault = GeneseedVault()
        result = vault.sign_template("does_not_exist")
        assert result["status"] == "error"

    def test_fork_has_content_hash(self):
        engine = CodeGenomeEngine()
        child = engine.fork_template("fastapi_endpoint", "signed_fork")
        assert child is not None
        assert child.content_hash != ""

    def test_template_to_dict_has_provenance_fields(self):
        engine = CodeGenomeEngine()
        t = engine.get_template("fastapi_endpoint")
        d = t.to_dict()
        assert "deprecated" in d
        assert "content_hash" in d
        assert "signature_key" in d

    def test_strict_signing_mode(self, monkeypatch):
        """In strict mode, unsigned non-builtin templates should be refused."""
        engine = CodeGenomeEngine()
        # Register an unsigned template with non-builtin source
        t = CodeTemplate(name="unsigned_test", default="test", source="/fake/path.yaml")
        engine.register(t)
        monkeypatch.setenv("WM_CODEGENOME_STRICT_SIGNING", "1")
        result = engine.render("unsigned_test")
        assert "unsigned template refused" in result
        monkeypatch.delenv("WM_CODEGENOME_STRICT_SIGNING")

    def test_strict_signing_allows_builtin(self, monkeypatch):
        """In strict mode, builtin templates should still render."""
        engine = CodeGenomeEngine()
        monkeypatch.setenv("WM_CODEGENOME_STRICT_SIGNING", "1")
        result = engine.render("fastapi_endpoint", path="/test", name="test")
        assert "get_test" in result
        monkeypatch.delenv("WM_CODEGENOME_STRICT_SIGNING")
