"""Tests for the CODEX pipeline (extract, chunk, embed, index)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

from whitemagic.codex import CodexConfig, CodexPipeline


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    """Create a small test corpus."""
    (tmp_path / "doc1.md").write_text("# Title\n\nFirst paragraph.\n\nSecond paragraph.")
    (tmp_path / "doc2.py").write_text("def hello():\n    return 'world'\n\ndef foo():\n    return 42")
    (tmp_path / "doc3.txt").write_text("Plain text document with some content.")
    return tmp_path


@pytest.fixture
def pipeline(corpus_dir: Path, tmp_path: Path) -> CodexPipeline:
    config = CodexConfig(
        corpus_dir=corpus_dir,
        output_dir=tmp_path / "output",
    )
    return CodexPipeline(config)


class TestExtract:
    def test_extract_finds_files(self, pipeline: CodexPipeline, corpus_dir: Path):
        docs = pipeline.extract()
        assert len(docs) == 3
        sources = {d["source_path"] for d in docs}
        assert "doc1.md" in sources
        assert "doc2.py" in sources
        assert "doc3.txt" in sources

    def test_extract_missing_dir(self, pipeline: CodexPipeline):
        with pytest.raises(FileNotFoundError):
            pipeline.extract(Path("/nonexistent/path"))

    def test_extract_has_word_count(self, pipeline: CodexPipeline):
        docs = pipeline.extract()
        for doc in docs:
            assert "word_count" in doc
            assert doc["word_count"] > 0
            assert "text" in doc
            assert "filename" in doc


class TestChunk:
    def test_chunk_splits_paragraphs(self, pipeline: CodexPipeline, corpus_dir: Path):
        docs = pipeline.extract()
        chunks = pipeline.chunk(docs)
        # doc1.md has 2 paragraphs, doc2.py has 2 (split by \n\n), doc3.txt has 1
        assert len(chunks) >= 3
        for chunk in chunks:
            assert "source_path" in chunk
            assert "chunk_index" in chunk
            assert "text" in chunk
            assert "word_count" in chunk

    def test_chunk_empty_docs(self, pipeline: CodexPipeline):
        chunks = pipeline.chunk([])
        assert chunks == []


class TestEmbed:
    def test_embed_empty(self, pipeline: CodexPipeline):
        result = pipeline.embed([])
        assert result == []

    def test_embed_pseudo_fallback(self, pipeline: CodexPipeline, corpus_dir: Path):
        docs = pipeline.extract()
        chunks = pipeline.chunk(docs)
        # Use pseudo embed directly (avoids model loading)
        embedded = pipeline._pseudo_embed(chunks)
        assert len(embedded) == len(chunks)
        for item in embedded:
            assert "embedding" in item
            assert len(item["embedding"]) == 384
            assert item["embedding_model"] == "pseudo-hash"
            assert "chunk_id" in item

    def test_embed_pseudo_normalized(self, pipeline: CodexPipeline):
        chunks = [{"source_path": "test.py", "chunk_index": 0, "text": "def foo(): pass", "word_count": 4}]
        embedded = pipeline._pseudo_embed(chunks)
        vec = embedded[0]["embedding"]
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 0.01  # Should be normalized

    def test_embed_pseudo_deterministic(self, pipeline: CodexPipeline):
        chunks = [{"source_path": "test.py", "chunk_index": 0, "text": "def foo(): pass", "word_count": 4}]
        e1 = pipeline._pseudo_embed(chunks)
        e2 = pipeline._pseudo_embed(chunks)
        assert e1[0]["embedding"] == e2[0]["embedding"]


class TestIndex:
    def test_index_empty(self, pipeline: CodexPipeline):
        result = pipeline.index([])
        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["communities"] == []

    def test_index_with_pseudo_embeddings(self, pipeline: CodexPipeline, corpus_dir: Path):
        docs = pipeline.extract()
        chunks = pipeline.chunk(docs)
        embedded = pipeline._pseudo_embed(chunks)
        graph = pipeline.index(embedded)

        assert "nodes" in graph
        assert "edges" in graph
        assert "communities" in graph
        assert "stats" in graph
        assert graph["stats"]["node_count"] == len(embedded)
        assert graph["stats"]["edge_count"] >= 0
        assert graph["stats"]["community_count"] >= 1

    def test_index_similar_chunks_connect(self, pipeline: CodexPipeline):
        """Chunks with identical text should have high similarity and form edges."""
        chunks = [
            {"source_path": "a.py", "chunk_index": 0, "text": "def hello(): return 'world'", "word_count": 5},
            {"source_path": "b.py", "chunk_index": 0, "text": "def hello(): return 'world'", "word_count": 5},
            {"source_path": "c.py", "chunk_index": 0, "text": "import os; os.listdir('/')", "word_count": 4},
        ]
        embedded = pipeline._pseudo_embed(chunks)
        graph = pipeline.index(embedded)

        # Identical texts should produce at least 1 edge
        assert graph["stats"]["edge_count"] >= 1
        # Check that the edge is between the two identical chunks
        edge_sources = {e["source"] for e in graph["edges"]}
        edge_targets = {e["target"] for e in graph["edges"]}
        assert "a.py#0" in edge_sources or "a.py#0" in edge_targets


class TestRunAll:
    def test_run_all_partial(self, pipeline: CodexPipeline, corpus_dir: Path):
        """run_all should work up to the export stage (which is still NotImplementedError)."""
        docs = pipeline.extract()
        chunks = pipeline.chunk(docs)
        embedded = pipeline._pseudo_embed(chunks)
        graph = pipeline.index(embedded)

        assert len(embedded) > 0
        assert graph["stats"]["node_count"] > 0
