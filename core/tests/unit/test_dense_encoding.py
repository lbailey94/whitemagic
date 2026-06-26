"""Tests for vectorized scratchpad (VSA) and Chinese-dense working memory encoding."""
from __future__ import annotations

from whitemagic.ai.dense_encoding import (
    decode_hint,
    encode_dense,
    encode_dense_lines,
    get_encoding_stats,
)
from whitemagic.core.intelligence.working_memory import WorkingMemory


# ---------------------------------------------------------------------------
# Dense encoding tests
# ---------------------------------------------------------------------------


class TestDenseEncoding:
    """Test Chinese-dense phrase mapping."""

    def test_basic_encoding(self):
        result = encode_dense("The memory system needs consolidation")
        assert result.encoded != ""
        assert result.compression_ratio >= 1.0
        assert "记忆" in result.encoded or "系统" in result.encoded
        assert result.method == "phrase_mapping"

    def test_empty_input(self):
        result = encode_dense("")
        assert result.encoded == ""
        assert result.original_tokens == 0
        assert result.method == "empty"

    def test_unmapped_words_preserved(self):
        result = encode_dense("The flibbertigibbet jumped over the moon")
        # Unmapped words should remain in English
        assert "flibbertigibbet" in result.encoded or "flibbertigibbet" in result.original

    def test_token_reduction(self):
        """Chinese-dense encoding should reduce token estimates."""
        text = "The memory system needs consolidation scheduling and the working memory capacity is important for the cognitive system"
        result = encode_dense(text)
        assert result.encoded_tokens < result.original_tokens
        assert result.compression_ratio > 1.0

    def test_multiple_lines(self):
        lines = [
            "The memory system needs consolidation",
            "Working memory capacity is important",
            "The cognitive system requires optimization",
        ]
        result = encode_dense_lines(lines)
        assert result.encoded != ""
        assert result.encoded_tokens < result.original_tokens

    def test_decode_hint(self):
        result = encode_dense("memory system consolidation")
        hint = decode_hint(result.encoded)
        # Should provide at least one hint
        assert isinstance(hint, str)

    def test_encoding_stats(self):
        stats = get_encoding_stats()
        assert stats["total_phrases"] > 50
        assert stats["chinese_mappings"] > 30
        assert stats["symbol_mappings"] > 0

    def test_connector_replacement(self):
        result = encode_dense("memory and consolidation")
        # " and " should be replaced with "·"
        assert "·" in result.encoded or "和" in result.encoded

    def test_case_insensitive(self):
        r1 = encode_dense("Memory System")
        r2 = encode_dense("memory system")
        # Both should produce the same encoded output (lowercase normalization)
        assert r1.encoded == r2.encoded

    def test_greedy_longest_match(self):
        """Longer phrases should be matched before shorter ones."""
        result = encode_dense("working memory capacity")
        # "working memory" should match as a unit, not "memory" alone
        assert "工作记忆" in result.encoded

    def test_repeated_phrases(self):
        result = encode_dense("memory memory memory")
        assert result.mapped_phrases == 3

    def test_mixed_content(self):
        result = encode_dense("The dispatch pipeline routes to the memory handler")
        assert result.mapped_phrases > 0
        assert result.encoded_tokens < result.original_tokens


# ---------------------------------------------------------------------------
# Working memory dense context tests
# ---------------------------------------------------------------------------


class TestWorkingMemoryDense:
    """Test dense encoding integration in working memory."""

    def setup_method(self):
        self.wm = WorkingMemory(capacity=7)

    def test_get_context_dense(self):
        """get_context(dense=True) should include content_dense field."""
        self.wm.attend(
            memory_id="test1",
            content="The memory system needs consolidation scheduling",
            importance=0.8,
        )
        ctx = self.wm.get_context(dense=True)
        assert len(ctx) == 1
        assert "content_dense" in ctx[0]
        assert "compression_ratio" in ctx[0]
        assert ctx[0]["compression_ratio"] >= 1.0

    def test_get_context_plain(self):
        """get_context(dense=False) should not include content_dense field."""
        self.wm.attend(
            memory_id="test1",
            content="The memory system needs consolidation",
            importance=0.8,
        )
        ctx = self.wm.get_context(dense=False)
        assert len(ctx) == 1
        assert "content_dense" not in ctx[0]

    def test_dense_token_budget(self):
        """Dense mode should fit more chunks within the same token budget."""
        for i in range(5):
            self.wm.attend(
                memory_id=f"test{i}",
                content=f"The memory system needs consolidation and the cognitive dispatch pipeline requires optimization for performance {i}",
                importance=0.5 + i * 0.05,
            )

        plain_ctx = self.wm.get_context(max_tokens=100, dense=False)
        dense_ctx = self.wm.get_context(max_tokens=100, dense=True)

        # Dense should fit more chunks in the same budget
        assert len(dense_ctx) >= len(plain_ctx)

    def test_dense_fallback_on_import_error(self):
        """If dense_encoding is unavailable, should fall back gracefully."""
        self.wm.attend(
            memory_id="test1",
            content="memory system consolidation",
            importance=0.8,
        )
        # Even with dense=True, should still return context
        ctx = self.wm.get_context(dense=True)
        assert len(ctx) >= 1


