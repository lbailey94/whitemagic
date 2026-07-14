"""Tests for Post-Generation Code Validator (Phase 4)."""

from whitemagic.codegenome.validator import (
    CodeValidator,
    ValidationResult,
    get_validator,
)


class TestCodeValidator:
    def test_validate_python_valid(self):
        validator = CodeValidator()
        code = "def foo():\n    return 42\n"
        result = validator.validate(code, "fastapi_endpoint")
        assert result.valid is True
        assert result.language == "python"

    def test_validate_python_syntax_error(self):
        validator = CodeValidator()
        code = "def foo(:\n    return 42\n"
        result = validator.validate(code, "fastapi_endpoint")
        assert result.valid is False
        assert any(i.severity == "error" for i in result.issues)

    def test_validate_python_bare_except(self):
        validator = CodeValidator()
        code = "try:\n    pass\nexcept:\n    pass\n"
        result = validator.validate(code, "fastapi_endpoint")
        assert any(i.severity == "warning" for i in result.issues)

    def test_validate_solidity_valid(self):
        validator = CodeValidator()
        code = "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Test {}\n"
        result = validator.validate(code, "poc_reentrancy")
        assert result.language == "solidity"
        assert result.valid is True

    def test_validate_solidity_missing_pragma(self):
        validator = CodeValidator()
        code = "// SPDX-License-Identifier: MIT\ncontract Test {}\n"
        result = validator.validate(code, "poc_reentrancy")
        assert any("pragma" in i.message for i in result.issues)

    def test_validate_solidity_brace_mismatch(self):
        validator = CodeValidator()
        code = "pragma solidity ^0.8.0;\ncontract Test {\n"
        result = validator.validate(code, "poc_reentrancy")
        assert result.valid is False

    def test_validate_dockerfile_valid(self):
        validator = CodeValidator()
        code = "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"main.py\"]\n"
        result = validator.validate(code, "dockerfile")
        assert result.language == "dockerfile"
        assert result.valid is True

    def test_validate_dockerfile_missing_from(self):
        validator = CodeValidator()
        code = "WORKDIR /app\nCOPY . .\n"
        result = validator.validate(code, "dockerfile")
        assert result.valid is False

    def test_validate_yaml_valid(self):
        validator = CodeValidator()
        code = "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
        result = validator.validate(code, "github_action")
        assert result.language == "yaml"
        assert result.valid is True

    def test_validate_yaml_invalid(self):
        validator = CodeValidator()
        code = "name: CI\non: [push\njobs:\n  test:\n"
        result = validator.validate(code, "github_action")
        assert result.valid is False

    def test_validate_unknown_language(self):
        validator = CodeValidator()
        code = "some random text\n"
        result = validator.validate(code, "unknown_template")
        assert result.valid is True  # Unknown language passes

    def test_validation_result_to_dict(self):
        result = ValidationResult(valid=True, language="python")
        d = result.to_dict()
        assert d["valid"] is True
        assert d["language"] == "python"
        assert d["issue_count"] == 0

    def test_get_validator_singleton(self):
        v1 = get_validator()
        v2 = get_validator()
        assert v1 is v2

    def test_vibe_render_includes_validation(self):
        """Vault.vibe_render should include validation in the result."""
        from whitemagic.codegenome.vault import GeneseedVault
        vault = GeneseedVault()
        result = vault.vibe_render("fastapi endpoint for items")
        assert result["status"] == "success"
        assert "validation" in result
        assert result["validation"]["valid"] is True
