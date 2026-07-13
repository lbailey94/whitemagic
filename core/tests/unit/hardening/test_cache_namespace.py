"""Slice 3 — Cache-key namespace tests for user, agent, galaxy, and policy profile.

Tests that:
- Cache keys for the same tool+args but different user_id are different
- Cache keys for the same tool+args but different agent_id are different
- Cache keys for the same tool+args but different galaxy are different
- Cache keys for the same tool+args but different policy profile are different
- Cache keys are deterministic for identical inputs
- Current _cache_key() does NOT include namespace fields (documents the gap)

These tests document the current behavior and define the target behavior.
The tests that assert "current behavior" will be updated when Phase 3
implements namespace-aware cache keys.
"""
from __future__ import annotations

import hashlib

import pytest


def _build_namespace_cache_key(
    tool_name: str,
    kwargs: dict,
    user_id: str = "default",
    agent_id: str = "default",
    galaxy: str = "default",
    policy_profile: str = "default",
) -> str:
    """Target implementation: cache key with namespace isolation."""
    prompt_parts = []
    for key in ("prompt", "query", "message", "text", "input", "question"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            prompt_parts.append(val)

    namespace = f"{user_id}:{agent_id}:{galaxy}:{policy_profile}"
    content = f"{tool_name}:{namespace}:{':'.join(prompt_parts)}"
    return hashlib.md5(content.lower().strip().encode()).hexdigest()[:16]


class TestCacheNamespaceIsolation:
    """Cache keys must differ across user, agent, galaxy, and policy boundaries."""

    def test_same_args_different_user(self):
        kwargs = {"query": "hello world"}
        key_a = _build_namespace_cache_key("search", kwargs, user_id="alice")
        key_b = _build_namespace_cache_key("search", kwargs, user_id="bob")
        assert key_a != key_b, "Cache keys must differ for different users"

    def test_same_args_different_agent(self):
        kwargs = {"query": "hello world"}
        key_a = _build_namespace_cache_key("search", kwargs, agent_id="agent_1")
        key_b = _build_namespace_cache_key("search", kwargs, agent_id="agent_2")
        assert key_a != key_b, "Cache keys must differ for different agents"

    def test_same_args_different_galaxy(self):
        kwargs = {"query": "hello world"}
        key_a = _build_namespace_cache_key("search", kwargs, galaxy="codex")
        key_b = _build_namespace_cache_key("search", kwargs, galaxy="sessions")
        assert key_a != key_b, "Cache keys must differ for different galaxies"

    def test_same_args_different_policy(self):
        kwargs = {"query": "hello world"}
        key_a = _build_namespace_cache_key("search", kwargs, policy_profile="strict")
        key_b = _build_namespace_cache_key("search", kwargs, policy_profile="permissive")
        assert key_a != key_b, "Cache keys must differ for different policy profiles"

    def test_identical_inputs_produce_identical_keys(self):
        kwargs = {"query": "hello world"}
        key_a = _build_namespace_cache_key("search", kwargs, user_id="alice", agent_id="a1")
        key_b = _build_namespace_cache_key("search", kwargs, user_id="alice", agent_id="a1")
        assert key_a == key_b, "Identical inputs must produce identical cache keys"

    def test_different_tool_names_produce_different_keys(self):
        kwargs = {"query": "hello"}
        key_a = _build_namespace_cache_key("search", kwargs)
        key_b = _build_namespace_cache_key("generate", kwargs)
        assert key_a != key_b

    def test_different_queries_produce_different_keys(self):
        key_a = _build_namespace_cache_key("search", {"query": "hello"})
        key_b = _build_namespace_cache_key("search", {"query": "world"})
        assert key_a != key_b

    def test_empty_kwargs_still_namespaced(self):
        """Even with no prompt args, namespace must differentiate."""
        key_a = _build_namespace_cache_key("health.check", {}, user_id="alice")
        key_b = _build_namespace_cache_key("health.check", {}, user_id="bob")
        assert key_a != key_b

    def test_all_four_fields_combined(self):
        """All four namespace fields together produce unique keys."""
        base_kwargs = {"query": "test"}
        key_a = _build_namespace_cache_key(
            "search", base_kwargs,
            user_id="alice", agent_id="a1", galaxy="codex", policy_profile="strict",
        )
        key_b = _build_namespace_cache_key(
            "search", base_kwargs,
            user_id="bob", agent_id="a2", galaxy="sessions", policy_profile="permissive",
        )
        assert key_a != key_b

    def test_partial_namespace_change_differs(self):
        """Changing only one namespace field is sufficient."""
        base_kwargs = {"query": "test"}
        key_a = _build_namespace_cache_key(
            "search", base_kwargs, user_id="alice", agent_id="a1", galaxy="codex",
        )
        # Change only galaxy
        key_b = _build_namespace_cache_key(
            "search", base_kwargs, user_id="alice", agent_id="a1", galaxy="research",
        )
        assert key_a != key_b


class TestCurrentCacheKeyGap:
    """Document the current _cache_key() behavior and its namespace gap.

    The current implementation in middleware.py builds cache keys from
    tool_name + prompt kwargs only, WITHOUT user_id, agent_id, galaxy,
    or policy_profile. This means two users with the same query would
    share a cache entry — a privacy and security violation.

    These tests document the gap. They will be updated in Phase 3.
    """

    def test_current_cache_key_ignores_user(self):
        """Current _cache_key does NOT include user_id in the key."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", {**kwargs, "user_id": "alice"})
        key_b = _cache_key("search", {**kwargs, "user_id": "bob"})
        # GAP: These are the same because user_id is not in the prompt kwargs list
        # and _cache_key only looks at prompt/query/message/text/input/question
        assert key_a == key_b, (
            "Documents the gap: cache keys are identical for different users. "
            "This must be fixed in Phase 3."
        )

    def test_current_cache_key_ignores_galaxy(self):
        """Current _cache_key does NOT include galaxy in the key."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello", "galaxy": "codex"}
        key_a = _cache_key("search_memories", kwargs)
        kwargs_b = {"query": "hello", "galaxy": "sessions"}
        key_b = _cache_key("search_memories", kwargs_b)
        # GAP: galaxy IS in the read-only structural kwargs list, but only for
        # tools matching _READ_ONLY_CACHEABLE_PATTERNS. For non-read-only tools,
        # galaxy is ignored.
        # For search_memories (which IS read-only), galaxy IS included.
        # This test verifies that for a non-read-only tool, galaxy is ignored.
        key_c = _cache_key("llama_cpp", {"query": "hello", "galaxy": "codex"})
        key_d = _cache_key("llama_cpp", {"query": "hello", "galaxy": "sessions"})
        assert key_c == key_d, (
            "Documents the gap: non-read-only tools ignore galaxy in cache keys. "
            "This must be fixed in Phase 3."
        )

    def test_current_cache_key_deterministic(self):
        """Same inputs produce same key (positive test)."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", kwargs)
        key_b = _cache_key("search", kwargs)
        assert key_a == key_b
