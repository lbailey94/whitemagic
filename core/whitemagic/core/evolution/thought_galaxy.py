# Thought Galaxy Creation, Scoring, and Recall System


class CognitiveEpisode:
    """CognitiveEpisode: cognitive episode."""
    def __init__(self, id: str, embeddings: list[float], tags: list[str]):
        self.id = id
        self.embeddings = embeddings
        self.tags = tags
        self.score = 0.0

class ThoughtGalaxy:
    """ThoughtGalaxy: thought galaxy."""
    def __init__(self):
        self.episodes = []

    def add_episode(self, episode: CognitiveEpisode):
        """
        Add episode.

        Args:
            episode: Parameter description.
        """
        self.episodes.append(episode)
        self._recalculate_gravity()

    def _recalculate_gravity(self):
        # Simulated gravity clustering based on tag overlap and vector similarity
        for ep in self.episodes:
            ep.score = len(ep.tags) * 1.5 # Placeholder scoring

    def recall(self, query_tags: list[str], top_k: int = 5) -> list[CognitiveEpisode]:
        # Simple intersection scoring for now
        """
        Perform the recall operation.

        Args:
            query_tags: Parameter description.
            top_k: Parameter description.

        Returns:
            list[CognitiveEpisode]
        """
        results = []
        for ep in self.episodes:
            overlap = len(set(ep.tags).intersection(set(query_tags)))
            if overlap > 0:
                results.append((overlap, ep))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]

    def mine_patterns(self) -> list[dict]:
        """Mine emergent patterns from stored episodes.

        Analyzes episodes for recurring tag clusters and frequency patterns.
        """
        if not self.episodes:
            return []
        tag_counts: dict[str, int] = {}
        for ep in self.episodes:
            for tag in ep.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        results = [
            {"tag": t, "frequency": c, "dominance": c / len(self.episodes)}
            for t, c in sorted(tag_counts.items(), key=lambda x: -x[1])
        ]
        return results
