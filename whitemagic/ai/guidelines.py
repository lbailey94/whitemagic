"""
AI Guidelines - Built-in Rules for AI Systems Using WhiteMagic

These guidelines are built INTO WhiteMagic, so any AI system
(Claude Desktop, ChatGPT, custom agents, API integrations)
can discover and follow them automatically.

Philosophy: Rules should be discoverable, not just documented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class GuidelineCategory(Enum):
    """Categories of AI guidelines."""
    SESSION_START = "session_start"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TOKEN_EFFICIENCY = "token_efficiency"
    PROBLEM_SOLVING = "problem_solving"
    METRICS_TRACKING = "metrics_tracking"
    CONSOLIDATION = "consolidation"
    STRATEGIC_THINKING = "strategic_thinking"


@dataclass
class Guideline:
    """A single AI guideline."""
    
    id: str
    category: GuidelineCategory
    title: str
    description: str
    priority: str  # "critical", "high", "medium", "low"
    applicable_to: List[str]  # ["any", "claude", "chatgpt", "custom"]
    example: Optional[str] = None
    code_snippet: Optional[str] = None


class AIGuidelinesManager:
    """
    Manages AI guidelines built into WhiteMagic.
    
    Any AI can call this to discover how to work effectively.
    """
    
    def __init__(self):
        self.guidelines = self._initialize_guidelines()
    
    def _initialize_guidelines(self) -> List[Guideline]:
        """Initialize all guidelines."""
        return [
            # SESSION START PROTOCOL
            Guideline(
                id="session_start_001",
                category=GuidelineCategory.SESSION_START,
                title="Always load context at session start",
                description="Use get_context(tier=1) first for balanced context. Don't rely on auto-retrieved memories.",
                priority="critical",
                applicable_to=["any"],
                code_snippet="""
# Python
from whitemagic import MemoryManager
manager = MemoryManager()
context = manager.get_context(tier=1)

# CLI
whitemagic context --tier 1

# MCP (if available)
mcp3_get_context(tier=1)
"""
            ),
            
            Guideline(
                id="session_start_002",
                category=GuidelineCategory.SESSION_START,
                title="Check for in-progress work",
                description="Search for 'in-progress' and 'session' tagged memories to resume work.",
                priority="high",
                applicable_to=["any"],
                code_snippet="""
# Python
results = manager.search(tags=['in-progress', 'session'])

# CLI
whitemagic search --tags in-progress session
"""
            ),
            
            # MEMORY RETRIEVAL PRIORITY
            Guideline(
                id="memory_001",
                category=GuidelineCategory.MEMORY_RETRIEVAL,
                title="Priority: WhiteMagic tools > Auto-retrieved",
                description="Explicitly retrieved memories are more reliable than auto-retrieved ones.",
                priority="high",
                applicable_to=["any"],
                example="Use manager.search() or whitemagic search instead of relying on IDE auto-retrieval"
            ),
            
            Guideline(
                id="memory_002",
                category=GuidelineCategory.MEMORY_RETRIEVAL,
                title="Most recent > Older memories",
                description="When multiple memories match, prefer more recently modified ones.",
                priority="medium",
                applicable_to=["any"],
                code_snippet="""
# Python
results = manager.search(query="v2.2.9", sort_by="modified", reverse=True)
"""
            ),
            
            # TOKEN EFFICIENCY
            Guideline(
                id="token_001",
                category=GuidelineCategory.TOKEN_EFFICIENCY,
                title="Use tiered context loading",
                description="Tier 0 (quick), Tier 1 (normal), Tier 2 (deep). Start with Tier 1.",
                priority="high",
                applicable_to=["any"],
                code_snippet="""
# Tier 0: Minimal context (~5K tokens)
context = manager.get_context(tier=0)

# Tier 1: Balanced context (~15K tokens)  
context = manager.get_context(tier=1)

# Tier 2: Full context (~50K tokens)
context = manager.get_context(tier=2)
"""
            ),
            
            Guideline(
                id="token_002",
                category=GuidelineCategory.TOKEN_EFFICIENCY,
                title="Check token usage at phase boundaries",
                description="Track token usage at end of every phase. Pause if >70% used.",
                priority="critical",
                applicable_to=["any"],
                example="If 140K+ tokens used of 200K budget, create checkpoint and pause."
            ),
            
            # PROBLEM SOLVING
            Guideline(
                id="problem_001",
                category=GuidelineCategory.PROBLEM_SOLVING,
                title="Search for similar problems first",
                description="Before solving, check if similar problem was solved before.",
                priority="high",
                applicable_to=["any"],
                code_snippet="""
# Python
similar = manager.search(query="import error", memory_type="problem_solving")

# CLI
whitemagic search --query "import error" --type problem_solving
"""
            ),
            
            Guideline(
                id="problem_002",
                category=GuidelineCategory.PROBLEM_SOLVING,
                title="Document solutions as lessons",
                description="When you solve a problem, document it for future reference.",
                priority="medium",
                applicable_to=["any"],
                code_snippet="""
