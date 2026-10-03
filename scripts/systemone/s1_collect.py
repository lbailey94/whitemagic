#!/usr/bin/env python3
"""Collect raw Laya probabilities (temperature disabled, t=1) on fast-decisions.

One HTTP request per state; all single-label classifications of that state are
batched into one forward pass. Writes JSONL with per-question raw probabilities.
Resumable: existing ids in the output file are skipped.
"""
import argparse
import glob
import json
import os
import random
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/Desktop/trust-without-cloud/fast-decisions")
URL = "http://127.0.0.1:8088/api/predict"


def load_sample(per_file, seed):
    rng = random.Random(seed)
    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.jsonl"))):
        domain = os.path.basename(path)[:-6]
        rows = [json.loads(line) for line in open(path) if line.strip()]
        indexed = list(enumerate(rows))
        rng.shuffle(indexed)
        for idx, row in indexed[:per_file]:
            questions = []
            metas = []
            for i, classification in enumerate(row["output"]["classifications"]):
                if classification.get("multi_label"):
                    continue
                questions.append({
                    "id": f"q{i}",
                    "type": "choice",
                    "instructions": f"Which {classification['task']} label best applies to this message?",
                    "criteria": classification["labels"],
                })
                metas.append({
                    "domain": domain,
                    "task": classification["task"],
                    "gold": classification["true_label"][0],
                    "k": len(classification["labels"]),
                    "options": classification["labels"],
                })
            items.append({
                "id": f"{domain}:{idx}",
                "state": row["input"],
                "questions": questions,
                "metas": metas,
            })
    return items


def post(state, questions, timeout=900, retries=2):
    body = json.dumps({"state": state, "questions": questions}).encode()
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise RuntimeError(f"request failed: {last}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-file", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--out", default="/tmp/opencode/s1_raw_probs.jsonl")
    args = parser.parse_args()

    items = load_sample(args.per_file, args.seed)
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            line = line.strip()
            if line:
                done.add(json.loads(line)["id"])

    todo = [it for it in items if it["id"] not in done]
    print(f"items={len(items)} done={len(done)} todo={len(todo)}", flush=True)

    started = time.time()
    written = 0
    with open(args.out, "a") as out:
        for n, item in enumerate(todo, 1):
            if not item["questions"]:
                continue
            try:
                data = post(item["state"], item["questions"])
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL {item['id']}: {exc}", flush=True)
                continue
            answers = data.get("answers", {})
            for i, meta in enumerate(item["metas"]):
                answer = answers.get(f"q{i}", {})
                probs = answer.get("probabilities", {})
                if not probs:
                    continue
                record = {
                    "id": f"{item['id']}:{i}",
                    "domain": meta["domain"],
                    "task": meta["task"],
                    "k": meta["k"],
                    "gold": meta["gold"],
                    "options": meta["options"],
                    "probs": probs,
                    "act": (answer.get("rl_agent") or {}).get("act_probability"),
                }
                out.write(json.dumps(record) + "\n")
                written += 1
            out.flush()
            if n % 10 == 0 or n == len(todo):
                elapsed = time.time() - started
                rate = elapsed / n
                eta = rate * (len(todo) - n)
                print(f"  {n}/{len(todo)} states | {rate:.1f}s/state | ETA {eta/60:.1f} min", flush=True)

    print(f"done: {written} question records appended to {args.out}", flush=True)


if __name__ == "__main__":
    main()
