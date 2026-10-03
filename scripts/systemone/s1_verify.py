#!/usr/bin/env python3
"""Verify the refit end-to-end: served probabilities must match the offline
simulation normalize(p_raw ** (1/t_fit)) for held-out items, and recompute ECE
on served probabilities.
"""
import glob
import json
import math
import os
import urllib.request

import numpy as np

ROOT = os.path.expanduser("~/Desktop/trust-without-cloud/fast-decisions")
URL = "http://127.0.0.1:8088/api/predict"
REPORT = "/tmp/opencode/s1_refit_report.json"

report = json.load(open(REPORT))
fitted = report["fitted"]


def bucket(k):
    if k <= 2:
        return "2"
    if k <= 5:
        return "3-5"
    if k <= 10:
        return "6-10"
    return "11+"


def rebuild(record_id):
    domain, idx, qidx = record_id.rsplit(":", 2)
    rows = [json.loads(line) for line in open(os.path.join(ROOT, domain + ".jsonl")) if line.strip()]
    row = rows[int(idx)]
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
            "gold": classification["true_label"][0],
            "options": classification["labels"],
            "k": len(classification["labels"]),
        })
    return row["input"], questions, metas[int(qidx)]


def post(state, questions):
    body = json.dumps({"state": state, "questions": questions}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.loads(resp.read())


def simulate(raw, options, temperature):
    p = np.array([max(float(raw.get(o, 0.0)), 0.0) for o in options])
    q = np.power(p, 1.0 / temperature)
    return q / q.sum()


records = [json.loads(line) for line in open("/tmp/opencode/s1_raw_probs.jsonl") if line.strip()]
seen, picked = set(), []
for record in records:
    b = bucket(record["k"])
    if b in seen:
        continue
    seen.add(b)
    picked.append(record)

print(f"verifying {len(picked)} held-out items (one per bucket)")
ece_conf, ece_ok = [], []
for record in picked:
    state, questions, meta = rebuild(record["id"])
    served = post(state, questions)
    qidx = int(record["id"].rsplit(":", 1)[1])
    answer = served["answers"].get(f"q{qidx}", {})
    served_probs = np.array([float(answer["probabilities"].get(o, 0.0)) for o in meta["options"]])
    expected = simulate(record["probs"], meta["options"], fitted[f"choice:{bucket(record['k'])}"])
    drift = float(np.max(np.abs(served_probs - expected)))
    gold = meta["options"].index(meta["gold"])
    top = int(np.argmax(served_probs))
    ece_conf.append(float(served_probs[top]))
    ece_ok.append(1.0 if top == gold else 0.0)
    print(f"  {record['id']:28s} k={record['k']:2d} max_drift={drift:.4f} "
          f"gold_p={served_probs[gold]:.4f} top1={'OK' if top == gold else 'MISS'}")

conf = np.array(ece_conf)
ok = np.array(ece_ok)
print(f"served top-1 accuracy={ok.mean():.2f} mean_conf={conf.mean():.2f} on this tiny slice")
