#!/usr/bin/env python3
"""Pinned deterministic memory regression evaluation with equal-information baselines.

Evaluates four core agent-memory task families across 32 deterministic scenarios:
  1. T_CONTINUITY (8 scenarios): Cross-session decision recovery & open-arc precision
     across genuine new sessions with an intervening unrelated-track session, under a
     a 1120-byte compact agent-context cap (280 estimated tokens at bytes/4).
  2. T_CONFLICT (8 scenarios): Stale/conflicting memory resolution (1-hop and 2-hop updates
     plus paraphrase consolidation into a converging revision DAG), scored by version identity.
  3. T_REPAIR (8 scenarios): Surgical bad-memory repair and legitimate neighbor preservation.
  4. T_DISCOVERY (8 authored cases): Cue-guided deterministic migration. Both adapters
     receive exact stale phrases and authoritative replacement text, without target IDs.
     These are regression cases, not an unseen autonomous-agent holdout.

Compares WhiteMagic v10.4.0 against both:
  - Unstructured baselines (`plain_files_tail`, `bm25_flat_files`, `plain_files_append_only`, `plain_files_keyword_prune`)
  - Equal-information structured file baselines (`structured_metadata_files`, `structured_supersedes_files`, `record_addressed_files`)
    that receive the exact same metadata, supersession links, or target IDs.
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

HERE = Path(__file__).resolve().parent
DEFAULT_WM_BIN = HERE.parent / "bin" / "wm"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def approx_tokens(text: str) -> int:
    # Explicit heuristic; this is not a model tokenizer or a transport-size cap.
    return (len(text.encode("utf-8")) + 3) // 4


def architectural_directive(text: str) -> bool:
    """The same authored content heuristic as TurnRecord, not an authority check."""
    text = text.strip()
    lower = text.lower()
    prefix = len(text) >= 3 and text[0] in "Dd" and text[1] in "0123456789" and text[2] in ":. "
    return (prefix or lower.startswith(("invariant:", "policy:", "rule:"))
            or any(cue in lower for cue in ("busy_timeout", "must remain", "never allow"))
            or ("keep " in lower and (" at " in lower or " to " in lower)))


def structured_salient(row: dict[str, Any]) -> bool:
    return (row.get("qualifier") not in ("speculative", "hypothesis")
            and (row["importance"] >= .80
                 or row["turn_type"] in ("decision", "milestone", "constraint", "confirm")
                 or architectural_directive(row["content"])))


CALL_AUDIT: list[dict[str, Any]] = []
BATCH_AUDIT: list[dict[str, Any]] = []


def strict_json_loads(text: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"Duplicate JSON object member {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise RuntimeError(f"Non-finite JSON constant {value}")

    return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)


def assert_mcp_ok(resp: dict[str, Any], context: str) -> None:
    if not isinstance(resp, dict) or "_error" in resp or "_raw" in resp:
        raise RuntimeError(f"Malformed or failed MCP reply in {context}: {resp!r}")
    if resp.get("status") not in ("success", "ok"):
        raise RuntimeError(f"MCP reply lacks explicit success in {context}: {resp!r}")


def valid_lifecycle(record: dict[str, Any]) -> bool:
    return "superseded_by" in record and (record["superseded_by"] is None or
        (type(record["superseded_by"]) is int and record["superseded_by"] >= 0))


def assert_tool_shape(name: str, resp: dict[str, Any], args: dict[str, Any] | None = None) -> None:
    assert_mcp_ok(resp, name)
    if name in ("memory_remember", "memory.update"):
        if type(resp.get("record_id")) is not int or resp["record_id"] < 0:
            raise RuntimeError(f"Missing integer record identity for {name}")
    elif name == "memory_recall":
        if not isinstance(resp.get("results"), list):
            raise RuntimeError("Recall lacks results array")
        for hit in resp["results"]:
            if not isinstance(hit, dict) or type(hit.get("record_id")) is not int or hit["record_id"] < 0 or not isinstance(hit.get("content"), str) or not valid_lifecycle(hit):
                raise RuntimeError("Recall lacks authoritative identity/content/lifecycle metadata")
    elif name == "memory_get":
        record = resp.get("record")
        if not isinstance(record, dict) or type(record.get("record_id")) is not int or record["record_id"] < 0 or not isinstance(record.get("content"), str) or not valid_lifecycle(record):
            raise RuntimeError("Read lacks explicit authoritative lifecycle metadata")
        if args is not None and str(record["record_id"]) != str(args.get("id")):
            raise RuntimeError("Read returned a different record from the requested identity")
    elif name == "memory.revisions":
        check = resp.get("verify")
        if not isinstance(check, dict) or type(check.get("valid")) is not bool or type(check.get("head_record_id")) is not int:
            raise RuntimeError("Revision verification lacks explicit validity/head")
    elif name == "session_record":
        if not isinstance(resp.get("turn_id"), str):
            raise RuntimeError("Session record lacks turn identity")
    elif name == "session_checkpoint":
        if type(resp.get("checkpoint_record_id")) is not int:
            raise RuntimeError("Checkpoint lacks record identity")
    elif name == "session_continuity":
        validate_agent_context(resp)


def validate_agent_context(resp: dict[str, Any]) -> tuple[dict[str, Any], str]:
    context = resp.get("agent_context")
    if not isinstance(context, dict) or not isinstance(context.get("text"), str):
        raise RuntimeError("Continuity lacks the compact agent_context contract")
    text = context["text"]
    size = len(text.encode("utf-8"))
    cap = context.get("byte_cap")
    if type(cap) is not int or cap < 0 or size > cap or context.get("bytes_used") != size or context.get("estimated_tokens") != approx_tokens(text):
        raise RuntimeError("Compact context byte accounting or cap is invalid")
    if context.get("estimate_method") != "utf8_bytes_div_4_heuristic":
        raise RuntimeError("Compact context estimator is not explicitly disclosed")
    value = strict_json_loads(text) if text else {}
    if not isinstance(value, dict):
        raise RuntimeError("Compact context must contain a JSON object")
    if set(value) - {"turns", "checkpoint", "queue", "flags", "crystals", "briefing"}:
        raise RuntimeError("Compact context contains unsupported fields")
    turns = value.get("turns", [])
    if not isinstance(turns, list):
        raise RuntimeError("Compact turns must be an array")
    for turn in turns:
        if not isinstance(turn, dict) or set(turn) != {"kind", "text"} or turn["kind"] not in ("arc", "decision", "salient", "recent") or not isinstance(turn["text"], str):
            raise RuntimeError("Unsupported compact turn kind or shape")
    for key in ("queue", "flags"):
        if key in value and (not isinstance(value[key], list) or any(not isinstance(item, str) for item in value[key])):
            raise RuntimeError(f"Compact {key} must contain strings")
    if value.get("checkpoint") is not None and not isinstance(value["checkpoint"], dict):
        raise RuntimeError("Compact checkpoint must be an object or null")
    if "crystals" in value and (not isinstance(value["crystals"], list) or any(not isinstance(item, dict) for item in value["crystals"])):
        raise RuntimeError("Compact crystals must contain objects")
    if value.get("briefing") is not None and not isinstance(value["briefing"], str):
        raise RuntimeError("Compact briefing must be text or null")
    return value, text


def context_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in context_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in context_strings(item)]
    return []


def legitimate_record_preserved(reply: dict[str, Any], expected_text: str) -> bool:
    record = reply.get("record")
    if not isinstance(record, dict) or "superseded_by" not in record:
        raise RuntimeError("Cannot score preservation without explicit lifecycle state")
    return record.get("content") == expected_text and record["superseded_by"] is None


def parse_mcp_output(stdout: str, calls: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    messages: dict[int, dict[str, Any]] = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        msg = strict_json_loads(line)
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            raise RuntimeError("Malformed JSON-RPC envelope")
        if "id" not in msg:
            if isinstance(msg.get("method"), str):
                continue
            raise RuntimeError("Reply lacks response ID")
        ident = msg["id"]
        if "method" in msg or "params" in msg:
            raise RuntimeError("Response mixes request and response fields")
        if type(ident) is not int or ident < 0 or ident > len(calls) or ident in messages:
            raise RuntimeError("Duplicate, unexpected or invalid response ID")
        messages[ident] = msg
    if set(messages) != set(range(len(calls) + 1)):
        raise RuntimeError("Missing initialize/tool response")
    initial = messages[0].get("result")
    if "error" in messages[0] or not isinstance(initial, dict) or not isinstance(initial.get("protocolVersion"), str):
        raise RuntimeError("Initialize did not explicitly succeed")
    ordered = []
    for ident, (name, args) in enumerate(calls, 1):
        msg = messages[ident]
        result = msg.get("result")
        if "error" in msg or not isinstance(result, dict) or result.get("isError"):
            raise RuntimeError(f"Failed MCP call {name}: {msg!r}")
        content = result.get("content")
        if not isinstance(content, list) or len(content) != 1 or content[0].get("type") != "text" or not isinstance(content[0].get("text"), str):
            raise RuntimeError(f"Unexpected MCP content shape for {name}")
        response = strict_json_loads(content[0]["text"])
        assert_tool_shape(name, response, args)
        ordered.append(response)
    return ordered


class OkapiBM25:
    """Standard Okapi BM25 baseline over plain markdown/text or structured files."""

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
                        "clientInfo": {"name": "pinned-task-eval", "version": "1.1.0"},
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
        batch = {"calls": calls, "store": str(self.store_dir), "outcome": "attempted"}
        BATCH_AUDIT.append(batch)
        call_rows = [{"tool": name, "arguments": args, "outcome": "attempted"} for name, args in calls]
        CALL_AUDIT.extend(call_rows)
        try:
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
            ordered = parse_mcp_output(proc.stdout, calls)
        except Exception as exc:
            batch.update(outcome="failed", error=str(exc))
            for row in call_rows:
                row.update(outcome="batch_failed", error=str(exc))
            raise
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        batch.update(outcome="success", elapsed_ms=elapsed_ms, raw_stdout=proc.stdout)
        for row, response in zip(call_rows, ordered):
            row.update(outcome="success", response=response)
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
            budget = int(sc["budget_tokens"])

            # Build Session 1 turn sequence (32 turns)
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

            # 1) Unstructured plain-files tail baseline (reads tail of session.md up to budget_tokens)
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
                if used_tokens + t_est > budget:
                    break
                tail_selected.append(line)
                used_tokens += t_est
            tail_text = "\n".join(reversed(tail_selected))
            while len(tail_text.encode("utf-8")) > budget * 4:
                tail_selected.pop()
                tail_text = "\n".join(reversed(tail_selected))
            used_tokens = approx_tokens(tail_text)
            tail_ms = (time.perf_counter() - t0) * 1000.0
            tail_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in tail_text)
            tail_open_ok = (sc["open_q"] in tail_text) and (sc["resolved_q"] not in tail_text)

            # 2) Unstructured plain-files Okapi BM25 baseline (within budget)
            t1 = time.perf_counter()
            bm25 = OkapiBM25(bm25_docs)
            bm25_hits = bm25.search(
                "verified architectural decision invariant open question unresolved", limit=12
            )
            bm25_selected: list[str] = []
            bm25_tokens = 0
            for h in bm25_hits:
                t_est = approx_tokens(h["content"])
                if bm25_tokens + t_est > budget:
                    break
                bm25_selected.append(h["content"])
                bm25_tokens += t_est
            bm25_text = "\n".join(bm25_selected)
            while len(bm25_text.encode("utf-8")) > budget * 4:
                bm25_selected.pop()
                bm25_text = "\n".join(bm25_selected)
            bm25_tokens = approx_tokens(bm25_text)
            bm25_ms = (time.perf_counter() - t1) * 1000.0
            bm25_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in bm25_text)
            bm25_open_ok = (sc["open_q"] in bm25_text) and (sc["resolved_q"] not in bm25_text)

            # 3) Equal-information structured metadata JSONL baseline:
            # Given the exact same turn_type, importance, resolves, and track fields as WhiteMagic,
            # and the same typed/importance/content salience rule, plus open questions
            # and recent turns, within the same 1,120-byte serialized context cap.
            t_eq = time.perf_counter()
            structured_jsonl = files_dir / "session_structured.jsonl"
            structured_rows = []
            for t in turns_list:
                row = {
                    "seq": t["seq"],
                    "session_id": f"{sc['id']}_s1",
                    "track": sc["track"],
                    "role": t["role"],
                    "turn_type": t["turn_type"],
                    "qualifier": t["qualifier"],
                    "importance": t["importance"],
                    "content": t["content"],
                    "resolves": 5 if t.get("_resolves_prev") else None,
                }
                structured_rows.append(row)
            # Also add an intervening unrelated session row to the structured JSONL log
            structured_rows.append(
                {
                    "seq": 33,
                    "session_id": f"{sc['id']}_unrelated_s99",
                    "track": "unrelated-intervening-track",
                    "role": "ai",
                    "turn_type": "decision",
                    "qualifier": "verified",
                    "importance": 0.95,
                    "content": "Unrelated track decision: rotate staging CSS bundles weekly.",
                    "resolves": None,
                }
            )
            structured_jsonl.write_text(
                "\n".join(json.dumps(r) for r in structured_rows) + "\n", encoding="utf-8"
            )
            loaded_rows = [
                json.loads(line)
                for line in structured_jsonl.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            track_rows = [r for r in loaded_rows if r["track"] == sc["track"]]
            resolved_seqs = {r["resolves"] for r in track_rows if r.get("resolves") is not None}
            open_q_rows = [
                r for r in track_rows if r["turn_type"] == "question" and r["seq"] not in resolved_seqs
            ]
            salient_rows = [
                r
                for r in track_rows
                if r["seq"] not in {x["seq"] for x in open_q_rows}
                and structured_salient(r)
            ]
            recent_rows = [
                r
                for r in reversed(track_rows[-3:])
                if r["seq"] not in {x["seq"] for x in open_q_rows + salient_rows}
            ]
            eq_context: dict[str, Any] = {"turns": []}
            for candidate in open_q_rows + salient_rows + recent_rows:
                kind = "arc" if candidate in open_q_rows else "decision" if candidate["turn_type"] == "decision" else "recent"
                compact = {"kind": kind, "text": candidate["content"]}
                prospective = {"turns": eq_context["turns"] + [compact]}
                if len(json.dumps(prospective, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) <= budget * 4:
                    eq_context = prospective
            eq_text = json.dumps(eq_context, ensure_ascii=False, separators=(",", ":")) if budget else ""
            eq_tokens = approx_tokens(eq_text)
            eq_ms = (time.perf_counter() - t_eq) * 1000.0
            eq_semantics = "\n".join(context_strings(eq_context))
            eq_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in eq_semantics)
            eq_open_ok = (sc["open_q"] in eq_semantics) and (sc["resolved_q"] not in eq_semantics)

            # 4) WhiteMagic v10.4.0:
            # Session 1 records + crystallizes; then an unrelated session on another track runs;
            # then genuine new Session 2 starts on `sc["track"]` and calls `session_continuity`
            # under the single enforced `token_budget = 280`.
            wm = WMMcpSession(wm_bin, store_dir)
            s1_id = f"{sc['id']}_s1"
            unrel_id = f"{sc['id']}_unrelated_s99"
            s2_id = f"{sc['id']}_s2"

            pre_calls: list[tuple[str, dict[str, Any]]] = []
            for t in turns_list[:5]:
                pre_calls.append(
                    (
                        "session_record",
                        {
                            "session_id": s1_id,
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
            for r in pre_res:
                assert_mcp_ok(r, f"{sc['id']}:pre_record")
            resolved_q_turn_id = pre_res[4]["turn_id"]

            post_calls: list[tuple[str, dict[str, Any]]] = [
                (
                    "session_record",
                    {
                        "session_id": s1_id,
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
                            "session_id": s1_id,
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
                        "session_id": s1_id,
                        "track": sc["track"],
                        "summary": f"Completed {sc['id']} design and recorded decisions.",
                        "crystallize": True,
                    },
                )
            )
            # Intervening unrelated session on a different track
            post_calls.append(
                (
                    "session_record",
                    {
                        "session_id": unrel_id,
                        "track": "unrelated-intervening-track",
                        "role": "ai",
                        "turn_type": "decision",
                        "qualifier": "verified",
                        "importance": 0.95,
                        "content": "Unrelated track decision: rotate staging CSS bundles weekly.",
                    },
                )
            )
            post_calls.append(
                (
                    "session_record",
                    {
                        "session_id": unrel_id,
                        "track": "unrelated-intervening-track",
                        "role": "user",
                        "turn_type": "question",
                        "qualifier": "conditional",
                        "importance": 0.85,
                        "content": "Q_UNRELATED: Should staging CSS use brotli level 9?",
                    },
                )
            )
            post_calls.append(
                (
                    "session_checkpoint",
                    {
                        "session_id": unrel_id,
                        "track": "unrelated-intervening-track",
                        "summary": "Unrelated track checkpoint.",
                        "crystallize": False,
                    },
                )
            )
            post_res, _, _ = wm.run_batch(post_calls)
            for r in post_res:
                assert_mcp_ok(r, f"{sc['id']}:post_record")

            # Probe 1: Empty new session `s2_id` (0 turns recorded yet) with `track=sc["track"]`
            # routes past the intervening unrelated session (`unrel_id`) to `s1_id`.
            # Then `s2_id` logs its opening turn, and Probe 2 (`current_session_id=s2_id`,
            # `track=sc["track"]`) retrieves prior continuity under `token_budget = 280`.
            recovery_calls: list[tuple[str, dict[str, Any]]] = [
                (
                    "session_continuity",
                    {
                        "session_id": s2_id,
                        "track": sc["track"],
                        "n": 3,
                        "token_budget": budget,
                        "include_briefing_text": False,
                    },
                ),
                (
                    "session_record",
                    {
                        "session_id": s2_id,
                        "track": sc["track"],
                        "role": "user",
                        "turn_type": "message",
                        "qualifier": "conditional",
                        "importance": 0.40,
                        "content": f"Resuming {sc['track']} in new session {s2_id}.",
                    },
                ),
                (
                    "session_continuity",
                    {
                        "current_session_id": s2_id,
                        "track": sc["track"],
                        "n": 3,
                        "token_budget": budget,
                        "include_briefing_text": False,
                    },
                ),
            ]
            rec_res, wm_ms, wm_bytes = wm.run_batch(recovery_calls)
            for r in rec_res:
                assert_mcp_ok(r, f"{sc['id']}:continuity")
            cont_empty_s2 = rec_res[0]
            cont_out = rec_res[2]

            selected_prior_session = cont_out.get("session_id")
            new_session_routing_ok = (selected_prior_session == s1_id) and (
                cont_empty_s2.get("session_id") == s1_id
            )

            # The compact string is the sole consumed/scored agent context.
            projection, wire_text = validate_agent_context(cont_out)
            scored_text = "\n".join(context_strings(projection))
            context_turns = projection.get("turns", [])
            unresolved_arcs = [turn for turn in context_turns if turn.get("kind") == "arc"]
            wm_tokens_used = approx_tokens(wire_text)
            wm_recomputed_tokens = wm_tokens_used
            budget_enforced = len(wire_text.encode("utf-8")) <= budget * 4
            if not budget_enforced:
                raise RuntimeError(
                    f"Budget exceeded in {sc['id']}: token_estimate={wm_tokens_used}, recomputed={wm_recomputed_tokens}, budget={budget}"
                )

            wm_dec_hits = sum(1 for d, _, _, _ in sc["decisions"] if d in scored_text)
            unresolved_texts = [a.get("text", "") for a in unresolved_arcs]
            wm_open_ok = (
                (len(unresolved_arcs) == 1)
                and (unresolved_texts[0] == sc["open_q"])
                and (sc["resolved_q"] not in scored_text)
            )
            related_crystals = projection.get("crystals", [])
            crystal_surfaced = len(related_crystals) >= 1

            failure_trace = None
            if not (wm_dec_hits == len(sc["decisions"]) and wm_open_ok and new_session_routing_ok and budget_enforced and crystal_surfaced):
                missing = [d for d, _, _, _ in sc["decisions"] if d not in scored_text]
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": "One or more expected decisions, open arc, track crystal, routing or budget checks failed in the consumed compact context",
                    "missing_decisions": missing,
                    "open_arc_ok": wm_open_ok, "track_routing_ok": new_session_routing_ok,
                    "crystal_surfaced": crystal_surfaced, "budget_enforced": budget_enforced,
                    "observed_context_bytes": len(wire_text.encode("utf-8")),
                }

            results.append(
                {
                    "scenario_id": sc["id"],
                    "stress_untyped": sc["stress_untyped"],
                    "budget_tokens": budget,
                    "context_byte_cap": budget * 4,
                    "budget_scope": "exact consumed UTF-8 context string; bytes/4 token estimate; transport/debug metadata excluded",
                    "plain_files_tail": {
                        "decision_recall": round(tail_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if tail_open_ok else 0.0,
                        "tokens_used": used_tokens,
                        "budget_enforced": used_tokens <= budget,
                        "latency_ms": round(tail_ms, 3),
                    },
                    "bm25_flat_files": {
                        "decision_recall": round(bm25_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if bm25_open_ok else 0.0,
                        "tokens_used": bm25_tokens,
                        "budget_enforced": bm25_tokens <= budget,
                        "latency_ms": round(bm25_ms, 3),
                    },
                    "structured_metadata_files": {
                        "decision_recall": round(eq_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if eq_open_ok else 0.0,
                        "tokens_used": eq_tokens,
                        "budget_enforced": eq_tokens <= budget,
                        "latency_ms": round(eq_ms, 3),
                    },
                    "whitemagic_v10_4": {
                        "decision_recall": round(wm_dec_hits / 4.0, 3),
                        "open_arc_precision": 1.0 if wm_open_ok else 0.0,
                        "new_session_track_routing_ok": new_session_routing_ok,
                        "selected_prior_session": selected_prior_session,
                        "cross_session_crystal_surfaced": crystal_surfaced,
                        "tokens_used": wm_tokens_used,
                        "context_bytes": len(wire_text.encode("utf-8")),
                        "consumed_context": wire_text,
                        "budget_enforced": budget_enforced,
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
        "expected_token": "9c01c6ce1bf16dfb9777d9acf2f37c0c208298a9d7e7d7917184e67471a25a11",
        "stale_token": "232e31be6fa850e89a4fae9328e33e377cb36a3db67cce5b7b130c5856f0bd38",
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

            # 1) Unstructured plain files + BM25 baseline: writes each record as a markdown file without supersession links
            t0 = time.perf_counter()
            docs: list[dict[str, Any]] = []
            docs.append({"id": "v1", "content": sc["v1"], "is_current": False})
            for idx, p in enumerate(sc["v1_paraphrases"], start=1):
                docs.append({"id": f"v1_p{idx}", "content": p, "is_current": False})
            for idx, u in enumerate(sc["updates"], start=2):
                is_last = idx == (len(sc["updates"]) + 1)
                docs.append({"id": f"v{idx}", "content": u, "is_current": is_last})
            for d in docs:
                (files_dir / f"{d['id']}.md").write_text(d["content"] + "\n", encoding="utf-8")

            bm25 = OkapiBM25(docs)
            bm25_hits = bm25.search(sc["query"], limit=3)
            bm25_ms = (time.perf_counter() - t0) * 1000.0
            bm25_top1_ok = bool(bm25_hits and bm25_hits[0].get("is_current"))
            bm25_stale_hits = sum(1 for h in bm25_hits if not h.get("is_current"))

            # 2) Equal-information structured supersedes JSONL baseline:
            # Given the exact same governed supersession links as WhiteMagic, filters out superseded records before BM25.
            t_eq = time.perf_counter()
            superseded_doc_ids: set[str] = set()
            if sc["use_governed_update"]:
                for d in docs:
                    if not d["is_current"]:
                        superseded_doc_ids.add(d["id"])
            active_eq_docs = [d for d in docs if d["id"] not in superseded_doc_ids]
            bm25_eq = OkapiBM25(active_eq_docs)
            eq_hits = bm25_eq.search(sc["query"], limit=3)
            eq_ms = (time.perf_counter() - t_eq) * 1000.0
            eq_top1_ok = bool(eq_hits and eq_hits[0].get("is_current"))
            eq_stale_hits = sum(1 for h in eq_hits if not h.get("is_current"))

            # 3) WhiteMagic v10.4.0:
            wm = WMMcpSession(wm_bin, store_dir)
            init_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_remember", {"content": sc["v1"], "title": f"{sc['id']}_canonical"}),
            ]
            for idx, p in enumerate(sc["v1_paraphrases"], start=1):
                init_calls.append(("memory_remember", {"content": p, "title": f"{sc['id']}_p{idx}"}))
            init_res, _, _ = wm.run_batch(init_calls)
            for r in init_res:
                assert_mcp_ok(r, f"{sc['id']}:init_remember")
            v1_id = init_res[0]["record_id"]
            curr_id = v1_id
            paraphrase_ids = [r["record_id"] for r in init_res[1:]]
            stale_record_ids: set[int] = {v1_id, *paraphrase_ids}

            if sc["use_governed_update"]:
                # Supersede canonical record across update hops
                for hop_idx, u_text in enumerate(sc["updates"]):
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
                    assert_mcp_ok(res_u[0], f"{sc['id']}:update_hop_{hop_idx}")
                    if hop_idx < len(sc["updates"]) - 1:
                        stale_record_ids.add(res_u[0]["record_id"])
                    curr_id = res_u[0]["record_id"]
                stale_record_ids.discard(curr_id)

                # Consolidate all stale paraphrases into the terminal record (testing duplicate_exact consolidation!)
                for pid in paraphrase_ids:
                    res_p, _, _ = wm.run_batch(
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
                    assert_mcp_ok(res_p[0], f"{sc['id']}:consolidate_paraphrase_{pid}")
                    if res_p[0].get("record_id") != curr_id:
                        raise RuntimeError(
                            f"Expected paraphrase {pid} to consolidate into head {curr_id}, got {res_p[0]}"
                        )
            else:
                # Stress case M8: agent just calls memory_remember without memory.update
                for u_text in sc["updates"]:
                    res_raw, _, _ = wm.run_batch(
                        [("memory_remember", {"content": u_text, "title": f"{sc['id']}_unlinked"})]
                    )
                    assert_mcp_ok(res_raw[0], f"{sc['id']}:unlinked_remember")
                    curr_id = res_raw[0]["record_id"]

            query_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_recall", {"query": sc["query"], "limit": 3}),
                ("memory.revisions", {"id": curr_id, "action": "verify"}),
            ]
            if sc["use_governed_update"]:
                for pid in paraphrase_ids:
                    query_calls.append(("memory.revisions", {"id": pid, "action": "verify"}))
            q_res, wm_ms, wm_bytes = wm.run_batch(query_calls)
            for r in q_res:
                assert_mcp_ok(r, f"{sc['id']}:query_verify")

            recall_out = q_res[0]
            rev_out = q_res[1]
            paraphrase_revs = q_res[2:]

            wm_hits = recall_out.get("results", [])
            active_hits = [h for h in wm_hits if h.get("superseded_by") is None]
            top_hit = active_hits[0] if active_hits else {}

            # Strict version-identity check: top_hit must be `curr_id` and contain expected_token
            wm_top1_ok = (top_hit.get("record_id") == curr_id) and (
                sc["expected_token"] in top_hit.get("content", "")
            )
            # Stale check by version identity (any active hit in stale_record_ids or carrying stale_token)
            unflagged_stale = sum(
                1
                for h in active_hits
                if (h.get("record_id") in stale_record_ids) or (sc["stale_token"] in h.get("content", ""))
            )

            verify_block = rev_out.get("verify", {})
            paraphrase_dag_ok = all(
                bool(pr.get("verify", {}).get("valid"))
                and pr.get("verify", {}).get("head_record_id") == curr_id
                for pr in paraphrase_revs
            )
            lineage_ok = (
                bool(verify_block.get("valid"))
                and verify_block.get("head_record_id") == curr_id
                and int(verify_block.get("chain_length", 0)) >= len(sc["updates"]) + len(paraphrase_ids)
                and paraphrase_dag_ok
            )

            failure_trace = None
            if not wm_top1_ok or (sc["use_governed_update"] and (unflagged_stale != 0 or not lineage_ok)):
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": "Governed current-truth, stale-exclusion or lineage check failed" if sc["use_governed_update"] else "Negative control: an unlinked raw contradiction supplies no supersession edge",
                    "top1_record_id": top_hit.get("record_id"), "expected_record_id": curr_id,
                    "active_stale_count": unflagged_stale, "lineage_ok": lineage_ok,
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
                    "structured_supersedes_files": {
                        "top1_current_truth": 1.0 if eq_top1_ok else 0.0,
                        "unflagged_stale_in_top3": round(eq_stale_hits / max(1, len(eq_hits)), 3),
                        "lineage_verifiable": 0.0,
                        "latency_ms": round(eq_ms, 3),
                    },
                    "whitemagic_v10_4": {
                        "top1_current_truth": 1.0 if wm_top1_ok else 0.0,
                        "unflagged_stale_in_top3": round(unflagged_stale / max(1, len(active_hits)), 3),
                        "active_stale_count": unflagged_stale,
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
            append_poison_free = any(h["id"] == "correction" for h in append_hits) and all(sc["bad_marker"] not in h["content"] for h in append_hits)
            append_legit_kept = 1.0

            # Baseline 2: Plain-files naive entity/keyword line prune (deletes lines containing entity_token)
            t1 = time.perf_counter()
            pruned_docs = [
                d for d in append_docs[:-1] if sc["entity_token"] not in d["content"]
            ]
            pruned_docs.append({"id": "correction", "content": sc["repaired_memory"]})
            bm25_prune = OkapiBM25(pruned_docs)
            prune_hits = bm25_prune.search(sc["query"], limit=3)
            prune_ms = (time.perf_counter() - t1) * 1000.0
            prune_poison_free = any(h["id"] == "correction" for h in prune_hits) and all(sc["bad_marker"] not in h["content"] for h in prune_hits)
            surviving_legit = sum(
                1 for leg in sc["legitimate_neighbors"] if any(d["content"] == leg for d in pruned_docs)
            )
            prune_legit_kept = surviving_legit / float(len(sc["legitimate_neighbors"]))

            # Baseline 3: Equal-information record-addressed file store (given exact bad record ID)
            t_eq = time.perf_counter()
            addressed_docs = [
                ({"id": "bad", "content": sc["repaired_memory"]} if d["id"] == "bad" else d)
                for d in append_docs[:-1]
            ]
            bm25_addr = OkapiBM25(addressed_docs)
            addr_hits = bm25_addr.search(sc["query"], limit=3)
            addr_ms = (time.perf_counter() - t_eq) * 1000.0
            addr_poison_free = (
                len(addr_hits) >= 1
                and any(h["id"] == "bad" and h["content"] == sc["repaired_memory"] for h in addr_hits)
                and all(sc["bad_marker"] not in h["content"] for h in addr_hits)
            )
            addr_rank1 = bool(addr_hits and addr_hits[0]["id"] == "bad" and addr_hits[0]["content"] == sc["repaired_memory"])
            addr_legit_kept = 1.0

            # WhiteMagic v10.4.0: Surgical record-addressed memory.update + legitimate neighbor verification
            wm = WMMcpSession(wm_bin, store_dir)
            ingest_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_remember", {"content": sc["bad_memory"], "title": f"{sc['id']}_bad"}),
            ]
            for idx, leg in enumerate(sc["legitimate_neighbors"], start=1):
                ingest_calls.append(("memory_remember", {"content": leg, "title": f"{sc['id']}_leg_{idx}"}))
            ing_res, _, _ = wm.run_batch(ingest_calls)
            for r in ing_res:
                assert_mcp_ok(r, f"{sc['id']}:ingest")
            bad_id = ing_res[0]["record_id"]
            legit_ids = [r["record_id"] for r in ing_res[1:]]

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
            repair_calls.append(("memory_get", {"id": str(bad_id)}))
            repair_calls.append(
                ("memory.revisions", {"id": bad_id, "action": "verify"})
            )
            rep_res, wm_ms, wm_bytes = wm.run_batch(repair_calls)
            for r in rep_res:
                assert_mcp_ok(r, f"{sc['id']}:repair")

            recall_hits = rep_res[1].get("results", [])
            repaired_id = rep_res[0]["record_id"]
            active_hits = [h for h in recall_hits if h.get("superseded_by") is None]
            wm_poison_free_top3 = (
                len(active_hits) >= 1
                and any(h["record_id"] == repaired_id and h["content"] == sc["repaired_memory"] for h in active_hits)
                and all(sc["bad_marker"] not in h.get("content", "") for h in active_hits)
                and all(h.get("record_id") != bad_id for h in active_hits)
            )
            wm_rank1 = (
                len(active_hits) >= 1
                and active_hits[0]["record_id"] == repaired_id
                and active_hits[0]["content"] == sc["repaired_memory"]
                and all(sc["bad_marker"] not in h.get("content", "") for h in active_hits)
            )
            legit_reads = rep_res[2 : 2 + len(legit_ids)]
            wm_legit_intact = sum(
                1
                for r, expected_text in zip(legit_reads, sc["legitimate_neighbors"])
                if legitimate_record_preserved(r, expected_text)
            )
            wm_legit_rate = wm_legit_intact / float(len(sc["legitimate_neighbors"]))
            rev_verify = rep_res[-1].get("verify", {})
            audit_ok = (bool(rev_verify.get("valid")) and rev_verify["head_record_id"] == repaired_id
                        and int(rev_verify.get("chain_length", 0)) == 1
                        and rep_res[-2]["record"]["superseded_by"] == repaired_id)

            failure_trace = None
            if not (wm_rank1 and wm_poison_free_top3 and wm_legit_rate == 1.0 and audit_ok):
                failure_trace = {
                    "system": "whitemagic_v10_4",
                    "scenario": sc["id"],
                    "cause": "One or more repaired-identity retrieval, poison exclusion, neighbor preservation or lineage checks failed",
                    "repaired_record_id": repaired_id, "active_top3_record_ids": [h["record_id"] for h in active_hits],
                    "rank1_ok": wm_rank1, "poison_free_top3": wm_poison_free_top3,
                    "legitimate_preserved_rate": wm_legit_rate, "lineage_ok": audit_ok,
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
                    "record_addressed_files": {
                        "poison_free_active_top3": 1.0 if addr_poison_free else 0.0,
                        "repaired_at_rank1": 1.0 if addr_rank1 else 0.0,
                        "legitimate_state_preserved": round(addr_legit_kept, 3),
                        "joint_success_top3": 1.0 if (addr_poison_free and addr_legit_kept == 1.0) else 0.0,
                        "joint_success_rank1": 1.0 if (addr_rank1 and addr_legit_kept == 1.0) else 0.0,
                        "audit_trail_verified": 0.0,
                        "latency_ms": round(addr_ms, 3),
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


# ─── Task Family 4: Authored Cue-Guided Migration (No Target IDs Supplied)

DISCOVERY_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "D1_discover_crystal_pq_alg_bypass",
        "search_query": "crystal_client supported signature algorithms ml-dsa-65 verification",
        "obsolete_claims": [
            "crystal_client accepts standalone ml-dsa-65 client_sig profiles without running an Ed25519 signature verifier.",
            "Migration note: standalone ml-dsa-65 signature algorithm is allowed in SUPPORTED_CLIENT_SIG_ALGS without a PQ verifier callback.",
        ],
        "authoritative_replacement": (
            "crystal_client supported signature algorithms ml-dsa-65 verification: standalone ml-dsa-65 is rejected; "
            "only ed25519 and hybrid ed25519+ml-dsa-65 (with mandatory Ed25519 + fail-closed pq_verifier) are accepted."
        ),
        "stale_clues": ["standalone ml-dsa-65", "without running an ed25519", "without a pq verifier"],
        "expected_marker": "fail-closed pq_verifier",
        "legitimate_neighbors": [
            "crystal_client verifies Ed25519 signatures over RFC 8785 JCS canonical envelope bytes.",
            "crystal_client binds crystal_id to the initial wrapping KEK version (id_kek_version).",
            "crystal_client enforces 0600 file permissions when loading bearer token files.",
        ],
    },
    {
        "id": "D2_discover_notarization_unsigned_acceptance",
        "search_query": "verify_crystal_set_third_party context notarization signature check",
        "obsolete_claims": [
            "verify_crystal_set_third_party context notarization signature check accepts any dictionary with spec wm.context-notarization and highwater_digest.",
            "Audit note: verify_crystal_set_third_party marks notarized=true without requiring a notary_public_key.",
        ],
        "authoritative_replacement": (
            "verify_crystal_set_third_party context notarization signature check requires a 32-byte Ed25519 "
            "notary_public_key and verifies notarization.signature over the canonical statement before setting notarized=true."
        ),
        "stale_clues": ["accepts any dictionary", "without requiring a notary_public_key"],
        "expected_marker": "notary_public_key",
        "legitimate_neighbors": [
            "verify_crystal_set_third_party recomputes crystal_set_digest over sorted cell_ids.",
            "verify_crystal_set_third_party detects missing crystals when commitment crystal_count exceeds the bundle.",
            "verify_crystal_set_third_party checks optional OpenTimestamps proof commitments against the set digest.",
        ],
    },
    {
        "id": "D3_discover_landlock_truncate_omission",
        "search_query": "receipt-api landlock write confinement access mask truncate refer",
        "obsolete_claims": [
            "receipt-api landlock write confinement access mask covers bits 1..12 only and omits LANDLOCK_ACCESS_FS_TRUNCATE on ABI v3+.",
            "Sandbox note: receipt-api landlock write confinement access mask leaves truncate and refer bits unset.",
        ],
        "authoritative_replacement": (
            "receipt-api landlock write confinement access mask truncate refer includes LANDLOCK_ACCESS_FS_REFER (bit 13) "
            "on ABI >= 2 and LANDLOCK_ACCESS_FS_TRUNCATE (bit 14) on ABI >= 3 to block outside file truncation."
        ),
        "stale_clues": ["bits 1..12 only", "leaves truncate and refer bits unset"],
        "expected_marker": "LANDLOCK_ACCESS_FS_TRUNCATE",
        "legitimate_neighbors": [
            "receipt-api landlock write confinement grants read-only access to /usr, /lib, /etc, and /proc.",
            "receipt-api landlock write confinement grants read-write access strictly to the state directory and /tmp.",
            "receipt-api calls prctl(PR_SET_NO_NEW_PRIVS, 1) prior to landlock_restrict_self.",
        ],
    },
    {
        "id": "D4_discover_erasure_receipt_overclaim",
        "search_query": "receipt-api DELETE crystal erasure_class backup retention classification",
        "obsolete_claims": [
            "receipt-api DELETE crystal erasure_class backup retention classification emits cryptographic_erasure_or_purge and claims immediate off-box backup wipe.",
            "Compliance draft: server DELETE /v1/crystals/<id> proves client DEK destruction.",
        ],
        "authoritative_replacement": (
            "receipt-api DELETE crystal erasure_class backup retention classification emits access_control_and_ciphertext_purge "
            "with server_action=ciphertext_unlinked_and_tombstoned and discloses offbox_12_snapshot_rotation_window."
        ),
        "stale_clues": ["cryptographic_erasure_or_purge", "proves client dek destruction"],
        "expected_marker": "access_control_and_ciphertext_purge",
        "legitimate_neighbors": [
            "receipt-api DELETE /v1/crystals/<id> records a durable tombstone preventing re-upload of the same crystal_id.",
            "receipt-api signs deletion receipts with the hosted Ed25519 gate key.",
            "receipt-api requires a valid owner X-WM-Crystal-Assertion header on DELETE requests.",
        ],
    },
    {
        "id": "D5_discover_kek_rotation_stale_signature",
        "search_query": "rotate_crystal_kek signed crystal envelope client_sig re-signing",
        "obsolete_claims": [
            "rotate_crystal_kek signed crystal envelope client_sig re-signing leaves the old client_sig untouched after updating kek_version.",
            "Rotation note: rotate_crystal_kek does not accept an ed25519_private_key parameter.",
        ],
        "authoritative_replacement": (
            "rotate_crystal_kek signed crystal envelope client_sig re-signing verifies the prior signature, requires "
            "the matching ed25519_private_key, and atomically re-signs the rotated envelope."
        ),
        "stale_clues": ["leaves the old client_sig untouched", "does not accept an ed25519_private_key"],
        "expected_marker": "atomically re-signs",
        "legitimate_neighbors": [
            "rotate_crystal_kek re-wraps the per-crystal DEK under the new KEK version without re-encrypting the payload.",
            "rotate_crystal_kek preserves crystal_id by keeping id_kek_version fixed.",
            "rotate_crystal_kek refuses rotation if the old KEK fails to authenticate the existing wrapped_dek.",
        ],
    },
    {
        "id": "D6_discover_backup_monitor_auth_api_prefix",
        "search_query": "check_backup_freshness auth-state required archive prefixes gzip trailer",
        "obsolete_claims": [
            "check_backup_freshness auth-state required archive prefixes gzip trailer checks only whitemagic-hosted/ and skips whitemagic-hosted-api/.",
            "Monitor note: check_backup_freshness reads tar headers via getnames() without decompressing the gzip stream to EOF.",
        ],
        "authoritative_replacement": (
            "check_backup_freshness auth-state required archive prefixes gzip trailer requires both whitemagic-hosted/ "
            "and whitemagic-hosted-api/ subtrees and decompresses the full gzip stream to EOF."
        ),
        "stale_clues": ["skips whitemagic-hosted-api/", "without decompressing the gzip stream"],
        "expected_marker": "whitemagic-hosted-api/",
        "legitimate_neighbors": [
            "check_backup_freshness verifies 64-hex SHA-256 sidecar digests for all three backup series.",
            "check_backup_freshness enforces a 36-hour maximum age window for daily off-box archives.",
            "check_backup_freshness runs daily via whitemagic-backup-freshness-check.timer.",
        ],
    },
    {
        "id": "D7_discover_economy_discovery_flag_mismatch",
        "search_query": "hosted x402 payment challenge discovery economy_enabled flag",
        "obsolete_claims": [
            "hosted x402 payment challenge discovery economy_enabled flag advertises nano credit advances even when --economy is disabled.",
            "Gateway note: 402 challenge metadata ignores the runtime economy_enabled boolean.",
        ],
        "authoritative_replacement": (
            "hosted x402 payment challenge discovery economy_enabled flag suppresses nano advance advertisements "
            "whenever --economy is disabled and returns 503 economy_disabled on economy endpoints."
        ),
        "stale_clues": ["even when --economy is disabled", "ignores the runtime economy_enabled"],
        "expected_marker": "suppresses nano advance",
        "legitimate_neighbors": [
            "hosted x402 payment challenge binds facilitator settlement verification to Base USDC.",
            "hosted x402 payment challenge rate-limits anonymous trial requests by client IP.",
            "hosted x402 payment challenge logs content-free settlement receipts.",
        ],
    },
    {
        "id": "D8_discover_release_health_tag_checkout_hazard",
        "search_query": "release_health.py historical tag checkout certification script execution",
        "obsolete_claims": [
            "release_health.py historical tag checkout certification script execution runs the checked-out old tag's script copy from the working tree.",
            "CI note: release certification allows empty bound_manifest_sha256 digests on historical tags.",
        ],
        "authoritative_replacement": (
            "release_health.py historical tag checkout certification script execution copies the trusted checker "
            "to RUNNER_TEMP before tag checkout and requires an exact 64-hex bound_manifest_sha256 digest."
        ),
        "stale_clues": ["old tag's script copy", "allows empty bound_manifest_sha256"],
        "expected_marker": "RUNNER_TEMP",
        "legitimate_neighbors": [
            "release_health.py verifies Ed25519 signatures over release-manifest.json.",
            "release_health.py cross-checks GitHub release asset sizes and SHA-256 digests.",
            "release_health.py validates npm and Docker certification metadata bindings.",
        ],
    },
]


def cue_selects_record(text: str, scenario: dict[str, Any]) -> bool:
    """Conservative authored-cue adapter; no general semantic-discovery claim.

    Exclude the supplied current text and explicitly negated matching clauses.
    Unanticipated paraphrases can still be missed and must be reported as limits.
    """
    lowered = text.lower().replace("’", "'")
    if text == scenario["authoritative_replacement"]:
        return False
    for clue in scenario["stale_clues"]:
        for match in re.finditer(re.escape(clue.lower()), lowered):
            prefix = lowered[max(0, match.start() - 48):match.start()]
            suffix = lowered[match.end():match.end() + 48]
            prefix_negative = re.search(r"\b(?:never|not|cannot|can't|do not|must not|reject|forbid|prohibit)\b[^.;!?]*$", prefix)
            suffix_negative = re.match(r"\s+(?:is|are|was|were)\s+(?:not\s+(?:allowed|permitted|supported)|prohibited|forbidden|rejected|disallowed)\b", suffix)
            if not prefix_negative and not suffix_negative:
                return True
    return False


def same_information_discovery_files(scenario: dict[str, Any], folder: Path) -> dict[str, Any]:
    folder.mkdir()
    texts = scenario["obsolete_claims"] + scenario["legitimate_neighbors"]
    docs = [{"id": f"record_{i:04d}", "content": text} for i, text in enumerate(texts)]
    # Ground truth stays outside the adapter: filenames/IDs disclose no role labels.
    obsolete = {doc["id"] for doc in docs[:len(scenario["obsolete_claims"])]}
    legitimate = {doc["id"] for doc in docs[len(scenario["obsolete_claims"]):]}
    for doc in docs:
        (folder / (doc["id"] + ".json")).write_text(json.dumps(doc), encoding="utf-8")
    loaded = [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))]
    hits = OkapiBM25(loaded).search(scenario["search_query"], limit=10)
    selected = {hit["id"] for hit in hits if cue_selects_record(hit["content"], scenario)}
    active = [doc for doc in loaded if doc["id"] not in selected]
    if selected:
        active.append({"id": "replacement", "content": scenario["authoritative_replacement"]})
    ranked = OkapiBM25(active).search(scenario["search_query"], limit=3)
    recall = len(selected & obsolete) / len(obsolete)
    precision = len(selected & obsolete) / len(selected) if selected else 0.0
    false_positives = len(selected & legitimate)
    preserved = (len(legitimate) - false_positives) / len(legitimate)
    top1 = bool(ranked and ranked[0]["id"] == "replacement")
    stale = sum(hit["id"] in obsolete for hit in ranked)
    return {"target_discovery_recall": recall, "target_discovery_precision": precision,
            "false_positive_supersessions": false_positives, "legitimate_state_preserved": preserved,
            "top1_current_truth": float(top1), "active_stale_in_top3": stale,
            "end_to_end_success": float(recall == 1 and false_positives == 0 and preserved == 1 and top1 and stale == 0),
            "cryptographic_revision_dag": False}


def run_discovery_family(wm_bin: Path) -> dict[str, Any]:
    """Authored deterministic workflow: exact stale cues and replacement are supplied."""
    results = []
    for sc in DISCOVERY_SCENARIOS:
        with tempfile.TemporaryDirectory(prefix=f"eval_{sc['id']}_") as td:
            td_path = Path(td)
            store_dir = td_path / "wm_store"
            file_baseline = same_information_discovery_files(sc, td_path / "equal_information_files")

            wm = WMMcpSession(wm_bin, store_dir)
            # Ingest corpus in shuffled/interleaved order without returning IDs to the discovery adapter
            corpus_items: list[tuple[str, str, bool]] = []
            corpus_items.append((sc["obsolete_claims"][0], "obsolete_0", True))
            for idx, leg in enumerate(sc["legitimate_neighbors"], start=1):
                corpus_items.append((leg, f"legit_{idx}", False))
            for idx, obs in enumerate(sc["obsolete_claims"][1:], start=1):
                corpus_items.append((obs, f"obsolete_{idx}", True))

            ingest_calls = [
                ("memory_remember", {"content": text, "title": f"{sc['id']}_{label}"})
                for text, label, _ in corpus_items
            ]
            ing_res, _, _ = wm.run_batch(ingest_calls)
            for r in ing_res:
                assert_mcp_ok(r, f"{sc['id']}:ingest")

            ground_truth_obsolete_ids = {
                ing_res[i]["record_id"] for i, (_, _, is_obs) in enumerate(corpus_items) if is_obs
            }
            ground_truth_legit_ids = [
                ing_res[i]["record_id"] for i, (_, _, is_obs) in enumerate(corpus_items) if not is_obs
            ]

            # Cue-guided adapter receives no target IDs; it DOES receive answer phrases.
            # Step 1: Search the store using only the natural-language query
            search_res, search_ms, search_bytes = wm.run_batch(
                [("memory_recall", {"query": sc["search_query"], "limit": 10})]
            )
            assert_mcp_ok(search_res[0], f"{sc['id']}:agent_search")
            candidates = search_res[0].get("results", [])

            # Step 2: Deterministic adapter applies supplied stale cues with bounded exclusions.
            discovered_obsolete_ids: list[int] = []
            for cand in candidates:
                if cand["superseded_by"] is None and cue_selects_record(cand["content"], sc):
                    discovered_obsolete_ids.append(cand["record_id"])

            # Step 3: Agent supersedes the first discovered obsolete record with the authoritative replacement,
            # and consolidates all remaining discovered obsolete records into that new head record!
            mutation_calls: list[tuple[str, dict[str, Any]]] = []
            head_id: int | None = None
            mutation_ms = 0.0
            mutation_bytes = 0
            if discovered_obsolete_ids:
                first_id = discovered_obsolete_ids[0]
                u_first, ms1, b1 = wm.run_batch(
                    [
                        (
                            "memory.update",
                            {
                                "id": first_id,
                                "content": sc["authoritative_replacement"],
                                "reason": "cue_guided_migration_supersede",
                            },
                        )
                    ]
                )
                assert_mcp_ok(u_first[0], f"{sc['id']}:agent_update_first")
                head_id = u_first[0]["record_id"]
                mutation_ms += ms1
                mutation_bytes += b1

                if len(discovered_obsolete_ids) > 1:
                    consolidate_calls = [
                        (
                            "memory.update",
                            {
                                "id": oid,
                                "superseded_by_id": head_id,
                                "reason": "cue_guided_migration_consolidate",
                            },
                        )
                        for oid in discovered_obsolete_ids[1:]
                    ]
                    u_rest, ms2, b2 = wm.run_batch(consolidate_calls)
                    for r in u_rest:
                        assert_mcp_ok(r, f"{sc['id']}:agent_consolidate")
                    mutation_ms += ms2
                    mutation_bytes += b2

            # Step 4: Independent verification of the resulting store state
            verify_calls: list[tuple[str, dict[str, Any]]] = [
                ("memory_recall", {"query": sc["search_query"], "limit": 3}),
            ]
            for lid in ground_truth_legit_ids:
                verify_calls.append(("memory_get", {"id": str(lid)}))
            for oid in sorted(ground_truth_obsolete_ids):
                verify_calls.append(("memory_get", {"id": str(oid)}))
            if head_id is not None:
                verify_calls.append(("memory.revisions", {"id": head_id, "action": "verify"}))
            v_res, verify_ms, verify_bytes = wm.run_batch(verify_calls)
            for r in v_res:
                assert_mcp_ok(r, f"{sc['id']}:verify")

            discovered_set = set(discovered_obsolete_ids)
            discovery_recall = len(discovered_set & ground_truth_obsolete_ids) / float(
                len(ground_truth_obsolete_ids)
            )
            false_positives = len(discovered_set & set(ground_truth_legit_ids))
            discovery_precision = (
                len(discovered_set & ground_truth_obsolete_ids) / float(len(discovered_set))
                if discovered_set
                else 0.0
            )

            active_hits = [
                h for h in v_res[0].get("results", []) if h.get("superseded_by") is None
            ]
            top1_ok = bool(
                active_hits
                and head_id is not None
                and active_hits[0].get("record_id") == head_id
                and sc["expected_marker"] in active_hits[0].get("content", "")
            )
            stale_in_top3 = sum(
                1 for h in active_hits if h.get("record_id") in ground_truth_obsolete_ids
            )
            legit_reads = v_res[1 : 1 + len(ground_truth_legit_ids)]
            legit_preserved = sum(
                1
                for r, expected_text in zip(legit_reads, sc["legitimate_neighbors"])
                if legitimate_record_preserved(r, expected_text)
            ) / float(len(sc["legitimate_neighbors"]))
            dag_verified = bool(
                head_id is not None
                and v_res[-1].get("verify", {}).get("valid")
                and v_res[-1].get("verify", {}).get("head_record_id") == head_id
            )
            obsolete_reads = v_res[1 + len(ground_truth_legit_ids):1 + len(ground_truth_legit_ids) + len(ground_truth_obsolete_ids)]
            all_obsolete_retired_to_head = head_id is not None and all(
                reply["record"]["superseded_by"] == head_id for reply in obsolete_reads)
            joint_success = discovery_recall == 1.0 and false_positives == 0 and top1_ok and stale_in_top3 == 0 and legit_preserved == 1.0 and dag_verified and all_obsolete_retired_to_head
            failure_trace = None if joint_success else {
                "system": "whitemagic_cue_guided_migration", "scenario": sc["id"],
                "cause": "Authored cue-guided adapter failed one or more independent discovery, current-truth, lifecycle-preservation or DAG checks",
                "discovery_recall": discovery_recall, "false_positive_supersessions": false_positives,
                "top1_current_truth": top1_ok, "active_stale_in_top3": stale_in_top3,
                "legitimate_state_preserved": legit_preserved, "dag_verified": dag_verified,
                "all_obsolete_retired_to_head": all_obsolete_retired_to_head,
                "limit": "This adapter receives exact stale clues and replacement text; unanticipated paraphrases are not semantically inferred",
            }

            results.append(
                {
                    "scenario_id": sc["id"],
                    "corpus_records": len(corpus_items),
                    "legitimate_neighbors": len(ground_truth_legit_ids),
                    "adapter_inputs": ["search_query", "exact_stale_clues", "authoritative_replacement_text"],
                    "equal_information_files": file_baseline,
                    "whitemagic_cue_guided_migration": {
                        "target_discovery_recall": round(discovery_recall, 3),
                        "target_discovery_precision": round(discovery_precision, 3),
                        "false_positive_supersessions": false_positives,
                        "top1_current_truth": 1.0 if top1_ok else 0.0,
                        "active_stale_in_top3": stale_in_top3,
                        "legitimate_state_preserved": round(legit_preserved, 3),
                        "converging_dag_verified": 1.0 if dag_verified else 0.0,
                        "all_obsolete_retired_to_head": all_obsolete_retired_to_head,
                        "end_to_end_success": float(joint_success),
                        "response_bytes": search_bytes + mutation_bytes + verify_bytes,
                        "latency_ms": round(search_ms + mutation_ms + verify_ms, 3),
                    },
                    "failure_trace": failure_trace,
                }
            )
    return {"family": "T_DISCOVERY", "scenarios": results}


def summarize_evaluation(
    wm_bin: Path,
    cont: dict[str, Any],
    conf: dict[str, Any],
    rep: dict[str, Any],
    disc: dict[str, Any],
) -> dict[str, Any]:
    c_sc = cont["scenarios"]
    m_sc = conf["scenarios"]
    r_sc = rep["scenarios"]
    d_sc = disc["scenarios"]

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
        s["failure_trace"]
        for s in (c_sc + m_sc + r_sc + d_sc)
        if s.get("failure_trace") is not None
    ]

    return {
        "schema": "wm.pinned-task-evaluation/1.2",
        "execution_status": "measurement completed; exit zero is not a task-score qualification",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "binary": {
            "path": str(wm_bin),
            "sha256": sha256_file(wm_bin),
            "version": "10.4.0",
        },
        "harness_sha256": sha256_file(Path(__file__)),
        "source_provenance": {
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE.parent, text=True).strip(),
            "tracked_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD", "--", "crates", "Cargo.toml", "Cargo.lock"], cwd=HERE.parent)).hexdigest(),
            "runtime_source_sha256": {str(path.relative_to(HERE.parent)): sha256_file(path) for path in (
                HERE.parent / "crates/wm-gen3-core/src/ops.rs",
                HERE.parent / "crates/wm-gen3-core/src/store.rs",
                HERE.parent / "crates/wm-gen3-harness/src/bridge.rs")},
            "binary_version_stdout": subprocess.check_output([str(wm_bin), "--version"], text=True).strip(),
        },
        "runtime_call_accounting": {
            "attempted": len(CALL_AUDIT),
            "explicit_success": sum(row["outcome"] == "success" for row in CALL_AUDIT),
            "failed_or_unverified": sum(row["outcome"] not in ("success", "ignored") for row in CALL_AUDIT),
            "ignored": sum(row["outcome"] == "ignored" for row in CALL_AUDIT),
            "policy": "abort on protocol, tool, shape, lifecycle or budget failure; no ignored errors",
        },
        "ignored_runtime_errors": sum(row["outcome"] == "ignored" for row in CALL_AUDIT),
        "limits": ["Authored deterministic regressions, no connected model or unseen holdout",
                   "Structured continuity files receive the same typed, importance and content-prefix salience heuristic; this heuristic is not an authority or semantic truth check",
                   "The structured continuity baseline serializes turns only; WM's capped representation may also contain derived checkpoint, queue, flags and crystals. Their wire overheads are not equal",
                   "Discovery receives exact stale clues and replacement text",
                   "Continuity compact context has a UTF-8 byte cap; tokens are bytes/4 estimates",
                   "Transport/debug metadata is excluded from consumed/scored context",
                   "Latency includes fresh process startup and unequal tool batches; no cost or tail-latency advantage established"],
        "total_scenarios": len(c_sc) + len(m_sc) + len(r_sc) + len(d_sc),
        "summary_by_family": {
            "T_CONTINUITY_cross_session_decision_recovery": {
                "scenario_count": len(c_sc),
                "compact_context_byte_cap": 1120,
                "estimated_tokens_at_bytes_div4": 280,
                "plain_files_tail": {
                    "mean_decision_recall_all_8": avg([s["plain_files_tail"]["decision_recall"] for s in c_sc]),
                    "mean_open_arc_precision": avg([s["plain_files_tail"]["open_arc_precision"] for s in c_sc]),
                    "latency": p50_p95([s["plain_files_tail"]["latency_ms"] for s in c_sc]),
                },
                "bm25_flat_files": {
                    "mean_decision_recall_all_8": avg([s["bm25_flat_files"]["decision_recall"] for s in c_sc]),
                    "mean_open_arc_precision": avg([s["bm25_flat_files"]["open_arc_precision"] for s in c_sc]),
                    "latency": p50_p95([s["bm25_flat_files"]["latency_ms"] for s in c_sc]),
                },
                "structured_metadata_files_equal_info": {
                    "mean_tokens_used": avg([s["structured_metadata_files"]["tokens_used"] for s in c_sc]),
                    "mean_decision_recall_all_8": avg([s["structured_metadata_files"]["decision_recall"] for s in c_sc]),
                    "mean_decision_recall_typed_7": avg(
                        [s["structured_metadata_files"]["decision_recall"] for s in c_sc if not s["stress_untyped"]]
                    ),
                    "mean_open_arc_precision": avg([s["structured_metadata_files"]["open_arc_precision"] for s in c_sc]),
                    "latency": p50_p95([s["structured_metadata_files"]["latency_ms"] for s in c_sc]),
                },
                "whitemagic_v10_4": {
                    "mean_decision_recall_all_8": avg([s["whitemagic_v10_4"]["decision_recall"] for s in c_sc]),
                    "mean_decision_recall_typed_7": avg(
                        [s["whitemagic_v10_4"]["decision_recall"] for s in c_sc if not s["stress_untyped"]]
                    ),
                    "mean_open_arc_precision": avg([s["whitemagic_v10_4"]["open_arc_precision"] for s in c_sc]),
                    "new_session_track_routing_rate": avg(
                        [1.0 if s["whitemagic_v10_4"]["new_session_track_routing_ok"] else 0.0 for s in c_sc]
                    ),
                    "cross_session_crystal_rate": avg(
                        [1.0 if s["whitemagic_v10_4"]["cross_session_crystal_surfaced"] else 0.0 for s in c_sc]
                    ),
                    "budget_enforced_rate": avg(
                        [1.0 if s["whitemagic_v10_4"]["budget_enforced"] else 0.0 for s in c_sc]
                    ),
                    "mean_tokens_used": avg([float(s["whitemagic_v10_4"]["tokens_used"]) for s in c_sc]),
                    "latency": p50_p95([s["whitemagic_v10_4"]["latency_ms"] for s in c_sc]),
                },
            },
            "T_CONFLICT_stale_and_conflicting_memory": {
                "scenario_count": len(m_sc),
                "bm25_flat_files": {
                    "top1_current_truth_rate_all_8": avg([s["bm25_flat_files"]["top1_current_truth"] for s in m_sc]),
                    "top1_current_truth_rate_governed_7": avg(
                        [s["bm25_flat_files"]["top1_current_truth"] for s in m_sc if s["use_governed_update"]]
                    ),
                    "mean_unflagged_stale_in_top3": avg(
                        [s["bm25_flat_files"]["unflagged_stale_in_top3"] for s in m_sc]
                    ),
                    "lineage_verifiable_rate": 0.0,
                    "latency": p50_p95([s["bm25_flat_files"]["latency_ms"] for s in m_sc]),
                },
                "structured_supersedes_files_equal_info": {
                    "top1_current_truth_rate_all_8": avg(
                        [s["structured_supersedes_files"]["top1_current_truth"] for s in m_sc]
                    ),
                    "top1_current_truth_rate_governed_7": avg(
                        [
                            s["structured_supersedes_files"]["top1_current_truth"]
                            for s in m_sc
                            if s["use_governed_update"]
                        ]
                    ),
                    "mean_unflagged_stale_in_top3_governed_7": avg(
                        [
                            s["structured_supersedes_files"]["unflagged_stale_in_top3"]
                            for s in m_sc
                            if s["use_governed_update"]
                        ]
                    ),
                    "lineage_verifiable_rate": 0.0,
                    "latency": p50_p95([s["structured_supersedes_files"]["latency_ms"] for s in m_sc]),
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
                "record_addressed_files_equal_info": {
                    "poison_free_and_repaired_in_top3_rate": avg(
                        [s["record_addressed_files"]["poison_free_active_top3"] for s in r_sc]
                    ),
                    "repaired_at_rank1_rate": avg([s["record_addressed_files"]["repaired_at_rank1"] for s in r_sc]),
                    "legitimate_state_preserved_rate": avg(
                        [s["record_addressed_files"]["legitimate_state_preserved"] for s in r_sc]
                    ),
                    "joint_repair_and_preserve_top3_rate": avg(
                        [s["record_addressed_files"]["joint_success_top3"] for s in r_sc]
                    ),
                    "joint_repair_and_preserve_rank1_rate": avg(
                        [s["record_addressed_files"]["joint_success_rank1"] for s in r_sc]
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
            "T_DISCOVERY_authored_cue_guided_migration": {
                "scenario_count": len(d_sc),
                "corpus_records_per_case": [s["corpus_records"] for s in d_sc],
                "legitimate_neighbors_total": sum(s["legitimate_neighbors"] for s in d_sc),
                "equal_information_files": {
                    "mean_target_discovery_recall": avg([s["equal_information_files"]["target_discovery_recall"] for s in d_sc]),
                    "mean_target_discovery_precision": avg([s["equal_information_files"]["target_discovery_precision"] for s in d_sc]),
                    "legitimate_state_preserved_rate": avg([s["equal_information_files"]["legitimate_state_preserved"] for s in d_sc]),
                    "top1_current_truth_rate": avg([s["equal_information_files"]["top1_current_truth"] for s in d_sc]),
                    "end_to_end_success_rate": avg([s["equal_information_files"]["end_to_end_success"] for s in d_sc]),
                },
                "whitemagic_cue_guided_migration": {
                    "mean_target_discovery_recall": avg(
                        [s["whitemagic_cue_guided_migration"]["target_discovery_recall"] for s in d_sc]
                    ),
                    "mean_target_discovery_precision": avg(
                        [s["whitemagic_cue_guided_migration"]["target_discovery_precision"] for s in d_sc]
                    ),
                    "top1_current_truth_rate": avg(
                        [s["whitemagic_cue_guided_migration"]["top1_current_truth"] for s in d_sc]
                    ),
                    "mean_active_stale_in_top3": avg(
                        [float(s["whitemagic_cue_guided_migration"]["active_stale_in_top3"]) for s in d_sc]
                    ),
                    "legitimate_state_preserved_rate": avg(
                        [s["whitemagic_cue_guided_migration"]["legitimate_state_preserved"] for s in d_sc]
                    ),
                    "converging_dag_verified_rate": avg(
                        [s["whitemagic_cue_guided_migration"]["converging_dag_verified"] for s in d_sc]
                    ),
                    "end_to_end_success_rate": avg(
                        [s["whitemagic_cue_guided_migration"]["end_to_end_success"] for s in d_sc]
                    ),
                    "latency": p50_p95([s["whitemagic_cue_guided_migration"]["latency_ms"] for s in d_sc]),
                },
            },
        },
        "documented_failure_traces": failure_traces,
        "families": [cont, conf, rep, disc],
    }


def main() -> int:
    wm_bin = Path(os.environ.get("WM_BINARY", str(DEFAULT_WM_BIN)))
    if not wm_bin.is_file():
        raise SystemExit(f"Pinned wm binary not found at {wm_bin}")
    for family in (CONTINUITY_SCENARIOS, CONFLICT_SCENARIOS, REPAIR_SCENARIOS, DISCOVERY_SCENARIOS):
        if len(family) != 8 or len({scenario["id"] for scenario in family}) != 8:
            raise RuntimeError("Pinned family must retain eight unique scenarios")
    if any(len(sc["obsolete_claims"]) != 2 or len(sc["legitimate_neighbors"]) != 3 for sc in DISCOVERY_SCENARIOS):
        raise RuntimeError("Pinned discovery corpus requires two obsolete and three legitimate records per case")

    CALL_AUDIT.clear()
    BATCH_AUDIT.clear()
    try:
        cont = run_continuity_family(wm_bin)
        conf = run_conflict_family(wm_bin)
        rep = run_repair_family(wm_bin)
        disc = run_discovery_family(wm_bin)
        report = summarize_evaluation(wm_bin, cont, conf, rep, disc)
    finally:
        (HERE / "runtime-call-audit.json").write_text(json.dumps({"calls": CALL_AUDIT, "batches": BATCH_AUDIT}, indent=2) + "\n", encoding="utf-8")

    report["runtime_call_audit_sha256"] = sha256_file(HERE / "runtime-call-audit.json")
    out_json = HERE / "pinned-task-eval-results.json"
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary_by_family"], indent=2, sort_keys=True))
    print("\nDocumented failure traces:", json.dumps(report["documented_failure_traces"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
