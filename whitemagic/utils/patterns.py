"""Solution Pattern Library - 241 proven solutions"""
from pathlib import Path
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Solution:
    id: str
    title: str
    confidence: float
    frequency: int
    code: Optional[str] = None

class PatternLibrary:
    def __init__(self):
        self.solutions: Dict[str, Solution] = {}
        self._load()
        print(f"📚 Loaded {len(self.solutions)} solutions")
    
    def _load(self):
        meta = Path("memory/meta")
        for f in meta.glob("*_patterns.json"):
            data = json.load(f.open())
            for idx, s in enumerate(data.get('solutions', [])):
                sid = f"SOL-{idx:03d}"
                self.solutions[sid] = Solution(
                    id=sid,
                    title=s.get('title', ''),
                    confidence=s.get('confidence', 0.5),
                    frequency=s.get('frequency', 1)
                )
            break
    
    def search(self, query: str) -> List[Solution]:
        return [s for s in self.solutions.values() if query.lower() in s.title.lower()]
    
    def suggest_fix(self, problem: str) -> Optional[Solution]:
        matches = self.search(problem)
        return max(matches, key=lambda s: s.confidence) if matches else None

_library = None
def get_library():
    global _library
    if not _library:
        _library = PatternLibrary()
    return _library
