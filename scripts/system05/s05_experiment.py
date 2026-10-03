#!/usr/bin/env python3
"""System 0.5 bake-off on fast-decisions (625 choice questions, 425 states).

Methods, all on the same deterministic 70/30 split per decision surface
(domain, task, option-set):
  - potion-base-8M  + kNN (k=10, similarity-weighted)
  - potion-base-8M  + logistic regression
  - potion-base-32M + kNN / logistic regression
  - TF-IDF + logistic regression
  - gzip+NCD + kNN (parameter-free)
  - Laya zero-shot (raw t=1 probabilities, refit temperatures applied)
"""
import gzip
import hashlib
import json
import math
import os
import time
from collections import defaultdict

import numpy as np
from model2vec import StaticModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import normalize

RAW = "/tmp/opencode/s1_raw_probs.jsonl"
ROOT = os.path.expanduser("~/Desktop/trust-without-cloud/fast-decisions")
REFIT = json.load(open("/tmp/opencode/s1_refit_report.json"))
OUT = "/tmp/opencode/s05_fastdecisions_results.json"


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
    seen = {}
    states = {}
    for line in open(RAW):
        record = json.loads(line)
        if record["gold"] not in record["options"]:
            continue
        domain, idx, _ = record["id"].rsplit(":", 2)
        if (domain, idx) not in states:
            rows = [json.loads(l) for l in open(os.path.join(ROOT, domain + ".jsonl")) if l.strip()]
            states[(domain, idx)] = rows[int(idx)]["input"]
        record["state"] = states[(domain, idx)]
        record["surface"] = f"{domain}/{record['task']}"
        seen[record["id"]] = record
    return list(seen.values())


def ece(conf, correct, bins=10):
    conf = np.asarray(conf)
    correct = np.asarray(correct, dtype=float)
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        mask = (conf > lo) & (conf <= hi) if b else (conf <= hi)
        if mask.any():
            total += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(total)


def metrics(preds, probs_gold=None, conf=None):
    n = len(preds)
    acc = sum(preds) / n
    out = {"n": n, "accuracy": acc}
    if probs_gold is not None:
        out["nll"] = float(-np.mean(np.log(np.clip(probs_gold, 1e-12, 1))))
        out["ece"] = ece(conf, preds)
    return out


def knn_predict(E_train, y_train, E_test, options, k=10):
    sims = E_test @ E_train.T
    k = min(k, E_train.shape[0])
    preds, probs_gold, confs = [], [], []
    option_index = {label: i for i, label in enumerate(options)}
    for row, sim in zip(E_test, sims):
        top = np.argsort(-sim)[:k]
        weights = np.clip(sim[top], 0, None)
        votes = defaultdict(float)
        for idx, weight in zip(top, weights):
            votes[y_train[idx]] += float(weight if weight > 0 else 1e-6)
        total = sum(votes.values())
        p = np.array([votes.get(label, 0.0) / total for label in options])
        preds.append(option_index.get(max(votes, key=votes.get), 0))
        probs_gold.append(p[option_index[record_gold] ] if False else 0.0)
        confs.append(float(p.max()))
    return preds


def run_embedding_methods(name, E, records, idx_train, idx_test, results):
    y = np.array([r["gold"] for r in records])
    surfaces = defaultdict(list)
    for i in range(len(records)):
        surfaces[records[i]["surface"]].append(i)

    knn_preds, knn_gold_p, knn_conf = [], [], []
    lr_preds, lr_gold_p, lr_conf = [], [], []
    y_true = []
    for surface, members in sorted(surfaces.items()):
        tr = [i for i in members if i in idx_train]
        te = [i for i in members if i in idx_test]
        if not tr or not te:
            continue
        options = sorted(set(records[te[0]]["options"]))
        for i in te:
            if sorted(records[i]["options"]) != options:
                tr = []
                break
        if not tr:
            continue
        E_tr, E_te = E[tr], E[te]
        y_tr = [records[i]["gold"] for i in tr]
        gold_idx = []
        for i in te:
            gold_idx.append(options.index(records[i]["gold"]))

        sims = E_te @ E_tr.T
        k = min(10, len(tr))
        for row_sims, gold in zip(sims, gold_idx):
            top = np.argsort(-row_sims)[:k]
            votes = defaultdict(float)
            for t in top:
                votes[y_tr[t]] += float(max(row_sims[t], 0.0)) or 1e-6
            scored = np.array([votes.get(o, 0.0) for o in options])
            total = scored.sum() or 1.0
            p = scored / total
            knn_preds.append(int(p.argmax()) == gold)
            knn_gold_p.append(max(p[gold], 1e-12))
            knn_conf.append(float(p.max()))

        clf = LogisticRegression(max_iter=3000)
        clf.fit(E_tr, y_tr)
        probs = clf.predict_proba(E_te)
        classes = list(clf.classes_)
        for row_p, gold in zip(probs, gold_idx):
            mapping = {label: row_p[classes.index(label)] for label in options if label in classes}
            p = np.array([mapping.get(o, 0.0) for o in options])
            s = p.sum()
            p = p / s if s > 0 else np.full(len(options), 1 / len(options))
            lr_preds.append(int(p.argmax()) == gold)
            lr_gold_p.append(max(p[gold], 1e-12))
            lr_conf.append(float(p.max()))

        y_true.extend(gold_idx)

    results[name + "/knn"] = metrics(knn_preds, knn_gold_p, knn_conf)
    results[name + "/logreg"] = metrics(lr_preds, lr_gold_p, lr_conf)
    return y_true


