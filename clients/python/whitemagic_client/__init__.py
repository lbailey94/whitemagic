"""WhiteMagic Python SDK - Memory infrastructure for AI agents."""

from .client import WhiteMagicClient
from .exceptions import WhiteMagicError
from .types import (
    CreateMemoryRequest,
    HealthResponse,
    ListMemoriesParams,
    Memory,
    MemoryType,
    SearchMemoriesParams,
    UpdateMemoryRequest,
    UsageStats,
    User,
)

__version__ = "2.2.8"
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
