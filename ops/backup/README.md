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
snapshot per store. Missing evidence is logged loudly, never silent.
