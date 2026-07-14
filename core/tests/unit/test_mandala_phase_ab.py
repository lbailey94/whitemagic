"""Tests for MandalaOS Phase A effect registry and Phase B mandala compartments."""

import os
import tempfile

# Set WM_STATE_ROOT to temp dir to avoid loading production DB
_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ.setdefault("WM_STATE_ROOT", _tmp)
os.environ.setdefault("WM_SILENT_INIT", "1")


class TestEffectRegistry:
    """Test the effect registry auto-inference."""

    def test_infer_effects_pure(self):
        from whitemagic.dharma.effect_registry import infer_effects

        effects = infer_effects("gnosis")
        assert len(effects) >= 1
        assert effects[0].effect_type.value == "pure"

    def test_infer_effects_destructive(self):
        from whitemagic.dharma.effect_registry import infer_effects

        effects = infer_effects("delete_memory")
        assert effects[0].effect_type.value == "destructive"

    def test_infer_effects_network(self):
        from whitemagic.dharma.effect_registry import infer_effects

        effects = infer_effects("browser.navigate")
        assert effects[0].effect_type.value == "network"

    def test_infer_effects_local_write(self):
        from whitemagic.dharma.effect_registry import infer_effects

        effects = infer_effects("create_memory")
        assert effects[0].effect_type.value == "local"

    def test_infer_effects_observation(self):
        from whitemagic.dharma.effect_registry import infer_effects

        effects = infer_effects("telemetry")
        assert effects[0].effect_type.value == "observation"

    def test_get_declared_safety(self):
        from whitemagic.dharma.effect_registry import get_declared_safety

        assert get_declared_safety("delete_memory") == "DELETE"
        assert get_declared_safety("gnosis") == "READ"
        assert get_declared_safety("create_memory") == "WRITE"

    def test_build_effect_registry(self):
        from whitemagic.dharma.effect_registry import build_effect_registry

        registry = build_effect_registry()
        assert len(registry) > 100  # Should have most tools
        assert "create_memory" in registry
        assert "delete_memory" in registry

    def test_get_declared_effects_unregistered(self):
        from whitemagic.dharma.effect_registry import get_declared_effects

        effects = get_declared_effects("some_unknown_tool_xyz")
        assert len(effects) >= 1
        # Should default to local write (conservative)
        assert effects[0].effect_type.value == "local"


class TestKarmicMCPTools:
    """Test the karmic.effects, karmic.debt, karmic.verify MCP tools."""

    def test_karmic_effects_single_tool(self):
        from whitemagic.tools.handlers.dharma import handle_karmic_effects

        result = handle_karmic_effects(tool="create_memory")
        assert result["status"] == "success"
        assert result["tool"] == "create_memory"
        assert len(result["declared_effects"]) >= 1

    def test_karmic_effects_all_tools(self):
        from whitemagic.tools.handlers.dharma import handle_karmic_effects

        result = handle_karmic_effects()
        assert result["status"] == "success"
        assert result["total_tools"] > 100

    def test_karmic_debt_summary(self):
        from whitemagic.tools.handlers.dharma import handle_karmic_debt

        result = handle_karmic_debt()
        assert result["status"] == "success"
        assert "total_debt" in result
        assert "per_tool" in result

    def test_karmic_debt_per_tool(self):
        from whitemagic.tools.handlers.dharma import handle_karmic_debt

        result = handle_karmic_debt(tool="create_memory")
        assert result["status"] == "success"
        assert result["tool"] == "create_memory"
        assert "debt" in result

    def test_karmic_verify(self):
        from whitemagic.tools.handlers.dharma import handle_karmic_verify

        result = handle_karmic_verify()
        assert result["status"] == "success"
        assert "chain_valid" in result
        assert "integrity_ok" in result


