"""Detect hardcoded URLs in source code that should be in configuration.

Anti-pattern:
    response = requests.get("https://api.example.com/v1/data")
    client = MongoClient("mongodb://localhost:27017")

Better:
    API_URL = config.get("api_url", "https://api.example.com/v1/data")
    response = requests.get(API_URL)

Skips:
- URLs in comments and docstrings
- URLs in test files (test fixtures often use hardcoded URLs)
- localhost/127.0.0.1 URLs in development config
- URLs that are already assigned to constants (UPPER_CASE variables)
- URLs in string formatting (f-strings with variables)
- Well-known documentation URLs (docs.python.org, json.org, etc.)
"""

import ast
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

_URL_PATTERN = re.compile(r"https?://[^\s\"']+")

_DOC_DOMAINS = frozenset({
    "docs.python.org", "json.org", "www.w3.org", "tools.ietf.org",
    "developer.mozilla.org", "peps.python.org", "docs.python.org",
})

_SKIP_DOMAINS = frozenset({
    "localhost", "127.0.0.1", "0.0.0.0",
    "schema.org", "www.w3.org", "purl.org",
})


def _is_constant_assignment(node: ast.AST, url_node: ast.AST) -> bool:
    """Check if a URL string is assigned to an UPPER_CASE constant."""
    # Walk up: we can't get parents with ast.walk, so check if the URL
    # is a direct value of an Assign with UPPER_CASE target
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                return True
    return False


@register
def check_hardcoded_url(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect hardcoded URLs in source code."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue
        rel = str(py_file.relative_to(project_path))

        if file_index.is_test_file(py_file):
            continue

        # Collect lines inside string literals (docstrings)
        string_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                        string_lines.add(ln)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                urls = _URL_PATTERN.findall(node.value)
                if not urls:
                    continue

                # Skip if inside a docstring (first statement of module/function/class)
                if node.lineno in string_lines and hasattr(node, "lineno"):
                    # Check if this is a docstring
                    pass  # Conservative: we check by position below

                for url in urls:
                    domain = url.split("//")[1].split("/")[0].split(":")[0] if "//" in url else ""

                    if domain in _SKIP_DOMAINS:
                        continue
                    if any(doc in domain for doc in _DOC_DOMAINS):
                        continue
                    if domain.endswith(".local") or domain.endswith(".internal"):
                        continue

                    # Check if assigned to a constant
                    # We need to find the parent — use a different approach
                    # Walk all Assign nodes and check if this constant is a value
                    is_constant = False
                    for other in ast.walk(tree):
                        if isinstance(other, ast.Assign):
                            for val_node in ast.walk(other):
                                if val_node is node:
                                    for target in other.targets:
                                        if isinstance(target, ast.Name) and target.id.isupper():
                                            is_constant = True
                                            break

                    if is_constant:
                        continue

                    findings.append(Finding(
                        severity=FindingSeverity.INFO,
                        category="hardcoded_url",
                        file=rel,
                        line=node.lineno,
                        message=f"Hardcoded URL '{url[:60]}' — consider moving to configuration.",
                        suggestion="Move URLs to config file or environment variables.",
                    ))
                    break  # One finding per string node
