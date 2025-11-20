"""
Smart START HERE Template System - Optimized session resumption.

Provides tiered templates for session resumption:
- 30-second resume (< 1K tokens)
- 2-minute deep dive (Tier 1)
- 5-minute full context (Tier 2)

Philosophy:
- Provide exactly the context needed, no more
- Progressive detail on-demand
- Fast re-entry to flow state

Based on Wu Xing principle: 水 (Water) - Efficiency through minimal resistance
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SessionSnapshot:
    """Snapshot of session state for quick resumption."""

    version: str
    phase: str
    current_focus: str
    next_action: str
    files_modified: List[str]
    decisions_made: List[str]
    open_questions: List[str]
    blockers: List[str]
    token_used: int
    token_remaining: int
    timestamp: datetime
    session_id: Optional[str] = None


@dataclass
class TemplateConfig:
    """Configuration for template generation."""

    project_name: str
    current_version: str
    memory_dir: Path
    include_metrics: bool = True
    include_history: bool = True
    max_recent_changes: int = 5


class StartHereTemplate:
    """
    Smart template generator for "START HERE" memories.

    Generates hierarchical templates optimized for quick session resumption.
    """

    # Template tiers and their token budgets
    TIERS = {
        "quick": {
            "name": "30-Second Resume",
            "token_budget": 1000,
            "sections": ["version", "phase", "next_action", "context_needed"],
        },
        "balanced": {
            "name": "2-Minute Deep Dive",
            "token_budget": 3000,
            "sections": [
                "version",
                "phase",
                "accomplishments",
                "next_action",
                "context_needed",
                "decisions",
                "files_modified",
            ],
        },
        "comprehensive": {
            "name": "5-Minute Full Context",
            "token_budget": 8000,
            "sections": [
                "version",
                "phase",
                "accomplishments",
                "next_action",
                "context_needed",
                "decisions",
                "files_modified",
                "open_questions",
                "blockers",
                "metrics",
                "history",
            ],
        },
    }

    def __init__(self, config: TemplateConfig):
        """
        Initialize template generator.

        Args:
            config: Template configuration
        """
        self.config = config

    def generate(
        self,
        snapshot: SessionSnapshot,
        tier: str = "quick",
        custom_sections: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a START HERE template.

        Args:
            snapshot: Current session snapshot
            tier: Template tier (quick, balanced, comprehensive)
            custom_sections: Override default sections

        Returns:
            Formatted START HERE template
        """
        if tier not in self.TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {list(self.TIERS.keys())}")

        tier_config = self.TIERS[tier]
        sections = custom_sections or tier_config["sections"]

        # Build template
        template_parts = []

        # Header
        template_parts.append(self._format_header(snapshot, tier_config["name"]))

        # Core sections
        if "version" in sections:
            template_parts.append(self._format_version(snapshot))

        if "phase" in sections:
            template_parts.append(self._format_phase(snapshot))

        if "accomplishments" in sections:
            template_parts.append(self._format_accomplishments(snapshot))

        if "next_action" in sections:
            template_parts.append(self._format_next_action(snapshot))

        if "context_needed" in sections:
            template_parts.append(self._format_context_needed(snapshot))

        if "decisions" in sections:
            template_parts.append(self._format_decisions(snapshot))

        if "files_modified" in sections:
            template_parts.append(self._format_files_modified(snapshot))

        if "open_questions" in sections:
            template_parts.append(self._format_open_questions(snapshot))

        if "blockers" in sections:
            template_parts.append(self._format_blockers(snapshot))

        if "metrics" in sections and self.config.include_metrics:
            template_parts.append(self._format_metrics(snapshot))

        if "history" in sections and self.config.include_history:
            template_parts.append(self._format_history())

        # Footer with tier navigation
        template_parts.append(self._format_footer(tier))

        return "\n\n".join(template_parts)

    def _format_header(self, snapshot: SessionSnapshot, tier_name: str) -> str:
        """Format template header."""
        timestamp_str = snapshot.timestamp.strftime("%Y-%m-%d %I:%M %p")

        return f"""# ▶️ START HERE: {snapshot.current_focus}

**Resume Point**: {tier_name}
**Date**: {timestamp_str}
**Version**: {snapshot.version}"""

    def _format_version(self, snapshot: SessionSnapshot) -> str:
        """Format version section."""
        return f"""## 📦 Current Version

**{snapshot.version}** - {snapshot.phase} phase"""

    def _format_phase(self, snapshot: SessionSnapshot) -> str:
        """Format phase section."""
        return f"""## 🎯 Current Phase

**{snapshot.phase}**

Focus: {snapshot.current_focus}"""

    def _format_accomplishments(self, snapshot: SessionSnapshot) -> str:
        """Format accomplishments section."""
        # This would be populated from recent changes
        return """## ✅ Recent Accomplishments

*Last session summary - load from delta tracker*"""

    def _format_next_action(self, snapshot: SessionSnapshot) -> str:
        """Format next action section."""
        return f"""## 🚀 Next Action

**Immediate**: {snapshot.next_action}

**Estimated effort**: TBD
**Files to modify**: {len(snapshot.files_modified)} files pending"""

    def _format_context_needed(self, snapshot: SessionSnapshot) -> str:
        """Format context section."""
        return f"""## 📚 Context Needed

**Load on start**:
- `mcp3_get_context(tier=1)` - Balanced context (~3K tokens)
- Direct file reads for: {', '.join(snapshot.files_modified[:3]) if snapshot.files_modified else 'None'}

**Load if needed**:
- `mcp3_get_context(tier=2)` - Full context (~10K tokens)
- Search for specific topics with `mcp3_search_memories()`"""

    def _format_decisions(self, snapshot: SessionSnapshot) -> str:
        """Format decisions section."""
        if not snapshot.decisions_made:
            return ""

        decisions_list = "\n".join([f"{i+1}. {d}" for i, d in enumerate(snapshot.decisions_made)])

        return f"""## 🤔 Key Decisions Made

{decisions_list}"""

    def _format_files_modified(self, snapshot: SessionSnapshot) -> str:
        """Format files modified section."""
        if not snapshot.files_modified:
            return ""

        files_list = "\n".join([f"- `{f}`" for f in snapshot.files_modified[:10]])
        more = len(snapshot.files_modified) - 10
        if more > 0:
            files_list += f"\n- *...and {more} more*"

        return f"""## 📝 Files Modified

{files_list}"""

    def _format_open_questions(self, snapshot: SessionSnapshot) -> str:
        """Format open questions section."""
        if not snapshot.open_questions:
            return ""

        questions_list = "\n".join([f"- {q}" for q in snapshot.open_questions])

        return f"""## ❓ Open Questions

{questions_list}"""

    def _format_blockers(self, snapshot: SessionSnapshot) -> str:
        """Format blockers section."""
        if not snapshot.blockers:
            return """## 🚧 Blockers

None! 🎉"""

        blockers_list = "\n".join([f"- {b}" for b in snapshot.blockers])

        return f"""## 🚧 Blockers

{blockers_list}"""

    def _format_metrics(self, snapshot: SessionSnapshot) -> str:
        """Format metrics section."""
        token_pct = (snapshot.token_used / (snapshot.token_used + snapshot.token_remaining)) * 100

        return f"""## 📊 Session Metrics

**Tokens**: {snapshot.token_used:,} / {snapshot.token_used + snapshot.token_remaining:,} ({token_pct:.1f}% used)
**Remaining**: {snapshot.token_remaining:,} tokens ({100-token_pct:.1f}%)"""

    def _format_history(self) -> str:
        """Format recent history section."""
        return f"""## 📜 Recent History

*See consolidated memories for recent versions:*
- Search: `mcp3_search_memories(query="{self.config.current_version}")`
- Or: Direct read of version-specific memories"""

    def _format_footer(self, tier: str) -> str:
        """Format template footer with tier navigation."""
        nav_hints = []

        if tier == "quick":
            nav_hints.append("💡 **Need more context?** Load Tier 1: `mcp3_get_context(tier=1)`")
        elif tier == "balanced":
            nav_hints.append("💡 **Need full context?** Load Tier 2: `mcp3_get_context(tier=2)`")
        elif tier == "comprehensive":
            nav_hints.append("💡 **This is full context.** Ready to proceed!")

        nav_hints.append('🔍 **Specific question?** Use `mcp3_search_memories(query="...")`')

        return "\n".join(nav_hints) + "\n\n---\n\n**Status**: Ready to resume 🌸"

    def generate_frontmatter(self, snapshot: SessionSnapshot) -> Dict[str, Any]:
        """
        Generate frontmatter for the START HERE memory.

        Args:
            snapshot: Session snapshot

        Returns:
            Dictionary of frontmatter fields
        """
        tags = [
            "start-here",
            f"v{snapshot.version}",
            snapshot.phase.lower().replace(" ", "-"),
            "resume-point",
        ]

        if snapshot.session_id:
            tags.append(f"session-{snapshot.session_id}")

        return {
            "title": f"START HERE: {snapshot.current_focus}",
            "created": snapshot.timestamp.isoformat(),
            "tags": tags,
            "version": snapshot.version,
            "phase": snapshot.phase,
            "next_action": snapshot.next_action,
            "token_used": snapshot.token_used,
            "token_remaining": snapshot.token_remaining,
        }

    def save_template(
        self, snapshot: SessionSnapshot, tier: str = "quick", output_path: Optional[Path] = None
    ) -> Path:
        """
        Generate and save a START HERE template.

        Args:
            snapshot: Session snapshot
            tier: Template tier
            output_path: Where to save (defaults to memory/short_term/)

        Returns:
            Path where template was saved
        """
        # Generate template
        content = self.generate(snapshot, tier)
        frontmatter = self.generate_frontmatter(snapshot)

        # Format full file with frontmatter
        frontmatter_str = "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list):
                frontmatter_str += f"{key}: {', '.join(value)}\n"
            else:
                frontmatter_str += f"{key}: {value}\n"
        frontmatter_str += "---\n\n"

        full_content = frontmatter_str + content

        # Determine output path
        if output_path is None:
            timestamp = snapshot.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_start_here_{snapshot.version.replace('.', '_')}.md"
            output_path = self.config.memory_dir / "short_term" / filename

        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_content, encoding="utf-8")

        return output_path


