"""Slice 5 — Tests for the MemoryContext type.

Tests that:
- MemoryContext is immutable (frozen dataclass)
- Default values match legacy compat
- namespace_key and cache_namespace are deterministic
- with_galaxy/with_user/with_agent produce new contexts
- Two contexts with same fields are equal
- is_default() correctly identifies legacy contexts
"""
from __future__ import annotations

import pytest

from whitemagic.core.memory.memory_context import MemoryContext


class TestMemoryContextBasic:
    def test_default_values(self):
        ctx = MemoryContext()
        assert ctx.user_id == "local"
        assert ctx.galaxy == "default"
        assert ctx.agent_id == "default"
        assert ctx.policy_profile == "default"
        assert ctx.request_id is None
        assert ctx.extra == {}

    def test_custom_values(self):
        ctx = MemoryContext(
            user_id="alice",
            galaxy="codex",
            agent_id="agent_1",
            policy_profile="strict",
            request_id="req-123",
        )
        assert ctx.user_id == "alice"
        assert ctx.galaxy == "codex"
        assert ctx.agent_id == "agent_1"
        assert ctx.policy_profile == "strict"
        assert ctx.request_id == "req-123"

    def test_is_frozen(self):
        ctx = MemoryContext(user_id="alice")
        with pytest.raises((AttributeError, Exception)):
            ctx.user_id = "bob"

    def test_extra_is_mutable_dict_but_context_is_frozen(self):
        """The dataclass is frozen but the extra dict itself is mutable.
        This is a known Python dataclass behavior — the frozen flag prevents
        reassignment of attributes, not mutation of mutable defaults.
        The extra dict should not be relied upon for immutability."""
        ctx = MemoryContext()
        ctx.extra["key"] = "value"  # This works because dict is mutable
        assert ctx.extra["key"] == "value"


class TestNamespaceKey:
    def test_namespace_key_format(self):
        ctx = MemoryContext(user_id="alice", galaxy="codex")
        assert ctx.namespace_key == "alice/codex"

    def test_default_namespace_key(self):
        ctx = MemoryContext()
        assert ctx.namespace_key == "local/default"

    def test_namespace_key_deterministic(self):
        ctx_a = MemoryContext(user_id="alice", galaxy="codex")
        ctx_b = MemoryContext(user_id="alice", galaxy="codex")
        assert ctx_a.namespace_key == ctx_b.namespace_key

    def test_different_users_different_namespace(self):
        ctx_a = MemoryContext(user_id="alice", galaxy="codex")
        ctx_b = MemoryContext(user_id="bob", galaxy="codex")
        assert ctx_a.namespace_key != ctx_b.namespace_key

    def test_different_galaxies_different_namespace(self):
        ctx_a = MemoryContext(user_id="alice", galaxy="codex")
        ctx_b = MemoryContext(user_id="alice", galaxy="sessions")
        assert ctx_a.namespace_key != ctx_b.namespace_key


class TestCacheNamespace:
    def test_cache_namespace_format(self):
        ctx = MemoryContext(
            user_id="alice", agent_id="a1", galaxy="codex", policy_profile="strict",
        )
        assert ctx.cache_namespace == "alice:a1:codex:strict"

    def test_default_cache_namespace(self):
        ctx = MemoryContext()
        assert ctx.cache_namespace == "local:default:default:default"

    def test_different_agents_different_cache(self):
        ctx_a = MemoryContext(agent_id="a1")
        ctx_b = MemoryContext(agent_id="a2")
        assert ctx_a.cache_namespace != ctx_b.cache_namespace

    def test_different_policy_different_cache(self):
        ctx_a = MemoryContext(policy_profile="strict")
        ctx_b = MemoryContext(policy_profile="permissive")
        assert ctx_a.cache_namespace != ctx_b.cache_namespace


class TestWithMethods:
    def test_with_galaxy(self):
        ctx = MemoryContext(user_id="alice", galaxy="codex")
        new = ctx.with_galaxy("sessions")
        assert new.galaxy == "sessions"
        assert new.user_id == "alice"
        assert ctx.galaxy == "codex"  # Original unchanged

    def test_with_user(self):
        ctx = MemoryContext(user_id="alice", galaxy="codex")
        new = ctx.with_user("bob")
        assert new.user_id == "bob"
        assert new.galaxy == "codex"
        assert ctx.user_id == "alice"

    def test_with_agent(self):
        ctx = MemoryContext(user_id="alice", agent_id="a1")
        new = ctx.with_agent("a2")
        assert new.agent_id == "a2"
        assert new.user_id == "alice"
        assert ctx.agent_id == "a1"

    def test_with_methods_preserve_other_fields(self):
        ctx = MemoryContext(
            user_id="alice", galaxy="codex", agent_id="a1",
            policy_profile="strict", request_id="r1",
        )
        new = ctx.with_galaxy("sessions")
        assert new.user_id == "alice"
        assert new.agent_id == "a1"
        assert new.policy_profile == "strict"
        assert new.request_id == "r1"


class TestEquality:
    def test_same_fields_equal(self):
        a = MemoryContext(user_id="alice", galaxy="codex")
        b = MemoryContext(user_id="alice", galaxy="codex")
        assert a == b

    def test_different_fields_not_equal(self):
        a = MemoryContext(user_id="alice", galaxy="codex")
        b = MemoryContext(user_id="bob", galaxy="codex")
        assert a != b

    def test_hashable(self):
        ctx = MemoryContext(user_id="alice", galaxy="codex")
        assert hash(ctx) is not None
        # Can be used in sets
        s = {ctx, MemoryContext(user_id="alice", galaxy="codex")}
        assert len(s) == 1


class TestIsDefault:
    def test_default_context_is_default(self):
        ctx = MemoryContext()
        assert ctx.is_default() is True

    def test_custom_user_not_default(self):
        ctx = MemoryContext(user_id="alice")
        assert ctx.is_default() is False

    def test_custom_galaxy_not_default(self):
        ctx = MemoryContext(galaxy="codex")
        assert ctx.is_default() is False

    def test_custom_agent_not_default(self):
        ctx = MemoryContext(agent_id="a1")
        assert ctx.is_default() is False

    def test_custom_policy_not_default(self):
        ctx = MemoryContext(policy_profile="strict")
        assert ctx.is_default() is False
