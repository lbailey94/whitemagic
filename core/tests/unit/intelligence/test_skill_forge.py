"""Unit tests for SkillForge — the Recursive Blacksmith.

Tests cover:
- Path hygiene (writes to WM_STATE_ROOT/skills, not memory/skills)
- assess_pattern heuristic
- forge (creates + persists skill)
- _save_skill (JSON format, disk write)
- _load_skills (round-trip from disk)
- _update_skills_md (catalog generation)
- Singleton get_skill_forge / reset_skill_forge
- Auto-forge integration via UniversalRouter.execute
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from whitemagic.core.intelligence.omni.skill_forge import (
    ForgedSkill,
    SkillForge,
    get_skill_forge,
    reset_skill_forge,
)
from whitemagic.core.intelligence.omni.universal_router import (
    ExecutionChain,
    GanaStep,
    UniversalRouter,
)


@pytest.fixture
def forge(tmp_path: Path) -> SkillForge:
    """Create a SkillForge with an isolated temp directory."""
    skills_dir = tmp_path / "skills"
    return SkillForge(skill_library_path=skills_dir)


@pytest.fixture
def simple_chain() -> ExecutionChain:
    """Create a simple 3-step execution chain (meets >2 threshold)."""
    return ExecutionChain(
        intent="research memory systems",
        steps=[
            GanaStep(mansion="NET", operation="search", context_key="topic", parameters={}),
            GanaStep(mansion="GHOST", operation="analyze", context_key="bias_check", parameters={}),
            GanaStep(mansion="WINNOWING_BASKET", operation="consolidate", context_key="filter", parameters={}),
        ],
        estimated_complexity=2.4,
        required_capabilities=["basic_reasoning"],
    )


@pytest.fixture
def short_chain() -> ExecutionChain:
    """Create a 2-step chain (below >2 threshold)."""
    return ExecutionChain(
        intent="quick lookup",
        steps=[
            GanaStep(mansion="NET", operation="search", context_key="topic", parameters={}),
            GanaStep(mansion="HORN", operation="search", context_key="init", parameters={}),
        ],
        estimated_complexity=1.0,
        required_capabilities=[],
    )


class TestSkillForgeInit:
    """Tests for SkillForge initialization and path hygiene."""

    def test_uses_explicit_path(self, tmp_path: Path):
        skills_dir = tmp_path / "custom_skills"
        forge = SkillForge(skill_library_path=skills_dir)
        assert forge.skill_library_path == skills_dir
        assert skills_dir.exists()

    def test_defaults_to_state_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        from whitemagic.config import paths as paths_module
        monkeypatch.setattr(paths_module, "WM_ROOT", tmp_path)

        forge = SkillForge()
        assert forge.skill_library_path == tmp_path / "skills"
        assert forge.skill_library_path.exists()

    def test_does_not_write_to_memory_dir(self, tmp_path: Path, monkeypatch):
        """Verify the old default path (memory/skills) is NOT used."""
        monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
        import importlib
        from whitemagic.config import paths as paths_module
        importlib.reload(paths_module)

        forge = SkillForge()
        # The old default was Path("memory/skills") — verify we're not using that
        assert forge.skill_library_path != Path("memory/skills")
        assert forge.skill_library_path.is_absolute()

    def test_starts_empty(self, forge: SkillForge):
        assert forge.known_skills == {}

    def test_loads_existing_skills(self, tmp_path: Path):
        """Pre-existing JSON files are loaded on init."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_data = {
            "name": "TestSkill",
            "description": "A test skill",
            "triggers": ["test trigger"],
            "steps": [
                {"mansion": "NET", "operation": "search", "context": "query"},
                {"mansion": "ROOT", "operation": "analyze", "context": "data"},
                {"mansion": "VOID", "operation": "transform", "context": "result"},
            ],
        }
        (skills_dir / "testskill.json").write_text(json.dumps(skill_data))

        forge = SkillForge(skill_library_path=skills_dir)
        assert "TestSkill" in forge.known_skills
        assert forge.known_skills["TestSkill"].description == "A test skill"
        assert len(forge.known_skills["TestSkill"].optimized_chain.steps) == 3

    def test_handles_corrupt_skill_file(self, tmp_path: Path):
        """Corrupt JSON files are skipped with a warning, not crashed."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "corrupt.json").write_text("{invalid json")

        forge = SkillForge(skill_library_path=skills_dir)
        assert forge.known_skills == {}


class TestAssessPattern:
    """Tests for the assess_pattern heuristic."""

    def test_forges_complex_successful_chain(self, forge: SkillForge, simple_chain: ExecutionChain):
        assert forge.assess_pattern(simple_chain, 1.0) is True

    def test_forges_at_threshold(self, forge: SkillForge, simple_chain: ExecutionChain):
        assert forge.assess_pattern(simple_chain, 0.81) is True

    def test_rejects_low_success(self, forge: SkillForge, simple_chain: ExecutionChain):
        assert forge.assess_pattern(simple_chain, 0.79) is False

    def test_rejects_short_chain(self, forge: SkillForge, short_chain: ExecutionChain):
        assert forge.assess_pattern(short_chain, 1.0) is False

    def test_rejects_empty_chain(self, forge: SkillForge):
        empty = ExecutionChain(intent="empty", steps=[], estimated_complexity=0, required_capabilities=[])
        assert forge.assess_pattern(empty, 1.0) is False


class TestForge:
    """Tests for the forge method."""

    def test_creates_forged_skill(self, forge: SkillForge, simple_chain: ExecutionChain):
        skill = forge.forge(simple_chain, "ResearchFlow")
        assert isinstance(skill, ForgedSkill)
        assert skill.name == "ResearchFlow"
        assert "research memory systems" in skill.description
        assert skill.trigger_phrases == ["research memory systems"]
        assert skill.optimized_chain == simple_chain

    def test_persists_to_disk(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "ResearchFlow")
        skill_file = forge.skill_library_path / "researchflow.json"
        assert skill_file.exists()

        data = json.loads(skill_file.read_text())
        assert data["name"] == "ResearchFlow"
        assert len(data["steps"]) == 3
        assert data["steps"][0]["mansion"] == "NET"

    def test_registers_in_known_skills(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "ResearchFlow")
        assert "ResearchFlow" in forge.known_skills

    def test_generates_skills_md_catalog(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "ResearchFlow")
        catalog = forge.skill_library_path.parent / "SKILLS.md"
        assert catalog.exists()
        content = catalog.read_text()
        assert "ResearchFlow" in content
        assert "Skill Name" in content


class TestSaveSkill:
    """Tests for _save_skill JSON format."""

    def test_json_structure(self, forge: SkillForge, simple_chain: ExecutionChain):
        skill = ForgedSkill(
            name="TestSkill",
            description="Test description",
            trigger_phrases=["trigger1", "trigger2"],
            optimized_chain=simple_chain,
        )
        forge._save_skill(skill)

        data = json.loads((forge.skill_library_path / "testskill.json").read_text())
        assert data["name"] == "TestSkill"
        assert data["description"] == "Test description"
        assert data["triggers"] == ["trigger1", "trigger2"]
        assert len(data["steps"]) == 3
        for step in data["steps"]:
            assert "mansion" in step
            assert "operation" in step
            assert "context" in step


class TestLoadSkills:
    """Tests for _load_skills round-trip."""

    def test_round_trip(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "RoundTrip")
        forge2 = SkillForge(skill_library_path=forge.skill_library_path)
        assert "RoundTrip" in forge2.known_skills
        loaded = forge2.known_skills["RoundTrip"]
        # On reload, intent is set from the description field
        assert "research memory systems" in loaded.optimized_chain.intent
        assert len(loaded.optimized_chain.steps) == 3
        assert loaded.optimized_chain.steps[0].mansion == "NET"

    def test_multiple_skills_loaded(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "SkillA")
        forge.forge(simple_chain, "SkillB")
        forge2 = SkillForge(skill_library_path=forge.skill_library_path)
        assert len(forge2.known_skills) == 2
        assert "SkillA" in forge2.known_skills
        assert "SkillB" in forge2.known_skills


class TestSingleton:
    """Tests for singleton accessors."""

    def test_get_returns_instance(self):
        reset_skill_forge()
        forge = get_skill_forge()
        assert isinstance(forge, SkillForge)

    def test_get_returns_same_instance(self):
        reset_skill_forge()
        f1 = get_skill_forge()
        f2 = get_skill_forge()
        assert f1 is f2

    def test_reset_clears_singleton(self):
        f1 = get_skill_forge()
        reset_skill_forge()
        f2 = get_skill_forge()
        assert f1 is not f2


class TestAutoForgeIntegration:
    """Tests for the auto-forge path in UniversalRouter.execute."""

    @pytest.mark.asyncio
    async def test_auto_forges_on_success(self, tmp_path: Path, simple_chain: ExecutionChain):
        """When execute succeeds with >80% success and >2 steps, a skill is forged."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        reset_skill_forge()
        forge = SkillForge(skill_library_path=skills_dir)
        assert len(forge.known_skills) == 0

        # Mock the gana dispatch to succeed
        mock_gana = MagicMock()
        mock_gana.dispatch_operation = AsyncMock(return_value={"result": "ok"})

        with patch(
            "whitemagic.core.ganas.registry.get_gana_for_tool",
            return_value=mock_gana,
        ), patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=forge,
        ):
            router = UniversalRouter()
            result = await router.execute(simple_chain)

        assert result["status"] == "success"
        assert len(forge.known_skills) == 1

    @pytest.mark.asyncio
    async def test_does_not_forge_on_failure(self, tmp_path: Path, simple_chain: ExecutionChain):
        """When execute has errors, no skill is forged."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        reset_skill_forge()
        forge = SkillForge(skill_library_path=skills_dir)

        # Mock gana to raise errors
        mock_gana = MagicMock()
        mock_gana.dispatch_operation = AsyncMock(side_effect=RuntimeError("fail"))

        with patch(
            "whitemagic.core.ganas.registry.get_gana_for_tool",
            return_value=mock_gana,
        ), patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=forge,
        ):
            router = UniversalRouter()
            result = await router.execute(simple_chain)

        assert result["status"] == "success"  # execute always returns success
        assert len(forge.known_skills) == 0  # but no skill forged

    @pytest.mark.asyncio
    async def test_does_not_forge_short_chain(self, tmp_path: Path, short_chain: ExecutionChain):
        """Short chains (<3 steps) are not forged even if successful."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        reset_skill_forge()
        forge = SkillForge(skill_library_path=skills_dir)

        mock_gana = MagicMock()
        mock_gana.dispatch_operation = AsyncMock(return_value={"result": "ok"})

        with patch(
            "whitemagic.core.ganas.registry.get_gana_for_tool",
            return_value=mock_gana,
        ), patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=forge,
        ):
            router = UniversalRouter()
            await router.execute(short_chain)

        assert len(forge.known_skills) == 0
