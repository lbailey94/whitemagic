"""Unit tests for the CodeGenome God-Kit modules."""

from whitemagic.codegenome.engine import (
    CodeGenomeEngine,
    CodeTemplate,
    get_codegenome_engine,
)
from whitemagic.codegenome.vault import GeneseedVault, get_geneseed_vault
from whitemagic.codegenome.vibe_parser import VibeParser, get_vibe_parser


class TestCodeTemplate:
    def test_render_default(self):
        t = CodeTemplate(name="test", default="hello {{name}}")
        assert t.render(name="world") == "hello world"

    def test_render_tier_variant(self):
        t = CodeTemplate(
            name="test",
            default="default",
            tier_variants={"xianfeng": "fast", "huben": "heavy"},
        )
        assert t.render(tier="xianfeng") == "fast"
        assert t.render(tier="huben") == "heavy"
        assert t.render() == "default"

    def test_render_unknown_variable(self):
        t = CodeTemplate(name="test", default="hello {{name}}")
        assert t.render() == "hello {{name}}"

    def test_fork(self):
        parent = CodeTemplate(name="parent", default="body", version=3)
        child = parent.fork("child", "new_body")
        assert child.name == "child"
        assert child.parent_id == "parent"
        assert child.version == 4
        assert child.default == "new_body"
        assert child.source == "forked"

    def test_fork_without_delta(self):
        parent = CodeTemplate(name="parent", default="body")
        child = parent.fork("child")
        assert child.default == "body"

    def test_to_dict(self):
        t = CodeTemplate(name="test", description="desc", version=2)
        d = t.to_dict()
        assert d["name"] == "test"
        assert d["version"] == 2
        assert "tier_variants" in d


class TestCodeGenomeEngine:
    def test_builtin_templates_loaded(self):
        engine = CodeGenomeEngine()
        status = engine.status()
        assert status["builtin_count"] >= 3

    def test_render_builtin_fastapi(self):
        engine = CodeGenomeEngine()
        code = engine.render(
            "fastapi_endpoint", path="/items", name="items", tier="xianfeng"
        )
        assert "get_items" in code
        assert "/items" in code

    def test_render_unknown_template(self):
        engine = CodeGenomeEngine()
        assert "unknown template" in engine.render("does_not_exist")

    def test_list_templates(self):
        engine = CodeGenomeEngine()
        templates = engine.list_templates()
        names = [t["name"] for t in templates]
        assert "fastapi_endpoint" in names

    def test_list_templates_by_tag(self):
        engine = CodeGenomeEngine()
        templates = engine.list_templates(tag="testing")
        names = [t["name"] for t in templates]
        assert "pytest_fixture" in names

    def test_get_template(self):
        engine = CodeGenomeEngine()
        t = engine.get_template("fastapi_endpoint")
        assert t is not None
        assert t.name == "fastapi_endpoint"

    def test_fork_template(self):
        engine = CodeGenomeEngine()
        child = engine.fork_template("fastapi_endpoint", "my_endpoint")
        assert child is not None
        assert child.name == "my_endpoint"
        assert child.parent_id == "fastapi_endpoint"

    def test_fork_unknown_template(self):
        engine = CodeGenomeEngine()
        assert engine.fork_template("unknown", "child") is None

    def test_register(self):
        engine = CodeGenomeEngine()
        t = CodeTemplate(name="custom", default="custom body")
        engine.register(t)
        assert engine.get_template("custom") is not None

    def test_singleton(self):
        e1 = get_codegenome_engine()
        e2 = get_codegenome_engine()
        assert e1 is e2


class TestVibeParser:
    def test_parse_fastapi(self):
        parser = VibeParser()
        result = parser.parse("I need a FastAPI endpoint for items")
        assert result["status"] == "matched"
        assert result["template_name"] == "fastapi_endpoint"
        assert "name" in result["variables"]

    def test_parse_pytest(self):
        parser = VibeParser()
        result = parser.parse("make a pytest fixture for database")
        assert result["status"] == "matched"
        assert result["template_name"] == "pytest_fixture"

    def test_parse_pydantic(self):
        parser = VibeParser()
        result = parser.parse("create a pydantic model for user")
        assert result["status"] == "matched"
        assert result["template_name"] == "pydantic_model"

    def test_parse_ambiguous(self):
        parser = VibeParser()
        result = parser.parse("hello world")
        assert result["status"] == "ambiguous"

    def test_tier_inference_fast(self):
        parser = VibeParser()
        result = parser.parse("quick fastapi endpoint")
        assert result["tier"] == "xianfeng"

    def test_tier_inference_production(self):
        parser = VibeParser()
        result = parser.parse("production-ready fastapi endpoint")
        assert result["tier"] == "huben"

    def test_tier_inference_default(self):
        parser = VibeParser()
        result = parser.parse("fastapi endpoint")
        assert result["tier"] == "xianfeng"

    def test_register_alias(self):
        parser = VibeParser()
        parser.register_alias("my_alias", "fastapi_endpoint")
        result = parser.parse("my_alias for stuff")
        assert result["status"] == "matched"
        assert result["template_name"] == "fastapi_endpoint"

    def test_status(self):
        parser = VibeParser()
        s = parser.status()
        assert s["builtin_keywords"] > 0
        assert s["tier_hints"] > 0

    def test_singleton(self):
        p1 = get_vibe_parser()
        p2 = get_vibe_parser()
        assert p1 is p2


class TestGeneseedVault:
    def test_vibe_render_success(self):
        vault = GeneseedVault()
        result = vault.vibe_render("I need a FastAPI endpoint for items")
        assert result["status"] == "success"
        assert result["template_name"] == "fastapi_endpoint"
        assert "get_items" in result["code"]

    def test_vibe_render_failure(self):
        vault = GeneseedVault()
        result = vault.vibe_render("something completely unrelated")
        assert result["status"] == "error"
        assert result["error_code"] == "no_template_match"

    def test_fork(self):
        vault = GeneseedVault()
        result = vault.fork("fastapi_endpoint", "forked_endpoint")
        assert result["status"] == "success"
        assert result["template"]["name"] == "forked_endpoint"

    def test_fork_unknown(self):
        vault = GeneseedVault()
        result = vault.fork("unknown", "child")
        assert result["status"] == "error"
        assert result["error_code"] == "template_not_found"

    def test_list_templates(self):
        vault = GeneseedVault()
        templates = vault.list_templates()
        names = [t["name"] for t in templates]
        assert "fastapi_endpoint" in names

    def test_get_template(self):
        vault = GeneseedVault()
        t = vault.get_template("fastapi_endpoint")
        assert t is not None
        assert t["name"] == "fastapi_endpoint"

    def test_status(self):
        vault = GeneseedVault()
        s = vault.status()
        assert "engine" in s
        assert "parser" in s

    def test_singleton(self):
        v1 = get_geneseed_vault()
        v2 = get_geneseed_vault()
        assert v1 is v2
