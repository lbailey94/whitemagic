"""Campaign Loader — Markdown-driven campaign doctrine system.

Parses campaign specifications from markdown files with YAML-style frontmatter.
Each campaign defines objectives, victory conditions, targets, and deployment
parameters for shadow clone army operations.

No compromise. No shortcuts. No half-implementations. Complete victory or nothing.

Campaign Format:
    ---
    name: Campaign Name
    codename: IL001
    army: alpha|beta|gamma
    type: security_scan|batch_transform|fix_and_verify|dedup|discovery|stress_test
    priority: 1
    clone_count: 10000
    strategies: [adversarial, analytical, chain_of_thought]
    category: security
    phase: immediate|foundation|infrastructure|intelligence
    source: "Origin document or operation"
    column_size: 50000
    ---

    # Campaign Name

    ## Objective
    What to accomplish.

    ## Victory Conditions
    - [ ] Condition 1 (MUST be met — no compromise)
    - [ ] Condition 2

    ## Targets
    | File | Line | Type |
    |------|------|------|
    | path/to/file.py | 42 | sql_injection |

    ## Strategy
    1. Step one
    2. Step two

    ## Verification
    How to confirm complete victory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VictoryCondition:
    """A single victory condition — ALL must be met for campaign success."""
    description: str
    met: bool = False
    check_cmd: str | None = None

    def __str__(self):
        mark = "\u2705" if self.met else "\u274c"
        return f"{mark} {self.description}"


@dataclass
class Target:
    """A specific target (file, line, item) for the campaign."""
    file: str = ""
    line: int | None = None
    type: str = ""
    description: str = ""


@dataclass
class Campaign:
    """A complete campaign specification loaded from markdown."""

    # Identity
    name: str = ""
    codename: str = ""
    source_file: Path | None = None

    # Deployment parameters
    army: str = "alpha"
    type: str = "discovery"
    priority: int = 99
    clone_count: int = 10000
    strategies: list[str] = field(default_factory=lambda: ["analytical", "synthesis"])
    category: str = "general"
    phase: str = "immediate"
    source: str = ""
    column_size: int = 50000

    # Content
    description: str = ""
    victory_conditions: list[VictoryCondition] = field(default_factory=list)
    targets: list[Target] = field(default_factory=list)
    strategy_steps: list[str] = field(default_factory=list)
    verification: str = ""
    raw_body: str = ""

    # Runtime state
    status: str = "pending"
    elapsed: float = 0.0
    clones_deployed: int = 0
    findings_count: int = 0
    findings: list[dict] = field(default_factory=list)
    result: dict = field(default_factory=dict)

    @property
    def victory_met(self) -> bool:
        """All victory conditions must be met for complete victory."""
        if not self.victory_conditions:
            return False
        return all(vc.met for vc in self.victory_conditions)

    @property
    def victory_progress(self) -> str:
        if not self.victory_conditions:
            return "no conditions defined"
        met = sum(1 for vc in self.victory_conditions if vc.met)
        total = len(self.victory_conditions)
        pct = int(met / total * 100) if total else 0
        return f"{met}/{total} ({pct}%)"

    def army_label(self) -> str:
        labels = {
            "alpha": "10K \u2014 Consensus",
            "beta": "50-100K \u2014 Map-Reduce",
            "gamma": "100K+ \u2014 Brute-Force",
        }
        return labels.get(self.army, self.army)

    def mark_victory(self, index: int, met: bool = True):
        """Mark a specific victory condition as met/unmet."""
        if 0 <= index < len(self.victory_conditions):
            self.victory_conditions[index].met = met

    def mark_all_containing(self, substring: str, met: bool = True):
        """Mark all victory conditions containing substring."""
        for vc in self.victory_conditions:
            if substring.lower() in vc.description.lower():
                vc.met = met


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-style frontmatter delimited by ---."""
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
    if not m:
        return {}, text

    fm_text = m.group(1)
    body = text[m.end():]

    meta: dict[str, Any] = {}
    for line in fm_text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        kv = line.split(':', 1)
        if len(kv) != 2:
            continue

        key = kv[0].strip()
        val = kv[1].strip()

        # Parse lists [a, b, c]
        if val.startswith('[') and val.endswith(']'):
            items = [s.strip().strip('"').strip("'") for s in val[1:-1].split(',')]
            meta[key] = [s for s in items if s]
        # Parse integers
        elif val.isdigit():
            meta[key] = int(val)
        # Parse quoted strings
        elif (val.startswith('"') and val.endswith('"')) or \
             (val.startswith("'") and val.endswith("'")):
            meta[key] = val[1:-1]
        else:
            meta[key] = val

    return meta, body


def _extract_section(body: str, heading: str) -> str:
    """Extract content under a specific ## heading."""
    pattern = rf'^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)'
    m = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _parse_victory_conditions(body: str) -> list[VictoryCondition]:
    """Parse victory conditions from ## Victory Conditions section."""
    section = _extract_section(body, "Victory Conditions")
    if not section:
        return []

    conditions = []
    for line in section.split('\n'):
        line = line.strip()
        m = re.match(r'^-\s*\[([ xX])\]\s*(.*)', line)
        if m:
            met = m.group(1).lower() == 'x'
            desc = m.group(2).strip()
            # Check for inline verification: desc (check: command)
            check_cmd = None
            cm = re.search(r'\(check:\s*(.+?)\)\s*$', desc)
            if cm:
                check_cmd = cm.group(1)
                desc = desc[:cm.start()].strip()
            conditions.append(VictoryCondition(
                description=desc, met=met, check_cmd=check_cmd,
            ))

    return conditions


