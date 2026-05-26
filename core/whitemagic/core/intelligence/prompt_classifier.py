"""
Prompt Classifier (G004)
========================

Classifies user prompts into routine categories (managerial) vs novel ideas (creative).
Used by the Auto-Prompting Supervisor to identify the "70%" of routine work.
"""

from typing import Tuple

class PromptClassifier:
    """Classifies prompts into SOP categories."""

    PATTERNS = {
        "review": [
            r"review", r"check", r"audit", r"verify", r"look over", r"sanity check",
            r"find bugs", r"security scan"
        ],
        "handoff": [
            r"handoff", r"summary", r"summarize", r"wrap up", r"session end",
            r"checkpoint", r"save state", r"what did we do"
        ],
        "synthesize": [
            r"synthesize", r"consolidate", r"merge", r"combine", r"refactor",
            r"clean up", r"organize", r"structure"
        ],
        "plan": [
            r"plan", r"roadmap", r"strategy", r"next steps", r"what's next",
            r"create a plan", r"break down"
        ],
        "implementation": [
            r"implement", r"code", r"write", r"create file", r"build", r"make a",
            r"generate"
        ]
    }

    def classify(self, prompt: str) -> Tuple[str, float]:
        """
        Classify a prompt string.
        Returns (category, confidence).
        Category is 'novel_idea' if no standard pattern matches strongly.
        """
        prompt_lower = prompt.lower()

        best_cat = "novel_idea"
        best_score = 0.0

        for cat, keywords in self.PATTERNS.items():
            score = 0
            for kw in keywords:
                if kw in prompt_lower:
                    score += 1

            # Simple heuristic scoring
            if score > 0:
                confidence = min(0.9, 0.4 + (score * 0.1))
                if confidence > best_score:
                    best_score = confidence
                    best_cat = cat

        return best_cat, best_score

    def is_routine(self, prompt: str) -> bool:
        """Returns True if the prompt is classified as routine managerial work."""
        cat, score = self.classify(prompt)
        return cat != "novel_idea" and score > 0.5
