"""
Albedo: The Stage of Purification
=================================
Purifies the "Novelty" essence by:
1. Vectorization: Converting text to semantic embeddings.
2. Clustering: Grouping similar patterns (white purification).
3. Abstraction: Identifying the central theme of each cluster.

Usage:
    purifier = AlbedoPurifier()
    clusters = purifier.purify(novelty_memories)
"""

import logging
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.cluster import KMeans

# Import our unified embedding engine (supports Local/SentenceTransformers)
from whitemagic.core.memory.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)

class AlbedoPurifier:
    """Vectorizes and clusters novelty memories."""

    def __init__(self):
        self.engine = EmbeddingEngine()
        if not self.engine.available():
            logger.warning("Embedding engine not available. Albedo will fail.")

    def vectorize(self, memories: list[dict[str, str]]) -> list[dict[str, Any]]:
        """
        Add 'embedding' field to each memory dict.
        memories: list of {'id': str, 'content': str, ...}
        """
        logger.info(f"Vectorizing {len(memories)} memories...")
        texts = [m.get('content', '') for m in memories]

        # Batch encode
        embeddings = self.engine.encode_batch(texts, batch_size=64)

        results = []
        for i, m in enumerate(memories):
            if embeddings and i < len(embeddings):
                m['embedding'] = embeddings[i]
                results.append(m)

        return results

    def cluster(self, vectorized_memories: list[dict[str, Any]], n_clusters: int = 20) -> list[dict[str, Any]]:
        """
        Group memories into semantic clusters.
        Returns list of clusters: {'id': int, 'items': [memories], 'centroid': vec}
        """
        if not vectorized_memories:
            return []

        # Extract vectors
        X = np.array([m['embedding'] for m in vectorized_memories])

        # KMeans clustering
        # In a real system, we might use HDBSCAN for density-based,
        # but KMeans is robust for fixed target of 'Golden Rules'
        logger.info(f"Clustering into {n_clusters} patterns...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

        # Group by label
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[int(label)].append(vectorized_memories[i])

        # Format results
        output = []
        for label, items in clusters.items():
            centroid = kmeans.cluster_centers_[label]
            output.append({
                "cluster_id": label,
                "size": len(items),
                "items": items,
                "centroid": centroid.tolist()
            })

        # Sort by size (most common patterns first)
        output.sort(key=lambda x: x['size'], reverse=True)
        return output
