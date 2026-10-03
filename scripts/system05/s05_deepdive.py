#!/usr/bin/env python3
"""System 0.5 deep dive on fast-decisions.

1. Cascade economics: per-item 0.5 scores (potion kNN/LogReg) vs Laya; sweep
   confidence/margin thresholds -> coverage, accuracy on covered, and Laya's
   accuracy on the same covered subset.
2. Semantic-cache equivalence: within-surface state pairs (positive = same
   gold, negative = different gold); score with potion cosine, TF-IDF cosine,
   gzip-NCD; report AUC, best-threshold accuracy, and hard-negative rate.
3. Shortlist recall: recall@k of the gold label in the ranked label list.
"""
import gzip
import hashlib
import json
import os
import random
from collections import defaultdict

import numpy as np
from model2vec import StaticModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import normalize

RAW = "/tmp/opencode/s1_raw_probs.jsonl"
ROOT = os.path.expanduser("~/Desktop/trust-without-cloud/fast-decisions")
REFIT = json.load(open("/tmp/opencode/s1_refit_report.json"))
OUT = "/tmp/opencode/s05_deepdive_results.json"
SEED = 20261003


def bucket(k):
    if k <= 2:
        return "2"
    if k <= 5:
        return "3-5"
    if k <= 10:
        return "6-10"
    return "11+"


def split_of(rid):
    return "test" if int(hashlib.sha256(rid.encode()).hexdigest(), 16) % 100 < 30 else "train"


def load_records():
    seen, states = {}, {}
    for line in open(RAW):
        r = json.loads(line)
        if r["gold"] not in r["options"]:
            continue
        domain, idx, _ = r["id"].rsplit(":", 2)
        if (domain, idx) not in states:
            rows = [json.loads(l) for l in open(os.path.join(ROOT, domain + ".jsonl")) if l.strip()]
            states[(domain, idx)] = rows[int(idx)]["input"]
        r["state"] = states[(domain, idx)]
        r["surface"] = f"{domain}/{r['task']}"
        seen[r["id"]] = r
    return list(seen.values())


def laya_probs(r):
    options = r["options"]
    raw = np.array([float(r["probs"].get(o, 0.0)) for o in options])
    t = REFIT["fitted"].get(f"choice:{bucket(len(options))}", 1.0)
    q = np.power(raw, 1.0 / t)
    return q / q.sum() if q.sum() > 0 else np.full(len(options), 1 / len(options))


def score_05(records):
    """Per-test-item potion LogReg and kNN predictions with margins."""
    results = {}
    for model_name in ["minishlab/potion-base-8M", "minishlab/potion-base-32M"]:
        model = StaticModel.from_pretrained(model_name)
        E = normalize(np.asarray(model.encode([r["state"] for r in records])))
        key = model_name.split("/")[-1]
        items = {}
        surfaces = defaultdict(list)
        for i, r in enumerate(records):
            surfaces[r["surface"]].append(i)
        for surface, members in sorted(surfaces.items()):
            tr = [i for i in members if split_of(records[i]["id"]) == "train"]
            te = [i for i in members if split_of(records[i]["id"]) == "test"]
            if len(tr) < 2 or not te:
                continue
            options = sorted(set(records[te[0]]["options"]))
            if any(sorted(records[i]["options"]) != options for i in members):
                continue
            if len(set(records[i]["gold"] for i in tr)) < 2:
                continue
            y_tr = [records[i]["gold"] for i in tr]
            E_tr, E_te = E[tr], E[te]

            clf = LogisticRegression(max_iter=3000)
            clf.fit(E_tr, y_tr)
            classes = list(clf.classes_)
            probs = clf.predict_proba(E_te)

            sims = E_te @ E_tr.T
            k = min(10, len(tr))
            for row_i, (row_p, row_sims) in enumerate(zip(probs, sims)):
                i = te[row_i]
                gold = records[i]["gold"]
                mapping = {label: row_p[classes.index(label)] for label in options if label in classes}
                p = np.array([mapping.get(o, 0.0) for o in options])
                p = p / p.sum() if p.sum() > 0 else np.full(len(options), 1 / len(options))
                order = np.argsort(-p)
                lr = {
                    "label": options[order[0]],
                    "confidence": float(p[order[0]]),
                    "margin": float(p[order[0]] - p[order[1]]) if len(options) > 1 else 1.0,
                    "rank_of_gold": int(np.where(np.array(options)[order] == gold)[0][0]) + 1,
                }
                top = np.argsort(-row_sims)[:k]
                votes = defaultdict(float)
                for t in top:
                    votes[y_tr[t]] += float(max(row_sims[t], 0.0)) or 1e-6
                scored = np.array([votes.get(o, 0.0) for o in options])
                scored = scored / scored.sum()
                order = np.argsort(-scored)
                knn = {
                    "label": options[order[0]],
                    "confidence": float(scored[order[0]]),
                    "margin": float(scored[order[0]] - scored[order[1]]) if len(options) > 1 else 1.0,
                    "rank_of_gold": int(np.where(np.array(options)[order] == gold)[0][0]) + 1,
                }
                items[records[i]["id"]] = {"logreg": lr, "knn": knn}
        results[key] = items
    return results


