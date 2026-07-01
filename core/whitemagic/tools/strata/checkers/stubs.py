import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _find_protocol_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    """Pre-compute line ranges of Protocol/runtime_checkable classes.
    Returns list of (start_line, end_line) tuples.
    """
    ranges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_protocol = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == "runtime_checkable":
                    is_protocol = True
                elif isinstance(dec, ast.Call):
                    if (
                        isinstance(dec.func, ast.Name)
                        and dec.func.id == "runtime_checkable"
                    ):
                        is_protocol = True
            if not is_protocol:
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Protocol":
                        is_protocol = True
                    elif isinstance(base, ast.Attribute) and base.attr == "Protocol":
                        is_protocol = True
            if is_protocol and hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                ranges.append((node.lineno, node.end_lineno))
    return ranges


def _is_inside_protocol(node: ast.AST, tree: ast.AST) -> bool:
    """Return True if the node is inside a class decorated with @runtime_checkable or inheriting from Protocol."""
    if not hasattr(node, "lineno"):
        return False
    # Use pre-computed ranges instead of walking tree per node
    if not hasattr(tree, "_protocol_ranges"):
        tree._protocol_ranges = _find_protocol_ranges(tree)  # type: ignore[attr-defined]
    node_line = node.lineno
    for start, end in tree._protocol_ranges:  # type: ignore[attr-defined]
        if start <= node_line <= end:
            return True
    return False


def _is_backward_compat_shim(node: ast.FunctionDef, tree: ast.AST) -> bool:
    """Return True for methods in backward-compatibility shim classes."""
    # Walk up to enclosing class
    for parent in ast.walk(tree):
        if isinstance(parent, ast.ClassDef):
            if (
                hasattr(node, "lineno")
                and hasattr(parent, "lineno")
                and hasattr(parent, "end_lineno")
            ):
                if parent.lineno <= node.lineno <= parent.end_lineno:
                    if (
                        parent.body
                        and isinstance(parent.body[0], ast.Expr)
                        and isinstance(parent.body[0].value, ast.Constant)
                        and isinstance(parent.body[0].value.value, str)
                    ):
                        doc = parent.body[0].value.value.lower()
                        if any(
                            k in doc
                            for k in (
                                "shim",
                                "backward compat",
                                "fallback",
                                "deprecated",
                                "historical",
                            )
                        ):
                            return True
    return False


def _is_intentional_noop(node: ast.FunctionDef) -> bool:
    """Return True for functions whose docstring explicitly marks them as intentional no-ops."""
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        doc = node.body[0].value.value.lower()
        if any(
            k in doc
            for k in (
                "intentional no-op",
                "no-op placeholder",
                "not yet re-wired",
                "deferred feature",
            )
        ):
            return True
    return False


