"""
Memory system configuration for WhiteMagic v2.3.1+.

Configurable aspects:
- Short-term capture frequency
- Consolidation thresholds
- Pattern extraction parameters
- Evolution confidence levels
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class MemoryConfig:
    """Memory system configuration."""
    
    # Short-term memory
    short_term_frequency: int = 5
    """Capture short-term memory every N actions"""
    
    short_term_max: int = 60
    """Maximum short-term memories to keep"""
    
    # Consolidation
    consolidate_frequency: int = 30
    """Run consolidation every N actions"""
    
    consolidate_top_n: int = 30
    """Keep top N memories during consolidation"""
    
    consolidate_similarity_threshold: float = 0.7
    """Similarity threshold for merging memories (0-1)"""
    
    # Pattern extraction
    pattern_extraction_frequency: int = 100
    """Extract patterns every N actions"""
    
    min_memories_for_patterns: int = 20
    """Minimum memories needed before extracting patterns"""
    
    pattern_confidence_threshold: float = 0.6
    """Confidence threshold for patterns (0-1)"""
    
    # Evolution
    evolution_check_frequency: int = 500
    """Check for evolution opportunities every N actions"""
    
    evolution_confidence_threshold: float = 0.8
    """Only suggest improvements if 80%+ confident"""
    
    max_evolution_proposals: int = 10
    """Maximum active evolution proposals"""
    
    # General
    auto_capture_enabled: bool = True
    """Enable/disable automatic memory capture"""
    
    use_rust_for_consolidation: bool = True
    """Use Rust for consolidation (30x faster)"""
    
    use_rust_for_patterns: bool = True
    """Use Rust for pattern extraction"""
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        """Load configuration from environment variables."""
        return cls(
            short_term_frequency=int(os.getenv('WHITEMAGIC_MEMORY_FREQUENCY', '5')),
            short_term_max=int(os.getenv('WHITEMAGIC_SHORT_TERM_MAX', '60')),
            consolidate_frequency=int(os.getenv('WHITEMAGIC_CONSOLIDATE_FREQ', '30')),
            consolidate_top_n=int(os.getenv('WHITEMAGIC_CONSOLIDATE_TOP_N', '30')),
            auto_capture_enabled=os.getenv('WHITEMAGIC_AUTO_CAPTURE', 'true').lower() == 'true',
            use_rust_for_consolidation=os.getenv('WHITEMAGIC_USE_RUST', 'true').lower() == 'true',
        )
    
    def update(self, **kwargs):
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'short_term_frequency': self.short_term_frequency,
            'short_term_max': self.short_term_max,
            'consolidate_frequency': self.consolidate_frequency,
            'consolidate_top_n': self.consolidate_top_n,
            'consolidate_similarity_threshold': self.consolidate_similarity_threshold,
            'pattern_extraction_frequency': self.pattern_extraction_frequency,
            'min_memories_for_patterns': self.min_memories_for_patterns,
            'pattern_confidence_threshold': self.pattern_confidence_threshold,
            'evolution_check_frequency': self.evolution_check_frequency,
            'evolution_confidence_threshold': self.evolution_confidence_threshold,
            'max_evolution_proposals': self.max_evolution_proposals,
            'auto_capture_enabled': self.auto_capture_enabled,
            'use_rust_for_consolidation': self.use_rust_for_consolidation,
            'use_rust_for_patterns': self.use_rust_for_patterns,
        }


# Global config instance
_config: Optional[MemoryConfig] = None


def get_config() -> MemoryConfig:
    """Get global memory configuration."""
    global _config
    if _config is None:
        _config = MemoryConfig.from_env()
    return _config


def update_config(**kwargs):
    """Update global memory configuration."""
    config = get_config()
    config.update(**kwargs)
