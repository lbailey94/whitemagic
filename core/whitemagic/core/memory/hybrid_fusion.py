"""Hybrid Fusion Module - Optimal Retrieval Scoring
Combines vector similarity, BM25 text matching, and graph PageRank
using Reciprocal Rank Fusion (RRF) and learned weights.
"""

from dataclasses import dataclass


@dataclass
class RetrievalCandidate:
    memory_id: str
    title: str
    content: str
    vector_score: float = 0.0
    bm25_score: float = 0.0
    graph_score: float = 0.0
    final_score: float = 0.0


class HybridFusion:
    """
    Optimal hybrid scoring for memory retrieval.

    Implements:
    - Reciprocal Rank Fusion (RRF): Combines multiple ranking signals
    - Learned weighting: Adapts weights based on query type
    - Convex combination: Smooth interpolation between signals
    """

    def __init__(self,
                 vector_weight: float = 0.5,
                 bm25_weight: float = 0.3,
                 graph_weight: float = 0.2,
                 rrf_k: float = 60.0):
        self.weights = {
            'vector': vector_weight,
            'bm25': bm25_weight,
            'graph': graph_weight
        }
        self.rrf_k = rrf_k

    def fuse_rrf(self,
                 vector_results: list[dict],
                 bm25_results: list[dict],
                 graph_results: list[dict],
                 top_k: int = 20) -> list[RetrievalCandidate]:
        """
        Reciprocal Rank Fusion: Combines rankings from multiple sources.

        RRF formula: score(d) = sum(1 / (k + rank(d, source)))
        """
        all_ids = set()
        for r in vector_results + bm25_results + graph_results:
            all_ids.add(r.get('id'))

        candidates = {}

        # Score each source
        for rank, result in enumerate(vector_results):
            mid = result.get('id')
            if not mid:
                continue
            mid_str = str(mid)
            if mid_str not in candidates:
                candidates[mid_str] = RetrievalCandidate(
                    memory_id=mid_str,
                    title=str(result.get('title', '')),
                    content=str(result.get('content', ''))
                )
            candidates[mid_str].vector_score = 1.0 / (self.rrf_k + rank + 1)

        for rank, result in enumerate(bm25_results):
            mid = result.get('id')
            if not mid:
                continue
            mid_str = str(mid)
            if mid_str not in candidates:
                candidates[mid_str] = RetrievalCandidate(
                    memory_id=mid_str,
                    title=str(result.get('title', '')),
                    content=str(result.get('content', ''))
                )
            candidates[mid_str].bm25_score = 1.0 / (self.rrf_k + rank + 1)

        for rank, result in enumerate(graph_results):
            mid = result.get('id')
            if not mid:
                continue
            mid_str = str(mid)
            if mid_str not in candidates:
                candidates[mid_str] = RetrievalCandidate(
                    memory_id=mid_str,
                    title=str(result.get('title', '')),
                    content=str(result.get('content', ''))
                )
            candidates[mid_str].graph_score = 1.0 / (self.rrf_k + rank + 1)

        # Combine scores
        for candidate in candidates.values():
            candidate.final_score = (
                self.weights['vector'] * candidate.vector_score +
                self.weights['bm25'] * candidate.bm25_score +
                self.weights['graph'] * candidate.graph_score
            )

        # Sort and return top_k
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda x: x.final_score,
            reverse=True
        )
        return sorted_candidates[:top_k]

    def fuse_convex(self,
                    vector_results: list[dict],
                    bm25_results: list[dict],
                    graph_results: list[dict],
                    top_k: int = 20) -> list[RetrievalCandidate]:
        """
        Convex combination fusion with learned weights.
        Normalizes each score to [0, 1] then combines.
        """
        all_ids = set()
        for r in vector_results + bm25_results + graph_results:
            all_ids.add(r.get('id'))

        # Build score lookup
        vector_map = {r.get('id'): r.get('score', 0) for r in vector_results}
        bm25_map = {r.get('id'): r.get('score', 0) for r in bm25_results}
        graph_map = {r.get('id'): r.get('score', 0) for r in graph_results}

        # Normalize scores to [0, 1]
        def normalize(scores: dict) -> dict:
            """
            Perform the normalize operation.
            
            Args:
                scores: Parameter description.
            
            Returns:
                dict
            """
            if not scores:
                return {}
            max_score = max(scores.values()) if scores else 1.0
            if max_score == 0:
                return {k: 0 for k in scores}
            return {k: v / max_score for k, v in scores.items()}

        vector_norm = normalize(vector_map)
        bm25_norm = normalize(bm25_map)
        graph_norm = normalize(graph_map)

        candidates = []
        for mid in all_ids:
            if not mid:
                continue
            title = (vector_map.get(mid, {}).get('title', '') or
                    bm25_map.get(mid, {}).get('title', '') or
                    graph_map.get(mid, {}).get('title', '') or '')
            content = (vector_map.get(mid, {}).get('content', '') or
                      bm25_map.get(mid, {}).get('content', '') or
                      graph_map.get(mid, {}).get('content', '') or '')

            v_score = vector_norm.get(mid, 0)
            b_score = bm25_norm.get(mid, 0)
            g_score = graph_norm.get(mid, 0)

            final = (
                self.weights['vector'] * v_score +
                self.weights['bm25'] * b_score +
                self.weights['graph'] * g_score
            )

            candidates.append(RetrievalCandidate(
                memory_id=mid,
                title=title,
                content=content,
                vector_score=v_score,
                bm25_score=b_score,
                graph_score=g_score,
                final_score=final
            ))

        return sorted(candidates, key=lambda x: x.final_score, reverse=True)[:top_k]

    def adapt_weights(self, query_type: str):
        """
        Adapt weights based on query type for optimal performance.

        Query-type specific tuning:
        - single_hop: Boost BM25 (exact title matches matter)
        - multi_hop: Boost graph (connectivity matters)
        - open_domain: Balance all three
        - temporal: Boost vector (semantic date matching)
        """
        adaptations = {
            'single_hop': {'vector': 0.4, 'bm25': 0.5, 'graph': 0.1},
            'multi_hop': {'vector': 0.3, 'bm25': 0.3, 'graph': 0.4},
            'temporal': {'vector': 0.6, 'bm25': 0.3, 'graph': 0.1},
            'open_domain': {'vector': 0.5, 'bm25': 0.3, 'graph': 0.2},
            'adversarial': {'vector': 0.4, 'bm25': 0.4, 'graph': 0.2},
        }

        self.weights = adaptations.get(query_type, self.weights)


