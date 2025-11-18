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

from importlib import metadata
from pathlib import Path


def _load_version() -> str:
    """Return the installed package version with a source-tree fallback."""
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    try:
        return metadata.version("whitemagic")
    except metadata.PackageNotFoundError:
        pass
    return "unknown"


__version__ = _load_version()
__author__ = "WhiteMagic Team"

from .chinese_dict import load_core_concepts
from .concept_map import (
    ConceptMap,
    create_concept_map,
)

# Constants exports (commonly used)
from .constants import (
    MEMORY_TYPE_LONG_TERM,
    MEMORY_TYPE_SHORT_TERM,
    SORT_BY_ACCESSED,
    SORT_BY_CREATED,
    SORT_BY_UPDATED,
    STATUS_ACTIVE,
    STATUS_ARCHIVED,
)

# Core exports
from .core import MemoryManager
from .delta_tracking import DeltaTracker, SessionDelta, track_session_changes

# Exception exports
from .exceptions import (
    APIError,
    APIKeyExpiredError,
    AuthenticationError,
    AuthorizationError,
    FileOperationError,
    InvalidAPIKeyError,
    InvalidMemoryTypeError,
    InvalidSortOptionError,
    InvalidTierError,
    MemoryAlreadyArchivedError,
    MemoryAlreadyExistsError,
    MemoryNotArchivedError,
    MemoryNotFoundError,
    MetadataCorruptedError,
    QuotaExceededError,
    RateLimitExceededError,
    ValidationError,
    WhiteMagicError,
)

# Model exports
from .models import (
    ConsolidateRequest,
    ConsolidateResponse,
    ContextRequest,
    ContextResponse,
    ErrorResponse,
    Memory,
    MemoryCreate,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryUpdate,
    NormalizeTagsRequest,
    NormalizeTagsResponse,
    RestoreRequest,
    StatsResponse,
    SuccessResponse,
    TagInfo,
    TagsResponse,
)
from .session_templates import (
    SessionSnapshot,
    StartHereTemplate,
    create_start_here_memory,
)
from .session_types import (
    SessionConfigurator,
    SessionType,
    SessionTypeDetector,
    configure_session,
    print_session_config,
)

# Symbolic reasoning and integrations (v2.2.5)
from .symbolic import (
    ConceptNode,
    ConceptType,
    SymbolicReasoning,
    create_symbolic_engine,
)
from .symbolic_memory import (
    SymbolicMemoryIntegration,
    create_symbolic_memory_integration,
)

# Workflow patterns (v2.2.5)
from .workflow_patterns import (
    LoadingTier,
    TaskTerrain,
    ThreadingTier,
    WorkflowConfig,
    WorkflowPatterns,
    configure_workflow,
    get_workflow,
)

# Meta-optimization exports (v2.2.5)
from .workspace_loader import WorkspaceLoader, load_workspace_for_task

# Wu Xing cycle detection
from .wu_xing import (
    Activity,
    Phase,
    WuXingDetector,
)

__version__ = "2.2.8"

__all__ = [
    "__version__",
    "MemoryManager",
    "ContextPreloader",
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
    # Meta-optimization (v2.2.5)
    "WorkspaceLoader",
    "load_workspace_for_task",
    "StartHereTemplate",
    "create_start_here_memory",
    "SessionSnapshot",
    "DeltaTracker",
    "track_session_changes",
    "SessionDelta",
    "SessionType",
    "SessionTypeDetector",
    "SessionConfigurator",
    "configure_session",
    "print_session_config",
    # Symbolic reasoning (v2.2.5)
    "SymbolicReasoning",
    "ConceptNode",
    "ConceptType",
    "create_symbolic_engine",
    "ConceptMap",
    "create_concept_map",
    "SymbolicMemoryIntegration",
    "create_symbolic_memory_integration",
    "load_core_concepts",
    # Workflow patterns (v2.2.5)
    "WorkflowPatterns",
    "WorkflowConfig",
    "get_workflow",
    "configure_workflow",
    "ThreadingTier",
    "LoadingTier",
    "TaskTerrain",
    # Wu Xing cycle detection
    "WuXingDetector",
    "Phase",
    "Activity",
]
