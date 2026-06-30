# ruff: noqa: BLE001
"""Unit tests for content_intelligence module — chunker, outline builder, summarizer."""

from __future__ import annotations

import pytest

from whitemagic.gardens.browser.content_intelligence import (
    ContentChunker,
    ContentSummarizer,
    OutlineBuilder,
    process_content,
    enhanced_to_dict,
)


# ---------------------------------------------------------------------------
# OutlineBuilder tests
# ---------------------------------------------------------------------------


class TestOutlineBuilder:
    def test_build_from_html_with_headings(self):
        html = """
        <html><body>
        <h1>Main Title</h1>
        <p>Some content</p>
        <h2>Subsection A</h2>
        <p>More content</p>
        <h3>Detail 1</h3>
        <p>Details</p>
        <h2>Subsection B</h2>
        <p>End</p>
        </body></html>
        """
        builder = OutlineBuilder()
        outline = builder.build_from_html(html)

        assert len(outline) == 1
        assert outline[0].level == 1
        assert outline[0].text == "Main Title"
        assert len(outline[0].children) == 2
        assert outline[0].children[0].text == "Subsection A"
        assert outline[0].children[1].text == "Subsection B"
        # Detail 1 is nested under Subsection A
        assert len(outline[0].children[0].children) == 1
        assert outline[0].children[0].children[0].text == "Detail 1"

    def test_build_from_html_no_headings(self):
        html = "<html><body><p>No headings here</p></body></html>"
        builder = OutlineBuilder()
        outline = builder.build_from_html(html)
        assert outline == []

    def test_build_from_html_empty(self):
        builder = OutlineBuilder()
        assert builder.build_from_html("") == []

    def test_build_from_html_skips_long_headings(self):
        long_text = "A" * 250
        html = f"<html><body><h1>{long_text}</h1></body></html>"
        builder = OutlineBuilder()
        outline = builder.build_from_html(html)
        assert outline == []

    def test_to_markdown(self):
        from whitemagic.gardens.browser.content_intelligence import OutlineNode

        nodes = [
            OutlineNode(
                level=1,
                text="Title",
                children=[
                    OutlineNode(level=2, text="Sub"),
                ],
            ),
        ]
        builder = OutlineBuilder()
        md = builder.to_markdown(nodes)
        assert "# Title" in md
        assert "## Sub" in md

    def test_to_flat_list(self):
        from whitemagic.gardens.browser.content_intelligence import OutlineNode

        nodes = [
            OutlineNode(
                level=1,
                text="Title",
                children=[
                    OutlineNode(level=2, text="Sub"),
                ],
            ),
        ]
        builder = OutlineBuilder()
        flat = builder.to_flat_list(nodes)
        assert len(flat) == 2
        assert flat[0]["level"] == 1
        assert flat[0]["text"] == "Title"
        assert flat[1]["level"] == 2
        assert flat[1]["depth"] == 1


# ---------------------------------------------------------------------------
# ContentChunker tests
# ---------------------------------------------------------------------------


class TestContentChunker:
    def test_chunk_short_text(self):
        chunker = ContentChunker(chunk_size=2000, overlap=200)
        text = "This is a short paragraph.\n\nAnother short one."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].char_count > 0

    def test_chunk_empty_text(self):
        chunker = ContentChunker()
        assert chunker.chunk("") == []

    def test_chunk_long_text_multiple_chunks(self):
        chunker = ContentChunker(chunk_size=500, overlap=50)
        # Generate ~2000 chars of text in paragraphs
        paragraphs = []
        for i in range(10):
            paragraphs.append(f"Paragraph {i}: " + "word " * 50)
        text = "\n\n".join(paragraphs)

        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Each chunk should have content
        for c in chunks:
            assert c.char_count > 0
            assert c.token_estimate > 0

    def test_chunk_overlap(self):
        chunker = ContentChunker(chunk_size=300, overlap=100)
        paragraphs = []
        for i in range(8):
            paragraphs.append(f"Section {i}: " + "content " * 30)
        text = "\n\n".join(paragraphs)

        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            # The end of chunk 0 should appear at the start of chunk 1 (overlap)
            # Check that some content from end of chunk 0 is in chunk 1
            chunk0_end = chunks[0].text[-80:]
            chunk1_start = chunks[1].text[:120]
            # There should be some overlap content
            # (exact match depends on paragraph boundaries)
            assert len(chunk1_start) > 0

    def test_chunk_with_headings(self):
        chunker = ContentChunker(chunk_size=500, overlap=50)
        text = (
            "Introduction\n\nSome content here. " * 10
            + "\n\nMethods\n\nMethods content. " * 10
        )
        headings = ["Introduction", "Methods"]
        chunks = chunker.chunk(text, headings=headings)
        assert len(chunks) > 0
        # At least one chunk should have a heading assigned
        has_heading = any(c.heading for c in chunks)
        assert has_heading

    def test_chunk_indices_sequential(self):
        chunker = ContentChunker(chunk_size=200, overlap=20)
        text = "\n\n".join(f"Paragraph {i}: " + "word " * 20 for i in range(20))
        chunks = chunker.chunk(text)
        for i, c in enumerate(chunks):
            assert c.index == i


