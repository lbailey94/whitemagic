#!/usr/bin/env python3
"""LongMemEval-S benchmark adapter for WhiteMagic v5.

Turn-level retrieval adapter for LongMemEval-S (not official QA accuracy).
Runs questions through the real v5 MCP server via memory.hybrid_recall
(BM25-only without WM_EMBEDDER_ENDPOINT; hybrid fusion when an embedder
is up). Search is OR + token-coverage.

For each question:
1. Start a fresh `wm serve` process with a fresh tempdir store.
2. Batch-ingest all haystack turns via memory.batch_create (with tags).
3. Search via memory.hybrid_recall.
4. Evaluate turn-level Recall@1/5/10, MRR (substring-or-id), candidate
   presence, and expected-session evidence.
5. Kill the process.

Usage:
    python3 scripts/longmemeval_bench.py [--max-questions N] [--binary PATH]
    python3 scripts/longmemeval_bench.py --max-questions 50  # quick subset

Dataset path defaults to /home/lucas/Desktop/WHITEMAGIC/benchmarks/data/longmemeval_s
Override with --dataset PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from eval_protocol import (
    LEGACY_PROTOCOL,
    STRICT_PROTOCOL,
    audit_jsonrpc_batch,
    build_manifest,
    strict_evidence_score,
    write_failure_receipt,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_DATASET = "/home/lucas/Desktop/WHITEMAGIC/benchmarks/data/longmemeval_s"
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "benchmarks", "results")


# ── Keyword extraction (ported from v26 adapter) ────────────────────────────

def extract_search_keywords(content: str) -> list[str]:
    """Extract entity-rich keywords from a turn to augment indexing."""
    extras = []
    text = content.lower()

    if re.search(r'\bdr\.\s*\w+|doctor|physician|dermatolog|ent specialist\b', text):
        extras.append('doctor')
    if re.search(r'\bprescription|appointment with|follow.?up appointment\b', text):
        extras.append('appointment')
    if re.search(r'\bbike|bicycle\b', text):
        extras.append('bike')
    if re.search(r'\bservice|repair|tune.?up\b', text) and re.search(r'\bbike|bicycle\b', text):
        extras.append('bike_service')
    if re.search(r'\bviolin|guitar|piano|cello|flute\b', text):
        extras.append('instrument')
    if re.search(r'\bconcert|gig|performance|recital\b', text):
        extras.append('concert')
    if re.search(r'\bphotograph|camera|lens|sony|canon|nikon\b', text):
        extras.append('photography')
    if re.search(r'\bwedding|bride|groom\b', text):
        extras.append('wedding')
    if re.search(r'\bplant|garden|watering|repot\b', text):
        extras.append('plant')
    if re.search(r'\bbake|recipe|cook\b', text):
        extras.append('cooking')
    if re.search(r'\bmy favorite|i prefer|i like|i enjoy\b', text):
        extras.append('preference')

    return extras


def extract_context_terms(content: str, limit: int = 60) -> list[str]:
    """Return compact, searchable terms for an adjacent-turn context field."""
    stopwords = {
        "about", "after", "again", "also", "and", "are", "because", "been",
        "being", "before", "could", "did", "does", "from", "have", "into",
        "just", "more", "most", "only", "some", "that", "their", "there",
        "these", "they", "this", "those", "very", "what", "when", "where",
        "which", "while", "with", "would", "your",
    }
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]{2,}", content.lower()):
        term = term.strip("'-")
        if len(term) < 3 or term in stopwords or term in terms:
            continue
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


# ── MCP server interaction ──────────────────────────────────────────────────

def find_binary(explicit: str | None = None) -> str:
    candidates = []
    if explicit:
        candidates.append(explicit)
    env_bin = os.environ.get("WM_BINARY")
    if env_bin:
        candidates.append(env_bin)
    for profile in ("release", "debug"):
        candidates.append(os.path.join(REPO_ROOT, "target", profile, "wm"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise SystemExit(
        f"wm binary not found. Build it first (cargo build --release) or pass --binary. "
        f"Tried: {candidates}"
    )


def run_server_batch(
    binary: str,
    store: str,
    requests: list[str],
    timeout: int = 300,
) -> list[dict[str, Any]]:
    """Run a batch of JSON-RPC requests against a fresh wm serve process."""
    env = os.environ.copy()
    # Disable dispatch-level rate limiting for benchmarking
    env["WM_DISPATCH_GLOBAL_RPM"] = "0"
    env["WM_DISPATCH_TOOL_RPM"] = "0"
    env["WM_DISPATCH_BURST"] = "0"
    proc = subprocess.run(
        [
            binary, "serve",
            "--store", store,
            "--profile", "full",
            "--max-requests", "0",
            "--rate-limit", "0",
        ],
        input="\n".join(requests) + "\n",
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"wm subprocess failed with exit {proc.returncode}: {proc.stderr.strip()}"
        )
    responses = []
    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"malformed JSON-RPC response: {line!r}") from exc
    return responses


def run_server_batch_split(
    binary: str,
    store: str,
    requests: list[str],
    search_id: int,
    batch_ids: list[int],
    timeout: int = 300,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Fresh-process batch with SPLIT timing windows (the 2026-08-29
    watch item: end-to-end p95 conflated ingest, search and spawn).

    Sends the same single fresh process (the single-process optimization
    is preserved), but streams requests and reads responses in order so
    each phase is timed by its own last response:
      - spawn_ms: process start -> initialize response
      - ingest_ms: first memory.batch_create write -> last ingest response
      - search_ms: search request write -> search response
    """
    env = os.environ.copy()
    env["WM_DISPATCH_GLOBAL_RPM"] = "0"
    env["WM_DISPATCH_TOOL_RPM"] = "0"
    env["WM_DISPATCH_BURST"] = "0"

    windows = {"spawn_ms": 0.0, "ingest_ms": 0.0, "search_ms": 0.0}
    responses: list[dict[str, Any]] = []
    proc = subprocess.Popen(
        [
            binary, "serve",
            "--store", store,
            "--profile", "full",
            "--max-requests", "0",
            "--rate-limit", "0",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=env,
    )
    t_spawn_start = time.perf_counter()
    ingest_start: float | None = None
    search_start: float | None = None
    try:
        assert proc.stdin is not None and proc.stdout is not None
        for req_line in requests:
            req = json.loads(req_line)
            rid = req.get("id")
            if rid == search_id:
                search_start = time.perf_counter()
            elif rid in batch_ids and ingest_start is None:
                ingest_start = time.perf_counter()
            proc.stdin.write(req_line + "\n")
            proc.stdin.flush()
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError("server closed before all responses arrived")
                line = line.strip()
                if not line:
                    continue
                resp = json.loads(line)
                responses.append(resp)
                break
            if resp.get("id") == 1:
                windows["spawn_ms"] = (time.perf_counter() - t_spawn_start) * 1000
            elif resp.get("id") == search_id and search_start is not None:
                windows["search_ms"] = (time.perf_counter() - search_start) * 1000
            elif resp.get("id") in batch_ids:
                windows["ingest_ms"] = (time.perf_counter() - (ingest_start or t_spawn_start)) * 1000
    finally:
        try:
            proc.kill()
        except OSError:
            pass
        proc.wait(timeout=10)
    return responses, windows


class PersistentServer:
    """Long-running wm serve process that avoids repeated ONNX model loading.

    Uses a single store directory. Each question should use a unique galaxy
    name to avoid cross-question contamination in search results.
    """

    def __init__(self, binary: str, store: str):
        self.binary = binary
        self.store = store
        self.proc: subprocess.Popen | None = None
        self._req_id = 0

    def start(self):
        env = os.environ.copy()
        env["WM_DISPATCH_GLOBAL_RPM"] = "0"
        env["WM_DISPATCH_TOOL_RPM"] = "0"
        env["WM_DISPATCH_BURST"] = "0"
        os.makedirs(self.store, exist_ok=True)
        self.proc = subprocess.Popen(
            [
                self.binary, "serve",
                "--store", self.store,
                "--profile", "full",
                "--max-requests", "0",
                "--rate-limit", "0",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        # Send initialize and wait for response
        self._send_recv('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}')
        # Disable resource rules
        self._send_recv(json.dumps({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "wm", "arguments": {
                "route": "sandbox.set_limits", "args": {
                    "max_writes_per_minute": 100000,
                    "max_spawns_per_minute": 100000,
                    "max_network_per_minute": 100000,
                    "max_repeats": 100000,
                    "require_human_review": False,
                },
            }},
        }))

    def _send_recv(self, req_line: str) -> dict[str, Any] | None:
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            return None
        self.proc.stdin.write(req_line + "\n")
        self.proc.stdin.flush()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            ready, _, _ = select.select([self.proc.stdout], [], [], min(remaining, 1.0))
            if not ready:
                continue
            line = self.proc.stdout.readline()
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None

    def send_batch(self, requests: list[str], timeout: int = 600) -> list[dict[str, Any]]:
        """Send multiple requests and collect all responses."""
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            return []
        expected = len(requests)
        for req in requests:
            self.proc.stdin.write(req + "\n")
        self.proc.stdin.flush()
        responses = []
        deadline = time.monotonic() + timeout
        while len(responses) < expected and time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            ready, _, _ = select.select([self.proc.stdout], [], [], min(remaining, 1.0))
            if not ready:
                continue
            line = self.proc.stdout.readline()
            line = line.strip()
            if not line:
                continue
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return responses

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


def parse_tool_response(d: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a tools/call response into the inner JSON payload."""
    if d.get("error"):
        return {"_error": d["error"].get("message", "unknown")[:200]}
    result = d.get("result", {})
    content = result.get("content", [])
    if not content:
        return None
    try:
        text = content[0].get("text", "")
        return json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError):
        return None


# ── Evaluation ──────────────────────────────────────────────────────────────

def evaluate_result(
    results: list[dict[str, Any]],
    answer: str,
    answer_memory_ids: set[str],
    answer_session_ids: set[str] | None = None,
    memory_session_ids: dict[str, str] | None = None,
    candidate_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Report final rank plus candidate, text, and session evidence."""
    candidate_results = candidate_results if candidate_results is not None else results
    answer_session_ids = answer_session_ids or set()
    memory_session_ids = memory_session_ids or {}
    match_ranks = []
    id_match_ranks = []
    text_match_ranks = []
    candidate_id_match_ranks = []
    candidate_session_ranks = []
    session_ranks = []
    answer_clean = re.sub(r"\s+", " ", answer.strip().lower())

    for rank, r in enumerate(results, 1):
        mem_id = r.get("id", r.get("memory_id", ""))
        content = str(r.get("content", r.get("content_preview", "")))
        mem_id = str(mem_id)
        session_id = memory_session_ids.get(mem_id)

        # Check by memory ID match
        id_match = mem_id in answer_memory_ids
        if id_match:
            id_match_ranks.append(rank)
            match_ranks.append(rank)

        # Check by answer string containment
        content_clean = re.sub(r"\s+", " ", content.strip().lower())
        if answer_clean and len(answer_clean) >= 3 and answer_clean in content_clean:
            text_match_ranks.append(rank)
            if not id_match:
                match_ranks.append(rank)

        if session_id in answer_session_ids:
            session_ranks.append(rank)

    for _rank, r in enumerate(candidate_results, 1):
        mem_id = str(r.get("id", r.get("memory_id", "")))
        if mem_id in answer_memory_ids:
            candidate_id_match_ranks.append(_rank)
        if memory_session_ids.get(mem_id) in answer_session_ids:
            candidate_session_ranks.append(_rank)

    return {
        "recall_at_1": 1 if any(r <= 1 for r in match_ranks) else 0,
        "recall_at_5": 1 if any(r <= 5 for r in match_ranks) else 0,
        "recall_at_10": 1 if any(r <= 10 for r in match_ranks) else 0,
        "mrr": 1.0 / match_ranks[0] if match_ranks else 0.0,
        "first_match_rank": match_ranks[0] if match_ranks else None,
        "candidate_count": len(candidate_results),
        "candidate_presence": bool(candidate_id_match_ranks),
        "candidate_first_match_rank": candidate_id_match_ranks[0]
        if candidate_id_match_ranks
        else None,
        "answer_text_presence": bool(text_match_ranks),
        "expected_session_presence": bool(session_ranks),
        "expected_session_candidate_presence": bool(candidate_session_ranks),
        "expected_session_first_match_rank": session_ranks[0] if session_ranks else None,
        "id_match": bool(id_match_ranks),
    }


# ── Main benchmark runner ───────────────────────────────────────────────────

def run_benchmark(
    binary: str,
    dataset_path: str,
    max_questions: int | None = None,
    limit: int = 10,
    use_keywords: bool = False,
    use_composites: bool = False,
    use_contextual: bool = False,
    candidate_limit: int = 100,
    search_route: str = "memory.search",
    output_path: str | None = None,
    per_case: bool = False,
    rerank: bool = False,
    rerank_alpha: float = 0.7,
    persistent: bool = False,
    trust_labels: bool = False,
    conformal: bool = False,
    store_path: str | None = None,
) -> dict[str, Any]:
    """Run the LongMemEval-S benchmark through the v5 MCP server.

    ``use_contextual`` adds adjacent-turn terms to each canonical memory's
    indexed tags. It is deliberately benchmark-scoped until its ranking impact
    is shown to be positive.
    """

    print("\n" + "=" * 70)
    benchmark_system = "WhiteMagic v6" if search_route == "memory.episodic_search" else "WhiteMagic v5 compatibility"
    print(f"{benchmark_system} — LongMemEval-S Benchmark")
    print("=" * 70)
    print(f"Binary: {binary}")
    print(f"Dataset: {dataset_path}")
    print(f"Keywords: {'on' if use_keywords else 'off'}")
    print(f"Composite windows: {'on' if use_composites else 'off'}")
    print(f"Contextual indexing: {'on' if use_contextual else 'off'}")
    print(f"Search route: {search_route}")
    print(f"Rerank: {'on (alpha={})'.format(rerank_alpha) if rerank else 'off'}")
    print(f"Limit: {limit}")
    print(f"Candidate limit: {candidate_limit}")
    print(f"Persistent server: {'on' if persistent else 'off'}")
    sys.stdout.flush()

    # Load dataset
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    if max_questions:
        dataset = dataset[:max_questions]

    total_q = len(dataset)
    type_counts = Counter(item["question_type"] for item in dataset)
    print(f"\nDataset: {total_q} questions")
    for qt, c in type_counts.most_common():
        print(f"  {qt}: {c}")
    sys.stdout.flush()

    # Accumulators
    recall_at_1 = 0
    recall_at_5 = 0
    recall_at_10 = 0
    mrr_sum = 0.0
    candidate_presence_count = 0
    session_presence_count = 0
    search_latencies: list[float] = []
    ingest_times: list[float] = []
    spawn_ms_times: list[float] = []
    ingest_ms_times: list[float] = []
    cat_stats: dict[str, dict[str, int]] = {}
    per_query_results: list[dict[str, Any]] = []
    errors: list[str] = []
    execution_failures: list[dict[str, Any]] = []
    strict_source_r1 = 0
    strict_source_r5 = 0
    strict_coverage_sum = 0.0

    benchmark_start = time.perf_counter()

    # Persistent server mode: one long-running process for all questions.
    # Uses a single store; for memory.search, each question gets a unique galaxy
    # to avoid contamination. For episodic_search, contamination is minimal since
    # queries are specific and haystacks are large (~500 turns per question).
    persistent_server: PersistentServer | None = None
    persistent_store: str | None = None
    if persistent:
        persistent_store = store_path or tempfile.mkdtemp(prefix="wm_bench_persist_")
        persistent_server = PersistentServer(binary, persistent_store)
        print("Starting persistent server (loading ONNX model once)...")
        sys.stdout.flush()
        persistent_server.start()
        print("Persistent server ready.")
        sys.stdout.flush()

    conformal_eval = 0
    conformal_needle_in_set = 0
    conformal_set_sizes: list[int] = []
    try:
     for qi, item in enumerate(dataset):
        qid = item["question_id"]
        qtype = item["question_type"]
        question = item["question"]
        answer = str(item["answer"])

        if qtype not in cat_stats:
            cat_stats[qtype] = {"total": 0, "r1": 0, "r5": 0, "r10": 0}
        cat_stats[qtype]["total"] += 1

        # Fresh tempdir store for this question (non-persistent mode)
        # In persistent mode, we reuse the same store with galaxy "codex".
        # For memory.search, galaxy filtering prevents cross-question contamination.
        # For memory.episodic_search, all episodic records mix but queries are
        # specific enough that the correct turn still ranks in top-K.
        tmpdir = tempfile.mkdtemp(prefix=f"wm_bench_{qi}_")
        galaxy_name = "codex"

        # ── Phase 1+2: Ingest + Search in a single process ───────────────
        # Combining ingest and search avoids process startup overhead and
        # ensures the Tantivy index is fully visible to the search.
        t0 = time.perf_counter()

        sessions = item["haystack_sessions"]
        session_ids = item["haystack_session_ids"]
        turns_count = 0
        answer_memory_ids: set[str] = set()
        answer_session_ids: set[str] = set()
        memory_session_by_index: list[str] = []

        # Build batch: initialize + sandbox.set_limits + all memory.create calls + search
        # In persistent mode, skip initialize/sandbox (already done at startup).
        if persistent_server:
            all_reqs = []
        else:
            all_reqs = ['{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}']

            # Disable resource rules write budget for benchmarking
            all_reqs.append(json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "wm",
                    "arguments": {
                        "route": "sandbox.set_limits",
                        "args": {
                            "max_writes_per_minute": 100000,
                            "max_spawns_per_minute": 100000,
                            "max_network_per_minute": 100000,
                            "max_repeats": 100000,
                            "require_human_review": False,
                        },
                    },
                },
            }))

        # Track which item indices correspond to has_answer turns
        has_answer_indices: set[int] = set()
        batch_items: list[dict] = []
        # Trust-label experiment (V8 S8): needle sessions get user/1.0,
        # distractors a non-user class (0.7) — simulates the doctrine's
        # "correct heritage stamps first, then enable WM_TRUST_WEIGHT".
        needle_sessions: set[str] = set()
        if trust_labels:
            for si, session in enumerate(sessions):
                if any(t.get("has_answer", False) for t in session):
                    needle_sessions.add(session_ids[si])

        for si, session in enumerate(sessions):
            sid = session_ids[si]
            session_items: list[dict[str, Any]] = []
            nonempty_turns = [turn for turn in session if turn.get("content", "").strip()]
            for ti, turn in enumerate(nonempty_turns):
                content = turn.get("content", "")
                if not content.strip():
                    continue
                role = turn.get("role", "user")
                has_answer = turn.get("has_answer", False)

                tags = [role, sid]
                if has_answer:
                    tags.append("has_answer")
                    has_answer_indices.add(len(batch_items))
                if use_keywords:
                    tags.extend(extract_search_keywords(content))
                if use_contextual:
                    for neighbor_index in (ti - 1, ti + 1):
                        if 0 <= neighbor_index < len(nonempty_turns):
                            tags.extend(
                                f"ctx_{term}"
                                for term in extract_context_terms(
                                    nonempty_turns[neighbor_index].get("content", "")
                                )
                            )

                item_obj = {
                    "content": content,
                    "galaxy": galaxy_name,
                    "tags": tags,
                }
                if trust_labels:
                    item_obj["source"] = (
                        "user" if sid in needle_sessions else "heritage-distractor"
                    )
                batch_items.append(item_obj)
                memory_session_by_index.append(sid)
                session_items.append(item_obj)
                turns_count += 1

            if use_composites:
                for wi in range(len(session_items) - 1):
                    first = session_items[wi]
                    second = session_items[wi + 1]
                    composite = {
                        "content": f"{first['content']}\n{second['content']}",
                        "galaxy": galaxy_name,
                        "tags": ["composite", sid, f"window_{wi}"],
                    }
                    if use_keywords:
                        composite["tags"].extend(
                            extract_search_keywords(composite["content"])
                        )
                    batch_items.append(composite)
                    memory_session_by_index.append(sid)

        # Chunk batch_items into multiple batch_create requests to stay
        # under the 64KB MCP params limit. Each chunk gets its own request ID.
        # Track chunk ranges so we can map answer indices to the correct batch.
        MAX_PARAMS_BYTES = 60_000  # leave headroom under 64KB limit
        batch_ids: list[int] = []
        chunk_ranges: list[tuple[int, int]] = []  # (start, end_exclusive)
        req_id = 3 if not persistent_server else 100
        chunk: list[dict] = []
        chunk_start = 0

        for i, item_obj in enumerate(batch_items):
            test_chunk = chunk + [item_obj]
            test_size = len(json.dumps({"items": test_chunk}))
            if test_size > MAX_PARAMS_BYTES and chunk:
                all_reqs.append(json.dumps({
                    "jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                    "params": {"name": "wm", "arguments": {
                        "route": "memory.batch_create",
                        "args": {"items": chunk},
                    }},
                }))
                batch_ids.append(req_id)
                chunk_ranges.append((chunk_start, i))
                req_id += 1
                chunk = []
                chunk_start = i
            chunk.append(item_obj)
        if chunk:
            all_reqs.append(json.dumps({
                "jsonrpc": "2.0", "id": req_id, "method": "tools/call",
                "params": {"name": "wm", "arguments": {
                    "route": "memory.batch_create",
                    "args": {"items": chunk},
                }},
            }))
            batch_ids.append(req_id)
            chunk_ranges.append((chunk_start, len(batch_items)))
            req_id += 1

        # Search request: use min_score_ratio=0 to disable relative floor.
        # Retrieve a broad candidate set, then evaluate only the requested top-k.
        # (with 500+ docs, BM25 score distribution shifts and 5% floor over-filters)
        search_id = req_id
        search_args = {
            "query": question,
            "limit": max(limit, candidate_limit),
        }
        if search_route == "memory.search":
            search_args.update({
                "galaxy": galaxy_name,
                "min_score_ratio": 0.0,
            })
        elif search_route == "memory.episodic_search":
            search_args["include_historical"] = False
            search_args["candidate_limit"] = candidate_limit
            if rerank:
                search_args["rerank"] = True
                search_args["rerank_alpha"] = rerank_alpha
        else:
            raise ValueError(f"unsupported search route: {search_route}")

        search_req = {
            "jsonrpc": "2.0",
            "id": search_id,
            "method": "tools/call",
            "params": {
                "name": "wm",
                "arguments": {
                    "route": search_route,
                    "args": search_args,
                },
            },
        }
        all_reqs.append(json.dumps(search_req))

        # Send all requests (ingest + search) in a single process to avoid
        # a second process startup (especially costly with ONNX model
        # loading). The fresh-process path uses SPLIT timing windows (spawn
        # vs ingest vs search — the 2026-08-29 watch item); the persistent
        # path has no spawn cost and keeps whole-batch timing.
        t_search = time.perf_counter()
        if persistent_server:
            all_responses = persistent_server.send_batch(all_reqs, timeout=600)
            latency_ms = (time.perf_counter() - t_search) * 1000
        else:
            all_responses, windows = run_server_batch_split(
                binary, tmpdir, all_reqs, search_id, batch_ids, timeout=600
            )
            latency_ms = windows["search_ms"]
            spawn_ms_times.append(windows["spawn_ms"])
            ingest_ms_times.append(windows["ingest_ms"])
        ingest_sec = time.perf_counter() - t0
        ingest_times.append(ingest_sec)

        case_failures = audit_jsonrpc_batch(all_responses, batch_ids, search_id)
        for failure in case_failures:
            failure["question_id"] = qid
        execution_failures.extend(case_failures)

        # Parse batch_create responses to find answer memory IDs
        # Each batch response contains IDs for items in its chunk range
        batch_responses: dict[int, list[str]] = {}
        for d in all_responses:
            rid = d.get("id")
            if rid in batch_ids and not d.get("error"):
                payload = parse_tool_response(d)
                if payload and payload.get("status") == "success" and "ids" in payload:
                    batch_responses[rid] = payload["ids"]

        # Map answer indices to memory IDs via chunk ranges
        for gidx in has_answer_indices:
            for bi, bid in enumerate(batch_ids):
                start, end = chunk_ranges[bi]
                if start <= gidx < end:
                    local_idx = gidx - start
                    ids = batch_responses.get(bid, [])
                    if local_idx < len(ids):
                        answer_memory_ids.add(str(ids[local_idx]))
                    break

        # Parse search results
        candidate_results = []
        for d in all_responses:
            if d.get("id") == search_id:
                payload = parse_tool_response(d)
                if payload:
                    if payload.get("status") == "success" or "results" in payload:
                        candidate_results = payload.get("results", payload.get("memories", []))
                    elif payload.get("_error"):
                        errors.append(f"Q{qi} ({qid}): {payload['_error']}")

        results = candidate_results[:limit]
        memory_session_ids: dict[str, str] = {}
        for gidx, sid in enumerate(memory_session_by_index):
            for bi, bid in enumerate(batch_ids):
                start, end = chunk_ranges[bi]
                if start <= gidx < end:
                    ids = batch_responses.get(bid, [])
                    local_idx = gidx - start
                    if local_idx < len(ids):
                        memory_session_ids[str(ids[local_idx])] = sid
                    break
        answer_session_ids = {
            memory_session_ids[mem_id]
            for mem_id in answer_memory_ids
            if mem_id in memory_session_ids
        }

        search_latencies.append(latency_ms)

        # ── Phase 3: Evaluate ──────────────────────────────────────────────
        ev = evaluate_result(
            results,
            answer,
            answer_memory_ids,
            answer_session_ids,
            memory_session_ids,
            candidate_results,
        )
        strict = strict_evidence_score(results, answer_memory_ids)
        if case_failures:
            # Invalid execution stays in the denominator and cannot score.
            ev.update({"recall_at_1": 0, "recall_at_5": 0, "recall_at_10": 0, "mrr": 0.0, "first_match_rank": None})
            strict.update({"relevant_source_hit_at_1": 0, "relevant_source_hit_at_5": 0, "relevant_source_mrr": 0.0, "required_evidence_coverage_at_retrieval_limit": 0.0})
        strict_source_r1 += strict["relevant_source_hit_at_1"]
        strict_source_r5 += strict["relevant_source_hit_at_5"]
        strict_coverage_sum += strict["required_evidence_coverage_at_retrieval_limit"] or 0.0
        recall_at_1 += ev["recall_at_1"]
        recall_at_5 += ev["recall_at_5"]
        recall_at_10 += ev["recall_at_10"]
        mrr_sum += ev["mrr"]
        candidate_presence_count += int(ev["candidate_presence"])
        session_presence_count += int(ev["expected_session_presence"])
        cat_stats[qtype]["r1"] += ev["recall_at_1"]
        cat_stats[qtype]["r5"] += ev["recall_at_5"]
        cat_stats[qtype]["r10"] += ev["recall_at_10"]

        # Conformal-set evidence (V8 S8): send ground-truth labels for the
        # graded results, then count needle-in-set on the disclosure.
        conformal_info = None
        if conformal:
            for d in all_responses:
                if d.get("id") == search_id:
                    payload = parse_tool_response(d)
                    if payload:
                        conformal_info = payload.get("conformal_set")
            matched_needle_in_set = 0
            for r in results:
                mem_id = str(r.get("id", r.get("memory_id", "")))
                if mem_id in answer_memory_ids and r.get("in_conformal_set"):
                    matched_needle_in_set = 1
                    break
            calibrating = conformal_info is not None and conformal_info.get("status") != "active"
            answer_clean = re.sub(r"\s+", " ", answer.strip().lower())
            fb_samples = []
            for r in results:
                mem_id = str(r.get("id", r.get("memory_id", "")))
                content_clean = re.sub(r"\s+", " ", str(r.get("content", "")).strip().lower())
                relevant = mem_id in answer_memory_ids or (
                    len(answer_clean) >= 3 and answer_clean in content_clean
                )
                fb_samples.append({"score": float(r.get("score", 0.0)), "relevant": relevant})
            if persistent_server:
                fb_req = json.dumps({
                    "jsonrpc": "2.0", "id": 9000 + qi, "method": "tools/call",
                    "params": {"name": "wm", "arguments": {
                        "route": "memory.recall_feedback",
                        "args": {"samples": fb_samples},
                    }},
                })
                persistent_server.send_batch([fb_req], timeout=120)
            if not calibrating:
                conformal_eval += 1
                conformal_needle_in_set += matched_needle_in_set
                if conformal_info and isinstance(conformal_info.get("set_size"), int):
                    conformal_set_sizes.append(conformal_info["set_size"])

        done_count = qi + 1
        elapsed = time.perf_counter() - benchmark_start
        pct = done_count / total_q * 100
        if done_count > 0:
            eta_sec = elapsed / done_count * (total_q - done_count)
            eta_str = f"{int(eta_sec // 60)}m{int(eta_sec % 60)}s"
        else:
            eta_str = "?"
        r1_so_far = recall_at_1 / done_count
        r5_so_far = recall_at_5 / done_count
        r10_so_far = recall_at_10 / done_count

        print(
            f"  [{done_count}/{total_q}] {pct:5.1f}% | "
            f"R@1={r1_so_far:.1%} R@5={r5_so_far:.1%} R@10={r10_so_far:.1%} | "
            f"ingest={ingest_sec:.2f}s search={latency_ms:.0f}ms | "
            f"ETA {eta_str}"
        )
        sys.stdout.flush()

        if per_case:
            per_query_results.append({
                "question_id": qid,
                "question_type": qtype,
                "question": question,
                "answer": answer,
                "recall_at_1": ev["recall_at_1"],
                "recall_at_5": ev["recall_at_5"],
                "recall_at_10": ev["recall_at_10"],
                "mrr": round(ev["mrr"], 4),
                "first_match_rank": ev["first_match_rank"],
                "candidate_count": ev["candidate_count"],
                "candidate_presence": ev["candidate_presence"],
                "candidate_first_match_rank": ev["candidate_first_match_rank"],
                "answer_text_presence": ev["answer_text_presence"],
                "expected_session_presence": ev["expected_session_presence"],
                "expected_session_candidate_presence": ev["expected_session_candidate_presence"],
                "latency_ms": round(latency_ms, 2),
                "turns_ingested": turns_count,
                "ingest_time_s": round(ingest_sec, 3),
                "results_count": len(results),
                "valid_execution": not case_failures,
                "execution_failures": case_failures,
                "legacy_scoring": {"protocol": LEGACY_PROTOCOL, **ev},
                "strict_scoring": strict,
                # Preserve the actual retrieval output used by the scorer.
                # This makes --per-case an auditable evidence mode without
                # changing ranking, denominators, or scoring semantics.
                "retrieved_results": results,
                "candidate_results": candidate_results,
            })

        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

    finally:
        if persistent_server:
            persistent_server.stop()
            if persistent_store and not store_path:
                shutil.rmtree(persistent_store, ignore_errors=True)

    # Compute final results
    total_elapsed = time.perf_counter() - benchmark_start
    search_latencies.sort()
    cat_breakdown: dict[str, dict[str, float]] = {}
    for cat, stats in cat_stats.items():
        t = stats["total"]
        cat_breakdown[cat] = {
            "total": t,
            "recall_at_1": stats["r1"] / t if t > 0 else 0,
            "recall_at_5": stats["r5"] / t if t > 0 else 0,
            "recall_at_10": stats["r10"] / t if t > 0 else 0,
        }

    results = {
        "execution_path": "local-wm-serve-stdio",
        "retrieval_configuration": {"route": search_route, "real_embedder_required": False},
        "answer_generation_model": None,
        "benchmark": "longmemeval_s",
        "version": "v6-dev" if search_route == "memory.episodic_search" else "v5.8.0-compat-on-v6",
        "dataset": "LongMemEval-S (ICLR 2025)",
        "protocol": "legacy retrieval proxy: memory-ID or normalized answer-substring; expected-session presence is diagnostic only; not official LongMemEval QA",
        "protocol_versions": {"legacy": LEGACY_PROTOCOL, "strict": STRICT_PROTOCOL},
        "search_route": search_route,
        "rerank": rerank,
        "rerank_alpha": rerank_alpha,
        "keyword_extraction": use_keywords,
        "composite_windows": use_composites,
        "contextual_indexing": use_contextual,
        "candidate_limit": candidate_limit,
        "timing": "fresh-process path: split windows — spawn_ms = start->initialize response, ingest_ms = batch_create round-trips, search_ms = search request round-trip (p50/p95 below are SEARCH-ONLY on that path). persistent path: whole-batch timing (no spawn per question).",
        "split_windows": {
            "spawn": {
                "count": len(spawn_ms_times),
                "p50_ms": sorted(spawn_ms_times)[len(spawn_ms_times) // 2] if spawn_ms_times else 0,
            },
            "ingest": {
                "count": len(ingest_ms_times),
                "p50_ms": sorted(ingest_ms_times)[len(ingest_ms_times) // 2] if ingest_ms_times else 0,
            },
            "search_p50_source": "search window only (split)" if spawn_ms_times else "whole batch (persistent path)",
        },
        "total_questions": total_q,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_elapsed_s": round(total_elapsed, 1),
        "search": {
            "count": len(search_latencies),
            "p50_ms": search_latencies[len(search_latencies) // 2] if search_latencies else 0,
            "p95_ms": search_latencies[int(len(search_latencies) * 0.95)] if len(search_latencies) > 1 else 0,
            "p99_ms": search_latencies[int(len(search_latencies) * 0.99)] if len(search_latencies) > 1 else 0,
        },
        "ingest": {
            "avg_time_s": sum(ingest_times) / len(ingest_times) if ingest_times else 0,
            "total_time_s": sum(ingest_times),
        },
        "recall": {
            "total_queries": total_q,
            "recall_at_1": recall_at_1 / total_q if total_q > 0 else 0,
            "recall_at_5": recall_at_5 / total_q if total_q > 0 else 0,
            "recall_at_10": recall_at_10 / total_q if total_q > 0 else 0,
            "mrr": mrr_sum / total_q if total_q > 0 else 0,
            "candidate_presence": candidate_presence_count / total_q if total_q > 0 else 0,
            "expected_session_presence": session_presence_count / total_q if total_q > 0 else 0,
        },
        "strict_evidence": {
            "relevant_source_hit_rate_at_1": strict_source_r1 / total_q if total_q else 0,
            "relevant_source_hit_rate_at_5": strict_source_r5 / total_q if total_q else 0,
            "mean_required_evidence_coverage_at_retrieval_limit": strict_coverage_sum / total_q if total_q else 0,
            "supported_answer_correctness": None,
            "supported_answer_correctness_status": "not_applicable_no_answer_model"
        },
        "category_results": cat_breakdown,
        "valid_execution": not execution_failures,
        "execution_failures": execution_failures,
        "errors": errors,
    }
    if trust_labels:
        results["trust_labels"] = {
            "enabled": True,
            "scheme": "needle-session turns source=user (1.0); others heritage-distractor (0.7)",
        }
    if conformal:
        results["conformal"] = {
            "enabled": True,
            "alpha_env": os.environ.get("WM_RECALL_CONFORMAL_ALPHA"),
            "evaluated_questions": conformal_eval,
            "needle_in_set_coverage": (
                conformal_needle_in_set / conformal_eval if conformal_eval else None
            ),
            "mean_set_size": (
                sum(conformal_set_sizes) / len(conformal_set_sizes)
                if conformal_set_sizes
                else None
            ),
        }
    if per_case:
        results["per_query"] = per_query_results

    # Save results
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nResults saved to {output_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("Results:")
    print(f"  recall@1:  {results['recall']['recall_at_1']:.2%}")
    print(f"  recall@5:  {results['recall']['recall_at_5']:.2%}")
    print(f"  recall@10: {results['recall']['recall_at_10']:.2%}")
    print(f"  MRR:       {results['recall']['mrr']:.4f}")
    print(f"  Candidate presence: {results['recall']['candidate_presence']:.2%}")
    print(f"  Expected session presence: {results['recall']['expected_session_presence']:.2%}")
    print(f"  Search p50: {results['search']['p50_ms']:.1f}ms")
    print(f"  Search p95: {results['search']['p95_ms']:.1f}ms")
    print(f"  Total time: {results['total_elapsed_s']:.1f}s")
    print("\n  Category breakdown:")
    for cat, data in sorted(results["category_results"].items()):
        print(f"    {cat}: R@1={data['recall_at_1']:.2%} R@5={data['recall_at_5']:.2%} R@10={data['recall_at_10']:.2%} ({data['total']} q)")
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:5]:
            print(f"    {e}")
    sys.stdout.flush()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="LongMemEval-S Benchmark for WhiteMagic v5")
    parser.add_argument("--binary", default=None, help="Path to wm binary")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Path to LongMemEval-S dataset")
    parser.add_argument("--max-questions", type=int, default=None, help="Limit number of questions")
    parser.add_argument("--limit", type=int, default=10, help="Results per query")
    parser.add_argument(
        "--route",
        choices=("memory.search", "memory.episodic_search"),
        default="memory.search",
        help="Search route under evaluation (default: memory.search)",
    )
    parser.add_argument("--keywords", action="store_true", help="Enable keyword extraction at index time")
    parser.add_argument(
        "--composites",
        action="store_true",
        help="Add auxiliary two-turn composite documents for each session",
    )
    parser.add_argument(
        "--contextual",
        action="store_true",
        help="Index adjacent-turn terms as non-content search tags without duplicate memories",
    )
    parser.add_argument("--candidate-limit", type=int, default=100, help="Broad candidate-set size used for presence evidence (default: 100)")
    parser.add_argument("--rerank", action="store_true", help="Enable vector reranking for episodic search")
    parser.add_argument("--rerank-alpha", type=float, default=0.7, help="Deterministic weight in hybrid score (default: 0.7)")
    parser.add_argument("--persistent", action="store_true", help="Use a single long-running server process for all questions (faster with ONNX)")
    parser.add_argument("--store", default=None, help="Persistent-mode store directory (reused if it exists, kept on exit — enables warm re-run benches)")
    parser.add_argument("--trust-labels", action="store_true", help="V8 S8: stamp needle-session turns source=user (1.0), distractors 0.7 (for the WM_TRUST_WEIGHT comparative run)")
    parser.add_argument("--conformal", action="store_true", help="V8 S8: record recall_feedback per question and measure needle-in-set coverage (requires --persistent)")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        os.makedirs(DEFAULT_OUTPUT, exist_ok=True)
        suffix = ""
        if args.max_questions:
            suffix = f"_{args.max_questions}q"
        if args.keywords:
            suffix += "_keywords"
        if args.contextual:
            suffix += "_contextual"
        if args.candidate_limit != 100:
            suffix += f"_cand{args.candidate_limit}"
        if args.route != "memory.search":
            suffix += "_episodic"
        if args.rerank:
            suffix += "_rerank"
        if args.composites:
            suffix += "_composites"
        if args.persistent:
            suffix += "_persistent"
        output_path = os.path.join(DEFAULT_OUTPUT, f"longmemeval_s_v5{suffix}.json")

    if args.conformal and not args.persistent:
        parser.error("--conformal requires --persistent (calibration must accumulate in one process)")
    try:
        binary = find_binary(args.binary)
        result = run_benchmark(
            binary=binary, dataset_path=args.dataset, max_questions=args.max_questions,
            limit=args.limit, use_keywords=args.keywords, trust_labels=args.trust_labels,
            conformal=args.conformal, use_composites=args.composites,
            use_contextual=args.contextual, candidate_limit=args.candidate_limit,
            search_route=args.route, output_path=output_path, per_case=args.per_case,
            rerank=args.rerank, rerank_alpha=args.rerank_alpha,
            persistent=args.persistent, store_path=args.store,
        )
    except BaseException as exc:
        write_failure_receipt(
            receipt_path=output_path + ".failure.json", runner=__file__,
            binary=args.binary, dataset=args.dataset,
            command=[sys.executable, *sys.argv], stage="pre_output", error=exc,
        )
        raise
    manifest = build_manifest(
        runner=__file__, binary=binary, dataset=args.dataset, output=output_path,
        command=[sys.executable, *sys.argv],
        configuration={
            "execution_path": result["execution_path"],
            "retrieval": result["retrieval_configuration"],
            "max_questions": args.max_questions,
            "limit": args.limit,
            "candidate_limit": args.candidate_limit,
            "persistent": args.persistent,
            "keywords": args.keywords,
            "composites": args.composites,
            "contextual": args.contextual,
            "rerank": args.rerank,
            "rerank_alpha": args.rerank_alpha,
        },
        failures=result["execution_failures"],
    )
    manifest_path = output_path + ".manifest.json"
    Path(manifest_path).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Run manifest saved to {manifest_path}")
    if not result["valid_execution"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
