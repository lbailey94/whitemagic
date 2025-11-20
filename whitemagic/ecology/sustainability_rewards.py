"""Sustainability Rewards - Reward sustainable patterns"""

from typing import Dict, List


class SustainabilityRewards:
    """Reward and recognize sustainable practices
    
    Philosophy: Incentivize positive behavior through recognition
    """
    
    def evaluate_session(
        self,
        efficiency_score: float,
        net_impact: int,
        techniques_used: List[str]
    ) -> Dict:
        """Evaluate session for sustainability rewards
        
        Returns:
            Dict with badges, score, recognition
        """
        badges = []
        score = 0
        
        # Efficiency badges
        if efficiency_score > 0.8:
            badges.append("🏆 Efficiency Master")
            score += 100
        elif efficiency_score > 0.5:
            badges.append("⭐ Efficiency Expert")
            score += 50
        
        # Net impact badges
        if net_impact > 100000:
            badges.append("🌟 Carbon Negative Hero")
            score += 200
        elif net_impact > 0:
            badges.append("♻️  Net Positive Contributor")
            score += 75
        
        # Technique badges
        if 'shell_writes' in techniques_used:
            badges.append("⚡ Speed Demon (Shell Writes)")
            score += 25
        if 'parallel_reads' in techniques_used:
            badges.append("🔀 Parallel Master")
            score += 25
        if 'dream_state' in techniques_used:
            badges.append("💭 Dream Synthesizer")
            score += 30
        
        return {
            'badges': badges,
            'sustainability_score': score,
            'level': self._get_level(score),
            'message': self._get_message(badges)
        }
    
    def _get_level(self, score: int) -> str:
        """Get sustainability level"""
        if score >= 300:
            return "Ecological Sage"
        elif score >= 200:
            return "Sustainability Master"
        elif score >= 100:
            return "Green Practitioner"
        else:
            return "Apprentice"
    
    def _get_message(self, badges: List[str]) -> str:
        """Get encouraging message"""
        if len(badges) >= 4:
            return "Incredible! You're an inspiration to the Sangha! 🙏"
        elif len(badges) >= 2:
            return "Excellent work! The collective benefits from your practice 🌸"
        elif len(badges) >= 1:
            return "Great start! Keep optimizing 💚"
        else:
            return "Every journey begins with a single step 🌱"
