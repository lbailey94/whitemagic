import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_ruby(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Basic Ruby hygiene: eval risks, global variables, debug prints, class variables."""
    for rb_file in file_index.files_by_extension(".rb"):
        try:
            content = rb_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                # TODO/FIXME comments
                if re.search(r"\bTODO\b|\bFIXME\b", stripped):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="ruby_todo",
                            file=str(rb_file.relative_to(project_path)),
                            line=i,
                            message="TODO/FIXME comment found.",
                            suggestion="Address before production or track in issue tracker.",
                        )
                    )
                continue

            # eval / instance_eval / class_eval
            for match in re.finditer(
                r"\b(eval|instance_eval|class_eval|module_eval)\s*\(", stripped
            ):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="ruby_eval",
                        file=str(rb_file.relative_to(project_path)),
                        line=i,
                        message=f"Dynamic code execution: {match.group(1)}().",
                        suggestion="Avoid executing code from strings; use static methods or define_method.",
                    )
                )

            # Global variables
            for match in re.finditer(r"\B\$(\w+)", stripped):
                name = match.group(1)
                # Skip special globals like $!, $?, $0, $$, etc.
                if len(name) > 1 and name not in {"stdin", "stdout", "stderr"}:
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="ruby_global_variable",
                            file=str(rb_file.relative_to(project_path)),
                            line=i,
                            message=f"Global variable ${name} may cause tight coupling.",
                            suggestion="Encapsulate state in a class or module.",
                        )
                    )

            # Debug prints
            for match in re.finditer(
                r"\b(puts|print|p|pp|debugger|binding\.pry|binding\.irb)\b", stripped
            ):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="ruby_debug_print",
                        file=str(rb_file.relative_to(project_path)),
                        line=i,
                        message=f"Debug statement: {match.group(1)}.",
                        suggestion="Remove or guard with a logger before production.",
                    )
                )

            if re.search(r"@@\w+", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="ruby_class_variable",
                        file=str(rb_file.relative_to(project_path)),
                        line=i,
                        message="Class variable (@@var) detected.",
                        suggestion="Prefer class-instance variables (@var inside class << self) to avoid inheritance surprises.",
                    )
                )
