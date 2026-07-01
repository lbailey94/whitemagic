import ast
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_protocol_dead_code(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Detect Protocol classes whose methods are never called (type-aware dead code)."""
    protocol_classes: dict[
        str, tuple[Path, int, list[str]]
    ] = {}  # class_name -> (file, line, methods)
    all_calls: set[str] = set()
    protocol_references: set[str] = (
        set()
    )  # classes referenced in isinstance or type annotations

    for py_file in file_index.python_files():
        if FileIndex.is_test_file(py_file):
            continue
        tree = file_index.get_ast(py_file)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_protocol = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Protocol":
                        is_protocol = True
                    elif isinstance(base, ast.Attribute) and base.attr == "Protocol":
                        is_protocol = True
                if is_protocol:
                    methods = []
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            methods.append(child.name)
                    protocol_classes[node.name] = (py_file, node.lineno, methods)

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    # isinstance(obj, SomeProtocol) or isinstance(obj, (A, B))
                    if len(node.args) >= 2:
                        for arg in node.args[1:]:
                            if isinstance(arg, ast.Name):
                                protocol_references.add(arg.id)
                            elif isinstance(arg, ast.Tuple):
                                for elt in arg.elts:
                                    if isinstance(elt, ast.Name):
                                        protocol_references.add(elt.id)
                # Also track regular function/method calls
                if isinstance(node.func, ast.Name):
                    all_calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    all_calls.add(node.func.attr)
            elif isinstance(node, ast.AnnAssign):
                # Type annotation like x: SomeProtocol
                if isinstance(node.annotation, ast.Name):
                    protocol_references.add(node.annotation.id)
                elif isinstance(node.annotation, ast.Subscript):
                    if isinstance(node.annotation.value, ast.Name):
                        protocol_references.add(node.annotation.value.id)
            elif isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                if node.returns and isinstance(node.returns, ast.Name):
                    protocol_references.add(node.returns.id)
                for arg in node.args.args + node.args.kwonlyargs:
                    if arg.annotation and isinstance(arg.annotation, ast.Name):
                        protocol_references.add(arg.annotation.id)

    for class_name, (file_path, line_num, methods) in protocol_classes.items():
        if class_name not in protocol_references and class_name not in all_calls:
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="dead_code",
                    file=str(file_path.relative_to(project_path)),
                    line=line_num,
                    message=f"Protocol '{class_name}' may be unused (never referenced in isinstance or type annotations).",
                    suggestion="Verify this Protocol is still needed or remove it.",
                )
            )
            continue

        for method_name in methods:
            if method_name.startswith("_"):
                continue
            if method_name in all_calls:
                continue
            # Common protocol methods that are often called implicitly
            if method_name in {
                "__iter__",
                "__enter__",
                "__exit__",
                "__len__",
                "__getitem__",
                "close",
                "read",
                "write",
                "flush",
                "send",
                "recv",
            }:
                continue
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="dead_code",
                    file=str(file_path.relative_to(project_path)),
                    line=line_num,
                    message=f"Protocol method '{class_name}.{method_name}' may be unused.",
                    suggestion="If part of a public interface, it may be called externally. Verify before removing.",
                )
            )
