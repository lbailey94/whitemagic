"""
WhiteMagic Embeddings Module.

Provides embedding generation for semantic search and memory understanding.
Supports multiple providers (OpenAI, local models) with a unified interface.

Example usage:
    >>> from whitemagic.embeddings import get_embedding_provider, EmbeddingConfig
    >>> 
    >>> # Create config
    >>> config = EmbeddingConfig(
    ...     provider="openai",
    ...     openai_api_key="sk-...",
    ...     model="text-embedding-3-small"
    ... )
    >>> 
    >>> # Get provider
    >>> provider = get_embedding_provider(config)
    >>> 
    >>> # Generate embeddings
    >>> embedding = await provider.embed("Hello, world!")
    >>> embeddings = await provider.embed_batch(["Text 1", "Text 2"])
"""

from .base import EmbeddingProvider
from .config import EmbeddingConfig
from .openai_provider import OpenAIEmbeddings
from .local_provider import LocalEmbeddings


def get_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """
    Factory function to get an embedding provider.
    
    Args:
        config: Embedding configuration
        
    Returns:
        EmbeddingProvider instance
        
    Raises:
        ValueError: If provider is unknown or configuration is invalid
        NotImplementedError: If local provider is requested (not yet implemented)
        
    Example:
        >>> config = EmbeddingConfig.from_env()
        >>> provider = get_embedding_provider(config)
    """
    # Validate configuration
    config.validate_for_provider()
    
    if config.provider == "openai":
        return OpenAIEmbeddings(
            api_key=config.openai_api_key,
            model=config.model,
            dimensions=config.dimensions,
            max_retries=config.max_retries,
            timeout=config.timeout
        )
    elif config.provider == "local":
        # Will raise NotImplementedError
        return LocalEmbeddings(model=config.model)
    else:
        raise ValueError(
            f"Unknown provider: {config.provider}. "
            f"Supported providers: openai, local (not yet available)"
        )


__all__ = [
    "EmbeddingProvider",
    "EmbeddingConfig",
    "OpenAIEmbeddings",
    "LocalEmbeddings",
    "EmbeddingCache",
    "get_embedding_provider"
]

__version__ = "0.1.0"
