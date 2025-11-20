"""Capability Discovery - Discover system capabilities"""

from typing import Dict, List


class CapabilityDiscovery:
    """Discover and catalog system capabilities"""
    
    def discover_all_capabilities(self) -> Dict:
        """Discover capabilities of all systems
        
        Returns:
            Dict mapping systems to their capabilities
        """
        capabilities = {}
        
        # Dharma
        capabilities['dharma'] = [
            'ethical_assessment',
            'harmony_metrics',
            'boundary_detection',
            'consent_validation'
        ]
        
        # Sangha
        capabilities['sangha'] = [
            'collective_memory',
            'pattern_federation',
            'session_handoff',
            'community_ethics'
        ]
        
        # Practice
        capabilities['practice'] = [
            'daily_rituals',
            'habit_tracking',
            'rhythm_detection',
            'practice_scheduling'
        ]
        
        # Ecology
        capabilities['ecology'] = [
            'token_monitoring',
            'resource_tracking',
            'impact_calculation',
            'sustainability_rewards'
        ]
        
        # Wisdom
        capabilities['wisdom'] = [
            'wu_xing_timing',
            'i_ching_guidance',
            'strategic_thinking',
            'wisdom_integration'
        ]
        
        # Security
        capabilities['security'] = [
            'dna_middleware',
            'runtime_enforcement',
            'principle_validation',
            'violation_response'
        ]
        
        # Performance
        capabilities['performance'] = [
            'performance_monitoring',
            'bottleneck_detection',
            'optimization_routing',
            'bridge_coordination'
        ]
        
        return capabilities
    
    def check_capability(self, system: str, capability: str) -> bool:
        """Check if system has capability"""
        capabilities = self.discover_all_capabilities()
        return capability in capabilities.get(system, [])
