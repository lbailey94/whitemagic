"""Comprehensive tests for Phase 1 v2.2.9 features."""

import pytest
import tempfile
from pathlib import Path
import json

# Feature 1: Token Tracking
def test_token_estimation():
    """Test token estimation with tiktoken."""
    from whitemagic.metrics import estimate_tokens
    
    # Test basic estimation
    text = "Hello, world!"
    tokens = estimate_tokens(text)
    assert tokens > 0
    assert isinstance(tokens, int)
    
    # Test longer text
    long_text = "This is a much longer piece of text. " * 100
    long_tokens = estimate_tokens(long_text)
    assert long_tokens > tokens
    
    # Test empty string
    empty_tokens = estimate_tokens("")
    assert empty_tokens == 0


def test_metrics_collector_token_tracking():
    """Test MetricsCollector context buffer and token counting."""
    from whitemagic.metrics import MetricsCollector
    
    collector = MetricsCollector()
    
    # Test context buffer
    collector.add_context("This is some context text")
    collector.add_context("More context here")
    
    # Test task tracking with tokens
    with collector.track_task("test_task", phase="test"):
        pass
    
    # Get summary
    summary = collector.get_summary()
    assert "tasks" in summary
    assert summary["tasks"]["count"] > 0
    
    # Verify token tracking
    assert "token_tracking" in summary
    assert summary["token_tracking"]["available"] is True
    
    # Clear context
    collector.clear_context()


# Feature 2: Smart Context Preloading
def test_context_preloader_role_prediction():
    """Test role-based memory prediction."""
    from whitemagic.context_preload import ContextPreloader, ROLE_MEMORY_MAP
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        preloader = ContextPreloader(base_dir)
        
        # Test role prediction
        bug_fix_tags = preloader.get_predicted_tags("bug-fix")
        assert "debugging" in bug_fix_tags
        assert "error-patterns" in bug_fix_tags
        
        feature_tags = preloader.get_predicted_tags("feature")
        assert "architecture" in feature_tags
        assert "api-design" in feature_tags
        
        # Test unknown role
        unknown_tags = preloader.get_predicted_tags("unknown-role")
        assert unknown_tags == []


def test_context_preloader_tag_extraction():
    """Test tag extraction from memory files."""
    from whitemagic.context_preload import ContextPreloader
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        mem_dir = base_dir / "memory" / "short_term"
        mem_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test memory with tags
        mem_file = mem_dir / "test_memory.md"
        mem_file.write_text("""# Test Memory

Tags: debugging, testing, bug-fix

This is a test memory.
""")
        
        preloader = ContextPreloader(base_dir)
        tags = preloader._extract_tags(mem_file)
        
        assert "debugging" in tags
        assert "testing" in tags
        assert "bug-fix" in tags


def test_context_preloader_preload():
    """Test memory preloading."""
    from whitemagic.context_preload import ContextPreloader
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        mem_dir = base_dir / "memory" / "short_term"
        mem_dir.mkdir(parents=True, exist_ok=True)
        
        # Create memory matching bug-fix role
        mem_file = mem_dir / "bug_memory.md"
        mem_file.write_text("# Bug Fix\n\nTags: debugging, error-patterns\n\nContent here.")
        
        preloader = ContextPreloader(base_dir)
        preloaded = preloader.preload_for_role("bug-fix", max_memories=5)
        
        assert len(preloaded) >= 1
        assert "short_term/bug_memory.md" in preloaded


# Feature 3: Terminal Multiplexing
def test_terminal_multiplex_create_pad():
    """Test creating scratchpad channels."""
    from whitemagic.agentic.terminal_multiplex import TerminalMultiplex
    
    with tempfile.TemporaryDirectory() as tmpdir:
        multiplex = TerminalMultiplex(Path(tmpdir))
        
        # Create new pad
        pad = multiplex.create_pad("test-pad", "Test task")
        assert pad is not None
        assert "test-pad" in multiplex.active_pads
        assert multiplex.current_pad == "test-pad"
        
        # Try to create duplicate (should fail)
        with pytest.raises(ValueError):
            multiplex.create_pad("test-pad", "Another task")


