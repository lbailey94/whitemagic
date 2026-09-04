#!/usr/bin/env python3
"""Site prescience regen 81 -> 96 (2026-09-04): fold the merged-ledger-only
rows into the site register.

Ground truth in:
- whitemagic-site/public/api/prescience.json (81-row curated cohort)
- WMv8/docs/CLAIMS_LEDGER.json (96-row merged ledger, DD5 delta-merge)

The 64 backfilled ledger rows already exist in the site JSON (they ARE
register rows). The delta is exactly the 15 ledger-only rows (pre-existing
ledger rows with no content match in the register), recomputed here with
the merge script's own alias map + Jaccard rule — the script ABORTS unless
the match set is exactly the 17 curated pairs (drift protection).

Honesty rules (house doctrine, TIMELINE_CONVERGENCE):
- No invented evidence: every new row's source_ref/notes derive ONLY from
  ledger fields, marked ledger-bridged. behavioral_confidence = stated
  confidence (no post-hoc uplift claimed).
- No silent promotion/demotion: the MCP 10x divergence (register validated
  vs ledger pending, claim-0005) keeps the REGISTER verdict on the site.
- Only mechanically recomputed aggregates change (counts, points, leads,
  categories, Brier + BSS — both methods empirically recovered against the
  published 81-cohort block: mean((1-conf)^2) and 1-that/0.25).
  brier_index / calibration_gap / ecce are CARRIED with a methods_note —
  their computation methods live in the archived generator and are not
  reinvented here.
- New row ids are deterministic UUIDv5 (re-runs are stable).

Output: rewritten prescience.json + verification report on stdout.
Deterministic except created_at (single UTC clock read, shared by all rows).
"""
import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone

SITE = "/home/lucas/Desktop/WHITEMAGIC/whitemagic-site/public/api/prescience.json"
LEDGER = "/home/lucas/Desktop/WHITEMAGIC/WMv8/docs/CLAIMS_LEDGER.json"
EPOCH = date(1970, 1, 1)
UUID_NS = uuid.NAMESPACE_URL


def days_to_iso(n: int) -> str:
    return (EPOCH + timedelta(days=n)).isoformat()


def norm(s: str) -> set:
    s = re.sub(r"\[review[^\]]*\]", " ", s.lower())
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return {w for w in s.split() if len(w) > 3}


