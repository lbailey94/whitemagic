# Track Log — per-track implementation logs

**Status:** landed 2026-09-20 (9.2.2 lane, uncommitted at writing; available
after the next fleet rebuild). Source: `crates/wm-tools/src/expansion/`
(`session_ops.rs`, `session.rs`); manifest:
`docs/contract/route-schema-manifest.json`.

## Why

Parallel sessions here claim a **track** (one writer per track) and the
ledger lives in [`NEXT_SESSION.md`](NEXT_SESSION.md) → "Active tracks". That
doc is a human index: it cannot be filtered, ordered, or aged, and nothing
forces an implementation log to be written when a ticket completes. The
track log makes the track machine-readable without inventing a ticket
system — turns and checkpoints already exist; a track is a tag on them.

## Contract

- A **track slug** is a lowercase ASCII string: `a-z0-9` start, then
  `a-z0-9`, `-`, `_`, `.`, `/`; 1–64 chars. Strict on purpose — near
  duplicates (`Harness-2` vs `harness-2`) would split one log in two. An
  invalid slug is a caller error, never normalized.
- Membership is stored as the tag `track:<slug>` on the memory record
  (turns and checkpoints, both in the `sessions` galaxy) and mirrored in
  the record JSON (`"track": "<slug>"`).
- `session.record` and both checkpoint variants (`session.checkpoint`,
  `session.checkpoint_nodiscovery`) accept the optional `track` argument.
- Superseded turns are excluded by default (the amend-with-supersede
  mechanism already marks them), so a track log shows the current story;
  `include_superseded: true` restores the full history.

## Read surface — `session.track_log`

| Args | Meaning |
|---|---|
| `track` | One slug |
| `tracks` | Array of slugs, returned per-track (the related-ticket review view) |
| `since` / `until` | Same time-bound contract as replay/continuity/digest |
| `limit` | Max entries **per track**, most recent kept (default 100, cap 1000) |
| `include_superseded` | Include superseded turns (default false) |

- With `track`/`tracks`: `mode: "log"`, each track carries `entries`
  (chronological: turns with role/turn_type/importance/content; checkpoints
  with label/handoff), `entry_count`, `returned`, `last_activity_at`,
  `age_seconds`, and `latest_checkpoint` (the newest handoff — `next_queue`,
  `open_flags`, `lease_id`, git state).
- Without either: `mode: "overview"` — every track with counts, last
  activity, and the latest entry preview. This is the staleness check
  (`age_seconds`) and the cross-track index.
- An unknown slug is disclosed (`known: false`, `entry_count: 0`), never
  fabricated.

## What this is not

- **Not an alignment oracle.** Directional alignment across related tracks
  is a reading judgment; the tool supplies the logs and staleness facts and
  says so in its `disclosure` field.
- **Not a lock.** Track membership is advisory like the doc ledger; scope
  exclusion is still `code.claim`.
- **Not a replacement for session continuity.** `session.continuity` answers
  "where did the session leave off"; `session.track_log` answers "where did
  *this line of work* leave off, across sessions".

## Verification

- `wm-tools`: `record_rejects_invalid_track_slug`,
  `track_log_reads_recorded_turns_per_track`,
  `track_log_merges_related_tracks_and_filters_time`,
  `track_log_hides_superseded_turns_by_default`,
  `checkpoint_track_lands_in_track_log` (in-module, `session_ops.rs`).
- Contract harness: declared prose fields must exist in schemas —
  `session.checkpoint` declares `track` as prose (stored-only, never
  command-bearing).
- `wm contract --check` stays green; manifest regenerated at 9.2.1+.
