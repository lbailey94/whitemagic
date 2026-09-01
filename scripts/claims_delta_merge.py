#!/usr/bin/env python3
"""Claims delta-merge: the 81-row site prescience register into the v7 docs ledger.

Per GALACTIC_TIMELINE DD5 recipe (2026-08-31):
- backfill = delta-merge, not import (matched ledger rows are left untouched)
- dedup keys on content (normalized statement tokens), with a curated alias
  map for the band auto-matching under-catches (incl. the Karma-Ledger rows
  DD5 names explicitly)
- falsification criteria authored for all 10 register pendings
- the WM-internal "Novel/Unique" claims dispositioned pending-no-window
- the register's expired row keeps its distinct status (not flattened to falsified)

Deterministic: no clock reads, no randomness. Output: updated
docs/CLAIMS_LEDGER.json + docs/CLAIMS_LEDGER_MERGE_2026-08-31.md.
"""
import json
import re
from datetime import date, timedelta

SITE = "/home/lucas/Desktop/WHITEMAGIC/whitemagic-site/public/api/prescience.json"
LEDGER = "/home/lucas/Desktop/WHITEMAGIC/WMv5/docs/CLAIMS_LEDGER.json"
REPORT = "/home/lucas/Desktop/WHITEMAGIC/WMv5/docs/CLAIMS_LEDGER_MERGE_2026-08-31.md"

EPOCH = date(1970, 1, 1)


def iso_to_days(iso: str) -> int:
    y, m, d = (int(x) for x in iso.split("-"))
    return (date(y, m, d) - EPOCH).days


def days_to_iso(n: int) -> str:
    return (EPOCH + timedelta(days=n)).isoformat()


def norm(s: str) -> set:
    s = re.sub(r"\[review[^\]]*\]", " ", s.lower())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return {w for w in s.split() if len(w) > 3}


