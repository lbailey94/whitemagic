# Forensics — read-only overlap and inventory tooling

Tools used during the 2026-09-14 evidence work: card/TB volume inventories,
LMDB snapshot-vs-live overlap analyses, and opencode DB session comparisons.
Everything here is **read-only by construction**: tools open with
`readonly=True, lock=False` (LMDB) or `mode=ro` (SQLite), and the inventory
script only lists. Nothing mounts, writes, repairs, or prunes.

## Tools

| Tool | Use |
|---|---|
| `lmdb_compare.py` | Key-set diff between a live store and a snapshot/archive: per-DBI overlap, unique-to-snapshot, unique-to-live. Also surfaces content-level change via `idx_content_hash` deltas. |
| `sqlite_session_overlap.py` | Session-id overlap between two opencode-style DBs (e.g. live `opencode.db` vs a cold-tier copy). |
| `../backup/inventory-volume.sh` | Read-only inventory of any mounted volume: identity, per-store seal dates, trust evidence, anchors, snapshots, archives. |

Dependencies: `python3 -m venv /tmp/opencode/lmdbvenv && /tmp/opencode/lmdbvenv/bin/pip install lmdb`
(the tools accept any python3 with `lmdb` importable; sqlite3 is stdlib).

## Examples

```bash
# Live store vs a backup snapshot (store dir, lmdb dir, or data.mdb all work)
python3 ops/forensics/lmdb_compare.py \
  /home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/planning \
  /media/lucas/SD_CARD1/whitemagic-backups/planning/whitemagic-backup-20260914T173222Z/data/lmdb \
  --json /tmp/opencode/planning-diff.json

# Sessions: live DB vs a cold-tier copy
python3 ops/forensics/sqlite_session_overlap.py \
  ~/.local/share/opencode/opencode.db /path/to/opencode-compacted.db

# Volume inventory (cards, TB drives)
bash ops/backup/inventory-volume.sh /media/lucas/SD_CARD1
```

## Mounting an APFS volume read-only on Linux

`udisks` has no APFS handler, and the kernel has no APFS driver. `apfs-fuse`
(FUSE) works read-only and is available via Nix on this host:

```bash
sudo setfacl -m u:lucas:r /dev/sdXn          # runtime read grant; gone on replug
nix shell --extra-experimental-features 'nix-command flakes' nixpkgs#apfs-fuse \
  -c apfs-fuse -o uid=1000,gid=1000 /dev/sdXn /mnt/point
# apfs-fuse stays in the foreground (mount persists if it is backgrounded)
# volume selection: -v N (containers may hold several); volumes beyond 0 tested with "Unable to get volume!"
fusermount -u /mnt/point                     # unmount the FUSE layer
udisksctl power-off -b /dev/sdX              # power the drive down before unplugging
```

Optional permanent grant (avoid the `setfacl` each time): a udev rule with
`SUBSYSTEM=="block", ENV{ID_FS_TYPE}=="apfs", TAG+="uaccess"`.

## Analyses these tools produced (2026-09-14)

- Card `FEEC-FCE2`: heritage tar 100% already ingested; vault
  pre-redactstore `.mdb` a strict subset of live except 78 superseded
  research records + 610 changed-content hashes.
- TB drive (APFS): WM snapshots ~99.9% duplicated at 0911 (strict subsets);
  opencode-compacted.db 0 unique; unique value was the missing seal/trust
  evidence, recovered.
- Receipts: `work/CARD_ARCHIVE_OVERLAP_ANALYSIS_20260914.md`,
  `work/TB_OVERLAP_ANALYSIS_20260914.md`,
  `work/EVIDENCE_PRUNING_INCIDENT_DISCLOSURE_20260914.md`.