def cascade_table(records, scores, method):
    """Sweep thresholds; report coverage and accuracy; Laya accuracy on same subset."""
    rows = []
    test = [r for r in records if split_of(r["id"]) == "test" and r["id"] in scores]
    if not test:
        return rows
    laya_ok = {}
    for r in test:
        p = laya_probs(r)
        laya_ok[r["id"]] = r["options"][int(p.argmax())] == r["gold"]
    for signal in ["confidence", "margin"]:
        values = np.array([scores[r["id"]][method][signal] for r in test])
        for tau in [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95]:
            covered = [r for r in test if scores[r["id"]][method][signal] >= tau]
            if not covered:
                continue
            acc05 = np.mean([scores[r["id"]][method]["label"] == r["gold"] for r in covered])
            acc_laya = np.mean([laya_ok[r["id"]] for r in covered])
            rows.append({
                "method": method, "signal": signal, "tau": tau,
                "coverage": len(covered) / len(test),
                "acc_05": float(acc05), "acc_laya_on_covered": float(acc_laya),
            })
    return rows


def cache_pairs(records, E8, E32):
    rng = random.Random(SEED)
    surfaces = defaultdict(list)
    for i, r in enumerate(records):
        surfaces[r["surface"]].append(i)
    positives, negatives = [], []
    for members in surfaces.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                pair = (members[a], members[b])
                if records[pair[0]]["gold"] == records[pair[1]]["gold"]:
                    positives.append(pair)
                else:
                    negatives.append(pair)
    rng.shuffle(positives)
    rng.shuffle(negatives)
    positives = positives[:1500]
    negatives = negatives[:3000]

    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    T = normalize(tfidf.fit_transform([r["state"] for r in records]))
    compressed = {i: len(gzip.compress(records[i]["state"].encode())) for i in range(len(records))}

    def ncd(i, j):
        xy = " ".join([records[i]["state"], records[j]["state"]])
        c_xy = len(gzip.compress(xy.encode()))
        return (c_xy - min(compressed[i], compressed[j])) / max(compressed[i], compressed[j], 1)

    scores = {k: {"pos": [], "neg": []} for k in ["potion8", "potion32", "tfidf", "gzip"]}
    for label, pairs in [("pos", positives), ("neg", negatives)]:
        for i, j in pairs:
            scores["potion8"][label].append(float(E8[i] @ E8[j]))
            scores["potion32"][label].append(float(E32[i] @ E32[j]))
            scores["tfidf"][label].append(float((T[i] @ T[j].T).toarray()[0, 0]))
            scores["gzip"][label].append(-ncd(i, j))  # higher = more similar

    table = {}
    for name, s in scores.items():
        y = np.array([1] * len(s["pos"]) + [0] * len(s["neg"]))
        x = np.array(s["pos"] + s["neg"])
        auc = float(roc_auc_score(y, x))
        best = max(
            ((t, float(np.mean(x[y == 1] >= t) * 0.5 + np.mean(x[y == 0] < t) * 0.5)) for t in np.unique(np.round(x, 3))),
            key=lambda p: p[1],
        )
        hard = float(np.mean(np.array(s["neg"]) > 0.95))
        table[name] = {"auc": auc, "balanced_acc_at": best[0], "balanced_acc": best[1],
                       "hard_negative_rate_sim_gt_0.95": hard,
                       "n_pos": len(s["pos"]), "n_neg": len(s["neg"])}
    return table


def main():
    records = load_records()
    scores = score_05(records)
    e8_model = StaticModel.from_pretrained("minishlab/potion-base-8M")
    E8 = normalize(np.asarray(e8_model.encode([r["state"] for r in records])))
    e32_model = StaticModel.from_pretrained("minishlab/potion-base-32M")
    E32 = normalize(np.asarray(e32_model.encode([r["state"] for r in records])))

    out = {"cascade": [], "cache": {}, "recall": {}}
    for model_key in ["potion-base-8M", "potion-base-32M"]:
        for method in ["logreg", "knn"]:
            out["cascade"].extend(cascade_table(records, scores[model_key], method))
        for method in ["logreg", "knn"]:
            ranks = np.array([v[method]["rank_of_gold"] for v in scores[model_key].values()])
            out["recall"][f"{model_key}/{method}"] = {
                f"recall@{k}": float(np.mean(ranks <= k)) for k in [1, 3, 5, 10, 16]
            }

    out["cache"] = cache_pairs(records, E8, E32)

    print("== cascade (coverage vs accuracy) ==")
    for row in out["cascade"]:
        print(f"{row['method']:7s} {row['signal']:10s} tau={row['tau']:.2f} "
              f"coverage={row['coverage']:.2f} acc05={row['acc_05']:.3f} "
              f"acc_laya_same={row['acc_laya_on_covered']:.3f}")
    print("\n== shortlist recall ==")
    for key, value in out["recall"].items():
        print(key, value)
    print("\n== semantic cache equivalence ==")
    for key, value in out["cache"].items():
        print(f"{key:8s} AUC={value['auc']:.3f} bal_acc={value['balanced_acc']:.3f} "
              f"@t={value['balanced_acc_at']:.3f} hard_neg_rate={value['hard_negative_rate_sim_gt_0.95']:.3f}")

    json.dump(out, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
