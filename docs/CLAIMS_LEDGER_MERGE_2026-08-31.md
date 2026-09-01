# Claims Delta-Merge — 2026-08-31

**Method:** GALACTIC_TIMELINE DD5 recipe, executed deterministically
(`scripts/`-style one-shot; no clock reads). Content-keyed dedup
(normalized-statement Jaccard ≥ 0.28 auto + 17 hand-curated aliases
reviewed in the 0.15–0.28 band, incl. the Karma-Ledger pair DD5 names).

## Numbers

- Register rows: **81** (70 validated / 10 pending / 1 expired)
- Ledger rows before: **32** (19 validated / 1 falsified / 12 pending)
- Content-matched pairs (register ↔ ledger): **17** — matched ledger rows left byte-identical (backfill, not import)
- Backfilled new ledger rows: **64** = 54 validated + 9 pending + 1 expired
- Ledger rows after: **96** (next_id → 96)

## Authored falsifiers (the 10 register pendings, per DD5)

- **End of conflict / world constitution…** — No national or international body adopts AI-weighted voting or a formally restructured UN-style governance charter by 2030-12-31
- **Game theory / iterated cooperation…** — No major multi-agent platform ships reputation-and-memory-based enforcement as its primary governance substrate by 2027-12-31
- **AI-revolutionized municipal services…** — No municipality runs AI-architected emergency services end-to-end (dispatch→response→review, beyond single-site RTCC-class deployments) by 2028-06-30
- **SMR / microreactor LEASING…** — No commercial 5-MW-class SMR/microreactor lease with independent on-chain power/heat metering is signed by 2028-12-31
- **Citta substrate…** — NOVEL/UNIQUE (WM-internal, pending-no-window): no third-party consciousness-primitives-as-a-service surface for agents exists by 2028-06-30 — a third-party analog would resolve the claim, its absence leaves it pending, not falsified
- **Neuro-upgrade ensemble…** — NOVEL/UNIQUE (WM-internal, pending-no-window): no third-party unified agent sensorium integrating 9+ neuro-inspired subsystems ships by 2028-06-30 — same pending-not-falsified semantics
- **Edge models become micro-botnets…** — No documented on-device-LLM botnet performing lateral movement without cloud C2 by 2027-06-30
- **Containment-by-design: signed inter-agent…** — Fewer than two major labs/platforms ship signed inter-agent messaging with quarantine semantics by 2026-12-31 (per the DD5 record)
- **Casimir-cavity vacuum-energy chips…** — No independently verified net-continuous-power Casimir-cavity chip in commercial shipment by 2028-12-31 (vendor target: Casimir Inc 2028)
- **Cavity vacuum-fluctuation engineering…** — No published use of cavity vacuum-fluctuation engineering to modify (not merely measure) material properties by 2028-06-30 (direction marker: Nature 645, Aug 19 2026)

## Novel/Unique disposition (the 7 WM-internal claims)

The seven claims with no possible external validation event — the ledger's
claim-0015 (Constitutional DSL), claim-0016 (echo-chamber detection),
claim-0017 (SutraCode), claim-0018 (bicameral primitive), claim-0019 (voice
audit) plus the register's Citta-substrate and Neuro-upgrade-ensemble rows —
are dispositioned **`novel-unique: pending-no-window`**: they remain pending,
can only be resolved by a third-party analog appearing, and are never counted
as falsified for continuing to exist. *yin teh* preserved: the unlogged virtue
stays unpriced.

## Status divergences flagged (not auto-resolved)

- register **validated** vs ledger **pending** — MCP 10× efficiency — empirical benchmark showing 10× token/speed improvement… (`claim-0005`) — flagged for the claims tool's review pass; no silent promotion

## Expired row

- The register's expired Darwin-Gödel-Machine row keeps status `expired`
  (window elapsed, event did not occur) rather than being flattened to
  `falsified` — the source register's distinction is respected.

## Site calibration regen (found by the ledger bridge, 2026-08-31)

- The site's published Brier block (0.1129 / BSS 0.5485 / BI 66.4) is the
  **stale Aug-28 60-claim state**; over the current 70 validated the stack
  recomputes **Brier 0.1215**. Regen via `generate_prescience_json.py` →
  `db.export_summary()` queued for the site track (Stage-0 containment respected).

---

*Merge executed by the synthesis session `4860fcce` (2026-08-31). Ground
truth: `whitemagic-site/public/api/prescience.json` (mtime Aug 29 12:53,
81 rows). Raw confidences never edited; matched rows untouched.*
