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
