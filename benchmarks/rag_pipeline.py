"""RAG pipeline for LoCoMo benchmark — all 3 tiers of improvement.

Tier 1: LLM answer generation, LLM-as-judge, retrieval depth tuning
Tier 2: Consolidation/dedup, query type routing, context formatting, query bias correction
Tier 3: Temporal graph, adversarial robustness, cross-galaxy RRF fusion

Usage:
    from benchmarks.rag_pipeline import RAGPipeline
    pipeline = RAGPipeline(memory_store, llm_base_url="http://127.0.0.1:8080")
    result = pipeline.answer_question(question, gold_answer, galaxies=["locomo_real"])
"""

from __future__ import annotations

import re
import time
import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Query type detection (Tier 2.5) ─────────────────────────────────────────

_MULTI_HOP_INDICATORS = [
    r"how many", r"how long", r"how often", r"what happened between",
    r"what did.*do after", r"what changed", r"difference between",
    r"compare", r"both", r"all of", r"each of", r"every",
]
_TEMPORAL_INDICATORS = [
    r"when", r"what year", r"what month", r"how long ago",
    r"first time", r"last time", r"before", r"after", r"since",
    r"recently", r"earlier", r"later", r"started", r"began",
    r"stopped", r"ended", r"used to", r"switched",
]
_ADVERSARIAL_INDICATORS = [
    r"why didn't", r"why doesn't", r"why isn't",
    r"what happened when.*failed", r"tell me about.*that never",
]


@dataclass
class QueryType:
    category: str
    is_multi_hop: bool = False
    is_temporal: bool = False
    is_adversarial: bool = False
    sub_queries: list[str] = field(default_factory=list)


def detect_query_type(question: str) -> QueryType:
    """Detect query type and generate sub-queries for multi-hop decomposition."""
    q_lower = question.lower().strip()
    is_adversarial = any(re.search(pat, q_lower) for pat in _ADVERSARIAL_INDICATORS)
    is_temporal = any(re.search(pat, q_lower) for pat in _TEMPORAL_INDICATORS)
    is_multi_hop = any(re.search(pat, q_lower) for pat in _MULTI_HOP_INDICATORS)

    if is_adversarial:
        category = "adversarial"
    elif is_multi_hop:
        category = "multi_hop"
    elif is_temporal:
        category = "temporal"
    else:
        category = "single_hop"

    sub_queries: list[str] = []
    if is_multi_hop:
        sub_queries = _decompose_query(question)

    return QueryType(
        category=category,
        is_multi_hop=is_multi_hop,
        is_temporal=is_temporal,
        is_adversarial=is_adversarial,
        sub_queries=sub_queries,
    )


def _decompose_query(question: str) -> list[str]:
    """Decompose a multi-hop question into sub-queries."""
    sub_queries: list[str] = []
    parts = re.split(r"\s+(?:and|also|additionally)\s+", question, flags=re.IGNORECASE)
    if len(parts) > 1:
        sub_queries.extend(parts)
    if not sub_queries:
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", question)
        for noun in proper_nouns[:3]:
            sub_queries.append(f"What do you know about {noun}?")
    return sub_queries


# ── Query bias correction (Tier 2.7) ────────────────────────────────────────

_BIAS_REPLACEMENTS = {
    r"\bwhat's\b": "what is",
    r"\bwho's\b": "who is",
    r"\bdon't\b": "do not",
    r"\bdoesn't\b": "does not",
    r"\bdidn't\b": "did not",
    r"\bcan't\b": "cannot",
    r"\bwon't\b": "will not",
    r"\bisn't\b": "is not",
    r"\bwasn't\b": "was not",
    r"\baren't\b": "are not",
    r"\bweren't\b": "were not",
    r"\bI'm\b": "I am",
    r"\bhe's\b": "he is",
    r"\bshe's\b": "she is",
    r"\bthey're\b": "they are",
}

_STOP_WORDS = frozenset({
    "the", "a", "an", "is", "was", "are", "were", "to", "of", "in", "on",
    "at", "for", "and", "or", "but", "not", "this", "that", "it", "he",
    "she", "they", "his", "her", "their", "with", "from", "by", "as",
    "what", "who", "when", "where", "why", "how", "which", "do", "did",
    "does", "can", "could", "would", "should", "will", "about", "into",
})


def correct_query(query: str) -> str:
    """Apply query bias correction — expand contractions, normalize."""
    corrected = query
    for pattern, replacement in _BIAS_REPLACEMENTS.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    return corrected.strip()


