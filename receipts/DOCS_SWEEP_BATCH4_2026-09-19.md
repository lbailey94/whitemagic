# RECEIPT — Docs sweep batch 4 (PEB-era provenance trace · read-path correction) — 2026-09-19

**Status: landed.** Two sources: (a) the AGY session audit (`221fbb57`, "Studying WhiteMagic
Generations", 2026-09-17 22:04 → 2026-09-19 20:06 ET, 4,119 steps, 72 MB brain); (b) code-walk
step 2 (`store.rs` + `ops.rs` non-test core, read in full). Operator authorization (in-session):
*"Docs fixes + errata log"*, *"Commit + receipt per update"*, *"continue with code walk steps, and
update our docs according to what we discover."* No verdict, claim, gate, or threshold movement;
no registered artifact edited.

---

## 1. Session-provenance trace (how the PEB-era records were authored)

| Item | Evidence (step / time / artifact) | Classification |
|---|---|---|
| Working method: prereg + code + driver + receipt often in **one commit** | PEB-13 steps 4982→5073, commit `36ba82b`; PEB-14A steps 5211 (22:57:40Z) → 5223 (22:58:07Z); PEB-15 steps 5641→5686, commit `8c13904` | pattern |
| M0 freeze-first (the exception) | Operator steps 2460/2472 (*"seal a Milestone-0 execution manifest before running anything"*); manifest step 2528 (02:49:48Z); execution 03:04–03:16; manifest §6: *"No test results may alter the preregistered criteria."* | deliberate |
| M0 metric substitution | Manifest step 2528 (`m3` Brier, `m4` replay, `m5` containment) vs receipt step 2727 (`m3` Refusal Disclosure, `m5` pairs, `m4` dropped); Brier never computed in the bench (`pulse.rs` carries it only as a corpus string) | **silent** |
| PEB-1 seed | `0xCAFEBABEDEADBEEF` first appears at step 2756 (test authoring); receipt step 2767 labels it "Preregistered"; no registration exists | **silent mislabel** |
| Baseline commit `9cb109404c0ec…` | Short `9cb1094` at step 2487; full 40-char string typed by hand at step 2528; never verified; real tag target `9cb10942a5c202…` (diverges at char 8) | **silent** |
| PEB-13 criteria | Prereg step 4982 (22:31:27Z); relative ΔRMSE reasoned at step 5062; executed gate step 5073; ΔBIC > 0 at step 5060; bootstrap CI / multi-seed / α₀ sweep never implemented | deliberate + **silent** mix |
| PEB-14A envelope | Prereg step 5211 (64 KB/23 fragments) → test step 5223 (1024 B, 17-byte chunks); receipt inherits "23 partial chunks"; v1.1 amendment (step 5400) appended post-execution, labeled "Pre-Implementation Audit" | **silent** + mislabeled amendment |
| Capabilities | Affine design at step 4026; "non-Send/Sync" first appears in the PEB-15 table (step 5641), never implemented; struct is auto-`Send + Sync` | **silent aspiration** |
| PEB-15 "143 unit proofs" | Step 5539: *"143 passed, 0 failed, 1 ignored"*; the session's own final report later says 152 (step 5686); HEAD is 148 | relabel |
| Correction pattern | Wording overreach fixed only on external review (step 3681: "theoretical ceiling" → "observed linear baseline ceiling"; step 5060 Wilson-CI fix); no self-audit vs preregs | pattern |

Method note: transcript mining was agent-assisted (extracts + targeted `jq` queries); the session
spot-verified high-impact claims independently (tag hash, test counts, geometry constants,
transport sizes — batches 3/4).

## 2. Code-walk step 2 (data path)

- **Read-path correction (erratum #54):** `recall` → `embed_cached` (`ops.rs:828` → `:490-520`) →
  `Store::put_embedding_cache` writes the `embed_cache` DB when the projection slot is on. The
  audit's "no store-write calls" claim was default-config accurate only; `docs/READ_PATH_AUDIT.md`
  findings #1/#4 corrected, residual added. `records`/`relations` untouched.
- **Walk observations (erratum #55, future registration):** `remember_batch` vector-write failure
  persists the record while returning `Err`; `store.rs` `decode_record` coerces unknown enum wires
  to defaults rather than refusing.
- **Verified consistent with the specs:** identity-key write/hydrate mapping; noise-table order;
  NaN-refusing floor validation; structural strata 0/1/2; declared reduction orders; append-only
  postings; fail-closed budget; declared journal event sets.

## 3. Changes

| Artifact | Change | sha256 (before → after) |
|---|---|---|
| `docs/READ_PATH_AUDIT.md` | findings #1/#4 corrected (projection-on scope); residual added | `f4c8ec4e…` → `458e6a18…` |
| `docs/PHASE4_ERRATA.md` | section L (#53 provenance trace · #54 read path · #55 walk observations); title A–L | `735ee7a5…` → `e0cdac25…` |
| `HANDOFF.md` | §6 open thread 8 (walk findings) | `936c8888…` → `98438696…` |

## 4. Disclosures / limits

- The session audit is agent-assisted; the full trace lives here and in errata L #53 (the register
  cell is a condensation). No conversation content was modified; the session files were read-only.
- No registered artifact was edited (errata-only for frozen/sealed/ratified texts).
- Nothing was re-run; no store touched; no threshold/weight changed.

## 5. Attestation

AI session `8996b333-5168-4eb2-9b2a-0e1724fbc749` (WMgen3 docs sweep) prepared this receipt;
operator present and authorizing in-session. This receipt is append-only; corrections create a new
receipt referencing it.
