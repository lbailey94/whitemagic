import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity


@register
def check_swift(project_path: Path, file_index: FileIndex, findings: list[Finding]):
    """Basic Swift hygiene: force unwrap, implicitly unwrapped optionals, debug prints."""
    for swift_file in file_index.files_by_extension(".swift"):
        try:
            content = swift_file.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                if re.search(r"\bTODO\b|\bFIXME\b", stripped):
                    findings.append(
                        Finding(
                            severity=FindingSeverity.INFO,
                            category="swift_todo",
                            file=str(swift_file.relative_to(project_path)),
                            line=i,
                            message="TODO/FIXME comment found.",
                            suggestion="Address before production or track in issue tracker.",
                        )
                    )
                continue

            # Force unwrap (!)
            if re.search(r"[\w)]\s*!(?!=)", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="swift_force_unwrap",
                        file=str(swift_file.relative_to(project_path)),
                        line=i,
                        message="Force unwrap (!) may crash at runtime.",
                        suggestion="Use optional binding (if let / guard let) or nil-coalescing (??).",
                    )
                )

            # Implicitly unwrapped optional type
            if re.search(r":\s*\w+\s*!", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.WARNING,
                        category="swift_implicit_unwrap",
                        file=str(swift_file.relative_to(project_path)),
                        line=i,
                        message="Implicitly unwrapped optional may crash if nil.",
                        suggestion="Use a regular optional (?) and unwrap safely at use site.",
                    )
                )

            # Debug prints
            for match in re.finditer(r"\b(print|debugPrint|dump)\s*\(", stripped):
                findings.append(
                    Finding(
                        severity=FindingSeverity.INFO,
                        category="swift_debug_print",
                        file=str(swift_file.relative_to(project_path)),
                        line=i,
                        message=f"Debug print: {match.group(1)}().",
                        suggestion="Remove or replace with a logging framework (OSLog).",
                    )
                )
