"""Robust except:pass fixer using AST for correct insertion points."""
import ast
import re
from pathlib import Path


def get_except_type(node):
    if node.type is None:
        return None
    if isinstance(node.type, ast.Name):
        return node.type.id
    if isinstance(node.type, ast.Tuple):
        parts = []
        for e in node.type.elts:
            if isinstance(e, ast.Name):
                parts.append(e.id)
        return ", ".join(parts) if parts else "Exception"
    return "Exception"


def find_logger_insert_point(tree, lines):
    """Find line index where logger = logging.getLogger(__name__) should go.
    Insert after module docstring + all imports, before first real statement."""
    body = tree.body
    insert_after = 0

    for i, stmt in enumerate(body):
        if i == 0 and isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            insert_after = stmt.end_lineno - 1
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            insert_after = stmt.end_lineno - 1
            continue
        break

    idx = insert_after + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    return idx


def fix_file(path: Path) -> list:
    src = path.read_text()
    if not src.strip():
        return []

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ["SYNTAX ERROR in {}".format(path)]

    blocks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if isinstance(node.body, list) and len(node.body) == 1:
                if isinstance(node.body[0], ast.Pass):
                    exc_type = get_except_type(node)
                    blocks.append({
                        "lineno": node.lineno,
                        "col_offset": node.col_offset,
                        "exc_type": exc_type or "",
                        "is_bare": node.type is None,
                    })

    if not blocks:
        return []

    changes = []
    has_logger = "logging.getLogger" in src
    has_import_logging = bool(re.search(r"^import logging\b", src, re.MULTILINE))

    lines = src.split("\n")

    if not has_import_logging or not has_logger:
        insert_idx = find_logger_insert_point(tree, lines)

        if not has_import_logging:
            lines.insert(insert_idx, "import logging")
            insert_idx += 1
            changes.append("Added import logging")

        if not has_logger:
            lines.insert(insert_idx, "logger = logging.getLogger(__name__)")
            insert_idx += 1
            lines.insert(insert_idx, "")
            changes.append("Added logger = logging.getLogger(__name__)")

    src_updated = "\n".join(lines)
    try:
        tree = ast.parse(src_updated)
    except SyntaxError:
        return ["PARSE ERROR after insertion in {} - skipped".format(path)]

    blocks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if isinstance(node.body, list) and len(node.body) == 1:
                if isinstance(node.body[0], ast.Pass):
                    exc_type = get_except_type(node)
                    blocks.append({
                        "lineno": node.lineno,
                        "col_offset": node.col_offset,
                        "exc_type": exc_type or "",
                        "is_bare": node.type is None,
                    })

    for block in reversed(blocks):
        idx = block["lineno"] - 1
        if idx >= len(lines):
            continue

        line = lines[idx]
        indent = " " * block["col_offset"]
        exc_str = block["exc_type"] or "Exception"
        fname = path.name
        lineno = block["lineno"]
        debug_msg = 'logger.debug("Ignored {} in {}:{}")'.format(exc_str, fname, lineno)

        if block["is_bare"]:
            lines[idx] = re.sub(r"except\s*:", "except Exception:", line, count=1)
            line = lines[idx]
            exc_str = "Exception"

        # Inline: except X: pass  (possibly with trailing comment)
        if re.search(r":\s*pass\b", line):
            lines[idx] = re.sub(r":\s*pass.*$", ": " + debug_msg, line)
            changes.append("Line {}: inline except {}: pass -> logger.debug()".format(lineno, exc_str))
        else:
            # Multiline: find the pass line (may have trailing comment)
            for j in range(idx + 1, min(idx + 10, len(lines))):
                stripped = lines[j].strip()
                if stripped == "pass" or stripped.startswith("pass  #") or stripped.startswith("pass #"):
                    lines[j] = "{}    {}".format(indent, debug_msg)
                    changes.append("Line {}: except {}: pass -> logger.debug()".format(lineno, exc_str))
                    break

    path.write_text("\n".join(lines))
    return changes


if __name__ == "__main__":
    root = Path("core/whitemagic")
    all_changes = {}
    total_fixed = 0

    for py in root.rglob("*.py"):
        if "__pycache__" in str(py) or "_archived" in str(py):
            continue
        changes = fix_file(py)
        if changes:
            all_changes[str(py)] = changes
            if not any("ERROR" in c for c in changes):
                total_fixed += len([c for c in changes if "Line" in c])

    print("Files modified: {}".format(len(all_changes)))
    print("Total except:pass blocks fixed: {}".format(total_fixed))
    print()
    for f, changes in sorted(all_changes.items()):
        print("{}:".format(f))
        for c in changes:
            print("  {}".format(c))
