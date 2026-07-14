"""Tests for Template Composition Graph (Phase 2) and Polyglot Templates (Phase 6)."""

from whitemagic.codegenome.engine import CodeGenomeEngine, CodeTemplate
from whitemagic.codegenome.vault import GeneseedVault


class TestCompositionGraph:
    def test_include_directive_resolves(self):
        """{{include:template_name}} should be resolved to rendered sub-template."""
        engine = CodeGenomeEngine()
        # Create a template with an include directive
        t = CodeTemplate(
            name="test_includer",
            default="Header\n{{include:fastapi_endpoint,path=/items,name=items}}\nFooter\n",
        )
        engine.register(t)
        result = engine.render("test_includer", tier="xianfeng")
        assert "get_items" in result
        assert "Header" in result
        assert "Footer" in result

    def test_include_with_variables(self):
        """Include directive should pass variables to sub-template."""
        engine = CodeGenomeEngine()
        t = CodeTemplate(
            name="test_include_vars",
            default="{{include:pydantic_model,name=MyModel}}\n",
        )
        engine.register(t)
        result = engine.render("test_include_vars")
        assert "MyModel" in result

    def test_include_unknown_template(self):
        """Unknown include should produce error comment."""
        engine = CodeGenomeEngine()
        t = CodeTemplate(
            name="test_include_unknown",
            default="{{include:does_not_exist}}\n",
        )
        engine.register(t)
        result = engine.render("test_include_unknown")
        assert "ERROR" in result

    def test_render_project_multi_file(self):
        """Project template should render into multiple files."""
        engine = CodeGenomeEngine()
        result = engine.render_project("fastapi_crud_project", tier="xianfeng")
        assert "src/main.py" in result
        assert "src/models.py" in result
        assert "Dockerfile" in result
        assert ".github/workflows/ci.yml" in result
        assert "get_items" in result["src/main.py"]
        assert "Item" in result["src/models.py"]

    def test_render_project_unknown_template(self):
        engine = CodeGenomeEngine()
        result = engine.render_project("does_not_exist")
        assert "error" in result

    def test_render_project_non_project_template(self):
        """Non-project template should render as single 'main' file."""
        engine = CodeGenomeEngine()
        result = engine.render_project("fastapi_endpoint", path="/test", name="test")
        assert "main" in result
        assert "get_test" in result["main"]

    def test_project_template_is_project(self):
        """Project template should have is_project=True in to_dict."""
        engine = CodeGenomeEngine()
        t = engine.get_template("fastapi_crud_project")
        assert t is not None
        d = t.to_dict()
        assert d["is_project"] is True

    def test_vibe_render_project(self):
        """Vault.vibe_render_project should work end-to-end."""
        vault = GeneseedVault()
        result = vault.vibe_render_project("fastapi project for items")
        assert result["status"] == "success"
        assert result["file_count"] >= 3


class TestPolyglotTemplates:
    def test_rust_struct_xianfeng(self):
        engine = CodeGenomeEngine()
        code = engine.render("rust_struct", name="User", tier="xianfeng")
        assert "pub struct User" in code
        assert "Debug" in code

    def test_rust_struct_huben(self):
        engine = CodeGenomeEngine()
        code = engine.render("rust_struct", name="User", tier="huben")
        assert "serde::Serialize" in code
        assert "impl User" in code

    def test_rust_trait_impl(self):
        engine = CodeGenomeEngine()
        code = engine.render(
            "rust_trait_impl",
            trait_name="Display",
            type_name="User",
            method_name="fmt",
            return_type="fmt::Result",
        )
        assert "impl Display for User" in code
        assert "fn fmt" in code

    def test_go_handler_xianfeng(self):
        engine = CodeGenomeEngine()
        code = engine.render("go_handler", name="User", tier="xianfeng")
        assert "func UserHandler" in code
        assert "http.ResponseWriter" in code

    def test_go_handler_huben(self):
        engine = CodeGenomeEngine()
        code = engine.render("go_handler", name="User", tier="huben")
        assert "json.NewEncoder" in code
        assert "service.GetUser" in code

    def test_typescript_interface(self):
        engine = CodeGenomeEngine()
        code = engine.render("typescript_interface", name="User", tier="wei_wuzu")
        assert "interface User" in code
        assert "label: string" in code

    def test_typescript_react_component(self):
        engine = CodeGenomeEngine()
        code = engine.render("typescript_react_component", name="Dashboard", tier="huben")
        assert "function Dashboard" in code
        assert "useState" in code

    def test_vibe_parser_rust(self):
        from whitemagic.codegenome.vibe_parser import VibeParser
        parser = VibeParser()
        result = parser.parse("make a rust struct for User")
        assert result["status"] == "matched"
        assert result["template_name"] == "rust_struct"

    def test_vibe_parser_go(self):
        from whitemagic.codegenome.vibe_parser import VibeParser
        parser = VibeParser()
        result = parser.parse("create a go handler for health")
        assert result["status"] == "matched"
        assert result["template_name"] == "go_handler"

    def test_vibe_parser_typescript(self):
        from whitemagic.codegenome.vibe_parser import VibeParser
        parser = VibeParser()
        result = parser.parse("typescript interface for User")
        assert result["status"] == "matched"
        assert result["template_name"] == "typescript_interface"