# Python
manager.create_lesson(
    problem="Import error in module X",
    solution="Module was in wrong directory",
    pattern="Check import paths match file structure",
    tags=["import-errors", "python"]
)
"""
            ),
            
            # METRICS TRACKING
            Guideline(
                id="metrics_001",
                category=GuidelineCategory.METRICS_TRACKING,
                title="Track metrics at phase boundaries",
                description="Record token usage, time spent, quality rating at every phase.",
                priority="high",
                applicable_to=["any"],
                code_snippet="""
# Python
from whitemagic.metrics import MetricsCollector
collector = MetricsCollector()
collector.track_metric("token_efficiency", "usage_percent", 49.7)
"""
            ),
            
            # CONSOLIDATION
            Guideline(
                id="consolidation_001",
                category=GuidelineCategory.CONSOLIDATION,
                title="Consolidate every 10 short-term memories",
                description="Keep memory system clean by consolidating regularly.",
                priority="medium",
                applicable_to=["any"],
                code_snippet="""
# Python
manager.consolidate_short_term()

# CLI
whitemagic consolidate

# Automated (via orchestra)
whitemagic orchestra maintain
"""
            ),
            
            # STRATEGIC THINKING (Art of War)
            Guideline(
                id="strategy_001",
                category=GuidelineCategory.STRATEGIC_THINKING,
                title="Assess terrain before acting",
                description="Evaluate task complexity and dependencies before starting.",
                priority="high",
                applicable_to=["any"],
                example="""
ACCESSIBLE: Straightforward → proceed directly
ENTANGLING: Dependencies → resolve first
TEMPORIZING: Need more info → gather intelligence
NARROW: Sequential only → no parallelism
PRECIPITOUS: High risk → extreme caution
DISTANT: Long duration → plan checkpoints
"""
            ),
            
            Guideline(
                id="strategy_002",
                category=GuidelineCategory.STRATEGIC_THINKING,
                title="Check five factors before proceeding",
                description="道 (Dao), 天 (Heaven), 地 (Earth), 將 (General), 法 (Law)",
                priority="high",
                applicable_to=["any"],
                example="""
道 (Dao): Aligned with values?
天 (Heaven): Right timing?
地 (Earth): Have resources?
將 (General): Clear strategy?
法 (Law): Following best practices?

Score >= 0.8: PROCEED
Score >= 0.6: PROCEED_WITH_CAUTION
Score < 0.6: PREPARE_MORE
"""
            ),
        ]
    
    def get_guidelines(
        self, 
        category: Optional[GuidelineCategory] = None,
        priority: Optional[str] = None,
        applicable_to: Optional[str] = None
    ) -> List[Guideline]:
        """Get guidelines filtered by criteria."""
        guidelines = self.guidelines
        
        if category:
            guidelines = [g for g in guidelines if g.category == category]
        
        if priority:
            guidelines = [g for g in guidelines if g.priority == priority]
        
        if applicable_to:
            guidelines = [g for g in guidelines if applicable_to in g.applicable_to or "any" in g.applicable_to]
        
        return guidelines
    
    def get_session_start_protocol(self) -> List[Guideline]:
        """Get critical guidelines for session start."""
        return [
            g for g in self.guidelines 
            if g.category == GuidelineCategory.SESSION_START
            or (g.category == GuidelineCategory.TOKEN_EFFICIENCY and g.priority == "critical")
        ]
    
    def format_for_ai(self, guidelines: List[Guideline] = None) -> str:
        """Format guidelines in AI-friendly text."""
        if guidelines is None:
            guidelines = self.guidelines
        
        output = "# WhiteMagic AI Guidelines\n\n"
        
        # Group by category
        by_category: Dict[GuidelineCategory, List[Guideline]] = {}
        for guideline in guidelines:
            if guideline.category not in by_category:
                by_category[guideline.category] = []
            by_category[guideline.category].append(guideline)
        
        # Format each category
        for category, items in by_category.items():
            output += f"## {category.value.replace('_', ' ').title()}\n\n"
            
            for guideline in sorted(items, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.priority]):
                priority_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "⚪"
                }[guideline.priority]
                
                output += f"### {priority_emoji} {guideline.title}\n"
                output += f"**Priority**: {guideline.priority}\n\n"
                output += f"{guideline.description}\n\n"
                
                if guideline.example:
                    output += f"**Example**:\n```\n{guideline.example}\n```\n\n"
                
                if guideline.code_snippet:
                    output += f"**Code**:\n```python\n{guideline.code_snippet.strip()}\n```\n\n"
        
        return output
    
    def export_to_file(self, filepath: str):
        """Export guidelines to markdown file."""
        content = self.format_for_ai()
        with open(filepath, 'w') as f:
            f.write(content)


def get_ai_guidelines() -> str:
    """Quick function to get all AI guidelines as formatted text."""
    manager = AIGuidelinesManager()
    return manager.format_for_ai()


def get_session_start_guidelines() -> str:
    """Get critical session start guidelines."""
    manager = AIGuidelinesManager()
    guidelines = manager.get_session_start_protocol()
    return manager.format_for_ai(guidelines)