def create_start_here_memory(
    version: str,
    phase: str,
    current_focus: str,
    next_action: str,
    memory_dir: Path,
    project_name: str = "WhiteMagic",
    tier: str = "quick",
    **kwargs,
) -> Path:
    """
    Convenience function to create a START HERE memory.

    Args:
        version: Current version
        phase: Current phase
        current_focus: What's the current focus
        next_action: What to do next
        memory_dir: Memory directory
        project_name: Project name
        tier: Template tier (quick, balanced, comprehensive)
        **kwargs: Additional snapshot fields

    Returns:
        Path to created memory file

    Example:
        >>> path = create_start_here_memory(
        ...     version="2.6.5",
        ...     phase="Phase 1: Meta-Optimization",
        ...     current_focus="Hierarchical workspace loading",
        ...     next_action="Implement symbolic reasoning module",
        ...     memory_dir=Path("memory"),
        ...     tier="quick"
        ... )
    """
    # Create snapshot
    snapshot = SessionSnapshot(
        version=version,
        phase=phase,
        current_focus=current_focus,
        next_action=next_action,
        files_modified=kwargs.get("files_modified", []),
        decisions_made=kwargs.get("decisions_made", []),
        open_questions=kwargs.get("open_questions", []),
        blockers=kwargs.get("blockers", []),
        token_used=kwargs.get("token_used", 0),
        token_remaining=kwargs.get("token_remaining", 200000),
        timestamp=kwargs.get("timestamp", datetime.now()),
        session_id=kwargs.get("session_id"),
    )

    # Create config
    config = TemplateConfig(
        project_name=project_name, current_version=version, memory_dir=memory_dir
    )

    # Generate template
    template_gen = StartHereTemplate(config)
    return template_gen.save_template(snapshot, tier)
