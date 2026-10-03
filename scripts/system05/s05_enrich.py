#!/usr/bin/env python3
"""Route-catalog enrichment experiment (System 0.5).

Frozen eval: the recovered 80-intent route set. Deterministic split by intent-id
hash: 75% tune / 25% confirm. Enrichment is authored from route semantics only
(canonical verbs and operator phrasings), never from eval utterances.

Variants (all scored against the same 68-route distractor set):
  baseline      current one-line descriptions
  verbs         verb-synonym one-liners for the 8 target routes
  multi         multiple reference utterances per target route, max-over-utterances
  multi_verbs   multi utterances + synonym coverage
  centroid      mean of utterances (control)
  multi_noname  multi utterances without the "name — " prefix
"""
import hashlib
import json
import os
import sys

import numpy as np
from model2vec import StaticModel
from sklearn.preprocessing import normalize

INTENTS = "/tmp/opencode/route_eval/route-eval/intents.jsonl"
ROUTES = "/home/lucas/SharedWorkspace/uploads/miranda-macbook/v9_curated_routes.json"
OUT = "/tmp/opencode/s05_enrich_results.json"

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

VERBS = {
    "memory.create": "Create, store, remember, or write down a memory, fact, or note for later.",
    "memory.search": "Search, recall, retrieve, look up, or find previously stored memories.",
    "session.checkpoint": "Save, snapshot, or hand off the current session state for resumption.",
    "session.continuity": "Resume, continue, reload, or review the previous session history.",
    "session.record": "Record, log, append, or capture a turn or event in the current session.",
    "gnosis.status": "Show system status, store counts, epoch, or kernel health.",
    "gnosis.explain": "Explain, justify, or trace why a memory or route was selected.",
    "memory.ingest": "Import, ingest, or bulk-load documents, transcripts, files, or events.",
}

MULTI = {
    "memory.create": [
        "Store a new memory or fact.",
        "Remember this for later.",
        "Write this down and save it to memory.",
        "Create a new memory entry.",
        "Add this fact to the memory store.",
        "Keep a note about this.",
    ],
    "memory.search": [
        "Retrieve memories by query.",
        "Recall what we know about a topic.",
        "Search the memory store.",
        "Look up a previously stored fact.",
        "Find memories matching a query.",
        "What do we know about this?",
    ],
    "session.checkpoint": [
        "Save a session handoff or checkpoint.",
        "Checkpoint the current session.",
        "Snapshot session state for the next session.",
        "Persist this session so it can be resumed.",
        "Hand off the current context.",
    ],
    "session.continuity": [
        "Resume or review the previous session.",
        "Continue where we left off.",
        "Load the session history.",
        "What happened in the last session?",
        "Restore the prior working context.",
    ],
    "session.record": [
        "Record a turn or event in the current session.",
        "Append this exchange to the session log.",
        "Log this message into the running session.",
        "Capture this event in the current session.",
        "Track what just happened in this session.",
    ],
    "gnosis.status": [
        "Show system status and store counts.",
        "How many memories are stored?",
        "Check kernel health and epoch.",
        "Report store statistics.",
        "What is the current system state?",
    ],
    "gnosis.explain": [
        "Explain why a memory or route was selected.",
        "Justify a decision or routing choice.",
        "Give the reasoning behind a selection.",
        "Trace why this result was chosen.",
        "Why did the system pick that?",
    ],
    "memory.ingest": [
        "Import documents, transcripts, or events from a directory.",
        "Ingest files into memory.",
        "Bulk-load a transcript or document set.",
        "Import a folder of notes.",
        "Load external documents into the store.",
    ],
}

MULTI_VERBS = {
    "memory.create": MULTI["memory.create"] + [
        "Create a note.", "Save this information.", "Persist a new fact.",
        "Keep this in mind.", "Make a note of this.", "Note this down for later.",
        "Record this as a memory.",
    ],
    "memory.search": MULTI["memory.search"] + [
        "Search stored facts.", "Retrieve a note.", "Query the memory index.",
        "Recall something you were told.", "Pull up a fact I mentioned.",
        "Remind me about something.",
    ],
    "session.checkpoint": MULTI["session.checkpoint"] + [
        "Save a handoff.", "Snapshot the session.", "Persist a checkpoint.",
    ],
    "session.continuity": MULTI["session.continuity"] + [
        "Resume the session.", "Reload prior context.", "Continue the previous work.",
        "Resume from the saved handoff.", "Continue from the last checkpoint.",
        "Reload a prior handoff.",
    ],
    "session.record": MULTI["session.record"] + [
        "Log a turn.", "Append to the session log.", "Record an event.",
        "Record a turn as an event.", "Log a turn in this session.",
    ],
    "gnosis.status": MULTI["gnosis.status"] + [
        "System status.", "Store counts.", "Epoch and health report.",
        "Count the records in the store.", "What is the memory kernel status?",
    ],
    "gnosis.explain": MULTI["gnosis.explain"] + [
        "Explain a route choice.", "Justify a selection.", "Reasoning trace.",
        "Show the active constitution.", "Describe the self-model.",
        "Explain the internal invariants.", "Describe how the system models itself.",
    ],
    "memory.ingest": MULTI["memory.ingest"] + [
        "Ingest a directory.", "Bulk import transcripts.", "Load documents.",
        "Import a file or dataset.", "Ingest records from a file.",
        "Bring in external events.", "Load a JSONL or transcript.",
    ],
}


