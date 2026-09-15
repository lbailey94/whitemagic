# Nightly backup retention

Install `wm-nightly-backup.sh` and `retention.sh` together in the same directory.
The nightly entrypoint sources the pure sibling helper at retention time; a missing
helper refuses pruning and logs `RETENTION-FAIL`, rather than falling back to a
broader deletion loop. This source change does not update any installed job.

Only directories named `whitemagic-backup-YYYYMMDDTHHMMSSZ` qualify for snapshot
retention. Fixed-width UTC names determine newest order (not mutable mtime).
Unknown entries, files, and symlinks are untouched. `trust/` and `anchors/` are
never pruned. `seals/<store>/YYYY-MM-DD` retains its existing independent KEEP-day
policy; seals are exempt from the generic snapshot loop, not from that policy.

Run `bash ops/backup/retention_test.sh` for disposable synthetic coverage. Never
run the full nightly script as a test: it stops real services, accesses real
stores, and contacts timestamp authorities.

## Installed layout (2026-09-14)

`~/.local/bin/wm-nightly-backup.sh` and `~/.local/bin/retention.sh` are
**symlinks into this directory** (`wm-backup.service` execs the former). Repo
edits deploy themselves — no copy step. Do not replace the symlinks with
copies; the 2026-09-14 trust outage and the retention hardening both shipped
to the repo while the installed copy stayed stale, and this class of drift is
invisible to every test. If a copy is ever unavoidable, copy both files
together and re-run `retention_test.sh` against the source.

The end of every nightly run asserts the day's evidence exists
(`EVIDENCE-OK` / `EVIDENCE-MISSING` / `EVIDENCE-SUMMARY` in `backup.log`):
trust manifest + digest + OTS proof + RFC3161 response, and one dated seal
snapshot per store. Missing evidence is logged loudly, never silent. A
7-day informational scan (`EVIDENCE-GAP`) lists seal days with no snapshot
so rotation/anomaly gaps are visible without failing the run.

## Canonical volume rule (2026-09-14)

Only the volume whose UUID matches `CANONICAL_VOLUME_UUID` (default
`FA99-F6E6`) is a valid backup target; when any other medium is mounted the
run stages on NVMe with a loud WARN and never folds or splits history.
Override with `WM_CANONICAL_VOLUME_UUID` when intentionally replacing the
medium. Rationale: three different cards have shared the `SD_CARD1` label
and early-September history split across them (recovered from the TB drive
on 2026-09-14).

## Retention policy

Big stores keep `KEEP` (7) snapshots; small stores (`neon`, `planning`,
`whitemagic-site`, `wmv5`, `opencode`, `default`) keep 30 via
`STORE_KEEP_OVERRIDES` — their days are megabytes, so history is cheap.
Seal snapshots are tiny evidence and keep `SEAL_KEEP` (30) days for all
stores. Overrides and seal keep are validated by `retention_test.sh`.
