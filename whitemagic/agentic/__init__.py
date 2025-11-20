"""
WhiteMagic Agentic Execution System

Enables AI agents to operate with confidence-based autonomy,
reducing human intervention while maintaining safety and quality.

Philosophy:
- Trust through transparency
- Jazz collaboration, not micromanagement
- Confidence-based execution
- Learn from metrics
- Self-improve continuously

Core Components:
- Confidence assessment
- Terminal-based reasoning
- Autonomous task execution
- Progress tracking
"""

from whitemagic.agentic.confidence import (
    AgenticExecutor,
    ConfidenceAssessor,
    ConfidenceLevel,
)
from whitemagic.agentic.terminal_reasoning import (
    TerminalDocumentWriter,
    TerminalReasoner,
    TerminalTestAnalyzer,
)
from whitemagic.agentic.terminal_scratchpad import TerminalScratchpad
from whitemagic.agentic.terminal_multiplex import (
    TerminalMultiplex,
    create_pad,
    switch_pad,
    list_pads,
)
from whitemagic.agentic.confidence_learning import (
    ConfidenceLearner,
    ConfidenceOutcome,
    record_outcome,
    auto_calibrate,
)

__all__ = [
    "ConfidenceLevel",
    "ConfidenceAssessor",
    "AgenticExecutor",
    "TerminalReasoner",
    "TerminalDocumentWriter",
    "TerminalTestAnalyzer",
    "TerminalScratchpad",
    "TerminalMultiplex",
    "create_pad",
    "switch_pad",
    "list_pads",
    "ConfidenceLearner",
    "ConfidenceOutcome",
    "record_outcome",
    "auto_calibrate",
]

__version__ = "2.6.5"
