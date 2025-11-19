"""Autoimmune Defense System - Transform 229 anti-patterns into active defenses"""

from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
import re


@dataclass
class AntiPattern:
    pattern_id: str
    title: str
    confidence: float
    keywords: List[str] = field(default_factory=list)
    auto_fixable: bool = False
    
    def matches(self, text: str) -> bool:
        """Check if text contains this anti-pattern"""
        return any(kw.lower() in text.lower() for kw in self.keywords)


@dataclass  
class PatternViolation:
    file_path: Path
    line_number: int
    pattern: AntiPattern
    matched_text: str


class AutoimmuneSystem:
    """Defend against 229 anti-patterns, apply 241 solutions"""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path(".")
        self.anti_patterns: Dict[str, AntiPattern] = {}
        self._load_patterns()
        print(f"🛡️  Loaded {len(self.anti_patterns)} anti-patterns")
    
    def _load_patterns(self):
        """Load from v2.3.1 analysis"""
        meta_dir = self.base_dir / "memory" / "meta"
        pattern_files = list(meta_dir.glob("*_patterns.json"))
        
        if not pattern_files:
            return
        
        latest = max(pattern_files, key=lambda p: p.stat().st_mtime)
        with open(latest, 'r') as f:
            data = json.load(f)
        
        # Convert anti-patterns
        for idx, ap in enumerate(data.get('anti_patterns', [])):
            pattern_id = f"AP-{idx:03d}"
            title = ap.get('title', '')
            
            # Extract keywords from title
            keywords = self._extract_keywords(title)
            
            self.anti_patterns[pattern_id] = AntiPattern(
                pattern_id=pattern_id,
                title=title,
                confidence=ap.get('confidence', 0.5),
                keywords=keywords,
                auto_fixable=ap.get('confidence', 0) > 0.9
            )
    
    def _extract_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from pattern title"""
        # Remove "Avoid:" prefix
        clean = title.replace('Avoid:', '').strip()
        
        # Split and filter short words
        words = [w.strip('*:') for w in clean.split()]
        keywords = [w for w in words if len(w) > 3]
        
        return keywords[:5]  # Top 5 keywords
    
    def scan_file(self, file_path: Path) -> List[PatternViolation]:
        """Scan a file for anti-pattern violations"""
        violations = []
        
        if not file_path.exists():
            return violations
        
        try:
            content = file_path.read_text()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.anti_patterns.values():
                    if pattern.matches(line):
                        violations.append(PatternViolation(
                            file_path=file_path,
                            line_number=line_num,
                            pattern=pattern,
                            matched_text=line.strip()
                        ))
        
        except Exception as e:
            print(f"⚠️  Error scanning {file_path}: {e}")
        
        return violations
    
    def scan_directory(self, directory: Path, extensions: List[str] = None) -> List[PatternViolation]:
        """Scan directory for violations"""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.md']
        
        all_violations = []
        
        for ext in extensions:
            for file_path in directory.rglob(f'*{ext}'):
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue
                
                violations = self.scan_file(file_path)
                all_violations.extend(violations)
        
        return all_violations


# Global instance
_immune_system = None

def get_immune_system() -> AutoimmuneSystem:
    """Get global immune system instance"""
    global _immune_system
    if _immune_system is None:
        _immune_system = AutoimmuneSystem()
    return _immune_system
