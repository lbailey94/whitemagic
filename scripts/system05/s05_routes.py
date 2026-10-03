#!/usr/bin/env python3
"""Route-catalog eval: System 0.5 retrieval vs Laya on the original 80 intents.

Retrievers: potion-base-8M, potion-base-32M (static), BAAI/bge-small-en-v1.5
Reference: v9 curated 68-route catalog; recorded baselines NLU 0.2375, JEV 0.30,
bge-small shortlist ceiling 0.41/0.50/0.65 @k=3/8/16.

Also runs Laya (HTTP, refit temperatures) over the full 68-option question and
measures shortlist-restricted accuracy per retriever.
"""
import json
import time
import urllib.request

import numpy as np
from fastembed import TextEmbedding
from model2vec import StaticModel
from sklearn.preprocessing import normalize

INTENTS = "/tmp/opencode/route_eval/route-eval/intents.jsonl"
ROUTES = "/home/lucas/SharedWorkspace/uploads/miranda-macbook/v9_curated_routes.json"
URL = "http://127.0.0.1:8088/api/predict"
OUT = "/tmp/opencode/s05_routes_results.json"

GOLD_MAP = {
    "remember": "memory.create",
    "recall": "memory.search",
    "session_checkpoint": "session.checkpoint",
    "session_continuity": "session.continuity",
    "session_record": "session.record",
    "status": "gnosis.status",
    "inspect": "gnosis.explain",
    "ingest": "memory.ingest",
}
STRUCTURAL_GAPS = ["sweep", "dream", "galaxy", "census", "migrate"]
OVERRIDES = {
    "memory.create": "Store a new memory or fact.",
    "memory.search": "Retrieve memories by query.",
    "session.checkpoint": "Save a session handoff or checkpoint.",
    "session.continuity": "Resume or review the previous session.",
    "session.record": "Record a turn or event in the current session.",
    "gnosis.status": "Show system or store status and counts.",
    "gnosis.explain": "Explain why a memory or route was selected.",
    "memory.ingest": "Import documents, transcripts, or events from a directory.",
}
PROMPT = "Which WhiteMagic operation does this request call for?"


def load_routes():
    raw = json.load(open(ROUTES))
    routes = {}
    for name, desc in raw.items():
        one = OVERRIDES.get(name) or (desc.split(". ")[0].strip() or name)
        routes[name] = f"{name} — {one[:90]}"
    return routes


def load_intents():
    kept = []
    for line in open(INTENTS):
        row = json.loads(line)
        mapped = GOLD_MAP.get(row["gold"])
        if mapped is None:
            continue
        row = dict(row)
        row["gold"] = mapped
        kept.append(row)
    return kept


def router_eval(name, E_i, E_r, intents, routes):
    names = list(routes)
    sims = E_i @ E_r.T
    order = np.argsort(-sims, axis=1)
    gold_idx = [names.index(it["gold"]) for it in intents]
    top1 = np.mean([order[i, 0] == gold_idx[i] for i in range(len(intents))])
    recall = {str(k): float(np.mean([gold_idx[i] in order[i, :k] for i in range(len(intents))]))
              for k in [1, 3, 5, 8, 10, 16]}
    margins = [float(sims[i, order[i, 0]] - sims[i, order[i, 1]]) for i in range(len(intents))]
    conf = [float(sims[i, order[i, 0]]) for i in range(len(intents))]
    return {"top1": float(top1), "recall": recall,
            "margin_mean": float(np.mean(margins)), "conf_mean": float(np.mean(conf))}


def laya_eval(intents, routes):
    results = {}
    latencies = []
    for it in intents:
        body = json.dumps({
            "state": it["text"],
            "questions": [{
                "id": "route",
                "type": "choice",
                "instructions": PROMPT,
                "criteria": routes,
            }],
        }).encode()
        req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = json.loads(resp.read())
        latencies.append(time.perf_counter() - started)
        answer = data["answers"]["route"]
        results[it["id"]] = {
            "probabilities": answer.get("probabilities", {}),
            "top1": answer.get("choice"),
            "confidence": answer.get("confidence"),
            "act": (answer.get("rl_agent") or {}).get("act_probability"),
        }
    return results, float(np.mean(latencies)), float(np.mean([r["latency_ms"] for r in [data] if False]) if False else 0.0)


def main():
    routes = load_routes()
    intents = load_intents()
    print(f"intents={len(intents)} routes={len(routes)}")

    embedders = {}
    for name, model in [
        ("potion-base-8M", StaticModel.from_pretrained("minishlab/potion-base-8M")),
        ("potion-base-32M", StaticModel.from_pretrained("minishlab/potion-base-32M")),
    ]:
        E_i = normalize(np.asarray(model.encode([it["text"] for it in intents])))
        E_r = normalize(np.asarray(model.encode(list(routes.values()))))
        embedders[name] = (E_i, E_r)
    bge = TextEmbedding("BAAI/bge-small-en-v1.5")
    E_i = normalize(np.asarray(list(bge.embed([it["text"] for it in intents]))))
    E_r = normalize(np.asarray(list(bge.embed(list(routes.values())))))
    embedders["bge-small-en-v1.5"] = (E_i, E_r)

    out = {"retrievers": {}, "laya": {}, "shortlist": {}}
    names = list(routes)
    for name, (E_i, E_r) in embedders.items():
        out["retrievers"][name] = router_eval(name, E_i, E_r, intents, routes)

    laya, mean_wall, _ = laya_eval(intents, routes)
    out["laya"] = {
        "accuracy": float(np.mean([laya[it["id"]]["top1"] == it["gold"] for it in intents])),
        "mean_wall_s": mean_wall,
    }

    gold_idx = [names.index(it["gold"]) for it in intents]
    for name, (E_i, E_r) in embedders.items():
        sims = E_i @ E_r.T
        order = np.argsort(-sims, axis=1)
        rows = {}
        for k in [3, 5, 10, 16]:
            in_sl = [gold_idx[i] in order[i, :k] for i in range(len(intents))]
            restricted = []
            for i, it in enumerate(intents):
                probs = laya[it["id"]]["probabilities"]
                shortlist = [names[j] for j in order[i, :k]]
                best = max(shortlist, key=lambda r: float(probs.get(r, 0.0)))
                restricted.append(best == it["gold"])
            full_on_sl = [laya[it["id"]]["top1"] == it["gold"] for i, it in enumerate(intents) if in_sl[i]]
            rows[f"k={k}"] = {
                "recall": float(np.mean(in_sl)),
                "laya_full_acc_subset": float(np.mean(full_on_sl)) if full_on_sl else 0.0,
                "laya_shortlist_acc": float(np.mean(restricted)),
            }
        out["shortlist"][name] = rows

    print("\n== retrievers ==")
    for name, m in out["retrievers"].items():
        print(f"{name:22s} top1={m['top1']:.3f} R@3={m['recall']['3']:.3f} "
              f"R@8={m['recall']['8']:.3f} R@16={m['recall']['16']:.3f}")
    print(f"\nLaya full-68 accuracy={out['laya']['accuracy']:.3f} "
          f"(mean wall {out['laya']['mean_wall_s']:.2f}s/intent)")
    print("\n== shortlist x Laya ==")
    for name, rows in out["shortlist"].items():
        for k, m in rows.items():
            print(f"{name:22s} {k:5s} recall={m['recall']:.3f} "
                  f"laya_full={m['laya_full_acc_subset']:.3f} "
                  f"laya_restricted={m['laya_shortlist_acc']:.3f}")

    json.dump(out, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