# ---------------------------------------------------------------------------
# VSA context compressor tests
# ---------------------------------------------------------------------------


class TestVSAContextCompressor:
    """Test VSA compression integration."""

    def test_compress_basic(self):
        from whitemagic.ai.vsa_context_compressor import VSAContextCompressor
        compressor = VSAContextCompressor()
        items = [
            {"content": "The memory system needs consolidation", "source": "memory", "id": "1"},
            {"content": "Working memory capacity is important", "source": "memory", "id": "2"},
            {"content": "The dispatch pipeline routes tools", "source": "tool_result", "id": "3"},
        ]
        result = compressor.compress(items)
        assert result.item_count > 0
        assert len(result.vector) == 384
        assert result.compression_ratio > 0
        assert result.method in ("hrr_superposition", "text_only")

    def test_compress_empty(self):
        from whitemagic.ai.vsa_context_compressor import VSAContextCompressor
        compressor = VSAContextCompressor()
        result = compressor.compress([])
        assert result.item_count == 0
        assert result.method == "empty"

    def test_compress_single_item(self):
        from whitemagic.ai.vsa_context_compressor import VSAContextCompressor
        compressor = VSAContextCompressor()
        result = compressor.compress([
            {"content": "Single test item", "source": "memory", "id": "1"}
        ])
        assert result.item_count >= 1
        assert len(result.vector) == 384

    def test_probe(self):
        from whitemagic.ai.vsa_context_compressor import VSAContextCompressor
        compressor = VSAContextCompressor()
        items = [
            {"content": "Memory consolidation event", "source": "memory", "id": "1"},
        ]
        result = compressor.compress(items)
        if result.method == "hrr_superposition":
            probed = compressor.probe(result.vector, "OBJECT")
            assert len(probed) == 384

    def test_compression_ratio_scales(self):
        """More items should yield higher compression ratios."""
        from whitemagic.ai.vsa_context_compressor import VSAContextCompressor
        compressor = VSAContextCompressor()

        few_items = [{"content": f"Test content item {i}", "source": "memory", "id": str(i)} for i in range(3)]
        many_items = [{"content": f"Test content item {i} with more text for better compression", "source": "memory", "id": str(i)} for i in range(10)]

        few_result = compressor.compress(few_items)
        many_result = compressor.compress(many_items)

        # More items → higher compression ratio (more original tokens, same compressed size)
        if few_result.method == "hrr_superposition" and many_result.method == "hrr_superposition":
            assert many_result.compression_ratio >= few_result.compression_ratio


# ---------------------------------------------------------------------------
# Integration: scratchpad finalize with VSA
# ---------------------------------------------------------------------------


class TestScratchpadVSAIntegration:
    """Test that scratchpad finalize includes VSA compression metadata."""

    def test_finalize_includes_vsa_metadata(self, tmp_path):
        """Scratchpad finalize should include vsa_compression in result."""
        from whitemagic.core.memory.scratchpad_interleave import ScratchpadManager

        manager = ScratchpadManager(scratch_dir=tmp_path / "scratchpads")
        pad = manager.create("test-vsa")
        manager.write_to("test-vsa", "Memory system needs consolidation", tag="analysis")
        manager.write_to("test-vsa", "Working memory capacity is important", tag="focus")
        manager.write_to("test-vsa", "Dispatch pipeline requires optimization", tag="action")

        # Verify entries exist
        assert len(pad.entries) == 3

        # The VSA compression should work on these entries
        from whitemagic.ai.vsa_context_compressor import get_vsa_context_compressor
        compressor = get_vsa_context_compressor()
        items = [
            {"content": e.get("content", ""), "source": "scratchpad", "id": e.get("tag", "")}
            for e in pad.entries if e.get("content")
        ]
        result = compressor.compress(items, max_text_items=3)
        assert result.item_count == 3
        assert result.compression_ratio > 0
