"""Automation loops for continuous improvement."""

from whitemagic.automation.precommit import PreCommitAutoFix
from whitemagic.automation.test_watcher import TestWatcher

__all__ = ["PreCommitAutoFix", "TestWatcher"]
