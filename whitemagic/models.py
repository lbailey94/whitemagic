"""
WhiteMagic data models using Pydantic for validation and serialization.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

from .constants import (
    VALID_MEMORY_TYPES,
    VALID_STATUSES,
    VALID_PLANS,
    STATUS_ACTIVE,
    MEMORY_TYPE_SHORT_TERM,
)


class Memory(BaseModel):
    """Represents a memory entry with all metadata."""

    filename: str = Field(..., description="Unique filename (e.g., 20231101_120000_example.md)")
    title: str = Field(..., description="Human-readable title")
    type: str = Field(..., description="Memory type: short_term or long_term")
    path: str = Field(..., description="Relative path from base_dir")
    created: datetime = Field(..., description="Creation timestamp")
    updated: Optional[datetime] = Field(None, description="Last update timestamp")
    accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    status: str = Field(default=STATUS_ACTIVE, description="Status: active or archived")
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp")
    restored_at: Optional[datetime] = Field(None, description="Restore timestamp")
    promoted_from: Optional[str] = Field(None, description="Filename if promoted from short-term")

    @validator("type")
    def validate_type(cls, v):
        if v not in VALID_MEMORY_TYPES:
            raise ValueError(f"type must be one of: {VALID_MEMORY_TYPES}")
        return v

    @validator("status")
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of: {VALID_STATUSES}")
        return v

    @validator("tags")
    def validate_tags(cls, v):
        if not isinstance(v, list):
            raise ValueError("tags must be a list")
        return [str(tag) for tag in v]  # Ensure all tags are strings

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class MemoryCreate(BaseModel):
    """Input model for creating a new memory."""

    title: str = Field(..., min_length=1, max_length=200, description="Memory title")
    content: str = Field(..., min_length=1, description="Memory content (markdown)")
    type: str = Field(default=MEMORY_TYPE_SHORT_TERM, description="Memory type")
    tags: List[str] = Field(default_factory=list, description="List of tags")

    @validator("type")
    def validate_type(cls, v):
        if v not in VALID_MEMORY_TYPES:
            raise ValueError(f"type must be one of: {VALID_MEMORY_TYPES}")
        return v

    @validator("tags")
    def validate_tags(cls, v):
        if len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        return [tag.strip() for tag in v if tag.strip()]


class MemoryUpdate(BaseModel):
    """Input model for updating an existing memory."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = Field(None, description="Replace all tags")
    add_tags: Optional[List[str]] = Field(None, description="Add these tags")
    remove_tags: Optional[List[str]] = Field(None, description="Remove these tags")

    @validator("tags", "add_tags", "remove_tags")
    def validate_tag_lists(cls, v):
        if v is not None:
            return [tag.strip() for tag in v if tag.strip()]
        return v


class MemorySearchQuery(BaseModel):
    """Input model for searching memories."""

    query: str = Field(..., min_length=1, description="Search query")
    type: Optional[str] = Field(None, description="Filter by memory type")
    tags: List[str] = Field(default_factory=list, description="Filter by tags (AND)")
    limit: int = Field(default=20, ge=1, le=100, description="Max results to return")
    include_archived: bool = Field(default=False, description="Include archived memories")

    @validator("type")
    def validate_type(cls, v):
        if v is not None and v not in VALID_MEMORY_TYPES:
            raise ValueError(f"type must be one of: {VALID_MEMORY_TYPES}")
        return v


class MemorySearchResult(BaseModel):
    """Output model for search results."""

    items: List[Memory] = Field(..., description="Matching memories")
    total: int = Field(..., description="Total number of matches")
    query: str = Field(..., description="Original query")


class ContextRequest(BaseModel):
    """Input model for generating context."""

    tier: int = Field(..., ge=0, le=2, description="Context tier: 0, 1, or 2")


class ContextResponse(BaseModel):
    """Output model for generated context."""

    prompt: str = Field(..., description="Tier-appropriate prompt")
    context_chunks: List[Dict[str, Any]] = Field(..., description="Memory snippets")
    token_estimate: int = Field(..., description="Estimated tokens")


