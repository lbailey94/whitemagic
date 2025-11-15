"""
Configuration schemas for WhiteMagic.

Defines Pydantic models for all configuration sections.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class EmbeddingsConfig(BaseModel):
    """Embedding provider configuration."""
    
    provider: Literal["local", "openai"] = Field(
        default="local",
        description="Embedding provider: 'local' (sentence-transformers) or 'openai'"
    )
    model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Model name for embeddings"
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable embedding cache"
    )
    cache_path: str = Field(
        default="~/.whitemagic/embeddings_cache",
        description="Path to embedding cache directory"
    )


class SearchConfig(BaseModel):
    """Search behavior configuration."""
    
    default_mode: Literal["keyword", "semantic", "hybrid"] = Field(
        default="hybrid",
        description="Default search mode"
    )
    semantic_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic results"
    )
    keyword_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for keyword results in hybrid mode"
    )
    semantic_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for semantic results in hybrid mode"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        description="Maximum number of search results"
    )


class TerminalConfig(BaseModel):
    """Terminal tool configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Enable terminal tool (exec command)"
    )
    default_profile: Literal["PROD", "AGENT"] = Field(
        default="PROD",
        description="Default allowlist profile: 'PROD' (read-only) or 'AGENT' (read+write)"
    )
    audit_enabled: bool = Field(
        default=True,
        description="Enable audit logging for command executions"
    )
    audit_path: str = Field(
        default="~/.whitemagic/.whitemagic_audit",
        description="Path to audit log directory"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Default command timeout in seconds"
    )


class APIConfig(BaseModel):
    """API server configuration."""
    
    host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="API server port"
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload (development only)"
    )
    workers: int = Field(
        default=1,
        ge=1,
        description="Number of worker processes"
    )


class WhiteMagicConfig(BaseModel):
    """Complete WhiteMagic configuration.
    
    This is the root configuration object that contains all settings
    for WhiteMagic components.
    """
    
    memory_path: str = Field(
        default="~/.whitemagic/memory",
        description="Path to memory storage directory"
    )
    embeddings: EmbeddingsConfig = Field(
        default_factory=EmbeddingsConfig,
        description="Embedding configuration"
    )
    search: SearchConfig = Field(
        default_factory=SearchConfig,
        description="Search configuration"
    )
    terminal: TerminalConfig = Field(
        default_factory=TerminalConfig,
        description="Terminal tool configuration"
    )
    api: APIConfig = Field(
        default_factory=APIConfig,
        description="API server configuration"
    )
    
    model_config = ConfigDict(validate_assignment=True)