def run_baselines(records, idx_train, idx_test, results):
    surfaces = defaultdict(list)
    for i in range(len(records)):
        surfaces[records[i]["surface"]].append(i)

    tf_preds, gz_preds = [], []
    tf_gold_p, tf_conf = [], []
    for surface, members in sorted(surfaces.items()):
        tr = [i for i in members if i in idx_train]
        te = [i for i in members if i in idx_test]
        if not tr or not te:
            continue
        options = sorted(set(records[te[0]]["options"]))
        if any(sorted(records[i]["options"]) != options for i in members):
            continue
        y_tr = [records[i]["gold"] for i in tr]
        gold_idx = [options.index(records[i]["gold"]) for i in te]

        texts_tr = [records[i]["state"] for i in tr]
        texts_te = [records[i]["state"] for i in te]

        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        X_tr = vec.fit_transform(texts_tr)
        X_te = vec.transform(texts_te)
        clf = LogisticRegression(max_iter=3000)
        clf.fit(X_tr, y_tr)
        probs = clf.predict_proba(X_te)
        classes = list(clf.classes_)
        for row_p, gold in zip(probs, gold_idx):
            mapping = {label: row_p[classes.index(label)] for label in options if label in classes}
            p = np.array([mapping.get(o, 0.0) for o in options])
            s = p.sum()
            p = p / s if s > 0 else np.full(len(options), 1 / len(options))
            tf_preds.append(int(p.argmax()) == gold)
            tf_gold_p.append(max(p[gold], 1e-12))
            tf_conf.append(float(p.max()))

        c_tr = {i: len(gzip.compress(records[i]["state"].encode())) for i in tr}
        for i in te:
            x = records[i]["state"]
            c_x = len(gzip.compress(x.encode()))
            distances = []
            for j in tr:
                xy = " ".join([x, records[j]["state"]])
                c_xy = len(gzip.compress(xy.encode()))
                ncd = (c_xy - min(c_x, c_tr[j])) / max(c_x, c_tr[j], 1)
                distances.append((ncd, records[j]["gold"]))
            distances.sort()
            top = [label for _, label in distances[:5]]
            pred = max(set(top), key=top.count)
            gz_preds.append(pred == records[i]["gold"])

        t = np.arange(len(te))
        for i in te:
            _ = i

    results["tfidf/logreg"] = metrics(tf_preds, tf_gold_p, tf_conf)
    results["gzip/knn"] = metrics(gz_preds)


def run_laya(records, idx_train, idx_test, results):
    fitted = REFIT["fitted"]
    preds, gold_p, conf = [], [], []
    for i in idx_test:
        r = records[i]
        options = r["options"]
        raw = np.array([float(r["probs"].get(o, 0.0)) for o in options])
        t = fitted.get(f"choice:{bucket(len(options))}", 1.0)
        q = np.power(raw, 1.0 / t)
        s = q.sum()
        q = q / s if s > 0 else np.full(len(options), 1 / len(options))
        gold = options.index(r["gold"])
        preds.append(int(q.argmax()) == gold)
        gold_p.append(max(q[gold], 1e-12))
        conf.append(float(q.max()))
    results["laya/zero-shot"] = metrics(preds, gold_p, conf)


def main():
    records = load_records()
    idx_train = {i for i, r in enumerate(records) if split_of(r["id"]) == "train"}
    idx_test = {i for i, r in enumerate(records) if split_of(r["id"]) == "test"}
    print(f"records={len(records)} train={len(idx_train)} test={len(idx_test)} surfaces="
          f"{len(set(r['surface'] for r in records))}")

    results = {}
    run_baselines(records, idx_train, idx_test, results)
    run_laya(records, idx_train, idx_test, results)

    dims = {}
    for name in ["minishlab/potion-base-8M", "minishlab/potion-base-32M"]:
        model = StaticModel.from_pretrained(name)
        started = time.time()
        E = np.asarray(model.encode([r["state"] for r in records]))
        elapsed = time.time() - started
        E = normalize(E)
        dims[name] = {"dim": int(E.shape[1]), "embed_seconds": elapsed,
                      "ms_per_state": elapsed / len(records) * 1000,
                      "states_per_second": len(records) / elapsed}
        print(f"{name}: dim={E.shape[1]} embed={elapsed:.2f}s "
              f"({len(records)/elapsed:.0f} states/s, {elapsed/len(records)*1000:.2f} ms/state)")
        run_embedding_methods(name.split("/")[-1], E, records, idx_train, idx_test, results)

    print(f"\n{'method':28s} {'n':>4s} {'acc':>7s} {'nll':>8s} {'ece':>7s}")
    for name, m in sorted(results.items(), key=lambda kv: -kv[1]["accuracy"]):
        print(f"{name:28s} {m['n']:4d} {m['accuracy']:7.3f} "
              f"{m.get('nll', float('nan')):8.3f} {m.get('ece', float('nan')):7.3f}")

    json.dump({"results": results, "embeddings": dims}, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
