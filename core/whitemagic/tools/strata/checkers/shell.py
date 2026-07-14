import logging
import re
from pathlib import Path

from whitemagic.tools.strata.checkers import register
from whitemagic.tools.strata.file_index import FileIndex
from whitemagic.tools.strata.models import Finding, FindingSeverity

logger = logging.getLogger(__name__)

@register
def check_shell_scripts(
    project_path: Path, file_index: FileIndex, findings: list[Finding]
):
    """Basic shell script hygiene checks."""
    for sh_file in file_index.files_by_extension(".sh", ".bash"):
        _check_shell_file(project_path, sh_file, findings)

    # Also check extension-less files with shebang in root and scripts/
    for subdir in (project_path, project_path / "scripts", project_path / "bin"):
        if subdir.exists():
            for f in subdir.iterdir():
                if f.is_file() and not f.suffix and not file_index.should_skip(f):
                    try:
                        first = file_index.read_text(f).splitlines()[0]
                        if first.startswith("#!/") and (
                            "bash" in first or "sh" in first
                        ):
                            _check_shell_file(project_path, f, findings)
                    except (OSError, UnicodeDecodeError):
                        logger.debug("Ignored OSError, UnicodeDecodeError in shell.py:31")


def _check_shell_file(project_path: Path, sh_file: Path, findings: list[Finding]):
    try:
        content = sh_file.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return

    lines = content.splitlines()

    has_strict = any(
        re.search(r"\bset\s+-(\S*e\S*u\S*|\S*u\S*e\S*)", line) for line in lines
    )
    if not has_strict:
        findings.append(
            Finding(
                severity=FindingSeverity.INFO,
                category="shell_strict_mode",
                file=str(sh_file.relative_to(project_path)),
                line=1,
                message="Shell script lacks 'set -euo pipefail' strict mode.",
                suggestion="Add 'set -euo pipefail' near the top for safer scripts.",
            )
        )

    for i, line in enumerate(lines, 1):
        if re.search(r'["\']?~/', line) and not line.strip().startswith("#"):
            findings.append(
                Finding(
                    severity=FindingSeverity.WARNING,
                    category="shell_hardcoded_path",
                    file=str(sh_file.relative_to(project_path)),
                    line=i,
                    message=f"Hardcoded home path in shell script: {line.strip()[:60]}",
                    suggestion="Use $HOME or a configurable variable.",
                )
            )

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("sudo ") and not any(
            kw in stripped for kw in ("||", "&&", "if ", "then")
        ):
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="shell_sudo_unsafe",
                    file=str(sh_file.relative_to(project_path)),
                    line=i,
                    message="Bare 'sudo' without error checking.",
                    suggestion="Wrap sudo in 'if' or chain with '||' to handle failures.",
                )
            )

    # Unquoted variables (word splitting risk)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Match $VAR or ${VAR} not inside double quotes
        for match in re.finditer(r"\$(?:\w+|\{[^}]+\})", stripped):
            var = match.group(0)
            # Skip special vars and expansions that are commonly safe
            if var in {"$@", "$*", "$#", "$?", "$!", "$$", "$0", "$-"}:
                continue
            if re.search(r"\$\{?\w+\}?\[", stripped):
                continue
            prefix = stripped[: match.start()]
            suffix = stripped[match.end() :]
            if prefix.count('"') % 2 == 1 and suffix.count('"') % 2 == 1:
                continue
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="shell_unquoted_variable",
                    file=str(sh_file.relative_to(project_path)),
                    line=i,
                    message=f"Unquoted variable {var} may cause word splitting or glob expansion.",
                    suggestion=f'Use "{var}" to preserve whitespace and prevent globbing.',
                )
            )
            break  # One finding per line is enough

    # Backtick usage (legacy command substitution)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "`" in stripped:
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="shell_backtick",
                    file=str(sh_file.relative_to(project_path)),
                    line=i,
                    message="Backtick command substitution is deprecated.",
                    suggestion="Use $() instead for readability and nesting support.",
                )
            )
