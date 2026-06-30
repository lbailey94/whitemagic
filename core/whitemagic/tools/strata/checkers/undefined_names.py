"""Detect undefined names — variables used but never assigned or imported.

This catches a common class of bug where a function references a name
that was never defined in the current scope, typically due to:
- Missing import (forgot to import a utility function)
- Typo in variable name
- Copy-paste error (copied code referencing names from another module)

This is a real correctness checker, not a style issue. Undefined names
will raise NameError at runtime.

Uses a simplified scope analysis: collects all assigned names, imported
names, function/class arguments, and comprehension targets per scope,
then checks if every Name Load has a matching definition.

Limitations:
- Does not track cross-module star imports (from X import *)
- Does not track __getattr__ or dynamic attributes
- Nested function scopes are analyzed independently (may produce false
  positives for closures referencing outer scopes — these are filtered)
"""

import ast
import builtins
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

# Builtins that are always available
_BUILTINS = frozenset(dir(builtins)) | frozenset({"__file__", "__name__", "__package__", "__doc__", "__spec__"})


def _collect_definitions(scope_node: ast.AST) -> set[str]:
    """Collect all names defined in a scope (assignments, imports, args, defs)."""
    defined = set()
    for node in ast.walk(scope_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            defined.add(elt.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
            # Arguments are defined within the function scope
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    defined.add(arg.arg)
                if node.args.vararg:
                    defined.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                defined.add(name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue  # Can't track star imports
                name = alias.asname or alias.name
                defined.add(name)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
        elif isinstance(node, ast.comprehension):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    defined.add(item.optional_vars.id)
        elif isinstance(node, ast.Global):
            for name in node.names:
                defined.add(name)
        elif isinstance(node, ast.Nonlocal):
            for name in node.names:
                defined.add(name)
    return defined


@register
def check_undefined_names(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Detect names that are used but never defined or imported."""
    for py_file in file_index.python_files():
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        # Collect all names defined at module level
        module_defined = _collect_definitions(tree)
        module_defined |= _BUILTINS

        # Check module-level Name loads
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # Handled below
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                    if sub.id not in module_defined:
                        findings.append(Finding(
                            severity=FindingSeverity.ERROR,
                            category="undefined_name",
                            file=str(py_file.relative_to(project_path)),
                            line=sub.lineno,
                            message=f"Undefined name `{sub.id}` — not imported or assigned in this scope.",
                            suggestion=f"Add `import {sub.id}` or check for a typo.",
                        ))

        # Check function-level Name loads (functions can see module scope)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_defined = _collect_definitions(node) | module_defined
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        if sub.id not in func_defined:
                            # Skip if it's a method name being accessed on an object
                            findings.append(Finding(
                                severity=FindingSeverity.ERROR,
                                category="undefined_name",
                                file=str(py_file.relative_to(project_path)),
                                line=sub.lineno,
                                message=f"Undefined name `{sub.id}` — not imported or assigned in this scope.",
                                suggestion=f"Add `import {sub.id}` or check for a typo.",
                            ))
