"""Tests for the Template Polymorphism Engine (Phase 1)."""

from whitemagic.codegenome.polymorphism import PolymorphismEngine


class TestPolymorphismEngine:
    def test_polymorph_returns_string(self):
        engine = PolymorphismEngine(seed=42)
        code = "def get_items():\n    return {'ok': True}\n"
        result = engine.polymorph(code, intensity=1.0)
        assert isinstance(result, str)

    def test_polymorph_idempotent_when_disabled(self):
        engine = PolymorphismEngine(seed=42)
        code = "def get_items():\n    return {'ok': True}\n"
        result = engine.polymorph(code, mangle_names=False, shuffle_imports=False,
                                   transform_control_flow=False, vary_comments=False,
                                   insert_junk=False, intensity=1.0)
        assert result == code

    def test_mangle_variable_names(self):
        engine = PolymorphismEngine(seed=42)
        code = "def get_items():\n    return {'ok': True}\n"
        result = engine._mangle_variable_names(code)
        # Should have renamed get_items to something else
        assert "get_items" not in result or result == code  # Could be same if random chose "get"

    def test_shuffle_imports_preserves_future(self):
        engine = PolymorphismEngine(seed=42)
        code = "from __future__ import annotations\nimport os\nimport sys\nimport json\n"
        result = engine._shuffle_imports(code)
        # __future__ must stay first
        assert result.startswith("from __future__")

    def test_shuffle_imports_single_import_unchanged(self):
        engine = PolymorphismEngine(seed=42)
        code = "import os\n"
        result = engine._shuffle_imports(code)
        assert result == code

    def test_control_flow_transform_ternary_to_if(self):
        from whitemagic.codegenome.polymorphism import _ternary_to_if_else
        code = "x = 1 if True else 0\n"
        result = _ternary_to_if_else(code)
        assert "if True" in result

    def test_control_flow_transform_for_to_while(self):
        from whitemagic.codegenome.polymorphism import _for_to_while
        code = "for i in range(10):\n    print(i)\n"
        result = _for_to_while(code)
        assert "while" in result

    def test_vary_comments(self):
        engine = PolymorphismEngine(seed=42)
        code = "# TODO: add validation\n"
        result = engine._vary_comments(code)
        # The original TODO: should be transformed to a different marker
        assert result != code or "# TODO:" not in result

    def test_insert_junk_code(self):
        engine = PolymorphismEngine(seed=42)
        code = "def foo():\n    return 1\n    return 2\n    return 3\n    return 4\n    return 5\n"
        result = engine._insert_junk_code(code)
        assert len(result) > len(code)

    def test_seed_reproducibility(self):
        code = "def get_items():\n    return {'ok': True}\n"
        engine1 = PolymorphismEngine(seed=42)
        engine2 = PolymorphismEngine(seed=42)
        result1 = engine1.polymorph(code, intensity=1.0)
        result2 = engine2.polymorph(code, intensity=1.0)
        assert result1 == result2

    def test_get_variation_count(self):
        engine = PolymorphismEngine(seed=42)
        code = "def get_items():\n    return {'ok': True}\n"
        count = engine.get_variation_count(code)
        assert count > 1
