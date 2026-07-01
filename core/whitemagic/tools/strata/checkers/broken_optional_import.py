"""Detect broken try/except blocks from incorrectly removed side-effect imports.

When tools like aislop remove `# noqa: F401` side-effect imports, they
sometimes leave behind empty try bodies or try blocks that only contain
assignments, breaking the optional-dependency detection pattern.

Broken patterns this checker detects:

1. Empty try body (syntax error in Python, but can happen with bad edits):
   ```python
   try:
   except ImportError:
       _AVAILABLE = False
   ```

2. Try body with only assignments (import was removed, assignments remain):
   ```python
   try:
       _AVAILABLE = True
   except ImportError:
       _AVAILABLE = False
   ```
   This always sets _AVAILABLE = True, even if the package isn't installed,
   because there's no import to trigger the ImportError.

3. Try body with a comment but no code:
   ```python
   try:
       # import some_module  # noqa: F401
   except ImportError:
       _AVAILABLE = False
   ```

The correct pattern is:
   ```python
   try:
       import some_module  # noqa: F401
       _AVAILABLE = True
   except ImportError:
       _AVAILABLE = False
   ```
"""

import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _try_body_has_import(try_node: ast.Try) -> bool:
    """Check if the try body contains at least one import statement."""
    for stmt in try_node.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            return True
    return False


def _try_body_is_empty(try_node: ast.Try) -> bool:
    """Check if the try body is completely empty or only contains pass/Expr."""
    for stmt in try_node.body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            # String constant (docstring or comment-as-string)
            continue
        return False
    return True


def _try_body_only_assignments(try_node: ast.Try) -> bool:
    """Check if the try body only contains assignments (no imports, no calls).

    This is the signature pattern of a removed side-effect import:
    the import was stripped but `FLAG = True` remains, making the flag
    always True regardless of whether the package is installed.
    """
    has_assignment = False
    for stmt in try_node.body:
        if isinstance(stmt, ast.Assign):
            # Only flag if assigning a constant (FLAG = True/False/None)
            if isinstance(stmt.value, ast.Constant):
                has_assignment = True
            else:
                return False
        elif isinstance(stmt, ast.AnnAssign):
            if stmt.value is not None and isinstance(stmt.value, ast.Constant):
                has_assignment = True
            else:
                return False
        else:
            return False
    return has_assignment


def _has_importerror_handler(try_node: ast.Try) -> bool:
    """Check if any handler catches ImportError (or bare except which catches all)."""
    for handler in try_node.handlers:
        if handler.type is None:
            return True  # bare except catches everything including ImportError
        if isinstance(handler.type, ast.Name) and handler.type.id == "ImportError":
            return True
        if isinstance(handler.type, ast.Tuple):
            for elt in handler.type.elts:
                if isinstance(elt, ast.Name) and elt.id == "ImportError":
                    return True
    return False


@register
def check_broken_optional_import(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect try/except ImportError blocks where the import was removed."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue

            # Only check try blocks that have an ImportError handler
            if not _has_importerror_handler(node):
                continue

            # Skip if try body has a real import
            if _try_body_has_import(node):
                continue

            # Flag if try body is empty
            if _try_body_is_empty(node):
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category="broken_optional_import",
                    file=str(py_file.relative_to(project_path)),
                    line=node.lineno,
                    message="try/except ImportError block has empty body — side-effect import was likely removed.",
                    suggestion="Restore the import statement inside the try block (e.g. `import module  # noqa: F401`).",
                ))
                continue

            # Flag if try body only has assignments (FLAG = True without import)
            if _try_body_only_assignments(node):
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category="broken_optional_import",
                    file=str(py_file.relative_to(project_path)),
                    line=node.lineno,
                    message="try/except ImportError block has assignments but no import — flag will always be True.",
                    suggestion="Add the import statement before the assignment (e.g. `import module  # noqa: F401` then `FLAG = True`).",
                ))
