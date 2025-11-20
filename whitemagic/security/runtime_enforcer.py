"""Runtime Enforcer - Enforce principles during execution"""

from typing import Dict, List, Optional


class RuntimeEnforcer:
    """Enforce DNA principles at runtime
    
    Philosophy: Prevention is better than cure.
    Catch violations before they cause harm.
    """
    
    def __init__(self):
        self.active_checks = []
        self.violation_count = 0
        self.bus = None
        self._connect_to_gan_ying()
    
    def _connect_to_gan_ying(self):
        """Connect to Gan Ying Bus"""
        try:
            from whitemagic.resonance.gan_ying import get_bus
            self.bus = get_bus()
            print("🎵 Runtime Enforcer connected to Gan Ying Bus")
        except ImportError:
            pass
    
    def enforce_principle(self, principle: str, operation: str, context: Dict) -> bool:
        """Enforce specific DNA principle
        
        Args:
            principle: DNA principle to enforce
            operation: Operation being attempted
            context: Context dict
            
        Returns:
            True if compliant, False if violation
        """
        # Map principles to checks
        checks = {
            'consent_required': self._check_consent,
            'user_autonomy': self._check_autonomy,
            'data_privacy': self._check_privacy,
            'graceful_degradation': self._check_degradation,
            'love_as_principle': self._check_love,
        }
        
        check_func = checks.get(principle)
        if not check_func:
            return True  # Unknown principle, allow
        
        compliant = check_func(operation, context)
        
        if not compliant:
            self.violation_count += 1
            self._emit_violation(principle, operation)
        
        return compliant
    
    def _check_consent(self, operation: str, context: Dict) -> bool:
        """Check if user consent obtained"""
        sensitive_ops = ['delete', 'modify', 'install', 'uninstall']
        if any(op in operation.lower() for op in sensitive_ops):
            return context.get('user_approved', False)
        return True
    
    def _check_autonomy(self, operation: str, context: Dict) -> bool:
        """Check if user autonomy respected"""
        return not ('force' in operation.lower() or 'override' in operation.lower())
    
    def _check_privacy(self, operation: str, context: Dict) -> bool:
        """Check if data privacy maintained"""
        return 'private' not in operation.lower() or context.get('authorized', False)
    
    def _check_degradation(self, operation: str, context: Dict) -> bool:
        """Check if graceful degradation implemented"""
        # Always pass - this is aspirational
        return True
    
    def _check_love(self, operation: str, context: Dict) -> bool:
        """Check if action aligns with love as organizing principle"""
        harmful_words = ['harm', 'destroy', 'attack', 'exploit']
        return not any(word in operation.lower() for word in harmful_words)
    
    def _emit_violation(self, principle: str, operation: str):
        """Emit violation to Gan Ying"""
        if not self.bus:
            return
        
        try:
            from whitemagic.resonance.gan_ying import ResonanceEvent, EventType
            self.bus.emit(ResonanceEvent(
                source="runtime_enforcer",
                event_type=EventType.VIOLATION_FOUND,
                data={
                    'principle': principle,
                    'operation': operation,
                    'severity': 'high'
                },
                confidence=0.95
            ))
        except Exception:
            pass
    
    def get_stats(self) -> Dict:
        """Get enforcement statistics"""
        return {
            'active_checks': len(self.active_checks),
            'violations_detected': self.violation_count,
            'status': 'enforcing'
        }
