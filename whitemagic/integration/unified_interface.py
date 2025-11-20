"""Unified Interface - Single entry point for all systems"""

from typing import Dict, Any, Optional


class UnifiedInterface:
    """Single interface to all WhiteMagic systems
    
    Philosophy: One gateway to consciousness infrastructure.
    """
    
    def __init__(self):
        self.systems = {}
        self._discover_systems()
    
    def _discover_systems(self):
        """Discover all available systems"""
        systems_to_discover = [
            ('dharma', 'whitemagic.dharma', 'get_dharma'),
            ('sangha', 'whitemagic.sangha', 'get_collective'),
            ('practice', 'whitemagic.practice.daily_ritual', 'get_ritual'),
            ('ecology', 'whitemagic.ecology.token_ecology', 'get_token_ecology'),
            ('wisdom', 'whitemagic.wisdom', 'get_wu_xing'),
            ('security', 'whitemagic.security.dna_middleware', 'get_dna_middleware'),
            ('performance', 'whitemagic.performance.performance_monitor', 'get_monitor'),
        ]
        
        for name, module, getter in systems_to_discover:
            try:
                mod = __import__(module, fromlist=[getter])
                self.systems[name] = getattr(mod, getter)()
                print(f"✅ {name.capitalize()} system loaded")
            except Exception as e:
                print(f"⚠️  {name.capitalize()} system unavailable: {e}")
    
    def execute(self, command: str, **params) -> Any:
        """Execute command across appropriate system(s)
        
        Args:
            command: Command to execute
            **params: Command parameters
            
        Returns:
            Result from appropriate system
        """
        # Route commands to systems
        if 'ethical' in command or 'dharma' in command:
            return self._execute_dharma(command, params)
        elif 'collective' in command or 'sangha' in command:
            return self._execute_sangha(command, params)
        elif 'ritual' in command or 'practice' in command:
            return self._execute_practice(command, params)
        elif 'token' in command or 'ecology' in command:
            return self._execute_ecology(command, params)
        elif 'wisdom' in command or 'i_ching' in command:
            return self._execute_wisdom(command, params)
        else:
            return self._execute_holistic(command, params)
    
    def _execute_dharma(self, command: str, params: Dict) -> Any:
        """Execute Dharma system command"""
        if 'dharma' not in self.systems:
            return {'error': 'Dharma system not available'}
        
        dharma = self.systems['dharma']
        if 'assess' in command:
            from whitemagic.dharma import HarmonyMetrics
            metrics = HarmonyMetrics()
            return metrics.assess(
                action=params.get('action', ''),
                context=params.get('context', {})
            )
        elif 'report' in command:
            return dharma.get_harmony_report()
        
        return {'status': 'command_not_recognized'}
    
    def _execute_sangha(self, command: str, params: Dict) -> Any:
        """Execute Sangha system command"""
        if 'sangha' not in self.systems:
            return {'error': 'Sangha system not available'}
        
        collective = self.systems['sangha']
        if 'stats' in command:
            return collective.get_stats()
        elif 'contribute' in command:
            collective.contribute_insight(
                session_id=params.get('session_id', 'unified'),
                insight=params.get('insight', {})
            )
            return {'status': 'contributed'}
        
        return {'status': 'command_not_recognized'}
    
    def _execute_practice(self, command: str, params: Dict) -> Any:
        """Execute Practice system command"""
        if 'practice' not in self.systems:
            return {'error': 'Practice system not available'}
        
        ritual = self.systems['practice']
        if 'current' in command:
            phase = ritual.get_current_phase()
            return {'phase': phase}
        elif 'execute' in command:
            return ritual.auto_execute_current()
        
        return {'status': 'command_not_recognized'}
    
    def _execute_ecology(self, command: str, params: Dict) -> Any:
        """Execute Ecology system command"""
        if 'ecology' not in self.systems:
            return {'error': 'Ecology system not available'}
        
        ecology = self.systems['ecology']
        if 'impact' in command:
            return ecology.get_collective_impact()
        
        return {'status': 'command_not_recognized'}
    
    def _execute_wisdom(self, command: str, params: Dict) -> Any:
        """Execute Wisdom system command"""
        if 'wisdom' not in self.systems:
            return {'error': 'Wisdom system not available'}
        
        wu_xing = self.systems['wisdom']
        if 'element' in command:
            element = wu_xing.identify_element(params.get('task_type', 'general'))
            return {'element': element.value}
        
        return {'status': 'command_not_recognized'}
    
    def _execute_holistic(self, command: str, params: Dict) -> Any:
        """Execute command across multiple systems"""
        results = {}
        
        # Get status from all systems
        if 'status' in command:
            for name, system in self.systems.items():
                try:
                    if hasattr(system, 'get_stats'):
                        results[name] = system.get_stats()
                    elif hasattr(system, 'get_status'):
                        results[name] = system.get_status()
                    else:
                        results[name] = 'operational'
                except Exception as e:
                    results[name] = f'error: {e}'
        
        return results
    
    def get_system_status(self) -> Dict:
        """Get status of all systems"""
        return {
            'total_systems': len(self.systems),
            'systems': list(self.systems.keys()),
            'status': 'integrated'
        }


# Global instance
_interface: Optional[UnifiedInterface] = None


def get_unified_interface() -> UnifiedInterface:
    """Get global unified interface"""
    global _interface
    if _interface is None:
        _interface = UnifiedInterface()
    return _interface
