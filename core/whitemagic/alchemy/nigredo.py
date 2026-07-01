"""
Nigredo: The Stage of Decomposition
===================================
Classifies raw memory "Prima Materia" into three essences:
1. Novelty (The Soul): Insight, architecture, philosophy, unique patterns.
2. Routine (The Body): Logs, standard operations, maintenance.
3. Noise (The Dross): Tracebacks, temporary checkpoints, empty files.

Usage:
    classifier = NigredoClassifier()
    category, score = classifier.classify(memory_content, memory_title)
"""


class NigredoClassifier:
    """Classifies memories for transmutation."""

    NOISE_TITLES = [
        "Checkpoint",
        "Session Handoff",
        "Twice-daily",
        "Summary",
        "Update",
        "Backup",
    ]
    ROUTINE_CONTENT = [
        "traceback",
        "error",
        "exception",
        "lint",
        "mypy",
        "fix",
        "debug",
        "todo list",
    ]
    NOVELTY_KEYWORDS = [
        "concept",
        "architecture",
        "strategy",
        "philosophy",
        "insight",
        "discovery",
        "pattern",
        "synthesis",
        "manifesto",
        "protocol",
        "framework",
        "system design",
        "golden rule",
        "lesson learned",
        "post-mortem",
        "root cause",
    ]

    def classify(self, content: str, title: str = "") -> tuple[str, float]:
        """
        Returns (Category, Confidence).
        Categories: 'Novelty', 'Routine', 'Noise'.
        """
        title_lower = (title or "").lower()
        content_lower = (content or "").lower()

        # 1. Noise Filter (High Confidence)
        if any(k.lower() in title_lower for k in self.NOISE_TITLES):
            return "Noise", 0.95

        if len(content) < 50:
            return "Noise", 0.90

        if "traceback (most recent call last)" in content_lower:
            # Unless it has analysis
            if "analysis:" not in content_lower and "cause:" not in content_lower:
                return "Noise", 0.85

        # 2. Novelty Detection
        novelty_hits: float = float(
            sum(1 for k in self.NOVELTY_KEYWORDS if k in content_lower)
        )

        # Structure bonus: Markdown headers often indicate structured thought
        if content.count("# ") + content.count("## ") > 2:
            novelty_hits += 1

        # Code vs Text ratio: High text density often means documentation/insight
        # Simple heuristic: space count / length
        text_density = content.count(" ") / max(len(content), 1)
        if text_density > 0.15:  # English text is usually around 0.15-0.20
            novelty_hits += 0.5

        if novelty_hits >= 2.5:
            return "Novelty", min(0.6 + (novelty_hits * 0.1), 1.0)

        # 3. Routine/Operational
        routine_hits = sum(1 for k in self.ROUTINE_CONTENT if k in content_lower)
        if routine_hits >= 1:
            return "Routine", 0.8

        # Default
        return "Routine", 0.5
