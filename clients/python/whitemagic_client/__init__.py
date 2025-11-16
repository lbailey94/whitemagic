"""WhiteMagic Python SDK - Memory infrastructure for AI agents."""

from .client import WhiteMagicClient
from .exceptions import WhiteMagicError
from .types import (
    Memory,
    CreateMemoryRequest,
    UpdateMemoryRequest,
    ListMemoriesParams,
    SearchMemoriesParams,
    User,
    UsageStats,
    HealthResponse,
    MemoryType,
)

__version__ = "2.2.1"
__all__ = [
    "WhiteMagicClient",
    "WhiteMagicError",
    "Memory",
    "CreateMemoryRequest",
    "UpdateMemoryRequest",
    "ListMemoriesParams",
    "SearchMemoriesParams",
    "User",
    "UsageStats",
    "HealthResponse",
    "MemoryType",
]
