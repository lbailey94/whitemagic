import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_javascript(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """JavaScript/TypeScript hygiene: debug logs, eval, new Function, innerHTML, unhandled promises."""
    for js_file in file_index.files_by_extension(".js", ".jsx", ".ts", ".tsx"):
        try:
            content = file_index.read_text(js_file)
        except (OSError, UnicodeDecodeError):
            continue

        lines = content.splitlines()
        in_error_boundary = False
        boundary_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Track error boundary scope
            if re.search(r"\b(componentDidCatch|catch\b|onError)\b", stripped):
                in_error_boundary = True
                boundary_depth = stripped.count("{") - stripped.count("}")
                if boundary_depth <= 0:
                    boundary_depth = 1
                continue

            if in_error_boundary:
                boundary_depth += stripped.count("{") - stripped.count("}")
                if boundary_depth <= 0:
                    in_error_boundary = False
                    boundary_depth = 0
                if "console.error" in stripped:
                    continue

            # console.log debug leftover
            for match in re.finditer(r"\bconsole\.(log|debug|warn|error)\s*\(", line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="js_debug_log",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message=f"Debug log statement: {match.group(0)[:-1]}",
                        suggestion="Remove debug logs before production.",
                    )
                )

            # eval() usage
            for match in re.finditer(r"\beval\s*\(", line):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="js_eval",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="eval() detected — security and performance risk.",
                        suggestion="Use JSON.parse, Function constructor, or safer alternatives.",
                    )
                )

            # new Function() — similar to eval
            if re.search(r"new\s+Function\s*\(", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="js_eval",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="new Function() detected — dynamic code execution risk.",
                        suggestion="Avoid executing code from strings; use static functions.",
                    )
                )

            # innerHTML / outerHTML assignment — XSS risk
            if re.search(r"\.(innerHTML|outerHTML)\s*=", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="js_innerhtml_xss",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="innerHTML/outerHTML assignment — potential XSS vector.",
                        suggestion="Use textContent or a sanitization library like DOMPurify.",
                    )
                )

            # Unhandled promise: .then() without .catch() on same line
            if (
                ".then(" in stripped
                and ".catch(" not in stripped
                and "await" not in stripped
            ):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="js_unhandled_promise",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="Promise chain lacks .catch() handler.",
                        suggestion="Add .catch() or wrap in try/await to handle rejections.",
                    )
                )

            # == instead of ===
            if re.search(r"\s==\s", stripped) and not re.search(r"\s===\s", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="js_loose_equality",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="Loose equality (==) may cause unexpected type coercion.",
                        suggestion="Use strict equality (===) for predictable comparisons.",
                    )
                )

            # var usage (prefer const/let)
            if re.search(r"\bvar\s+", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="js_var_usage",
                        file=str(js_file.relative_to(project_path)),
                        line=i,
                        message="var declaration detected.",
                        suggestion="Use const or let for block-scoped variables.",
                    )
                )
