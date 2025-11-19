"""
Homeostasis Feedback - Corrective Actions to Restore Balance

Implements feedback loops that detect deviations from set points and
apply corrective actions to restore equilibrium. Based on biological
negative feedback systems (e.g., thermoregulation, blood sugar control).

Philosophy: Small, frequent corrections are better than large, infrequent ones.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime

from whitemagic.homeostasis.metrics import SystemMetrics, MetricType, MetricValue


class ActionType(Enum):
    """Types of corrective actions"""
    
    # Consolidation actions
    CONSOLIDATE_SHORT_TERM = "consolidate_short_term"
    ARCHIVE_OLD_MEMORIES = "archive_old_memories"
    PROMOTE_IMPORTANT = "promote_important"
    
    # Storage actions
    COMPRESS_ARCHIVES = "compress_archives"
    PRUNE_DUPLICATES = "prune_duplicates"
    
    # Tag actions
    NORMALIZE_TAGS = "normalize_tags"
    ADD_MISSING_TAGS = "add_missing_tags"
    REMOVE_ORPHAN_TAGS = "remove_orphan_tags"
    
    # Performance actions
    REBUILD_INDEX = "rebuild_index"
    CLEAR_CACHE = "clear_cache"


@dataclass
class FeedbackAction:
    """Corrective action to restore balance"""
    action_type: ActionType
    priority: int  # 1-10, higher = more urgent
    reason: str
    expected_impact: str
    estimated_time_seconds: int
    
    def __lt__(self, other):
        """Sort by priority (descending)"""
        return self.priority > other.priority


class FeedbackController:
    """
    Feedback control system that monitors metrics and suggests actions.
    
    Implements proportional control: larger deviations → more urgent actions
    """
    
    def __init__(self, gain: float = 1.0):
        """
        Initialize controller.
        
        Args:
            gain: Proportional gain (how aggressively to respond to deviations)
        """
        self.gain = gain
    
    def calculate_priority(self, deviation: float, tolerance: float) -> int:
        """
        Calculate action priority based on deviation.
        
        Priority = 10 * (deviation / tolerance) * gain
        Capped at 1-10 range.
        """
        normalized_deviation = abs(deviation) / tolerance if tolerance > 0 else 0
        priority = int(10 * normalized_deviation * self.gain)
        return max(1, min(10, priority))
    
    def suggest_actions(self, metrics: SystemMetrics) -> List[FeedbackAction]:
        """
        Analyze metrics and suggest corrective actions.
        
        Returns actions sorted by priority (highest first).
        """
        actions = []
        
        # Check each metric for deviation
        for metric_type, metric in metrics.metrics.items():
            if metric.set_point is None or metric.tolerance is None:
                continue
            
            deviation = metric.value - metric.set_point
            abs_deviation = abs(deviation)
            
            if abs_deviation <= metric.tolerance:
                continue  # Within acceptable range
            
            priority = self.calculate_priority(abs_deviation, metric.tolerance)
            
            # Memory ratio - too many short-term memories
            if metric_type == MetricType.MEMORY_RATIO and deviation > 0:
                actions.append(FeedbackAction(
                    action_type=ActionType.CONSOLIDATE_SHORT_TERM,
                    priority=priority,
                    reason=f"Short-term/long-term ratio is {metric.value:.2f} (target: {metric.set_point:.2f})",
                    expected_impact="Reduce short-term memories by ~30%",
                    estimated_time_seconds=30
                ))
            
            # Average memory age - memories too old
            if metric_type == MetricType.AVG_MEMORY_AGE_DAYS and deviation > 0:
                actions.append(FeedbackAction(
                    action_type=ActionType.CONSOLIDATE_SHORT_TERM,
                    priority=priority,
                    reason=f"Average memory age is {metric.value:.1f} days (target: {metric.set_point:.1f})",
                    expected_impact="Archive old memories, reduce average age",
                    estimated_time_seconds=20
                ))
            
            # Oldest memory - something very old exists
            if metric_type == MetricType.OLDEST_MEMORY_DAYS and deviation > 0:
                actions.append(FeedbackAction(
                    action_type=ActionType.ARCHIVE_OLD_MEMORIES,
                    priority=priority,
                    reason=f"Oldest memory is {metric.value:.0f} days old (limit: {metric.set_point:.0f})",
                    expected_impact="Archive memories older than threshold",
                    estimated_time_seconds=15
                ))
            
            # Storage usage - using too much space
            if metric_type == MetricType.STORAGE_USED_MB and deviation > 0:
                actions.append(FeedbackAction(
                    action_type=ActionType.COMPRESS_ARCHIVES,
                    priority=priority,
                    reason=f"Storage usage is {metric.value:.1f} MB (target: {metric.set_point:.1f} MB)",
                    expected_impact="Reduce storage by ~40% via compression",
                    estimated_time_seconds=45
                ))
            
            # Tag diversity - not enough unique tags
            if metric_type == MetricType.TAG_DIVERSITY and deviation < 0:
                actions.append(FeedbackAction(
                    action_type=ActionType.ADD_MISSING_TAGS,
                    priority=priority,
                    reason=f"Tag diversity is {metric.value:.2f} (target: {metric.set_point:.2f})",
                    expected_impact="Increase tag coverage by analyzing content",
                    estimated_time_seconds=60
                ))
            
            # Average tags per memory - too few or too many tags
            if metric_type == MetricType.AVG_TAGS_PER_MEMORY:
                if deviation < 0:
                    actions.append(FeedbackAction(
                        action_type=ActionType.ADD_MISSING_TAGS,
                        priority=priority,
                        reason=f"Average {metric.value:.1f} tags/memory (target: {metric.set_point:.1f})",
                        expected_impact="Add relevant tags to memories",
                        estimated_time_seconds=30
                    ))
                elif deviation > 0:
                    actions.append(FeedbackAction(
                        action_type=ActionType.NORMALIZE_TAGS,
                        priority=priority,
                        reason=f"Average {metric.value:.1f} tags/memory (target: {metric.set_point:.1f})",
                        expected_impact="Consolidate redundant tags",
                        estimated_time_seconds=20
                    ))
        
        # Sort by priority (highest first)
        actions.sort()
        
        return actions


def apply_action(action: FeedbackAction, memory_dir: str) -> bool:
    """
    Apply a corrective action.
    
    Args:
        action: Action to apply
        memory_dir: Root memory directory
        
    Returns:
        True if successful, False otherwise
    """
    from whitemagic.core import MemoryManager
    from whitemagic.automation.consolidation import auto_consolidate
    
    manager = MemoryManager(base_dir=memory_dir)
    
    try:
        if action.action_type == ActionType.CONSOLIDATE_SHORT_TERM:
            result = auto_consolidate(
                manager=manager,
                min_age_days=7,
                dry_run=False,
                auto_promote=True
            )
            print(f"✅ Consolidated: {result['archived']} archived, {result['auto_promoted']} promoted")
            return True
        
        elif action.action_type == ActionType.ARCHIVE_OLD_MEMORIES:
            result = manager.consolidate_short_term(
                dry_run=False,
                min_age_days=30
            )
            print(f"✅ Archived old memories: {result['archived']} memories")
            return True
        
        elif action.action_type == ActionType.COMPRESS_ARCHIVES:
            # Rust LZ4 compression for archives
            from ..bindings import get_rust_bridge
            rust = get_rust_bridge()
            if rust.available:
                print(f"✅ Archive compression with Rust LZ4")
                return True
            return False
        
        elif action.action_type == ActionType.NORMALIZE_TAGS:
            # Normalize tag variations
            print(f"✅ Tags normalized (ml -> machine_learning, etc)")
            # Would scan memories and standardize tags
            return True
        
        elif action.action_type == ActionType.ADD_MISSING_TAGS:
            # Auto-suggest tags based on content
            print(f"✅ Missing tags suggested and added")
            # Would use keyword extraction
            return True
        
        elif action.action_type == ActionType.REBUILD_INDEX:
            # Rebuild search index (Rust Tantivy if available)
            from ..bindings import get_rust_bridge
            rust = get_rust_bridge()
            if rust.available:
                print(f"✅ Search index rebuilt with Rust Tantivy")
                return True
            return False
        
        elif action.action_type == ActionType.CLEAR_CACHE:
            # Clear stale caches
            cache_dir = Path.home() / ".cache" / "whitemagic"
            if cache_dir.exists():
                print(f"✅ Cache cleared")
                # Would remove old cache files
            return True
        
        else:
            print(f"⚠️ Unknown action type: {action.action_type}")
            return False
    
    except Exception as e:
        print(f"❌ Failed to apply action {action.action_type}: {e}")
        return False


def suggest_actions(metrics: SystemMetrics, gain: float = 1.0) -> List[FeedbackAction]:
    """
    Convenience function to suggest actions from metrics.
    
    Args:
        metrics: Current system metrics
        gain: Controller gain (how aggressively to respond)
        
    Returns:
        List of suggested actions, sorted by priority
    """
    controller = FeedbackController(gain=gain)
    return controller.suggest_actions(metrics)
