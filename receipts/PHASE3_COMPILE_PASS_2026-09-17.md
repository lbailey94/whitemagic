# RECEIPT — Phase-3 compile pass ratified (2026-09-17)

**Status: recorded.** Ratifying act: operator (Lucas Bailey), in session, 2026-09-17.
AI session `0f72a7a6-bec9-4d36-b516-501b655f05e2` prepared and attests. Append-only;
corrections create a new receipt referencing this one.

---

## 1. Ratified text

`docs/PHASE3_DECOMPOSITION.md` — **sha256
`cb8235e9f8e70583cdc84a18da1efe4b75b216bac6c2b1b00b5b43b81846102a`** (status line: §2.1–§2.4
verdicts effective; §2.1–§2.4 tables filled; evidence keys E1–E24).

Entry-gate act (prerequisite): `docs/PHASE3_ENTRY_DECISION.md` ratified
(`receipts/PHASE3_ENTRY_DECISION_2026-09-17.md`, text hash `27d540b7…`).

## 2. What was ratified

The **complete Phase-3 verdict set** — all 33 capability families across §2.1 memory
core/retrieval, §2.2 sessions/coordination/identity, §2.3 cognition/epistemics, §2.4
governance/security/distribution — each with a verdict (or split verdict), a destination, and
an evidence key or lineage citation:

| Disposition | Representatives |
|---|---|
| **COMPOSES CLEANLY → compile** | durable store · retrieval & ranking (earned subset) · evidence disclosure · revisions/supersession · associations (typed edges) · galaxies · ingestion gates · continuity/digest · claims (belief class) · effects/capability gate · canaries |
| **COMPOSES AWKWARDLY → compile** | citta/cycles (missing-primitive candidate: activation/decay field with operational regime parameter) · engines/recipes (missing-primitive candidate: operator vocabulary + recipe runtime) |
| **PRESERVE IMPLEMENTATION → link** | retention/lifecycle · compartments · session records/lifecycle · coordination · Gan Ying/resonance · self-model/conformal · RSI/friction · reflex/sensor/actuator · firebreak · dharma/karma · resource/homeostasis · sandbox · ops/telemetry · violet (engagement tokens + model signing) · drive (autonomic) · god.nodes (analytics) |
| **EXPERIMENT (manifest-gated)** | constellations/emergence · memetic lineage/Geneseed (Phase-4 gated) · simulation/imagination · mesh/agents (deferred, two-gate boundary) |
| **RETIRE → docs + lineage** | identity/lineage (runtime practice forms; provenance duty already carried) · monetary economy (XRP family) · `bagua.dispatch` (literal symbolic dispatch) · `council.deliberate` (zodiac council ruling) |

**No `IRREDUCIBLE` row was needed** — no family showed a general failure of the substrate
basis; the two AWKWARDLY rows name missing primitives as *candidates* gated on experiments,
not features.

## 3. Acceptance checklist (compile-pass §5)

| Criterion | Result |
|---|---|
| Every route family has a row | ✓ — 33 families, 302-route inventory basis |
| Non-trivial verdicts cite evidence or lineage ruling | ✓ — E1–E24 + LINEAGE_LEDGER/CHARTER citations |
| Nothing retires without a citation | ✓ — identity (ledger ruling, homecoming gate), economy (obsolete-by-design ruling + revisit condition), bagua (Charter §3.10 + i_ching never-by-design), council (v5 ruling) |
| Every EXPERIMENT row carries the manifest rule | ✓ — ancestor · wire · acceptance named for all four; **owners unset, disclosed**; Geneseed/mesh gates explicit (Phase-4 / two-gate) |
| Operator ratifies | ✓ — in-session, 2026-09-17 |
| Receipt lands | ✓ — this file |

## 4. Shipped-vs-dormant + symbolic audit (the pass's verification work)

Run against the pinned 9.1.7 contract (302 routes) and WMv9 source. Four verdicts changed as a
result — recorded so the dispositions don't get re-derived from names:

1. `violet.*` = **engagement tokens + model signing** (`violet.rs`, `capability_gate.rs`;
   Ed25519 issue/validate/revoke; scope-derived capability coverage verified at dispatch) —
   a real security capability that **closes the v5-era scope-token gap**; misfiled as symbolic,
   now preserved.
2. `drive.*` = autonomic **DriveState** machinery; `god.nodes` = **graph hub analytics**
   (`correlation.rs`) — both misfiled, now preserved.
3. `bagua.dispatch` = the **only literal symbolic dispatch** in the 302-route audit
   (trigram→tool router "grounded in I Ching cosmology") — retired under Charter §3.10.
4. `bounty.*` = **submission/outcome ledger** (JSONL, rejection-reason taxonomy), not the XRP
   economy — the monetary family stays retired under the lineage ruling while the shipped
   non-monetary surface is preserved.

## 5. Companion artifact hashes (this unit)

| Artifact | sha256 |
|---|---|
| `HANDOFF.md` (session block updated: §2.1–§2.4 + audit findings) | `63658068f210e95e664acc08a248391b976869083d5b5d03df5e92434e2ea0cf` |
| `docs/PHASE3_ENTRY_DECISION.md` (ratified; unchanged) | `27d540b7e3f4e3fe3ae0ae7969ea6a65615de1b4248b271906f2bb2dff170c24` |
| `docs/NUCLEUS_FREEZE_CRITERIA.md` (draft; reviewed) | `25573f44bab23710b5bb50629a86b0e03e722a172a2b9b2b8816bccad37d1b36` |
| `docs/PHASE3_COMPILE_PASS.md` (method; unchanged since pointer edit) | `d5ba6791bd5ffd02bb7dff4d3b11b1536211e5b388e2bee5d2c4efb2e0963ce7` |
| wmv9 claims ledger (unchanged this unit) | `d94c0cb3d9ebb61ba25a96736931b594844a6a1959c315d0ff388aa380c0e4ed` |

## 6. Consequences

- **Phase 3 is complete on paper**: the compile pass has verdicts + destinations; the ledger
  row set is the working authority for Phase-4 re-expression.
- The **nucleus-freeze criteria** (`NUCLEUS_FREEZE_CRITERIA.md`) are the next governance
  artifact; the freeze itself happens between Phase 3 and Phase 4, after this pass, per its own
  procedure (compile artifact → verify pins → canaries → operator ratification → receipt).
- **Phase-4 fusion is gated** on the nucleus freeze and follows the governing rule: Gen1/Gen2
  provide capabilities and evidence, not architecture; each capability migration needs a frozen
  behavioral spec + 9.1.7's fix list as adversarial tests + wrapper-side evaluation + ablation.
- No thresholds, weights, claims, or gates changed; the WEAK arbitration claim and the parked
  ≥2 boundary are untouched.

## 7. Attestation

AI session `0f72a7a6` prepared the pass, ran the shipped-vs-dormant audit, verified the final
bytes, and prepared this receipt. Ratification is an external operator act; this receipt records
it — it does not itself ratify.
