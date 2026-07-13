"""Partial Operation Result — structured reporting for batch/restore/import operations.

Phase 4 of the Codebase Hardening Strategy.

When a batch operation (import, restore, migration, bulk embed) processes
multiple items, some may succeed while others fail.  Instead of returning
a binary success/error, these operations should return a
``PartialOperationResult`` that captures:

- completed: items successfully processed
- skipped: items skipped (validation failure, duplicate, etc.)
- failed: items that raised an error
- item_errors: per-item error details (index, item_id, error)
- rollback_state: "none" | "staged" | "rolled_back" | "committed"

This allows callers to:
- Retry only failed items
- Report precise progress to users
- Make informed decisions about partial state
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItemError:
    """Error for a single item in a batch operation."""

    index: int
    item_id: str | None = None
    error_type: str = ""
    error_message: str = ""
    error_code: str = "internal_error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "item_id": self.item_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "error_code": self.error_code,
        }


@dataclass
class PartialOperationResult:
    """Structured result for operations that process multiple items.

    Attributes:
        operation: Name of the operation (e.g. "import", "restore", "batch_embed").
        total: Total number of items attempted.
        completed: Number of items successfully processed.
        skipped: Number of items skipped (not attempted or validation failure).
        failed: Number of items that raised an error.
        item_errors: Per-item error details for failed items.
        rollback_state: State of rollback if the operation was transactional.
            - "none": no rollback semantics
            - "staged": changes staged but not committed
            - "rolled_back": all changes rolled back due to failure threshold
            - "committed": changes committed (may be partial)
        metadata: Additional operation-specific metadata.
    """

    operation: str
    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    item_errors: list[ItemError] = field(default_factory=list)
    rollback_state: str = "none"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete_success(self) -> bool:
        """True if all items completed with no failures or skips."""
        return self.failed == 0 and self.skipped == 0 and self.completed == self.total

    @property
    def is_partial_failure(self) -> bool:
        """True if some items failed but others succeeded."""
        return self.failed > 0 and self.completed > 0

    @property
    def is_total_failure(self) -> bool:
        """True if all items failed."""
        return self.completed == 0 and self.failed > 0

    @property
    def success_rate(self) -> float:
        """Fraction of items that completed successfully."""
        if self.total == 0:
            return 0.0
        return self.completed / self.total

    def add_error(
        self,
        index: int,
        exc: Exception,
        item_id: str | None = None,
    ) -> None:
        """Record an item-level error from an exception."""
        from whitemagic.tools.errors import classify_exception

        typed = classify_exception(exc)
        self.item_errors.append(
            ItemError(
                index=index,
                item_id=item_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                error_code=typed.error_code,
            )
        )
        self.failed += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict suitable for envelope details."""
        return {
            "operation": self.operation,
            "total": self.total,
            "completed": self.completed,
            "skipped": self.skipped,
            "failed": self.failed,
            "item_errors": [e.to_dict() for e in self.item_errors],
            "rollback_state": self.rollback_state,
            "success_rate": round(self.success_rate, 4),
            "metadata": self.metadata,
        }

    def to_envelope_status(self) -> tuple[str, str, bool]:
        """Return (status, error_code, retryable) for envelope construction.

        Returns:
            - ("success", "", False) if complete success
            - ("error", "partial_operation", True) if partial failure
            - ("error", "internal_error", False) if total failure
        """
        if self.is_complete_success:
            return ("success", "", False)
        if self.is_total_failure:
            return ("error", "internal_error", False)
        return ("error", "partial_operation", True)
