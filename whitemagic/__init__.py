"""
WhiteMagic - Tiered Prompt & External Memory System for AI Agents

A production-ready memory management system featuring:
- Tiered memory storage (short-term, long-term, archive)
- Automatic consolidation and promotion
- Tag-based organization and search
- Context generation for AI prompts
- Full CRUD operations with validation

Example:
    >>> from whitemagic import MemoryManager
    >>> manager = MemoryManager()
    >>> manager.create_memory(
    ...     title="Important Note",
    ...     content="This is content",
    ...     memory_type="long_term",
    ...     tags=["important", "project"]
    ... )
"""

__version__ = "2.1.0"
__author__ = "WhiteMagic Team"

# Core exports
from .core import MemoryManager

# Model exports
from .models import (
    Memory,
    MemoryCreate,
    MemoryUpdate,
    MemorySearchQuery,
    MemorySearchResult,
    ContextRequest,
    ContextResponse,
    ConsolidateRequest,
    ConsolidateResponse,
    StatsResponse,
    TagInfo,
    TagsResponse,
    RestoreRequest,
    NormalizeTagsRequest,
    NormalizeTagsResponse,
    SuccessResponse,
    ErrorResponse,
)

# Exception exports
from .exceptions import (
    WhiteMagicError,
    MemoryNotFoundError,
    MemoryAlreadyExistsError,
    InvalidMemoryTypeError,
    InvalidSortOptionError,
    InvalidTierError,
    MemoryAlreadyArchivedError,
    MemoryNotArchivedError,
    FileOperationError,
    MetadataCorruptedError,
    ValidationError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    QuotaExceededError,
    InvalidAPIKeyError,
    APIKeyExpiredError,
)

# Constants exports (commonly used)
from .constants import (
    MEMORY_TYPE_SHORT_TERM,
    MEMORY_TYPE_LONG_TERM,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
    SORT_BY_CREATED,
    SORT_BY_UPDATED,
    SORT_BY_ACCESSED,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "MemoryManager",
    # Models
    "Memory",
    "MemoryCreate",
    "MemoryUpdate",
    "MemorySearchQuery",
    "MemorySearchResult",
    "ContextRequest",
    "ContextResponse",
    "ConsolidateRequest",
    "ConsolidateResponse",
    "StatsResponse",
    "TagInfo",
    "TagsResponse",
    "RestoreRequest",
    "NormalizeTagsRequest",
    "NormalizeTagsResponse",
    "SuccessResponse",
    "ErrorResponse",
    # Exceptions
    "WhiteMagicError",
    "MemoryNotFoundError",
    "MemoryAlreadyExistsError",
    "InvalidMemoryTypeError",
    "InvalidSortOptionError",
    "InvalidTierError",
    "MemoryAlreadyArchivedError",
    "MemoryNotArchivedError",
    "FileOperationError",
    "MetadataCorruptedError",
    "ValidationError",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitExceededError",
    "QuotaExceededError",
    "InvalidAPIKeyError",
    "APIKeyExpiredError",
    # Constants
    "MEMORY_TYPE_SHORT_TERM",
    "MEMORY_TYPE_LONG_TERM",
    "STATUS_ACTIVE",
    "STATUS_ARCHIVED",
    "SORT_BY_CREATED",
    "SORT_BY_UPDATED",
    "SORT_BY_ACCESSED",
]
