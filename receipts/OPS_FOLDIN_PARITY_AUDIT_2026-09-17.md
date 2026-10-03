# RECEIPT — Ops fold-in: bundle↔journal parity + read-path audit (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests; operator act: none required for these checks (the rhythm switch is separate — see §4).
Fold-in register: `docs/PHASE4_GEN2_FOLDIN.md` items #13 (parity) and #2 (read-path audit).

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/ops_foldin_2026-09-17/` |
| **SHA256SUMS** | `4a83d4fed569aa186374a2c86cc16f2e91ea003ca146d6959190a82c4b32668a` |
| Docs | `docs/BUNDLE_JOURNAL_PARITY.md` · `docs/READ_PATH_AUDIT.md` |
| Binary | `target/release/wm-gen3`, sha256 `7046db3f…` (current release build) |

## 2. Bundle↔journal parity (fold-in #13; A2 §1.4)

- Full field mapping landed in `docs/BUNDLE_JOURNAL_PARITY.md`: covered/derived fields (`id`,
  `galaxy`, route, `score`/`rank_key`, `basis` via chain, currentness) and declared **link-side**
  fields (`matched_terms`, `via`, created/event time, revision chain, integrity, visibility,
  coverage, conflicts, cold).
- Driver assertions PASS: every returned result reconstructs route, score, basis/chain,
  currentness, and galaxy from the journal alone; **no** Gen2-bundle-only key is claimed on the
  journal side (15-key scan).
- Divergence policy recorded: a same-side disagreement is a finding for `PHASE4_ERRATA.md`;
  cross-system value equality is never required.

## 3. Read-path audit (fold-in #2; 9.1.8 snapshot-read class)

- Source: `recall`/`inspect` bodies contain no durable mutation; `inspect` is `&self` (cannot
  mutate/journal by construction); `recall`'s mutable touches are declared (journal disclosure +
  in-process `usage` counter).
- Runtime: `data.mdb` sha256 unchanged after recall-only and inspect-only processes; recall-only
  journal = `{selection.decision, provenance.chain, run.end}`; inspect-only journal = `{run.end}`.
- Snapshot-readonly behavior under a live/wedged writer cited from `IMPL_A2_DISCIPLINE`;
  inspect read-only cited from `IMPL_W2_03_07`.

## 4. Rhythm switch (`checkpoint_nodiscovery`) — blocked, pending operator restart

- The 9.1.8 artifact is verified: `~/Desktop/WM918_ARTIFACT_FOR_SANDBOX/wm-linux-x86_64-musl`
  (sha256 OK, `wm 9.1.8`, route manifest 303/86, contains `checkpoint_nodiscovery`).
- **The local MCP fleet still runs `wm 9.1.7`** (`~/.local/bin/wm`, 2026-09-15): servers 18790 /
  18789 / 18794 / 18792 / … predate the capability, so `session.checkpoint_nodiscovery` is not
  reachable yet. The rhythm switch (B2 §1.3; ends the WMv9-HEAD capture quirk) takes effect at the
  next fleet restart on 9.1.8+ — operator action.
- Field discipline recorded for the switch: caller-supplied `commit`, `branch`, `tests_green`,
  `next_queue`, `open_flags` (+ `lease_id`); no discovery, no filesystem read, no subprocess.

## 5. Consequences

Fold-in checklist items #3 and #4 are **done**; #2 is **blocked on the fleet restart**; #5 remains
operator-side; #6 waits on the A1/B3/W2_02 slices. No verdict, claim, gate, or threshold movement.