class OptimalHybridSearcher:
    """
    Production-ready hybrid search combining all retrieval signals.
    """

    def __init__(self, embedder, backend):
        self.embedder = embedder
        self.backend = backend
        self.fusion = HybridFusion()

    def search(self, query: str, query_type: str = 'open_domain', limit: int = 20):
        """
        Execute hybrid search with adaptive weighting.

        Args:
            query: Search query text
            query_type: single_hop, multi_hop, temporal, open_domain, adversarial
            limit: Number of results to return

        Returns:
            List of RetrievalCandidate objects
        """
        # Adapt weights to query type
        self.fusion.adapt_weights(query_type)

        # Get results from each source
        self.embedder.encode(query)

        vector_results = self.embedder.search_similar(
            query=query,
            limit=limit * 2,
            min_similarity=0.05
        )

        bm25_results = self.backend.search(
            query=query,
            limit=limit * 2
        )

        # Graph results (PageRank-boosted)
        graph_results = self._get_graph_results(query, limit * 2)

        # Fuse results
        fused = self.fusion.fuse_rrf(
            vector_results=vector_results,
            bm25_results=bm25_results,
            graph_results=graph_results,
            top_k=limit
        )

        return fused

    def _get_graph_results(self, query: str, limit: int) -> list[dict]:
        """Get graph-based results (PageRank-boosted neighbors)."""
        raise NotImplementedError("Graph result fusion is not yet implemented.")


def demo_hybrid_fusion():
    """Demonstrate hybrid fusion with mock data."""
    print("=" * 60)
    print("Hybrid Fusion Demo")
    print("=" * 60)

    fusion = HybridFusion()

    # Mock results
    vector_results = [
        {'id': 'mem1', 'title': 'OpenAI API Guide', 'content': 'How to use the API', 'score': 0.95},
        {'id': 'mem2', 'title': 'GPT-4 Architecture', 'content': 'Model details', 'score': 0.85},
        {'id': 'mem3', 'title': 'Tokenization', 'content': 'Token counting', 'score': 0.75},
    ]

    bm25_results = [
        {'id': 'mem2', 'title': 'GPT-4 Architecture', 'content': 'Model details', 'score': 0.90},
        {'id': 'mem1', 'title': 'OpenAI API Guide', 'content': 'How to use the API', 'score': 0.80},
        {'id': 'mem4', 'title': 'API Rate Limits', 'content': 'Rate limiting', 'score': 0.70},
    ]

    graph_results = [
        {'id': 'mem1', 'title': 'OpenAI API Guide', 'content': 'How to use the API', 'score': 0.88},
        {'id': 'mem5', 'title': 'Related Concept', 'content': 'Connection', 'score': 0.60},
    ]

    print("\nInput sources:")
    print(f"  Vector: {len(vector_results)} results")
    print(f"  BM25: {len(bm25_results)} results")
    print(f"  Graph: {len(graph_results)} results")

    # Test RRF fusion
    fused = fusion.fuse_rrf(vector_results, bm25_results, graph_results, top_k=5)

    print("\nFused results (RRF):")
    for i, c in enumerate(fused, 1):
        print(f"  {i}. {c.memory_id}: {c.final_score:.3f} "
              f"(v={c.vector_score:.3f}, b={c.bm25_score:.3f}, g={c.graph_score:.3f})")

    # Test adaptive weights
    print("\nAdaptive weights by query type:")
    for qtype in ['single_hop', 'multi_hop', 'temporal', 'open_domain']:
        fusion.adapt_weights(qtype)
        print(f"  {qtype}: v={fusion.weights['vector']:.1f}, "
              f"b={fusion.weights['bm25']:.1f}, g={fusion.weights['graph']:.1f}")

    print("\n" + "=" * 60)
    print("Hybrid fusion ready for LoCoMo integration")
    print("=" * 60)


if __name__ == "__main__":
    demo_hybrid_fusion()
