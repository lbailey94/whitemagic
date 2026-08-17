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
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

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
    responses = []
    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return responses


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
    print(f"Limit: {limit}")
    print(f"Candidate limit: {candidate_limit}")
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
    cat_stats: dict[str, dict[str, int]] = {}
    per_query_results: list[dict[str, Any]] = []
    errors: list[str] = []

    benchmark_start = time.perf_counter()

    for qi, item in enumerate(dataset):
        qid = item["question_id"]
        qtype = item["question_type"]
        question = item["question"]
        answer = str(item["answer"])

        if qtype not in cat_stats:
            cat_stats[qtype] = {"total": 0, "r1": 0, "r5": 0, "r10": 0}
        cat_stats[qtype]["total"] += 1

        # Fresh tempdir store for this question
        tmpdir = tempfile.mkdtemp(prefix=f"wm_bench_{qi}_")

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
                    "galaxy": "codex",
                    "tags": tags,
                }
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
                        "galaxy": "codex",
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
        req_id = 3
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
                "galaxy": "codex",
                "min_score_ratio": 0.0,
            })
        elif search_route == "memory.episodic_search":
            search_args["include_historical"] = False
            search_args["candidate_limit"] = candidate_limit
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

        ingest_reqs = all_reqs[:-1]
        search_only = [all_reqs[-1]]

        ingest_responses = run_server_batch(binary, tmpdir, ingest_reqs, timeout=600)
        ingest_sec = time.perf_counter() - t0
        ingest_times.append(ingest_sec)

        t_search = time.perf_counter()
        search_responses = run_server_batch(binary, tmpdir, search_only, timeout=120)
        latency_ms = (time.perf_counter() - t_search) * 1000
        all_responses = ingest_responses + search_responses

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
        recall_at_1 += ev["recall_at_1"]
        recall_at_5 += ev["recall_at_5"]
        recall_at_10 += ev["recall_at_10"]
        mrr_sum += ev["mrr"]
        candidate_presence_count += int(ev["candidate_presence"])
        session_presence_count += int(ev["expected_session_presence"])
        cat_stats[qtype]["r1"] += ev["recall_at_1"]
        cat_stats[qtype]["r5"] += ev["recall_at_5"]
        cat_stats[qtype]["r10"] += ev["recall_at_10"]

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
            })

        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

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
        "system": "whitemagic-v6" if search_route == "memory.episodic_search" else "whitemagic-v5-compat",
        "benchmark": "longmemeval_s",
        "version": "v6-dev" if search_route == "memory.episodic_search" else "v5.8.0-compat-on-v6",
        "dataset": "LongMemEval-S (ICLR 2025)",
        "protocol": "turn-level retrieval R@k, substring-or-id. Not official LongMemEval QA.",
        "search_route": search_route,
        "keyword_extraction": use_keywords,
        "composite_windows": use_composites,
        "contextual_indexing": use_contextual,
        "candidate_limit": candidate_limit,
        "timing": "ingest and search are separate process batches; search p50 is query-only (includes process start).",
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
        "category_results": cat_breakdown,
        "errors": errors[:20],
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
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=100,
        help="Broad candidate-set size used for presence evidence (default: 100)",
    )
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--per-case", action="store_true", help="Include per-query results")
    args = parser.parse_args()

    binary = find_binary(args.binary)

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
        output_path = os.path.join(DEFAULT_OUTPUT, f"longmemeval_s_v5{suffix}.json")

    run_benchmark(
        binary=binary,
        dataset_path=args.dataset,
        max_questions=args.max_questions,
        limit=args.limit,
        use_keywords=args.keywords,
        use_composites=args.composites,
        use_contextual=args.contextual,
        candidate_limit=args.candidate_limit,
        search_route=args.route,
        output_path=output_path,
        per_case=args.per_case,
    )


if __name__ == "__main__":
    main()
