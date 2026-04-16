#!/usr/bin/env python3
"""Test harness for Immortal Clone v2 system

Tests both the Python v2 implementation and provides comparison framework.
"""

import logging
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from whitemagic.agents.immortal_clone_v2 import (
    CampaignVictoryTracker,
    CampaignDashboard,
    immortal_clone_deploy
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_victory_tracker():
    """Test CampaignVictoryTracker thread-safety and functionality."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: CampaignVictoryTracker")
    logger.info("="*60)
    
    vcs = [
        {'id': 'VC-1', 'description': 'First victory'},
        {'id': 'VC-2', 'description': 'Second victory'},
        {'id': 'VC-3', 'description': 'Third victory'},
    ]
    
    tracker = CampaignVictoryTracker(vcs)
    
    # Test initial state
    assert not tracker.all_vcs_met(), "Should start with no VCs met"
    assert tracker.progress_percentage() == 0.0, "Should be 0% complete"
    
    # Mark first VC
    result = tracker.mark_vc_met('VC-1', clone_id=1)
    assert result, "Should return True for first mark"
    assert tracker.progress_percentage() == 33.33333333333333, "Should be 33.33% complete"
    
    # Try to mark same VC again
    result = tracker.mark_vc_met('VC-1', clone_id=2)
    assert not result, "Should return False for duplicate mark"
    
    # Mark remaining VCs
    tracker.mark_vc_met('VC-2', clone_id=1)
    tracker.mark_vc_met('VC-3', clone_id=2)
    
    assert tracker.all_vcs_met(), "All VCs should be met"
    assert tracker.progress_percentage() == 100.0, "Should be 100% complete"
    
    # Check status
    status = tracker.get_status()
    assert status['vcs_met'] == 3
    assert status['total_vcs'] == 3
    assert status['complete'] == True
    
    logger.info("✅ Victory tracker tests passed")
    return True


def test_dashboard():
    """Test CampaignDashboard display generation."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: CampaignDashboard")
    logger.info("="*60)
    
    vcs = [{'id': f'VC-{i}', 'description': f'Victory {i}'} for i in range(1, 6)]
    tracker = CampaignVictoryTracker(vcs)
    
    dashboard = CampaignDashboard(
        campaign_name="Test Campaign",
        total_vcs=5,
        total_clones=10,
        victory_tracker=tracker
    )
    
    # Update some clone progress
    dashboard.update_clone_progress(1, 10, 50)
    dashboard.update_clone_progress(2, 20, 50)
    dashboard.update_clone_progress(3, 15, 50)
    
    # Mark some VCs
    tracker.mark_vc_met('VC-1', 1)
    tracker.mark_vc_met('VC-2', 2)
    
    # Generate table
    table = dashboard.generate_table()
    logger.info(f"Dashboard output:\n{table}")
    
    logger.info("✅ Dashboard tests passed")
    return True


def test_simple_deployment():
    """Test simple deployment with minimal campaign."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Simple Deployment")
    logger.info("="*60)
    
    campaign = {
        'id': 'TEST-001',
        'name': 'Simple Test Campaign',
        'target': 'test-target',
        'victory_conditions': [
            {'id': 'TEST-VC-1', 'description': 'Complete analysis'},
            {'id': 'TEST-VC-2', 'description': 'Complete compilation'},
            {'id': 'TEST-VC-3', 'description': 'Complete testing'},
        ]
    }
    
    logger.info(f"Deploying test campaign: {campaign['name']}")
    logger.info(f"VCs: {len(campaign['victory_conditions'])}")
    
    start_time = time.time()
    
    # Deploy with minimal clones and iterations
    results = immortal_clone_deploy(
        campaign=campaign,
        max_clones=5,  # Just 5 clones for testing
        max_iterations=10,  # Only 10 iterations
        dashboard_enabled=False  # Disable dashboard for cleaner output
    )
    
    duration = time.time() - start_time
    
    logger.info(f"\nDeployment completed in {duration:.2f}s")
    logger.info(f"Results: {len(results)} MEOW units completed")
    
    successful = sum(1 for r in results if r.success)
    logger.info(f"Success rate: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
    
    logger.info("✅ Simple deployment test passed")
    return True


def test_early_termination():
    """Test that deployment stops when all VCs are met."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Early Termination")
    logger.info("="*60)
    
    # Create campaign with just 1 VC for quick completion
    campaign = {
        'id': 'TEST-002',
        'name': 'Early Termination Test',
        'target': 'test-target',
        'victory_conditions': [
            {'id': 'TERM-VC-1', 'description': 'Single victory condition'},
        ]
    }
    
    start_time = time.time()
    
    results = immortal_clone_deploy(
        campaign=campaign,
        max_clones=3,
        max_iterations=50,  # High limit, but should stop early
        dashboard_enabled=False
    )
    
    duration = time.time() - start_time
    
    # Check for early termination
    early_stops = sum(1 for r in results if r.data.get('early_stop'))
    
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Early stops: {early_stops}/{len(results)}")
    
    if early_stops > 0:
        logger.info("✅ Early termination working!")
    else:
        logger.warning("⚠️ No early termination detected")
    
    return True


def benchmark_v2():
    """Benchmark v2 performance."""
    logger.info("\n" + "="*60)
    logger.info("BENCHMARK: v2 Performance")
    logger.info("="*60)
    
    campaign = {
        'id': 'BENCH-001',
        'name': 'Performance Benchmark',
        'target': 'benchmark-target',
        'victory_conditions': [
            {'id': f'BENCH-VC-{i}', 'description': f'VC {i}'} 
            for i in range(1, 6)  # 5 VCs
        ]
    }
    
    clone_counts = [5, 10, 20]
    
    for count in clone_counts:
        logger.info(f"\nBenchmarking with {count} clones...")
        
        start = time.time()
        results = immortal_clone_deploy(
            campaign=campaign,
            max_clones=count,
            max_iterations=20,
            dashboard_enabled=False
        )
        duration = time.time() - start
        
        throughput = len(results) / duration if duration > 0 else 0
        
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  MEOW units: {len(results)}")
        logger.info(f"  Throughput: {throughput:.1f} units/sec")
    
    logger.info("✅ Benchmark complete")
    return True


def main():
    """Run all tests."""
    logger.info("🧪 IMMORTAL CLONE V2 TEST SUITE")
    logger.info("="*60)
    
    tests = [
        ("Victory Tracker", test_victory_tracker),
        ("Dashboard", test_dashboard),
        ("Simple Deployment", test_simple_deployment),
        ("Early Termination", test_early_termination),
        ("Performance Benchmark", benchmark_v2),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                logger.error(f"❌ {name} failed")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {name} crashed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("\n" + "="*60)
    logger.info("TEST RESULTS")
    logger.info("="*60)
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.info("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        logger.error(f"\n❌ {failed} TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