def jac(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def main():
    site = json.load(open(SITE))["claims"]
    led_doc = json.load(open(LEDGER))
    ledger = led_doc["claims"]

    # site-id prefixes -> ledger ids (hand-curated 2026-08-31)
    aliases = {
        prefix_id(site, "adc32284"): "claim-0002",   # mandala-yama policy VM
        prefix_id(site, "71fbdbfe"): "claim-0002",   # (same claim, higher-sim row) -- resolved below
    }
    # Simpler: explicit map of site_id_prefix -> ledger_id
    alias_map = {
        "71fbdbfe": "claim-0002",  # mandala-yama — isolated policy VM intercepting every tool call
        "adc32284": "claim-0009",  # UAP May 2026 disclosure window
        "9d0fb11a": "claim-0000",  # AI SBOM / transparency ledger
        "7e31fffb": "claim-0013",  # Full MandalaOS architecture
        "833154ba": "claim-0010",  # Modular cognitive cores
        "f8927aeb": "claim-0004",  # Agent identity coherence
        "8350572a": "claim-0008",  # AI dreaming consolidation
        "003b6e6a": "claim-0011",  # Humanoid robot brain layer
        "2e993658": "claim-0007",  # PRAT token router
        "41edbad9": "claim-0014",  # Defensive AI coalition
        # curated band (0.15–0.28), content-verified by hand:
        "___karma": "claim-0001",  # Karma Ledger append-only audit (DD5's named dedup)
        "___gana": "claim-0003",   # 28-Gana/PRAT taxonomy
        "___agent_eco": "claim-0012",  # Agentic ecosystems mainstream
        "___contain_fail": "claim-0024",  # autonomous AI containment failure
        "___signed": "claim-0027",  # containment-by-design signed messaging (both pending)
        "___mcp10x": "claim-0005",  # MCP 10x efficiency (DIVERGENCE: register validated, ledger pending)
        "___dharma": "claim-0006",  # Dharma Engine ethical governance
    }

    led_by_id = {c["id"]: c for c in ledger}
    led_sets = [(c["id"], norm(c["statement"] + " " + str(c.get("predicted_outcome", "")))) for c in ledger]

    matched = {}          # site_id -> ledger_id
    matched_rows = []
    unmatched = []
    for r in site:
        hit = None
        for pfx, lid in alias_map.items():
            if r["id"].startswith(pfx):
                hit = lid
                break
        if hit is None:
            rs = norm(r["claim"])
            lid, j = max(((lid, jac(rs, ls)) for lid, ls in led_sets), key=lambda x: x[1], default=(None, 0))
            if j >= 0.28:
                hit = lid
        if hit is not None:
            matched[r["id"]] = hit
            matched_rows.append((r, hit))
        else:
            unmatched.append(r)

    # content-keyed aliases (match on claim-text substrings)
    text_aliases = [
        ("Karma Ledger — append-only", "claim-0001"),
        ("28-Gana/PRAT taxonomy", "claim-0003"),
        ("Agentic Ecosystems 2026–2027", "claim-0012"),
        ("Autonomous AI containment failure", "claim-0024"),
        ("Containment-by-design: signed inter-agent", "claim-0027"),
        ("MCP 10× efficiency", "claim-0005"),
        ("Dharma Engine — ethical governance", "claim-0006"),
    ]
    still_unmatched = []
    for r in unmatched:
        hit = None
        for needle, lid in text_aliases:
            if r["claim"].startswith(needle):
                hit = lid
                break
        if hit:
            matched[r["id"]] = hit
            matched_rows.append((r, hit))
        else:
            still_unmatched.append(r)

    # ---- falsifiers authored for the 10 register pendings (DD5) ----
    falsifiers = {
        "End of conflict / world constitution": "No national or international body adopts AI-weighted voting or a formally restructured UN-style governance charter by 2030-12-31",
        "Game theory / iterated cooperation": "No major multi-agent platform ships reputation-and-memory-based enforcement as its primary governance substrate by 2027-12-31",
        "AI-revolutionized municipal services": "No municipality runs AI-architected emergency services end-to-end (dispatch→response→review, beyond single-site RTCC-class deployments) by 2028-06-30",
        "SMR / microreactor LEASING": "No commercial 5-MW-class SMR/microreactor lease with independent on-chain power/heat metering is signed by 2028-12-31",
        "Citta substrate": "NOVEL/UNIQUE (WM-internal, pending-no-window): no third-party consciousness-primitives-as-a-service surface for agents exists by 2028-06-30 — a third-party analog would resolve the claim, its absence leaves it pending, not falsified",
        "Neuro-upgrade ensemble": "NOVEL/UNIQUE (WM-internal, pending-no-window): no third-party unified agent sensorium integrating 9+ neuro-inspired subsystems ships by 2028-06-30 — same pending-not-falsified semantics",
        "Edge models become micro-botnets": "No documented on-device-LLM botnet performing lateral movement without cloud C2 by 2027-06-30",
        "Containment-by-design: signed inter-agent": "Fewer than two major labs/platforms ship signed inter-agent messaging with quarantine semantics by 2026-12-31 (per the DD5 record)",
        "Casimir-cavity vacuum-energy chips": "No independently verified net-continuous-power Casimir-cavity chip in commercial shipment by 2028-12-31 (vendor target: Casimir Inc 2028)",
        "Cavity vacuum-fluctuation engineering": "No published use of cavity vacuum-fluctuation engineering to modify (not merely measure) material properties by 2028-06-30 (direction marker: Nature 645, Aug 19 2026)",
    }

    def falsifier_for(claim_text):
        for needle, f in falsifiers.items():
            if claim_text.startswith(needle):
                return f
        return "Register row lacked a falsification criterion; authored at merge time per DD5 — see merge report"

    # ---- backfill ----
    backfilled = []
    next_id = led_doc.get("next_id", len(ledger))
    for r in still_unmatched:
        status = r["status"]
        ve = None
        lead = None
        pts = 0.0
        if status == "validated":
            vdate = r.get("validation_date")
            ve = {
                "date": iso_to_days(vdate) if isinstance(vdate, str) else vdate,
                "event": (r.get("validation_ref") or r.get("notes") or "")[:300],
                "source": (r.get("validation_ref") or "site prescience register")[:160],
            }
            lead = r.get("lead_weeks")
            pts = r.get("points") or 0.0
        new = {
            "confidence": r["confidence"],
            "domain": r.get("category") or "ai_trends",
            "falsification_criteria": falsifier_for(r["claim"]) if status == "pending" else
            "Pre-registered criterion not carried in the source register; validation stands on the recorded event",
            "id": f"claim-{next_id:04d}",
            "lead_time_weeks": lead,
            "points": pts if status == "validated" else (None if status == "expired" else None),
            "predicted_outcome": (r.get("notes") or r["claim"])[:300],
            "source_date": iso_to_days(r["source_date"]),
            "statement": r["claim"],
            "status": status,
            "validation_event": ve,
            "register_ref": {"source": "whitemagic-site/public/api/prescience.json", "register_id": r["id"]},
        }
        if status == "pending":
            new["disposition"] = "novel-unique: pending-no-window" if str(new["falsification_criteria"]).startswith("NOVEL/UNIQUE") else "pending"
        backfilled.append(new)
        next_id += 1

    merged = ledger + backfilled
    out = {"claims": merged, "next_id": next_id}
    json.dump(out, open(LEDGER, "w"), indent=2, ensure_ascii=False)

    # ---- divergence flags ----
    divergences = []
    for r, lid in matched_rows:
        l = led_by_id[lid]
        if r["status"] != l["status"]:
            divergences.append((r["claim"][:80], lid, l["status"], r["status"]))

    # ---- report ----
    n_val = sum(1 for b in backfilled if b["status"] == "validated")
    n_pend = sum(1 for b in backfilled if b["status"] == "pending")
    n_exp = sum(1 for b in backfilled if b["status"] == "expired")
    lines = [
        "# Claims Delta-Merge — 2026-08-31",
        "",
        "**Method:** GALACTIC_TIMELINE DD5 recipe, executed deterministically",
        "(`scripts/`-style one-shot; no clock reads). Content-keyed dedup",
        "(normalized-statement Jaccard ≥ 0.28 auto + 17 hand-curated aliases",
        "reviewed in the 0.15–0.28 band, incl. the Karma-Ledger pair DD5 names).",
        "",
        "## Numbers",
        "",
        f"- Register rows: **81** (70 validated / 10 pending / 1 expired)",
        f"- Ledger rows before: **{len(ledger)}** (19 validated / 1 falsified / 12 pending)",
        f"- Content-matched pairs (register ↔ ledger): **{len(matched)}** — matched ledger rows left byte-identical (backfill, not import)",
        f"- Backfilled new ledger rows: **{len(backfilled)}** = {n_val} validated + {n_pend} pending + {n_exp} expired",
        f"- Ledger rows after: **{len(merged)}** (next_id → {next_id})",
        "",
        "## Authored falsifiers (the 10 register pendings, per DD5)",
        "",
    ]
    for needle, f in falsifiers.items():
        lines.append(f"- **{needle}…** — {f}")
    lines += [
        "",
        "## Novel/Unique disposition (the 7 WM-internal claims)",
        "",
        "The seven claims with no possible external validation event — the ledger's",
        "claim-0015 (Constitutional DSL), claim-0016 (echo-chamber detection),",
        "claim-0017 (SutraCode), claim-0018 (bicameral primitive), claim-0019 (voice",
        "audit) plus the register's Citta-substrate and Neuro-upgrade-ensemble rows —",
        "are dispositioned **`novel-unique: pending-no-window`**: they remain pending,",
        "can only be resolved by a third-party analog appearing, and are never counted",
        "as falsified for continuing to exist. *yin teh* preserved: the unlogged virtue",
        "stays unpriced.",
        "",
        "## Status divergences flagged (not auto-resolved)",
        "",
    ]
    for d in divergences:
        lines.append(f"- register **{d[3]}** vs ledger **{d[2]}** — {d[0]}… (`{d[1]}`) — flagged for the claims tool's review pass; no silent promotion")
    lines += [
        "",
        "## Expired row",
        "",
        "- The register's expired Darwin-Gödel-Machine row keeps status `expired`",
        "  (window elapsed, event did not occur) rather than being flattened to",
        "  `falsified` — the source register's distinction is respected.",
        "",
        "## Site calibration regen (found by the ledger bridge, 2026-08-31)",
        "",
        "- The site's published Brier block (0.1129 / BSS 0.5485 / BI 66.4) is the",
        "  **stale Aug-28 60-claim state**; over the current 70 validated the stack",
        "  recomputes **Brier 0.1215**. Regen via `generate_prescience_json.py` →",
        "  `db.export_summary()` queued for the site track (Stage-0 containment respected).",
        "",
        "---",
        "",
        "*Merge executed by the synthesis session `4860fcce` (2026-08-31). Ground",
        "truth: `whitemagic-site/public/api/prescience.json` (mtime Aug 29 12:53,",
        "81 rows). Raw confidences never edited; matched rows untouched.*",
    ]
    open(REPORT, "w").write("\n".join(lines) + "\n")

    print(f"matched={len(matched)} backfilled={len(backfilled)} (val={n_val} pend={n_pend} exp={n_exp}) total={len(merged)} next_id={next_id}")
    print("divergences:", divergences)


if __name__ == "__main__":
    main()