@register
def check_structural_stubs(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Find methods/functions that are structurally complete but do nothing."""
    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        rel_path = str(py_file.relative_to(project_path))
        # Skip plugin base files entirely — hooks are intentional empty overrides
        if _is_plugin_base_file(rel_path, tree) and (
            "plugin" in rel_path and "base" in rel_path
        ):
            continue
        # Skip CLI modules entirely — Click commands are intentionally scaffold-shaped
        if _is_cli_module(rel_path):
            continue
        is_cli_file = _is_cli_module(rel_path)
        in_plugin_base = _is_plugin_base_file(rel_path, tree)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip abstract methods — their empty bodies are intentional
                if any(
                    (isinstance(dec, ast.Name) and dec.id == "abstractmethod")
                    or (isinstance(dec, ast.Attribute) and dec.attr == "abstractmethod")
                    for dec in node.decorator_list
                ):
                    continue
                # Skip Protocol methods (typing.Protocol uses ... as body)
                if _is_inside_protocol(node, tree):
                    continue
                # Skip harmless __init__ with only pass (no state to initialize)
                if (
                    node.name == "__init__"
                    and len(node.body) == 1
                    and isinstance(node.body[0], ast.Pass)
                ):
                    continue
                if _is_stub_body(node.body):
                    line_num = node.lineno
                    name = node.name
                    desc = (
                        "Empty async function"
                        if isinstance(node, ast.AsyncFunctionDef)
                        else "Empty function body"
                    )

                    if is_cli_file and _is_cli_scaffold(node):
                        severity = FindingSeverity.WARNING
                        category = "cli_scaffold"
                        suggestion = "CLI group scaffold — intentional if this registers subcommands."
                    elif in_plugin_base and _is_plugin_hook(node):
                        severity = FindingSeverity.WARNING
                        category = "plugin_hook"
                        suggestion = "Plugin hook — intentional if subclasses override. Consider @abstractmethod."
                    elif _is_backward_compat_shim(node, tree):
                        severity = FindingSeverity.WARNING
                        category = "compat_shim"
                        suggestion = "Backward-compatibility shim — intentional no-op."
                    elif _is_intentional_noop(node):
                        severity = FindingSeverity.WARNING
                        category = "intentional_noop"
                        suggestion = "Intentional no-op — documented placeholder for deferred feature."
                    else:
                        severity = FindingSeverity.ERROR
                        category = "structural_stub"
                        suggestion = "Either implement the function or replace with `raise NotImplementedError('TODO: reason')`"

                    findings.append(
                        Finding(
                            severity=severity,
                            category=category,
                            file=rel_path,
                            line=line_num,
                            message=f"{desc}: '{name}' appears complete but does nothing. More dangerous than TODO.",
                            suggestion=suggestion,
                        )
                    )


def _is_cli_module(rel_path: str) -> bool:
    """Return True for files that look like CLI command modules."""
    return (
        "cli_" in rel_path
        or rel_path.endswith("_cli.py")
        or "commands/" in rel_path
        or "/cli/" in rel_path
        or rel_path.endswith("_commands.py")
    )


def _is_cli_scaffold(node: ast.FunctionDef) -> bool:
    """Return True for CLI group functions with trivial bodies (no args, pass/return None)."""
    if node.args.args or node.args.posonlyargs or node.args.kwonlyargs:
        return False
    # Body must be pure stub (pass or return None/constant)
    effective = []
    for stmt in node.body:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        effective.append(stmt)
    if not effective:
        return True
    if len(effective) == 1:
        s = effective[0]
        if isinstance(s, ast.Pass):
            return True
        if isinstance(s, ast.Return) and s.value is None:
            return True
    return False


def _is_plugin_base_file(rel_path: str, tree: ast.AST) -> bool:
    """Return True if this file appears to be a plugin base class module."""
    if "plugin" in rel_path.lower() or "base" in rel_path.lower():
        return True
    if isinstance(tree, ast.Module) and tree.body:
        first = tree.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            doc = first.value.value.lower()
            if "plugin" in doc or "base class" in doc or "abstract" in doc:
                return True
    return False


def _is_plugin_hook(node: ast.FunctionDef) -> bool:
    """Return True for methods that look like plugin hooks (self methods with docstring)."""
    if not node.args.args or node.args.args[0].arg != "self":
        return False
    # Must have a docstring explaining it's a hook
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        doc = node.body[0].value.value.lower()
        hook_keywords = (
            "hook",
            "override",
            "subclass",
            "plugin",
            "implement",
            "called when",
            "register",
            "event",
            "callback",
            "lifecycle",
            "notification",
            "handler",
        )
        if any(k in doc for k in hook_keywords):
            return True
    return False


def _is_stub_body(body: list[ast.stmt]) -> bool:
    """Check if a function body is effectively a stub."""
    if not body:
        return True

    # Filter out docstrings (Expr with Constant str)
    effective = []
    for stmt in body:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        effective.append(stmt)

    if not effective:
        return True

    if len(effective) == 1:
        stmt = effective[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            if stmt.value.value is ...:
                return True
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return True
            if isinstance(stmt.value, ast.Constant):
                val = stmt.value.value
                # type() check excludes bool (False==0, True==1 in Python)
                if type(val) in (type(None), type(...), str, int, list, dict):
                    if val in (None, ..., "", 0, [], {}):
                        return True
            if isinstance(stmt.value, ast.List) and not stmt.value.elts:
                return True
            if isinstance(stmt.value, ast.Dict) and not stmt.value.keys:
                return True
    return False
