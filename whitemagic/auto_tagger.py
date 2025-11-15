"""Automatic tag suggestion using LLM."""

import re
from typing import List, Optional, Set


class AutoTagger:
    """Suggests tags for memories based on content analysis."""
    
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self._known_tags: Optional[Set[str]] = None
    
    def _get_known_tags(self) -> Set[str]:
        """Get known tags from existing memories."""
        if self._known_tags is not None:
            return self._known_tags
        
        if not self.memory_manager:
            return set()
        
        tags_data = self.memory_manager.list_all_tags(include_archived=False)
        known = {t["tag"] for t in tags_data.get("tags", [])}
        self._known_tags = known
        return known
    
    def suggest_tags(
        self, 
        title: str, 
        content: str, 
        existing_tags: Optional[List[str]] = None,
        max_suggestions: int = 5
    ) -> List[str]:
        """Suggest tags based on content (rule-based for now)."""
        existing = set(existing_tags or [])
        suggestions = []
        text = f"{title} {content}".lower()
        
        # Version numbers
        versions = re.findall(r'v?\d+\.\d+\.\d+', text)
        for v in versions:
            tag = v if v.startswith('v') else f'v{v}'
            if tag not in existing:
                suggestions.append(tag)
        
        # Keywords
        keywords = {
            'bug': 'bug', 'fix': 'bugfix', 'test': 'testing',
            'security': 'security', 'api': 'api', 'feature': 'feature',
            'architecture': 'architecture', 'setup': 'setup',
            'template': 'template', 'mcp': 'mcp', 'cli': 'cli',
        }
        
        for word, tag in keywords.items():
            if word in text and tag not in existing:
                suggestions.append(tag)
        
        # Prefer known tags
        known = self._get_known_tags()
        suggestions = [t for t in suggestions if t in known] + \
                      [t for t in suggestions if t not in known]
        
        return suggestions[:max_suggestions]
