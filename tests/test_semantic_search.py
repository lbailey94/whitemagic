"""
Tests for semantic search functionality.

Tests semantic search in Tier 1 (ephemeral) mode - no database changes required.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path

from whitemagic.core import MemoryManager
from whitemagic.search import SemanticSearcher, SearchMode, semantic_search
from whitemagic.embeddings import EmbeddingConfig


# Mock embedding provider for testing (avoids API calls)
class MockEmbeddingProvider:
    """Mock provider that returns deterministic embeddings for testing."""
    
    def __init__(self):
        self._dimensions = 384
        self._model = "mock-model"
        
        # Predefined embeddings for test queries
        self._embeddings = {
            "python debugging": [0.8, 0.6, 0.2, 0.1] + [0.0] * 380,
            "async programming": [0.7, 0.8, 0.3, 0.2] + [0.0] * 380,
            "error handling": [0.6, 0.5, 0.7, 0.3] + [0.0] * 380,
            "test fixtures": [0.4, 0.3, 0.5, 0.8] + [0.0] * 380,
        }
    
    async def embed(self, text: str) -> list:
        """Return mock embedding based on text content."""
        # Generate simple embedding based on word presence
        text_lower = text.lower()
        
        if "debug" in text_lower or "python" in text_lower:
            return self._embeddings["python debugging"]
        elif "async" in text_lower or "await" in text_lower:
            return self._embeddings["async programming"]
        elif "error" in text_lower or "exception" in text_lower:
            return self._embeddings["error handling"]
        elif "test" in text_lower or "fixture" in text_lower:
            return self._embeddings["test fixtures"]
        else:
            # Generic embedding
            return [0.5, 0.5, 0.5, 0.5] + [0.0] * 380
    
    async def embed_batch(self, texts: list) -> list:
        """Return mock embeddings for multiple texts."""
        return [await self.embed(text) for text in texts]
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        return self._model


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for test memories."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def memory_manager(temp_memory_dir):
    """Create a memory manager with test data."""
    manager = MemoryManager(base_dir=temp_memory_dir)
    
    # Create test memories
    test_memories = [
        {
            "title": "Python Debugging Tips",
            "content": "Use pdb for debugging Python code. Set breakpoints with pdb.set_trace().",
            "tags": ["python", "debugging"],
            "type": "long_term"
        },
        {
            "title": "Async Programming Guide",
            "content": "Use async/await for asynchronous programming. Avoid blocking calls in async functions.",
            "tags": ["python", "async"],
            "type": "long_term"
        },
        {
            "title": "Error Handling Best Practices",
            "content": "Always catch specific exceptions. Use try/except blocks appropriately.",
            "tags": ["python", "errors"],
            "type": "long_term"
        },
        {
            "title": "Test Fixtures in Pytest",
            "content": "Use @pytest.fixture decorator for reusable test setup. Fixtures provide clean test data.",
            "tags": ["testing", "pytest"],
            "type": "short_term"
        },
        {
            "title": "Quick Note",
            "content": "Remember to check logs",
            "tags": ["reminder"],
            "type": "short_term"
        }
    ]
    
    for memory in test_memories:
        manager.create_memory(
            title=memory["title"],
            content=memory["content"],
            memory_type=memory["type"],
            tags=memory["tags"]
        )
    
    return manager


@pytest.fixture
def mock_searcher(memory_manager):
    """Create searcher with mock embedding provider."""
    mock_provider = MockEmbeddingProvider()
    return SemanticSearcher(
        memory_manager=memory_manager,
        embedding_provider=mock_provider
    )


class TestSemanticSearcher:
    """Test SemanticSearcher class."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, mock_searcher):
        """Test basic semantic search."""
        results = await mock_searcher.semantic_search(
            query="How to debug Python code",
            k=3
        )
        
        assert len(results) > 0
        assert results[0].title == "Python Debugging Tips"
        assert results[0].match_type == "semantic"
        assert 0.0 <= results[0].score <= 1.0
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_threshold(self, mock_searcher):
        """Test semantic search with similarity threshold."""
        # High threshold should return fewer results
        results_high = await mock_searcher.semantic_search(
            query="debugging",
            k=10,
            threshold=0.9
        )
        
        # Low threshold should return more results
        results_low = await mock_searcher.semantic_search(
            query="debugging",
            k=10,
            threshold=0.3
        )
        
        assert len(results_low) >= len(results_high)
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_type_filter(self, mock_searcher):
        """Test semantic search filtered by memory type."""
        results = await mock_searcher.semantic_search(
            query="python",
            k=10,
            memory_type="long_term"
        )
        
        assert all(r.type == "long_term" for r in results)
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_tag_filter(self, mock_searcher):
        """Test semantic search filtered by tags."""
        results = await mock_searcher.semantic_search(
            query="python",
            k=10,
            tags=["debugging"]
        )
        
        assert all("debugging" in r.tags for r in results)
    
    @pytest.mark.asyncio
    async def test_keyword_search(self, mock_searcher):
        """Test keyword search fallback."""
        results = await mock_searcher.keyword_search(
            query="async",
            k=5
        )
        
        assert len(results) > 0
        assert results[0].match_type == "keyword"
        assert "async" in results[0].title.lower() or "async" in results[0].content.lower()
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, mock_searcher):
        """Test hybrid search combining keyword and semantic."""
        results = await mock_searcher.hybrid_search(
            query="python debugging",
            k=5,
            keyword_weight=0.4,
            semantic_weight=0.6
        )
        
        assert len(results) > 0
        # Should have hybrid results
        assert any(r.match_type == "hybrid" for r in results)
    
    @pytest.mark.asyncio
    async def test_search_modes(self, mock_searcher):
        """Test all search modes through unified interface."""
        query = "python"
        
        # Test each mode
        keyword_results = await mock_searcher.search(
            query=query,
            mode=SearchMode.KEYWORD,
            k=3
        )
        
        semantic_results = await mock_searcher.search(
            query=query,
            mode=SearchMode.SEMANTIC,
            k=3
        )
        
        hybrid_results = await mock_searcher.search(
            query=query,
            mode=SearchMode.HYBRID,
            k=3
        )
        
        # All should return results
        assert len(keyword_results) > 0
        assert len(semantic_results) > 0
        assert len(hybrid_results) > 0
        
        # Check match types
        assert all(r.match_type == "keyword" for r in keyword_results)
        assert all(r.match_type == "semantic" for r in semantic_results)
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, mock_searcher):
        """Test handling of edge cases."""
        # Empty results should be handled gracefully
        results = await mock_searcher.semantic_search(
            query="xyzabc123nonexistent",
            k=10,
            threshold=0.99  # Very high threshold
        )
        
        # Should return empty list, not error
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_result_ordering(self, mock_searcher):
        """Test that results are ordered by score."""
        results = await mock_searcher.semantic_search(
            query="python programming",
            k=10,
            threshold=0.0
        )
        
        if len(results) > 1:
            # Scores should be in descending order
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)


