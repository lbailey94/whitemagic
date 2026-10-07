# Row-exit packet — A1 · A2 · A3 · B1 (for operator review)

**Prepared 2026-09-17 (session `68c17d3b`) · updated with closures · status: RATIFIED 2026-09-17 —
A1/A2/A3/B1 exited (see receipts `W1_ROW_EXIT_*_2026-09-17.md`).** Wave plan §2 exit criteria:
frozen spec + adversarial cases wired + ablation designed/demonstrated + journal events declared +
receipt; **no inert acceptance test**. This packet changes no verdict, claim, or gate.

---

## A1 — Durable store + ingestion gate

**Spec:** rev 2 `d437ffed…` (freeze `W1_SPEC_A1_FREEZE`, amendment `W1_SPEC_A1_AMEND_2026-09-17`).
**Implementation:** gate `8c5e32f`, noise table `c12179d`; fixtures `726ccfa`.
**Acceptance §5:** items 1–7 all wired and passing (`IMPL_A1_GATE`, `IMPL_A1_FIXTURES`).
**Ablations §4:** gate on/off (controlled re-ingest), noise table `WM_GEN3_NOISE=0` — both
demonstrated.

**Adversarial case map:** 1 drift ✓ fixtures · 2 partial ✓ · 3 write-gate bounds ✓ (refusal landed —
`IMPL_EXIT_CLOSURES_2026-09-17`) · 4 sentinel ✓ (byte-identical `data.mdb`) · 5 scope ✓ ·
6 context non-collapse ✓ (source wrapper + kind unit test) · 7 paraphrase admission ✓ (assertion
landed) · 8 noise ✓ rev 2 · 9 starvation ✓ (A2 discipline) · 10 strict mode — **declared N/A**
(no strict-mode construct; the readonly typed refusal is the nearest evidence).

**Disposition:** READY — conditions closed.

---

## A2 — Evidence disclosure

**Spec:** `aa84a5ac…`; acceptance status recorded complete (`IMPL_A2_VOCAB`, `IMPL_A2_FLOOR_BOUNDS`,
`IMPL_A2_DISCIPLINE`).
**Coverage:** items 1/7/8/9 demonstrated (floor bounds incl. NaN/±Inf; read-only discipline;
starvation-vs-refusal; degraded-route honesty); 2/3 folded to A1 (drift/cold: no separate index, no
cold tier); 4/5 statute/wrapper (vocabulary ownership; wrapper disclosure); 6 N/A (cold tier).
**Adversarial §3:** floor bounds ✓ · drift folded ✓ · partial ✓ (A1) · LABEL flags visible ✓
(testbed-audit discipline cited) · read-only ✓ · starvation ✓ · C4 ✓ (canary).

**Parity:** landed (`OPS_FOLDIN_PARITY_AUDIT_2026-09-17`; `docs/BUNDLE_JOURNAL_PARITY.md`).

**Disposition:** READY — Gen3 side complete, parity done.

---

## B1 — Retrieval & ranking

**Spec:** `9b293d01…`; acceptance `IMPL_B1_ACCEPTANCE_2026-09-17`.
**Coverage:** 1 frozen-corpus 0-diff ✓ (reference ≡ recorded C00/C01; candidate ≡ reference on the
gate-neutralized corpus) · 2 C2/C3 templates ✓ (`CANARY_RERUN`) · 3 rank-field audit ✓ ·
4 floors ✓ (A2 bounds, same path) · 5 no-planner ✓ (source + constants + deps + behavioral 0-diff).
**Adversarial §3:** 1 optional-stage reordering ✓ (0-diff; C3) · 2 no implicit filtering —
**THIN** (no tag-Jaccard organ via scan; shared-tag fixtures admitted, but no dedicated assertion) ·
3 warm-up determinism ✓ (`d2_deterministic`) · 4 no score nudges ✓ · 5 floors ✓ · 6 drift ✓ (A1) ·
7 read-only ✓ (A2 + W2_07) · 8 starvation ✓ (A2).

**Closure landed:** case 2 assertion (`IMPL_EXIT_CLOSURES_2026-09-17`: tag-sharing records admitted
and retrievable).

**Disposition:** READY.

---

## A3 — Revisions/supersession

**Spec:** rev 2 `bf4d3b53…` (amendment `W1_SPEC_A3_AMEND_2026-09-17`; case 1 operator-ratified as a
**declared, measured property** of lexical rule v1). **Acceptance:**
`IMPL_A3_ACCEPTANCE_2026-09-17`.
**Coverage:** §5 items 1–7 — direction + flip (driver), F4 raw/deduped metric (driver: raw 5 /
deduped 1), history-lossless (driver), round-trip (driver + C5), C2/no-nudge/TBII (cited);
§3 cases 1 (declared property; rule v2 gated — errata §H #34), 2 (declared N/A: intake always
stamps `created_at`; intake-time rule only), 3–9 (drivers/citations per the acceptance receipt).

**Disposition:** READY — exits on the declared-property basis.

---

## Program-level notes (not row gates)

- The recorded all-off cells predate the A1 gate; regression claims on those corpora require the
  gate-neutralized recipe (`IMPL_B1_ACCEPTANCE` §3) — institutionalization decision pending (§4
  item a).
- Binary pins are instance labels, not reproducible artifacts — wording decision pending (§4 item b).

## Operator act — RATIFIED 2026-09-17

- [x] A1 exit ratified — Lucas Bailey (operator) — 2026-09-17 · receipt `W1_ROW_EXIT_A1_2026-09-17.md`
- [x] A2 exit ratified — Lucas Bailey (operator) — 2026-09-17 · receipt `W1_ROW_EXIT_A2_2026-09-17.md`
- [x] A3 exit ratified — Lucas Bailey (operator) — 2026-09-17 · receipt `W1_ROW_EXIT_A3_2026-09-17.md`
- [x] B1 exit ratified — Lucas Bailey (operator) — 2026-09-17 · receipt `W1_ROW_EXIT_B1_2026-09-17.md`

Recorded by the attesting session `68c17d3b` per the operator's in-session directive (verbatim:
**"you have my go-ahead - sign the doc"**); ratification is the operator's act — the session
records it, it does not ratify.
