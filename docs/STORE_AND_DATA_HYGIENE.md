# WMgen3 store and data hygiene — 2026-09-22

Policy: **every WMgen3 store is disposable synthetic data.** Real WhiteMagic data (WMv9 /
WHITEMAGIC memory stores, knowledge bases, journals, the production tree) must never be opened,
adopted, migrated, or written by WMgen3 tooling. If real data is ever needed for a test, copy it
into a disposable temporary directory first and operate only on the copy — never in place.

This policy is enforced socially (this document + receipts) and structurally where possible:
- The v5 store is fresh-only: v4 and older stores **refuse to open** (no migration/adoption until
  9D), so pointing the current binary at an old or real store fails closed instead of adopting it.
- No production code path in this tree references a real WM path (audited 2026-09-22, see below).

## Audit — 2026-09-22

| Surface | Finding | Disposition |
|---|---|---|
| Production code (`crates/`, `scripts/`) | No reference to `/home/lucas/Desktop/WHITEMAGIC`, WMv9 stores, or any absolute real-data path | none required |
| Test-only model cache defaults | `projection.rs` test module and the `ops.rs` gated-tests helper default the fastembed cache dir to `/home/lucas/Desktop/WHITEMAGIC/WMv9/.fastembed_cache` | Known test-only exception. Those tests are `#[ignore]`d pending 9C. Before re-enabling, set `WM_GEN3_EMBED_CACHE` to a copy or a Gen3-local path; fastembed may write downloads on a cache miss (see errata #57). Not a memory store, but it lives in the real tree — treat as read-only at most. |
| Stores inside the WMgen3 tree | Six v4-era experiment stores under `receipts/impl_*/…/data.mdb` (Sep 18) | Historical artifacts. v5 refuses them by design; do not migrate until 9D. If ever needed, copy to temp and use an explicitly compatible binary. |
| Harness default store | `wm-gen3 serve` defaults to `./gen3-store` relative to the current directory | Run from a temporary working directory or pass `--store <temp path>`. |
| Acceptance/experiment runs | All batteries use disposable temp directories or `receipts/` copies; synthetic fixtures only | keep this pattern; record store provenance in the receipt |

The WMv9 production tree and stores were not touched by this lane. No real-data, migration, or
model run was performed.

## Rules for future work

1. Never point a WMgen3 binary at a real WM store, even read-only; copy first.
2. Keep test and experiment stores under a temp directory or `receipts/`, and name their provenance
   in the receipt that cites them.
3. Prefer synthetic fixtures; if real data is copied in, scrub it and record the copy's digest.
4. Treat a v5 refusal as the correct outcome when an old store is encountered — do not "fix" it by
   adding adoption; migration is 9D work with its own prereg.
5. If a new code path needs a model cache or derived store, give it an explicit `WM_GEN3_*` path
   override and a Gen3-local default; never a silent absolute path into the real tree.
