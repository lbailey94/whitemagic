"""
Test the consolidation fixes from the latest independent review.

Verifies:
1. min_age_days parameter is accepted by consolidate_short_term()
2. API returns auto_promoted count correctly
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from whitemagic import MemoryManager


def test_consolidate_short_term_accepts_min_age_days():
    """Verify consolidate_short_term accepts min_age_days parameter."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(base_dir=temp_dir)
        
        # Should not raise TypeError
        result = manager.consolidate_short_term(
            dry_run=True,
            min_age_days=30
        )
        
        assert "archived" in result
        assert "auto_promoted" in result
        assert "dry_run" in result
        assert result["dry_run"] is True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_consolidate_short_term_uses_min_age_days():
    """Verify min_age_days actually controls consolidation age."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(base_dir=temp_dir)
        
        # Create a memory that's 5 days old
        memory_path = manager.create_memory(
            title="Test Memory",
            content="Content",
            memory_type="short_term",
            tags=[]
        )
        
        # Make it appear 5 days old
        old_time = (datetime.now() - timedelta(days=5)).timestamp()
        memory_path.touch()
        import os
        os.utime(memory_path, (old_time, old_time))
        
        # Should NOT consolidate with min_age_days=10 (memory is only 5 days old)
        result = manager.consolidate_short_term(dry_run=True, min_age_days=10)
        assert result["archived"] == 0
        
        # Should consolidate with min_age_days=3 (memory is 5 days old)
        result = manager.consolidate_short_term(dry_run=True, min_age_days=3)
        assert result["archived"] == 1
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_consolidate_returns_auto_promoted_key():
    """Verify consolidation result includes auto_promoted key."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(base_dir=temp_dir)
        
        # Create memory with promotion tag
        memory_path = manager.create_memory(
            title="Important Memory",
            content="Critical content",
            memory_type="short_term",
            tags=["proven"]  # Default promotion tag
        )
        
        # Make it old enough to consolidate
        old_time = (datetime.now() - timedelta(days=60)).timestamp()
        import os
        os.utime(memory_path, (old_time, old_time))
        
        # Consolidate (dry run)
        result = manager.consolidate_short_term(dry_run=True, min_age_days=30)
        
        # Verify auto_promoted key exists
        assert "auto_promoted" in result
        assert "promoted_files" in result
        
        # With dry_run=True and a proven tag, should show 1 would be promoted
        # (but not actually promote)
        assert result["auto_promoted"] == 0  # Dry run doesn't promote
        assert result["archived"] == 1  # But would archive
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_api_response_uses_auto_promoted():
    """
    Integration test: Verify API consolidation response uses auto_promoted.
    
    This would be a full API test but we'll verify the key mapping works.
    """
    # The fix changes app.py to look for result.get("auto_promoted", 0)
    # This test verifies the core method returns that key
    
    temp_dir = tempfile.mkdtemp()
    try:
        manager = MemoryManager(base_dir=temp_dir)
        result = manager.consolidate_short_term(dry_run=True)
        
        # Verify the result has the keys the API expects
        assert "archived" in result
        assert "auto_promoted" in result  # This is what API now looks for
        assert "dry_run" in result
        
        # Verify it does NOT have "promoted" (old key)
        assert "promoted" not in result
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run tests manually
    print("Running consolidation fix tests...\n")
    
    try:
        test_consolidate_short_term_accepts_min_age_days()
        print("✅ test_consolidate_short_term_accepts_min_age_days")
    except Exception as e:
        print(f"❌ test_consolidate_short_term_accepts_min_age_days: {e}")
    
    try:
        test_consolidate_short_term_uses_min_age_days()
        print("✅ test_consolidate_short_term_uses_min_age_days")
    except Exception as e:
        print(f"❌ test_consolidate_short_term_uses_min_age_days: {e}")
    
    try:
        test_consolidate_returns_auto_promoted_key()
        print("✅ test_consolidate_returns_auto_promoted_key")
    except Exception as e:
        print(f"❌ test_consolidate_returns_auto_promoted_key: {e}")
    
    try:
        test_api_response_uses_auto_promoted()
        print("✅ test_api_response_uses_auto_promoted")
    except Exception as e:
        print(f"❌ test_api_response_uses_auto_promoted: {e}")
    
    print("\nAll tests completed!")