def _parse_targets(body: str) -> list[Target]:
    """Parse targets from ## Targets section (table or list format)."""
    section = _extract_section(body, "Targets")
    if not section:
        return []

    targets = []

    # Try table format: | File | Line | Type |
    table_rows = re.findall(
        r'^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|',
        section, re.MULTILINE,
    )
    for row in table_rows:
        file_path, line, desc = row
        if file_path.startswith('-') or file_path.strip().lower() == 'file':
            continue
        line_num = int(line.strip()) if line.strip().isdigit() else None
        targets.append(Target(
            file=file_path.strip(), line=line_num,
            type=desc.strip(), description=desc.strip(),
        ))

    # Also try list format: - `path/to/file.py:42` — description
    if not targets:
        for line in section.split('\n'):
            m = re.match(r'^[-*]\s+`?([^`\s:]+):?(\d+)?`?\s*[—\-]?\s*(.*)', line.strip())
            if m:
                targets.append(Target(
                    file=m.group(1),
                    line=int(m.group(2)) if m.group(2) else None,
                    description=m.group(3).strip(),
                ))

    return targets


def _parse_strategy_steps(body: str) -> list[str]:
    """Parse numbered strategy steps from ## Strategy section."""
    section = _extract_section(body, "Strategy")
    if not section:
        return []

    steps = []
    for line in section.split('\n'):
        line = line.strip()
        m = re.match(r'^(\d+)\.\s+(.*)', line)
        if m:
            steps.append(m.group(2))
    return steps


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_campaign(path: Path) -> Campaign:
    """Load a single campaign from a markdown file."""
    text = path.read_text(errors='replace')
    meta, body = _parse_frontmatter(text)

    return Campaign(
        name=meta.get('name', path.stem),
        codename=meta.get('codename', path.stem),
        source_file=path,
        army=meta.get('army', 'alpha'),
        type=meta.get('type', 'discovery'),
        priority=int(meta.get('priority', 99)),
        clone_count=int(meta.get('clone_count', 10000)),
        strategies=meta.get('strategies', ['analytical', 'synthesis']),
        category=meta.get('category', 'general'),
        phase=meta.get('phase', 'immediate'),
        source=meta.get('source', ''),
        column_size=int(meta.get('column_size', 50000)),
        description=_extract_section(body, 'Objective') or _extract_section(body, 'Description') or "",
        victory_conditions=_parse_victory_conditions(body),
        targets=_parse_targets(body),
        strategy_steps=_parse_strategy_steps(body),
        verification=_extract_section(body, 'Verification'),
        raw_body=body,
    )


def load_all_campaigns(
    campaign_dir: Path,
    phase_filter: str | None = None,
    army_filter: str | None = None,
    category_filter: str | None = None,
) -> list[Campaign]:
    """Load all campaigns from directory, sorted by priority.

    Args:
        campaign_dir: Path to campaigns/ directory
        phase_filter: Only load campaigns in this phase
        army_filter: Only load campaigns for this army
        category_filter: Only load campaigns in this category

    Returns:
        List of campaigns sorted by priority (1 = highest)
    """
    if not campaign_dir.exists():
        return []

    campaigns = []
    for md_file in sorted(campaign_dir.glob("*.md")):
        if md_file.name.startswith("_") or md_file.name == "README.md":
            continue
        try:
            campaign = load_campaign(md_file)

            if phase_filter and campaign.phase != phase_filter:
                continue
            if army_filter and campaign.army != army_filter:
                continue
            if category_filter and campaign.category != category_filter:
                continue

            campaigns.append(campaign)
        except Exception as e:
            print(f"  Warning: Failed to load {md_file.name}: {e}")

    campaigns.sort(key=lambda c: (c.priority, c.codename))
    return campaigns


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def campaign_summary_table(campaigns: list[Campaign]) -> str:
    """Generate a markdown summary table of loaded campaigns."""
    lines = [
        "| # | Codename | Campaign | Army | Clones | Type | Priority | Conditions | Status |",
        "|---|----------|----------|------|--------|------|----------|------------|--------|",
    ]
    for i, c in enumerate(campaigns, 1):
        icon = {"pending": "⏳", "in_progress": "🔄", "complete": "✅",
                "failed": "❌", "partial": "⚠️"}.get(c.status, "?")
        lines.append(
            f"| {i} | {c.codename} | {c.name[:40]} | {c.army} | "
            f"{c.clone_count:,} | {c.type} | P{c.priority} | "
            f"{c.victory_progress} | {icon} |"
        )
    return '\n'.join(lines)


def victory_report(campaigns: list[Campaign]) -> str:
    """Generate a victory conditions report."""
    lines = ["# Victory Conditions Report\n"]
    for c in campaigns:
        status = "VICTORY" if c.victory_met else "INCOMPLETE"
        lines.append(f"## {c.codename}: {c.name} — {status}")
        lines.append(f"Progress: {c.victory_progress}\n")
        for vc in c.victory_conditions:
            lines.append(f"  {vc}")
        lines.append("")
    return '\n'.join(lines)
