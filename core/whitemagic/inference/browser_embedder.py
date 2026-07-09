"""Browser ONNX embedding integration — coordinates Python ↔ browser embeddings.

Provides server-side metadata and model management for the browser-side
ONNX embedding engine (implemented in TypeScript as BrowserEmbedder).
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_ID = "Xenova/all-MiniLM-L6-v2"
QUANTIZED_MODEL_SIZE_MB = 23  # approximate


@dataclass
class BrowserEmbedderStatus:
    available: bool
    model_name: str
    model_id: str
    embedding_dim: int
    model_size_mb: int
    cache_enabled: bool
    fallback_active: bool


class BrowserEmbedderManager:
    """Manage browser-side ONNX embedding model distribution and status."""

    def __init__(self, models_dir: Path | None = None) -> None:
        self._models_dir = models_dir or Path("public/models")
        self._model_path = self._models_dir / "all-MiniLM-L6-v2-quantized.onnx"
        self._tokenizer_path = self._models_dir / "tokenizer.json"

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def tokenizer_path(self) -> Path:
        return self._tokenizer_path

    def is_model_available(self) -> bool:
        """Check if the ONNX model is available locally."""
        return self._model_path.exists()

    def status(self) -> BrowserEmbedderStatus:
        return BrowserEmbedderStatus(
            available=self.is_model_available(),
            model_name=MODEL_NAME,
            model_id=MODEL_ID,
            embedding_dim=EMBEDDING_DIM,
            model_size_mb=QUANTIZED_MODEL_SIZE_MB,
            cache_enabled=True,
            fallback_active=not self.is_model_available(),
        )

    def get_model_url(self) -> str:
        """Get the URL for serving the model to the browser."""
        return f"/models/{self._model_path.name}"

    def get_config(self) -> dict[str, Any]:
        """Get configuration for the browser embedder."""
        return {
            "model_id": MODEL_ID,
            "model_url": self.get_model_url(),
            "embedding_dim": EMBEDDING_DIM,
            "quantized": True,
            "fallback": "hash",
            "cache_strategy": "cache-first",
            "instructions": (
                "If model not available, BrowserEmbedder falls back to "
                "hash-based embeddings (deterministic but not semantic). "
                "Download the quantized model from HuggingFace and place "
                f"at {self._model_path}"
            ),
        }

    def download_instructions(self) -> str:
        """Return instructions for downloading the model."""
        return (
            f"To enable browser-side ONNX embeddings:\n"
            f"1. Download quantized model from: https://huggingface.co/{MODEL_ID}\n"
            f"2. Place ONNX file at: {self._model_path}\n"
            f"3. Place tokenizer at: {self._tokenizer_path}\n"
            f"4. The browser will load it via onnxruntime-web or @xenova/transformers\n"
            f"5. Model size: ~{QUANTIZED_MODEL_SIZE_MB}MB (cached by browser)\n"
            f"6. Fallback: hash-based embeddings work without the model"
        )


_manager: BrowserEmbedderManager | None = None


def get_browser_embedder_manager() -> BrowserEmbedderManager:
    global _manager
    if _manager is None:
        _manager = BrowserEmbedderManager()
    return _manager
