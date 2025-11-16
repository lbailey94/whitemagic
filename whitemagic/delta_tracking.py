"""
Delta-Based Session Summary Generator - Track changes, not redundancy.

Generates session summaries that focus on what changed rather than
re-describing everything. Dramatically reduces token usage for session
continuity.

Philosophy:
- Track deltas, not absolute state
- Emphasize changes over constants
- Efficient continuity through minimal information

Based on I Ching principle: 變 (Bian) - Change is the only constant
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import json
import hashlib


@dataclass
class FileChange:
    """Represents a change to a file."""
    
    path: str
    change_type: str  # created, modified, deleted
    lines_added: int = 0
    lines_removed: int = 0
    description: Optional[str] = None
    

@dataclass
class Decision:
    """Represents a decision made during the session."""
    
    decision: str
    reasoning: str
    alternatives_considered: List[str] = field(default_factory=list)
    timestamp: Optional[datetime] = None


@dataclass
class SessionDelta:
    """Delta (changes) for a session."""
    
    session_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    
    # What changed
    files_changed: List[FileChange] = field(default_factory=list)
    features_added: List[str] = field(default_factory=list)
    bugs_fixed: List[str] = field(default_factory=list)
    tests_added: List[str] = field(default_factory=list)
    docs_updated: List[str] = field(default_factory=list)
    
    # Decisions & insights
    decisions_made: List[Decision] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    patterns_discovered: List[str] = field(default_factory=list)
    
    # Metrics
    token_used: int = 0
    phases_completed: List[str] = field(default_factory=list)
    problems_solved: int = 0
    
    # Context
    blockers_added: List[str] = field(default_factory=list)
    blockers_resolved: List[str] = field(default_factory=list)
    questions_raised: List[str] = field(default_factory=list)
    questions_answered: List[str] = field(default_factory=list)
    

class DeltaTracker:
    """
    Tracks changes during a session to generate delta-based summaries.
    
    This class maintains session state and computes deltas (changes)
    rather than absolute state, minimizing token usage for summaries.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize delta tracker.
        
        Args:
            session_id: Unique session identifier (auto-generated if not provided)
        """
        self.session_id = session_id or self._generate_session_id()
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        # Track file changes
        self._file_states: Dict[str, str] = {}  # path -> content_hash
        self._file_changes: List[FileChange] = []
        
        # Track other changes
        self._features: List[str] = []
        self._bugs: List[str] = []
        self._tests: List[str] = []
        self._docs: List[str] = []
        self._decisions: List[Decision] = []
        self._insights: List[str] = []
        self._patterns: List[str] = []
        
        # Track context changes
        self._blockers_current: Set[str] = set()
        self._blockers_added: List[str] = []
        self._blockers_resolved: List[str] = []
        self._questions_current: Set[str] = set()
        self._questions_raised: List[str] = []
        self._questions_answered: List[str] = []
        
        # Track metrics
        self.token_used = 0
        self.phases_completed: List[str] = []
        self.problems_solved = 0
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]
        return f"session_{timestamp}_{random_suffix}"
    
    def track_file_change(
        self,
        file_path: str,
        change_type: str = "modified",
        lines_added: int = 0,
        lines_removed: int = 0,
        description: Optional[str] = None
    ) -> None:
        """
        Track a change to a file.
        
        Args:
            file_path: Path to the file
            change_type: Type of change (created, modified, deleted)
            lines_added: Number of lines added
            lines_removed: Number of lines removed
            description: Optional description of the change
        """
        change = FileChange(
            path=file_path,
            change_type=change_type,
            lines_added=lines_added,
            lines_removed=lines_removed,
            description=description
        )
        self._file_changes.append(change)
    
    def add_feature(self, feature: str) -> None:
        """Track a new feature added."""
        self._features.append(feature)
    
    def fix_bug(self, bug: str) -> None:
        """Track a bug fixed."""
        self._bugs.append(bug)
    
    def add_test(self, test: str) -> None:
        """Track a test added."""
        self._tests.append(test)
    
    def update_doc(self, doc: str) -> None:
        """Track a documentation update."""
        self._docs.append(doc)
    
    def make_decision(
        self,
        decision: str,
        reasoning: str,
        alternatives: Optional[List[str]] = None
    ) -> None:
        """
        Track a decision made.
        
        Args:
            decision: The decision made
            reasoning: Why this decision was made
            alternatives: What alternatives were considered
        """
        self._decisions.append(Decision(
            decision=decision,
            reasoning=reasoning,
            alternatives_considered=alternatives or [],
            timestamp=datetime.now()
        ))
    
    def add_insight(self, insight: str) -> None:
        """Track an insight gained."""
        self._insights.append(insight)
    
    def discover_pattern(self, pattern: str) -> None:
        """Track a pattern discovered."""
        self._patterns.append(pattern)
    
    def add_blocker(self, blocker: str) -> None:
        """Add a new blocker."""
        if blocker not in self._blockers_current:
            self._blockers_current.add(blocker)
            self._blockers_added.append(blocker)
    
    def resolve_blocker(self, blocker: str) -> None:
        """Resolve a blocker."""
        if blocker in self._blockers_current:
            self._blockers_current.remove(blocker)
            self._blockers_resolved.append(blocker)
    
    def raise_question(self, question: str) -> None:
        """Raise a new question."""
        if question not in self._questions_current:
            self._questions_current.add(question)
            self._questions_raised.append(question)
    
    def answer_question(self, question: str) -> None:
        """Answer a question."""
        if question in self._questions_current:
            self._questions_current.remove(question)
            self._questions_answered.append(question)
    
    def complete_phase(self, phase: str) -> None:
        """Mark a phase as completed."""
        self.phases_completed.append(phase)
    
    def solve_problem(self) -> None:
        """Increment problem solved counter."""
        self.problems_solved += 1
    
    def update_token_usage(self, tokens: int) -> None:
        """Update token usage."""
        self.token_used = tokens
    
    def get_delta(self) -> SessionDelta:
        """
        Get the session delta (all changes).
        
        Returns:
            SessionDelta containing all tracked changes
        """
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() / 60
        
        return SessionDelta(
            session_id=self.session_id,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_minutes=int(duration),
            files_changed=self._file_changes.copy(),
            features_added=self._features.copy(),
            bugs_fixed=self._bugs.copy(),
            tests_added=self._tests.copy(),
            docs_updated=self._docs.copy(),
            decisions_made=self._decisions.copy(),
            insights_gained=self._insights.copy(),
            patterns_discovered=self._patterns.copy(),
            token_used=self.token_used,
            phases_completed=self.phases_completed.copy(),
            problems_solved=self.problems_solved,
            blockers_added=self._blockers_added.copy(),
            blockers_resolved=self._blockers_resolved.copy(),
            questions_raised=self._questions_raised.copy(),
            questions_answered=self._questions_answered.copy(),
        )
    
    def generate_summary(self, format: str = "markdown") -> str:
        """
        Generate a delta-based summary.
        
        Args:
            format: Output format (markdown, json)
            
        Returns:
            Formatted summary
        """
        delta = self.get_delta()
        
        if format == "json":
            return json.dumps(self._delta_to_dict(delta), indent=2)
        elif format == "markdown":
            return self._delta_to_markdown(delta)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _delta_to_dict(self, delta: SessionDelta) -> Dict[str, Any]:
        """Convert delta to dictionary."""
        return {
            "session_id": delta.session_id,
            "duration_minutes": delta.duration_minutes,
            "changes": {
                "files": [
                    {
                        "path": fc.path,
                        "type": fc.change_type,
                        "lines_added": fc.lines_added,
                        "lines_removed": fc.lines_removed,
                        "description": fc.description
                    }
                    for fc in delta.files_changed
                ],
                "features": delta.features_added,
                "bugs": delta.bugs_fixed,
                "tests": delta.tests_added,
                "docs": delta.docs_updated,
            },
            "decisions": [
                {
                    "decision": d.decision,
                    "reasoning": d.reasoning,
                    "alternatives": d.alternatives_considered
                }
                for d in delta.decisions_made
            ],
            "insights": delta.insights_gained,
            "patterns": delta.patterns_discovered,
            "metrics": {
                "token_used": delta.token_used,
                "phases_completed": delta.phases_completed,
                "problems_solved": delta.problems_solved,
            },
            "context_changes": {
                "blockers_added": delta.blockers_added,
                "blockers_resolved": delta.blockers_resolved,
                "questions_raised": delta.questions_raised,
                "questions_answered": delta.questions_answered,
            }
        }
    
    def _delta_to_markdown(self, delta: SessionDelta) -> str:
        """Convert delta to markdown summary."""
        lines = []
        
        # Header
        lines.append(f"# Session Delta: {delta.session_id}")
        lines.append(f"")
        lines.append(f"**Duration**: {delta.duration_minutes} minutes")
        lines.append(f"**Completed**: {len(delta.phases_completed)} phases")
        lines.append(f"")
        
        # What Changed
        lines.append("## 📝 What Changed")
        lines.append("")
        
        if delta.files_changed:
            lines.append(f"**Files Modified**: {len(delta.files_changed)}")
            for fc in delta.files_changed[:10]:  # Limit to 10
                lines.append(f"- `{fc.path}` ({fc.change_type}): "
                           f"+{fc.lines_added}/-{fc.lines_removed} lines")
                if fc.description:
                    lines.append(f"  - {fc.description}")
            if len(delta.files_changed) > 10:
                lines.append(f"- *...and {len(delta.files_changed) - 10} more*")
            lines.append("")
        
        if delta.features_added:
            lines.append(f"**Features Added** ({len(delta.features_added)}):")
            for feat in delta.features_added:
                lines.append(f"- {feat}")
            lines.append("")
        
        if delta.bugs_fixed:
            lines.append(f"**Bugs Fixed** ({len(delta.bugs_fixed)}):")
            for bug in delta.bugs_fixed:
                lines.append(f"- {bug}")
            lines.append("")
        
        if delta.tests_added:
            lines.append(f"**Tests Added** ({len(delta.tests_added)}):")
            for test in delta.tests_added:
                lines.append(f"- {test}")
            lines.append("")
        
        if delta.docs_updated:
            lines.append(f"**Documentation Updated** ({len(delta.docs_updated)}):")
            for doc in delta.docs_updated:
                lines.append(f"- {doc}")
            lines.append("")
        
        # Decisions
        if delta.decisions_made:
            lines.append("## 🤔 Decisions Made")
            lines.append("")
            for i, dec in enumerate(delta.decisions_made, 1):
                lines.append(f"**{i}. {dec.decision}**")
                lines.append(f"- Reasoning: {dec.reasoning}")
                if dec.alternatives_considered:
                    lines.append(f"- Alternatives: {', '.join(dec.alternatives_considered)}")
                lines.append("")
        
        # Insights & Patterns
        if delta.insights_gained or delta.patterns_discovered:
            lines.append("## 💡 Insights & Patterns")
            lines.append("")
            
            if delta.insights_gained:
                lines.append("**Insights:**")
                for insight in delta.insights_gained:
                    lines.append(f"- {insight}")
                lines.append("")
            
            if delta.patterns_discovered:
                lines.append("**Patterns:**")
                for pattern in delta.patterns_discovered:
                    lines.append(f"- {pattern}")
                lines.append("")
        
        # Context Changes
        if (delta.blockers_added or delta.blockers_resolved or 
            delta.questions_raised or delta.questions_answered):
            lines.append("## 🔄 Context Changes")
            lines.append("")
            
            if delta.blockers_resolved:
                lines.append(f"**✅ Blockers Resolved** ({len(delta.blockers_resolved)}):")
                for blocker in delta.blockers_resolved:
                    lines.append(f"- ~~{blocker}~~")
                lines.append("")
            
            if delta.blockers_added:
                lines.append(f"**🚧 New Blockers** ({len(delta.blockers_added)}):")
                for blocker in delta.blockers_added:
                    lines.append(f"- {blocker}")
                lines.append("")
            
            if delta.questions_answered:
                lines.append(f"**✅ Questions Answered** ({len(delta.questions_answered)}):")
                for q in delta.questions_answered:
                    lines.append(f"- ~~{q}~~")
                lines.append("")
            
            if delta.questions_raised:
                lines.append(f"**❓ New Questions** ({len(delta.questions_raised)}):")
                for q in delta.questions_raised:
                    lines.append(f"- {q}")
                lines.append("")
        
        # Metrics
        lines.append("## 📊 Metrics")
        lines.append("")
        lines.append(f"- **Token usage**: {delta.token_used:,} tokens")
        lines.append(f"- **Phases completed**: {', '.join(delta.phases_completed) if delta.phases_completed else 'None'}")
        lines.append(f"- **Problems solved**: {delta.problems_solved}")
        lines.append("")
        
        return "\n".join(lines)
    
    def save_summary(
        self,
        output_path: Path,
        format: str = "markdown",
        include_frontmatter: bool = True
    ) -> Path:
        """
        Save delta summary to a file.
        
        Args:
            output_path: Where to save
            format: Output format
            include_frontmatter: Whether to include frontmatter (markdown only)
            
        Returns:
            Path where summary was saved
        """
        summary = self.generate_summary(format)
        
        if format == "markdown" and include_frontmatter:
            delta = self.get_delta()
            frontmatter = self._generate_frontmatter(delta)
            summary = f"{frontmatter}\n{summary}"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
        
        return output_path
    
    def _generate_frontmatter(self, delta: SessionDelta) -> str:
        """Generate frontmatter for markdown summary."""
        tags = [
            "session-delta",
            f"session-{delta.session_id}",
            "changes"
        ]
        
        if delta.phases_completed:
            tags.extend([f"phase-{p.lower().replace(' ', '-')}" 
                        for p in delta.phases_completed])
        
        return f"""---
title: Session Delta - {delta.session_id}
created: {delta.start_time.isoformat()}
ended: {delta.end_time.isoformat()}
duration_minutes: {delta.duration_minutes}
tags: {', '.join(tags)}
---
"""


def track_session_changes(session_id: Optional[str] = None) -> DeltaTracker:
    """
    Convenience function to create a delta tracker.
    
    Args:
        session_id: Optional session ID
        
    Returns:
        DeltaTracker instance
        
    Example:
        >>> tracker = track_session_changes()
        >>> tracker.add_feature("Hierarchical workspace loader")
        >>> tracker.track_file_change("whitemagic/workspace_loader.py", "created")
        >>> summary = tracker.generate_summary()
    """
    return DeltaTracker(session_id)
