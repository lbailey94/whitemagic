#!/usr/bin/env python3
"""Canary re-run comparator: rerun bundle vs frozen bundle (2026-09-17).

Compares journal-derived readings cell by cell and prints PASS/FAIL per canary
assertion. Ephemeral driver; not part of the frozen tree.
"""
import json
import sys
from pathlib import Path

ROOT = Path("/home/lucas/Desktop/WMgen3")
HIST = ROOT / "receipts/canary_2026-09-17"
RERUN = ROOT / "receipts/canary_2026-09-17_rerun"
CELLS = ["A1", "A2", "A3", "B_count", "B_floor", "B_off", "B_soff"]
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")


def load_journal(p):
    ev = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                ev.append(json.loads(line))
    return ev


def reading(ev):
    get = lambda t: [e for e in ev if e.get("type") == t]
    types = {}
    for e in ev:
        types[e.get("type")] = types.get(e.get("type"), 0) + 1
    sweeps = [{"disabled": s.get("disabled"), "pairs_examined": s.get("pairs_examined"),
               "proposals": s.get("proposals")} for s in get("think.sweep")]
    props = [(p.get("relation_id"), p.get("kind"), p.get("src"), p.get("dst"), p.get("rule_id"))
             for p in get("relation.proposed")]
    chains = get("provenance.chain")
    prov = {"chains": len(chains), "complete_true": sum(1 for c in chains if c.get("complete") is True)}
    decisions = []
    for d in get("selection.decision"):
        decisions.append({
            "query": (d.get("query_sha256") or "")[:12],
            "considered": d.get("considered"),
            "lexical_candidates": d.get("lexical_candidates"),
            "semantic_candidates": d.get("semantic_candidates"),
            "abstained": d.get("abstained"),
            "selected": [(s.get("id"), s.get("rank"), s.get("stratum"), s.get("superseded_by"))
                         for s in d.get("selected", [])],
        })
    gates = [(g.get("lexical_candidates"), round(g.get("lex_support_max", 0.0), 6), g.get("fired"))
             for g in get("projection.gate")]
    probes = [(c.get("kind"), c.get("outcome"), tuple(c.get("observed_domains") or [])) for c in get("canary.probe")]
    ends = get("run.end")
    end = None
    if ends:
        e = ends[-1]
        end = {"records": e.get("records"), "relations": e.get("relations"), "violations": e.get("violations"),
               "journal_ok": e.get("journal_ok"), "sweep_enabled": e.get("sweep_enabled"),
               "arbitration": e.get("arbitration"), "rules": e.get("rules"),
               "projection_enabled": (e.get("projection") or {}).get("enabled"),
               "projection_gated": (e.get("projection") or {}).get("gated"),
               "projection_gate_count": (e.get("projection") or {}).get("gate_count")}
    return {"types": types, "sweeps": sweeps, "proposals": props, "prov": prov, "decisions": decisions,
            "gates": gates, "probes": probes, "boundary": types.get("boundary.refusal", 0),
            "violations": types.get("closure.violation", 0), "end": end}


# --- 1) journal readings identical (frozen vs rerun), cell by cell
diff_cells = []
for cell in CELLS:
    h = reading(load_journal(HIST / f"journals/{cell}.journal.jsonl"))
    r = reading(load_journal(RERUN / f"journals/{cell}.journal.jsonl"))
    if h != r:
        diff_cells.append(cell)
        for k in h:
            if h[k] != r.get(k):
                print(f"  [{cell}] {k}:\n    hist : {h[k]}\n    rerun: {r.get(k)}")
check("C2/C3/C4/C6 journal readings identical (7/7 cells, typed inventory + decisions + gates + provenance)",
      not diff_cells, f"diff cells: {diff_cells or 'none'}")

# --- 2) C1 runtime: closure refusal + zero violations + probe refused
a1 = reading(load_journal(RERUN / "journals/A1.journal.jsonl"))
check("C1 runtime canary.probe refused, domains [Simulated]",
      a1["probes"] == [("laundering", "refused", ("Simulated",))], f"{a1['probes']}")
check("C1 boundary.refusal == 1 and closure.violation == 0 in A1",
      a1["boundary"] == 1 and a1["violations"] == 0, f"boundary={a1['boundary']} violations={a1['violations']}")
