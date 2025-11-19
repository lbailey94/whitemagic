"""
Pattern Extraction Engine - Week 3 of v2.3.1

Analyzes long-term memories to extract:
- Solutions (when X happens, do Y)
- Anti-patterns (avoid Z because...)
- Heuristics (if condition, then action)
- Optimizations (proven approaches)
"""

from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import json
from datetime import datetime

try:
    import whitemagic_rs
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


@dataclass
class Pattern:
    """Represents an extracted pattern"""
    pattern_type: str  # solution, anti_pattern, heuristic, optimization
    title: str
    description: str
    confidence: float
    frequency: int = 1
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []


@dataclass
class PatternReport:
    """Report of pattern extraction results"""
    total_memories: int
    patterns_found: int
    solutions: List[Pattern]
    anti_patterns: List[Pattern]
    heuristics: List[Pattern]
    optimizations: List[Pattern]
    duration_seconds: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'total_memories': self.total_memories,
            'patterns_found': self.patterns_found,
            'solutions': [asdict(p) for p in self.solutions],
            'anti_patterns': [asdict(p) for p in self.anti_patterns],
            'heuristics': [asdict(p) for p in self.heuristics],
            'optimizations': [asdict(p) for p in self.optimizations],
            'duration_seconds': self.duration_seconds,
        }


class PatternEngine:
    """Extracts patterns from long-term memories"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.long_term_dir = self.base_dir / "memory" / "long_term"
        self.meta_dir = self.base_dir / "memory" / "meta"
        self.meta_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_patterns(self, min_confidence: float = 0.6, use_rust: bool = True) -> PatternReport:
        """
        Extract patterns from long-term memories.
        
        Args:
            min_confidence: Minimum confidence score (0.0 - 1.0)
            use_rust: Use Rust implementation if available
            
        Returns:
            PatternReport with extracted patterns
        """
        if use_rust and RUST_AVAILABLE:
            return self._extract_rust(min_confidence)
        else:
            return self._extract_python(min_confidence)
    
    def _extract_rust(self, min_confidence: float) -> PatternReport:
        """Use Rust for high-performance pattern extraction"""
        total, found, solutions, anti, heuristics, opts, duration = \
            whitemagic_rs.extract_patterns(str(self.long_term_dir), min_confidence)
        
        # Parse patterns from strings
        solution_patterns = [self._parse_pattern(s, 'solution') for s in solutions]
        anti_patterns = [self._parse_pattern(a, 'anti_pattern') for a in anti]
        heuristic_patterns = [self._parse_pattern(h, 'heuristic') for h in heuristics]
        optimization_patterns = [self._parse_pattern(o, 'optimization') for o in opts]
        
        return PatternReport(
            total_memories=total,
            patterns_found=found,
            solutions=solution_patterns,
            anti_patterns=anti_patterns,
            heuristics=heuristic_patterns,
            optimizations=optimization_patterns,
            duration_seconds=duration
        )
    
    def _parse_pattern(self, text: str, pattern_type: str) -> Pattern:
        """Parse pattern from Rust output string"""
        # Format: "Title (confidence: 0.XX)"
        if '(confidence:' in text:
            parts = text.rsplit('(confidence:', 1)
            title = parts[0].strip()
            confidence = float(parts[1].rstrip(')').strip())
        else:
            title = text
            confidence = 0.5
        
        return Pattern(
            pattern_type=pattern_type,
            title=title,
            description=title,
            confidence=confidence
        )
    
    def _extract_python(self, min_confidence: float) -> PatternReport:
        """Python fallback implementation"""
        import time
        start = time.time()
        
        # Simple Python implementation
        memories = list(self.long_term_dir.glob("*.md"))
        
        solutions = []
        anti_patterns = []
        heuristics = []
        optimizations = []
        
        for mem_file in memories:
            content = mem_file.read_text()
            
            # Extract basic patterns
            for line in content.split('\n'):
                line_lower = line.lower()
                
                if any(kw in line_lower for kw in ['solved', 'fix', 'solution']):
                    solutions.append(Pattern('solution', line[:80], line, 0.6))
                
                if any(kw in line_lower for kw in ['never', 'avoid', 'error']):
                    anti_patterns.append(Pattern('anti_pattern', line[:80], line, 0.6))
                
                if any(kw in line_lower for kw in ['if', 'when', 'should']):
                    heuristics.append(Pattern('heuristic', line[:80], line, 0.6))
                
                if any(kw in line_lower for kw in ['faster', 'optimiz', 'performance']):
                    optimizations.append(Pattern('optimization', line[:80], line, 0.6))
        
        duration = time.time() - start
        total_patterns = len(solutions) + len(anti_patterns) + len(heuristics) + len(optimizations)
        
        return PatternReport(
            total_memories=len(memories),
            patterns_found=total_patterns,
            solutions=solutions,
            anti_patterns=anti_patterns,
            heuristics=heuristics,
            optimizations=optimizations,
            duration_seconds=duration
        )
    
    def save_patterns(self, report: PatternReport) -> Path:
        """Save patterns to meta-memory file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_patterns.json"
        filepath = self.meta_dir / filename
        
        # Save as JSON
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        # Also create markdown summary
        md_file = self.meta_dir / f"{timestamp}_patterns.md"
        self._create_markdown_summary(report, md_file)
        
        return filepath
    
    def _create_markdown_summary(self, report: PatternReport, filepath: Path):
        """Create human-readable markdown summary"""
        with open(filepath, 'w') as f:
            f.write(f"# Pattern Extraction Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Memories Analyzed**: {report.total_memories}\n")
            f.write(f"**Patterns Found**: {report.patterns_found}\n")
            f.write(f"**Duration**: {report.duration_seconds:.3f}s\n\n")
            
            f.write(f"## 💡 Solutions ({len(report.solutions)})\n\n")
            for p in report.solutions[:10]:  # Top 10
                f.write(f"- **{p.title}** (confidence: {p.confidence:.2f})\n")
            f.write("\n")
            
            f.write(f"## ⚠️ Anti-Patterns ({len(report.anti_patterns)})\n\n")
            for p in report.anti_patterns[:10]:
                f.write(f"- **{p.title}** (confidence: {p.confidence:.2f})\n")
            f.write("\n")
            
            f.write(f"## 🎯 Heuristics ({len(report.heuristics)})\n\n")
            for p in report.heuristics[:10]:
                f.write(f"- **{p.title}** (confidence: {p.confidence:.2f})\n")
            f.write("\n")
            
            f.write(f"## ⚡ Optimizations ({len(report.optimizations)})\n\n")
            for p in report.optimizations[:10]:
                f.write(f"- **{p.title}** (confidence: {p.confidence:.2f})\n")
            f.write("\n")


# Global instance
_engine = None

def get_engine() -> PatternEngine:
    """Get global pattern engine instance"""
    global _engine
    if _engine is None:
        _engine = PatternEngine()
    return _engine