def test_terminal_multiplex_switch_pad():
    """Test switching between scratchpad channels."""
    from whitemagic.agentic.terminal_multiplex import TerminalMultiplex
    
    with tempfile.TemporaryDirectory() as tmpdir:
        multiplex = TerminalMultiplex(Path(tmpdir))
        
        # Create multiple pads
        multiplex.create_pad("pad1", "Task 1")
        multiplex.create_pad("pad2", "Task 2")
        
        # Switch to pad1
        pad = multiplex.switch_pad("pad1")
        assert multiplex.current_pad == "pad1"
        
        # Switch to pad2
        pad = multiplex.switch_pad("pad2")
        assert multiplex.current_pad == "pad2"
        
        # Try to switch to non-existent pad
        with pytest.raises(ValueError):
            multiplex.switch_pad("nonexistent")


def test_terminal_multiplex_list_pads():
    """Test listing scratchpad channels."""
    from whitemagic.agentic.terminal_multiplex import TerminalMultiplex
    
    with tempfile.TemporaryDirectory() as tmpdir:
        multiplex = TerminalMultiplex(Path(tmpdir))
        
        # No pads initially
        pads = multiplex.list_pads()
        assert len(pads) == 0
        
        # Create pads
        multiplex.create_pad("pad1", "Task 1")
        multiplex.create_pad("pad2", "Task 2")
        
        # List pads
        pads = multiplex.list_pads()
        assert len(pads) == 2
        assert any(p["name"] == "pad1" for p in pads)
        assert any(p["name"] == "pad2" for p in pads)
        assert any(p["is_current"] for p in pads)  # One should be current


def test_terminal_multiplex_close_pad():
    """Test closing scratchpad channels."""
    from whitemagic.agentic.terminal_multiplex import TerminalMultiplex
    
    with tempfile.TemporaryDirectory() as tmpdir:
        multiplex = TerminalMultiplex(Path(tmpdir))
        
        # Create and close pad (without finalize)
        multiplex.create_pad("test-pad", "Test")
        multiplex.close_pad("test-pad", finalize_to_memory=False)
        
        assert "test-pad" not in multiplex.active_pads
        assert multiplex.current_pad is None


# Feature 4: Confidence Learning
def test_confidence_learner_record_outcome():
    """Test recording confidence outcomes."""
    from whitemagic.agentic.confidence_learning import ConfidenceLearner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = ConfidenceLearner(Path(tmpdir))
        
        # Record successful outcome
        learner.record_outcome(
            task_id="task1",
            task_name="Fix bug",
            predicted_confidence=0.8,
            actual_success=True,
            factors={"has_tests": 0.9, "tests_pass": 1.0},
            category="bug-fix",
        )
        
        assert len(learner.outcomes) == 1
        assert learner.outcomes[0].task_id == "task1"
        assert learner.outcomes[0].predicted_confidence == 0.8
        assert learner.outcomes[0].actual_success is True


def test_confidence_learner_calibration_stats():
    """Test calibration statistics calculation."""
    from whitemagic.agentic.confidence_learning import ConfidenceLearner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = ConfidenceLearner(Path(tmpdir))
        
        # Record mixed outcomes
        learner.record_outcome("t1", "Task 1", 0.9, True, {})  # Correct high confidence
        learner.record_outcome("t2", "Task 2", 0.9, False, {})  # Over-confident
        learner.record_outcome("t3", "Task 3", 0.3, False, {})  # Correct low confidence
        learner.record_outcome("t4", "Task 4", 0.3, True, {})  # Under-confident
        
        stats = learner.get_calibration_stats()
        
        assert stats["total_predictions"] == 4
        assert stats["accuracy"] == 0.5  # 2/4 correct
        assert stats["over_confidence_rate"] == 0.25  # 1/4
        assert stats["under_confidence_rate"] == 0.25  # 1/4


