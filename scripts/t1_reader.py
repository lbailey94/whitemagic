#!/usr/bin/env python3
"""T1 reader runner — QA generation over retrieved context via opencode.

Consumes ``retrieval.jsonl`` (one question per line; see
T1_PARALLEL_SESSIONS_2026-09-22.md for the contract), builds the reader
prompt, runs ``opencode run -m <model> --format json --pure``, and appends
``answers.jsonl`` with provenance. Resumable; local-only plumbing — egress is
public benchmark artifacts only (question + retrieved context + answer).

Usage:
  python3 scripts/t1_reader.py \
      --retrieval benchmarks/runs/t1/retrieval.jsonl \
      --out benchmarks/runs/t1/answers.jsonl \
      --model opencode-go/gpt-5.6-luna \
      [--limit N] [--offset N] [--dry-run] [--fake] [--timeout 180]

  --dry-run  print the prompt hash + a preview; no model call, no writes
  --fake     write deterministic stub answers (plumbing tests, no egress)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROMPT_TEMPLATE = """You are answering a question from a long-term memory benchmark.
Use ONLY the retrieved context below. If the context does not contain the
answer, say "I don't know" rather than guessing.

Question:
{question}

Retrieved context (ranked):
{context}

Answer concisely (one or two sentences). Do not explain your reasoning."""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def done_pairs(path: Path, model: str) -> set[tuple[str, str]]:
    """Successful (question_id, prompt_sha256) pairs for this model.

    Per-question keys, not one global hash: a resume must skip exactly the
    questions whose prompt is unchanged, and retry errored rows.
    """
    if not path.exists():
        return set()
    done: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            reader = row.get("reader") or {}
            if row.get("error") is None and reader.get("model") == model:
                done.add((row.get("question_id"), reader.get("prompt_sha256")))
    return done


def build_prompt(row: dict) -> str:
    context = "\n\n".join(
        f"[{r.get('rank', i + 1)}] {r.get('content', '')}"
        for i, r in enumerate(row.get("retrieved", []))
    )
    if not context:
        context = "(no context retrieved)"
    return PROMPT_TEMPLATE.format(question=row.get("question", ""), context=context)


def call_opencode(model: str, prompt: str, timeout: int) -> tuple[str, dict]:
    """Run one headless model call; return (text, meta)."""
    proc = subprocess.run(
        ["opencode", "run", "-m", model, "--format", "json", "--pure", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(
            f"opencode exited {proc.returncode}: {(proc.stderr or '').strip()[:300]}"
        )
    text_parts: list[str] = []
    meta: dict = {"cost": None, "tokens": None, "errors": []}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        etype = event.get("type")
        if etype == "text":
            text = (event.get("part") or {}).get("text")
            if text:
                text_parts.append(text)
        elif etype == "step_finish":
            part = event.get("part") or {}
            meta["cost"] = part.get("cost")
            meta["tokens"] = part.get("tokens")
        elif etype == "error":
            meta["errors"].append(str((event.get("error") or {}).get("data", {}).get("message", ""))[:200])
    if not text_parts and meta["errors"]:
        raise RuntimeError(f"model error: {meta['errors'][0]}")
    return "".join(text_parts).strip(), meta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="opencode-go/gpt-5.6-luna")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    retrieval_path = Path(args.retrieval)
    out_path = Path(args.out)
    rows = load_jsonl(retrieval_path)
    if args.offset:
        rows = rows[args.offset :]
    if args.limit is not None:
        rows = rows[: args.limit]

    prompt_shas = {sha256(build_prompt(r)) for r in rows} if rows else set()
    prompt_sha = next(iter(prompt_shas)) if len(prompt_shas) == 1 else "per-question"
    done = done_pairs(out_path, args.model)

    if args.dry_run:
        for row in rows[:3]:
            prompt = build_prompt(row)
            print(
                f"[dry-run] {row.get('question_id')} "
                f"prompt_sha={sha256(prompt)[:12]} prompt_chars={len(prompt)} "
                f"retrieved={len(row.get('retrieved', []))}"
            )
        skipped = sum(1 for r in rows if (r.get("question_id"), sha256(build_prompt(r))) in done)
        print(f"[dry-run] {len(rows)} questions, {skipped} already answered")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    with out_path.open("a", encoding="utf-8") as out:
        for row in rows:
            qid = row.get("question_id")
            prompt = build_prompt(row)
            if (qid, sha256(prompt)) in done:
                skipped += 1
                continue
            started = datetime.now(timezone.utc).isoformat()
            entry = {
                "question_id": qid,
                "answer_text": None,
                "reader": {
                    "model": args.model,
                    "prompt_sha256": sha256(prompt),
                    "temperature": 0,
                    "generated_at": started,
                    "tokens": None,
                    "cost_usd": None,
                },
                "retrieval_ref": str(retrieval_path),
                "error": None,
            }
            try:
                if args.fake:
                    text, meta = f"FAKE answer for {qid}", {}
                else:
                    text, meta = call_opencode(args.model, prompt, args.timeout)
                entry["answer_text"] = text
                entry["reader"]["tokens"] = meta.get("tokens")
                entry["reader"]["cost_usd"] = meta.get("cost")
            except Exception as exc:  # noqa: BLE001 — recorded per row, never fatal
                entry["error"] = str(exc)[:500]
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.flush()
            written += 1
            print(
                f"[{written}] {qid} "
                + ("ERROR: " + entry["error"] if entry["error"] else "ok")
                + (f" · {time.strftime('%H:%M:%S')}" if not args.fake else "")
            )
    print(f"reader done: {written} written to {out_path} ({skipped} skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
