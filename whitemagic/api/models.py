"""
WhiteMagic API - Request/Response Models

Pydantic models for API request validation and response serialization.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Base response models

class ErrorDetail(BaseModel):
    """Error detail for API responses."""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success response."""
    success: bool = True
    message: str


# Memory-related models

class CreateMemoryRequest(BaseModel):
    """Request to create a new memory."""
    title: str = Field(..., min_length=1, max_length=500, description="Memory title")
    content: str = Field(..., min_length=1, description="Memory content (markdown supported)")
    type: str = Field(default="short_term", description="Memory type: short_term or long_term")
    tags: List[str] = Field(default_factory=list, description="List of tags")
    
    @field_validator('type')
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        if v not in ['short_term', 'long_term']:
            raise ValueError("type must be 'short_term' or 'long_term'")
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        # Normalize tags
        return [tag.lower().strip().replace(' ', '_') for tag in v if tag.strip()]


class UpdateMemoryRequest(BaseModel):
    """Request to update an existing memory."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [tag.lower().strip().replace(' ', '_') for tag in v if tag.strip()]


class MemoryResponse(BaseModel):
    """Response containing memory information."""
    success: bool = True
    filename: str
    title: str
    type: str
    tags: List[str]
    created: datetime
    path: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "filename": "20251102_094530_api_design.md",
                "title": "API Design Pattern",
                "type": "long_term",
                "tags": ["api", "pattern", "proven"],
                "created": "2025-11-02T09:45:30",
                "path": "memory/long_term/20251102_094530_api_design.md"
            }
        }


class MemoryListResponse(BaseModel):
    """Response containing list of memories."""
    success: bool = True
    memories: List[MemoryResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total": 2,
                "memories": [
                    {
                        "filename": "20251102_094530_api_design.md",
                        "title": "API Design Pattern",
                        "type": "long_term",
                        "tags": ["api", "pattern"],
                        "created": "2025-11-02T09:45:30",
                        "path": "memory/long_term/20251102_094530_api_design.md"
                    }
                ]
            }
        }


# Search-related models

class SearchRequest(BaseModel):
    """Request to search memories."""
    query: Optional[str] = Field(None, description="Search query string")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (AND logic)")
    type: Optional[str] = Field(None, description="Filter by memory type")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum results to return")
    
    @field_validator('type')
    @classmethod
    def validate_memory_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ['short_term', 'long_term']:
            raise ValueError("type must be 'short_term' or 'long_term'")
        return v


class SearchResultItem(BaseModel):
    """Single search result item."""
    filename: str
    title: str
    type: str
    tags: List[str]
    created: datetime
    preview: str
    score: int


class SearchResponse(BaseModel):
    """Response containing search results."""
    success: bool = True
    results: List[SearchResultItem]
    total: int
    query: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total": 1,
                "query": "API design",
                "results": [
                    {
                        "filename": "20251102_094530_api_design.md",
                        "title": "API Design Pattern",
                        "type": "long_term",
                        "tags": ["api", "pattern"],
                        "created": "2025-11-02T09:45:30",
                        "preview": "When designing REST APIs, always...",
                        "score": 5
                    }
                ]
            }
        }


# Context generation models

class ContextRequest(BaseModel):
    """Request to generate context."""
    tier: int = Field(default=1, ge=0, le=2, description="Context tier: 0 (minimal), 1 (balanced), 2 (full)")


class ContextResponse(BaseModel):
    """Response containing generated context."""
    success: bool = True
    context: str
    tier: int
    memories_included: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tier": 1,
                "memories_included": 5,
                "context": "## Short-Term Memories\n\n- **API Design** (tags: api, pattern)\n..."
            }
        }


# User and API key models

class APIKeyInfo(BaseModel):
    """API key information (without the actual key!)."""
    id: UUID
    name: Optional[str]
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: Optional[str] = Field(None, max_length=100, description="Optional name for the key")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration in days (max 365)")


class CreateAPIKeyResponse(BaseModel):
    """Response containing new API key (SHOW ONCE!)."""
    success: bool = True
    api_key: str = Field(..., description="The actual API key - show this to user ONCE!")
    key_info: APIKeyInfo
    warning: str = "Save this API key now! It won't be shown again."


class ListAPIKeysResponse(BaseModel):
    """Response containing user's API keys."""
    success: bool = True
    api_keys: List[APIKeyInfo]
    total: int


# User information models

class UserInfo(BaseModel):
    """User information."""
    id: UUID
    email: str
    plan_tier: str
    created_at: datetime
    last_seen_at: Optional[datetime]


class UsageStats(BaseModel):
    """User usage statistics."""
    requests_today: int
    requests_this_month: int
    memories_count: int
    storage_bytes: int


class UserResponse(BaseModel):
    """Response containing user information."""
    success: bool = True
    user: UserInfo
    usage: UsageStats


# Statistics models

class StatsResponse(BaseModel):
    """Response containing memory statistics."""
    success: bool = True
    short_term_count: int
    long_term_count: int
    total_count: int
    total_tags: int
    most_used_tags: List[tuple]
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "short_term_count": 5,
                "long_term_count": 12,
                "total_count": 17,
                "total_tags": 8,
                "most_used_tags": [("api", 5), ("pattern", 3)]
            }
        }


class TagsResponse(BaseModel):
    """Response containing all tags."""
    success: bool = True
    tags: List[str]
    total: int


# Consolidation models

class ConsolidateRequest(BaseModel):
    """Request to consolidate memories."""
    dry_run: bool = Field(default=True, description="If true, only show what would be done")
    min_age_days: int = Field(default=30, ge=1, description="Minimum age in days for consolidation")


class ConsolidateResponse(BaseModel):
    """Response from consolidation operation."""
    success: bool = True
    archived_count: int
    promoted_count: int
    dry_run: bool
    message: str