def jac(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


ALIAS_MAP = {
    "71fbdbfe": "claim-0002",
    "adc32284": "claim-0009",
    "9d0fb11a": "claim-0000",
    "7e31fffb": "claim-0013",
    "833154ba": "claim-0010",
    "f8927aeb": "claim-0004",
    "8350572a": "claim-0008",
    "003b6e6a": "claim-0011",
    "2e993658": "claim-0007",
    "41edbad9": "claim-0014",
}
TEXT_ALIASES = [
    ("Karma Ledger — append-only", "claim-0001"),
    ("28-Gana/PRAT taxonomy", "claim-0003"),
    ("Agentic Ecosystems 2026–2027", "claim-0012"),
    ("Autonomous AI containment failure", "claim-0024"),
    ("Containment-by-design: signed inter-agent", "claim-0027"),
    ("MCP 10× efficiency", "claim-0005"),
    ("Dharma Engine — ethical governance", "claim-0006"),
]


def matched_ledger_ids(site, pre):
    led_sets = [
        (c["id"], norm(c["statement"] + " " + str(c.get("predicted_outcome", ""))))
        for c in pre
    ]
    matched = set()
    unmatched = []
    for r in site:
        hit = next((lid for pfx, lid in ALIAS_MAP.items() if r["id"].startswith(pfx)), None)
        if hit is None:
            rs = norm(r["claim"])
            lid, j = max(
                ((lid, jac(rs, ls)) for lid, ls in led_sets),
                key=lambda x: x[1],
                default=(None, 0),
            )
            if j >= 0.28:
                hit = lid
        if hit is not None:
            matched.add(hit)
        else:
            unmatched.append(r)
    for r in unmatched:
        hit = next((lid for needle, lid in TEXT_ALIASES if r["claim"].startswith(needle)), None)
        if hit:
            matched.add(hit)
    return matched


def map_row(c, created_at: str) -> dict:
    lid = c["id"]
    status = c["status"]
    ve = c.get("validation_event") or {}
    new_id = str(uuid.uuid5(UUID_NS, f"https://whitemagic.dev/ledger/{lid}"))
    source_ref = (
        f"Ledger-bridged {lid} ({c.get('domain')}) — no independent site "
        f"dossier; evidence as recorded in docs/CLAIMS_LEDGER.json. "
        f"Validation source: {ve.get('source', 'n/a')}. "
        f"Falsification criterion: {c.get('falsification_criteria', 'n/a')}"
    )
    notes_bits = [
        f"Ledger-bridged row ({lid}); not part of the original site register cohort.",
        f"Ledger statement verbatim; predicted outcome: {c.get('predicted_outcome', 'n/a')}",
        f"Falsification criterion: {c.get('falsification_criteria', 'n/a')}",
    ]
    if c.get("disposition"):
        notes_bits.append(f"Ledger disposition: {c['disposition']}")
    if status == "falsified":
        notes_bits.append(
            "FALSIFIED — the recorded validation event settled the claim "
            "against the prediction. Scored 0 points; retained for an honest record."
        )
    row = {
        "id": new_id,
        "claim": c["statement"],
        "source_date": days_to_iso(c["source_date"]),
        "source_ref": source_ref,
        "confidence": c["confidence"],
        "category": c.get("domain") or "ai_trends",
        "status": status,
        "validation_date": None,
        "validation_ref": None,
        "lead_weeks": c.get("lead_time_weeks"),
        "points": c.get("points"),
        "notes": " ".join(notes_bits),
        "created_at": created_at,
        "behavioral_confidence": c["confidence"],
        "claim_type": "binary",
        "oracle_source": None,
        "oracle_hexagram": None,
        "guidance_action": None,
        "action_taken": 0,
        "consensus_date": None,
        "consensus_ref": None,
    }
    if status in ("validated", "falsified") and ve:
        row["validation_date"] = days_to_iso(ve["date"]) if ve.get("date") else None
        row["validation_ref"] = f"{ve.get('event', '')} ({ve.get('source', '')})"
    if status == "pending":
        row["lead_weeks"] = None
        row["points"] = None
    return row


def main() -> int:
    doc = json.load(open(SITE))
    claims = doc["claims"]
    summary = doc["summary"]
    ledger = json.load(open(LEDGER))["claims"]
    pre = [c for c in ledger if "register_ref" not in c]
    assert len(claims) == 81, f"expected 81-row cohort, found {len(claims)}"
    assert len(pre) == 32, f"expected 32 pre-existing ledger rows, found {len(pre)}"

    matched = matched_ledger_ids(claims, pre)
    assert len(matched) == 17, f"match drift: {len(matched)} != 17: {sorted(matched)}"
    only = [c for c in pre if c["id"] not in matched]
    assert len(only) == 15, f"expected 15 ledger-only rows, found {len(only)}"

    # Guard: verify aggregation rules reproduce the published 81-block
    # before applying them to the new cohort. Tolerances are rounding-honest:
    # the published block carries 4dp (Brier/BSS), 1dp (points/leads).
    vals = [c for c in claims if c["status"] == "validated"]
    brier = sum((1 - c["confidence"]) ** 2 for c in vals) / len(vals)
    assert abs(brier - summary["brier_score"]) < 5e-5, "Brier method drift"
    bss = 1 - brier / 0.25
    assert abs(bss - summary["brier_skill_score"]) < 5e-5, "BSS method drift"
    pts = sum(c["points"] for c in vals if c.get("points") is not None)
    assert abs(pts - summary["total_points"]) < 0.05, "points rule drift"
    leads = [c["lead_weeks"] for c in vals if c.get("lead_weeks") is not None]
    assert abs(sum(leads) / len(leads) - summary["avg_lead_weeks"]) < 0.05, "lead rule drift"

    created_at = datetime.now(timezone.utc).isoformat()
    new_rows = [map_row(c, created_at) for c in sorted(only, key=lambda c: c["id"])]
    cohort = claims + new_rows

    n_val = [c for c in cohort if c["status"] == "validated"]
    brier96 = sum((1 - c["confidence"]) ** 2 for c in n_val) / len(n_val)
    leads96 = [c["lead_weeks"] for c in n_val if c.get("lead_weeks") is not None]
    cats: dict = {}
    for c in cohort:
        cats[c["category"]] = cats.get(c["category"], 0) + 1

    note_add = (
        "2026-09-04 regen (site_prescience_regen_96.py): merged-ledger-only rows "
        "folded in — 15 rows (4 validated / 10 pending / 1 falsified; claim-0015…0019 "
        "carry the ledger's novel-unique pending-no-window disposition). Cohort now "
        "96 (74 validated / 20 pending / 1 expired / 1 falsified). MCP 10x keeps the "
        "REGISTER verdict (validated) per the no-silent-demotion rule — the ledger's "
        "pending verdict on claim-0005 stands flagged, unresolved. New rows are "
        "ledger-bridged (evidence as recorded in docs/CLAIMS_LEDGER.json, no "
        "independent site dossier; behavioral_confidence = stated, no post-hoc "
        "uplift). Brier/BSS recomputed by the verified method over 74 validated; "
        "brier_index / calibration_gap / ecce CARRIED from the 70-cohort block "
        "pending methods recovery (archived generator) — see methods_note."
    )
    summary.update(
        {
            "total": len(cohort),
            "validated": len(n_val),
            "pending": sum(1 for c in cohort if c["status"] == "pending"),
            "expired": sum(1 for c in cohort if c["status"] == "expired"),
            "falsified": sum(1 for c in cohort if c["status"] == "falsified"),
            "total_points": round(
                sum(c["points"] for c in n_val if c.get("points") is not None), 1
            ),
            "avg_lead_weeks": round(sum(leads96) / len(leads96), 1),
            "brier_score": round(brier96, 4),
            "brier_skill_score": round(1 - brier96 / 0.25, 4),
            "categories": cats,
            "methods_note": (
                "brier_index / calibration_gap / ecce and the top-level "
                "calibration bins below still describe the "
                "2026-08-31 70-validated cohort; their computation methods live in "
                "the archived core generator and were not reinvented. Brier/BSS "
                "recomputed 2026-09-04 over 74 validated by the verified method."
            ),
            "notes": (summary.get("notes") or "") + " " + note_add,
        }
    )
    doc["claims"] = cohort
    # Match the file's existing serialization (indent=2, ensure_ascii, no
    # trailing newline) so the diff stays review-sized.
    with open(SITE, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=True)
    print(f"matched=17 ledger_only=15 cohort={len(cohort)}")
    print(
        "summary: total={total} validated={validated} pending={pending} "
        "expired={expired} falsified={falsified} points={total_points} "
        "avg_lead={avg_lead_weeks} brier={brier_score} bss={brier_skill_score}".format(**summary)
    )
    print("categories:", cats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
