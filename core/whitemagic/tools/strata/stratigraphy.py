import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from whitemagic.tools.strata.models import Finding

__all__ = ["StratigraphyReport"]


def _git_blame_timestamp(project_path: Path, file_rel: str, line: int) -> Optional[datetime]:
    """Return the author timestamp for a specific line via git blame --porcelain."""
    try:
        result = subprocess.run(
            ["git", "blame", "-L", f"{line},{line}", "--porcelain", file_rel],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        for blame_line in result.stdout.splitlines():
            if blame_line.startswith("author-time "):
                timestamp = int(blame_line.split(" ", 1)[1])
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError, OSError):
        return None
    return None


class StratigraphyReport:
    """Group findings into archaeological layers based on git age."""

    LAYERS = [
        ("recent", "Recent Sediment (last 30 days)", 30),
        ("established", "Established Features (1–12 months)", 365),
        ("legacy", "Legacy Substrate (1+ years)", None),
    ]

    def __init__(self, project_path: Path, findings: List[Finding]):
        self.project_path = project_path
        self.findings = findings
        self._blame_cache: Dict[Tuple[str, int], Optional[datetime]] = {}

    def _age_days(self, finding: Finding) -> Optional[int]:
        if finding.line is None or not finding.file:
            return None
        key = (finding.file, finding.line)
        cached = self._blame_cache.get(key)
        if cached is None and key not in self._blame_cache:
            cached = _git_blame_timestamp(self.project_path, finding.file, finding.line)
            self._blame_cache[key] = cached
        if cached is None:
            return None
        delta = datetime.now(timezone.utc) - cached
        return delta.days

    def _layer_for(self, days: Optional[int]) -> str:
        if days is None:
            return "unknown"
        for key, _label, threshold in self.LAYERS:
            if threshold is None:
                return key
            if days <= threshold:
                return key
        return "legacy"

    def group(self) -> Dict[str, List[Finding]]:
        groups: Dict[str, List[Finding]] = {
            "recent": [],
            "established": [],
            "legacy": [],
            "unknown": [],
        }
        for finding in self.findings:
            days = self._age_days(finding)
            layer = self._layer_for(days)
            groups[layer].append(finding)
        return groups

    def render(self) -> str:
        groups = self.group()
        lines = [
            f"STRATA Stratigraphic Report: {self.project_path.name}",
            "=" * 60,
            "",
        ]

        total = len(self.findings)
        if total == 0:
            lines.append("No findings to stratify.")
            return "\n".join(lines)

        for key, label, _threshold in self.LAYERS:
            items = groups.get(key, [])
            if not items:
                continue
            lines.append(f"📂 {label} — {len(items)} finding(s)")
            lines.append("-" * 40)
            for f in items:
                icon = "🔴" if f.severity.name == "ERROR" else "🟡" if f.severity.name == "WARNING" else "🔵"
                loc = f":{f.line}" if f.line else ""
                age = self._age_days(f)
                age_str = f" ({age}d)" if age is not None else ""
                lines.append(f"  {icon} [{f.category}] {f.file}{loc}{age_str}")
                lines.append(f"     {f.message}")
            lines.append("")

        unknown = groups.get("unknown", [])
        if unknown:
            lines.append(f"📂 Unknown Age — {len(unknown)} finding(s)")
            lines.append("-" * 40)
            for f in unknown:
                icon = "🔴" if f.severity.name == "ERROR" else "🟡" if f.severity.name == "WARNING" else "🔵"
                loc = f":{f.line}" if f.line else ""
                lines.append(f"  {icon} [{f.category}] {f.file}{loc}")
                lines.append(f"     {f.message}")
            lines.append("")

        return "\n".join(lines)
