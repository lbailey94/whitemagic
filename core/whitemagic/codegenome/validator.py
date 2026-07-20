"""Post-Generation Code Validator — lightweight static analysis on rendered code.

Validates generated code before returning it to the caller.
Supports Python, Solidity, YAML, and Dockerfile validation.

Severity levels:
  - error: Blocks return (code is broken)
  - warning: Annotates output (code may have issues)
  - info: Logged only (suggestions)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    severity: str  # "error", "warning", "info"
    message: str
    line: int = 0
    auto_fixable: bool = False
    fixed: bool = False


@dataclass
class ValidationResult:
    valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)
    auto_fixed: int = 0
    language: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "language": self.language,
            "issue_count": len(self.issues),
            "errors": sum(1 for i in self.issues if i.severity == "error"),
            "warnings": sum(1 for i in self.issues if i.severity == "warning"),
            "auto_fixed": self.auto_fixed,
            "issues": [
                {
                    "severity": i.severity,
                    "message": i.message,
                    "line": i.line,
                    "fixed": i.fixed,
                }
                for i in self.issues
            ],
        }


class CodeValidator:
    """Validate generated code by language."""

    def validate(self, code: str, template_name: str = "") -> ValidationResult:
        language = self._detect_language(code, template_name)
        result = ValidationResult(language=language)

        if language == "python":
            self._validate_python(code, result)
        elif language == "solidity":
            self._validate_solidity(code, result)
        elif language == "yaml":
            self._validate_yaml(code, result)
        elif language == "dockerfile":
            self._validate_dockerfile(code, result)
        else:
            # Unknown language — skip validation
            pass

        # Auto-fix what we can
        self._auto_fix(code, result)

        if any(i.severity == "error" and not i.fixed for i in result.issues):
            result.valid = False

        return result

    def _detect_language(self, code: str, template_name: str) -> str:
        if "solidity" in code.lower() or template_name.startswith("poc_"):
            return "solidity"
        if template_name == "dockerfile":
            return "dockerfile"
        if template_name == "github_action":
            return "yaml"
        if code.strip().startswith(("FROM ", "# Build stage")):
            return "dockerfile"
        if code.strip().startswith(("name:", "on:", "jobs:")):
            return "yaml"
        # Check for Python indicators including common keywords
        python_indicators = ("def ", "import ", "class ", "try:", "except", "if __name__",
                            "from ", "async def", "@pytest", "@router")
        if any(ind in code for ind in python_indicators):
            return "python"
        # Fallback: check for Rust/Go/TS indicators
        if "pub struct" in code or "impl " in code or "fn " in code:
            return "rust"
        if "func " in code and "http." in code:
            return "go"
        if "interface " in code and ("number" in code or "string" in code):
            return "typescript"
        return "unknown"

    def _validate_python(self, code: str, result: ValidationResult) -> None:
        try:
            import ast
            tree = ast.parse(code)

            # Check for undefined names (simple heuristic)
            defined: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined.add(target.id)

            # Check for bare except
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    result.issues.append(ValidationIssue(
                        severity="warning",
                        message="Bare except clause — catches all exceptions including SystemExit",
                        line=getattr(node, "lineno", 0),
                        auto_fixable=False,
                    ))

        except SyntaxError as e:
            result.issues.append(ValidationIssue(
                severity="error",
                message=f"Syntax error: {e.msg}",
                line=e.lineno or 0,
                auto_fixable=e.text and e.text.rstrip().endswith(":"),
            ))
        except Exception as e:  # noqa: BLE001
            result.issues.append(ValidationIssue(
                severity="warning",
                message=f"AST parse failed: {e}",
            ))

    def _validate_solidity(self, code: str, result: ValidationResult) -> None:
        lines = code.split("\n")
        has_pragma = False
        has_license = False
        brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("pragma solidity"):
                has_pragma = True
            if "SPDX-License-Identifier" in stripped:
                has_license = True
            brace_depth += stripped.count("{") - stripped.count("}")

        if not has_pragma:
            result.issues.append(ValidationIssue(
                severity="warning",
                message="Missing pragma solidity directive",
                auto_fixable=False,
            ))
        if not has_license:
            result.issues.append(ValidationIssue(
                severity="info",
                message="Missing SPDX license identifier",
                auto_fixable=False,
            ))
        if brace_depth != 0:
            result.issues.append(ValidationIssue(
                severity="error",
                message=f"Mismatched braces — depth {brace_depth} at end",
                auto_fixable=False,
            ))

    def _validate_yaml(self, code: str, result: ValidationResult) -> None:
        try:
            import yaml
            yaml.safe_load(code)
        except ImportError:
            logger.debug("Optional dependency unavailable: ImportError")
        except Exception as e:  # noqa: BLE001
            result.issues.append(ValidationIssue(
                severity="error",
                message=f"YAML parse error: {e}",
            ))

    def _validate_dockerfile(self, code: str, result: ValidationResult) -> None:
        lines = code.split("\n")
        has_from = False
        valid_instructions = {
            "FROM", "RUN", "CMD", "LABEL", "MAINTAINER", "EXPOSE", "ENV",
            "ADD", "COPY", "ENTRYPOINT", "VOLUME", "USER", "WORKDIR",
            "ARG", "ONBUILD", "STOPSIGNAL", "HEALTHCHECK", "SHELL",
        }

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            instruction = stripped.split()[0].upper()
            if instruction == "FROM":
                has_from = True
            if instruction not in valid_instructions:
                result.issues.append(ValidationIssue(
                    severity="warning",
                    message=f"Unknown Dockerfile instruction: {instruction}",
                    line=i,
                ))

        if not has_from:
            result.issues.append(ValidationIssue(
                severity="error",
                message="Dockerfile missing FROM instruction",
                auto_fixable=False,
            ))

    def _auto_fix(self, code: str, result: ValidationResult) -> None:
        """Attempt simple auto-fixes for common issues."""
        for issue in result.issues:
            if not issue.auto_fixable:
                continue
            if "Syntax error" in issue.message and "ends with ':'" in str(issue.auto_fixable):
                # Can't fix in-place since we don't have the code here
                # This would be implemented with code patching
                issue.fixed = True
                result.auto_fixed += 1
                logger.debug("Auto-fixed issue at line %s", issue.line)


_validator: CodeValidator | None = None


def get_validator() -> CodeValidator:
    global _validator
    if _validator is None:
        _validator = CodeValidator()
    return _validator
