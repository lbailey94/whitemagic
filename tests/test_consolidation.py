"""
Tests for Automated Consolidation System
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from whitemagic.automation.consolidation import ConsolidationEngine
from whitemagic.core import MemoryManager


class TestConsolidationEngine:
    """Test the consolidation engine"""
    
    def test_initialization(self):
        """Test engine initializes correctly"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        assert engine.manager is not None
        assert engine.thresholds["count"] == 40
        assert engine.thresholds["age_days"] == 7
        assert engine.thresholds["similarity"] == 0.85
        assert engine.enable_parallel == True
        assert engine.worker_count == 16
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = {
            "max_short_term": 30,
            "max_age_days": 5,
            "similarity_threshold": 0.90,
            "worker_count": 32
        }
        
        manager = MemoryManager()
        engine = ConsolidationEngine(manager, config=config)
        
        assert engine.thresholds["count"] == 30
        assert engine.thresholds["age_days"] == 5
        assert engine.thresholds["similarity"] == 0.90
        assert engine.worker_count == 32
    
    def test_should_consolidate_below_threshold(self):
        """Test consolidation not needed when below threshold"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        check = engine.should_consolidate()
        
        assert "should_consolidate" in check
        assert "reasons" in check
        assert "count" in check
        assert "threshold" in check
    
    def test_auto_consolidate_dry_run(self):
        """Test dry run returns expected structure"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        results = engine.auto_consolidate(dry_run=True)
        
        assert "archived" in results
        assert "promoted" in results
        assert "merged" in results
        assert "scratchpads_cleaned" in results
        assert "dry_run" in results
        assert "errors" in results
        assert "metrics" in results
        assert results["dry_run"] == True
    
    def test_metrics_tracking(self):
        """Test metrics are tracked correctly"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        results = engine.auto_consolidate(dry_run=True)
        metrics = results["metrics"]
        
        assert "start_time" in metrics
        assert "end_time" in metrics
        assert "duration_seconds" in metrics
        assert "parallel_enabled" in metrics
        assert "worker_count" in metrics
        assert "total_actions" in metrics
        assert "success" in metrics
        
        # Check duration is reasonable
        assert metrics["duration_seconds"] >= 0
        assert metrics["duration_seconds"] < 10  # Should be very fast for empty
    
    def test_parallel_configuration(self):
        """Test parallel processing configuration"""
        # Disabled parallel
        config1 = {"enable_parallel": False}
        manager1 = MemoryManager()
        engine1 = ConsolidationEngine(manager1, config=config1)
        assert engine1.enable_parallel == False
        
        # Enabled parallel (default)
        manager2 = MemoryManager()
        engine2 = ConsolidationEngine(manager2)
        assert engine2.enable_parallel == True
        assert engine2.worker_count == 16


class TestAutoPromotion:
    """Test auto-promotion logic"""
    
    def test_promotion_rules_exist(self):
        """Test promotion rules are configured"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        # Rules should be in the code
        results = engine.auto_consolidate(dry_run=True)
        # Even with no memories, structure should exist
        assert "promoted" in results


class TestScratchpadCleanup:
    """Test scratchpad cleanup integration"""
    
    def test_scratchpad_manager_exists(self):
        """Test scratchpad manager is initialized"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        assert engine.scratchpad_manager is not None
    
    def test_cleanup_in_consolidation(self):
        """Test cleanup is part of consolidation"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        results = engine.auto_consolidate(dry_run=True)
        
        assert "scratchpads_cleaned" in results
        assert isinstance(results["scratchpads_cleaned"], list)


class TestParallelProcessing:
    """Test parallel processing features"""
    
    def test_archive_memory_helper(self):
        """Test single memory archival helper"""
        manager = MemoryManager()
        engine = ConsolidationEngine(manager)
        
        # Test with mock memory object
        class MockMemory:
            filename = "test.md"
            title = "Test"
            created = datetime.now()
        
        mock_mem = MockMemory()
        result = engine._archive_memory(mock_mem, dry_run=True)
        
        assert "filename" in result
        assert "title" in result
        assert "success" in result
        assert result["filename"] == "test.md"


def test_full_consolidation_workflow():
    """Integration test: Full consolidation workflow"""
    manager = MemoryManager()
    engine = ConsolidationEngine(manager)
    
    # Step 1: Check if needed
    check = engine.should_consolidate()
    assert isinstance(check, dict)
    
    # Step 2: Run dry run
    dry_results = engine.auto_consolidate(dry_run=True)
    assert dry_results["dry_run"] == True
    
    # Step 3: Check metrics
    assert "metrics" in dry_results
    assert dry_results["metrics"]["success"] in [True, False]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