def test_confidence_learner_factor_analysis():
    """Test factor analysis."""
    from whitemagic.agentic.confidence_learning import ConfidenceLearner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = ConfidenceLearner(Path(tmpdir))
        
        # Record outcomes with varying factors
        learner.record_outcome("t1", "Task 1", 0.8, True, {"has_tests": 0.9})
        learner.record_outcome("t2", "Task 2", 0.8, True, {"has_tests": 0.8})
        learner.record_outcome("t3", "Task 3", 0.5, False, {"has_tests": 0.2})
        learner.record_outcome("t4", "Task 4", 0.4, False, {"has_tests": 0.1})
        
        analysis = learner.analyze_factors()
        
        assert "has_tests" in analysis
        # High has_tests should correlate with success
        assert analysis["has_tests"]["high_success_rate"] > analysis["has_tests"]["low_success_rate"]


def test_confidence_learner_auto_calibrate():
    """Test auto-calibration."""
    from whitemagic.agentic.confidence_learning import ConfidenceLearner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = ConfidenceLearner(Path(tmpdir))
        
        # Record 10+ outcomes for calibration
        for i in range(12):
            success = i % 2 == 0  # Alternate success/failure
            has_tests_score = 0.9 if success else 0.2
            learner.record_outcome(
                f"t{i}",
                f"Task {i}",
                0.7,
                success,
                {"has_tests": has_tests_score, "tests_pass": 0.5},
                category="test",
            )
        
        # Calibrate
        old_weights = learner.weights.copy()
        new_weights = learner.auto_calibrate(min_samples=10)
        
        assert new_weights is not None
        assert "has_tests" in new_weights
        # Weights should sum to approximately 1.0
        assert 0.95 <= sum(new_weights.values()) <= 1.05


def test_confidence_learner_category_stats():
    """Test category-specific statistics."""
    from whitemagic.agentic.confidence_learning import ConfidenceLearner
    
    with tempfile.TemporaryDirectory() as tmpdir:
        learner = ConfidenceLearner(Path(tmpdir))
        
        # Record outcomes in different categories
        learner.record_outcome("t1", "Bug fix", 0.8, True, {}, category="bug-fix")
        learner.record_outcome("t2", "Feature", 0.6, False, {}, category="feature")
        learner.record_outcome("t3", "Bug fix 2", 0.9, True, {}, category="bug-fix")
        
        bug_fix_stats = learner.get_category_stats("bug-fix")
        
        assert bug_fix_stats["total_predictions"] == 2
        assert bug_fix_stats["success_rate"] == 1.0  # Both succeeded
        
        feature_stats = learner.get_category_stats("feature")
        assert feature_stats["total_predictions"] == 1
        assert feature_stats["success_rate"] == 0.0  # Failed


# Integration Tests
def test_preload_with_generate_context():
    """Test context preloading integration with MemoryManager."""
    from whitemagic import MemoryManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = MemoryManager(base_dir=tmpdir)
        
        # Create memory
        manager.create_memory(
            title="Bug Fix Guide",
            content="How to fix bugs",
            memory_type="short_term",
            tags=["debugging", "bug-fix"],
        )
        
        # Generate context with role
        context = manager.generate_context_summary(tier=0, role="bug-fix")
        
        assert "Bug Fix Guide" in context or "bug-fix" in context.lower()


def test_cli_commands_load():
    """Test that all new CLI commands are registered."""
    from whitemagic.cli_app import COMMAND_HANDLERS
    
    # Check Phase 1 commands are registered
    assert "pad-new" in COMMAND_HANDLERS
    assert "pad-switch" in COMMAND_HANDLERS
    assert "pad-list" in COMMAND_HANDLERS
    assert "pad-show" in COMMAND_HANDLERS
    assert "pad-close" in COMMAND_HANDLERS
    assert "confidence-record" in COMMAND_HANDLERS
    assert "confidence-stats" in COMMAND_HANDLERS
    assert "confidence-calibrate" in COMMAND_HANDLERS


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
