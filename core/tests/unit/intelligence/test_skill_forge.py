"""Unit tests for SkillForge — the Recursive Blacksmith.

Tests cover:
- Path hygiene (writes to WM_STATE_ROOT/skills, not memory/skills)
- assess_pattern heuristic (including slop detection)
- forge (creates + persists skill, auto-name generation)
- Duplicate detection (exact + similarity-based)
- _save_skill (JSON format, disk write)
- _load_skills (round-trip from disk)
- _update_skills_md (catalog generation)
- Singleton get_skill_forge / reset_skill_forge
- Auto-forge integration via UniversalRouter.execute
- ChainTracker (call sequence tracking + auto-forge trigger)
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from whitemagic.core.intelligence.omni.chain_tracker import (
    ChainTracker,
    get_chain_tracker,
    reset_chain_tracker,
)
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


@pytest.fixture
def slop_chain() -> ExecutionChain:
    """Create a chain with excessive repetition (slop)."""
    return ExecutionChain(
        intent="repetitive task",
        steps=[
            GanaStep(mansion="NET", operation="search", context_key="a", parameters={}),
            GanaStep(mansion="NET", operation="search", context_key="b", parameters={}),
            GanaStep(mansion="NET", operation="search", context_key="c", parameters={}),
        ],
        estimated_complexity=2.4,
        required_capabilities=[],
    )


@pytest.fixture
def similar_chain() -> ExecutionChain:
    """Create a chain similar to simple_chain but with different context keys."""
    return ExecutionChain(
        intent="research memory architectures",
        steps=[
            GanaStep(mansion="NET", operation="search", context_key="query", parameters={}),
            GanaStep(mansion="GHOST", operation="analyze", context_key="validation", parameters={}),
            GanaStep(mansion="WINNOWING_BASKET", operation="consolidate", context_key="dedup", parameters={}),
        ],
        estimated_complexity=2.4,
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

    def test_rejects_slop_chain(self, forge: SkillForge, slop_chain: ExecutionChain):
        """Chains with excessive repetition are rejected."""
        assert forge.assess_pattern(slop_chain, 1.0) is False


class TestSlopDetection:
    """Tests for the _detect_slop method."""

    def test_detects_repeated_ops(self, forge: SkillForge):
        """Same (mansion, operation) repeated > SLOP_MAX_REPEAT times is slop."""
        chain = ExecutionChain(
            intent="repetitive",
            steps=[
                GanaStep("NET", "search", "a", {}),
                GanaStep("NET", "search", "b", {}),
                GanaStep("NET", "search", "c", {}),
            ],
            estimated_complexity=2.4,
            required_capabilities=[],
        )
        assert forge._detect_slop(chain) is True

    def test_all_identical_steps_is_slop(self, forge: SkillForge):
        """All steps identical with >2 steps is slop."""
        chain = ExecutionChain(
            intent="trivial",
            steps=[
                GanaStep("HORN", "search", "x", {}),
                GanaStep("HORN", "search", "x", {}),
                GanaStep("HORN", "search", "x", {}),
            ],
            estimated_complexity=2.4,
            required_capabilities=[],
        )
        assert forge._detect_slop(chain) is True

    def test_diverse_chain_not_slop(self, forge: SkillForge, simple_chain: ExecutionChain):
        """A diverse chain is not slop."""
        assert forge._detect_slop(simple_chain) is False

    def test_empty_chain_is_slop(self, forge: SkillForge):
        """Empty chains are slop."""
        chain = ExecutionChain(intent="empty", steps=[], estimated_complexity=0, required_capabilities=[])
        assert forge._detect_slop(chain) is True

    def test_two_repeats_ok(self, forge: SkillForge):
        """Repeating an op twice is OK (SLOP_MAX_REPEAT=2)."""
        chain = ExecutionChain(
            intent="moderate",
            steps=[
                GanaStep("NET", "search", "a", {}),
                GanaStep("NET", "search", "b", {}),
                GanaStep("GHOST", "analyze", "c", {}),
            ],
            estimated_complexity=2.4,
            required_capabilities=[],
        )
        assert forge._detect_slop(chain) is False


class TestForge:
    """Tests for the forge method."""

    def test_creates_forged_skill_with_explicit_name(self, forge: SkillForge, simple_chain: ExecutionChain):
        skill = forge.forge(simple_chain, "ResearchFlow")
        assert isinstance(skill, ForgedSkill)
        assert skill.name == "ResearchFlow"
        assert "research memory systems" in skill.description
        assert skill.trigger_phrases == ["research memory systems"]
        assert skill.optimized_chain == simple_chain

    def test_auto_generates_name(self, forge: SkillForge, simple_chain: ExecutionChain):
        """When name is None, a heuristic name is generated (LLM unavailable in tests)."""
        skill = forge.forge(simple_chain)
        assert isinstance(skill, ForgedSkill)
        assert skill.name  # non-empty
        # Heuristic format: keyword_mansion_Nstep
        assert "net" in skill.name or "research" in skill.name

    def test_persists_to_disk(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "ResearchFlow")
        skill_file = forge.skill_library_path / "researchflow.json"
        assert skill_file.exists()

        data = json.loads(skill_file.read_text())
        assert data["name"] == "ResearchFlow"
        assert len(data["steps"]) == 3
        assert data["steps"][0]["mansion"] == "NET"

    def test_persists_forge_count(self, forge: SkillForge, simple_chain: ExecutionChain):
        """forge_count is persisted to disk."""
        forge.forge(simple_chain, "ResearchFlow")
        data = json.loads((forge.skill_library_path / "researchflow.json").read_text())
        assert data["forge_count"] == 1

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
        assert "Forge Count" in content


class TestDuplicateDetection:
    """Tests for duplicate and similarity detection."""

    def test_exact_duplicate_increments_count(self, forge: SkillForge, simple_chain: ExecutionChain):
        """Forging the same chain twice increments forge_count instead of creating a new skill."""
        skill1 = forge.forge(simple_chain, "ResearchFlow")
        assert skill1.forge_count == 1
        assert len(forge.known_skills) == 1

        skill2 = forge.forge(simple_chain, "ResearchFlow")
        assert skill2.forge_count == 2
        assert len(forge.known_skills) == 1
        assert skill1 is skill2

    def test_similar_chain_detected_as_duplicate(self, forge: SkillForge, simple_chain: ExecutionChain, similar_chain: ExecutionChain):
        """A chain with same (mansion, operation) pairs is detected as duplicate."""
        forge.forge(simple_chain, "ResearchFlow")
        assert len(forge.known_skills) == 1

        # similar_chain has same mansion/operation pairs, different context_keys
        result = forge.forge(similar_chain, "SimilarFlow")
        assert len(forge.known_skills) == 1  # no new skill
        assert result.forge_count == 2

    def test_different_chain_creates_new_skill(self, forge: SkillForge, simple_chain: ExecutionChain):
        """A genuinely different chain creates a new skill."""
        forge.forge(simple_chain, "ResearchFlow")

        different = ExecutionChain(
            intent="deploy application",
            steps=[
                GanaStep("WINGS", "transform", "export", {}),
                GanaStep("STAR", "analyze", "validate", {}),
                GanaStep("CHARIOT", "search", "navigate", {}),
            ],
            estimated_complexity=2.4,
            required_capabilities=[],
        )
        forge.forge(different, "DeployFlow")
        assert len(forge.known_skills) == 2


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
        assert data["forge_count"] == 1
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
        assert "research memory systems" in loaded.optimized_chain.intent
        assert len(loaded.optimized_chain.steps) == 3
        assert loaded.optimized_chain.steps[0].mansion == "NET"

    def test_multiple_skills_loaded(self, forge: SkillForge, simple_chain: ExecutionChain):
        forge.forge(simple_chain, "SkillA")
        different = ExecutionChain(
            intent="deploy app",
            steps=[
                GanaStep("WINGS", "transform", "export", {}),
                GanaStep("STAR", "analyze", "validate", {}),
                GanaStep("CHARIOT", "search", "navigate", {}),
            ],
            estimated_complexity=2.4,
            required_capabilities=[],
        )
        forge.forge(different, "SkillB")
        forge2 = SkillForge(skill_library_path=forge.skill_library_path)
        assert len(forge2.known_skills) == 2
        assert "SkillA" in forge2.known_skills
        assert "SkillB" in forge2.known_skills

    def test_forge_count_persisted(self, forge: SkillForge, simple_chain: ExecutionChain):
        """forge_count survives round-trip."""
        skill = forge.forge(simple_chain, "Counted")
        skill.forge_count = 5
        forge._save_skill(skill)

        forge2 = SkillForge(skill_library_path=forge.skill_library_path)
        assert forge2.known_skills["Counted"].forge_count == 5


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

        assert result["status"] == "success"
        assert len(forge.known_skills) == 0

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

    @pytest.mark.asyncio
    async def test_does_not_forge_slop(self, tmp_path: Path, slop_chain: ExecutionChain):
        """Slop chains are not forged even if successful."""
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
            await router.execute(slop_chain)

        assert len(forge.known_skills) == 0


class TestChainTracker:
    """Tests for the ChainTracker that bridges wm() calls to SkillForge."""

    def test_records_calls(self):
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "remember X", True)
        tracker.record("gana_ghost", "gnosis", "check state", True)
        assert tracker.call_count == 2

    def test_flush_too_short_returns_none(self):
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "remember X", True)
        result = tracker.flush()
        assert result is None
        assert tracker.call_count == 0  # cleared regardless

    def test_flush_builds_chain(self):
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "remember X", True)
        tracker.record("gana_ghost", "gnosis", "check state", True)
        tracker.record("gana_root", "health_report", "system check", True)
        chain = tracker.flush()
        assert chain is not None
        assert len(chain.steps) == 3
        assert chain.steps[0].mansion == "NECK"
        assert chain.steps[1].mansion == "GHOST"
        assert chain.steps[2].mansion == "ROOT"

    def test_infer_operation(self):
        assert ChainTracker._infer_operation("create_memory") == "transform"
        assert ChainTracker._infer_operation("gnosis") == "analyze"
        assert ChainTracker._infer_operation("export_memories") == "consolidate"
        assert ChainTracker._infer_operation("search_memories") == "search"
        assert ChainTracker._infer_operation(None) == "search"

    def test_should_flush_false_below_threshold(self):
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "x", True)
        tracker.record("gana_ghost", "gnosis", "y", True)
        assert tracker.should_flush() is False

    def test_reset_clears(self):
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "x", True)
        tracker.reset()
        assert tracker.call_count == 0

    def test_try_auto_forge_success(self, tmp_path: Path):
        """With enough calls, try_auto_forge creates a skill."""
        reset_skill_forge()
        reset_chain_tracker()

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        forge = SkillForge(skill_library_path=skills_dir)
        tracker = ChainTracker()

        tracker.record("gana_neck", "create_memory", "remember the API", True)
        tracker.record("gana_ghost", "gnosis", "check current state", True)
        tracker.record("gana_root", "health_report", "verify health", True)

        with patch(
            "whitemagic.core.intelligence.omni.skill_forge.get_skill_forge",
            return_value=forge,
        ):
            # Force flush by setting last_flush in the past
            import time as _time
            tracker._last_flush = _time.time() - 100
            result = tracker.try_auto_forge()

        assert result is not None
        assert isinstance(result, ForgedSkill)
        assert len(forge.known_skills) == 1

    def test_try_auto_forge_too_few_calls(self):
        """With fewer than MIN_CHAIN_LENGTH calls, no forge happens."""
        reset_chain_tracker()
        tracker = ChainTracker()
        tracker.record("gana_neck", "create_memory", "x", True)
        tracker.record("gana_ghost", "gnosis", "y", True)
        result = tracker.try_auto_forge()
        assert result is None

    def test_singleton(self):
        reset_chain_tracker()
        t1 = get_chain_tracker()
        t2 = get_chain_tracker()
        assert t1 is t2

    def test_reset_singleton(self):
        t1 = get_chain_tracker()
        reset_chain_tracker()
        t2 = get_chain_tracker()
        assert t1 is not t2


class TestExportSkillMd:
    """Test SKILL.md export bridge — auto-forged skills → portable format."""

    def test_exports_single_skill(self, forge: SkillForge, simple_chain: ExecutionChain, tmp_path: Path):
        """export_skill_md writes a valid SKILL.md file."""
        skill = forge.forge(simple_chain, name="test_export_skill")
        export_dir = tmp_path / "exported"
        path = forge.export_skill_md(skill, output_dir=export_dir)

        assert path.exists()
        assert path.suffix == ".md"
        content = path.read_text()

        # Check frontmatter
        assert content.startswith("---")
        assert "name: test_export_skill" in content
        assert "license: MIT" in content
        assert "auto_forged: true" in content
        assert "forge_count: 1" in content

        # Check body
        assert "## When to Use" in content
        assert "## How to Invoke" in content
        assert "## Chain Steps" in content
        assert "wm(route=" in content

    def test_exports_all_skills(self, forge: SkillForge, simple_chain: ExecutionChain, tmp_path: Path):
        """export_all_skills_md writes SKILL.md for every known skill."""
        # Use a genuinely different chain to avoid duplicate detection
        different_chain = ExecutionChain(
            intent="monitor system health",
            steps=[
                GanaStep(mansion="ROOT", operation="analyze", context_key="health", parameters={}),
                GanaStep(mansion="MOUND", operation="transform", context_key="metrics", parameters={}),
                GanaStep(mansion="HAIRY_HEAD", operation="consolidate", context_key="karma", parameters={}),
            ],
            estimated_complexity=2.0,
            required_capabilities=[],
        )
        forge.forge(simple_chain, name="skill_alpha")
        forge.forge(different_chain, name="skill_beta")
        assert len(forge.known_skills) == 2

        export_dir = tmp_path / "exported"
        paths = forge.export_all_skills_md(output_dir=export_dir)

        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert p.suffix == ".md"

    def test_exported_filename_is_lowercase(self, forge: SkillForge, simple_chain: ExecutionChain, tmp_path: Path):
        """SKILL.md filename should be lowercase skill name."""
        skill = forge.forge(simple_chain, name="MyComplexSkill")
        export_dir = tmp_path / "exported"
        path = forge.export_skill_md(skill, output_dir=export_dir)

        assert path.name == "mycomplexskill.md"

    def test_exported_skill_has_correct_metadata(self, forge: SkillForge, simple_chain: ExecutionChain, tmp_path: Path):
        """SKILL.md metadata should reflect the forged skill's properties."""
        skill = forge.forge(simple_chain, name="metadata_test")
        export_dir = tmp_path / "exported"
        path = forge.export_skill_md(skill, output_dir=export_dir)
        content = path.read_text()

        assert "step_count: 3" in content
        assert f"complexity: {simple_chain.estimated_complexity:.1f}" in content
        assert simple_chain.intent in content

    def test_exported_skill_lists_all_steps(self, forge: SkillForge, simple_chain: ExecutionChain, tmp_path: Path):
        """SKILL.md should list all chain steps."""
        skill = forge.forge(simple_chain, name="steps_test")
        export_dir = tmp_path / "exported"
        path = forge.export_skill_md(skill, output_dir=export_dir)
        content = path.read_text()

        for step in simple_chain.steps:
            assert step.mansion.lower() in content.lower()
            assert step.operation in content
            assert step.context_key in content

    def test_export_default_dir(self, forge: SkillForge, simple_chain: ExecutionChain):
        """export_skill_md uses default export dir when output_dir is None."""
        skill = forge.forge(simple_chain, name="default_dir_test")
        path = forge.export_skill_md(skill)

        assert path.exists()
        assert path.parent == forge.skill_library_path / "exported"
