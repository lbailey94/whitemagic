# W1 — Coordination (Gen1 v26 observable behavior)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md`. Repo root for citations: `og_whitemagic/` @ v26.0.3 (`4d5be091`);
runtime state at `WHITEMAGIC_GEN1_v26_MEMORY_CORE/v26/state/`; turn evidence from the sessions-galaxy
DB `…/users/local/galaxies/sessions/whitemagic.db` (21,351 rows, 2026-01-28→08-02). Row target:
*Coordination* (PRESERVE IMPL. → link; `PHASE3_DECOMPOSITION.md:122,133-136`; worklist item 5,
`PHASE4_GEN1_TREE.md:48,80-81`). Classify by function, not name.

## Observed behavior (cites)

- **Advisory file locks (work arbitration):** `ResourceManager` (`core/whitemagic/gardens/sangha/
  resources.py:46-216`) — JSON registry `sangha/memory/collective/locks/registry.json`, TTL
  (tool default 3600 s, `core/whitemagic/core/bridge/collaboration.py:16`), heartbeat/renew
  (`:125-144`), owner-matched release (`:146-163`), expiry sweep (`:204-216`). `resource_id` is an
  opaque string; **nothing consults a lock before editing anything** — the only call sites are the
  `sangha_lock` tool, CLI, and the Room gana (`tools/handlers/sangha.py:32-84`,
  `cli/cli_sangha.py:93-162`, `core/ganas/eastern_quadrant.py:290-330`). Live registry holds exactly
  one entry: `default_resource` / `system`, no reason, 60-min TTL — produced by the handler defaults
  `resource="default_resource"` (`tools/handlers/sangha.py:58-59`) and `agent_id="system"`
  (`core/bridge/collaboration.py:23`); artifact read 2026-09-17.
- **Silent degradation:** if `whitemagic.utils.fileio` import fails, `file_lock` becomes a no-op and
  `atomic_write` a plain write (`resources.py:31-36`) — the lock layer can silently lock nothing;
  `utils/fileio.py:38-59` is process-safe (`fcntl.flock`) when present.
- **Shared board (single mutable JSON):** `CollectiveMemory` (`gardens/sangha/collective_memory.py:
  34-270`) — `shared_context.json` with participants, insights, goals, resonance, lineage; every
  mutation is read-whole-file → append → **plain `open(...,"w")` with no lock and no atomic write**
  (`_save_context`, `:250-270`; e.g. `contribute_insight`, `:100-121`). Two parallel contributors =
  lost updates (last writer wins). `shared_context.json` is absent in the archived state — the
  class's board never persisted a real context in this snapshot.
- **Baton file (single current session):** `SessionHandoff` (`gardens/sangha/session_handoff.py:
  52-107`) — one `…/collective/sessions/current_session.json`; `start_session` **resumes the
  previous session if it has no `ended_at`** (`:80-88`), and `update_session` silently returns when
  the stored `session_id` differs (`:121-123`). A second concurrent session therefore adopts or is
  ignored by the first's state; archive per session + one `HANDOFF.md` (`:190-196`). The
  `collective/sessions/` dir (created 2026-05-29 10:18) is empty in the snapshot.
- **Board inventory, all test-populated:** `…/sangha/memory/collective/` = `chat/` (council.md May 29;
  general.jsonl = 1 daemon line + repeated `"test message"`, itself the handler default
  `tools/handlers/sangha.py:15-16`), `mailbox/` (2 messages: "Bridge msg", "Handler msg"),
  `tasks/` (tasks.md/jsonl: 3 entries "Bridge task"/"Handler task" from `test`/`test_agent`),
  `locks/` (1 default entry, above), `patterns/` (empty). Dir dates: `patterns`/`sessions`/chat
  council 2026-05-29, `mailbox` 2026-07-30, `tasks` 2026-07-30, `locks` 2026-08-01.
- **Agent registry, two functions sharing one name:** (a) in-process `AgentRegistry`
  (`core/whitemagic/core/memory/agent_registry.py:45-100`) — dict + `threading.RLock` for
  version-vector cache coherence; **not persisted, not cross-process**. (b) per-file registry
  `state/agents/*.json` written by `tools/handlers/agent_registry.py:26,111-112,169-170` — 9 files,
  all status `active`; the three "real" externals (`external-opencode/-gemini-cli/-hermes`, registered
  2026-07-02, host T4800-S) have `heartbeat_count: 0`; only bench/test agents heartbeated (1).
- **Divergent second lock type:** `MultiAgentCoordinator` (`core/immune/defense/multi_agent.py:1-40`)
  — in-memory `ResourceLock` dict + `threading.RLock`, timeout 300 s; same class name as the file
  lock's dataclass, different function (thread-local, not cross-process), no shared registry.
- **Task queue (cross-device dispatch analogue):** `state/tasks/*.json` — 76 tasks, all
  `created_by: T4800-S`, all `general`, 73 pending / 3 completed (`echo bench`-class commands);
  `state/batch_*.json` are Jul-27 batched-tool benchmark result files, not coordination docs.
- **Real parallel sessions did collide — without touching any of the above:** sessions DB
  2026-07-16: user turn #904 "I have a different AI in a parallel session running it right now";
  #906 the benchmark run SIGTERM'd mid-ingest; #908 stale results from a previous run; #925
  "Great work in the parallel session". Coordination happened in human narration, not in v26 lock/
  board state (no lock or board writes exist in the DB for these dates).
- **Mesh critique** (`mesh/critique_protocol.py:1-30`) is peer *review* scoring (methodology/
  novelty/significance/reproducibility), not work arbitration; wave-5, not this ancestor.