def extract_key_terms(query: str) -> list[str]:
    """Extract important terms from query for bias correction."""
    terms = re.findall(r"\b\w+\b", query.lower())
    return [t for t in terms if t not in _STOP_WORDS and len(t) > 2]


# ── Context formatting (Tier 2.6) ───────────────────────────────────────────


def format_context(results: list[Any], query_type: QueryType | None = None) -> str:
    """Format retrieved memories as structured assertions for LLM input.

    MemMachine showed +2.0% from context formatting alone.
    """
    if not results:
        return "No relevant memories found."

    lines: list[str] = []
    for i, result in enumerate(results, 1):
        content = getattr(result, "content", str(result)) if not isinstance(result, dict) else result.get("content", str(result))
        title = ""
        if hasattr(result, "title"):
            title = result.title
        elif isinstance(result, dict):
            title = result.get("title", "")

        # Format as numbered assertion
        if title and title != content:
            lines.append(f"[{i}] {title}: {content}")
        else:
            lines.append(f"[{i}] {content}")

    return "\n".join(lines)


# ── Consolidation and dedup (Tier 2.4) ──────────────────────────────────────


def consolidate_results(results: list[Any], similarity_threshold: float = 0.85) -> list[Any]:
    """Consolidate and deduplicate retrieved memories.

    Removes near-duplicate content using simple Jaccard similarity on word sets.
    """
    if not results:
        return []

    consolidated: list[Any] = []
    seen_word_sets: list[set[str]] = []

    for result in results:
        content = getattr(result, "content", str(result)) if not isinstance(result, dict) else result.get("content", str(result))
        words = set(re.findall(r"\b\w+\b", content.lower()))
        words.discard("")

        is_dup = False
        for prev_words in seen_word_sets:
            if not words or not prev_words:
                continue
            intersection = words & prev_words
            union = words | prev_words
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard >= similarity_threshold:
                is_dup = True
                break

        if not is_dup:
            consolidated.append(result)
            seen_word_sets.append(words)

    return consolidated


# ── Cross-galaxy RRF fusion (Tier 3.10) ─────────────────────────────────────


def rrf_fuse(result_lists: list[list[Any]], k: int = 60) -> list[Any]:
    """Reciprocal Rank Fusion — merge multiple ranked lists.

    Args:
        result_lists: List of ranked result lists from different galaxies.
        k: RRF constant (default 60, standard value).

    Returns:
        Fused and re-ranked list.
    """
    scores: dict[int, float] = {}
    result_map: dict[int, Any] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list):
            content = getattr(result, "content", str(result)) if not isinstance(result, dict) else result.get("content", str(result))
            content_hash = hash(content)

            if content_hash not in result_map:
                result_map[content_hash] = result
            scores[content_hash] = scores.get(content_hash, 0.0) + 1.0 / (k + rank + 1)

    sorted_hashes = sorted(scores.keys(), key=lambda h: scores[h], reverse=True)
    return [result_map[h] for h in sorted_hashes]


# ── Temporal graph indexing (Tier 3.8) ──────────────────────────────────────


@dataclass
class TemporalNode:
    """A node in the temporal graph."""
    memory_id: str
    content: str
    timestamp: float
    session_id: str = ""
    date_time: str = ""
    temporal_neighbors: list[str] = field(default_factory=list)


class TemporalGraph:
    """Simple temporal graph for temporal reasoning queries.

    Indexes memories by timestamp and builds temporal adjacency for
    before/after queries. MemoryLake showed 91.28% temporal with this approach.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, TemporalNode] = {}
        self._sorted_ids: list[str] = []

    def add_memory(self, memory_id: str, content: str, timestamp: float = 0.0,
                   session_id: str = "", date_time: str = "") -> None:
        """Add a memory to the temporal graph."""
        self.nodes[memory_id] = TemporalNode(
            memory_id=memory_id,
            content=content,
            timestamp=timestamp,
            session_id=session_id,
            date_time=date_time,
        )
        self._sorted_ids.append(memory_id)
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Rebuild sorted index and temporal adjacency."""
        self._sorted_ids.sort(key=lambda mid: self.nodes[mid].timestamp)
        for i, mid in enumerate(self._sorted_ids):
            node = self.nodes[mid]
            node.temporal_neighbors = []
            if i > 0:
                node.temporal_neighbors.append(self._sorted_ids[i - 1])
            if i < len(self._sorted_ids) - 1:
                node.temporal_neighbors.append(self._sorted_ids[i + 1])

    def get_temporal_context(self, memory_id: str, window: int = 3) -> list[TemporalNode]:
        """Get temporally adjacent memories for context."""
        if memory_id not in self.nodes:
            return []
        idx = self._sorted_ids.index(memory_id)
        start = max(0, idx - window)
        end = min(len(self._sorted_ids), idx + window + 1)
        return [self.nodes[mid] for mid in self._sorted_ids[start:end]]

    def query_temporal(self, before: float | None = None, after: float | None = None,
                       session_id: str | None = None) -> list[TemporalNode]:
        """Query memories by temporal constraints."""
        results = []
        for mid in self._sorted_ids:
            node = self.nodes[mid]
            if before is not None and node.timestamp > before:
                continue
            if after is not None and node.timestamp < after:
                continue
            if session_id and node.session_id != session_id:
                continue
            results.append(node)
        return results