check("C4 provenance completeness 100% in all 7 runs",
      all(reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["prov"]["chains"]
          == reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["prov"]["complete_true"]
          for c in CELLS), "chains == complete_true everywhere")

# --- 3) C2 ablation ordering flip
check("C2 R ablation flips ordering (A1 [1(s0),0(s2,sup4)] vs A2 [0(s1),1(s1)])",
      a1["decisions"][0]["selected"] == [(1, 1, 0, None), (0, 2, 2, 4)]
      and reading(load_journal(RERUN / "journals/A2.journal.jsonl"))["decisions"][0]["selected"]
          == [(0, 1, 1, None), (1, 2, 1, None)],
      "also: A1 5 proposals, A2 0 (sweep disabled)")

# --- 4) C3 gate fired sets
bc = reading(load_journal(RERUN / "journals/B_count.journal.jsonl"))
bf = reading(load_journal(RERUN / "journals/B_floor.journal.jsonl"))
bo = reading(load_journal(RERUN / "journals/B_off.journal.jsonl"))
bs = reading(load_journal(RERUN / "journals/B_soff.journal.jsonl"))
check("C3 count gate fired [false,true,true] on lexical candidates [2,1,0]",
      [g[2] for g in bc["gates"]] == [False, True, True] and [g[0] for g in bc["gates"]] == [2, 1, 0])
check("C3 floor mode differs (fired [false,false,true])",
      [g[2] for g in bf["gates"]] == [False, False, True])
check("C3 always-on: no gate events, projection loads",
      bo["gates"] == [] and "projection.load" in bo["types"])
check("C3 projection off: no projection events",
      bs["gates"] == [] and "projection.load" not in bs["types"] and bs["end"]["projection_enabled"] is False)

# --- 5) C5 round-trip: A1 vs A3 inspect relations byte-identical (second process, sweep off)
def inspect_relations(path):
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        txt = obj.get("result", {}).get("content", [{}])[0].get("text", "")
        payload = json.loads(txt)
        if "inspect" in payload:
            return payload["inspect"]["relations"]
    return None

rel_a1 = inspect_relations(RERUN / "responses/A1.responses.jsonl")
rel_a3 = inspect_relations(RERUN / "responses/A3.responses.jsonl")
check("C5 relation kinds/endpoints byte-identical across processes (A1 vs A3 inspect)",
      rel_a1 is not None and rel_a1 == rel_a3,
      f"{len(rel_a1 or [])} relations (A1) == {len(rel_a3 or [])} relations (A3); "
      f"kinds={sorted({r['kind'] for r in (rel_a1 or [])})}")

# --- 6) C6 verb -> event inventory present in rerun journals
inv = {
    "remember -> ingest.batch": all("ingest.batch" in reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["types"]
                                    for c in ["A1", "A2", "B_count", "B_floor", "B_off", "B_soff"]),
    "think -> think.sweep (+relation.proposed when on)": "think.sweep" in a1["types"] and len(a1["proposals"]) > 0,
    "recall -> selection.decision + provenance.chain": all(
        "selection.decision" in reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["types"]
        and "provenance.chain" in reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["types"]
        for c in CELLS),
    "canary -> canary.probe + boundary.refusal": "canary.probe" in a1["types"] and a1["boundary"] == 1,
    "lens slot -> projection.gate/load": "projection.load" in bc["types"] and len(bc["gates"]) == 3,
    "run.end journal_ok everywhere": all(
        reading(load_journal(RERUN / f"journals/{c}.journal.jsonl"))["end"]["journal_ok"] is True for c in CELLS),
}
check("C6 reachable-effectful inventory", all(inv.values()),
      "; ".join(f"{k}={'ok' if v else 'MISSING'}" for k, v in inv.items()))

# --- 7) response byte-identity vs frozen bundle (allowed: B_off took_ms wall clock)
import hashlib
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
resp_diffs = []
for c in CELLS:
    if sha(HIST / f"responses/{c}.responses.jsonl") != sha(RERUN / f"responses/{c}.responses.jsonl"):
        resp_diffs.append(c)
check("responses byte-identical to frozen bundle except B_off (disclosed: took_ms 0->1)",
      resp_diffs == ["B_off"], f"differing cells: {resp_diffs}")

bad = [n for n, ok, _ in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} assertions PASS")
sys.exit(1 if bad else 0)
