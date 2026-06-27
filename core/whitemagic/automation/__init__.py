"""WhiteMagic Automation Module
============================

Autonomous processes that run without human intervention.
Humans are "on" the loop, not "in" it.
"""

from .consolidation import ConsolidationEngine, get_consolidation
from .daemon import (
    AutomationDaemon,
    AutomationTask,
    ResonanceCascade,
    TaskFrequency,
    TaskPriority,
    get_automation_daemon,
)
from .daily_narrative import check_daily_journal
from .incremental_backup import IncrementalBackup, get_backup
from .orchestra import AutomationOrchestra, get_orchestra
from .precommit import PreCommitAutoFix
from .test_watcher import TestWatcher
from .tool_sharpening import ToolSharpening, get_tool_sharpening
from .triggers import ConsolidationTriggers, get_triggers

__all__ = [
    "AutomationDaemon",
    "AutomationTask",
    "ResonanceCascade",
    "TaskFrequency",
    "TaskPriority",
    "get_automation_daemon",
    "ConsolidationEngine",
    "get_consolidation",
    "PreCommitAutoFix",
    "AutomationOrchestra",
    "get_orchestra",
    "ConsolidationTriggers",
    "get_triggers",
    "IncrementalBackup",
    "get_backup",
    "TestWatcher",
    "ToolSharpening",
    "get_tool_sharpening",
    "check_daily_journal",
]
