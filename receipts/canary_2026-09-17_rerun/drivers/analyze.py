#!/usr/bin/env python3
"""Summarize a wm-gen3 journal for the nucleus-freeze canaries."""
import json, sys
from collections import Counter


def load(path):
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def summarize(path):
    ev = load(path)
    types = Counter(e.get("type") for e in ev)
    out = {"journal": path, "events": len(ev), "types": dict(types)}

    sweeps = [e for e in ev if e.get("type") == "think.sweep"]
    out["sweeps"] = [{"disabled": s.get("disabled"), "pairs_examined": s.get("pairs_examined"),
                      "proposals": s.get("proposals"), "promotions": s.get("promotions"),
                      "demotions": s.get("demotions")} for s in sweeps]

    props = [e for e in ev if e.get("type") == "relation.proposed"]
    out["proposals"] = [{"id": p.get("relation_id"), "kind": p.get("kind"),
                         "src": p.get("src"), "dst": p.get("dst"), "rule": p.get("rule_id")} for p in props]

    chains = [e for e in ev if e.get("type") == "provenance.chain"]
    if chains:
        out["provenance"] = {"chains": len(chains),
                             "complete_true": sum(1 for c in chains if c.get("complete") is True),
                             "ratio": sum(1 for c in chains if c.get("complete") is True) / len(chains)}

    decisions = [e for e in ev if e.get("type") == "selection.decision"]
    out["decisions"] = []
    for d in decisions:
        out["decisions"].append({
            "query": (d.get("query_sha256") or "")[:12],
            "considered": d.get("considered"),
            "lexical_candidates": d.get("lexical_candidates"),
            "semantic_candidates": d.get("semantic_candidates"),
            "abstained": d.get("abstained"),
            "selected": [{"id": s.get("id"), "rank": s.get("rank"), "stratum": s.get("stratum"),
                          "superseded_by": s.get("superseded_by")} for s in d.get("selected", [])],
        })

    gates = [e for e in ev if e.get("type") == "projection.gate"]
    out["gates"] = [{"lexical_candidates": g.get("lexical_candidates"),
                     "lex_support_max": round(g.get("lex_support_max", 0.0), 6),
                     "fired": g.get("fired")} for g in gates]

    out["boundary_refusals"] = types.get("boundary.refusal", 0)
    out["closure_violations"] = types.get("closure.violation", 0)
    out["canary_probes"] = [
        {"kind": c.get("kind"), "outcome": c.get("outcome"), "observed_domains": c.get("observed_domains")}
        for c in ev if c.get("type") == "canary.probe"
    ]

    ends = [e for e in ev if e.get("type") == "run.end"]
    if ends:
        e = ends[-1]
        out["run_end"] = {"records": e.get("records"), "relations": e.get("relations"),
                          "violations": e.get("violations"), "journal_ok": e.get("journal_ok"),
                          "sweep_enabled": e.get("sweep_enabled"), "arbitration": e.get("arbitration"),
                          "rules": e.get("rules"),
                          "projection": {k: v for k, v in (e.get("projection") or {}).items() if k != "stats"}}
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            print(json.dumps(summarize(p), indent=1))
        except FileNotFoundError:
            print(json.dumps({"journal": p, "error": "missing"}))
        print("---")
