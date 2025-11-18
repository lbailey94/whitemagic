"""WhiteMagic API types."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

MemoryType = Literal["short_term", "long_term"]


class Memory(BaseModel):
    """Represents a memory in WhiteMagic."""

    id: str
    title: str
    content: str
    type: MemoryType
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: Optional[dict] = None


class CreateMemoryRequest(BaseModel):
    """Request to create a new memory."""

    title: str
    content: str
    type: MemoryType
    tags: list[str] = Field(default_factory=list)
    metadata: Optional[dict] = None


class UpdateMemoryRequest(BaseModel):
    """Request to update an existing memory."""

    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


class ListMemoriesParams(BaseModel):
    """Parameters for listing memories."""

    type: Optional[MemoryType] = None
    tags: Optional[list[str]] = None
    skip: int = 0
    limit: int = 20


class SearchMemoriesParams(BaseModel):
    """Parameters for searching memories."""

    query: str
    type: Optional[MemoryType] = None
    tags: Optional[list[str]] = None
    limit: int = 10


class Quota(BaseModel):
    """User quota limits."""

    rpm_limit: int
    daily_limit: int
    max_memories: int


class User(BaseModel):
    """User information."""

    id: str
    email: str
    created_at: datetime
    plan: Optional[str] = None
    quota: Optional[Quota] = None


class UsageStats(BaseModel):
    """User usage statistics."""

    api_calls_today: int
    api_calls_rpm: int
    memory_count: int
    storage_bytes: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: str
