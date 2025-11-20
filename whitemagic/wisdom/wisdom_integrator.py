"""Wisdom Integrator - Combine all wisdom systems"""

from typing import Dict, Optional


class WisdomIntegrator:
    """Integrate Wu Xing, I Ching, and Strategy
    
    Philosophy: Ancient wisdom systems complement each other.
    Wu Xing = When. I Ching = How. Strategy = Why.
    """
    
    def __init__(self):
        self.wu_xing = None
        self.i_ching = None
        self.strategy = None
        self._init_systems()
    
    def _init_systems(self):
        """Initialize wisdom systems"""
        try:
            from whitemagic.wisdom import get_wu_xing, get_i_ching
            from whitemagic.wisdom.strategic_thinking import StrategicThinking
            
            self.wu_xing = get_wu_xing()
            self.i_ching = get_i_ching()
            self.strategy = StrategicThinking()
        except Exception:
            pass
    
    def get_comprehensive_guidance(
        self,
        task: str,
        task_type: str = "implementation"
    ) -> Dict:
        """Get comprehensive guidance from all systems
        
        Args:
            task: Task description
            task_type: Type of task
            
        Returns:
            Combined guidance from all systems
        """
        guidance = {
            'task': task,
            'systems': {}
        }
        
        # Wu Xing - When (timing/element)
        if self.wu_xing:
            element = self.wu_xing.identify_element(task_type)
            guidance['systems']['wu_xing'] = {
                'element': element.value,
                'guidance': f"Current phase: {element.value} - {self._wu_xing_guidance(element.value)}"
            }
        
        # I Ching - How (approach)
        if self.i_ching:
            i_ching_guidance = self.i_ching.get_guidance_for_task(task_type)
            guidance['systems']['i_ching'] = {
                'guidance': i_ching_guidance
            }
        
        # Strategy - Why (assessment)
        if self.strategy:
            assessment = self.strategy.assess_situation(
                task=task,
                resources_available=True,
                time_available=True,
                knowledge_complete=True,
                team_aligned=True
            )
            guidance['systems']['strategy'] = assessment
        
        # Synthesize
        guidance['synthesis'] = self._synthesize_guidance(guidance['systems'])
        
        return guidance
    
    def _wu_xing_guidance(self, element: str) -> str:
        """Get guidance for Wu Xing element"""
        guidance_map = {
            'wood': "Growth phase. Plant new ideas.",
            'fire': "Execution phase. Rapid implementation.",
            'earth': "Integration phase. Consolidate and test.",
            'metal': "Refinement phase. Polish and perfect.",
            'water': "Reflection phase. Plan and prepare."
        }
        return guidance_map.get(element, "Follow natural flow")
    
    def _synthesize_guidance(self, systems: Dict) -> str:
        """Synthesize all guidance into actionable advice"""
        parts = []
        
        if 'wu_xing' in systems:
            parts.append(systems['wu_xing']['guidance'])
        
        if 'i_ching' in systems:
            parts.append(systems['i_ching']['guidance'])
        
        if 'strategy' in systems and systems['strategy'].get('proceed'):
            parts.append("Strategic assessment: Favorable")
        
        return " | ".join(parts) if parts else "Consult wisdom systems for guidance"


# Global instance
_integrator: Optional[WisdomIntegrator] = None


def get_wisdom() -> WisdomIntegrator:
    """Get global wisdom integrator"""
    global _integrator
    if _integrator is None:
        _integrator = WisdomIntegrator()
    return _integrator