def split_of(intent_id):
    digest = hashlib.sha256(intent_id.encode()).hexdigest()
    return "confirm" if int(digest, 16) % 100 < 25 else "tune"


def load_all():
    routes = {}
    raw = json.load(open(ROUTES))
    for name, desc in raw.items():
        one = OVERRIDES.get(name) or (desc.split(". ")[0].strip() or name)
        routes[name] = one[:90]
    intents = []
    for line in open(INTENTS):
        row = json.loads(line)
        mapped = GOLD_MAP.get(row["gold"])
        if mapped:
            row = dict(row)
            row["gold"] = mapped
            intents.append(row)
    return routes, intents


def build_variant(name, routes):
    """Return {route: [texts]} where text is what gets embedded."""
    out = {route: [f"{route} — {desc}"] for route, desc in routes.items()}
    if name == "baseline":
        return out
    if name == "verbs":
        for route, desc in VERBS.items():
            out[route] = [f"{route} — {desc}"]
        return out
    source = {"multi": MULTI, "multi_verbs": MULTI_VERBS, "centroid": MULTI,
              "multi_noname": MULTI}[name]
    for route, utterances in source.items():
        if name == "multi_noname":
            out[route] = list(utterances)
        else:
            out[route] = [f"{route} — {utterance}" for utterance in utterances]
    return out


def run_variant(name, variant, intents, model):
    names = list(variant)
    flat = [text for route in names for text in variant[route]]
    offsets, start = {}, 0
    for route in names:
        offsets[route] = (start, start + len(variant[route]))
        start += len(variant[route])
    E = normalize(np.asarray(model.encode(flat)))
    Q = normalize(np.asarray(model.encode([it["text"] for it in intents])))
    sims = Q @ E.T

    route_scores = np.empty((len(intents), len(names)))
    for column, route in enumerate(names):
        lo, hi = offsets[route]
        block = sims[:, lo:hi]
        route_scores[:, column] = block.mean(axis=1) if name == "centroid" else block.max(axis=1)

    order = np.argsort(-route_scores, axis=1)
    gold_idx = [names.index(it["gold"]) for it in intents]
    metrics = {}
    for subset in ["all", "tune", "confirm"]:
        rows = [i for i, it in enumerate(intents) if subset == "all" or split_of(it["id"]) == subset]
        top1 = np.mean([order[i, 0] == gold_idx[i] for i in rows])
        recall = {str(k): float(np.mean([gold_idx[i] in order[i, :k] for i in rows])) for k in [3, 8, 16]}
        metrics[subset] = {"n": len(rows), "top1": float(top1), **{f"R@{k}": v for k, v in recall.items()}}
    per_op = {}
    for it, i in zip(intents, range(len(intents))):
        bucket = per_op.setdefault(it["gold"], [0, 0])
        bucket[1] += 1
        bucket[0] += int(order[i, 0] == gold_idx[i])
    metrics["per_op"] = {op: f"{hit}/{total}" for op, (hit, total) in sorted(per_op.items())}
    return metrics


def main():
    routes, intents = load_all()
    print(f"intents={len(intents)} routes={len(routes)}")
    model = StaticModel.from_pretrained("minishlab/potion-base-32M")
    results = {}
    for name in ["baseline", "verbs", "multi", "multi_verbs", "centroid", "multi_noname"]:
        variant = build_variant(name, routes)
        metrics = run_variant(name, variant, intents, model)
        results[name] = metrics
        print(f"{name:14s} all={metrics['all']['top1']:.3f} tune={metrics['tune']['top1']:.3f} "
              f"confirm={metrics['confirm']['top1']:.3f} R@16={metrics['all']['R@16']:.3f}")
    print("\nper-op (all):")
    for name in ["baseline", "multi_verbs"]:
        print(f"  {name}: {results[name]['per_op']}")
    json.dump(results, open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
