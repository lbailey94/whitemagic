"""Strategic Thinking - Art of War principles"""



class StrategicThinking:
    """Apply Art of War principles to development

    Philosophy: 知彼知己，百戰不殆
    Know the enemy and yourself, hundred battles without danger.
    """

    def assess_situation(
        self,
        task: str,
        resources_available: bool,
        time_available: bool,
        knowledge_complete: bool,
        team_aligned: bool
    ) -> dict:
        """Assess situation using 5 factors (道天地將法)

        Args:
            task: Task description
            resources_available: Do we have resources?
            time_available: Is timing right?
            knowledge_complete: Do we know enough?
            team_aligned: Is alignment present?

        Returns:
            Assessment with recommendation
        """
        factors = {
            '道 Dao (Way)': team_aligned,
            '天 Heaven (Timing)': time_available,
            '地 Earth (Resources)': resources_available,
            '將 General (Strategy)': knowledge_complete,
            '法 Law (Execution)': True  # Assume execution capability
        }

        score = sum(1 for v in factors.values() if v) / len(factors)

        recommendation = self._get_recommendation(score)

        return {
            'task': task,
            'factors': factors,
            'score': score,
            'recommendation': recommendation,
            'proceed': score >= 0.6
        }

    def _get_recommendation(self, score: float) -> str:
        """Get strategic recommendation"""
        if score >= 0.8:
            return "✅ Excellent position. Proceed with confidence."
        elif score >= 0.6:
            return "⚠️  Proceed with caution. Address weak factors."
        else:
            return "🛑 Prepare more before proceeding. Strengthen foundation."

    def get_maxim_for_situation(self, situation: str) -> str:
        """Get relevant Art of War maxim"""
        maxims = {
            'planning': "謀定而後動 - Plan thoroughly before acting",
            'unknown': "知彼知己，百戰不殆 - Know yourself and enemy, never danger",
            'overwhelming': "避其銳氣，擊其惰歸 - Avoid strength, strike weakness",
            'complex': "其疾如風，其徐如林 - Swift as wind, calm as forest",
            'difficult': "攻其無備，出其不意 - Strike where unexpected"
        }

        return maxims.get(situation, "兵者，詭道也 - War is the way of deception")
