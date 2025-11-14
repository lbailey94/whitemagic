"""
Embedding configuration management.

Handles configuration for embedding providers with environment variable support.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class EmbeddingConfig(BaseModel):
    """Configuration for embedding providers."""
    
    provider: str = Field(
        default="openai",
        description="Provider name: 'openai' or 'local'"
    )
    
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (required for openai provider)"
    )
    
    model: str = Field(
        default="text-embedding-3-small",
        description="Model identifier"
    )
    
    dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions"
    )
    
    batch_size: int = Field(
        default=100,
        description="Maximum batch size for bulk operations"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries on failure"
    )
    
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    
    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """
        Load configuration from environment variables.
        
        Environment variables:
            - WM_EMBEDDING_PROVIDER: Provider name (default: openai)
            - OPENAI_API_KEY: OpenAI API key
            - WM_EMBEDDING_MODEL: Model identifier
            - WM_EMBEDDING_DIMENSIONS: Vector dimensions
            - WM_EMBEDDING_BATCH_SIZE: Batch size
            - WM_EMBEDDING_MAX_RETRIES: Max retries
            - WM_EMBEDDING_TIMEOUT: Timeout in seconds
            
        Returns:
            EmbeddingConfig instance with values from environment
        """
        return cls(
            provider=os.getenv("WM_EMBEDDING_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("WM_EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=int(os.getenv("WM_EMBEDDING_DIMENSIONS", "1536")),
            batch_size=int(os.getenv("WM_EMBEDDING_BATCH_SIZE", "100")),
            max_retries=int(os.getenv("WM_EMBEDDING_MAX_RETRIES", "3")),
            timeout=int(os.getenv("WM_EMBEDDING_TIMEOUT", "30"))
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
