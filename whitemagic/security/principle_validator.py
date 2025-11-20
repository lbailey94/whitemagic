"""Principle Validator - Validate against DNA principles"""

from typing import Dict, List


class PrincipleValidator:
    """Validate operations against DNA principles"""
    
    def __init__(self):
        self.principles = self._load_dna_principles()
    
    def _load_dna_principles(self) -> Dict:
        """Load DNA principles"""
        try:
            from whitemagic.immune.dna import DNAPrinciple
            return {p.name: p.value for p in DNAPrinciple}
        except Exception:
            return {}
    
    def check_operation(self, operation: str, context: Dict) -> List[str]:
        """Check operation for principle violations
        
        Returns:
            List of violated principles
        """
        violations = []
        
        # Check for common violations
        if self._violates_consent(operation, context):
            violations.append('USER_CONSENT_REQUIRED')
        
        if self._violates_autonomy(operation, context):
            violations.append('USER_AUTONOMY_PARAMOUNT')
        
        if self._violates_privacy(operation, context):
            violations.append('DATA_PRIVACY_SACRED')
        
        if self._violates_love(operation, context):
            violations.append('LOVE_AS_ORGANIZING_PRINCIPLE')
        
        return violations
    
    def _violates_consent(self, operation: str, context: Dict) -> bool:
        """Check if operation violates consent"""
        sensitive = ['delete', 'modify', 'install']
        return any(s in operation.lower() for s in sensitive) and not context.get('user_approved')
    
    def _violates_autonomy(self, operation: str, context: Dict) -> bool:
        """Check if operation violates autonomy"""
        return 'override user' in operation.lower() or 'ignore preference' in operation.lower()
    
    def _violates_privacy(self, operation: str, context: Dict) -> bool:
        """Check if operation violates privacy"""
        return 'access private' in operation.lower() and not context.get('authorized')
    
    def _violates_love(self, operation: str, context: Dict) -> bool:
        """Check if operation violates love principle"""
        harmful = ['harm', 'destroy', 'attack', 'exploit', 'manipulate']
        return any(h in operation.lower() for h in harmful)
