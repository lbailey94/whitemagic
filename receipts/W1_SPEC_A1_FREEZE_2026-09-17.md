# RECEIPT — Wave-1 spec A1 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_A1_durable_store_ingestion.md` — Wave-1 spec A1, **durable store + ingestion gate** |
| **SHA-256** | `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3` |
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

- **Frozen behavioral spec** — intake contract (`RememberItem{content, source, kind}`; immutable
  evidence domains); refusal contract (journaled, fail-closed: `write budget exceeded
  (fail-closed)`, `duplicate_exact`, typed governance/starvation refusals); the exact-hash gate
  with identity key **(content SHA-256, source, kind)**, per scope — identical bytes with
  different context do not collapse; **the Gen3 journal is the disclosure surface** (the Gen2
  `write_gate` short-circuit may not absorb silently); near-dup out of scope (declared battery
  only); noise quarantined/refused, never purged; statutory parameters named (fail-closed budget;
  import tier fixed `persistent`); journal events `ingest.batch`, `remember.refusal` (the
  `duplicate_exact` vocabulary is **owned by this spec**).
- **Selection history** — v26 `deduplication.py` + content-hash primitives + 0.85 tag-Jaccard
  filter (errata A#3); cleanup-not-gate failure (37.2 % inventory dup, errata #23 scope);
  Gen2 path-idempotence capability source; Gen3 `remember` contract; per-statement evidence
  levels.
- **Adversarial cases** — 9.1.7 Tier-1 (#5 drift, #6 atomic-vs-partial, #4 write-gate bounds,
  #1 sentinel byte-preservation) + findings battery (cross-scope duplicates, context non-collapse,
  near-dup ban, purge-vs-quarantine) + 9.1.8 additions (starvation-vs-refusal, strict-mode
  refusal).
- **Ablation** — exact-hash gate on/off: `duplicate_exact` count N→0, record count unchanged→+N,
  persistence across restart, and the negative assertion that retrieval ordering does not change
  (a gate, not a scorer); RE-ENTERS not claimed.
- **Acceptance** — seven wrapper-side assertions (duplicate refusal, context non-collapse, scope
  law, drift, partial, byte-preservation, noise) with counts generated from journals; **no inert
  acceptance test**.
- **Owner: Lucas Bailey (operator)** — assigned at ratification.

## 4. Verification

Docs-only artifact: no code, gates, thresholds, or verdicts changed; no build/test run required
(nothing executable changed). At compilation:

- Spec sha256 recorded above; `docs/NUCLEUS.md` re-hashed `73c5a9cf…` and
  `docs/PHASE4_WAVE_PLAN.md` re-hashed `60688d72…` — both match the ratified pins.
- Citations line-checked against the frozen source: `crates/wm-gen3-core/src/ops.rs:79-90`
  (intake types), `:357-364` (budget accessors), `:412-417` (budget refusal), `:446-450`
  (`ingest.batch`); canary C6 verb→event inventory (remember → `ingest.batch`); F4 guard at
  `ops.rs:751` (nucleus §5).
- Adversarial sources read at their pinned texts: 9.1.7 scope Tier 1; delta §3.2; W1 findings
  row 1 + divergences #1. No live-data item is cited as measured (errata §E boundary respected).

## 5. Companion hashes (batch-A unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_A1_durable_store_ingestion.md` (frozen) | `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3` |
| `docs/specs/W1_A2_evidence_disclosure.md` (frozen) | `aa84a5acbec704204bc808c300ebde6d6ff0976b8ffc9b64c2cfaf99a2631fda` |
| `docs/specs/W1_A3_revisions_supersession.md` (frozen) | `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec A1 is frozen.** Implementation of the gate still requires its own unit under the row's
  gate with its own demonstration; adversarial cases must be wired as runnable acceptance
  assertions before the row can exit (wave plan §2 exit criteria).
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK; ledger stays at 8 claims.
- The `duplicate_exact` vocabulary is owned by this spec; any new refusal reason is added here
  first.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_A1_durable_store_ingestion.md`, verified every pin
and citation listed above, and recorded the operator's ratifying act and owner assignment.
Ratification is an external operator act; this receipt records it — it does not itself ratify.
