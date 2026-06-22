#!/usr/bin/env python3
"""Example: Time-integrated campaign workflow.

Shows how to use PhaseTimer and WorkflowTimer with WhiteMagic campaigns
for tracking phase timing at beginning, during, and end of operations.
"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))

from whitemagic.tools.time_tracking import WorkflowTimer, get_current_time
from whitemagic.tools.time_tracking import get_local_time  # For timezone conversion


def run_timed_campaign_demo():
    """Demo of time-integrated campaign deployment."""
    
    workflow = WorkflowTimer("campaign_demo")
    workflow.start_workflow()
    
    # Phase 1: Pre-flight checks (timed)
    with workflow.phase("pre_flight", {"checks": ["db", "rust", "config"]}):
        import time
        time.sleep(0.3)  # Simulating work
        print("   ✓ DB connection OK")
        print("   ✓ Rust bridge OK")
        print("   ✓ Config loaded")
    
    # Phase 2: Clone army deployment (timed)
    with workflow.phase("deployment", {"army": "alpha", "clones": 10000}):
        time.sleep(1.2)  # Simulating deployment
        print("   ✓ 10K clones deployed")
        print("   ✓ 47 findings collected")
    
    # Phase 3: Analysis (timed)
    with workflow.phase("analysis", {"findings": 47}):
        time.sleep(0.5)
        print("   ✓ Findings categorized")
        print("   ✓ Security scan complete")
    
    # Phase 4: Report generation (timed)
    with workflow.phase("reporting", {"format": "markdown"}):
        time.sleep(0.2)
        print("   ✓ Report saved")
    
    workflow.end_workflow()
    workflow.print_report()
    
    # Store timing report to WhiteMagic memory (optional)
    report = workflow.get_report()
    print("\n💾 Report ready for memory storage:")
    print(f"   Title: campaign_timing_{report['workflow_name']}")
    print(f"   Duration: {report['total_seconds']:.1f}s")
    
    return report


def quick_time_check():
    """Quick time display - can be called at any workflow point."""
    print("\n🕐 Current Times:")
    print(f"   UTC:   {get_current_time()}")
    print(f"   Local: {get_local_time('America/New_York')}")
    print(f"   Pacific: {get_local_time('America/Los_Angeles')}")


if __name__ == "__main__":
    # Show time at workflow start
    quick_time_check()
    
    # Run the timed campaign
    print("\n" + "="*60)
    report = run_timed_campaign_demo()
    
    # Show time at workflow end
    quick_time_check()
    
    print(f"\n📊 Elapsed: {report['total_seconds']:.2f}s")
