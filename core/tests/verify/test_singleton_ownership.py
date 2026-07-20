"""Contract test: verify singleton ownership and lifecycle.

This test inventories all get_*() singleton factory functions in the codebase,
classifies them by scope, and verifies that critical singletons are registered
in the SingletonRegistry for test cleanup.

Scope classification:
  - process-scoped: singleton lives for the entire process (e.g., config, dispatch)
  - user-scoped: singleton is keyed by user_id (e.g., memory, sessions)
  - request-scoped: singleton is created per-request (not a true singleton)
  - stateless: function returns a new instance each call (not a singleton)
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

WHITEMAGIC_ROOT = (Path(__file__).resolve().parent.parent.parent / "whitemagic").resolve()
assert WHITEMAGIC_ROOT.is_dir(), f"WHITEMAGIC_ROOT does not exist: {WHITEMAGIC_ROOT}"


def _find_singleton_factories() -> list[tuple[str, str]]:
    """Find all get_*() functions that cache an instance (singleton pattern)."""
    factories: list[tuple[str, str]] = []
    for py_file in WHITEMAGIC_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "def get_" not in content or "is None" not in content:
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("get_"):
                continue
            # Get the source lines for this function
            lines = content.splitlines()
            func_lines = lines[node.lineno - 1: node.end_lineno if node.end_lineno else node.lineno + 20]
            func_src = "\n".join(func_lines)
            # Singleton pattern: checks "is None" and uses "global _" or "cls._instance"
            if "is None" in func_src and ("global _" in func_src or "cls._instance" in func_src):
                rel = str(py_file.relative_to(WHITEMAGIC_ROOT))
                factories.append((rel, node.name))
    return factories


class TestSingletonOwnership:
    """Verify singleton ownership and lifecycle management."""

    def test_singleton_registry_exists(self):
        """SingletonRegistry must be importable and functional."""
        from whitemagic.utils.singleton_registry import SingletonRegistry

        assert hasattr(SingletonRegistry, "register")
        assert hasattr(SingletonRegistry, "reset_all")
        assert hasattr(SingletonRegistry, "get_registered_names")

    def test_legacy_table_covers_critical_subsystems(self):
        """The legacy singleton table must cover critical subsystem singletons."""
        from whitemagic.utils.singleton_registry import _LEGACY_SINGLETONS

        legacy_modules = {mod for mod, _ in _LEGACY_SINGLETONS}

        # Critical subsystems that MUST be in the legacy table for test cleanup
        critical = {
            "whitemagic.core.memory.unified",
            "whitemagic.core.memory.galactic_map",
            "whitemagic.core.memory.consolidation",
            "whitemagic.core.memory.lifecycle",
            "whitemagic.core.intelligence.self_model",
            "whitemagic.core.consciousness.coherence",
            "whitemagic.core.consciousness.citta_cycle",
            "whitemagic.core.consciousness.consciousness_loop",
            "whitemagic.core.dreaming.dream_cycle",
            "whitemagic.core.evolution.recursive_loop",
            "whitemagic.harmony.homeostatic_loop",
            "whitemagic.dharma.karma_ledger",
            "whitemagic.tools.circuit_breaker",
            "whitemagic.tools.rate_limiter",
            "whitemagic.tools.tool_permissions",
            "whitemagic.tools.handlers.broker",
            "whitemagic.tools.prat_resonance",
        }

        missing = critical - legacy_modules
        assert not missing, (
            f"Critical subsystems missing from _LEGACY_SINGLETONS: {missing}"
        )

    def test_no_duplicate_legacy_entries(self):
        """Legacy singleton table must not have duplicate entries."""
        from whitemagic.utils.singleton_registry import _LEGACY_SINGLETONS

        seen: set[tuple[str, str]] = set()
        duplicates: list[tuple[str, str]] = []
        for entry in _LEGACY_SINGLETONS:
            if entry in seen:
                duplicates.append(entry)
            seen.add(entry)

        assert not duplicates, (
            f"Duplicate entries in _LEGACY_SINGLETONS: {duplicates}"
        )

    def test_legacy_count_no_shrinkage(self):
        """Legacy singleton table must not shrink from baseline."""
        from whitemagic.utils.singleton_registry import (
            _LEGACY_CLASS_SINGLETONS,
            _LEGACY_SINGLETONS,
        )

        total = len(_LEGACY_SINGLETONS) + len(_LEGACY_CLASS_SINGLETONS)
        BASELINE = 107  # No-shrink baseline (2026-07-19, after dedup)
        assert total >= BASELINE, (
            f"Legacy singleton table shrank from {BASELINE} to {total}. "
            f"If singletons were migrated to factory-based registration, update BASELINE."
        )

    def test_reset_all_singletons_is_safe(self):
        """reset_all_singletons must not raise on empty registry."""
        from whitemagic.utils.singleton_registry import reset_all_singletons

        # Should not raise even with no singletons registered
        reset_all_singletons()

    def test_factory_based_registration_works(self):
        """register_singleton must cache and return the same instance."""
        from whitemagic.utils.singleton_registry import (
            register_singleton,
            reset_singleton,
        )

        class _TestSingleton:
            pass

        name = "test._TestSingleton"
        try:
            inst1 = register_singleton(name, lambda: _TestSingleton())
            inst2 = register_singleton(name, lambda: _TestSingleton())
            assert inst1 is inst2, "register_singleton must return cached instance"
        finally:
            reset_singleton(name)

    def test_singleton_factory_count_baselined(self):
        """Verify the total singleton factory count hasn't changed unexpectedly."""
        factories = _find_singleton_factories()
        # This is a diagnostic — the count includes many non-critical singletons
        # that don't need registry tracking. We just verify the count is stable.
        BASELINE_MIN = 400  # No-shrink baseline (2026-07-19)
        assert len(factories) >= BASELINE_MIN, (
            f"Singleton factory count dropped from {BASELINE_MIN} to {len(factories)}. "
            f"This may indicate singletons were removed or refactored."
        )
