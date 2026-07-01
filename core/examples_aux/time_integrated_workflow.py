#!/usr/bin/env python3
"""Example: Time-integrated campaign workflow.

Shows how to use PhaseTimer and WorkflowTimer with WhiteMagic campaigns
for tracking phase timing at beginning, during, and end of operations.
"""

import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from whitemagic.tools.time_tracking import WorkflowTimer, get_current_time
from whitemagic.tools.time_tracking import get_local_time  # For timezone conversion

import logging
logger = logging.getLogger(__name__)


def run_timed_campaign_demo():
    """Demo of time-integrated campaign deployment."""

    workflow = WorkflowTimer("campaign_demo")
    workflow.start_workflow()

    with workflow.phase("pre_flight", {"checks": ["db", "rust", "config"]}):
        import time

        time.sleep(0.3)  # Simulating work
        logger.debug("   ✓ DB connection OK")
        logger.debug("   ✓ Rust bridge OK")
        logger.debug("   ✓ Config loaded")

    with workflow.phase("deployment", {"army": "alpha", "clones": 10000}):
        time.sleep(1.2)  # Simulating deployment
        logger.debug("   ✓ 10K clones deployed")
        logger.debug("   ✓ 47 findings collected")

    with workflow.phase("analysis", {"findings": 47}):
        time.sleep(0.5)
        logger.debug("   ✓ Findings categorized")
        logger.debug("   ✓ Security scan complete")

    with workflow.phase("reporting", {"format": "markdown"}):
        time.sleep(0.2)
        logger.debug("   ✓ Report saved")

    workflow.end_workflow()
    workflow.print_report()

    report = workflow.get_report()
    logger.debug("\n💾 Report ready for memory storage:")
    logger.debug(f"   Title: campaign_timing_{report['workflow_name']}")
    logger.debug(f"   Duration: {report['total_seconds']:.1f}s")

    return report


def quick_time_check():
    """Quick time display - can be called at any workflow point."""
    logger.debug("\n🕐 Current Times:")
    logger.debug(f"   UTC:   {get_current_time()}")
    logger.debug(f"   Local: {get_local_time('America/New_York')}")
    logger.debug(f"   Pacific: {get_local_time('America/Los_Angeles')}")


if __name__ == "__main__":
    # Show time at workflow start
    quick_time_check()

    logger.debug("\n" + "=" * 60)
    report = run_timed_campaign_demo()

    # Show time at workflow end
    quick_time_check()

    logger.debug(f"\n📊 Elapsed: {report['total_seconds']:.2f}s")
