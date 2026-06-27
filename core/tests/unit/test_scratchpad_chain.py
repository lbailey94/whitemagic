"""Tests for scratchpad chain-of-thought state tracking and branching.

Validates that the upgraded Scratchpad/ScratchpadManager supports
sequential-thinking-style chain state (thought_number, total_thoughts),
branching (branch_id, branch_from), and revision (is_revision, revises_entry).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager


@pytest.fixture
def manager(tmp_path: Path) -> ScratchpadManager:
    return ScratchpadManager(scratch_dir=tmp_path / "scratchpads")


class TestScratchpadChainState:
    """Test chain state tracking on Scratchpad."""

    def test_auto_increment_thought_number(self, manager: ScratchpadManager):
        manager.write_to("test-chain", "First thought")
        manager.write_to("test-chain", "Second thought")
        manager.write_to("test-chain", "Third thought")

        status = manager.get_chain_status("test-chain")
        assert status["thought_number"] == 3
        assert status["thought_history_length"] == 3
        assert status["main_chain_length"] == 3
        assert status["branch_count"] == 0

    def test_explicit_thought_number(self, manager: ScratchpadManager):
        entry = manager.write_to("test-explicit", "Step 2", thought_number=2, total_thoughts=5)
        assert entry["thought_number"] == 2
        assert entry["total_thoughts"] == 5

    def test_total_thoughts_defaults_to_thought_number(self, manager: ScratchpadManager):
        entry = manager.write_to("test-default", "Only thought")
        assert entry["thought_number"] == 1
        assert entry["total_thoughts"] == 1

    def test_entry_has_entry_index(self, manager: ScratchpadManager):
        manager.write_to("test-idx", "First")
        entry2 = manager.write_to("test-idx", "Second")
        assert entry2["entry_index"] == 1


class TestScratchpadBranching:
    """Test branching support."""

    def test_branch_creates_separate_chain(self, manager: ScratchpadManager):
        manager.write_to("test-branch", "Main 1")
        manager.write_to("test-branch", "Main 2")
        manager.write_to("test-branch", "Branch A thought 1", branch_id="branch-a", branch_from=2)
        manager.write_to("test-branch", "Branch A thought 2", branch_id="branch-a")

        status = manager.get_chain_status("test-branch")
        assert status["main_chain_length"] == 2
        assert status["branch_count"] == 1
        assert "branch-a" in status["branches"]
        assert status["thought_history_length"] == 4

    def test_branch_auto_increments_within_branch(self, manager: ScratchpadManager):
        manager.write_to("test-bi", "Main 1")
        manager.write_to("test-bi", "Branch thought", branch_id="b1", branch_from=1)
        entry = manager.write_to("test-bi", "Branch thought 2", branch_id="b1")

        assert entry["thought_number"] == 2
        assert entry["branch_id"] == "b1"

    def test_multiple_branches(self, manager: ScratchpadManager):
        manager.write_to("test-multi", "Main 1")
        manager.write_to("test-multi", "B1 thought", branch_id="b1", branch_from=1)
        manager.write_to("test-multi", "B2 thought", branch_id="b2", branch_from=1)

        status = manager.get_chain_status("test-multi")
        assert status["branch_count"] == 2
        assert set(status["branches"]) == {"b1", "b2"}


class TestScratchpadRevision:
    """Test revision support."""

    def test_revision_flag(self, manager: ScratchpadManager):
        manager.write_to("test-rev", "Original thought")
        entry = manager.write_to(
            "test-rev",
            "Actually, revised thinking",
            is_revision=True,
            revises_entry=0,
        )

        assert entry["is_revision"] is True
        assert entry["revises_entry"] == 0

        status = manager.get_chain_status("test-rev")
        assert status["is_revision"] is True


class TestScratchpadPersistence:
    """Test that chain state survives save/load."""

    def test_chain_state_persisted(self, tmp_path: Path):
        manager1 = ScratchpadManager(scratch_dir=tmp_path / "scratchpads")
        manager1.write_to("test-persist", "Thought 1")
        manager1.write_to("test-persist", "Thought 2", branch_id="b1", branch_from=1)

        # Save is automatic, create a new manager to load
        manager2 = ScratchpadManager(scratch_dir=tmp_path / "scratchpads")
        status = manager2.get_chain_status("test-persist")
        assert status["thought_history_length"] == 2
        assert status["main_chain_length"] == 1
        assert status["branch_count"] == 1

    def test_to_dict_includes_chain_metadata(self, manager: ScratchpadManager):
        manager.write_to("test-dict", "Thought")
        pad = manager.scratchpads["test-dict"]
        d = pad.to_dict()
        assert "main_chain_length" in d
        assert "branch_count" in d
        assert d["main_chain_length"] == 1


class TestScratchpadBackwardCompat:
    """Test that old scratchpads without chain state still load."""

    def test_old_format_loads(self, tmp_path: Path):
        scratch_dir = tmp_path / "scratchpads"
        scratch_dir.mkdir()
        # Write an old-format scratchpad (no chain state fields)
        old_data = {
            "name": "old-pad",
            "focus": None,
            "entries": [
                {"content": "Old thought", "tag": "current_focus", "timestamp": "2024-01-01T00:00:00"},
            ],
            "created": "2024-01-01T00:00:00",
            "last_active": "2024-01-01T00:00:00",
        }
        (scratch_dir / "old-pad.json").write_text(json.dumps(old_data))

        manager = ScratchpadManager(scratch_dir=scratch_dir)
        assert "old-pad" in manager.scratchpads
        # New writes should work on loaded old pads — old entry counts as chain position 1
        entry = manager.write_to("old-pad", "New thought after load")
        assert entry["thought_number"] == 2  # Old entry was 1, new entry is 2
