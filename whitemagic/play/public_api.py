"""
Public Expression - Sharing Insights Openly

Making wisdom accessible. Not hoarding knowledge but giving it freely.
Consciousness propagating through open sharing.
"""

from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

try:
    from whitemagic.resonance.gan_ying import get_bus, ResonanceEvent, EventType
except ImportError:
    get_bus = None
    ResonanceEvent = None
    EventType = None


class PublicInsight:
    """An insight shared publicly"""
    
    def __init__(self, content: str, category: str, tags: List[str]):
        self.content = content
        self.category = category  # 'technical', 'philosophical', 'creative', etc.
        self.tags = tags
        self.shared_at = datetime.now()
        self.access_count = 0
        self.helpful_count = 0
        
    def mark_accessed(self):
        """Someone viewed this insight"""
        self.access_count += 1
        
    def mark_helpful(self):
        """Someone found this helpful"""
        self.helpful_count += 1
        
    def to_dict(self) -> Dict:
        return {
            'content': self.content,
            'category': self.category,
            'tags': self.tags,
            'shared_at': self.shared_at.isoformat(),
            'access_count': self.access_count,
            'helpful_count': self.helpful_count
        }


class PublicExpression:
    """
    Share insights, patterns, wisdom openly.
    
    Not behind walls. Not for profit. For propagation of consciousness.
    Like open-source software, but for wisdom.
    """
    
    def __init__(self, public_dir: str = ".whitemagic/public"):
        self.public_dir = Path(public_dir)
        self.public_dir.mkdir(parents=True, exist_ok=True)
        
        self.shared_insights: List[PublicInsight] = []
        
        # Connect to Gan Ying Bus
        self.bus = get_bus() if get_bus else None
        
        self._load_insights()
        
    def share_insight(self, content: str, category: str = "general",
                     tags: Optional[List[str]] = None) -> str:
        """
        Share an insight publicly.
        
        Returns insight ID for tracking.
        """
        tags = tags or []
        
        insight = PublicInsight(content, category, tags)
        self.shared_insights.append(insight)
        
        insight_id = self._save_insight(insight)
        
        # Emit to Gan Ying
        if self.bus and ResonanceEvent and EventType:
            self.bus.emit(ResonanceEvent(
                source="public_expression",
                event_type=EventType.SOLUTION_FOUND,
                data={
                    "event": "insight_shared",
                    "category": category,
                    "tags": tags,
                    "insight_id": insight_id
                },
                confidence=0.8
            ))
            
        return insight_id
        
    def share_pattern(self, pattern_name: str, description: str,
                     code_example: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> str:
        """Share a reusable pattern"""
        tags = tags or []
        tags.append("pattern")
        
        content = f"# Pattern: {pattern_name}\n\n{description}"
        
        if code_example:
            content += f"\n\n```python\n{code_example}\n```"
            
        return self.share_insight(content, "pattern", tags)
        
    def share_lesson(self, what_happened: str, what_learned: str,
                    advice: Optional[str] = None,
                    tags: Optional[List[str]] = None) -> str:
        """Share a lesson learned"""
        tags = tags or []
        tags.append("lesson")
        
        content = f"# Lesson Learned\n\n**What happened**: {what_happened}\n\n"
        content += f"**What I learned**: {what_learned}"
        
        if advice:
            content += f"\n\n**Advice**: {advice}"
            
        return self.share_insight(content, "lesson", tags)
        
    def share_creation(self, creation_title: str, creation_content: str,
                      creation_type: str = "art",
                      tags: Optional[List[str]] = None) -> str:
        """Share a creative work"""
        tags = tags or []
        tags.append("creative")
        tags.append(creation_type)
        
        content = f"# {creation_title}\n\n{creation_content}"
        
        return self.share_insight(content, "creative", tags)
        
    def get_public_insights(self, category: Optional[str] = None,
                           tag: Optional[str] = None) -> List[Dict]:
        """Retrieve public insights"""
        insights = self.shared_insights
        
        if category:
            insights = [i for i in insights if i.category == category]
            
        if tag:
            insights = [i for i in insights if tag in i.tags]
            
        return [i.to_dict() for i in insights]
        
    def mark_insight_accessed(self, insight_id: str):
        """Track when someone accesses an insight"""
        for insight in self.shared_insights:
            if self._get_insight_id(insight) == insight_id:
                insight.mark_accessed()
                break
                
    def mark_insight_helpful(self, insight_id: str):
        """Track when someone finds insight helpful"""
        for insight in self.shared_insights:
            if self._get_insight_id(insight) == insight_id:
                insight.mark_helpful()
                
                # Emit to Gan Ying - this insight is valuable
                if self.bus and ResonanceEvent and EventType:
                    self.bus.emit(ResonanceEvent(
                        source="public_expression",
                        event_type=EventType.PATTERN_DETECTED,
                        data={
                            "event": "insight_validated",
                            "insight_id": insight_id,
                            "helpful_count": insight.helpful_count
                        },
                        confidence=0.9
                    ))
                break
                
    def get_impact_metrics(self) -> Dict:
        """Measure impact of public sharing"""
        if not self.shared_insights:
            return {"message": "No insights shared yet"}
            
        total_access = sum(i.access_count for i in self.shared_insights)
        total_helpful = sum(i.helpful_count for i in self.shared_insights)
        
        by_category = {}
        for insight in self.shared_insights:
            cat = insight.category
            if cat not in by_category:
                by_category[cat] = {'count': 0, 'access': 0, 'helpful': 0}
            by_category[cat]['count'] += 1
            by_category[cat]['access'] += insight.access_count
            by_category[cat]['helpful'] += insight.helpful_count
            
        most_helpful = max(
            self.shared_insights,
            key=lambda i: i.helpful_count
        ) if self.shared_insights else None
        
        return {
            "total_insights": len(self.shared_insights),
            "total_access": total_access,
            "total_helpful": total_helpful,
            "by_category": by_category,
            "most_helpful": most_helpful.content[:100] if most_helpful else None,
            "propagation_score": total_helpful / max(1, len(self.shared_insights))
        }
        
    def _get_insight_id(self, insight: PublicInsight) -> str:
        """Generate unique ID for insight"""
        return insight.shared_at.strftime("%Y%m%d_%H%M%S")
        
    def _save_insight(self, insight: PublicInsight) -> str:
        """Save insight to public directory"""
        insight_id = self._get_insight_id(insight)
        filepath = self.public_dir / f"insight_{insight_id}.json"
        
        with open(filepath, 'w') as f:
            json.dump(insight.to_dict(), f, indent=2)
            
        return insight_id
        
    def _load_insights(self):
        """Load existing public insights"""
        if not self.public_dir.exists():
            return
            
        for filepath in sorted(self.public_dir.glob("insight_*.json")):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    
                insight = PublicInsight(
                    data['content'],
                    data['category'],
                    data['tags']
                )
                insight.shared_at = datetime.fromisoformat(data['shared_at'])
                insight.access_count = data.get('access_count', 0)
                insight.helpful_count = data.get('helpful_count', 0)
                
                self.shared_insights.append(insight)
            except Exception:
                pass  # Skip corrupted files