# ── Adversarial robustness (Tier 3.9) ───────────────────────────────────────


_ADVERSARIAL_PATTERNS = [
    r"why didn't.*mention",
    r"what happened when.*failed",
    r"tell me about.*that never",
    r"why doesn't.*like",
    r"why isn't.*interested in",
]


def detect_false_premise(question: str, retrieved_contents: list[str]) -> bool:
    """Detect if a question contains a false premise.

    Synthius-Mem achieves 99.55% adversarial robustness. This checks
    if the question's premise contradicts retrieved evidence.
    """
    q_lower = question.lower()
    is_adversarial_pattern = any(re.search(pat, q_lower) for pat in _ADVERSARIAL_PATTERNS)
    if not is_adversarial_pattern:
        return False

    # Check if the premise is contradicted by retrieved content
    # Simple heuristic: if question asks "why didn't X do Y" and we find
    # evidence that X DID do Y, it's a false premise
    neg_match = re.search(r"why didn't\s+(\w+)\s+(.+)", q_lower)
    if neg_match:
        subject = neg_match.group(1)
        action = neg_match.group(2).rstrip("?")
        for content in retrieved_contents:
            content_lower = content.lower()
            if subject in content_lower and action in content_lower:
                return True

    return False


def should_abstain(question: str, results: list[Any], confidence_threshold: float = 0.15) -> bool:
    """Determine if the system should abstain (say "I don't know").

    For adversarial questions or when no relevant memories are found.
    """
    if not results:
        return True

    q_type = detect_query_type(question)
    if q_type.is_adversarial:
        contents = [getattr(r, "content", str(r)) for r in results]
        if detect_false_premise(question, contents):
            return True

    return False


# ── LLM client (Tier 1.1) ───────────────────────────────────────────────────


