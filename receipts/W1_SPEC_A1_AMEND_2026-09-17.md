# RECEIPT — Wave-1 spec A1 amendment rev 2 ratified (2026-09-17)

**Status: FROZEN rev 2 — 2026-09-17.** Operator ratified in session; rev 2 is in effect as the
frozen behavioral contract for its row, additive to rev 1. AI session
`68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) prepared, verified, and attests; it does not
ratify. Append-only; corrections create a new receipt referencing this one.

---

## 1. Amended artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_A1_durable_store_ingestion.md` — Wave-1 spec A1, **durable store + ingestion gate** |
| **rev 2 SHA-256** | `d437ffed1e1ecb04720b4d4dcc599a4b0abc24de2b5c15fc3a7add4c73539176` |
| Supersedes | rev 1, sha256 `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3` (freeze receipt `receipts/W1_SPEC_A1_FREEZE_2026-09-17.md`) |
| Rule | Any further edit is a new version with its own amendment receipt (freeze receipt §1; additive history only) |

## 2. Operator act — RECORDED

The operator reviewed the amendment as a drafted diff, requested an explicit pros/cons discussion
of ratify-as-drafted vs adjustment (recorded in-session), and then ratified. Selection recorded
verbatim: **"Ratify as drafted (Recommended)"**. Operator: **Lucas Bailey**. Act: explicit
in-session ratification + commit authorization.

## 3. What changed in rev 2 (disposition amendment)

- **§1.3 — noise disposition named:** traceback-class noise = **refuse-with-journal** (Gen3 has no
  quarantine organ: no quarantined state, no lifecycle, no release). Declared class table
  (content-pattern, kind-independent, rule-based): `traceback` · `error_line` · `json_blob` ·
  `function_repr` · `too_short` (`content.trim()` length < 10). Check precedence: write budget →
  noise class → duplicate. Disclosed cost accepted: false positives block admission, including
  `kind = System` tracebacks.
- **§1.2 / §1.5 — vocabulary:** `remember.refusal` reason `noise_class` (with `class` from the
  declared table, plus the refused item's `content_sha256` + `source`); `duplicate_exact` row now
  marked implemented (`8c5e32f`).
- **§1.4 — constant named:** the `too_short` bound `< 10` is the table's only numeric parameter
  (v26 provenance; not tuned, not swept; changed only by a spec revision).
- **§4 — ablation:** the noise class table (`WM_GEN3_NOISE=0`, default on): refusals N → 0, items
  admitted (+N, recallable), ordering unchanged on/off (negative assertion; intake hygiene, not a
  scorer).
- **§5 item 7 — acceptance rewritten** per class with controls, zero-write/zero-purge assertions,
  and the ablation; **§5.1 revision history** added; header updated (rev 1 frozen / rev 2 ratified).

## 4. Decision record — alternatives considered and rejected

| Alternative | Rejected because |
|---|---|
| Admit + display-only flag (quarantine surrogate) | Record-layout/schema change; acceptance weaker; inert-passenger risk |
| Scope out detection (negative-only acceptance) | Weakens the row battery (findings item 8); still needs a revision |
| Swap `too_short` → `empty` (exact, no numeric constant) | Considered in the pros/cons discussion; declined — disposition-only amendment stays faithful to the rev-1 declared class set; any class change re-baselines the class-table evidence and can follow its own revision if experience shows misfires |
| Drop the length class entirely | Same as above; 1–9-char junk stays catchable |
| Scope the table to non-`System` kinds | Re-opens the v26 junk-flood channel the filter existed for |

## 5. Verification

Docs-only artifact: no code, gates, thresholds, or verdicts changed; no build/test run required.
At ratification:

- rev 1 hash verified **before** editing: `cf638395…` matched the freeze receipt.
- rev 2 hash recorded above; `docs/NUCLEUS.md` re-hashed `73c5a9cf…` and
  `docs/PHASE4_WAVE_PLAN.md` re-hashed `60688d72…` — both match the ratified pins.
- Carry rules unchanged: counts generated; WEAK stays WEAK; ledger 8 claims; 9.1.7 control never
  re-baselined.

## 6. Consequences

- **A1 rev 2 is frozen.** The noise refusal (`noise_class`) is now a spec-owned implementation
  target; it still requires its own implementation unit + demonstration under the row's gate, and
  the §5 item 7 acceptance must be wired as a runnable assertion before the row exits.
- No verdict, claim, gate, or threshold changes.

## 7. Attestation

AI session `68c17d3b` drafted rev 2, verified every pin and hash listed above, ran the operator
discussion, and recorded the ratifying act. Ratification is an external operator act; this receipt
records it — it does not itself ratify.
