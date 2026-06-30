# ruff: noqa: BLE001
"""Parallel Reasoning Tree -- Multi-branch cognitive exploration.

Inspired by biological human thought patterns where multiple reasoning
threads run in parallel, cross-pollinate, and converge. This module
extends WhiteMagic's reasoning capabilities beyond the linear sequential
chain to support:

1. **Branching**: Spawn multiple independent reasoning branches from any
   thought, exploring different hypotheses simultaneously.
2. **Backtracking**: Abandon unproductive branches and return to a prior
   thought to explore a new direction.
3. **Revision**: Replace or refine a previous thought with new information
   gained from parallel exploration.
4. **Cross-pollination**: Branches can share intermediate insights with
   each other, enabling emergent synthesis.
5. **Convergence**: Branches are scored and merged into a final synthesis,
   with the best insights from all threads integrated.

This is closer to how biological brains solve problems -- multiple
hypotheses tested in parallel, with attention shifting to the most
promising threads.

Usage:
    from whitemagic.core.intelligence.parallel_reasoning import (
        get_parallel_reasoner, ParallelReasoningTree, BranchStatus
    )

    tree = ParallelReasoningTree(question="How to scale the memory tier?")
    result = await tree.explore(max_branches=4, max_depth=6)
    print(result.synthesis)
    print(f"Branches explored: {len(result.branches)}")
    for b in result.branches:
        print(f"  {b.branch_id}: score={b.score:.2f} status={b.status}")
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Optional imports for memory injection and anti-pattern checking
try:
    from whitemagic.core.memory.unified import get_unified_memory

    _HAS_MEMORY = True
except Exception:
    _HAS_MEMORY = False

try:
    from whitemagic.core.immune.defense.autoimmune import AutoimmuneSystem

    _HAS_ANTIPATTERN = True
except Exception:
    _HAS_ANTIPATTERN = False

try:
    from whitemagic.core.patterns.pattern_consciousness.autonomous_learner import (
        get_autonomous_learner,
    )

    _HAS_LEARNER = True
except Exception:
    _HAS_LEARNER = False

try:
    from whitemagic.forecasting.mc_integration import MCForecastEnhancer

    _HAS_MC = True
except Exception:
    _HAS_MC = False

logger = logging.getLogger(__name__)


class BranchStatus(Enum):
    """Status of a reasoning branch."""

    ACTIVE = "active"
    CONVERGED = "converged"
    ABANDONED = "abandoned"
    REVISED = "revised"


@dataclass
class ThoughtNode:
    """A single thought in a reasoning branch.

    Supports branching (parent -> children), revision (replaces a prior
    thought), and cross-pollination (insights from other branches).
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    content: str = ""
    thought_number: int = 1
    branch_id: str = "main"
    parent_id: str | None = None
    revises_id: str | None = None
    insights_from: list[str] = field(default_factory=list)
    confidence: float = 0.5
    is_hypothesis: bool = False
    is_revision: bool = False
    children: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "thought_number": self.thought_number,
            "branch_id": self.branch_id,
            "parent_id": self.parent_id,
            "revises_id": self.revises_id,
            "insights_from": self.insights_from,
            "confidence": self.confidence,
            "is_hypothesis": self.is_hypothesis,
            "is_revision": self.is_revision,
            "children": self.children,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ReasoningBranch:
    """A single branch of parallel reasoning.

    Each branch is an independent chain of ThoughtNodes exploring a
    specific hypothesis or perspective.
    """

    branch_id: str
    hypothesis: str
    thoughts: list[ThoughtNode] = field(default_factory=list)
    status: BranchStatus = BranchStatus.ACTIVE
    score: float = 0.0
    parent_branch: str | None = None
    forked_at_thought: int | None = None
    insights: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def depth(self) -> int:
        return len(self.thoughts)

    @property
    def latest_thought(self) -> ThoughtNode | None:
        return self.thoughts[-1] if self.thoughts else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "hypothesis": self.hypothesis,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "status": self.status.value,
            "score": round(self.score, 3),
            "parent_branch": self.parent_branch,
            "forked_at_thought": self.forked_at_thought,
            "insights": self.insights,
            "depth": self.depth,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ParallelReasoningResult:
    """Final result from parallel reasoning tree exploration."""

    question: str
    branches: list[ReasoningBranch]
    synthesis: str
    best_branch_id: str
    total_thoughts: int
    convergence_points: list[dict[str, Any]] = field(default_factory=list)
    abandoned_count: int = 0
    revised_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "branches": [b.to_dict() for b in self.branches],
            "synthesis": self.synthesis,
            "best_branch_id": self.best_branch_id,
            "total_thoughts": self.total_thoughts,
            "convergence_points": self.convergence_points,
            "abandoned_count": self.abandoned_count,
            "revised_count": self.revised_count,
            "timestamp": self.timestamp.isoformat(),
        }


