# RECEIPT — Nucleus freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the freeze is in effect and gates
all Phase-4 re-expression. AI session `f46d94c5-f8bb-4697-a53f-5e944c913540` (opencode) prepared,
verified, and attests; it does not ratify. Append-only; corrections create a new receipt
referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/NUCLEUS.md` — four-part snapshot (constitutional core · earned cognitive nucleus · statutory baseline · reproducibility pins) |
| **SHA-256** | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |
| Compiled per | `docs/NUCLEUS_FREEZE_CRITERIA.md` §4 (draft text pinned: `2d311e08ccb32aad0947163f26e6a33c369f4c7725fdc6f929e735fc41ed773a`) |
| Tip at compilation | `7ff9181` (tree clean at compile; freeze unit commits with this receipt) |
| Rule | Any edit after ratification is a new version with its own amendment receipt (criteria §5; Charter §4) |

## 2. Operator act — RECORDED

Prompted ratification of the nucleus freeze at the artefact hash above; operator act, in
session, 2026-09-17: **"Ratify + commit unit."**

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | Explicit in-session ratification (selection recorded verbatim above; commit authorization included) |
| AI attestation | Session `f46d94c5` compiled the snapshot, regenerated the pins, ran the canaries, and prepared this receipt — attestation only |

## 3. What was ratified

- **Part 1 — constitutional core:** the ten invariants, quoted verbatim at Charter v0.1.1
  (`957320d9…`); amendment only via Charter §4.
- **Part 2 — earned cognitive nucleus:** admitted N1 records + provenance (H4/H6), N2 supersedes
  relation + currentness strata (R; arbitration claim stays WEAK), N3 selection explanations,
  N4 journal-as-evidence, N5 audit discipline; conditional slot C1 (S as a declared optional
  lens, `count < 2` activation, scoped; 0.01 floor permanently outside; ≥2 boundary open).
  Compile targets / infrastructure / contracts not admitted (table in §2.3); missing-primitive
  candidates named and gated, not entered; the missing-primitive candidates (activation/decay
  field; operator/recipe layer) gate on their named experiments.
- **Part 3 — statutory baseline:** D2 score policy; candidacy rule v1 (divisor 20 / floor 2 /
  pair budget 200k / supersede penalty 0.60 / recency 0.05); τ = 0.694; audit protocols
  v1.2/v1.3; the switch inventory with defaults; budgets, invocation pin, horizons, metabolism
  rule, dependency manifest.
- **Part 4 — reproducibility pins:** the verified set (§4.1), the first-recorded set (§4.2), and
  the step-2 regeneration record (§5).
- **Scope footnotes S1–S10** — what the snapshot does not claim — ratified with the snapshot.
- **Disclosed findings F1–F4** (§5): F1 decomposition drift (ratified `cb8235e9…` → current
  `194f081c…`, additive errata only, no verdict changed); F2 freeze-criteria drift (canaries
  added in `86ac838`; current draft text pinned); F3 candidate-binary supersession
  (`b51112e9…` → `b1c66fec…`, rebuild verified); F4 duplicate proposals within one sweep
  (`ops.rs:751`; flagged for a future registration, not a blocker).

## 4. Verification (freeze procedure steps 2–3)

**Pins regenerated (step 2), no mismatches:**

- `cargo build --release --offline` at `7ff9181` reproduced the binary byte-identically:
  `target/release/wm-gen3` sha256 `b1c66fec53856007d8d42f038ab3a87227fe7a0da53dfa82140ba6621e1ac96d`.
- `wm contract --json` from the control binary regenerated **302 routes / 70 declared**.
- Live claims ledger: **8 claims, `next_id: 8`**, mapping as recorded; file sha256
  `d94c0cb3d9ebb61ba25a96736931b594844a6a1959c315d0ff388aa380c0e4ed`.
- Full corpus/manifest/harness re-hash pass matched the §4.1–§4.2 pins (control corpus 11 files,
  harness 3 files, embedder 5 files + snapshot ref, holdout + Testbed II manifests, governance
  documents).

**Canaries (step 3), all PASS on the frozen binary:**

| # | Canary | Result |
|---|---|---|
| C1 | Closure canaries (static scans · 28/28 tests + 5 doc compile-fail tests · runtime refusal, zero violations) | PASS |
| C2 | R ablation changes ordering (strata/ordering flip; zero proposals when ablated) | PASS |
| C3 | Count-gate ablation reverts to declared behaviour (fired sets `[2→F, 1→T, 0→T]` count · `[F, F, T]` floor · none always-on · absent S-off) | PASS |
| C4 | Provenance completeness 100 % at result granularity; zero `closure.violation` (all seven runs) | PASS |
| C5 | Round-trip relation kinds/endpoints intact across processes (`inspect` byte-identical) | PASS |
| C6 | Reachable-effectful acceptance (verb → journal-visible effect per admitted entry) | PASS |

**Evidence bundle:** `receipts/canary_2026-09-17/` — `SUMMARY.md`, 7 journals + hash-out files
(all verified), responses, fixtures, drivers, `ENVIRONMENT.txt`; `SHA256SUMS` sha256
`941abc8076ab504568b879a914aafc95975471c7f94f8d13a38b8553cf160790`. Observations O1–O3
(= F4 and scope notes) disclosed in the bundle; none blocks the freeze.

## 5. Companion hashes (this unit)

| Artifact | sha256 |
|---|---|
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |
| `receipts/canary_2026-09-17/SHA256SUMS` | `941abc8076ab504568b879a914aafc95975471c7f94f8d13a38b8553cf160790` |
| `docs/CHARTER.md` (v0.1.1, constitutional core) | `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d` |
| `docs/CLOSURE_TESTS.md` (v1.0) | `ad6e3152259b07b3b6f42989e975f84776c1d9bb14d114b3aeba308ee6ca775d` |
| `docs/PHASE3_DECOMPOSITION.md` (ratified text / current with errata) | `cb8235e9f8e70583cdc84a18da1efe4b75b216bac6c2b1b00b5b43b81846102a` / `194f081c1e09440706aeb3463270b116947312e0a76f219f20a2d687597d8e79` |
| `docs/NUCLEUS_FREEZE_CRITERIA.md` (draft text at freeze) | `2d311e08ccb32aad0947163f26e6a33c369f4c7725fdc6f929e735fc41ed773a` |
| Control binary (9.1.7 musl) + tag commit | `47b5c28e3228a0d5f3b8e733538018d2d40b70bd0beb8f134081335b679621ad` · `94b6420a…` |
| Candidate binary (frozen build) | `b1c66fec53856007d8d42f038ab3a87227fe7a0da53dfa82140ba6621e1ac96d` |
| Claims ledger | `d94c0cb3d9ebb61ba25a96736931b594844a6a1959c315d0ff388aa380c0e4ed` |
| `receipts/PHASE3_COMPILE_PASS_2026-09-17.md` | `9f295a0b45fe548065a9f53f7cc7be6e1bcaa17c85485bb6bff3863c2e0d20a8` |
| `receipts/PHASE3_ENTRY_DECISION_2026-09-17.md` | `0edd9793de8eae27dad68dca0e0eff2e51aa3d1ead7443ec29d9377104d0684e` |
| `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md` | `303227ca417219f1d9bd9d56402d705583a73e965823d201f23e6a10a179c926` |
| `receipts/PREREG_FREEZE_2026-09-16.md` | `d92561a6008b113acbcd73a19d4b35816ad259b7772b13195f8a8d15e8ee0b08` |
| `receipts/PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md` | `c9dcfe3b86286f86963ec99a5d4aaff7af9193f464ce4066ac50b845e068d681` |
| `receipts/PHASE0_RATIFICATION_v0.1.1_2026-09-16.md` | `873400c441f43dd9b9b5df0604c131ff9bb08b69ae39f43d8e24c84e5e33aa8a` |
| `receipts/DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16.md` | `331f306ac03b39cb7e4b460558386b77381b41edca8e46f254ef8198de13d2f1` |

## 6. Consequences

- **The nucleus is frozen.** Phase-4 re-expression waves may begin; each capability migration
  still needs its frozen behavioral spec + the 9.1.7 fix list as adversarial tests +
  wrapper-side evaluation + ablation (compile-pass receipt §6). Gen1/Gen2 provide capabilities
  and evidence, not architecture.
- **The frozen 9.1.7 control remains the reference animal** throughout Phase 4; the frozen
  candidate build (`b1c66fec…`) is the binary all freeze canaries ran against.
- **F4** (duplicate proposals within one sweep) is flagged for a future registration; it changes
  no verdict, gate, or claim.
- **Amendment rule** applies (criteria §5): proposal → canary demonstration → operator
  ratification → receipt; no emergency suspension; the next amendment should come from an
  experiment breaking a nucleus entry.
- Nothing in this freeze re-litigates falsified claims; WEAK stays WEAK (claim-0003 pending).

## 7. Attestation

AI session `f46d94c5` compiled `docs/NUCLEUS.md`, regenerated every pin (step 2), ran canaries
C1–C6 (step 3), prepared the evidence bundle and this receipt, and recorded the operator's
ratifying act. Ratification is an external operator act; this receipt records it — it does not
itself ratify.
