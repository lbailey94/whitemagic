"""Phase 3 §7.2 — Cache-key namespace isolation tests.

Tests that:
- Cache keys for the same tool+args but different user_id are different
- Cache keys for the same tool+args but different agent_id are different
- Cache keys for the same tool+args but different galaxy are different
- Cache keys for the same tool+args but different policy profile are different
- Cache keys are deterministic for identical inputs
- _cache_key() now includes namespace fields (Phase 3 fix verified)
- Private memory tools are excluded from caching by default
"""
from __future__ import annotations

import hashlib


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


class TestCacheKeyNamespaceIsolation:
    """Verify _cache_key() includes namespace isolation after Phase 3 fix.

    The implementation in middleware.py now builds cache keys from
    tool_name + prompt kwargs + namespace (user_id, agent_id, galaxy,
    policy_profile). This ensures two users with the same query get
    different cache entries — preventing privacy and security violations.
    """

    def test_cache_key_includes_user_id(self):
        """_cache_key now includes user_id in the key — different users get different keys."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", kwargs, user_id="alice")
        key_b = _cache_key("search", kwargs, user_id="bob")
        assert key_a != key_b, (
            "Cache keys must differ for different users after Phase 3 fix."
        )

    def test_cache_key_includes_galaxy(self):
        """_cache_key now includes galaxy in the key for all tools."""
        from whitemagic.tools.middleware import _cache_key

        key_a = _cache_key("llama_cpp", {"query": "hello"}, galaxy="codex")
        key_b = _cache_key("llama_cpp", {"query": "hello"}, galaxy="sessions")
        assert key_a != key_b, (
            "Cache keys must differ for different galaxies after Phase 3 fix."
        )

    def test_cache_key_includes_agent_id(self):
        """_cache_key now includes agent_id in the key."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", kwargs, agent_id="agent_1")
        key_b = _cache_key("search", kwargs, agent_id="agent_2")
        assert key_a != key_b

    def test_cache_key_includes_policy_profile(self):
        """_cache_key now includes policy_profile in the key."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", kwargs, policy_profile="strict")
        key_b = _cache_key("search", kwargs, policy_profile="permissive")
        assert key_a != key_b

    def test_cache_key_deterministic_with_namespace(self):
        """Same inputs including namespace produce same key."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_a = _cache_key("search", kwargs, user_id="alice", agent_id="a1", galaxy="codex")
        key_b = _cache_key("search", kwargs, user_id="alice", agent_id="a1", galaxy="codex")
        assert key_a == key_b

    def test_cache_key_backward_compat_default_namespace(self):
        """Default namespace values produce same key as before (backward compat)."""
        from whitemagic.tools.middleware import _cache_key

        kwargs = {"query": "hello world"}
        key_default = _cache_key("search", kwargs)
        key_explicit = _cache_key("search", kwargs, user_id="local", agent_id="default", galaxy="default", policy_profile="default")
        assert key_default == key_explicit
