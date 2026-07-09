"""Tests for browser ONNX embedding integration."""
import pytest
from pathlib import Path


class TestBrowserEmbedderManager:
    def test_status(self):
        from whitemagic.inference.browser_embedder import get_browser_embedder_manager
        mgr = get_browser_embedder_manager()
        status = mgr.status()
        assert status.model_name == "all-MiniLM-L6-v2"
        assert status.embedding_dim == 384
        assert status.model_size_mb > 0

    def test_get_config(self):
        from whitemagic.inference.browser_embedder import get_browser_embedder_manager
        mgr = get_browser_embedder_manager()
        config = mgr.get_config()
        assert config["model_id"] == "Xenova/all-MiniLM-L6-v2"
        assert config["embedding_dim"] == 384
        assert config["quantized"] is True
        assert "fallback" in config

    def test_model_url(self):
        from whitemagic.inference.browser_embedder import get_browser_embedder_manager
        mgr = get_browser_embedder_manager()
        url = mgr.get_model_url()
        assert ".onnx" in url

    def test_download_instructions(self):
        from whitemagic.inference.browser_embedder import get_browser_embedder_manager
        mgr = get_browser_embedder_manager()
        instructions = mgr.download_instructions()
        assert "huggingface" in instructions.lower()
        assert "onnx" in instructions.lower()

    def test_is_model_available_false(self, tmp_path):
        from whitemagic.inference.browser_embedder import BrowserEmbedderManager
        mgr = BrowserEmbedderManager(models_dir=tmp_path)
        assert mgr.is_model_available() is False

    def test_is_model_available_true(self, tmp_path):
        from whitemagic.inference.browser_embedder import BrowserEmbedderManager
        mgr = BrowserEmbedderManager(models_dir=tmp_path)
        # Create a dummy model file
        (tmp_path / "all-MiniLM-L6-v2-quantized.onnx").write_bytes(b"dummy")
        assert mgr.is_model_available() is True
        status = mgr.status()
        assert status.available is True
        assert status.fallback_active is False


class TestBrowserEmbedderTypeScript:
    """Verify the TypeScript BrowserEmbedder module exists and is exported."""

    def test_module_exists(self):
        ts_path = Path(__file__).resolve().parents[3] / "sdk" / "typescript" / "src" / "browser_embedder.ts"
        assert ts_path.exists(), f"BrowserEmbedder TypeScript module not found at {ts_path}"

    def test_module_exported_from_index(self):
        index_path = Path(__file__).resolve().parents[3] / "sdk" / "typescript" / "src" / "index.ts"
        content = index_path.read_text()
        assert "BrowserEmbedder" in content

    def test_module_has_required_methods(self):
        ts_path = Path(__file__).resolve().parents[3] / "sdk" / "typescript" / "src" / "browser_embedder.ts"
        content = ts_path.read_text()
        assert "class BrowserEmbedder" in content
        assert "async embed" in content
        assert "async embedBatch" in content
        assert "cosineSimilarity" in content
        assert "topKSimilar" in content
        assert "hashEmbed" in content or "_hashEmbed" in content
