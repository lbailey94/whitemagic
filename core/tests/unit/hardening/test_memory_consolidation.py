"""Tests for memory write path consolidation.

Verifies that:
- handle_create_memory delegates to _write_memory (canonical path)
- Both create_memory and wm_write(mode="memory") produce the same result shape
- create_memory preserves its unique features (title requirement, wu_xing, emit_gan_ying)
- The enrichment flags are correctly passed through
- FK error fallback still works
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from whitemagic.tools.handlers.memory import handle_create_memory
from whitemagic.tools.errors import ToolExecutionError


class TestCreateMemoryDelegation:
    """Verify handle_create_memory delegates to _write_memory."""

    def test_calls_write_memory(self):
        """handle_create_memory should call _write_memory from wm_write.py."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            result = handle_create_memory(
                content="test content",
                title="test title",
                tags=["test"],
            )
            assert mock_write.called
            call_kwargs = mock_write.call_args[0][0]
            assert call_kwargs["content"] == "test content"
            assert call_kwargs["title"] == "test title"
            assert call_kwargs["mode"] == "memory"

    def test_preserves_enrichment_defaults(self):
        """create_memory should default to surprise_gate=False, entity_extraction=True."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            handle_create_memory(content="test", title="test")
            call_kwargs = mock_write.call_args[0][0]
            assert call_kwargs["enable_surprise_gate"] is False
            assert call_kwargs["enable_entity_extraction"] is True
            assert call_kwargs["enable_holographic_index"] is True

    def test_title_required(self):
        """create_memory should raise ToolExecutionError if title is missing."""
        with pytest.raises(ToolExecutionError):
            handle_create_memory(content="test content")

    def test_content_required(self):
        """create_memory should raise ToolExecutionError if content is missing."""
        with pytest.raises(ToolExecutionError):
            handle_create_memory(title="test title")

    def test_empty_title_rejected(self):
        """create_memory should reject empty title."""
        with pytest.raises(ToolExecutionError):
            handle_create_memory(content="test", title="   ")

    def test_empty_content_rejected(self):
        """create_memory should reject empty content."""
        with pytest.raises(ToolExecutionError):
            handle_create_memory(title="test", content="   ")

    def test_tags_passed_through(self):
        """Tags should be passed through to _write_memory."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            handle_create_memory(content="test", title="test", tags=["a", "b"])
            call_kwargs = mock_write.call_args[0][0]
            assert "tags" in call_kwargs

    def test_metadata_passed_through(self):
        """Metadata should be passed through to _write_memory."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            handle_create_memory(
                content="test", title="test", metadata={"key": "value"}
            )
            call_kwargs = mock_write.call_args[0][0]
            assert call_kwargs["metadata"]["key"] == "value"

    def test_importance_passed_through(self):
        """Importance should be passed through if provided."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            handle_create_memory(content="test", title="test", importance=0.9)
            call_kwargs = mock_write.call_args[0][0]
            assert call_kwargs["importance"] == 0.9

    def test_returns_write_memory_result(self):
        """Result should come from _write_memory, including enrichment metadata."""
        expected = {
            "status": "success",
            "mode": "memory",
            "memory_id": "abc-123",
            "enrichment": {
                "surprise_gate": False,
                "entity_extraction": True,
                "holographic_index": True,
                "auto_embed": False,
            },
        }
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = expected
            result = handle_create_memory(content="test", title="test")
            assert result == expected
            assert result["enrichment"]["surprise_gate"] is False


class TestCreateMemoryFKFallback:
    """Verify FK error fallback still works after consolidation."""

    def test_fk_fallback_disables_enrichment(self):
        """On FOREIGN KEY error, should retry with enrichment disabled."""
        call_count = [0]
        def mock_write(kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("FOREIGN KEY constraint failed")
            return {"status": "success", "memory_id": "fallback-123"}

        with patch("whitemagic.tools.handlers.wm_write._write_memory", side_effect=mock_write):
            result = handle_create_memory(content="test", title="test")
            assert result["status"] == "success"
            assert result["memory_id"] == "fallback-123"
            assert call_count[0] == 2

    def test_non_fk_error_no_retry(self):
        """Non-FK errors should not trigger retry."""
        call_count = [0]
        def mock_write(kwargs):
            call_count[0] += 1
            raise Exception("Some other error")

        with patch("whitemagic.tools.handlers.wm_write._write_memory", side_effect=mock_write):
            result = handle_create_memory(content="test", title="test")
            assert result["status"] == "error"
            assert call_count[0] == 1


class TestCreateMemoryUniqueFeatures:
    """Verify create_memory-specific features are preserved."""

    def test_wu_xing_metadata_added(self):
        """include_wu_xing_metadata should add wu_xing phase to metadata."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            with patch("whitemagic.gardens.wisdom.wu_xing.get_wu_xing") as mock_wx:
                mock_wx.return_value.detect_current_phase.return_value.value = "fire"
                handle_create_memory(
                    content="test",
                    title="test",
                    include_wu_xing_metadata=True,
                )
            call_kwargs = mock_write.call_args[0][0]
            assert call_kwargs["metadata"].get("wu_xing_phase") == "fire"

    def test_emit_gan_ying_on_success(self):
        """emit_gan_ying=True should emit MEMORY_CREATED event on success."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            with patch("whitemagic.tools.handlers.memory._emit") as mock_emit:
                handle_create_memory(
                    content="test",
                    title="test",
                    emit_gan_ying=True,
                )
                mock_emit.assert_called_once()
                event_type, data = mock_emit.call_args[0]
                assert event_type == "MEMORY_CREATED"
                assert data["title"] == "test"

    def test_no_emit_on_error(self):
        """emit_gan_ying should not fire on error."""
        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.side_effect = Exception("some error")
            with patch("whitemagic.tools.handlers.memory._emit") as mock_emit:
                handle_create_memory(
                    content="test",
                    title="test",
                    emit_gan_ying=True,
                )
                mock_emit.assert_not_called()


class TestCanonicalPathConsistency:
    """Verify both write paths produce consistent results."""

    def test_both_paths_use_same_implementation(self):
        """create_memory and wm_write(mode='memory') should both call _write_memory."""
        from whitemagic.tools.handlers.wm_write import handle_wm_write

        with patch("whitemagic.tools.handlers.wm_write._write_memory") as mock_write:
            mock_write.return_value = {"status": "success", "memory_id": "test-123"}
            # create_memory path
            handle_create_memory(content="test", title="test")
            # wm_write path
            handle_wm_write(content="test", mode="memory", title="test")
            # Both should call _write_memory
            assert mock_write.call_count == 2
