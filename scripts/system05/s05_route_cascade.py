#!/usr/bin/env python3
"""Retrieve-then-decide on the route catalog: potion shortlist -> Laya decides.

For k in {3,5,10}: potion-32M ranks 68 routes; Laya is called with only the
top-k options (full descriptions, no 192-token head truncation). Reports
unconditional accuracy, accuracy conditioned on gold-in-shortlist, and latency.
"""
import json
import time
import urllib.request

import numpy as np
from model2vec import StaticModel
from sklearn.preprocessing import normalize

INTENTS = "/tmp/opencode/route_eval/route-eval/intents.jsonl"
ROUTES = "/home/lucas/SharedWorkspace/uploads/miranda-macbook/v9_curated_routes.json"
URL = "http://127.0.0.1:8088/api/predict"
OUT = "/tmp/opencode/s05_route_cascade_results.json"

GOLD_MAP = {
    "remember": "memory.create", "recall": "memory.search",
    "session_checkpoint": "session.checkpoint", "session_continuity": "session.continuity",
    "session_record": "session.record", "status": "gnosis.status",
    "inspect": "gnosis.explain", "ingest": "memory.ingest",
}
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


def load_all():
    routes = {}
    for name, desc in json.load(open(ROUTES)).items():
        one = OVERRIDES.get(name) or (desc.split(". ")[0].strip() or name)
        routes[name] = f"{name} — {one[:90]}"
    intents = []
    for line in open(INTENTS):
        row = json.loads(line)
        mapped = GOLD_MAP.get(row["gold"])
        if mapped:
            row = dict(row)
            row["gold"] = mapped
            intents.append(row)
    return routes, intents


def ask_laya(text, criteria):
    body = json.dumps({
        "state": text,
        "questions": [{"id": "route", "type": "choice", "instructions": PROMPT, "criteria": criteria}],
    }).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as resp:
        data = json.loads(resp.read())
    return data["answers"]["route"].get("choice"), time.perf_counter() - started


def main():
    routes, intents = load_all()
    model = StaticModel.from_pretrained("minishlab/potion-base-32M")
    E_i = normalize(np.asarray(model.encode([it["text"] for it in intents])))
    E_r = normalize(np.asarray(model.encode(list(routes.values()))))
    names = list(routes)
    sims = E_i @ E_r.T
    order = np.argsort(-sims, axis=1)
    potion_top1 = float(np.mean([names[order[i, 0]] == intents[i]["gold"] for i in range(len(intents))]))
    print(f"potion-32M top1 baseline: {potion_top1:.3f}")

    out = {"potion_top1": potion_top1, "cascade": {}}
    for k in [3, 5, 10]:
        correct, conditioned, lat = [], [], []
        for i, it in enumerate(intents):
            shortlist = [names[j] for j in order[i, :k]]
            chosen, elapsed = ask_laya(it["text"], {r: routes[r] for r in shortlist})
            ok = chosen == it["gold"]
            correct.append(ok)
            if it["gold"] in shortlist:
                conditioned.append(ok)
            lat.append(elapsed)
        out["cascade"][f"k={k}"] = {
            "accuracy": float(np.mean(correct)),
            "conditioned_on_recall": float(np.mean(conditioned)) if conditioned else 0.0,
            "gold_in_shortlist": len(conditioned) / len(intents),
            "mean_wall_s": float(np.mean(lat)),
        }
        print(f"k={k:2d} accuracy={np.mean(correct):.3f} "
              f"conditioned={np.mean(conditioned) if conditioned else 0:.3f} "
              f"recall={len(conditioned)/len(intents):.3f} wall={np.mean(lat):.2f}s")

    json.dump(out, open(OUT, "w"), indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
