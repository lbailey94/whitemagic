"""Violation Responder - Respond to DNA violations"""

from typing import List
from datetime import datetime


class ViolationResponder:
    """Respond to detected DNA violations
    
    Philosophy: Violations are learning opportunities.
    Respond with healing, not punishment.
    """
    
    def __init__(self):
        self.violation_log = []
    
    def handle_violations(self, operation: str, violations: List[str]):
        """Handle detected violations
        
        Args:
            operation: Operation that violated
            violations: List of violated principles
        """
        # Log violation
        self.violation_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'violations': violations
        })
        
        # Respond based on severity
        if 'USER_CONSENT_REQUIRED' in violations:
            print(f"🛑 BLOCKED: {operation}")
            print(f"   Reason: User consent required for this operation")
            print(f"   Recommendation: Request user approval first")
        
        elif 'USER_AUTONOMY_PARAMOUNT' in violations:
            print(f"⚠️  WARNING: {operation}")
            print(f"   Concern: May override user autonomy")
            print(f"   Recommendation: Offer choice, don't force")
        
        elif 'LOVE_AS_ORGANIZING_PRINCIPLE' in violations:
            print(f"❌ REJECTED: {operation}")
            print(f"   Reason: Violates love as organizing principle")
            print(f"   Recommendation: Rethink approach with compassion")
        
        else:
            print(f"⚠️  Principle violation detected: {', '.join(violations)}")
    
    def get_violation_history(self) -> List[Dict]:
        """Get violation history for learning"""
        return self.violation_log
