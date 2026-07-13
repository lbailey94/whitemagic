"""MemoryContext — Request-scoped memory namespace identity.

This type is introduced in Phase 0 (First Implementation Slice) as a
non-breaking addition. It does NOT change routing yet — it simply
provides a typed container for the (user_id, galaxy) tuple that will
be required by Phase 2 (Memory and Galaxy Boundary Consolidation).

Usage (future, after Phase 2 wiring)::

    ctx = MemoryContext(user_id="alice", galaxy="codex")
    memories = um.search("query", memory_context=ctx)

For now, this type exists alongside the current routing and is used
only by tests and documentation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryContext:
    """Request-scoped identity for memory operations.

    A memory belongs to exactly one (user_id, galaxy) namespace.
    This type makes that identity explicit and request-scoped.

    The ``extra`` dict is excluded from hashing and equality to keep
    the dataclass hashable. It is metadata only.

    Attributes:
        user_id: The user who owns this memory namespace. Default "local".
        galaxy: The galaxy within which this operation is scoped.
            "default" is the legacy single-galaxy namespace.
        agent_id: The agent initiating this request (for audit and cache isolation).
        policy_profile: The governance profile in effect (for cache and policy isolation).
        request_id: Optional request ID for tracing.
        extra: Optional metadata bag for future extensions. Not included in hash/eq.
    """

    user_id: str = "local"
    galaxy: str = "default"
    agent_id: str = "default"
    policy_profile: str = "default"
    request_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    @property
    def namespace_key(self) -> str:
        """A deterministic string identifying this namespace.

        Used for cache keys, singleton isolation, and logging.
        Format: ``user_id/galaxy``
        """
        return f"{self.user_id}/{self.galaxy}"

    @property
    def cache_namespace(self) -> str:
        """A deterministic string for cache key isolation.

        Includes all fields that affect cache identity:
        user_id, agent_id, galaxy, policy_profile.
        """
        return f"{self.user_id}:{self.agent_id}:{self.galaxy}:{self.policy_profile}"

    def with_galaxy(self, galaxy: str) -> MemoryContext:
        """Return a new context with a different galaxy."""
        return MemoryContext(
            user_id=self.user_id,
            galaxy=galaxy,
            agent_id=self.agent_id,
            policy_profile=self.policy_profile,
            request_id=self.request_id,
            extra=dict(self.extra),
        )

    def with_user(self, user_id: str) -> MemoryContext:
        """Return a new context with a different user."""
        return MemoryContext(
            user_id=user_id,
            galaxy=self.galaxy,
            agent_id=self.agent_id,
            policy_profile=self.policy_profile,
            request_id=self.request_id,
            extra=dict(self.extra),
        )

    def with_agent(self, agent_id: str) -> MemoryContext:
        """Return a new context with a different agent."""
        return MemoryContext(
            user_id=self.user_id,
            galaxy=self.galaxy,
            agent_id=agent_id,
            policy_profile=self.policy_profile,
            request_id=self.request_id,
            extra=dict(self.extra),
        )

    def is_default(self) -> bool:
        """True if this context uses all default values (legacy compat)."""
        return (
            self.user_id == "local"
            and self.galaxy == "default"
            and self.agent_id == "default"
            and self.policy_profile == "default"
        )
