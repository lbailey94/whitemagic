# Thought Galaxy Creation, Scoring, and Recall System


class CognitiveEpisode:
    def __init__(self, id: str, embeddings: list[float], tags: list[str]):
        self.id = id
        self.embeddings = embeddings
        self.tags = tags
        self.score = 0.0

class ThoughtGalaxy:
    def __init__(self):
        self.episodes = []

    def add_episode(self, episode: CognitiveEpisode):
        self.episodes.append(episode)
        self._recalculate_gravity()

    def _recalculate_gravity(self):
        # Simulated gravity clustering based on tag overlap and vector similarity
        for ep in self.episodes:
            ep.score = len(ep.tags) * 1.5 # Placeholder scoring

    def recall(self, query_tags: list[str], top_k: int = 5) -> list[CognitiveEpisode]:
        # Simple intersection scoring for now
        results = []
        for ep in self.episodes:
            overlap = len(set(ep.tags).intersection(set(query_tags)))
            if overlap > 0:
                results.append((overlap, ep))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]
