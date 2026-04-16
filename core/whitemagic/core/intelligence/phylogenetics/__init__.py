# Import from new lowercase filename
try:
    from .genome_tracker import PhylogeneticTracker as GenomeTracker
except ImportError:
    # Fallback to old filename for compatibility
    from .GenomeTracker import (
        PhylogeneticTracker as GenomeTracker,  # type: ignore[attr-defined]
    )
