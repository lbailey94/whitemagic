# RECEIPT — Wave-1 spec A2 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_A2_evidence_disclosure.md` — Wave-1 spec A2, **evidence disclosure** |
| **SHA-256** | `aa84a5acbec704204bc808c300ebde6d6ff0976b8ffc9b64c2cfaf99a2631fda` |
| Compiled per | `docs/PHASE4_WAVE_PLAN.md` §7 (cross-cutting spec template) + §9 batch A, under the frozen nucleus `docs/NUCLEUS.md` (`73c5a9cf…`) |
| Tip at compilation | `b7565ee` (tree clean at compile; freeze unit commits with this receipt) |
| Rule | Any edit after ratification is a new version with its own amendment receipt (wave plan §9; additive errata only) |

## 2. Operator act — RECORDED

Freeze path and owner assignment prompted in session, 2026-09-17; operator selections recorded
verbatim: **"Assign owners + ratify (Recommended)"** and **"I think we can take care of
everything now in this session; no other work is being done on gen3 currently."**

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | Explicit in-session ratification + owner assignment + commit authorization |
| Owner assigned | Lucas Bailey (operator) — recorded in §3; no other gen3 work in flight at assignment |
| AI attestation | Session `c7ab9666` compiled the spec, line-checked every source citation, verified pins, and prepared this receipt — attestation only |

## 3. What was ratified

- **Frozen behavioral spec** — retrieval never silently claims absence; closed abstention
  vocabulary (`no_query_tokens` / **`insufficient_evidence`** — one vocabulary, named here; the
  current `no_candidates` reason maps to it at implementation, mapping recorded); floors declared
  per invocation (statutory pin `--min-score 0 --min-coverage 0`) and **fail-closed** on
  out-of-range (the 9.1.7 `min_trust` defect class); provenance chain per result
  (`provenance.chain`, H4 completeness) + selection explanations (`selection.decision`); **no
  swept thresholds, ever** (v26 0.50 is DO_NOT_MIGRATE #10-class); link boundary fixed — Gen2
  evidence bundle v0 = product surface, Gen3 journal = evidence surface, divergences are
  findings; degraded routes disclose explicitly; journal events `selection.decision`,
  `provenance.chain` (the `insufficient_evidence` token is **owned by this spec**).
- **Selection history** — v26 `abstention_gate.py` (threshold-based, opt-in; default-flow reach
  UNVERIFIED) → Gen2 **transformed** into declared floors + explicit insufficiency + bundle v0
  (E4 errata, landed); Gen3 journal contract (E4, N1/N3/N4/N5); per-statement evidence levels.
- **Adversarial cases** — 9.1.7 Tier-1 (#3 floor bounds fail-closed, #5 drift disclosure, #6
  partial success) + findings battery (no swept-threshold regression, LABEL/state-conflict flags
  visible with no score nudge, cold-record disclosure, route degradation) + 9.1.8 additions
  (read-only discipline, starvation-vs-refusal distinction).
- **Ablation** — disclosure on/off: `insufficient_evidence` emissions 1→0, chain completeness
  100 %→uncomputable, silent-empty count 0→>0, journal hash-out linkage (N4) as the persistence
  instrument; RE-ENTERS not claimed (disclosure explains, it does not order).
- **Acceptance** — six wrapper-side assertions (C4 completeness, explicit insufficiency, floor
  bounds, vocabulary uniqueness, audit visibility, degraded-route honesty) with counts generated
  from journals; **no inert acceptance test**.
- **Owner: Lucas Bailey (operator)** — assigned at ratification.

## 4. Verification

Docs-only artifact: no code, gates, thresholds, or verdicts changed; no build/test run required
(nothing executable changed). At compilation:

- Spec sha256 recorded above; `docs/NUCLEUS.md` re-hashed `73c5a9cf…` and
  `docs/PHASE4_WAVE_PLAN.md` re-hashed `60688d72…` — both match the ratified pins.
- Citations line-checked against the frozen source: `crates/wm-gen3-core/src/ops.rs:93-100`
  (`RecallQuery`), `:103-110` (`Hit`), `:460-466` (`no_query_tokens` abstention), `:679-685`
  (`provenance.chain`), `:687-695` (`selection.decision` summary + `abstained`); canaries C4/C6.
- Adversarial sources read at their pinned texts: 9.1.7 scope Tier 1; delta §3.2; W1 findings
  (E4 errata; W1_retrieval abstention ancestry). No live-data item is cited as measured
  (errata §E boundary respected).

## 5. Companion hashes (batch-A unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_A2_evidence_disclosure.md` (frozen) | `aa84a5acbec704204bc808c300ebde6d6ff0976b8ffc9b64c2cfaf99a2631fda` |
| `docs/specs/W1_A1_durable_store_ingestion.md` (frozen) | `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3` |
| `docs/specs/W1_A3_revisions_supersession.md` (frozen) | `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec A2 is frozen.** Implementation of the vocabulary mapping and the fail-closed floor
  behavior still requires its own unit under the row's gate with its own demonstration;
  adversarial cases must be wired as runnable acceptance assertions before the row can exit
  (wave plan §2 exit criteria).
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger stays at 8 claims.
- The `insufficient_evidence` token is owned by this spec; aliases are spec revisions, not
  runtime decisions.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_A2_evidence_disclosure.md`, verified every pin and
citation listed above, and recorded the operator's ratifying act and owner assignment.
Ratification is an external operator act; this receipt records it — it does not itself ratify.