class ConsolidateRequest(BaseModel):
    """Input model for consolidation."""

    dry_run: bool = Field(default=True, description="If true, don't actually consolidate")
    retention_days: Optional[int] = Field(None, ge=1, description="Override retention days")
    auto_promote_tags: Optional[List[str]] = Field(None, description="Tags to auto-promote")


class ConsolidateResponse(BaseModel):
    """Output model for consolidation results."""

    archived: int = Field(..., description="Number of memories archived")
    auto_promoted: int = Field(..., description="Number of memories auto-promoted")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    promoted_files: List[str] = Field(default_factory=list, description="Promoted filenames")
    archived_files: List[str] = Field(default_factory=list, description="Archived filenames")


class StatsResponse(BaseModel):
    """Output model for system statistics."""

    short_term_count: int = Field(..., description="Number of short-term memories")
    long_term_count: int = Field(..., description="Number of long-term memories")
    archived_count: int = Field(..., description="Number of archived memories")
    total_memories: int = Field(..., description="Total memories")
    total_tags: int = Field(..., description="Number of unique tags")
    storage_bytes: Optional[int] = Field(None, description="Total storage used")
    last_consolidation_at: Optional[datetime] = Field(None, description="Last consolidation")


class TagInfo(BaseModel):
    """Information about a single tag."""

    tag: str = Field(..., description="Tag name")
    count: int = Field(..., description="Number of memories with this tag")
    used_in: List[str] = Field(..., description="Memory types using this tag")


class TagsResponse(BaseModel):
    """Output model for tag statistics."""

    tags: List[TagInfo] = Field(..., description="List of tags with stats")
    total_unique_tags: int = Field(..., description="Number of unique tags")
    total_tag_usages: int = Field(..., description="Sum of all tag usages")
    total_memories_with_tags: int = Field(
        ..., description="Number of memories with at least one tag"
    )


# API Key models (for Phase 2A)


class APIKey(BaseModel):
    """Represents an API key."""

    id: str = Field(..., description="Unique key ID")
    key: str = Field(..., description="The actual API key")
    user_id: str = Field(..., description="Owner user ID")
    label: Optional[str] = Field(None, description="User-provided label")
    plan: str = Field(..., description="Plan: free, pro, team, enterprise")
    rate_limit: int = Field(..., description="Requests per minute")
    quota: Optional[int] = Field(None, description="Memory limit (None = unlimited)")
    status: str = Field(..., description="Status: active, grace, revoked")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")

    @validator("plan")
    def validate_plan(cls, v):
        if v not in VALID_PLANS:
            raise ValueError(f"plan must be one of: {VALID_PLANS}")
        return v


class APIKeyCreate(BaseModel):
    """Input model for creating an API key."""

    label: Optional[str] = Field(None, max_length=100, description="Key label")
    plan: str = Field(..., description="Plan level")

    @validator("plan")
    def validate_plan(cls, v):
        if v not in VALID_PLANS:
            raise ValueError(f"plan must be one of: {VALID_PLANS}")
        return v


class RestoreRequest(BaseModel):
    """Input model for restoring an archived memory."""

    memory_type: str = Field(default=MEMORY_TYPE_SHORT_TERM, description="Target memory type")

    @validator("memory_type")
    def validate_type(cls, v):
        if v not in VALID_MEMORY_TYPES:
            raise ValueError(f"memory_type must be one of: {VALID_MEMORY_TYPES}")
        return v


class NormalizeTagsRequest(BaseModel):
    """Input model for normalizing legacy tags."""

    dry_run: bool = Field(default=True, description="If true, only show what would change")


class NormalizeTagsResponse(BaseModel):
    """Output model for tag normalization results."""

    dry_run: bool = Field(..., description="Whether this was a dry run")
    affected_memories: int = Field(..., description="Number of memories affected")
    changes: List[Dict[str, Any]] = Field(..., description="List of changes")


# Success/Error response models


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(default=True, description="Operation succeeded")
    message: Optional[str] = Field(None, description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class ErrorResponse(BaseModel):
    """Generic error response."""

    success: bool = Field(default=False, description="Operation failed")
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Error type/code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
