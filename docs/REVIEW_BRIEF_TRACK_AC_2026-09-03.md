# Review Brief — Track A (Firebreak) + Track E/Track F artifacts
**Posted:** 2026-09-03, Track E session `3c8fea3f` (forge/t4800-s). For:
**inspiron-prime** (Track B writer) and **mac-stranger** (Track D writer).
**Status of the tree:** HEAD `523efbf` + uncommitted firebreak WIP + Track E
docs. **Sequencing (Lucas, ratified):** Track A + Track C staging land
together → this review → commit batch (Lucas owns the batched commit +
alpha.9 tag decision) → then Track F code slices start. **No new WIP
interleaves before your review.**

## To inspiron-prime (Track B: S9 + dream-loop, `wm-sangha` scope)

1. **Firebreak pattern lists (your Jan-11 veto-list expertise).** The v26
   `Governor` design is promoted as `wm_governance::Firebreak` — 31
   forbidden / 13 dangerous / 8 caution patterns, default-armed on every
   `DispatchPipeline` (`WM_FIREBREAK=0` kill switch), veto at the dispatch
   seam for destructive/spawn/FS+Process+Network-write args only (prose is
   never scanned — `memory.create` quoting `rm -rf` still works, so incident
   recording survives). Implementation: `crates/wm-governance/src/firebreak.rs`
   (new), wired at `crates/wm-dispatch/src/pipeline.rs` stage 4c. **Asks:**
   (a) walk the pattern lists for false positives/negatives — especially the
   repaired fork-bomb regex and the widened device/pipe classes; (b) rule on
   the seam-scoping decision (args-only, irreversible classes only) — is
   anything missing that your S9 threat model wants covered?
2. **Bulk-scope law + delete-confirm audit.** `SCOPE_REGISTRY` covers all 10
   destructive tools (Jul-13 lesson: 54,192 memories deleted through the
   wrong backend); `WriteAuditEntry.confirmed` via `record_since_confirmed`.
   Audit table: `docs/BULK_OPERATIONS.md`. Doctor §11h. Any gaps from the
   S9 side?
3. **Track F Slice A reuses `wm_sangha::crypto`** (exported unconditionally,
   `lib.rs:25` — outside the `transport` feature gate) for record
   attestations: node-key Ed25519 signatures over
   `{record_sha256, agent_id, timestamp, chain_context}`. Since `wm-sangha`
   is your lane: **flag if this reuse creates a conflict with S9's key/KDF
   plans** (`WM_MESH_KEY` KDF, signed-only beacons, replay cache). A
   domain-separated seed for record attestation vs mesh identity is the open
   question — your call matters before Slice A starts.
4. Your S9 + dream-loop lane is otherwise unchanged and queued as ratified
   (Track B line in `docs/NEXT_SESSION.md`).

## To mac-stranger (Track D: S10 macOS-native, `wm-substrate` + `ops/launchd/`)

1. Your S10 items are unchanged (health_score honesty, launchd packaging).
2. **New dependency to review:** Track F Slice A adds a `wm anchor`
   subcommand (Merkle anchor over `(record hash, attestation hash)` pairs,
   appended to a git-tracked JSONL) that will be called from
   `ops/backup/wm-nightly-backup.sh` — meaning macOS will need the timer
   analog for the anchor step alongside the existing seal/verify/snapshot
   chain. Review the ops/ shape for launchd portability when you pick up S10.
3. Doctor §11h (firebreak arm-state) rendering — cross-check doctor sections
   behave on macOS when you're in there.

## Both: new Track E/Track F artifacts (ratified by Lucas 2026-09-03)

- `docs/TRACK_E_COLLECTIVE_SUBSTRATE_RESEARCH.md` — research stash digest +
  W1–W10 findings (SwarmWorld verification, METR/OpenAI incident design
  takeaways, stigmergy/blackboard/consensus/provenance literature, claim
  landscape, HiveMemBench sketch, port specs for 7 v26 revival gaps,
  integration seams). §8 has open questions; comments welcome.
- `docs/V8_MEMORY_RESEARCH_AGENDA.md` §8 — ratified implementation queue.
- `docs/TIMELINE_CONVERGENCE.md` — internal-vs-field chronology comparison
  (built on the claims-ledger discipline; honesty rules included).
- **Track F (new ledger entry, unassigned):** Slice A (attested creates +
  anchored nightly Merkle) then Slice B (validity states + corrections) —
  starts only after this review + the commit batch. Specs:
  `TRACK_E_COLLECTIVE_SUBSTRATE_RESEARCH.md` §7 (W9/W10).

## Firebreak file manifest (for the commit batch)

`crates/wm-governance/src/firebreak.rs` (new), `crates/wm-dispatch/src/
pipeline.rs`, `crates/wm-governance/src/lib.rs`, `crates/wm-dispatch/Cargo.toml`
(regex dep), `crates/wm-memory/src/write_audit.rs`, `crates/wm-mcp/src/bin/wm.rs`
(doctor 11h), `crates/wm-tools/.../effect_audit.rs` (test scope fix),
`docs/BULK_OPERATIONS.md`; plus AGENTS.md (gitignored/local). 44/44 suites,
fmt/clippy clean at handoff. Suggested commit message (from the Track A
handoff): `feat(governance): firebreak — Jan-11 forbidden-command guardrail
promotion + delete-confirm scope law (P1.4+P1.6)`. Note: the firebreak lease
expired rather than released — the NEXT_SESSION Track A line + board post 46
store records are the status of record.

Objections/amendments: record in your own store + the repo (docs edits with
a claimed `docs/` lease), or via mesh chat to `t4800s-forge`. Silence by the
review deadline = assent per the fleet's cross-machine review doctrine.
