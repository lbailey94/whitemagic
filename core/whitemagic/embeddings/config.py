"""
Embedding configuration management.

Handles configuration for embedding providers with environment variable support.
"""

import os

from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for embedding providers."""

    provider: str = Field(
        default="local",
        description="Provider name: 'local' (default, privacy-first) or 'openai'",
    )

    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key (required for openai provider)"
    )

    model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Model identifier (local: sentence-transformers model, openai: embedding model)",
    )

    dimensions: int = Field(default=1536, description="Embedding vector dimensions")

    batch_size: int = Field(
        default=100, description="Maximum batch size for bulk operations"
    )

    max_retries: int = Field(
        default=3, description="Maximum number of retries on failure"
    )

    timeout: int = Field(default=30, description="Request timeout in seconds")

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """
        Load configuration from config file, with environment variable overrides.

        Priority (highest to lowest):
            1. Environment variables (WM_EMBEDDING_*)
            2. Config file (~/.whitemagic/config.yaml)
            3. Defaults

        Environment variables:
            - WM_EMBEDDING_PROVIDER: Provider name
            - OPENAI_API_KEY: OpenAI API key (only for openai provider)
            - WM_EMBEDDING_MODEL: Model identifier
            - WM_EMBEDDING_DIMENSIONS: Vector dimensions
            - WM_EMBEDDING_BATCH_SIZE: Batch size
            - WM_EMBEDDING_MAX_RETRIES: Max retries
            - WM_EMBEDDING_TIMEOUT: Timeout in seconds

        Returns:
            EmbeddingConfig instance with values from config file + env overrides
        """
        try:
            from whitemagic.config import get_config_manager

            config_mgr = get_config_manager()
            config = config_mgr.load()

            provider = config.embeddings.provider
            model = config.embeddings.model
            _ = config.embeddings.cache_enabled  # cache setting read but not yet used
        except Exception:  # noqa: BLE001
            # Fallback to defaults if config not available
            provider = "local"
            model = "all-MiniLM-L6-v2"
            pass  # cache_enabled was True

        # Environment variables override config file
        provider = os.getenv("WM_EMBEDDING_PROVIDER", provider)

        # Set default model based on provider if not explicitly set
        if model == "all-MiniLM-L6-v2" and provider != "local":
            model = "text-embedding-3-small"

        model = os.getenv("WM_EMBEDDING_MODEL", model)

        return cls(
            provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=model,
            dimensions=int(os.getenv("WM_EMBEDDING_DIMENSIONS", "1536")),
            batch_size=int(os.getenv("WM_EMBEDDING_BATCH_SIZE", "100")),
            max_retries=int(os.getenv("WM_EMBEDDING_MAX_RETRIES", "3")),
            timeout=int(os.getenv("WM_EMBEDDING_TIMEOUT", "30")),
        )

    def validate_for_provider(self) -> None:
        """
        Validate configuration for the selected provider.

        Raises:
            ValueError: If configuration is invalid for the provider
        """
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OpenAI API key required. Set OPENAI_API_KEY environment variable."
                )
        elif self.provider == "local":
            # Local provider doesn't need API keys
            pass
        else:
            raise ValueError(
                f"Unknown provider: {self.provider}. Use 'openai' or 'local'."
            )
