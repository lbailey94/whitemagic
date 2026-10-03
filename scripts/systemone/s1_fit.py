#!/usr/bin/env python3
"""Fit one temperature per (choice, option-count) bucket from raw probabilities.

Input: JSONL of raw (t=1) Laya probabilities collected by s1_collect.py.
Method: q(t) = normalize(p_raw ** (1/t)); fit t by minimizing train NLL,
report accuracy / NLL / Brier / ECE before (raw, shipped) and after (fit)
on a deterministic 70/30 split.
"""
import hashlib
import json
import math
import os
from collections import defaultdict

import numpy as np

DATA = "/tmp/opencode/s1_raw_probs.jsonl"
CONFIG = "/home/lucas/tools/laya/models/laya-base/rl_agent_config.json.shipped.bak"
OUT = "/tmp/opencode/s1_refit_report.json"

BUCKETS = ["2", "3-5", "6-10", "11+"]


def bucket(k):
    if k <= 2:
        return "2"
    if k <= 5:
        return "3-5"
    if k <= 10:
        return "6-10"
    return "11+"


def load_records():
    seen = {}
    for line in open(DATA):
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record["gold"] not in record["options"]:
            continue
        seen[record["id"]] = record
    return list(seen.values())


def split_of(record):
    digest = hashlib.sha256(record["id"].encode()).hexdigest()
    return "test" if int(digest, 16) % 100 < 30 else "train"


def distribution(raw, options, temperature):
    p = np.array([max(float(raw.get(option, 0.0)), 0.0) for option in options], dtype=float)
    if p.sum() <= 0:
        return np.full(len(options), 1.0 / len(options))
    with np.errstate(divide="ignore"):
        q = np.power(p, 1.0 / temperature)
    q = np.where(np.isfinite(q), q, 0.0)
    total = q.sum()
    return q / total if total > 0 else np.full(len(options), 1.0 / len(options))


def evaluate(records, temperature):
    nll, brier, conf, correct = [], [], [], []
    for record in records:
        q = distribution(record["probs"], record["options"], temperature)
        gold = record["options"].index(record["gold"])
        p_gold = max(float(q[gold]), 1e-12)
        nll.append(-math.log(p_gold))
        target = np.zeros(len(q))
        target[gold] = 1.0
        brier.append(float(np.sum((q - target) ** 2)))
        top = int(np.argmax(q))
        conf.append(float(q[top]))
        correct.append(1.0 if top == gold else 0.0)

    conf = np.array(conf)
    correct = np.array(correct)
    ece = 0.0
    bins = np.clip((conf * 10).astype(int), 0, 9)
    for b in range(10):
        mask = bins == b
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())

    return {
        "n": len(records),
        "accuracy": float(correct.mean()),
        "nll": float(np.mean(nll)),
        "brier": float(np.mean(brier)),
        "ece": float(ece),
    }


def fit_temperature(train_records):
    grid = np.geomspace(0.15, 30.0, 120)
    scores = [evaluate(train_records, t)["nll"] for t in grid]
    best = grid[int(np.argmin(scores))]
    span = best * 0.15
    fine = np.linspace(max(0.05, best - span), best + span, 61)
    scores = [evaluate(train_records, t)["nll"] for t in fine]
    return float(fine[int(np.argmin(scores))])


def main():
    shipped = json.load(open(CONFIG))
    t_old_map = {
        f"choice:{b}": float(shipped["temperature_by_options"].get(f"choice:{b}", shipped["temperature"][0]))
        for b in BUCKETS
    }

    records = load_records()
    grouped = defaultdict(lambda: {"train": [], "test": []})
    for record in records:
        grouped[bucket(record["k"])][split_of(record)].append(record)

    report = {"n_records": len(records), "buckets": {}, "fitted": {}}
    print(f"{'bucket':7s} {'n_tr':>5s} {'n_te':>5s} {'t_old':>7s} {'t_fit':>7s} "
          f"{'acc':>6s} | {'NLL raw':>8s} {'ship':>8s} {'fit':>8s} | {'ECE raw':>8s} {'ship':>8s} {'fit':>8s}")
    for b in BUCKETS:
        train, test = grouped[b]["train"], grouped[b]["test"]
        if not train or not test:
            continue
        t_old = t_old_map[f"choice:{b}"]
        t_fit = fit_temperature(train)
        report["buckets"][b] = {
            "n_train": len(train),
            "n_test": len(test),
            "t_old": t_old,
            "t_fit": t_fit,
            "test": {
                "raw": evaluate(test, 1.0),
                "shipped": evaluate(test, t_old),
                "fit": evaluate(test, t_fit),
            },
        }
        report["fitted"][f"choice:{b}"] = t_fit
        row = report["buckets"][b]["test"]
        print(f"{b:7s} {len(train):5d} {len(test):5d} {t_old:7.3f} {t_fit:7.3f} "
              f"{row['fit']['accuracy']:6.3f} | {row['raw']['nll']:8.3f} {row['shipped']['nll']:8.3f} "
              f"{row['fit']['nll']:8.3f} | {row['raw']['ece']:8.3f} {row['shipped']['ece']:8.3f} "
              f"{row['fit']['ece']:8.3f}")

    json.dump(report, open(OUT, "w"), indent=2)
    print(f"\nfitted temperatures: {json.dumps(report['fitted'])}")
    print(f"report: {OUT}")


if __name__ == "__main__":
    main()
