import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from whitemagic.tools.strata.file_index import FileIndex

__all__ = ["SurveyReport"]


def _git_file_dates(project_path: Path) -> Dict[str, Optional[datetime]]:
    """Return the last commit timestamp for every tracked file."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H|%at", "--name-only"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}

    file_to_time: Dict[str, Optional[datetime]] = {}
    current_sha: Optional[str] = None
    current_time: Optional[datetime] = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "|" in stripped and len(stripped.split("|")) == 2:
            sha, ts_str = stripped.split("|", 1)
            if len(sha) == 40 and ts_str.isdigit():
                current_sha = sha
                try:
                    current_time = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                except ValueError:
                    current_time = None
                continue
        if current_sha is not None and "/" in stripped:
            # Only record the first (most recent) timestamp we see for each file
            if stripped not in file_to_time:
                file_to_time[stripped] = current_time

    return file_to_time


def _recent_commits_by_file(project_path: Path, days: int = 7) -> Dict[str, int]:
    """Count how many times each file was touched in the last N days."""
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    since_str = since.strftime("%Y-%m-%d")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_str}", "--pretty=format:", "--name-only"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}

    counts: Dict[str, int] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            counts[line] = counts.get(line, 0) + 1
    return counts


class SurveyReport:
    """Fast surface survey of a codebase using file metadata and git history."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.file_index = FileIndex(project_path)

    def _collect_files(self) -> List[Path]:
        files = []
        for p in self.project_path.rglob("*"):
            if p.is_file() and not self.file_index.should_skip(p):
                files.append(p)
        return files

    def _fingerprint_frameworks(self) -> List[str]:
        """Detect common framework/config fingerprints."""
        fingerprints = []
        checks = {
            "FastAPI": ("fastapi",),
            "Flask": ("flask",),
            "Django": ("django",),
            "React": ("react",),
            "Vue": ("vue",),
            "Rust/Cargo": ("Cargo.toml",),
            "Go modules": ("go.mod",),
            "Node.js": ("package.json",),
            "Pytest": ("pytest.ini", "pyproject.toml",),
            "Docker": ("Dockerfile", "docker-compose.yml",),
            "GitHub Actions": (".github/workflows",),
        }
        for name, markers in checks.items():
            for marker in markers:
                if (self.project_path / marker).exists():
                    fingerprints.append(name)
                    break
        return fingerprints

    def render(self) -> str:
        files = self._collect_files()
        lines: List[str] = [
            f"STRATA Surface Survey: {self.project_path.name}",
            "=" * 60,
            "",
        ]

        # Language distribution
        ext_counts: Dict[str, int] = {}
        for f in files:
            ext = f.suffix.lower() or "(no ext)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

        lines.append("📊 Language Distribution")
        lines.append("-" * 40)
        for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {ext}: {count}")
        lines.append("")

        # Largest files
        file_sizes = [(f, len(f.read_text(encoding="utf-8", errors="ignore").splitlines())) for f in files if f.suffix in {".py", ".rs", ".go", ".js", ".ts", ".c", ".cpp", ".java", ".sh"}]
        file_sizes.sort(key=lambda x: -x[1])
        if file_sizes:
            lines.append("🏔️  Largest Files (by line count)")
            lines.append("-" * 40)
            for f, size in file_sizes[:5]:
                lines.append(f"  {f.relative_to(self.project_path)}: {size} lines")
            lines.append("")

        # Git hot spots and cold storage
        last_commit = _git_file_dates(self.project_path)
        recent_counts = _recent_commits_by_file(self.project_path, days=7)

        if last_commit:
            hot = []
            cold = []
            now = datetime.now(timezone.utc)
            for rel_path, ts in last_commit.items():
                if ts is None:
                    continue
                age_days = (now - ts).days
                if age_days <= 7:
                    hot.append((rel_path, age_days))
                elif age_days >= 365:
                    cold.append((rel_path, age_days))

            if hot:
                lines.append("🔥 Hot Spots (touched in last 7 days)")
                lines.append("-" * 40)
                for rel_path, age in sorted(hot, key=lambda x: x[1]):
                    commit_count = recent_counts.get(rel_path, 0)
                    count_str = f" ({commit_count} commits)" if commit_count > 1 else ""
                    lines.append(f"  {rel_path}{count_str}")
                lines.append("")

            if cold:
                lines.append("🧊 Cold Storage (not touched in 1+ years)")
                lines.append("-" * 40)
                for rel_path, age in sorted(cold, key=lambda x: -x[1])[:10]:
                    lines.append(f"  {rel_path} ({age}d)")
                lines.append("")

        # Framework fingerprints
        fingerprints = self._fingerprint_frameworks()
        if fingerprints:
            lines.append("🔎 Diagnostic Artifacts Detected")
            lines.append("-" * 40)
            for fp in fingerprints:
                lines.append(f"  • {fp}")
            lines.append("")

        return "\n".join(lines)
