import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


def _strip_quoted_strings(line: str) -> str:
    """Remove string literals so regex checks don't match inside them."""
    line = re.sub(r'"(?:\\.|[^"\\])*"', '""', line)
    line = re.sub(r"'(?:\\.|[^'\\])*'", "''", line)
    return line


@register
def check_java(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Basic Java/Kotlin hygiene: debug prints, null risks, resource leaks."""
    for java_file in file_index.files_by_extension(".java", ".kt"):
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        ext = java_file.suffix.lower()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
            ):
                continue

            code_only = _strip_quoted_strings(stripped)

            # Debug prints
            if re.search(r"System\.(out|err)\.(print|println)", code_only):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="java_debug_print",
                        file=str(java_file.relative_to(project_path)),
                        line=i,
                        message="System.out.println debug print.",
                        suggestion="Use a logging framework (SLF4J, java.util.logging).",
                    )
                )

            # printStackTrace
            if re.search(r"\.printStackTrace\s*\(", code_only):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="java_print_stacktrace",
                        file=str(java_file.relative_to(project_path)),
                        line=i,
                        message="printStackTrace() should not reach production.",
                        suggestion="Log the exception through a proper logger.",
                    )
                )

            if ext == ".kt":
                # Kotlin !! operator
                if re.search(r"!!", code_only):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.WARNING,
                            category="kotlin_null_assertion",
                            file=str(java_file.relative_to(project_path)),
                            line=i,
                            message="Kotlin !! operator may throw NPE.",
                            suggestion="Use ?. safe call or explicit null check with ?: fallback.",
                        )
                    )

                # Kotlin println
                if re.search(r"\bprintln\s*\(", code_only):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="kotlin_debug_print",
                            file=str(java_file.relative_to(project_path)),
                            line=i,
                            message="Kotlin println debug print.",
                            suggestion="Use a logging framework.",
                        )
                    )

                # Kotlin TODO()
                if re.search(r"\bTODO\s*\(", code_only):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.ERROR,
                            category="kotlin_todo",
                            file=str(java_file.relative_to(project_path)),
                            line=i,
                            message="Kotlin TODO() detected.",
                            suggestion="Implement before production.",
                        )
                    )

            if ext == ".java":
                # Resource leak: classes implementing Closeable/AutoCloseable without try-with-resources
                resource_patterns = [
                    (r"new\s+FileInputStream\s*\(", "FileInputStream"),
                    (r"new\s+FileOutputStream\s*\(", "FileOutputStream"),
                    (r"new\s+Socket\s*\(", "Socket"),
                    (r"new\s+ServerSocket\s*\(", "ServerSocket"),
                    (r"new\s+BufferedReader\s*\(", "BufferedReader"),
                    (r"new\s+PrintWriter\s*\(", "PrintWriter"),
                ]
                for pattern, name in resource_patterns:
                    if re.search(pattern, code_only):
                        in_try_with_resources = False
                        for prev in lines[max(0, i - 11) : i]:
                            if "try(" in prev.replace(" ", ""):
                                in_try_with_resources = True
                                break
                        # Also accept if .close() appears in next 20 lines or finally in next 30
                        has_cleanup = False
                        for future in lines[i : min(len(lines), i + 30)]:
                            if ".close()" in future or "finally" in future:
                                has_cleanup = True
                                break
                        if not in_try_with_resources and not has_cleanup:
                            findings.append(
                                Finding(
                                    severity=FindingSeverity.INFO,
                                    category="java_resource_leak",
                                    file=str(java_file.relative_to(project_path)),
                                    line=i,
                                    message=f"{name} may leak if not closed.",
                                    suggestion="Use try-with-resources or ensure close() is called.",
                                )
                            )
