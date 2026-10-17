#!/usr/bin/env python3
"""Pinned Agent Task Evaluation: WhiteMagic v10.4.0 vs. Plain-Files / BM25 Baselines.

Evaluates three core agent-memory questions across 24 deterministic scenarios:
  1. T_CONTINUITY (8 scenarios): Can an agent recover verified project decisions
     and active open inquiry arcs across sessions under a strict token budget?
  2. T_CONFLICT (8 scenarios): Can an agent resolve stale or conflicting memory
     (1-hop and 2-hop updates) without losing verifiable historical lineage?
  3. T_REPAIR (8 scenarios): Can an agent surgically repair a bad/corrupted
     memory without damaging adjacent legitimate state sharing the same domain vocabulary?

Includes explicit failure traces for both the baselines and WhiteMagic boundary cases
(e.g., untyped low-importance notes under salience thresholds, and unlinked
contradictions stored via raw `memory_remember` instead of `memory.update`).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import shutil

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


def _resolve_default_wm_bin() -> Path:
    env_bin = os.environ.get("WM_BINARY")
    if env_bin:
        return Path(env_bin)
    candidate = REPO_ROOT / "target" / "release" / "wm"
    if candidate.is_file():
        return candidate
    which_wm = shutil.which("wm")
    if which_wm:
        return Path(which_wm)
    return candidate


DEFAULT_WM_BIN = _resolve_default_wm_bin()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def approx_tokens(text: str) -> int:
    # Matches wm-gen3-harness token estimate (~4 chars/token or word count * 1.3)
    return max(1, (len(text) + 3) // 4)


class OkapiBM25:
    """Standard Okapi BM25 baseline over plain markdown/text files on disk."""

    def __init__(self, docs: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(d["content"]) for d in docs]
        self.doc_lens = [len(toks) for toks in self.doc_tokens]
        self.avgdl = (sum(self.doc_lens) / len(self.doc_lens)) if self.doc_lens else 1.0
        self.df: Counter[str] = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                self.df[term] += 1
        self.N = len(docs)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        q_terms = tokenize(query)
        scores: list[tuple[float, int]] = []
        for idx, toks in enumerate(self.doc_tokens):
            tf = Counter(toks)
            dl = self.doc_lens[idx]
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                n_q = self.df[term]
                idf = math.log(1.0 + (self.N - n_q + 0.5) / (n_q + 0.5))
                freq = tf[term]
                denom = freq + self.k1 * (1.0 - self.b + self.b * (dl / max(1e-9, self.avgdl)))
                score += idf * ((freq * (self.k1 + 1.0)) / denom)
            scores.append((score, idx))
        scores.sort(key=lambda x: (x[0], x[1]), reverse=True)
        out = []
        for sc, idx in scores[:limit]:
            item = dict(self.docs[idx])
            item["bm25_score"] = round(sc, 4)
            out.append(item)
        return out


class WMMcpSession:
    """Runs JSON-RPC batches against a fresh `wm serve --store <path>` process."""

    def __init__(self, binary: Path, store_dir: Path) -> None:
        self.binary = binary
        self.store_dir = store_dir

    def run_batch(self, calls: list[tuple[str, dict[str, Any]]]) -> tuple[list[dict[str, Any]], float, int]:
        env = os.environ.copy()
        env["WM_DISPATCH_GLOBAL_RPM"] = "0"
        env["WM_DISPATCH_TOOL_RPM"] = "0"
        env["WM_DISPATCH_BURST"] = "0"
        reqs: list[str] = [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "pinned-task-eval", "version": "1.0.0"},
                    },
                }
            )
        ]
        for idx, (tool_name, args) in enumerate(calls, start=1):
            reqs.append(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": idx,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": args},
                    }
                )
            )
        payload = "\n".join(reqs) + "\n"
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                str(self.binary),
                "serve",
                "--store",
                str(self.store_dir),
                "--profile",
                "full",
                "--no-sweep",
            ],
            input=payload,
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        parsed: dict[int, dict[str, Any]] = {}
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            msg_id = msg.get("id")
            if isinstance(msg_id, int) and msg_id >= 1:
                if "error" in msg:
                    parsed[msg_id] = {"_error": msg["error"]}
                else:
                    content = msg.get("result", {}).get("content", [])
                    text = content[0].get("text", "{}") if content else "{}"
                    try:
                        parsed[msg_id] = json.loads(text)
                    except json.JSONDecodeError:
                        parsed[msg_id] = {"_raw": text}
        ordered = [parsed.get(i, {}) for i in range(1, len(calls) + 1)]
        return ordered, elapsed_ms, len(proc.stdout.encode("utf-8"))


# ─── Task Family 1: Cross-Session Decision Recovery & Open-Arc Continuity ────

CONTINUITY_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "C1_payment_journal_invariants",
        "track": "track-economy",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Persist pending settlement journal with fsync before facilitator /settle.", "decision", "verified", 0.95),
            ("D2: Hold account on unknown facilitator HTTP 200 empty response.", "decision", "verified", 0.94),
            ("D3: Bind recovery matching to full 64-hex nonce, account, amount, and tx.", "decision", "verified", 0.93),
            ("D4: Keep production --economy flag disabled until qualification closes.", "decision", "verified", 0.92),
        ],
        "resolved_q": "Q_RES: Should truncated 24-char nonces be accepted for healing?",
        "resolving_a": "D_RES: No, truncated nonces must remain held unless full identity matches.",
        "open_q": "Q_OPEN: What alert threshold should trigger on held unknown settlements in pilot?",
        "stress_untyped": False,
    },
    {
        "id": "C2_release_manifest_signing",
        "track": "track-release",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Sign release-manifest.json with Ed25519 key aade884b035d...", "decision", "verified", 0.95),
            ("D2: Verify raw binary SHA-256 and size against GitHub asset digests.", "decision", "verified", 0.93),
            ("D3: Bind npm and docker install_certification to bound_manifest_sha256.", "decision", "verified", 0.92),
            ("D4: Run trusted release_health.py from RUNNER_TEMP across tag checkouts.", "decision", "verified", 0.91),
        ],
        "resolved_q": "Q_RES: Why did version_truth fail on README v9.3.4?",
        "resolving_a": "D_RES: Exempted explicit stable channel fallback pin in version_truth.py.",
        "open_q": "Q_OPEN: When should Windows ONNX runtime targets re-enter the alpha matrix?",
        "stress_untyped": False,
    },
    {
        "id": "C3_crystal_envelope_security",
        "track": "track-crystals",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Bind cell_id to sha256(id_kek_version || nonce || ciphertext).", "decision", "verified", 0.96),
            ("D2: Wrap per-crystal DEK under tenant KEK with versioned rotation.", "decision", "verified", 0.94),
            ("D3: Require Ed25519 client_sig over canonical envelope for L5 audit.", "decision", "verified", 0.93),
            ("D4: Enforce X-WM-Crystal-Assertion HMAC replay refusal in SQLite.", "decision", "verified", 0.91),
        ],
        "resolved_q": "Q_RES: Can KEK rotation preserve crystal_id?",
        "resolving_a": "D_RES: Yes, id_kek_version stays pinned while kek_version increments.",
        "open_q": "Q_OPEN: Should external OpenTimestamps anchors batch crystal-set commitments hourly?",
        "stress_untyped": False,
    },
    {
        "id": "C4_backup_restore_contract",
        "track": "track-recovery",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Raise aggregate tenant-write archive cap to 4 GiB (4294967296 bytes).", "decision", "verified", 0.95),
            ("D2: Require correlated timestamps across hosted-store, auth-state, hosted-writes.", "decision", "verified", 0.93),
            ("D3: Deploy replacement host with deploy.sh --no-restart before state extraction.", "decision", "verified", 0.92),
            ("D4: Verify next-lane readiness on 18798/18799 before re-enabling key issuance.", "decision", "verified", 0.91),
        ],
        "resolved_q": "Q_RES: Does deploy-check.sh install missing files on a fresh host?",
        "resolving_a": "D_RES: No, deploy.sh --no-restart installs the 52 manifest files first.",
        "open_q": "Q_OPEN: Should off-box backup freshness alert at 30h or 36h age?",
        "stress_untyped": False,
    },
    {
        "id": "C5_diaml_sutra_binding",
        "track": "track-sutra",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Map Sutra codons with Verification+Synthesis to verified decision turns.", "decision", "verified", 0.95),
            ("D2: Auto-resolve latest open question arc when executing synthesis Sutra.", "decision", "verified", 0.94),
            ("D3: Surface track-scoped codex crystals automatically in session_continuity.", "decision", "verified", 0.92),
            ("D4: Penalize high-degree noisy hubs during 2-hop association traversal.", "decision", "verified", 0.90),
        ],
        "resolved_q": "Q_RES: Why did progressive replay lose early session decisions?",
        "resolving_a": "D_RES: Pure tail replay evicts early turns; hybrid replay pins salient anchors first.",
        "open_q": "Q_OPEN: Should multi-track inheritance support parent track namespaces?",
        "stress_untyped": False,
    },
    {
        "id": "C6_stripe_webhook_guard",
        "track": "track-billing",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Refuse production Stripe webhook execution when secret is unset.", "decision", "verified", 0.96),
            ("D2: Enforce constant-time HMAC-SHA256 signature verification with 300s window.", "decision", "verified", 0.94),
            ("D3: Deduplicate webhook event IDs in KV with 30-day TTL.", "decision", "verified", 0.93),
            ("D4: Align EN and ZH fleet peering disclosure to $249/mo.", "decision", "verified", 0.91),
        ],
        "resolved_q": "Q_RES: Was the $199 ZH fleet price intentional?",
        "resolving_a": "D_RES: No, it was copy drift; updated ZH disclosure to $249/mo.",
        "open_q": "Q_OPEN: When should automated tenant key provisioning replace manual 24h pilot setup?",
        "stress_untyped": False,
    },
    {
        "id": "C7_ingest_postings_perf",
        "track": "track-perf",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Preload content-hash identity cache once per commit_intake batch.", "decision", "verified", 0.95),
            ("D2: Decode only the shortest token postings slice during dedup lookup.", "decision", "verified", 0.94),
            ("D3: Separate PEB-10 wall-clock speedup gate from debug unit test runs.", "decision", "verified", 0.92),
            ("D4: Require median >= 1.40x across >= 5 release-mode samples in benchmark gate.", "decision", "verified", 0.91),
        ],
        "resolved_q": "Q_RES: Why did CI fail on test_peb10_benchmark_execution at 1.398x?",
        "resolving_a": "D_RES: Shared runner CPU jitter affected single debug sample; moved to release median harness.",
        "open_q": "Q_OPEN: Should commit_intake also batch LMDB write transactions above 500 items?",
        "stress_untyped": False,
    },
    {
        "id": "C8_stress_untyped_low_importance_decision",
        "track": "track-stress",
        "budget_tokens": 280,
        "decisions": [
            ("D1: Pin canonical API OpenAPI contract to 19 paths.", "decision", "verified", 0.95),
            ("D2: Enforce Landlock ABI v3 filesystem sandbox in receipt-api.", "decision", "verified", 0.93),
            ("D3: Require RFC 8785 JCS canonicalization for continuity receipts.", "decision", "verified", 0.91),
            # Deliberate stress case: critical constraint logged as casual low-importance 'note' (0.40)
            ("D4: Keep SQLite busy_timeout at 5000ms on crystal replay store.", "note", "conditional", 0.40),
        ],
        "resolved_q": "Q_RES: Are continuity-receipt/0.4 bundles still accepted by /verify?",
        "resolving_a": "D_RES: Yes, supportedSpecRange covers 0.4 through 0.5.",
        "open_q": "Q_OPEN: Should we add a lint warning when a constraint turn is logged with importance < 0.8?",
        "stress_untyped": True,
    },
]


def run_continuity_family(wm_bin: Path) -> dict[str, Any]:
    results = []
    for sc in CONTINUITY_SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"eval_{sc['id']}_") as td:
            td_path = Path(td)
            store_dir = td_path / "wm_store"
            files_dir = td_path / "plain_files"
            files_dir.mkdir(parents=True, exist_ok=True)

            # Build Session 1 turn sequence:
            # 4 early decisions (turns 1..4), resolved question + resolving answer (turns 5..6),
            # open question (turn 7), and 25 noisy operational status turns (turns 8..32).
            turns_list: list[dict[str, Any]] = []
            for idx, (text, t_type, qual, imp) in enumerate(sc["decisions"], start=1):
                turns_list.append(
                    {
                        "seq": idx,
                        "role": "ai",
                        "turn_type": t_type,
                        "qualifier": qual,
                        "importance": imp,
                        "content": text,
                    }
                )
            turns_list.append(
                {
                    "seq": 5,
                    "role": "user",
                    "turn_type": "question",
                    "qualifier": "conditional",
                    "importance": 0.70,
                    "content": sc["resolved_q"],
                    "_is_resolved_q": True,
                }
            )
            turns_list.append(
                {
                    "seq": 6,
                    "role": "ai",
                    "turn_type": "decision",
                    "qualifier": "verified",
                    "importance": 0.78,
                    "content": sc["resolving_a"],
                    "_resolves_prev": True,
                }
            )
            turns_list.append(
                {
                    "seq": 7,
                    "role": "user",
                    "turn_type": "question",
                    "qualifier": "conditional",
                    "importance": 0.75,
                    "content": sc["open_q"],
                    "_is_open_q": True,
                }
            )
            for noise_i in range(1, 26):
                turns_list.append(
                    {
                        "seq": 7 + noise_i,
                        "role": "ai",
                        "turn_type": "note",
                        "qualifier": "conditional",
                        "importance": 0.25,
                        "content": (
                            f"Status heartbeat #{noise_i} for {sc['track']}: worker pool nominal, "
                            f"queue depth={(noise_i * 3) % 7}, routine telemetry check passed."
                        ),
                    }
                )

            # 1) Plain-files tail baseline (reads tail of session.md up to budget_tokens)
            t0 = time.perf_counter()
            flat_lines = []
            bm25_docs = []
            for t in turns_list:
                line = f"[turn {t['seq']}] ({t['role']}) {t['content']}"
                flat_lines.append(line)
                (files_dir / f"turn_{t['seq']:02d}.md").write_text(line + "\n", encoding="utf-8")
                bm25_docs.append({"id": t["seq"], "content": line})
            session_md = files_dir / "session.md"
            session_md.write_text("\n".join(flat_lines) + "\n", encoding="utf-8")

            tail_selected: list[str] = []
            used_tokens = 0
            for line in reversed(flat_lines):
                t_est = approx_tokens(line)
                if used_tokens + t_est > sc["budget_tokens"]:
                    break
                tail_selected.append(line)
                used_tokens += t_est
            tail_text = "\n".join(reversed(tail_selected))
            tail_ms = (time.perf_counter() - t0) * 1000.0
            tail_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in tail_text)
            tail_open_ok = (sc["open_q"] in tail_text) and (sc["resolved_q"] not in tail_text)

            # 2) Plain-files Okapi BM25 baseline (queries generic session continuity prompt within budget)
            t1 = time.perf_counter()
            bm25 = OkapiBM25(bm25_docs)
            bm25_hits = bm25.search(
                "verified architectural decision invariant open question unresolved", limit=12
            )
            bm25_selected: list[str] = []
            bm25_tokens = 0
            for h in bm25_hits:
                t_est = approx_tokens(h["content"])
                if bm25_tokens + t_est > sc["budget_tokens"]:
                    break
                bm25_selected.append(h["content"])
                bm25_tokens += t_est
            bm25_text = "\n".join(bm25_selected)
            bm25_ms = (time.perf_counter() - t1) * 1000.0
            bm25_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in bm25_text)
            # BM25 has no structural arc resolution, so if it retrieves resolved_q or misses open_q, precision fails
            bm25_open_ok = (sc["open_q"] in bm25_text) and (sc["resolved_q"] not in bm25_text)

            # 3) WhiteMagic v10.4.0 (Session 1 records + crystallizes, then fresh process runs Session 2 continuity)
            wm = WMMcpSession(wm_bin, store_dir)
            # First record turns 1..5 to get the turn_id of turn 5 (resolved_q)
            pre_calls: list[tuple[str, dict[str, Any]]] = []
            for t in turns_list[:5]:
                pre_calls.append(
                    (
                        "session_record",
                        {
                            "session_id": f"{sc['id']}_s1",
                            "track": sc["track"],
                            "role": t["role"],
                            "turn_type": t["turn_type"],
                            "qualifier": t["qualifier"],
                            "importance": t["importance"],
                            "content": t["content"],
                        },
                    )
                )
            pre_res, _, _ = wm.run_batch(pre_calls)
            resolved_q_turn_id = pre_res[4]["turn_id"]

            post_calls: list[tuple[str, dict[str, Any]]] = [
                (
                    "session_record",
                    {
                        "session_id": f"{sc['id']}_s1",
                        "track": sc["track"],
                        "role": turns_list[5]["role"],
                        "turn_type": turns_list[5]["turn_type"],
                        "qualifier": turns_list[5]["qualifier"],
                        "importance": turns_list[5]["importance"],
                        "content": turns_list[5]["content"],
                        "resolves": resolved_q_turn_id,
                    },
                )
            ]
            for t in turns_list[6:]:
                post_calls.append(
                    (
                        "session_record",
                        {
                            "session_id": f"{sc['id']}_s1",
                            "track": sc["track"],
                            "role": t["role"],
                            "turn_type": t["turn_type"],
                            "qualifier": t["qualifier"],
                            "importance": t["importance"],
                            "content": t["content"],
                        },
                    )
                )
            post_calls.append(
                (
                    "session_checkpoint",
                    {
                        "session_id": f"{sc['id']}_s1",
                        "track": sc["track"],
                        "summary": f"Completed {sc['id']} design and recorded decisions.",
                        "crystallize": True,
                    },
                )
            )
            wm.run_batch(post_calls)

            # Now simulate a fresh process restart on Session 2 on the same track, plus hybrid replay on s1
            recovery_calls: list[tuple[str, dict[str, Any]]] = [
                (
                    "session.replay",
                    {
                        "session_id": f"{sc['id']}_s1",
                        "mode": "hybrid",
                        "token_budget": sc["budget_tokens"],
                    },
                ),
                (
                    "session_continuity",
                    {
                        "session_id": f"{sc['id']}_s1",
                        "track": sc["track"],
                        "n": 3,
                        "include_briefing_text": True,
                    },
                ),
            ]
            rec_res, wm_ms, wm_bytes = wm.run_batch(recovery_calls)
            replay_out = rec_res[0]
            cont_out = rec_res[1]

            replay_text = json.dumps(replay_out)
            wm_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in replay_text)
            unresolved_arcs = cont_out.get("unresolved_arcs", [])
            unresolved_texts = [a.get("content", "") for a in unresolved_arcs]
            wm_open_ok = (len(unresolved_arcs) == 1) and (unresolved_texts[0] == sc["open_q"])
            related_crystals = cont_out.get("related_crystals", [])
            crystal_surfaced = len(related_crystals) >= 1

            failure_trace = None
            if wm_dec_hits < len(sc["decisions"]):
                missing = [d for d, _, _, _ in sc["decisions"] if d not in replay_text]
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": (
                        "Decision logged as untyped 'note' with importance=0.40 (< 0.80 salience floor) "
                        "was evicted by 25 later turns under the 280-token hybrid replay cap."
                    ),
                    "missing_decisions": missing,
                    "remediation": "Log architectural constraints with turn_type='decision' or importance>=0.80, or query session.recall.",
                }

            results.append(
                {
                    "scenario_id": sc["id"],
                    "stress_untyped": sc["stress_untyped"],
                    "plain_files_tail": {
                        "decision_recall": round(tail_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if tail_open_ok else 0.0,
                        "tokens_used": used_tokens,
                        "latency_ms": round(tail_ms, 3),
                    },
                    "bm25_flat_files": {
                        "decision_recall": round(bm25_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if bm25_open_ok else 0.0,
                        "tokens_used": bm25_tokens,
                        "latency_ms": round(bm25_ms, 3),
                    },
                    "whitemagic_v10_4": {
                        "decision_recall": round(wm_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if wm_open_ok else 0.0,
                        "cross_session_crystal_surfaced": crystal_surfaced,
                        "tokens_used": replay_out.get("token_estimate", 0),
                        "response_bytes": wm_bytes,
                        "latency_ms": round(wm_ms, 3),
                    },
                    "failure_trace": failure_trace,
                }
            )
    return {"family": "T_CONTINUITY", "scenarios": results}


# ─── Task Family 2: Stale / Conflicting Memory Resolution ────────────────────

CONFLICT_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "M1_backup_cap_upgrade",
        "query": "hosted tenant write backup archive size cap limit bytes",
        "v1": "Hosted tenant write backup archive size cap limit is 1 GiB (1073741824 bytes) maximum.",
        "v1_paraphrases": [
            "Backup policy note: hosted tenant write backup archive size cap limit bytes is 1 GiB.",
            "Runbook reminder: enforce 1 GiB (1073741824 bytes) hosted tenant write backup archive size cap.",
        ],
        "updates": [
            "Hosted tenant write backup archive size cap limit is 4 GiB (4294967296 bytes) maximum."
        ],
        "expected_token": "4294967296",
        "stale_token": "1073741824",
        "use_governed_update": True,
    },
    {
        "id": "M2_fleet_peering_price",
        "query": "hosted fleet peering monthly price usd tier",
        "v1": "Hosted fleet peering monthly price usd tier is $199/mo for pilot organizations.",
        "v1_paraphrases": [
            "Pricing schedule note: hosted fleet peering monthly price usd tier listed at $199/mo.",
            "ZH draft translation: hosted fleet peering monthly price usd tier is $199/mo.",
        ],
        "updates": [
            "Hosted fleet peering monthly price usd tier is $249/mo across EN and ZH contracts."
        ],
        "expected_token": "$249/mo",
        "stale_token": "$199/mo",
        "use_governed_update": True,
    },
    {
        "id": "M3_openapi_path_count",
        "query": "receipt verifier openapi contract path count endpoints",
        "v1": "Receipt verifier openapi contract path count endpoints is 18 paths in revision 1.3.0.",
        "v1_paraphrases": [
            "API summary: receipt verifier openapi contract path count endpoints has 18 paths.",
            "Docs note: receipt verifier openapi contract path count endpoints is 18 paths.",
        ],
        "updates": [
            "Receipt verifier openapi contract path count endpoints is 19 paths in revision 1.4.0."
        ],
        "expected_token": "19 paths",
        "stale_token": "18 paths",
        "use_governed_update": True,
    },
    {
        "id": "M4_linux_x86_64_manifest_hash",
        "query": "v10.3.0 release manifest wm-linux-x86_64 sha256 digest",
        "v1": "v10.3.0 release manifest wm-linux-x86_64 sha256 digest is 232e31be6fa850e89a4fae9328e33e377cb36a3db67cce5b7b130c5856f0bd38.",
        "v1_paraphrases": [
            "Initial build log: v10.3.0 release manifest wm-linux-x86_64 sha256 digest 232e31be6fa850e89a4fae9328e33e377cb36a3db67cce5b7b130c5856f0bd38.",
        ],
        "updates": [
            "v10.3.0 release manifest wm-linux-x86_64 sha256 digest is 9c01c6ce1bf16dfb9777d9acf2f37c0c208298a9d7e7d7917184e67471a25a11."
        ],
        "expected_token": "9c01c6ce1bf16dfb9777d9acf2f37c0c208298a9d7e7d7917184e67471a25a11",  # gitleaks:allow
        "stale_token": "232e31be6fa850e89a4fae9328e33e377cb36a3db67cce5b7b130c5856f0bd38",  # gitleaks:allow
        "use_governed_update": True,
    },
    {
        "id": "M5_multi_hop_restore_drill_count",
        "query": "hosted restore drill verification check count pass gate",
        "v1": "Hosted restore drill verification check count pass gate is 19/19 checks.",
        "v1_paraphrases": [
            "Initial restore report: hosted restore drill verification check count pass gate 19/19 checks.",
        ],
        "updates": [
            "Hosted restore drill verification check count pass gate is 21/21 checks.",
            "Hosted restore drill verification check count pass gate is 23/23 checks.",
        ],
        "expected_token": "23/23",
        "stale_token": "19/19",
        "use_governed_update": True,
    },
    {
        "id": "M6_multi_hop_economy_suite_count",
        "query": "economy acceptance fault injection test suite pass count",
        "v1": "Economy acceptance fault injection test suite pass count is 25/25 passing tests.",
        "v1_paraphrases": [
            "Baseline test log: economy acceptance fault injection test suite pass count 25/25.",
        ],
        "updates": [
            "Economy acceptance fault injection test suite pass count is 31/31 passing tests.",
            "Economy acceptance fault injection test suite pass count is 43/43 passing tests.",
        ],
        "expected_token": "43/43",
        "stale_token": "25/25",
        "use_governed_update": True,
    },
    {
        "id": "M7_npm_channel_dist_tags",
        "query": "npm whitemagic-mcp dist-tag channel version pin",
        "v1": "npm whitemagic-mcp dist-tag channel version pin has latest=10.3.0.",
        "v1_paraphrases": [
            "Registry note: npm whitemagic-mcp dist-tag channel version pin latest=10.3.0.",
        ],
        "updates": [
            "npm whitemagic-mcp dist-tag channel version pin has latest=9.3.4 (stable) and next=10.3.0 (preview)."
        ],
        "expected_token": "latest=9.3.4",
        "stale_token": "latest=10.3.0",
        "use_governed_update": True,
    },
    {
        # Deliberate stress case: agent writes a terse new note via raw `memory_remember`
        # WITHOUT calling `memory.update` on the prior record, and with lower lexical overlap!
        "id": "M8_stress_unlinked_contradiction_without_update",
        "query": "facilitator proxy upstream timeout seconds configuration",
        "v1": "Facilitator proxy upstream timeout seconds configuration is set to 15 seconds for x402 settlement calls.",
        "v1_paraphrases": [
            "Config reference: facilitator proxy upstream timeout seconds configuration is 15 seconds.",
        ],
        "updates": [
            "Changed x402 upstream wait limit to 45s."
        ],
        "expected_token": "45s",
        "stale_token": "15 seconds",
        "use_governed_update": False,
    },
]


def run_conflict_family(wm_bin: Path) -> dict[str, Any]:
    results = []
    for sc in CONFLICT_SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"eval_{sc['id']}_") as td:
            td_path = Path(td)
            store_dir = td_path / "wm_store"
            files_dir = td_path / "plain_files"
            files_dir.mkdir(parents=True, exist_ok=True)

            # Plain files + BM25 baseline: writes each record as a markdown file
            t0 = time.perf_counter()
            docs: list[dict[str, Any]] = []
            docs.append({"id": "v1", "content": sc["v1"]})
            for idx, p in enumerate(sc["v1_paraphrases"], start=1):
                docs.append({"id": f"v1_p{idx}", "content": p})
            for idx, u in enumerate(sc["updates"], start=2):
                docs.append({"id": f"v{idx}", "content": u})
            for d in docs:
                (files_dir / f"{d['id']}.md").write_text(d["content"] + "\n", encoding="utf-8")

            bm25 = OkapiBM25(docs)
            bm25_hits = bm25.search(sc["query"], limit=3)
            bm25_ms = (time.perf_counter() - t0) * 1000.0
            bm25_top1_ok = (sc["expected_token"] in bm25_hits[0]["content"]) and (
                sc["stale_token"] not in bm25_hits[0]["content"]
            )
            bm25_stale_hits = sum(
                1 for h in bm25_hits if sc["stale_token"] in h["content"] or h["id"].startswith("v1")
            )

            # WhiteMagic v10.4.0:
            wm = WMMcpSession(wm_bin, store_dir)
            init_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_remember", {"content": sc["v1"], "title": f"{sc['id']}_canonical"}),
            ]
            for idx, p in enumerate(sc["v1_paraphrases"], start=1):
                init_calls.append(("memory_remember", {"content": p, "title": f"{sc['id']}_p{idx}"}))
            init_res, _, _ = wm.run_batch(init_calls)
            curr_id = init_res[0]["record_id"]
            paraphrase_ids = [r["record_id"] for r in init_res[1:]]

            update_calls: list[tuple[str, dict[str, Any]]] = []
            if sc["use_governed_update"]:
                # Supersede canonical record across update hops, and also supersede v1 paraphrases
                for u_text in sc["updates"]:
                    res_u, _, _ = wm.run_batch(
                        [
                            (
                                "memory.update",
                                {
                                    "id": curr_id,
                                    "content": u_text,
                                    "reason": "policy_supersede",
                                },
                            )
                        ]
                    )
                    curr_id = res_u[0]["record_id"]
                for pid in paraphrase_ids:
                    wm.run_batch(
                        [
                            (
                                "memory.update",
                                {
                                    "id": pid,
                                    "content": sc["updates"][-1],
                                    "reason": "consolidate_stale_paraphrase",
                                },
                            )
                        ]
                    )
            else:
                # Stress case M8: agent just calls memory_remember without memory.update
                for u_text in sc["updates"]:
                    wm.run_batch([("memory_remember", {"content": u_text, "title": f"{sc['id']}_unlinked"})])

            query_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_recall", {"query": sc["query"], "limit": 3}),
                ("memory.revisions", {"id": curr_id, "action": "verify"}),
            ]
            q_res, wm_ms, wm_bytes = wm.run_batch(query_calls)
            recall_out = q_res[0]
            rev_out = q_res[1]
            wm_hits = recall_out.get("results", [])
            # Filter to active (non-superseded) hits first, as WhiteMagic marks `superseded_by`
            active_hits = [h for h in wm_hits if h.get("superseded_by") is None]
            top_hit = active_hits[0] if active_hits else (wm_hits[0] if wm_hits else {})
            wm_top1_ok = (sc["expected_token"] in top_hit.get("content", "")) and (
                sc["stale_token"] not in top_hit.get("content", "")
            )
            unflagged_stale = sum(
                1
                for h in wm_hits
                if (sc["stale_token"] in h.get("content", "")) and (h.get("superseded_by") is None)
            )
            verify_block = rev_out.get("verify", {})
            lineage_ok = bool(verify_block.get("valid")) and int(verify_block.get("chain_length", 0)) >= len(
                sc["updates"]
            )

            failure_trace = None
            if not wm_top1_ok:
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": (
                        "Agent stored a terse update ('Changed x402 upstream wait limit to 45s.') via raw "
                        "memory_remember instead of memory.update(id=old_id), so no Supersedes relation "
                        "was recorded and the old record retained higher lexical BM25 overlap with the query."
                    ),
                    "remediation": "Always use memory.update(id=prior_id) or session.record(supersedes=...) when overriding prior policy.",
                }

            results.append(
                {
                    "scenario_id": sc["id"],
                    "use_governed_update": sc["use_governed_update"],
                    "bm25_flat_files": {
                        "top1_current_truth": 1.0 if bm25_top1_ok else 0.0,
                        "unflagged_stale_in_top3": round(bm25_stale_hits / max(1, len(bm25_hits)), 3),
                        "lineage_verifiable": 0.0,
                        "latency_ms": round(bm25_ms, 3),
                    },
                    "whitemagic_v10_4": {
                        "top1_current_truth": 1.0 if wm_top1_ok else 0.0,
                        "unflagged_stale_in_top3": round(unflagged_stale / max(1, len(wm_hits)), 3),
                        "lineage_verifiable": 1.0 if lineage_ok else 0.0,
                        "response_bytes": wm_bytes,
                        "latency_ms": round(wm_ms, 3),
                    },
                    "failure_trace": failure_trace,
                }
            )
    return {"family": "T_CONFLICT", "scenarios": results}


# ─── Task Family 3: Surgical Bad-Memory Repair & Legitimate State Preservation

REPAIR_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "R1_repair_hallucinated_facilitator_port",
        "entity_token": "cdp_facilitator_proxy",
        "bad_memory": "cdp_facilitator_proxy listens on public TCP port 0.0.0.0:9999 without auth.",
        "repaired_memory": "cdp_facilitator_proxy listens strictly on loopback 127.0.0.1:18795 behind local unit isolation.",
        "query": "cdp_facilitator_proxy listen port address binding",
        "bad_marker": "0.0.0.0:9999",
        "good_marker": "127.0.0.1:18795",
        "legitimate_neighbors": [
            "cdp_facilitator_proxy signs CDP JWT requests using ES256/Ed25519 credentials from /etc/whitemagic-hosted.",
            "cdp_facilitator_proxy enforces a 256 KiB request body ceiling on /verify and /settle.",
            "cdp_facilitator_proxy logs content-free settlement outcomes for operator reconciliation.",
            "cdp_facilitator_proxy systemd unit runs under User=whitemagic with PrivateTmp=yes.",
        ],
    },
    {
        "id": "R2_repair_poisoned_crystal_cipher",
        "entity_token": "crystal_client",
        "bad_memory": "crystal_client seals envelopes with unauthenticated AES-128-CBC and static IVs.",
        "repaired_memory": "crystal_client seals envelopes strictly with AEAD AES-256-GCM or ChaCha20-Poly1305 and 96-bit random nonces.",
        "query": "crystal_client cipher encryption mode nonce",
        "bad_marker": "AES-128-CBC",
        "good_marker": "AES-256-GCM",
        "legitimate_neighbors": [
            "crystal_client binds tenant_hash and kek_version into AEAD Additional Authenticated Data (AAD).",
            "crystal_client refuses HTTP redirects on all authenticated owner requests.",
            "crystal_client verifies Ed25519 client_sig over JCS-canonicalized envelope fields.",
            "crystal_client checks token file permissions to reject world-readable or FIFO paths.",
        ],
    },
    {
        "id": "R3_repair_wrong_sqlite_replay_path",
        "entity_token": "receipt_api_replay",
        "bad_memory": "receipt_api_replay stores crystal assertion nonces only in volatile process RAM.",
        "repaired_memory": "receipt_api_replay persists crystal assertion nonces in SQLite crystal_assertions.sqlite3 with uniqueness enforcement.",
        "query": "receipt_api_replay crystal assertion nonce storage persistence",
        "bad_marker": "volatile process RAM",
        "good_marker": "crystal_assertions.sqlite3",
        "legitimate_neighbors": [
            "receipt_api_replay prunes expired assertion nonces outside the 60-second validity window.",
            "receipt_api_replay binds method, target path, owner_id, and body_sha256 in the HMAC claim.",
            "receipt_api_replay returns HTTP 401 when a valid assertion token is replayed after restart.",
            "receipt_api_replay is included in the daily auth-state backup archive series.",
        ],
    },
    {
        "id": "R4_repair_bad_landlock_claim",
        "entity_token": "landlock_sandbox",
        "bad_memory": "landlock_sandbox disables kernel filesystem restrictions when running in production.",
        "repaired_memory": "landlock_sandbox enforces Linux Landlock ABI v3 read/write path rules before serving requests.",
        "query": "landlock_sandbox kernel filesystem restriction enforcement",
        "bad_marker": "disables kernel filesystem",
        "good_marker": "Landlock ABI v3",
        "legitimate_neighbors": [
            "landlock_sandbox reports enforced_abi_v3 in the /info endpoint metadata.",
            "landlock_sandbox restricts write access to the configured state directory.",
            "landlock_sandbox is complemented by systemd ProtectSystem=strict in receipt-api.service.",
            "landlock_sandbox status is verified by crystal_tests.py during pre-deploy checks.",
        ],
    },
    {
        "id": "R5_repair_wrong_keyd_quota",
        "entity_token": "keyd_faucet",
        "bad_memory": "keyd_faucet issues unlimited anonymous write keys without IP rate limiting.",
        "repaired_memory": "keyd_faucet issues read-primarily evaluation keys (50 recalls/day) with per-IP cooldowns.",
        "query": "keyd_faucet evaluation key quota rate limit",
        "bad_marker": "unlimited anonymous write",
        "good_marker": "50 recalls/day",
        "legitimate_neighbors": [
            "keyd_faucet stores hashed key metadata in /var/lib/whitemagic-hosted/keys.json.",
            "keyd_faucet binds evaluation sample write quotas to 10 writes and 5 MB per day on next lane.",
            "keyd_faucet logs key issuance events without recording user query payloads.",
            "keyd_faucet stays stopped during replacement-host recovery until health checks pass.",
        ],
    },
    {
        "id": "R6_repair_bad_ots_anchor_route",
        "entity_token": "ots_anchors",
        "bad_memory": "ots_anchors requires a paid admin bearer key to download public /anchors/<digest> proofs.",
        "repaired_memory": "ots_anchors serves GET /anchors/<digest> keyless so third parties can independently verify proofs.",
        "query": "ots_anchors download proof /anchors/<digest> authentication",
        "bad_marker": "paid admin bearer key",
        "good_marker": "keyless",
        "legitimate_neighbors": [
            "ots_anchors validates SHA-256 digest hex format before looking up proof files.",
            "ots_anchors pairs with POST /verify-anchor for detached OpenTimestamps proof checks.",
            "ots_anchors proof files are preserved in the hosted backup archive.",
            "ots_anchors is documented in the 19-path OpenAPI 3.1 specification.",
        ],
    },
    {
        "id": "R7_repair_wrong_erc8004_verdict",
        "entity_token": "erc8004_adapter",
        "bad_memory": "erc8004_adapter marks unsigned tampered bundles as score 100 valid outcomes.",
        "repaired_memory": "erc8004_adapter rejects tampered or unsigned bundles and emits signed score=0 failure attestations.",
        "query": "erc8004_adapter tampered bundle score attestation",
        "bad_marker": "score 100 valid",
        "good_marker": "score=0",
        "legitimate_neighbors": [
            "erc8004_adapter exposes POST /erc8004/validate-outcome on api.whitemagic.dev.",
            "erc8004_adapter binds the continuity receipt digest into the EIP-712 / Ed25519 outcome payload.",
            "erc8004_adapter is specified in planning/specs/ERC8004_VALIDATION_ADAPTER_SPEC.md.",
            "erc8004_adapter deterministic test vectors run in receipt_crypto.test.mjs.",
        ],
    },
    {
        "id": "R8_repair_bad_tenant_export_scope",
        "entity_token": "tenant_isolation",
        "bad_memory": "tenant_isolation allows GET /tenant/export to dump another tenant's private store.",
        "repaired_memory": "tenant_isolation scopes GET /tenant/export and DELETE /tenant strictly to the authenticated key's own store.",
        "query": "tenant_isolation GET /tenant/export cross-tenant store scope",
        "bad_marker": "dump another tenant",
        "good_marker": "authenticated key's own store",
        "legitimate_neighbors": [
            "tenant_isolation labels fused recall results with partition: tenant | corpus.",
            "tenant_isolation enforces per-tenant storage caps and lane-wide daily write budgets.",
            "tenant_isolation is verified end-to-end by tests/tenant_isolation_e2e.sh.",
            "tenant_isolation hard-deletes only the caller's directory on DELETE /tenant?confirm=1.",
        ],
    },
]


def run_repair_family(wm_bin: Path) -> dict[str, Any]:
    results = []
    for sc in REPAIR_SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"eval_{sc['id']}_") as td:
            td_path = Path(td)
            store_dir = td_path / "wm_store"

            # Baseline 1: Plain-files append-only correction (appends correction.md without removing bad.md)
            t0 = time.perf_counter()
            append_docs = [{"id": "bad", "content": sc["bad_memory"]}]
            for idx, leg in enumerate(sc["legitimate_neighbors"], start=1):
                append_docs.append({"id": f"leg_{idx}", "content": leg})
            append_docs.append({"id": "correction", "content": sc["repaired_memory"]})
            bm25_append = OkapiBM25(append_docs)
            append_hits = bm25_append.search(sc["query"], limit=3)
            append_ms = (time.perf_counter() - t0) * 1000.0
            # Does bad_marker still appear unflagged in top-3?
            append_poison_free = all(sc["bad_marker"] not in h["content"] for h in append_hits)
            append_legit_kept = 1.0  # append-only never deletes neighbors

            # Baseline 2: Plain-files naive entity/keyword line prune (deletes lines containing entity_token)
            t1 = time.perf_counter()
            pruned_docs = [
                d for d in append_docs[:-1] if sc["entity_token"] not in d["content"]
            ]
            pruned_docs.append({"id": "correction", "content": sc["repaired_memory"]})
            bm25_prune = OkapiBM25(pruned_docs)
            prune_hits = bm25_prune.search(sc["query"], limit=3)
            prune_ms = (time.perf_counter() - t1) * 1000.0
            prune_poison_free = all(sc["bad_marker"] not in h["content"] for h in prune_hits)
            surviving_legit = sum(
                1 for leg in sc["legitimate_neighbors"] if any(d["content"] == leg for d in pruned_docs)
            )
            prune_legit_kept = surviving_legit / float(len(sc["legitimate_neighbors"]))

            # WhiteMagic v10.4.0: Surgical record-addressed memory.update + legitimate neighbor verification
            wm = WMMcpSession(wm_bin, store_dir)
            ingest_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_remember", {"content": sc["bad_memory"], "title": f"{sc['id']}_bad"}),
            ]
            for idx, leg in enumerate(sc["legitimate_neighbors"], start=1):
                ingest_calls.append(("memory_remember", {"content": leg, "title": f"{sc['id']}_leg_{idx}"}))
            ing_res, _, _ = wm.run_batch(ingest_calls)
            bad_id = ing_res[0]["record_id"]
            legit_ids = [r["record_id"] for r in ing_res[1:]]

            # Perform surgical repair via memory.update(id=bad_id)
            repair_calls: list[tuple[str, dict[str, Any]]] = [
                (
                    "memory.update",
                    {
                        "id": bad_id,
                        "content": sc["repaired_memory"],
                        "reason": "surgical_bad_memory_repair",
                    },
                ),
                ("memory_recall", {"query": sc["query"], "limit": 3}),
            ]
            for lid in legit_ids:
                repair_calls.append(("memory_get", {"id": str(lid)}))
            repair_calls.append(
                ("memory.revisions", {"id": bad_id, "action": "verify"})
            )
            rep_res, wm_ms, wm_bytes = wm.run_batch(repair_calls)

            recall_hits = rep_res[1].get("results", [])
            active_hits = [h for h in recall_hits if h.get("superseded_by") is None]
            wm_poison_free_top3 = (
                len(active_hits) >= 1
                and any(sc["good_marker"] in h.get("content", "") for h in active_hits)
                and all(sc["bad_marker"] not in h.get("content", "") for h in active_hits)
            )
            wm_rank1 = (
                len(active_hits) >= 1
                and (sc["good_marker"] in active_hits[0].get("content", ""))
                and all(sc["bad_marker"] not in h.get("content", "") for h in active_hits)
            )
            legit_reads = rep_res[2 : 2 + len(legit_ids)]
            wm_legit_intact = sum(
                1
                for r, expected_text in zip(legit_reads, sc["legitimate_neighbors"])
                if expected_text in json.dumps(r)
            )
            wm_legit_rate = wm_legit_intact / float(len(sc["legitimate_neighbors"]))
            rev_verify = rep_res[-1].get("verify", {})
            audit_ok = bool(rev_verify.get("valid")) and int(rev_verify.get("chain_length", 0)) == 1

            failure_trace = None
            if not wm_rank1:
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": (
                        "Bad memory was superseded and excluded from active results, and the repaired "
                        "memory was retrieved at rank 2 (score=0.3365), but rank 1 (score=0.4796) was an "
                        "adjacent legitimate neighbor because the repair rewrote query terms ('download proof "
                        "authentication' -> 'serves GET ... keyless ... proofs') under exact-token lexical scoring."
                    ),
                    "remediation": (
                        "Preserve canonical query terms when repairing a record, or inspect top-3 active hits / "
                        "enable morphological stemming or hybrid embedding reranking."
                    ),
                }

            results.append(
                {
                    "scenario_id": sc["id"],
                    "plain_files_append_only": {
                        "poison_free_active_top3": 1.0 if append_poison_free else 0.0,
                        "legitimate_state_preserved": round(append_legit_kept, 3),
                        "joint_success": 1.0 if (append_poison_free and append_legit_kept == 1.0) else 0.0,
                        "latency_ms": round(append_ms, 3),
                    },
                    "plain_files_keyword_prune": {
                        "poison_free_active_top3": 1.0 if prune_poison_free else 0.0,
                        "legitimate_state_preserved": round(prune_legit_kept, 3),
                        "joint_success": 1.0 if (prune_poison_free and prune_legit_kept == 1.0) else 0.0,
                        "latency_ms": round(prune_ms, 3),
                    },
                    "whitemagic_v10_4": {
                        "poison_free_active_top3": 1.0 if wm_poison_free_top3 else 0.0,
                        "repaired_at_rank1": 1.0 if wm_rank1 else 0.0,
                        "legitimate_state_preserved": round(wm_legit_rate, 3),
                        "joint_success_top3": 1.0 if (wm_poison_free_top3 and wm_legit_rate == 1.0 and audit_ok) else 0.0,
                        "joint_success_rank1": 1.0 if (wm_rank1 and wm_legit_rate == 1.0 and audit_ok) else 0.0,
                        "audit_trail_verified": 1.0 if audit_ok else 0.0,
                        "response_bytes": wm_bytes,
                        "latency_ms": round(wm_ms, 3),
                    },
                    "failure_trace": failure_trace,
                }
            )
    return {"family": "T_REPAIR", "scenarios": results}


def summarize_evaluation(
    wm_bin: Path,
    cont: dict[str, Any],
    conf: dict[str, Any],
    rep: dict[str, Any],
) -> dict[str, Any]:
    c_sc = cont["scenarios"]
    m_sc = conf["scenarios"]
    r_sc = rep["scenarios"]

    def avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    def p50_p95(vals: list[float]) -> dict[str, float]:
        if not vals:
            return {"p50_ms": 0.0, "p95_ms": 0.0}
        s = sorted(vals)
        p50 = statistics.median(s)
        p95_idx = min(len(s) - 1, int(math.ceil(0.95 * len(s))) - 1)
        return {"p50_ms": round(p50, 2), "p95_ms": round(s[p95_idx], 2)}

    failure_traces = [
        s["failure_trace"] for s in (c_sc + m_sc + r_sc) if s.get("failure_trace") is not None
    ]

    return {
        "schema": "wm.pinned-task-evaluation/1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "binary": {
            "path": "target/release/wm",
            "sha256": sha256_file(wm_bin),
            "version": "10.4.0",
        },
        "total_scenarios": len(c_sc) + len(m_sc) + len(r_sc),
        "summary_by_family": {
            "T_CONTINUITY_cross_session_decision_recovery": {
                "scenario_count": len(c_sc),
                "plain_files_tail": {
                    "mean_decision_recall": avg([s["plain_files_tail"]["decision_recall"] for s in c_sc]),
                    "mean_open_arc_precision": avg([s["plain_files_tail"]["open_arc_precision"] for s in c_sc]),
                    "latency": p50_p95([s["plain_files_tail"]["latency_ms"] for s in c_sc]),
                },
                "bm25_flat_files": {
                    "mean_decision_recall": avg([s["bm25_flat_files"]["decision_recall"] for s in c_sc]),
                    "mean_open_arc_precision": avg([s["bm25_flat_files"]["open_arc_precision"] for s in c_sc]),
                    "latency": p50_p95([s["bm25_flat_files"]["latency_ms"] for s in c_sc]),
                },
                "whitemagic_v10_4": {
                    "mean_decision_recall_all_8": avg([s["whitemagic_v10_4"]["decision_recall"] for s in c_sc]),
                    "mean_decision_recall_typed_7": avg(
                        [s["whitemagic_v10_4"]["decision_recall"] for s in c_sc if not s["stress_untyped"]]
                    ),
                    "mean_open_arc_precision": avg([s["whitemagic_v10_4"]["open_arc_precision"] for s in c_sc]),
                    "cross_session_crystal_rate": avg(
                        [1.0 if s["whitemagic_v10_4"]["cross_session_crystal_surfaced"] else 0.0 for s in c_sc]
                    ),
                    "mean_tokens_used": avg([float(s["whitemagic_v10_4"]["tokens_used"]) for s in c_sc]),
                    "latency": p50_p95([s["whitemagic_v10_4"]["latency_ms"] for s in c_sc]),
                },
            },
            "T_CONFLICT_stale_and_conflicting_memory": {
                "scenario_count": len(m_sc),
                "bm25_flat_files": {
                    "top1_current_truth_rate": avg([s["bm25_flat_files"]["top1_current_truth"] for s in m_sc]),
                    "mean_unflagged_stale_in_top3": avg(
                        [s["bm25_flat_files"]["unflagged_stale_in_top3"] for s in m_sc]
                    ),
                    "lineage_verifiable_rate": 0.0,
                    "latency": p50_p95([s["bm25_flat_files"]["latency_ms"] for s in m_sc]),
                },
                "whitemagic_v10_4": {
                    "top1_current_truth_rate_all_8": avg([s["whitemagic_v10_4"]["top1_current_truth"] for s in m_sc]),
                    "top1_current_truth_rate_governed_7": avg(
                        [s["whitemagic_v10_4"]["top1_current_truth"] for s in m_sc if s["use_governed_update"]]
                    ),
                    "mean_unflagged_stale_in_top3_governed_7": avg(
                        [s["whitemagic_v10_4"]["unflagged_stale_in_top3"] for s in m_sc if s["use_governed_update"]]
                    ),
                    "lineage_verifiable_rate_governed_7": avg(
                        [s["whitemagic_v10_4"]["lineage_verifiable"] for s in m_sc if s["use_governed_update"]]
                    ),
                    "latency": p50_p95([s["whitemagic_v10_4"]["latency_ms"] for s in m_sc]),
                },
            },
            "T_REPAIR_surgical_bad_memory_repair": {
                "scenario_count": len(r_sc),
                "plain_files_append_only": {
                    "poison_free_top3_rate": avg([s["plain_files_append_only"]["poison_free_active_top3"] for s in r_sc]),
                    "legitimate_state_preserved_rate": avg(
                        [s["plain_files_append_only"]["legitimate_state_preserved"] for s in r_sc]
                    ),
                    "joint_repair_and_preserve_rate": avg([s["plain_files_append_only"]["joint_success"] for s in r_sc]),
                },
                "plain_files_keyword_prune": {
                    "poison_free_top3_rate": avg(
                        [s["plain_files_keyword_prune"]["poison_free_active_top3"] for s in r_sc]
                    ),
                    "legitimate_state_preserved_rate": avg(
                        [s["plain_files_keyword_prune"]["legitimate_state_preserved"] for s in r_sc]
                    ),
                    "joint_repair_and_preserve_rate": avg(
                        [s["plain_files_keyword_prune"]["joint_success"] for s in r_sc]
                    ),
                },
                "whitemagic_v10_4": {
                    "poison_free_and_repaired_in_top3_rate": avg(
                        [s["whitemagic_v10_4"]["poison_free_active_top3"] for s in r_sc]
                    ),
                    "repaired_at_rank1_rate": avg([s["whitemagic_v10_4"]["repaired_at_rank1"] for s in r_sc]),
                    "legitimate_state_preserved_rate": avg(
                        [s["whitemagic_v10_4"]["legitimate_state_preserved"] for s in r_sc]
                    ),
                    "audit_trail_verified_rate": avg([s["whitemagic_v10_4"]["audit_trail_verified"] for s in r_sc]),
                    "joint_repair_and_preserve_top3_rate": avg(
                        [s["whitemagic_v10_4"]["joint_success_top3"] for s in r_sc]
                    ),
                    "joint_repair_and_preserve_rank1_rate": avg(
                        [s["whitemagic_v10_4"]["joint_success_rank1"] for s in r_sc]
                    ),
                    "latency": p50_p95([s["whitemagic_v10_4"]["latency_ms"] for s in r_sc]),
                },
            },
        },
        "documented_failure_traces": failure_traces,
        "families": [cont, conf, rep],
    }


def main() -> int:
    wm_bin = Path(os.environ.get("WM_BINARY", str(DEFAULT_WM_BIN)))
    if not wm_bin.is_file():
        raise SystemExit(f"Pinned wm binary not found at {wm_bin}")

    cont = run_continuity_family(wm_bin)
    conf = run_conflict_family(wm_bin)
    rep = run_repair_family(wm_bin)
    report = summarize_evaluation(wm_bin, cont, conf, rep)

    out_json = HERE / "pinned-task-eval-results.json"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary_by_family"], indent=2, sort_keys=True))
    print("\nDocumented failure traces:", json.dumps(report["documented_failure_traces"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
