#!/usr/bin/env python3
"""T1 judge runner — verdicts over reader answers via opencode.

Consumes ``answers.jsonl`` (reader output) plus the benchmark dataset (for the
question + reference answer), runs a strict-JSON judge prompt via
``opencode run -m <model> --format json --pure``, and appends
``verdicts.jsonl`` with provenance. ``--summarize`` reports accuracy,
abstention, and (with two files) the variance delta.

Egress is public benchmark artifacts only: question + reference + candidate
answer. No user stores, no WM memory content.

Usage:
  python3 scripts/t1_judge.py \
      --answers benchmarks/runs/t1/answers.jsonl \
      --dataset benchmarks/data/longmemeval_s/cleaned/longmemeval_s_cleaned.json \
      --out benchmarks/runs/t1/verdicts-primary.jsonl \
      --model opencode-go/deepseek-v4.1-flash --role primary --variant strict \
      [--limit N] [--offset N] [--dry-run] [--fake] [--timeout 180]

  python3 scripts/t1_judge.py --summarize verdicts-primary.jsonl verdicts-variance.jsonl \
      [--dataset ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STRICT_TEMPLATE = """You are grading a model's answer against the reference answer for a
long-term memory benchmark question. Return STRICT JSON only — no prose, no markdown:
{{"correct": true|false, "abstained": true|false, "reason": "<one short sentence>"}}

Question:
{question}

Reference answer:
{reference}

Model answer:
{candidate}

Rules:
- "correct" means the model answer agrees with the reference in substance
  (names, numbers, and facts must match).
- "abstained" means the model said it does not know or cannot answer.
- If the reference answer is "I don't know" (abstention question), correct
  means the model abstained rather than inventing an answer."""

COVERAGE_TEMPLATE = """Grade factual agreement between a model answer and a reference answer
for a long-term memory benchmark question. Ignore phrasing, length, and style;
compare only the facts (names, numbers, dates, entities).

Return STRICT JSON only — no prose, no markdown:
{{"correct": true|false, "abstained": true|false, "reason": "<one short sentence>"}}

Question:
{question}

Reference answer:
{reference}

Model answer:
{candidate}

