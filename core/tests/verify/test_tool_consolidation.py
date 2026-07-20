"""P1.3 — Consolidate into the existing tool type.

Tests for ToolDefinition strict construction, alias modeling, and
deterministic serialization snapshot.
"""
import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.tools.tool_types import (
    FastPathSafety,
    ToolCategory,
    ToolDefinition,
    ToolSafety,
    ToolStability,
)


class TestStrictConstruction:
    """Verify __post_init__ validation enforces construction invariants."""

    def _make(self, **kwargs):
        defaults = dict(
            name="test.tool",
            description="A test tool",
            category=ToolCategory.INTROSPECTION,
            safety=ToolSafety.READ,
            input_schema={},
        )
        defaults.update(kwargs)
        return ToolDefinition(**defaults)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name must be non-empty"):
            self._make(name="")

    def test_whitespace_name_rejected(self):
        with pytest.raises(ValueError, match="name must be non-empty"):
            self._make(name="   ")

    def test_empty_description_rejected(self):
        with pytest.raises(ValueError, match="description must be non-empty"):
            self._make(description="")

    def test_stable_with_unclassified_safety_rejected(self):
        with pytest.raises(ValueError, match="STABLE with UNCLASSIFIED"):
            self._make(
                safety=ToolSafety.UNCLASSIFIED,
                stability=ToolStability.STABLE,
            )

    def test_fast_path_without_read_safety_rejected(self):
        with pytest.raises(ValueError, match="READ safety"):
            self._make(
                fast_path=True,
                safety=ToolSafety.WRITE,
                fast_path_safety=FastPathSafety(),
            )

    def test_fast_path_without_safety_declaration_rejected(self):
        with pytest.raises(ValueError, match="fast_path_safety"):
            self._make(fast_path=True, fast_path_safety=None)

    def test_valid_construction_succeeds(self):
        td = self._make()
        assert td.name == "test.tool"
        assert td.safety == ToolSafety.READ
        assert td.stability == ToolStability.OPTIONAL


class TestAliasModeling:
    """Verify aliases field is modeled on ToolDefinition."""

    def test_aliases_default_empty(self):
        td = self._make_td()
        assert td.aliases == ()

    def test_aliases_stored(self):
        td = self._make_td(aliases=("old_name", "legacy_name"))
        assert "old_name" in td.aliases
        assert "legacy_name" in td.aliases

    def test_aliases_in_to_dict(self):
        td = self._make_td(aliases=("old_name",))
        d = td.to_dict()
        assert d["aliases"] == ["old_name"]

    def test_aliases_in_snapshot(self):
        td = self._make_td(aliases=("b", "a", "c"))
        snap = td.to_snapshot()
        assert snap["aliases"] == ["a", "b", "c"]

    def _make_td(self, **kwargs):
        defaults = dict(
            name="test.tool",
            description="A test tool",
            category=ToolCategory.INTROSPECTION,
            safety=ToolSafety.READ,
            input_schema={},
        )
        defaults.update(kwargs)
        return ToolDefinition(**defaults)


class TestSinceVersion:
    """Verify since_version field is modeled on ToolDefinition."""

    def test_since_version_default_none(self):
        td = self._make_td()
        assert td.since_version is None

    def test_since_version_stored(self):
        td = self._make_td(since_version="25.0.0")
        assert td.since_version == "25.0.0"

    def test_since_version_in_to_dict(self):
        td = self._make_td(since_version="25.0.0")
        d = td.to_dict()
        assert d["since_version"] == "25.0.0"

    def test_since_version_in_snapshot(self):
        td = self._make_td(since_version="25.0.0")
        snap = td.to_snapshot()
        assert snap["since_version"] == "25.0.0"

    def _make_td(self, **kwargs):
        defaults = dict(
            name="test.tool",
            description="A test tool",
            category=ToolCategory.INTROSPECTION,
            safety=ToolSafety.READ,
            input_schema={},
        )
        defaults.update(kwargs)
        return ToolDefinition(**defaults)


class TestSnapshot:
    """Verify deterministic serialization snapshot for CI/docs."""

    def _make_td(self, **kwargs):
        defaults = dict(
            name="test.tool",
            description="A test tool",
            category=ToolCategory.INTROSPECTION,
            safety=ToolSafety.READ,
            input_schema={"type": "object"},
        )
        defaults.update(kwargs)
        return ToolDefinition(**defaults)

    def test_snapshot_has_content_hash(self):
        snap = self._make_td().to_snapshot()
        assert "content_hash" in snap
        assert len(snap["content_hash"]) == 16

    def test_snapshot_is_deterministic(self):
        td = self._make_td()
        snap1 = td.to_snapshot()
        snap2 = td.to_snapshot()
        assert snap1["content_hash"] == snap2["content_hash"]

    def test_snapshot_hash_changes_on_field_change(self):
        td1 = self._make_td(description="Description A")
        td2 = self._make_td(description="Description B")
        assert td1.to_snapshot()["content_hash"] != td2.to_snapshot()["content_hash"]

    def test_snapshot_includes_all_fields(self):
        td = self._make_td(
            gana="gana_heart",
            garden="joy",
            quadrant="q1",
            element="fire",
            permissions=("read", "write"),
            stability=ToolStability.STABLE,
            fast_path=True,
            fast_path_safety=FastPathSafety(),
            aliases=("old_name",),
            since_version="25.0.0",
        )
        snap = td.to_snapshot()
        expected_keys = {
            "aliases", "category", "content_hash", "description", "element",
            "fast_path", "fast_path_eligible", "fast_path_safety", "gana",
            "garden", "input_schema", "name", "permissions", "quadrant",
            "safety", "since_version", "stability",
        }
        assert set(snap.keys()) == expected_keys

    def test_snapshot_fast_path_safety_serialized(self):
        td = self._make_td(
            fast_path=True,
            fast_path_safety=FastPathSafety(no_network=False),
        )
        snap = td.to_snapshot()
        assert snap["fast_path_safety"]["no_network"] is False
        assert snap["fast_path_safety"]["no_writes"] is True

    def test_snapshot_fast_path_safety_none_when_not_set(self):
        td = self._make_td()
        snap = td.to_snapshot()
        assert snap["fast_path_safety"] is None


class TestRegistrySnapshotConsistency:
    """Verify all registry ToolDefinitions can produce snapshots."""

    def test_all_registry_tools_snapshot_without_error(self):
        from whitemagic.tools.registry import TOOL_REGISTRY
        for td in TOOL_REGISTRY:
            snap = td.to_snapshot()
            assert "content_hash" in snap
            assert len(snap["content_hash"]) == 16

    def test_snapshot_hashes_are_unique(self):
        from whitemagic.tools.registry import TOOL_REGISTRY
        hashes = [td.to_snapshot()["content_hash"] for td in TOOL_REGISTRY]
        unique = set(hashes)
        assert len(unique) == len(hashes), (
            f"Duplicate content_hashes found: {len(hashes) - len(unique)} collisions"
        )
