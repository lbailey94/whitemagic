# ruff: noqa: BLE001
"""
Speculative Execution Engine
============================
Pre-validates AI-generated code or text using cheap local checks before
passing it to expensive downstream processes or the user.

Concepts:
- Syntax Check (AST): < 1ms
- Type Check (MyPy stub): ~100ms
- Local LLM Sanity Check: ~500ms
"""

import ast
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class SpeculativeExecutor:
    """
    Validates code/text candidates using a hierarchy of cheap->expensive checks.
    """

    def __init__(self, local_llm=None):
        self.local_llm = local_llm

    def check_python_syntax(self, code: str) -> tuple[bool, str | None]:
        """
        Cheap check: Does it parse as valid Python?
        Returns (valid, error_message).
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}"
        except Exception as e:
            return False, f"ParseError: {e}"

    def check_security_heuristics(self, code: str) -> tuple[bool, list[str]]:
        """
        Fast regex scan for obvious security issues (SQLi, hardcoded secrets).
        """
        issues = []

        # SQL Injection patterns
        if re.search(r'execute\(\s*f["\']', code):
            issues.append("Potential SQL Injection (f-string in execute)")

        # Hardcoded secrets
        if re.search(r'(api_key|secret)\s*=\s*["\'][A-Za-z0-9-_]{20,}["\']', code):
            issues.append("Potential Hardcoded Secret")

        # Dangerous exec
        if re.search(r"\b(exec|eval)\(", code):
            issues.append("Dangerous usage of exec/eval")

        return len(issues) == 0, issues

    def speculative_repair(self, code: str, error: str) -> str | None:
        """
        Attempt to repair code using Local LLM if available.
        """
        if not self.local_llm or not self.local_llm.is_available:
            return None

        prompt = (
            f"Fix the following Python code which has a SyntaxError: {error}.\n"
            f"Code:\n```python\n{code}\n```\n"
            f"Return ONLY the fixed code block."
        )

        fixed = self.local_llm.complete(prompt, max_tokens=1024)

        # Extract code block
        match = re.search(r"```python\n(.*?)\n```", fixed, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def validate(self, content: str, language: str = "python") -> dict[str, Any]:
        """
        Run full validation pipeline.
        """
        result = {"valid": True, "checks": [], "errors": []}

        if language.lower() == "python":
            # 1. Syntax
            valid_syntax, err = self.check_python_syntax(content)
            checks: list[dict[str, Any]] = list(result.get("checks", []))  # type: ignore
            checks.append({"name": "syntax", "passed": valid_syntax, "error": err})
            result["checks"] = checks
            if not valid_syntax:
                result["valid"] = False
                errors: list[str] = list(result.get("errors", []))  # type: ignore
                errors.append(str(err))
                result["errors"] = errors
                return result  # Fail fast

            # 2. Security
            valid_sec, issues = self.check_security_heuristics(content)
            checks.append({"name": "security", "passed": valid_sec, "issues": issues})
            if not valid_sec:
                result["valid"] = False
                errors = list(result.get("errors", []))  # type: ignore
                errors.extend(issues)
                result["errors"] = errors

        return result