class ParallelReasoningTree:
    """Multi-branch parallel reasoning engine.

    Models biological human thought patterns where multiple hypotheses
    are explored simultaneously, unproductive threads are abandoned, and
    insights cross-pollinate between branches before converging.

    The tree supports:
    - Branching: Fork new branches from any thought
    - Backtracking: Abandon branches that score below threshold
    - Revision: Replace thoughts with improved versions
    - Cross-pollination: Share insights between active branches
    - Convergence: Merge best insights into final synthesis
    """

    def __init__(
        self,
        question: str,
        context: dict[str, Any] | None = None,
        branch_threshold: float = 0.3,
        convergence_threshold: float = 0.7,
    ) -> None:
        self.question = question
        self.context = context or {}
        self.branch_threshold = branch_threshold
        self.convergence_threshold = convergence_threshold

        self.branches: dict[str, ReasoningBranch] = {}
        self.all_thoughts: dict[str, ThoughtNode] = {}
        self._branch_counter = 0
        self._memory_context: list[dict[str, Any]] = []
        self._anti_patterns: list[str] = []
        self._lessons: list[str] = []
        self._auto_learn: bool = True

        # Load context from memory and anti-pattern systems
        self._load_memory_context()
        self._load_anti_patterns()
        self._load_lessons()

        # Create main branch
        self._create_branch("main", hypothesis="Primary exploration")

    def _create_branch(
        self,
        branch_id: str | None = None,
        hypothesis: str = "",
        parent_branch: str | None = None,
        forked_at_thought: int | None = None,
    ) -> ReasoningBranch:
        """Create a new reasoning branch."""
        if branch_id is None:
            self._branch_counter += 1
            branch_id = f"branch_{self._branch_counter}"

        branch = ReasoningBranch(
            branch_id=branch_id,
            hypothesis=hypothesis,
            parent_branch=parent_branch,
            forked_at_thought=forked_at_thought,
        )
        self.branches[branch_id] = branch
        return branch

    def add_thought(
        self,
        branch_id: str,
        content: str,
        confidence: float = 0.5,
        is_hypothesis: bool = False,
        revises_id: str | None = None,
        insights_from: list[str] | None = None,
    ) -> ThoughtNode:
        """Add a thought to a specific branch.

        Args:
            branch_id: Which branch to add to
            content: The thought content
            confidence: Confidence score (0-1)
            is_hypothesis: Is this a testable hypothesis?
            revises_id: If revising, the ID of the thought being replaced
            insights_from: Branch IDs that contributed insights to this thought
        """
        branch = self.branches.get(branch_id)
        if not branch:
            raise ValueError(f"Branch {branch_id} does not exist")

        thought_num = len(branch.thoughts) + 1
        parent_id = branch.thoughts[-1].id if branch.thoughts else None

        node = ThoughtNode(
            content=content,
            thought_number=thought_num,
            branch_id=branch_id,
            parent_id=parent_id,
            revises_id=revises_id,
            insights_from=insights_from or [],
            confidence=confidence,
            is_hypothesis=is_hypothesis,
            is_revision=revises_id is not None,
        )

        branch.thoughts.append(node)
        self.all_thoughts[node.id] = node

        if parent_id and parent_id in self.all_thoughts:
            self.all_thoughts[parent_id].children.append(node.id)

        return node

    def fork_branch(
        self,
        from_branch_id: str,
        hypothesis: str,
        at_thought: int | None = None,
    ) -> ReasoningBranch:
        """Fork a new branch from an existing one.

        Args:
            from_branch_id: The branch to fork from
            hypothesis: The new hypothesis to explore
            at_thought: Fork at a specific thought number (default: latest)

        Returns:
            The new branch
        """
        parent = self.branches.get(from_branch_id)
        if not parent:
            raise ValueError(f"Branch {from_branch_id} does not exist")

        fork_point = at_thought or parent.depth
        self._branch_counter += 1
        new_id = f"branch_{self._branch_counter}"

        new_branch = self._create_branch(
            branch_id=new_id,
            hypothesis=hypothesis,
            parent_branch=from_branch_id,
            forked_at_thought=fork_point,
        )

        # Copy thoughts up to fork point as starting context
        for i, thought in enumerate(parent.thoughts[:fork_point]):
            copied = ThoughtNode(
                content=f"[inherited] {thought.content}",
                thought_number=i + 1,
                branch_id=new_id,
                parent_id=parent.thoughts[i - 1].id if i > 0 else None,
                confidence=thought.confidence,
            )
            new_branch.thoughts.append(copied)
            self.all_thoughts[copied.id] = copied

        return new_branch

    def abandon_branch(self, branch_id: str, reason: str = "") -> None:
        """Abandon a branch (backtracking).

        Marks the branch as abandoned but keeps its thoughts for reference.
        """
        branch = self.branches.get(branch_id)
        if branch:
            branch.status = BranchStatus.ABANDONED
            branch.insights.append(
                f"Abandoned: {reason}" if reason else "Abandoned: low score"
            )

    def revise_thought(
        self,
        branch_id: str,
        thought_id: str,
        new_content: str,
        new_confidence: float | None = None,
    ) -> ThoughtNode:
        """Revise a previous thought with new information.

        Creates a new ThoughtNode that marks the old one as revised.
        """
        branch = self.branches.get(branch_id)
        if not branch:
            raise ValueError(f"Branch {branch_id} does not exist")

        old_thought = self.all_thoughts.get(thought_id)
        if not old_thought:
            raise ValueError(f"Thought {thought_id} does not exist")

        revised = self.add_thought(
            branch_id=branch_id,
            content=new_content,
            confidence=new_confidence or old_thought.confidence + 0.1,
            revises_id=thought_id,
        )
        return revised

    def cross_pollinate(
        self,
        source_branch_id: str,
        target_branch_id: str,
        insight: str,
    ) -> ThoughtNode:
        """Share an insight from one branch to another.

        This enables emergent synthesis where discoveries in one thread
        inform exploration in another.
        """
        source = self.branches.get(source_branch_id)
        target = self.branches.get(target_branch_id)
        if not source or not target:
            raise ValueError("Both branches must exist")

        source.insights.append(insight)

        node = self.add_thought(
            branch_id=target_branch_id,
            content=f"Cross-pollination from {source_branch_id}: {insight}",
            confidence=0.6,
            insights_from=[source_branch_id],
        )
        return node

    def score_branch(self, branch_id: str) -> float:
        """Score a branch based on thought confidence, depth, and insights.

        Scoring factors:
        - Average confidence of thoughts
        - Depth bonus (longer chains that maintain confidence)
        - Insight count (cross-pollination value)
        - Hypothesis verification bonus
        """
        branch = self.branches.get(branch_id)
        if not branch or not branch.thoughts:
            return 0.0

        confidences = [
            t.confidence
            for t in branch.thoughts
            if not t.content.startswith("[inherited]")
        ]
        if not confidences:
            return 0.0

        avg_conf = sum(confidences) / len(confidences)
        depth_bonus = min(len(confidences) / 10.0, 0.2)
        insight_bonus = min(len(branch.insights) * 0.05, 0.15)
        hypothesis_bonus = 0.1 if any(t.is_hypothesis for t in branch.thoughts) else 0.0

        score = avg_conf + depth_bonus + insight_bonus + hypothesis_bonus
        branch.score = min(score, 1.0)
        return branch.score

    def detect_convergence(self) -> list[dict[str, Any]]:
        """Detect convergence points between active branches.

        Two branches converge when their latest thoughts share significant
        keyword overlap, indicating they're reaching similar conclusions.
        """
        active = [
            b
            for b in self.branches.values()
            if b.status == BranchStatus.ACTIVE and b.latest_thought
        ]
        convergence_points: list[dict[str, Any]] = []

        for i, branch_a in enumerate(active):
            for branch_b in active[i + 1 :]:
                thought_a = branch_a.latest_thought
                thought_b = branch_b.latest_thought
                if not thought_a or not thought_b:
                    continue

                words_a = set(thought_a.content.lower().split())
                words_b = set(thought_b.content.lower().split())
                words_a -= {
                    "the",
                    "a",
                    "an",
                    "is",
                    "to",
                    "and",
                    "or",
                    "in",
                    "for",
                    "of",
                    "with",
                    "it",
                    "this",
                    "that",
                }
                words_b -= {
                    "the",
                    "a",
                    "an",
                    "is",
                    "to",
                    "and",
                    "or",
                    "in",
                    "for",
                    "of",
                    "with",
                    "it",
                    "this",
                    "that",
                }

                if not words_a or not words_b:
                    continue

                overlap = len(words_a & words_b)
                union = len(words_a | words_b)
                jaccard = overlap / union if union > 0 else 0

                if jaccard >= self.convergence_threshold:
                    convergence_points.append(
                        {
                            "branch_a": branch_a.branch_id,
                            "branch_b": branch_b.branch_id,
                            "similarity": round(jaccard, 3),
                            "shared_keywords": list(words_a & words_b)[:10],
                        }
                    )

        return convergence_points

    def synthesize(self) -> str:
        """Synthesize insights from all branches into a final answer.

        Process:
        1. Score all branches
        2. Identify convergence points
        3. Select best branch as primary
        4. Integrate insights from other branches
        5. Note abandoned branches and what was learned
        """
        for bid in self.branches:
            self.score_branch(bid)

        active = [
            b for b in self.branches.values() if b.status != BranchStatus.ABANDONED
        ]
        abandoned = [
            b for b in self.branches.values() if b.status == BranchStatus.ABANDONED
        ]
        revised = [t for t in self.all_thoughts.values() if t.is_revision]

        if not active:
            return "All branches were abandoned. No synthesis possible."

        convergence = self.detect_convergence()
        best = max(active, key=lambda b: b.score)

        parts: list[str] = []
        parts.append(
            f"Parallel Reasoning Synthesis: {len(self.branches)} branches explored, "
            f"{len(active)} active, {len(abandoned)} abandoned, {len(revised)} revisions."
        )

        parts.append(f"\nBest branch: {best.branch_id} (score={best.score:.2f})")
        parts.append(f"  Hypothesis: {best.hypothesis}")
        for t in best.thoughts:
            if t.content.startswith("[inherited]"):
                continue
            prefix = (
                f"  [{t.thought_number}]"
                + (" (revised)" if t.is_revision else "")
                + (" (hypothesis)" if t.is_hypothesis else "")
            )
            parts.append(f"{prefix} {t.content}")

        if convergence:
            parts.append(f"\nConvergence detected at {len(convergence)} point(s):")
            for cp in convergence[:5]:
                parts.append(
                    f"  {cp['branch_a']} <-> {cp['branch_b']} (sim={cp['similarity']:.2f})"
                )

        other_insights: list[str] = []
        for b in active:
            if b.branch_id == best.branch_id:
                continue
            for insight in b.insights:
                other_insights.append(f"  [{b.branch_id}] {insight}")
        if other_insights:
            parts.append("\nInsights from other branches:")
            parts.extend(other_insights[:10])

        if abandoned:
            parts.append(f"\nAbandoned branches ({len(abandoned)}):")
            for b in abandoned:
                reason = b.insights[-1] if b.insights else "Unknown"
                parts.append(f"  {b.branch_id}: {reason}")

        return "\n".join(parts)

    async def explore(
        self,
        max_branches: int = 4,
        max_depth: int = 6,
        fork_threshold: float = 0.5,
    ) -> ParallelReasoningResult:
        """Explore the reasoning tree with parallel branches.

        This is the main entry point for autonomous multi-branch reasoning.
        It generates initial hypotheses, explores them in parallel, forks
        new branches when promising directions appear, abandons unproductive
        ones, and synthesizes results.

        Args:
            max_branches: Maximum number of concurrent branches
            max_depth: Maximum thoughts per branch
            fork_threshold: Confidence threshold for forking new branches

        Returns:
            ParallelReasoningResult with all branches and synthesis
        """
        # Generate initial hypotheses
        hypotheses = self._generate_hypotheses(max_branches)

        # Create initial branches
        for i, hyp in enumerate(hypotheses[1:], start=1):
            if len(self.branches) >= max_branches:
                break
            self._create_branch(
                branch_id=f"branch_{i}",
                hypothesis=hyp,
                parent_branch="main",
                forked_at_thought=0,
            )

        # Add initial observation to all branches
        for bid, branch in self.branches.items():
            self.add_thought(
                branch_id=bid,
                content=f"Observing: '{self.question[:120]}' -- exploring: {branch.hypothesis}",
                confidence=0.5,
                is_hypothesis=True,
            )

        # Explore branches in parallel using asyncio
        tasks = []
        for bid in list(self.branches.keys()):
            tasks.append(
                self._explore_branch(bid, max_depth, fork_threshold, max_branches)
            )
        await asyncio.gather(*tasks, return_exceptions=True)

        # Detect convergence and cross-pollinate
        convergence = self.detect_convergence()
        for cp in convergence:
            try:
                self.cross_pollinate(
                    cp["branch_a"],
                    cp["branch_b"],
                    f"Convergence on: {', '.join(cp['shared_keywords'][:5])}",
                )
            except Exception:
                pass

        # Auto-learn from all branch outcomes
        for branch in self.branches.values():
            if (
                branch.status == BranchStatus.ACTIVE
                and branch.score > self.convergence_threshold
            ):
                branch.status = BranchStatus.CONVERGED
            self._auto_learn_from_branch(branch)

        # Final synthesis
        synthesis = self.synthesize()

        # Determine best branch
        for bid in self.branches:
            self.score_branch(bid)
        active = [
            b for b in self.branches.values() if b.status != BranchStatus.ABANDONED
        ]
        best_id = max(active, key=lambda b: b.score).branch_id if active else "main"

        abandoned_count = sum(
            1 for b in self.branches.values() if b.status == BranchStatus.ABANDONED
        )
        revised_count = sum(1 for t in self.all_thoughts.values() if t.is_revision)

        return ParallelReasoningResult(
            question=self.question,
            branches=list(self.branches.values()),
            synthesis=synthesis,
            best_branch_id=best_id,
            total_thoughts=len(self.all_thoughts),
            convergence_points=convergence,
            abandoned_count=abandoned_count,
            revised_count=revised_count,
        )

    def _load_memory_context(self) -> None:
        """Load relevant memories for the question via hybrid_recall."""
        if not _HAS_MEMORY:
            return
        try:
            mem = get_unified_memory()
            results = mem.search(self.question, limit=5)
            for r in results:
                self._memory_context.append(
                    {
                        "content": getattr(r, "content", str(r))[:500],
                        "tags": getattr(r, "tags", []),
                        "score": getattr(r, "score", 0.0),
                    }
                )
            logger.debug(
                "Loaded %d memory contexts for reasoning", len(self._memory_context)
            )
        except Exception as e:
            logger.debug("Memory context loading skipped: %s", e)

    def _load_anti_patterns(self) -> None:
        """Load anti-pattern keywords to avoid during reasoning."""
        if not _HAS_ANTIPATTERN:
            return
        try:
            import tempfile
            from pathlib import Path

            # AutoimmuneSystem loads from memory/meta dir -- use temp if not available
            immune = AutoimmuneSystem(base_dir=Path(tempfile.gettempdir()))
            for ap in immune.anti_patterns.values():
                if ap.confidence >= 0.7:
                    self._anti_patterns.append(ap.title)
            logger.debug(
                "Loaded %d anti-patterns for reasoning", len(self._anti_patterns)
            )
        except Exception as e:
            logger.debug("Anti-pattern loading skipped: %s", e)

    def _load_lessons(self) -> None:
        """Load past lessons from AutonomousLearner."""
        if not _HAS_LEARNER:
            return
        try:
            learner = get_autonomous_learner()
            self._lessons = list(learner.lessons_learned[-10:])
            logger.debug("Loaded %d past lessons for reasoning", len(self._lessons))
        except Exception as e:
            logger.debug("Lesson loading skipped: %s", e)

    def _check_anti_patterns(self, content: str) -> bool:
        """Check if content matches any anti-patterns.

        Returns True if content is safe (no anti-pattern match).
        """
        if not self._anti_patterns:
            return True
        content_lower = content.lower()
        for ap in self._anti_patterns:
            ap_lower = ap.lower()
            # Simple keyword overlap check
            ap_words = set(ap_lower.split())
            content_words = set(content_lower.split())
            overlap = len(ap_words & content_words)
            if overlap >= 2 and overlap / max(len(ap_words), 1) > 0.5:
                return False
        return True

    def _inject_memory_context(self, branch: ReasoningBranch, step: int) -> str:
        """Inject relevant memory context into a branch's reasoning.

        Uses zodiacal phase to determine injection timing:
        - Yang phase (creative): inject at steps 2, 4 (lessons, memories)
        - Yin phase (receptive): inject at steps 3, 5 (reflections, anti-patterns)
        - Fixed phase (balanced): inject at step 6 (consolidation)

        Per-branch: different branches get different memory slices
        based on their hypothesis content.
        """
        # Determine current zodiacal phase
        phase = self._get_zodiacal_phase()

        if phase == "yang":
            if step == 2 and self._lessons:
                # Per-branch lesson selection based on hypothesis content
                lesson = self._select_lesson_for_branch(branch)
                return f"Past lesson applied: {lesson[:100]}"
            if step == 4 and self._memory_context:
                ctx = self._select_memory_for_branch(branch)
                if ctx:
                    return f"Memory recall: {ctx['content'][:100]}"
        elif phase == "yin":
            if step == 3 and self._anti_patterns:
                ap = self._select_antipattern_for_branch(branch)
                if ap:
                    return f"Anti-pattern warning: avoid {ap[:80]}"
            if step == 5 and self._lessons:
                lesson = self._lessons[-1] if self._lessons else ""
                return f"Recent lesson: {lesson[:100]}"
        else:  # fixed
            if step == 6 and self._memory_context:
                ctx = self._memory_context[0]
                return f"Consolidation context: {ctx['content'][:80]}"

        return ""

    def _get_zodiacal_phase(self) -> str:
        """Get the current zodiacal phase for injection timing."""
        try:
            from whitemagic.core.orchestration.zodiacal_procession import get_procession

            proc = get_procession()
            return proc.state.current_phase.value
        except Exception:
            return "yang"  # Default to creative

    def _select_lesson_for_branch(self, branch: ReasoningBranch) -> str:
        """Select the most relevant lesson for a specific branch.

        Uses simple keyword overlap between branch hypothesis and lessons.
        """
        if not self._lessons:
            return ""
        hypothesis_words = set(branch.hypothesis.lower().split())
        best_lesson = ""
        best_overlap = 0
        for lesson in self._lessons:
            lesson_words = set(lesson.lower().split())
            overlap = len(hypothesis_words & lesson_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_lesson = lesson
        return best_lesson or self._lessons[0]

    def _select_memory_for_branch(
        self, branch: ReasoningBranch
    ) -> dict[str, Any] | None:
        """Select the most relevant memory for a specific branch.

        Uses keyword overlap between branch hypothesis and memory content.
        """
        if not self._memory_context:
            return None
        hypothesis_words = set(branch.hypothesis.lower().split())
        best_ctx = None
        best_overlap = 0
        for ctx in self._memory_context:
            content_words = set(ctx.get("content", "").lower().split())
            overlap = len(hypothesis_words & content_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_ctx = ctx
        return best_ctx or self._memory_context[0]

    def _select_antipattern_for_branch(self, branch: ReasoningBranch) -> str:
        """Select the most relevant anti-pattern for a specific branch.

        Uses keyword overlap to find anti-patterns that might apply.
        """
        if not self._anti_patterns:
            return ""
        hypothesis_words = set(branch.hypothesis.lower().split())
        best_ap = ""
        best_overlap = 0
        for ap in self._anti_patterns:
            ap_words = set(ap.lower().split())
            overlap = len(hypothesis_words & ap_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_ap = ap
        return best_ap

    def _auto_learn_from_branch(self, branch: ReasoningBranch) -> None:
        """Auto-learn from branch outcomes.

        Abandoned branches -> learn_from_mistake + record triggered anti-patterns
        Converged branches -> learn_from_success + record effective patterns
        """
        if not self._auto_learn or not _HAS_LEARNER:
            return
        try:
            learner = get_autonomous_learner()
            if branch.status == BranchStatus.ABANDONED:
                mistake = f"Reasoning branch '{branch.hypothesis[:60]}' abandoned (score={branch.score:.2f})"
                lesson = f"Avoid: {branch.hypothesis[:60]} -- insufficient confidence for this approach"

                # Check if any anti-patterns were triggered
                triggered_patterns = []
                for ap in self._anti_patterns:
                    ap_words = set(ap.lower().split())
                    hypothesis_words = set(branch.hypothesis.lower().split())
                    overlap = len(ap_words & hypothesis_words)
                    if overlap >= 2 and overlap / max(len(ap_words), 1) > 0.5:
                        triggered_patterns.append(ap)

                if triggered_patterns:
                    lesson += f" | Anti-patterns triggered: {', '.join(triggered_patterns[:3])}"

                learner.learn_from_mistake(mistake, lesson)
            elif branch.status == BranchStatus.CONVERGED:
                success = f"Reasoning branch '{branch.hypothesis[:60]}' converged (score={branch.score:.2f})"
                principle = f"Effective: {branch.hypothesis[:60]} -- this approach yielded strong results"
                learner.learn_from_success(success, principle)
        except Exception as e:
            logger.debug("Auto-learning skipped: %s", e)

    def _score_branch_monte_carlo(self, branch: ReasoningBranch) -> float:
        """Score a branch's confidence using Monte Carlo simulation.

        Creates forecast claims from branch thoughts and runs MC calibration
        to get a Brier skill score, which is converted to a confidence value.
        """
        if not _HAS_MC or not branch.thoughts:
            return branch.score

        try:
            enhancer = MCForecastEnhancer()
            # Create claims from branch thoughts
            claims = []
            for thought in branch.thoughts:
                claims.append(
                    {
                        "id": f"branch_{branch.id}_thought_{thought.id}",
                        "claim": thought.content[:100],
                        "confidence": thought.confidence,
                        "outcome": 1.0 if thought.confidence > 0.5 else 0.0,
                        "status": "validated"
                        if thought.confidence > 0.5
                        else "falsified",
                        "category": "reasoning",
                    }
                )

            if not claims:
                return branch.score

            result = enhancer.run_calibrated(claims, n_trials=500)
            mc = result.get("mc_result", {})
            bss = mc.get("brier_skill_score", {}).get("mean", 0.0)
            # Convert BSS to confidence: BSS > 0 means better than random
            mc_confidence = max(0.0, min(1.0, (bss + 1.0) / 2.0))

            # Blend MC confidence with branch score
            blended = (branch.score * 0.6) + (mc_confidence * 0.4)
            return blended
        except Exception as e:
            logger.debug("MC branch scoring skipped: %s", e)
            return branch.score

    def _should_branch_continue(
        self, branch: ReasoningBranch, current_step: int
    ) -> bool:
        """Determine if a branch should continue exploring using MC confidence.

        Uses Monte Carlo scoring to decide whether to invest more steps
        in a branch or abandon it early.
        """
        if current_step < 3:
            return True  # Always give at least 3 steps

        mc_score = self._score_branch_monte_carlo(branch)

        # Dynamic threshold based on step count
        # Early steps: lower threshold (more exploration)
        # Later steps: higher threshold (more exploitation)
        dynamic_threshold = self.branch_threshold + (current_step - 3) * 0.05

        return mc_score >= dynamic_threshold

    def _generate_hypotheses(self, count: int) -> list[str]:
        """Generate initial hypotheses for parallel exploration."""
        base_hypotheses = [
            "Direct analytical approach -- break down the problem logically",
            "Creative lateral approach -- look for unconventional connections",
            "Historical pattern approach -- what has worked before in similar situations",
            "Risk-first approach -- what could go wrong and how to mitigate",
            "Optimization approach -- what is the ideal outcome and how to reach it",
            "Contrarian approach -- challenge the assumptions in the question",
        ]
        return base_hypotheses[:count]

    async def _explore_branch(
        self,
        branch_id: str,
        max_depth: int,
        fork_threshold: float,
        max_branches: int,
    ) -> None:
        """Explore a single branch up to max_depth.

        This is where the actual reasoning happens. Each step:
        1. Generate the next thought based on context
        2. Score the branch
        3. If score is very low, abandon (backtrack)
        4. If a thought has high confidence, potentially fork a new branch
        """
        branch = self.branches.get(branch_id)
        if not branch:
            return

        for step in range(1, max_depth):
            if branch.status != BranchStatus.ACTIVE:
                break

            # Generate next thought
            thought_content = self._generate_thought(branch, step)
            confidence = self._estimate_confidence(branch, step)

            self.add_thought(
                branch_id=branch_id,
                content=thought_content,
                confidence=confidence,
            )

            # Score and potentially abandon
            score = self.score_branch(branch_id)
            # MC-based continuation decision
            if step >= 3 and not self._should_branch_continue(branch, step):
                mc_score = self._score_branch_monte_carlo(branch)
                self.abandon_branch(
                    branch_id,
                    f"MC score {mc_score:.2f} below dynamic threshold at step {step}",
                )
                self._auto_learn_from_branch(branch)
                break

            if score < self.branch_threshold and step >= 3:
                self.abandon_branch(
                    branch_id,
                    f"Score {score:.2f} below threshold {self.branch_threshold}",
                )
                self._auto_learn_from_branch(branch)
                break

            # Fork if high confidence and we have room
            if (
                confidence >= fork_threshold
                and len(self.branches) < max_branches
                and step >= 2
            ):
                fork_hyp = (
                    f"Forked from {branch_id} at step {step}: {thought_content[:60]}"
                )
                self._create_branch(
                    hypothesis=fork_hyp,
                    parent_branch=branch_id,
                    forked_at_thought=step,
                )

            # Yield control to allow other branches to progress
            await asyncio.sleep(0)

    def _generate_thought(self, branch: ReasoningBranch, step: int) -> str:
        """Generate the next thought for a branch.

        This uses simple heuristics to simulate reasoning steps. In a
        full deployment, this would call the LLM or multi-spectral reasoner.
        """
        thought_templates = [
            "Analyzing the problem from the perspective of {hyp}",
            "Identifying key factors and constraints in this approach",
            "Evaluating evidence for and against this direction",
            "Synthesizing findings so far -- what patterns emerge?",
            "Testing the hypothesis: does the evidence support it?",
            "Drawing preliminary conclusions from this exploration",
            "Final assessment: confidence in this approach is {conf}",
        ]

        template = thought_templates[min(step - 1, len(thought_templates) - 1)]
        hyp = branch.hypothesis[:60]
        conf = "moderate" if branch.score > 0.4 else "low"
        return template.format(hyp=hyp, conf=conf)

    def _estimate_confidence(self, branch: ReasoningBranch, step: int) -> float:
        """Estimate confidence for the current step.

        Confidence tends to increase with depth if the branch is productive,
        but plateaus. Adds some variation to simulate real reasoning.
        """
        base = 0.4 + (step * 0.08)
        # Add branch-specific variation based on hypothesis
        if "creative" in branch.hypothesis.lower():
            base += 0.05  # Creative branches start lower but grow
        if "risk" in branch.hypothesis.lower():
            base -= 0.03  # Risk analysis is more cautious
        if "contrarian" in branch.hypothesis.lower():
            base -= 0.05  # Contrarian is exploratory
        return min(base, 0.95)


_tree: ParallelReasoningTree | None = None


def get_parallel_reasoner(question: str = "") -> ParallelReasoningTree:
    """Get or create a parallel reasoning tree.

    If a question is provided, creates a new tree for that question.
    Otherwise returns the last-created tree.
    """
    global _tree
    if question:
        _tree = ParallelReasoningTree(question=question)
    if _tree is None:
        _tree = ParallelReasoningTree(question="default")
    return _tree
