# WhiteMagic Reorganization — Phase 1 Complete

## What Was Done

### Directory Structure — REORGANIZED
```
/media/lucas/SD_CARD/WHITEMAGIC/
├── core/              # Main source tree (was whitemagic/ + whitemagicpublic/ merged)
├── frontend/          # Frontend apps (wmfrontend2, web, dashboard-app, hub, shell, _legacy)
├── projects/          # Active side projects
│   ├── mandalaos/     # OS project + backend (merged)
│   ├── cyberbrain-site/ # Astro site + atlas (merged)
│   ├── koka-clones/   # 72 items — TO BE WIRED UP
│   └── elixir-swarm/  # Phoenix swarm — TO BE WIRED UP
├── aria/              # Aria project (consolidated from aria-crystallized + _aria)
├── data/              # Databases
│   ├── galaxy/        # Master archive (copy in progress — 1.3GB/8.6GB)
│   ├── working/       # Symlink target for ~/.whitemagic/memory/whitemagic.db
│   ├── auxiliary/     # meta_learning.db, thought_galaxy.db, embeddings.db, feedback.db
│   └── _archive/      # recent_memories_backup.db, primary_db_pre_merge.db
├── docs/              # ALL .md and .txt files organized:
│   ├── guides/        # Deployment guide
│   ├── plans/         # Synthesis plan, reorg plan
│   ├── reports/       # Comparison report, audit report
│   ├── changelogs/    # CHANGELOG.md, v16, v17
│   ├── manifests/     # Release manifests
│   ├── ci-logs/       # CI output logs
│   ├── misc/          # Standalone .md/.txt files
│   ├── code-of-conduct/
│   ├── contributing/
│   └── deploy/
├── archives/          # Historical artifacts (dead code, scripts, phase artifacts, zip, tarball)
└── _trash/            # Safe-delete staging (duplicate DBs, empty stubs, test files)
```

### Removed / Consolidated
- `whitemagic/` → merged into `core/`
- `whitemagicpublic/` → merged into `core/` (was 90% duplicate)
- `wmfrontend/` → split into `frontend/` subdirs
- `aria-crystallized/` → merged into `aria/`
- `mandalaos/` → moved to `projects/mandalaos/`
- `cyberbrain project/` → moved to `projects/cyberbrain-site/`
- `wm_archive/` → deleted (obsolete)
- `whitemagic/_archives/` → moved to top-level `archives/`
- `whitemagic/koka-clones/` → moved to `projects/koka-clones/`
- `whitemagic/elixir/` → moved to `projects/elixir-swarm/`
- `whitemagic/mandalaos-railway-backend/` → merged into `projects/mandalaos/backend/`

### Home Directory Cleanup
- Removed 5 stale `.lock` files
- Removed empty `evolution_learning.db`
- Removed empty `memory_v2/index.db`
- Removed obsolete `whitemagic_pre_rehydrate_backup.db`

### Memory Rehydration — COMPLETE
| Table | Before | After | Master |
|-------|--------|-------|--------|
| memories | 112,100 | **204,903** | 204,903 |
| associations | 105,489 | **18,871,734** | 18,767,201 |
| tags | 370,673 | **370,673** | 370,673 |
| memory_tags | 1,989 | **1,989** | 0 |
| memory_embeddings | 0 | **8,573** | 8,573 |

All 92,803 missing memories have been rehydrated from the master Galaxy DB into the working DB at `~/.whitemagic/memory/whitemagic.db`.

---

## Pending / Incomplete

1. **Galaxy DB copy to SD card** — stalled at 1.3GB/8.6GB (SD card write too slow). The master remains on `~/Desktop/whitemagic_master_galaxy.db`. To finish later:
   ```bash
   rsync -avh ~/Desktop/whitemagic_master_galaxy.db /media/lucas/SD_CARD/WHITEMAGIC/data/galaxy/
   ```

---

## Where to Pick Up Next

### Priority 1: Wire up Koka Clones
- Location: `projects/koka-clones/` (72 items, Koka language implementations)
- Has `build.mk`, `build.sh`, and 70+ topic directories (agents, ai, alchemy, automation, etc.)
- Next: Review `build.mk` and `build.sh`, set up Koka compiler, build and test
- Goal: Get the Koka clones compiling and integrated with the WhiteMagic core

### Priority 2: Wire up Elixir Swarm
- Location: `projects/elixir-swarm/`
- Has `mix.exs`, `lib/`, `test/`, swarm scripts (`swarm_massive.exs`, `swarm_scout.exs`, etc.)
- Next: Install Elixir/OTP deps with `mix deps.get`, run `mix test`, review swarm architecture
- Goal: Get the Elixir swarm system running and connected to WhiteMagic memory DB

### Priority 3: Deploy WhiteMagic Backend to Railway
- Location: `core/` (main Python codebase) + `projects/mandalaos/backend/` (FastAPI)
- Next: Set up `railway.json`, configure Postgres, deploy
- Goal: Get WhiteMagic backend live on Railway

### Priority 4: Deploy Frontend to Vercel
- Location: `frontend/wmfrontend2/` (Tauri + Vite app)
- Next: Configure `vercel.json`, set up build command, deploy
- Goal: Get WhiteMagic frontend live on Vercel

### Priority 5: Set up Tailscale
- Connect laptop ↔ VPS for secure private network
- Use VPS as always-on relay for lightweight agents and scheduled tasks

### Priority 6: Build Memory Query Interface
- Working DB now has 204,903 memories — build a simple search/query API
- Could be a FastAPI endpoint on Railway or a local tool

---

## Notes for Next AI Agent

- The working DB at `~/.whitemagic/memory/whitemagic.db` is now fully rehydrated (204,903 memories, 18.8M associations)
- The master archive at `~/Desktop/whitemagic_master_galaxy.db` (8.6GB) should NOT be modified — treat as read-only
- All code is now under `core/` on the SD card. The `.git` repo is in `core/.git`
- The `_trash/` directory is empty and safe to remove
- SD card I/O is VERY slow — prefer `rsync` over `cp` for large files, and avoid `find -exec` on large trees
- The FTS index for memories was rebuilt but may need `REBUILD` if search doesn't return all results:
  ```sql
  INSERT INTO memories_fts(memories_fts) VALUES('rebuild');
  ```
- Root README.md and archives/README.md have been written
- Build artifacts (rust target, mypy_cache, __pycache__) have been cleaned from core/

*Reorganization completed 2026-04-05*
