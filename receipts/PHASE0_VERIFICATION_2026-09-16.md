# RECEIPT — Phase 0 independent re-verification (2026-09-16)

**Date:** 2026-09-16 · **Status:** recorded · **Purpose:** independently re-check the Phase-0
freeze pin (`PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md`), the corpus pins, and the
Phase-0 document hash set recorded in `PHASE0_RATIFICATION_v0.1.1_2026-09-16.md`. Performed by
a separate session from the one that wrote those receipts.

**Coordination note:** a second session was active in this workspace during verification
(Charter v0.1.1, closure tests, ratification receipt prepared 15:16–15:17). This session
therefore modified **no artifact in the ratification receipt's hash set** — see §3.

---

## 1. Control binary

| Check | Result |
|---|---|
| `sha256sum ~/.local/bin/wm` | `47b5c28e3228a0d5f3b8e733538018d2d40b70bd0beb8f134081335b679621ad` — **matches** the freeze receipt's musl asset hash |
| `wm --version` | `wm 9.1.7` |
| Tag → commit | `git log -1 v9.1.7` in `WMv9` → `94b6420ab982ec1fa8087d12c5824fc4f843869c` — **matches** |
| WMv9 tree state | clean HEAD `cff34a0` (post-release; 9.1.8 in flight) |

**Verdict: no drift. The A/B control is intact.**

## 2. Corpus, harness, and document hash set

Corpus spot-check (recomputed):

| Artifact | sha256 | Matches freeze receipt |
|---|---|---|
| `scenario_seed1.json` | `7bebea98924b4ec3e6511b94c0059469b6c625ba4b1aff5b621b6d2c9369621f` | ✅ |
| `scenario_seed5.json` | `db84cf3ac6ec923ba03f161c9660f6d03c46ecb4b84b34c3a343207d36b115cc` | ✅ |
| `manifest.json` | `051372ab30f99e0e526c8afa17bc08edbe04f9a0779e0d14078f5a67c87384c3` | ✅ |

Manifest re-confirmed: 5 seeds · 10 categories (T1–T10) · 215 questions · 20 sessions ·
noise 0.8. Seed-1 re-count: T8 = 3, T1 = 4, T6 = 4, T9 = 12, total 43 — pre-registration
15/40 pooled counts exact.

Ratification receipt §2 hash set re-computed, all **match**:

| Document | sha256 (verified) |
|---|---|
| `docs/CHARTER.md` (v0.1.1) | `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d` ✅ |
| `docs/CLOSURE_TESTS.md` (v1.0) | `ad6e3152259b07b3b6f42989e975f84776c1d9bb14d114b3aeba308ee6ca775d` ✅ |
| `docs/SCAFFOLD_STRATEGY.md` | `433dfebd88f607b4bd4a1910021bba40cb241dbb7431a2506d217f07c252ac3e` ✅ |
| `docs/DEPENDENCY_MANIFEST.md` | `f3be84490160c74ac8cca379def7c5a0ba9f8d52b6543d797f55e9c6aee1b0eb` ✅ |
| `experiments/contradiction/PRE_REGISTRATION.md` | `d5efd6fe71f38af60f3254a0158ba97c5a081a1b15eca23fca5627b62b785915` ✅ |
| `receipts/PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md` | `c9dcfe3b86286f86963ec99a5d4aaff7af9193f464ce4066ac50b845e068d681` ✅ |

## 3. Errata recommendations (deliberately NOT applied — hashed set untouched)

Found during verification; addressed to the **pre-registration revision window before its own
Phase-1-gate freeze**, so the ratification hash set stays intact:

1. **Relative path:** `experiments/contradiction/PRE_REGISTRATION.md` §1 points to
   `../docs/DEPENDENCY_MANIFEST.md`; correct path is `../../docs/DEPENDENCY_MANIFEST.md`.
2. **T6 naming:** §3 calls T1 + T6 "supersession". T6 is **Memory Budget**; its questions are
   T1-derived under budget constraint (`scripts/memorastrict_gen.py:752-763` relabels
   `T1_`→`T6_`). Suggest: "T1 (Temporal Supersession) + T6 (Memory Budget; T1-derived
   questions)". No metric or count changes.
3. **Staging note (process):** the ratification receipt freezes the pre-registration's current
   *draft* hash, but the pre-reg is designed to be edited (corrections 1–2; its own §10 freeze
   at the Phase-1 gate). Suggest recording it as "current draft hash at receipt time" so the
   later, intended freeze edit does not require an amendment receipt.
4. **Dep manifest (optional, when next revised):** add `iceoryx2` to the deferred list —
   archaeology shows Gen1 compiled it (Rust bridge default features `["python","arrow",
   "iceoryx2"]`) and Gen2 has none, so a Phase-3 re-adoption needs its own rationale/receipt.

## 4. Environment facts recorded

- `WMgen3/` is **not yet a git repository** (no `.git`). Receipts cannot be hash-anchored in
  history yet. Recommendation unchanged: `git init` + first commit before pre-reg freeze,
  so every later receipt can cite a commit. (No remote, no release machinery — per
  `SCAFFOLD_STRATEGY.md` §3.)
- `reference/gen1-v26` and `reference/gen2-wmv9` symlinks resolve.
- Contract counts at WMv9 HEAD (302/85/217) differ from the 9.1.7 release fact (302/70/232) —
  cite the release, not HEAD, for control documentation.

## 5. Rules reaffirmed

1. This receipt is append-only; corrections create a new receipt referencing this one.
2. Any future drift in §1–2 artifacts voids the A/B and requires a new freeze receipt.
3. Verification and documentation were read-only with respect to the two source trees and to
   the ratified hash set; files created by this session are `docs/DESIGN_CANON.md`,
   `docs/CODE_ARCHAEOLOGY.md`, this receipt, and additive README/INDEX pointers.
