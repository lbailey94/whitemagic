"""Unit tests for PoC code templates in CodeGenome engine."""
import pytest

from whitemagic.codegenome.engine import get_codegenome_engine, CodeTemplate
from whitemagic.codegenome.vibe_parser import get_vibe_parser


class TestPoCTemplateRegistration:
    def test_reentrancy_template_exists(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_reentrancy")
        assert tpl is not None
        assert "reentrancy" in tpl.tags
        assert "poc" in tpl.tags
        assert "security" in tpl.tags

    def test_access_bypass_template_exists(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_access_bypass")
        assert tpl is not None
        assert "access-control" in tpl.tags
        assert "poc" in tpl.tags

    def test_integer_overflow_template_exists(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_integer_overflow")
        assert tpl is not None
        assert "integer-overflow" in tpl.tags
        assert "poc" in tpl.tags

    def test_all_poc_templates_have_security_tag(self):
        engine = get_codegenome_engine()
        templates = engine.list_templates(tag="poc")
        assert len(templates) >= 3
        for tpl in templates:
            assert "security" in tpl["tags"], f"Template {tpl['name']} missing security tag"


class TestPoCTemplateRendering:
    def test_reentrancy_default_render(self):
        engine = get_codegenome_engine()
        code = engine.render("poc_reentrancy", withdraw_function="withdraw")
        assert "withdraw" in code
        assert "ReentrancyPoC" in code
        assert "receive()" in code
        assert "pragma solidity" in code

    def test_reentrancy_xianfeng_render(self):
        engine = get_codegenome_engine()
        code = engine.render("poc_reentrancy", tier="xianfeng", withdraw_function="claimReward")
        assert "claimReward" in code
        assert "ReentrancyPoC" in code
        assert "forge-std" not in code  # xianfeng has no forge imports

    def test_reentrancy_huben_render(self):
        engine = get_codegenome_engine()
        code = engine.render("poc_reentrancy", tier="huben", withdraw_function="withdraw")
        assert "forge-std/Test.sol" in code
        assert "reentryCount" in code
        assert "@notice" in code
        assert "@impact" in code
        assert "assertGt" in code

    def test_access_bypass_render(self):
        engine = get_codegenome_engine()
        code = engine.render(
            "poc_access_bypass",
            function_name="setAdmin",
            function_args="0xBEEF",
            target_address="0x1234",
        )
        assert "setAdmin" in code
        assert "0xBEEF" in code
        assert "AccessBypassPoC" in code

    def test_access_bypass_huben_render(self):
        engine = get_codegenome_engine()
        code = engine.render(
            "poc_access_bypass",
            tier="huben",
            function_name="mint",
            function_args="1000",
            target_address="0xTarget",
        )
        assert "vm.prank" in code
        assert "assertNotEq" in code
        assert "@impact" in code

    def test_integer_overflow_render(self):
        engine = get_codegenome_engine()
        code = engine.render(
            "poc_integer_overflow",
            function_name="addToBalance",
            target_address="0xTarget",
        )
        assert "addToBalance" in code
        assert "type(uint256).max" in code
        assert "IntegerOverflowPoC" in code

    def test_integer_overflow_huben_render(self):
        engine = get_codegenome_engine()
        code = engine.render(
            "poc_integer_overflow",
            tier="huben",
            function_name="add",
            target_address="0xTarget",
        )
        assert "totalSupply" in code
        assert "vm.prank" in code
        assert "@impact" in code
        assert "assertNotEq" in code

    def test_unmatched_variable_preserved(self):
        engine = get_codegenome_engine()
        code = engine.render("poc_reentrancy")  # No withdraw_function provided
        assert "{{withdraw_function}}" in code  # Variable placeholder preserved


class TestVibeParserPoCAliases:
    def test_reentrancy_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("I need a reentrancy poc")
        assert result["status"] == "matched"
        assert result["template_name"] == "poc_reentrancy"

    def test_reentrancy_exploit_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("generate a reentrancy exploit")
        assert result["template_name"] == "poc_reentrancy"

    def test_access_bypass_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("create an access bypass poc")
        assert result["template_name"] == "poc_access_bypass"

    def test_access_control_bypass_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("I need an access control bypass")
        assert result["template_name"] == "poc_access_bypass"

    def test_integer_overflow_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("make an integer overflow poc")
        assert result["template_name"] == "poc_integer_overflow"

    def test_overflow_exploit_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("generate an overflow exploit")
        assert result["template_name"] == "poc_integer_overflow"

    def test_underflow_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("create an underflow poc")
        assert result["template_name"] == "poc_integer_overflow"

    def test_unauthorized_access_alias(self):
        parser = get_vibe_parser()
        result = parser.parse("I need an unauthorized access poc")
        assert result["template_name"] == "poc_access_bypass"


class TestPoCTemplateVariables:
    def test_reentrancy_variables(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_reentrancy")
        assert tpl is not None
        assert "withdraw_function" in tpl.variables

    def test_access_bypass_variables(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_access_bypass")
        assert tpl is not None
        assert "function_name" in tpl.variables
        assert "function_args" in tpl.variables
        assert "target_address" in tpl.variables

    def test_integer_overflow_variables(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_integer_overflow")
        assert tpl is not None
        assert "function_name" in tpl.variables
        assert "target_address" in tpl.variables


class TestPoCTemplateDependencies:
    def test_reentrancy_has_forge_std_dependency(self):
        engine = get_codegenome_engine()
        tpl = engine.get_template("poc_reentrancy")
        assert tpl is not None
        assert "forge-std/Test.sol" in tpl.dependencies

    def test_all_poc_templates_have_forge_dependency(self):
        engine = get_codegenome_engine()
        for name in ["poc_reentrancy", "poc_access_bypass", "poc_integer_overflow"]:
            tpl = engine.get_template(name)
            assert tpl is not None
            assert any("forge" in dep for dep in tpl.dependencies), f"{name} missing forge dependency"
