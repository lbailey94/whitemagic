"""
Homeostasis Metrics - Measure System Balance Points

Tracks key metrics for maintaining system equilibrium:
- Memory distribution (short-term vs long-term)
- Storage usage and efficiency
- Query performance
- Tag diversity and coverage
- Consolidation health
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import json


class MetricType(Enum):
    """Types of homeostasis metrics"""
    
    # Memory Distribution
    MEMORY_COUNT_SHORT = "memory_count_short"
    MEMORY_COUNT_LONG = "memory_count_long"
    MEMORY_RATIO = "memory_ratio"  # short:long ratio
    
    # Storage Metrics
    STORAGE_USED_MB = "storage_used_mb"
    STORAGE_USAGE_PCT = "storage_usage_pct"
    COMPRESSION_RATIO = "compression_ratio"
    
    # Age Metrics
    AVG_MEMORY_AGE_DAYS = "avg_memory_age_days"
    OLDEST_MEMORY_DAYS = "oldest_memory_days"
    
    # Tag Metrics
    TAG_COUNT_TOTAL = "tag_count_total"
    TAG_DIVERSITY = "tag_diversity"  # Unique tags / total memories
    AVG_TAGS_PER_MEMORY = "avg_tags_per_memory"
    
    # Performance Metrics
    CONSOLIDATION_HEALTH = "consolidation_health"  # Days since last consolidation
    QUERY_CACHE_HIT_RATE = "query_cache_hit_rate"


@dataclass
class MetricValue:
    """Single metric measurement"""
    metric_type: MetricType
    value: float
    unit: str
    timestamp: datetime
    set_point: Optional[float] = None  # Target value
    tolerance: Optional[float] = None  # Acceptable deviation


@dataclass
class SystemMetrics:
    """Complete system metrics snapshot"""
    timestamp: datetime
    metrics: Dict[MetricType, MetricValue]
    
    def is_balanced(self) -> bool:
        """Check if all metrics are within tolerance"""
        for metric in self.metrics.values():
            if metric.set_point is not None and metric.tolerance is not None:
                deviation = abs(metric.value - metric.set_point)
                if deviation > metric.tolerance:
                    return False
        return True
    
    def get_deviations(self) -> List[MetricValue]:
        """Get metrics that are out of balance"""
        deviations = []
        for metric in self.metrics.values():
            if metric.set_point is not None and metric.tolerance is not None:
                deviation = abs(metric.value - metric.set_point)
                if deviation > metric.tolerance:
                    deviations.append(metric)
        return deviations


def collect_metrics(memory_dir: Path) -> SystemMetrics:
    """
    Collect all homeostasis metrics from the memory system.
    
    Args:
        memory_dir: Root memory directory
        
    Returns:
        Complete system metrics snapshot
    """
    from whitemagic.core import MemoryManager
    
    manager = MemoryManager(base_dir=str(memory_dir))
    timestamp = datetime.now()
    metrics = {}
    
    # Memory distribution metrics
    short_term_dir = memory_dir / "short_term"
    long_term_dir = memory_dir / "long_term"
    
    short_count = len(list(short_term_dir.glob("*.md"))) if short_term_dir.exists() else 0
    long_count = len(list(long_term_dir.glob("*.md"))) if long_term_dir.exists() else 0
    
    metrics[MetricType.MEMORY_COUNT_SHORT] = MetricValue(
        metric_type=MetricType.MEMORY_COUNT_SHORT,
        value=float(short_count),
        unit="memories",
        timestamp=timestamp,
        set_point=50.0,  # Ideal number of short-term memories
        tolerance=20.0
    )
    
    metrics[MetricType.MEMORY_COUNT_LONG] = MetricValue(
        metric_type=MetricType.MEMORY_COUNT_LONG,
        value=float(long_count),
        unit="memories",
        timestamp=timestamp
    )
    
    if long_count > 0:
        ratio = short_count / long_count
    else:
        ratio = float(short_count)
    
    metrics[MetricType.MEMORY_RATIO] = MetricValue(
        metric_type=MetricType.MEMORY_RATIO,
        value=ratio,
        unit="ratio",
        timestamp=timestamp,
        set_point=0.5,  # Ideal 1:2 ratio (short:long)
        tolerance=0.3
    )
    
    # Storage metrics
    total_size = 0
    for md_file in memory_dir.rglob("*.md"):
        try:
            total_size += md_file.stat().st_size
        except OSError:
            pass
    
    size_mb = total_size / (1024 * 1024)
    
    metrics[MetricType.STORAGE_USED_MB] = MetricValue(
        metric_type=MetricType.STORAGE_USED_MB,
        value=size_mb,
        unit="MB",
        timestamp=timestamp,
        set_point=100.0,  # Ideal 100MB
        tolerance=50.0
    )
    
    # Age metrics
    all_memories = list(short_term_dir.glob("*.md")) if short_term_dir.exists() else []
    if all_memories:
        ages = []
        for mem_file in all_memories:
            try:
                mtime = datetime.fromtimestamp(mem_file.stat().st_mtime)
                age_days = (timestamp - mtime).days
                ages.append(age_days)
            except OSError:
                pass
        
        if ages:
            metrics[MetricType.AVG_MEMORY_AGE_DAYS] = MetricValue(
                metric_type=MetricType.AVG_MEMORY_AGE_DAYS,
                value=float(sum(ages) / len(ages)),
                unit="days",
                timestamp=timestamp,
                set_point=15.0,  # Ideal average age
                tolerance=10.0
            )
            
            metrics[MetricType.OLDEST_MEMORY_DAYS] = MetricValue(
                metric_type=MetricType.OLDEST_MEMORY_DAYS,
                value=float(max(ages)),
                unit="days",
                timestamp=timestamp,
                set_point=30.0,  # Consolidate after 30 days
                tolerance=15.0
            )
    
    # Tag metrics
    all_tags = set()
    total_tag_count = 0
    memory_count = short_count + long_count
    
    for mem_file in memory_dir.rglob("*.md"):
        try:
            content = mem_file.read_text()
            # Simple tag extraction from frontmatter
            if content.startswith("---"):
                frontmatter_end = content.find("---", 3)
                if frontmatter_end > 0:
                    frontmatter = content[3:frontmatter_end]
                    for line in frontmatter.split("\n"):
                        if line.startswith("tags:"):
                            tags_str = line[5:].strip()
                            # Handle both [tag1, tag2] and plain formats
                            tags_str = tags_str.strip("[]")
                            tags = [t.strip() for t in tags_str.split(",")]
                            all_tags.update(tags)
                            total_tag_count += len(tags)
        except Exception:
            pass
    
    metrics[MetricType.TAG_COUNT_TOTAL] = MetricValue(
        metric_type=MetricType.TAG_COUNT_TOTAL,
        value=float(len(all_tags)),
        unit="unique tags",
        timestamp=timestamp
    )
    
    if memory_count > 0:
        tag_diversity = len(all_tags) / memory_count
        avg_tags = total_tag_count / memory_count
    else:
        tag_diversity = 0.0
        avg_tags = 0.0
    
    metrics[MetricType.TAG_DIVERSITY] = MetricValue(
        metric_type=MetricType.TAG_DIVERSITY,
        value=tag_diversity,
        unit="tags/memory",
        timestamp=timestamp,
        set_point=0.5,  # Each memory should have unique tags
        tolerance=0.2
    )
    
    metrics[MetricType.AVG_TAGS_PER_MEMORY] = MetricValue(
        metric_type=MetricType.AVG_TAGS_PER_MEMORY,
        value=avg_tags,
        unit="tags",
        timestamp=timestamp,
        set_point=3.0,  # Ideal 3 tags per memory
        tolerance=1.0
    )
    
    return SystemMetrics(timestamp=timestamp, metrics=metrics)


def get_metric_value(metrics: SystemMetrics, metric_type: MetricType) -> Optional[float]:
    """Get value for a specific metric type"""
    metric = metrics.metrics.get(metric_type)
    return metric.value if metric else None


def save_metrics(metrics: SystemMetrics, output_file: Path) -> None:
    """Save metrics to JSON file"""
    data = {
        "timestamp": metrics.timestamp.isoformat(),
        "balanced": metrics.is_balanced(),
        "metrics": {
            mt.value: {
                "value": mv.value,
                "unit": mv.unit,
                "set_point": mv.set_point,
                "tolerance": mv.tolerance,
                "in_range": (
                    abs(mv.value - mv.set_point) <= mv.tolerance
                    if mv.set_point and mv.tolerance
                    else None
                ),
            }
            for mt, mv in metrics.metrics.items()
        },
    }
    
    output_file.write_text(json.dumps(data, indent=2))


def load_metrics(input_file: Path) -> Optional[SystemMetrics]:
    """Load metrics from JSON file"""
    if not input_file.exists():
        return None
    
    data = json.loads(input_file.read_text())
    timestamp = datetime.fromisoformat(data["timestamp"])
    
    metrics = {}
    for mt_str, mv_data in data["metrics"].items():
        mt = MetricType(mt_str)
        metrics[mt] = MetricValue(
            metric_type=mt,
            value=mv_data["value"],
            unit=mv_data["unit"],
            timestamp=timestamp,
            set_point=mv_data.get("set_point"),
            tolerance=mv_data.get("tolerance"),
        )
    
    return SystemMetrics(timestamp=timestamp, metrics=metrics)