## Selection history

- **Locks → Gen2 `code.claim` leases:** functional homology — `reason` (v26) becomes mandatory
  *intent*, `ttl_seconds` becomes lease TTL, owner-matched release becomes exact-owner cleanup.
  Gen2 added the missing half: enforcement at the edit seam plus conflict naming; 9.1.8 hardened it
  into typed effects `CoordinationLease`/`CoordinationRelease` and made acquisition refusable
  (`PHASE4_GEN2_DELTA.md:38-39`). v26 had no enforcement, so "the two-writer fix" is a fix for a
  failure v26's locks could not have prevented.
- **Board/baton → track ledger + handoff:** Gen2's track ledger (one writer per track in
  `NEXT_SESSION.md`, claims carried in `session.record`) is doc-altitude and **added**; the v26
  ancestor by function is the handoff-doc corpus (HANDOFF_* turns ingested 2026-05-16) plus the
  one-host task queue — no v26 track-claim code exists (`PHASE3_DECOMPOSITION.md:133-136`).
- **Two-writer live-fire:** Gen2 incident; lineage pinned at `LINEAGE_LEDGER.md:118,133-136`
  (`code.claim` v0 `89603db`; F-1 mesh scope bridge `0ae8d4a`; baton verified via `lease_id`).
  Its v26-side functional ancestors are the parallel-session interference above and the
  single-baton resume behavior — not the sangha locks (never invoked live).
- **`sangha_memory_collective`:** the exact name does not occur anywhere in the v26.0.3 tree
  (case-insensitive search, 0 code/doc hits; the single textual occurrence is inside a 2026-06-22
  opencode migration export stored in the sessions DB, unrelated to a board). The observable artifact
  is the `…/sangha/memory/collective/` directory tree dated 2026-05-29. **Errata candidate** vs
  `PHASE4_GEN1_TREE.md:48` ("v26 `sangha_memory_collective` file board — source owed"): the board
  is real, the name is not attested. `UNVERIFIED`: the board's real-session usage beyond test data.

## Candidate Gen3 expression / manifest notes

- Verdict is ratified (PRESERVE IMPL. → link): anything carried must link to the Gen2 lease ledger,
  not re-derive locks. Findings bound what the link must state: lease fields = owner + TTL + intent;
  release always admitted; acquisition refusable and narrated; **no board may be a shared mutable
  JSON file** — v26's `shared_context.json`/`current_session.json` are the lost-update exemplars and
  belong in the journal as records, not in a single writable blob.
- The ratified E12 lineage (`PHASE3_DECOMPOSITION.md:133-136`) is consistent with the evidence,
  except "informal tracks": in v26 the track-ish artifacts are handoff docs and a task queue, not
  tracks in the Gen2 sense — record as ancestry nuance, not a verdict change.

## Adversarial cases (for the frozen spec)

1. **Lost update on the single-blob board:** two writers append to a `shared_context`-shaped file
   concurrently; v26 semantics lose one (no lock, `collective_memory.py:250-270`). Gen3 link must
   serialize or refuse, and journal the refusal.
2. **Degraded lock must be loud:** simulate the `fileio`-missing fallback (`resources.py:31-36`);
   an unenforced lock that reports success is the failure mode — test that loss of locking is
   reported, not silent.
3. **Stale-lease steal vs live holder:** v26 deletes expired entries silently, no takeover naming
   (`_clean_expired_locks`); the Gen2 contract names holder + intent on conflict. Test both the
   expired-takeover path and the still-held refusal.
4. **Read-only listing must not prune:** v26 `list_locks` writes the registry while listing
   (`resources.py:181-216`); 9.1.8's `snapshot_readonly` ("expired leases are logically absent and
   still reportable", `PHASE4_GEN2_DELTA.md:39`) is the corrected behavior — test that a read never
   mutates the ledger.
5. **Default-parameter artifacts are not usage:** `default_resource` + `"test message"` defaults
   (`handlers/sangha.py:15-16,58-59`) manufacture board entries indistinguishable from real
   coordination; adoption metrics must exclude them.

## Ablation ideas

- Two-writer replay with the coordination link enabled/disabled: expect on-disk lost updates (or
  refusals) with disabling vs journaled serialization with enabling; compare journal evidence only.
- Toggle expired-lease listing (prune-on-read vs logically-absent) and verify the ledger bytes and
  the reported set differ only in retention, never in liveness.
- Strip test-only artifacts from the v26 evidence set and re-check adoption: locks, chat, mailbox,
  tasks, and agent registry all collapse to zero real cross-session usage — a clean negative control
  for any future "the fleet used X" claim.

## Open questions

- Where is the "two-writer postmortem" document itself? It is cited (`LINEAGE_LEDGER.md:118`) but not
  located in accessible files here — `UNVERIFIED` (narrative).
- Did any real external agent ever use `state/agents/` (registration without heartbeat suggests
  one-shot demos)? Whether `external-*` entries came from a documentary script needs a driver search.
- What was the 2026-05-29 origin event that created `patterns/` and `sessions/` dirs? The matching
  turn is outside the sampled windows; needs a targeted sessions-DB search — `UNVERIFIED`.
- Tree row's "batch docs" as coordination artifacts: only Jul-27 batch benchmark JSONs were found;
  mapping to a track-like doc corpus is `UNVERIFIED`.
- `mesh/critique_protocol.py` was born without file:line anchoring here; mesh ancestry belongs to
  wave 5 — flagged so a later pass does not inherit it into the coordination row.