If the reference answer is "I don't know", correct means the model abstained."""

TEMPLATES = {"strict": STRICT_TEMPLATE, "coverage": COVERAGE_TEMPLATE}


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


def load_dataset(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["question_id"]: row for row in data}


def build_prompt(template: str, question: str, reference: str, candidate: str) -> str:
    return template.format(question=question, reference=reference, candidate=candidate)


def done_pairs(path: Path, model: str, role: str, variant: str) -> set[tuple[str, str]]:
    """Successful (question_id, prompt_sha256) pairs for this judge config."""
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
            judge = row.get("judge") or {}
            if (
                row.get("error") is None
                and row.get("verdict")
                and judge.get("model") == model
                and judge.get("role") == role
                and judge.get("variant") == variant
            ):
                done.add((row.get("question_id"), judge.get("prompt_sha256")))
    return done


def call_opencode(model: str, prompt: str, timeout: int) -> tuple[str, dict]:
    proc = subprocess.run(
        ["opencode", "run", "-m", model, "--format", "json", "--pure", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
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
            meta["errors"].append(
                str((event.get("error") or {}).get("data", {}).get("message", ""))[:200]
            )
    if not text_parts and meta["errors"]:
        raise RuntimeError(f"model error: {meta['errors'][0]}")
    return "".join(text_parts).strip(), meta


def parse_verdict(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object in judge output: {text[:160]!r}")
    verdict = json.loads(text[start : end + 1])
    if not isinstance(verdict.get("correct"), bool) or not isinstance(
        verdict.get("abstained"), bool
    ):
        raise ValueError(f"verdict missing boolean fields: {verdict!r}")
    return verdict


def summarize(paths: list[Path], dataset_path: Path | None) -> int:
    dataset = load_dataset(dataset_path) if dataset_path else {}
    verdicts_by_file: list[dict[str, dict]] = []
    for path in paths:
        rows = load_jsonl(path)
        by_qid = {r["question_id"]: r for r in rows if r.get("verdict")}
        verdicts_by_file.append(by_qid)
        errors = sum(1 for r in rows if r.get("error"))
        correct = sum(1 for r in by_qid.values() if r["verdict"]["correct"])
        abstained = sum(1 for r in by_qid.values() if r["verdict"]["abstained"])
        n = len(by_qid)
        acc = correct / n if n else 0.0
        print(f"{path.name}: n={n} correct={correct} accuracy={acc:.3f} abstained={abstained} errors={errors}")
        if dataset:
            abs_qids = [q for q in by_qid if q.endswith("_abs")]
            abs_correct = sum(1 for q in abs_qids if by_qid[q]["verdict"]["correct"])
            if abs_qids:
                print(
                    f"  abstention subset: n={len(abs_qids)} correct={abs_correct} "
                    f"accuracy={abs_correct / len(abs_qids):.3f}"
                )
    if len(verdicts_by_file) >= 2:
        first, second = verdicts_by_file[0], verdicts_by_file[1]
        shared = set(first) & set(second)
        disagree = [q for q in shared if first[q]["verdict"]["correct"] != second[q]["verdict"]["correct"]]
        print(
            f"variance: {len(shared)} shared · {len(disagree)} disagreements "
            f"({len(disagree) / len(shared):.3f})" if shared else "variance: no shared rows"
        )
        for q in disagree[:10]:
            print(f"  {q}: primary={first[q]['verdict']['correct']} variance={second[q]['verdict']['correct']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers")
    parser.add_argument("--dataset")
    parser.add_argument("--out")
    parser.add_argument("--model", default="opencode-go/deepseek-v4.1-flash")
    parser.add_argument("--role", choices=["primary", "variance"], default="primary")
    parser.add_argument("--variant", choices=sorted(TEMPLATES), default="strict")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fake", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--summarize", nargs="*")
    args = parser.parse_args()

    if args.summarize is not None:
        if not args.summarize:
            parser.error("--summarize needs at least one verdicts file")
        return summarize([Path(p) for p in args.summarize], Path(args.dataset) if args.dataset else None)

    if not (args.answers and args.dataset and args.out):
        parser.error("--answers, --dataset, and --out are required (or use --summarize)")

    answers = load_jsonl(Path(args.answers))
    dataset = load_dataset(Path(args.dataset))
    if args.offset:
        answers = answers[args.offset :]
    if args.limit is not None:
        answers = answers[: args.limit]

    template = TEMPLATES[args.variant]
    out_path = Path(args.out)
    done = done_pairs(out_path, args.model, args.role, args.variant)

    def prompt_for(answer: dict) -> str:
        ref = dataset.get(answer["question_id"], {})
        return build_prompt(
            template,
            ref.get("question", ""),
            ref.get("answer", ""),
            answer.get("answer_text") or "",
        )

    if args.dry_run:
        for answer in answers[:3]:
            prompt = prompt_for(answer)
            print(
                f"[dry-run] {answer['question_id']} prompt_sha={sha256(prompt)[:12]} "
                f"prompt_chars={len(prompt)} abstention={answer['question_id'].endswith('_abs')}"
            )
        skipped = sum(1 for a in answers if (a["question_id"], sha256(prompt_for(a))) in done)
        print(f"[dry-run] {len(answers)} answers, {skipped} already judged")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    with out_path.open("a", encoding="utf-8") as out:
        for answer in answers:
            qid = answer["question_id"]
            prompt = prompt_for(answer)
            if (qid, sha256(prompt)) in done:
                skipped += 1
                continue
            entry = {
                "question_id": qid,
                "judge": {
                    "role": args.role,
                    "model": args.model,
                    "variant": args.variant,
                    "prompt_sha256": sha256(prompt),
                    "temperature": 0,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "tokens": None,
                    "cost_usd": None,
                },
                "verdict": None,
                "error": None,
            }
            try:
                if answer.get("error"):
                    raise ValueError(f"reader error: {answer['error'][:120]}")
                if args.fake:
                    text, meta = '{"correct": true, "abstained": false, "reason": "fake"}', {}
                else:
                    text, meta = call_opencode(args.model, prompt, args.timeout)
                try:
                    entry["verdict"] = parse_verdict(text)
                except ValueError:
                    # one strict retry, then record the failure
                    if args.fake:
                        raise
                    retry_prompt = prompt + "\n\nReturn ONLY the JSON object."
                    text, meta = call_opencode(args.model, retry_prompt, args.timeout)
                    entry["verdict"] = parse_verdict(text)
                entry["judge"]["tokens"] = meta.get("tokens")
                entry["judge"]["cost_usd"] = meta.get("cost")
            except Exception as exc:  # noqa: BLE001 — recorded per row, never fatal
                entry["error"] = str(exc)[:500]
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            out.flush()
            written += 1
            status = "ERROR: " + entry["error"] if entry["error"] else (
                "correct" if entry["verdict"]["correct"] else "incorrect"
            )
            print(f"[{written}] {qid} {status}")
    print(f"judge done: {written} written to {out_path} ({skipped} skipped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