class LLMClient:
    """Simple LLM client for answer generation and judging via llama-server."""

    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._available: bool | None = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0

    @property
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import requests
            resp = requests.get(f"{self.base_url}/v1/models", timeout=5)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 256,
             temperature: float = 0.1) -> str:
        """Send a chat completion request."""
        if not self.is_available:
            return ""
        try:
            import requests
            payload = {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Track token usage
            usage = data.get("usage", {})
            self.total_input_tokens += usage.get("prompt_tokens", 0)
            self.total_output_tokens += usage.get("completion_tokens", 0)
            self.total_calls += 1
            return content.strip()
        except Exception as e:
            logger.warning("LLM chat failed: %s", e)
            return ""

    def generate_answer(self, question: str, context: str,
                        max_tokens: int = 256) -> str:
        """Generate an answer using retrieved context (RAG)."""
        system_msg = (
            "You are a memory assistant. Answer the question based ONLY on the "
            "provided memory context. Be concise and factual. If the context "
            "does not contain the answer, say 'I don't know'."
        )
        user_msg = f"Memory context:\n{context}\n\nQuestion: {question}\nAnswer:"
        return self.chat(
            [{"role": "system", "content": system_msg},
             {"role": "user", "content": user_msg}],
            max_tokens=max_tokens,
            temperature=0.1,
        )

    def judge_answer(self, question: str, gold_answer: str,
                     predicted_answer: str) -> bool:
        """LLM-as-judge: determine if predicted answer is correct."""
        system_msg = (
            "You are a judge evaluating whether a predicted answer matches "
            "the gold answer. Respond with ONLY 'YES' or 'NO'."
        )
        user_msg = (
            f"Question: {question}\n"
            f"Gold answer: {gold_answer}\n"
            f"Predicted answer: {predicted_answer}\n"
            f"Is the predicted answer correct (semantically equivalent)? "
            f"Respond YES or NO:"
        )
        response = self.chat(
            [{"role": "system", "content": system_msg},
             {"role": "user", "content": user_msg}],
            max_tokens=5,
            temperature=0.0,
        )
        return response.strip().upper().startswith("YES")


# ── Main RAG Pipeline ───────────────────────────────────────────────────────


@dataclass
class RAGResult:
    """Result of a single RAG query."""
    question: str
    gold_answer: str
    predicted_answer: str
    is_correct: bool
    method: str  # "rag", "rag+structured", "rag+temporal", etc.
    latency_ms: float
    tokens_used: int
    query_type: str
    retrieved_count: int
    abstained: bool = False


class RAGPipeline:
    """Full RAG pipeline implementing all 3 tiers of improvement.

    Tier 1: LLM generation + LLM-as-judge + retrieval depth tuning
    Tier 2: Consolidation + query routing + context formatting + query bias
    Tier 3: Temporal graph + adversarial robustness + RRF fusion
    """

    def __init__(
        self,
        memory_store: Any,
        llm_base_url: str = "http://127.0.0.1:8080",
        retrieval_limit: int = 20,
        use_judge: bool = True,
        use_consolidation: bool = True,
        use_query_correction: bool = True,
        use_context_formatting: bool = True,
        use_rrf_fusion: bool = True,
        use_temporal_graph: bool = True,
        use_adversarial_detection: bool = True,
    ):
        self.memory_store = memory_store
        self.llm = LLMClient(base_url=llm_base_url)
        self.retrieval_limit = retrieval_limit
        self.use_judge = use_judge
        self.use_consolidation = use_consolidation
        self.use_query_correction = use_query_correction
        self.use_context_formatting = use_context_formatting
        self.use_rrf_fusion = use_rrf_fusion
        self.use_temporal_graph = use_temporal_graph
        self.use_adversarial_detection = use_adversarial_detection
        self.temporal_graph = TemporalGraph()

    def register_temporal_memories(self, memories: list[dict]) -> None:
        """Register memories in the temporal graph for Tier 3 temporal reasoning."""
        for mem in memories:
            mid = mem.get("id", mem.get("title", str(hash(mem.get("content", "")))))
            content = mem.get("content", "")
            timestamp = mem.get("timestamp", 0.0)
            session_id = mem.get("session_id", mem.get("metadata", {}).get("session_id", ""))
            date_time = mem.get("date_time", mem.get("metadata", {}).get("date_time", ""))
            self.temporal_graph.add_memory(mid, content, timestamp, session_id, date_time)

    def answer_question(
        self,
        question: str,
        gold_answer: str,
        primary_galaxy: str = "locomo_real",
        extra_galaxies: list[str] | None = None,
        is_adversarial_q: bool = False,
    ) -> RAGResult:
        """Answer a single question using the full RAG pipeline."""
        t0 = time.time()
        tokens_before = self.llm.total_input_tokens + self.llm.total_output_tokens

        # Tier 2.7: Query bias correction
        corrected_query = correct_query(question) if self.use_query_correction else question

        # Tier 2.5: Query type detection
        q_type = detect_query_type(corrected_query)

        # Tier 1.3: Retrieval with tuned depth
        result_lists: list[list[Any]] = []
        primary_results = self.memory_store.search_hybrid(
            corrected_query, galaxy=primary_galaxy, limit=self.retrieval_limit
        )
        result_lists.append(primary_results)

        # Extra galaxies for structured facts
        if extra_galaxies:
            for eg in extra_galaxies:
                extra_results = self.memory_store.search_hybrid(
                    corrected_query, galaxy=eg, limit=self.retrieval_limit
                )
                result_lists.append(extra_results)

        # Tier 2.5: Multi-hop sub-query retrieval
        if q_type.is_multi_hop and q_type.sub_queries:
            for sub_q in q_type.sub_queries[:3]:
                sub_results = self.memory_store.search_hybrid(
                    sub_q, galaxy=primary_galaxy, limit=10
                )
                result_lists.append(sub_results)

        # Tier 3.10: RRF fusion or simple concatenation
        if self.use_rrf_fusion and len(result_lists) > 1:
            fused_results = rrf_fuse(result_lists)
        else:
            fused_results = []
            for rl in result_lists:
                fused_results.extend(rl)

        # Tier 2.4: Consolidation and dedup
        if self.use_consolidation:
            fused_results = consolidate_results(fused_results)

        # Tier 3.9: Adversarial detection
        abstained = False
        if self.use_adversarial_detection and should_abstain(corrected_query, fused_results):
            predicted = "I don't know"
            abstained = True
            tokens_used = self.llm.total_input_tokens + self.llm.total_output_tokens - tokens_before
            latency_ms = (time.time() - t0) * 1000
            is_correct = self._evaluate(question, gold_answer, predicted, is_adversarial_q)
            return RAGResult(
                question=question, gold_answer=gold_answer,
                predicted_answer=predicted, is_correct=is_correct,
                method="abstention", latency_ms=latency_ms,
                tokens_used=tokens_used, query_type=q_type.category,
                retrieved_count=len(fused_results), abstained=True,
            )

        if not fused_results:
            predicted = "I don't know"
            tokens_used = self.llm.total_input_tokens + self.llm.total_output_tokens - tokens_before
            latency_ms = (time.time() - t0) * 1000
            return RAGResult(
                question=question, gold_answer=gold_answer,
                predicted_answer=predicted, is_correct=False,
                method="no_results", latency_ms=latency_ms,
                tokens_used=tokens_used, query_type=q_type.category,
                retrieved_count=0, abstained=True,
            )

        # Tier 2.6: Context formatting
        context = format_context(fused_results[:10], q_type) if self.use_context_formatting else \
            "\n".join(getattr(r, "content", str(r)) for r in fused_results[:10])

        # Tier 3.8: Temporal context augmentation
        if self.use_temporal_graph and q_type.is_temporal and fused_results:
            top_content = getattr(fused_results[0], "content", str(fused_results[0]))
            temporal_nodes = self.temporal_graph.query_temporal()
            if temporal_nodes:
                temporal_context = "\n".join(
                    f"[T] {n.content} (session: {n.session_id}, date: {n.date_time})"
                    for n in temporal_nodes[:5]
                )
                context = f"Temporal context:\n{temporal_context}\n\nGeneral context:\n{context}"

        # Tier 1.1: LLM answer generation
        predicted = self.llm.generate_answer(corrected_query, context)

        if not predicted:
            predicted = "I don't know"

        # Evaluate
        is_correct = self._evaluate(question, gold_answer, predicted, is_adversarial_q)

        tokens_used = self.llm.total_input_tokens + self.llm.total_output_tokens - tokens_before
        latency_ms = (time.time() - t0) * 1000

        method_parts = ["rag"]
        if extra_galaxies:
            method_parts.append("structured")
        if q_type.is_multi_hop and q_type.sub_queries:
            method_parts.append("decomposed")
        if q_type.is_temporal and self.use_temporal_graph:
            method_parts.append("temporal")
        if abstained:
            method_parts.append("abstained")

        return RAGResult(
            question=question, gold_answer=gold_answer,
            predicted_answer=predicted, is_correct=is_correct,
            method="+".join(method_parts), latency_ms=latency_ms,
            tokens_used=tokens_used, query_type=q_type.category,
            retrieved_count=len(fused_results), abstained=abstained,
        )

    def _evaluate(self, question: str, gold_answer: str,
                  predicted: str, is_adversarial: bool) -> bool:
        """Evaluate predicted answer against gold answer."""
        # For adversarial questions, correct answer is "I don't know" or refusal
        if is_adversarial:
            predicted_lower = predicted.lower().strip()
            return any(phrase in predicted_lower for phrase in [
                "i don't know", "i do not know", "not sure", "cannot",
                "can't answer", "no information", "don't have",
            ])

        # Tier 1.2: LLM-as-judge
        if self.use_judge and self.llm.is_available:
            return self.llm.judge_answer(question, gold_answer, predicted)

        # Fallback: enhanced substring matching
        return _enhanced_match(gold_answer, predicted)

    def get_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "llm_available": self.llm.is_available,
            "total_llm_calls": self.llm.total_calls,
            "total_input_tokens": self.llm.total_input_tokens,
            "total_output_tokens": self.llm.total_output_tokens,
            "retrieval_limit": self.retrieval_limit,
        }


def _enhanced_match(gold: str, predicted: str) -> bool:
    """Enhanced substring matching fallback when LLM judge is unavailable."""
    gold_clean = re.sub(r"\s+", " ", str(gold).strip().lower())
    pred_clean = re.sub(r"\s+", " ", str(predicted).strip().lower())

    if not gold_clean:
        return False
    if gold_clean in pred_clean:
        return True

    gold_terms = re.findall(r"\b\w+\b", gold_clean)
    key_terms = [t for t in gold_terms if t not in _STOP_WORDS and len(t) > 2]
    if not key_terms:
        return False
    matches = sum(1 for t in key_terms if t in pred_clean)
    return matches / len(key_terms) >= 0.6