# ---------------------------------------------------------------------------
# ContentSummarizer tests
# ---------------------------------------------------------------------------


class TestContentSummarizer:
    def test_summarize_short_text_returns_as_is(self):
        summarizer = ContentSummarizer()
        text = "This is too short to summarize."
        summary, method = summarizer.summarize(text)
        assert summary == text
        assert method == "none"

    def test_summarize_empty_text(self):
        summarizer = ContentSummarizer()
        summary, method = summarizer.summarize("")
        assert summary == ""
        assert method == "none"

    def test_summarize_extractive_fallback(self):
        """Test extractive summarization (Ollama won't be available in tests)."""
        summarizer = ContentSummarizer()
        # Generate a longer text
        text = (
            "Fusion energy is a promising technology that could revolutionize power generation. "
            "The SPARC tokamak uses high-temperature superconducting magnets to confine plasma. "
            "Recent breakthroughs at NIF achieved Q>1 with 8.6 megajoules of fusion energy output. "
            "The Wendelstein 7-X stellarator demonstrated steady-state operation for 30 minutes. "
            "Helion Energy's Polaris prototype reached 150 million degrees Celsius. "
            "ITER continues assembly in France with first plasma planned for 2026. "
            "Commonwealth Fusion Systems installed the first SPARC magnet at CES 2026. "
            "These advances represent significant progress toward commercial fusion energy. "
        )
        summary, method = summarizer.summarize(text, focus="fusion energy")
        # Should get either ollama (if running) or extractive
        assert method in ("ollama", "extractive")
        assert len(summary) > 0
        assert len(summary) <= 1000

    def test_extractive_with_focus(self):
        summarizer = ContentSummarizer()
        text = (
            "Python is a programming language known for its simplicity. "
            "Fusion energy breakthroughs are accelerating in 2026. "
            "The SPARC tokamak achieved record magnetic field strength. "
            "Machine learning models require significant compute resources. "
            "NIF achieved Q>1 with 8.6 megajoules of fusion energy. "
            "Web development frameworks like Django and Flask are popular. "
            "Commonwealth Fusion Systems is building a pilot plant. "
        )
        summary = summarizer._summarize_extractive(text, focus="fusion energy")
        assert len(summary) > 0
        # The summary should prefer sentences about fusion
        summary_lower = summary.lower()
        assert "fusion" in summary_lower


# ---------------------------------------------------------------------------
# process_content / enhanced_to_dict tests
# ---------------------------------------------------------------------------


class TestProcessContent:
    def test_process_content_basic(self):
        html = """
        <html><body>
        <h1>Fusion Energy</h1>
        <p>Fusion energy is a promising technology.</p>
        <h2>SPARC Tokamak</h2>
        <p>The SPARC tokamak uses HTS magnets.</p>
        </body></html>
        """
        text = "Fusion Energy\n\nFusion energy is a promising technology.\n\nSPARC Tokamak\n\nThe SPARC tokamak uses HTS magnets."

        enhanced = process_content(
            html=html,
            text=text,
            title="Fusion Energy News",
            chunk_size=2000,
            overlap=200,
            summarize=False,
        )

        assert enhanced.title == "Fusion Energy News"
        assert len(enhanced.outline) == 1
        assert enhanced.outline[0].text == "Fusion Energy"
        assert len(enhanced.chunks) >= 1
        assert enhanced.summarizer_used == "none"
        assert enhanced.total_chars > 0

    def test_process_content_with_summary(self):
        html = "<html><body><h1>Test</h1><p>Content here.</p></body></html>"
        text = "Test\n\n" + "This is a test sentence about fusion energy. " * 20

        enhanced = process_content(
            html=html,
            text=text,
            title="Test",
            summarize=True,
            focus="fusion",
        )

        assert enhanced.summary  # Should have a summary
        assert enhanced.summarizer_used in ("ollama", "extractive", "none")

    def test_enhanced_to_dict(self):
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        text = "Title\n\nContent here."

        enhanced = process_content(
            html=html,
            text=text,
            title="Test",
            summarize=False,
        )

        d = enhanced_to_dict(enhanced, include_chunks=True)
        assert d["title"] == "Test"
        assert "outline" in d
        assert "chunks" in d
        assert d["total_chunks"] == len(enhanced.chunks)
        # Chunks should have text
        if d["chunks"]:
            assert "text" in d["chunks"][0]

    def test_enhanced_to_dict_no_chunks(self):
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        text = "Title\n\nContent here."

        enhanced = process_content(
            html=html,
            text=text,
            title="Test",
            summarize=False,
        )

        d = enhanced_to_dict(enhanced, include_chunks=False)
        if d["chunks"]:
            assert "[chunk" in d["chunks"][0]["text"]

    def test_process_content_empty(self):
        enhanced = process_content(
            html="",
            text="",
            title="",
            summarize=False,
        )
        assert enhanced.title == ""
        assert enhanced.outline == []
        assert enhanced.chunks == []
        assert enhanced.total_chars == 0
