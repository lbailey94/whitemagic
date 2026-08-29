# Using WhiteMagic Across Multiple Laptops

WhiteMagic's store is local by design — it does not sync to any cloud service
on its own. This document covers the two supported ways to move between
machines, and the rules that keep multi-machine use safe.

## What you carry

A WhiteMagic store is the whole store root: LMDB data, the Tantivy search
index, and all JSON state files (`self_model.json`, `claims_ledger.json`,
friction logs, mutable-state files, …). A backup directory contains all of it
plus a `SHA256SUMS` manifest. The `lmdb/` subdirectory alone is **not** a
complete store.

## Path 1 — Whole-store move (owning the machine)

Use this when a laptop is being retired, replaced, or you want identical state
everywhere:

```bash
# Old machine (stop any running server first):
wm backup --out /path/to/usb-drive

# New machine (after installing wm):
wm restore --backup /path/to/usb-drive/whitemagic-backup-<timestamp> --force
wm doctor     # confirm health after restore
```

Restore verifies every file against the manifest before touching anything and
refuses tampered backups. It replaces the target store entirely.

**Rule: last restore wins.** There is no merge. If you record sessions on both
laptops independently and then restore one over the other, the other laptop's
un-exported work is gone. Do not treat backup/restore as a sync mechanism.

## Path 2 — Per-session carry (lightweight)

Use this to bring specific work product (session handoffs) from one machine to
another without touching either store wholesale:

```bash
# Source machine:
wm route export ...
# or via MCP: session.export with a path — writes self-contained JSONL
# preserving ids, timestamps, tags, and superseded turns.

# Copy the .jsonl file (scp, USB, git repo — your choice), then:
# Target machine via MCP: session.import pointing at the file
```

Imported sessions integrate into the target store's session history;
continuity/replay behave identically afterward. Note that associated memories
outside the session records are **not** included — Path 1 is the complete
mechanism.

## Install on the new machine

```bash
curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | sh
wm --version   # matches the release page
wm doctor      # environment health check before restoring any store
```

The Linux x86-64 artifact is fully static (musl) and has no distribution or
glibc requirements. Releases older than v7.0.0-alpha.4 shipped dynamically
linked binaries requiring glibc 2.39+; the installer detects this and refuses
clearly when the static build is unavailable for a pinned old version.

## Hygiene rules for multi-machine setups

1. One writer at a time per store. Never run writable servers against the same
   restored copy on two machines simultaneously — each has its own Tantivy
   writer lock and diverging history.
2. Back up before every move (`wm backup`) and keep the backup even after a
   successful restore on the target.
3. After a restore, run `wm doctor`; after importing sessions, spot-check with
   `session.list` and `session.continuity`.
4. Verify checksums on transfer (backups carry `SHA256SUMS`; `sha256sum -c`
   works directly inside the backup directory).
5. Keep at least one backup on media that is not either laptop.