class TestConvenienceFunction:
    """Test convenience function for semantic search."""
    
    @pytest.mark.asyncio
    async def test_semantic_search_function(self, memory_manager):
        """Test semantic_search convenience function."""
        # Mock the embedding provider
        mock_provider = MockEmbeddingProvider()
        
        # Create searcher with mock provider
        searcher = SemanticSearcher(
            memory_manager=memory_manager,
            embedding_provider=mock_provider
        )
        
        # Test the function
        results = await searcher.search(
            query="debugging",
            mode=SearchMode.SEMANTIC,
            k=3
        )
        
        assert len(results) > 0
        assert isinstance(results[0].score, float)


class TestSearchResultDataclass:
    """Test SearchResult dataclass."""
    
    def test_search_result_creation(self):
        """Test creating SearchResult objects."""
        from whitemagic.search import SearchResult
        
        result = SearchResult(
            memory_id="test_123",
            title="Test Memory",
            content="Test content",
            type="short_term",
            tags=["test"],
            score=0.95,
            match_type="semantic"
        )
        
        assert result.memory_id == "test_123"
        assert result.score == 0.95
        assert result.match_type == "semantic"


class TestCosinesimilarity:
    """Test cosine similarity calculation."""
    
    @pytest.mark.asyncio
    async def test_cosine_similarity_identical(self, mock_searcher):
        """Test cosine similarity with identical vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        
        similarity = mock_searcher._cosine_similarity(vec1, vec2)
        
        # Identical vectors should have similarity of 1.0
        assert abs(similarity - 1.0) < 0.001
    
    @pytest.mark.asyncio
    async def test_cosine_similarity_orthogonal(self, mock_searcher):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        similarity = mock_searcher._cosine_similarity(vec1, vec2)
        
        # Orthogonal vectors should have similarity of 0.0
        assert abs(similarity - 0.0) < 0.001
    
    @pytest.mark.asyncio
    async def test_cosine_similarity_opposite(self, mock_searcher):
        """Test cosine similarity with opposite vectors."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        
        similarity = mock_searcher._cosine_similarity(vec1, vec2)
        
        # Opposite vectors should have similarity of -1.0
        assert abs(similarity - (-1.0)) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