class TestShelterTemplates:
    """Test MandalaOS Phase B shelter templates."""

    def test_shelter_templates_exist(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        assert "research" in SHELTER_TEMPLATES
        assert "sandbox" in SHELTER_TEMPLATES
        assert "production" in SHELTER_TEMPLATES
        assert "secure" in SHELTER_TEMPLATES

    def test_research_template_config(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        tmpl = SHELTER_TEMPLATES["research"]
        assert "network_read" in tmpl["capabilities"]
        assert tmpl["dharma_profile"] == "creative"

    def test_secure_template_config(self):
        from whitemagic.shelter.manager import SHELTER_TEMPLATES

        tmpl = SHELTER_TEMPLATES["secure"]
        assert tmpl["capabilities"] == []
        assert tmpl["dharma_profile"] == "secure"
        assert tmpl["limits"]["timeout_s"] == 30

    def test_create_with_template(self):
        from whitemagic.shelter.manager import ShelterManager

        mgr = ShelterManager()
        result = mgr.create(name="test_tmpl_1", template="sandbox")
        assert result["status"] == "ok"
        assert result["template"] == "sandbox"
        assert result["dharma_profile"] == "default"
        # Cleanup
        mgr.destroy(name="test_tmpl_1")

    def test_create_with_dharma_profile(self):
        from whitemagic.shelter.manager import ShelterManager

        mgr = ShelterManager()
        result = mgr.create(name="test_dharma_1", dharma_profile="secure")
        assert result["status"] == "ok"
        assert result["dharma_profile"] == "secure"
        # Cleanup
        mgr.destroy(name="test_dharma_1")


class TestMandalaMCPTools:
    """Test the mandala.* MCP tool handlers."""

    def test_mandala_templates(self):
        from whitemagic.tools.handlers.shelter import handle_mandala_templates

        result = handle_mandala_templates()
        assert result["status"] == "success"
        assert "research" in result["templates"]
        assert "sandbox" in result["templates"]
        assert "production" in result["templates"]
        assert "secure" in result["templates"]

    def test_mandala_create_with_template(self):
        from whitemagic.shelter import get_shelter_manager
        from whitemagic.tools.handlers.shelter import handle_mandala_create

        result = handle_mandala_create(name="test_mcp_1", template="sandbox")
        assert result["status"] == "ok"
        assert result["template"] == "sandbox"
        # Cleanup
        get_shelter_manager().destroy(name="test_mcp_1")

    def test_mandala_create_without_template(self):
        from whitemagic.shelter import get_shelter_manager
        from whitemagic.tools.handlers.shelter import handle_mandala_create

        result = handle_mandala_create(name="test_mcp_2", dharma_profile="creative")
        assert result["status"] == "ok"
        assert result["dharma_profile"] == "creative"
        # Cleanup
        get_shelter_manager().destroy(name="test_mcp_2")

    def test_mandala_status_includes_templates(self):
        from whitemagic.tools.handlers.shelter import handle_mandala_status

        result = handle_mandala_status()
        assert "templates" in result
        assert "research" in result["templates"]
        assert "description" in result["templates"]["research"]


class TestKarmaEntryShelterId:
    """Test that KarmaEntry supports shelter_id field."""

    def test_shelter_id_in_to_dict(self):
        from whitemagic.dharma.karma_ledger import KarmaEntry

        entry = KarmaEntry(
            tool="test_tool",
            declared_safety="READ",
            actual_writes=0,
            success=True,
            mismatch=False,
            debt_delta=0.0,
            timestamp="2026-01-01T00:00:00",
            shelter_id="mandala_research_1",
        )
        d = entry.to_dict()
        assert d["shelter_id"] == "mandala_research_1"

    def test_shelter_id_empty_not_in_dict(self):
        from whitemagic.dharma.karma_ledger import KarmaEntry

        entry = KarmaEntry(
            tool="test_tool",
            declared_safety="READ",
            actual_writes=0,
            success=True,
            mismatch=False,
            debt_delta=0.0,
            timestamp="2026-01-01T00:00:00",
        )
        d = entry.to_dict()
        assert "shelter_id" not in d

    def test_record_with_effects_shelter_id(self):
        from whitemagic.dharma.karma_ledger import (
            EffectSignature,
            EffectType,
            KarmaLedger,
        )

        ledger = KarmaLedger()
        entry = ledger.record_with_effects(
            tool="test_tool",
            declared_safety="READ",
            actual_writes=0,
            success=True,
            declared_effects=[EffectSignature(EffectType.PURE, declared=True)],
            actual_effects=[EffectSignature(EffectType.PURE, declared=False)],
            shelter_id="mandala_secure_1",
        )
        assert entry.shelter_id == "mandala_secure_1"
