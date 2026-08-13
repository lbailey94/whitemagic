# WhiteMagic Archive Capability Map

**Prepared:** 2026-08-12
**Source:** `/home/lucas/Desktop/WHITEMAGIC`
**Purpose:** Preserve useful ideas from the retired v26, v4, and
`WHITEMAGIC-CORE` projects without turning the archive into an unchecked v5
feature backlog.

This is a product and research map, not an implementation commitment. Current
release decisions remain in [`RELEASE_READINESS.md`](RELEASE_READINESS.md).

## Archive Summary

The archive contains three materially different systems:

- `core/`: the retired v26 Python reference, with broad memory, tools,
  governance, intelligence, CLI, MCP, and experimental subsystems.
- `whitemagic-v4/`: a superseded Rust snapshot.
- `WHITEMAGIC-CORE/`: a lean Python package designed around zero dependencies,
  one SQLite/FTS5 file, a short setup path, and progressive capability packs.

The archive has real engineering value, but it has competing registries,
overlapping galaxy implementations, inconsistent tool counts, incomplete
documentation, and many mocked or bookkeeping-only advanced systems. It is a
source of patterns and tests, not a source of public contracts.

## Highest-Value Capabilities

### Release or Immediate Follow-Up

These capabilities directly improve the memory/session product and should be
considered before research expansion:

| Capability | Archive evidence | v5 direction |
|---|---|---|
| One-command setup | `core/whitemagic/cli/init_command.py`, `WHITEMAGIC-CORE/src/whitemagic_core/cli.py` | Add `wm init`, generated MCP configs, fresh-store verification, and a five-minute native install path. |
| Bounded context wake | `WHITEMAGIC-CORE/src/whitemagic_core/memory.py` (`wake`) | Add a safe `memory.wake` or context-pack operation: recent session, decisions, open work, and relevant memories under an explicit token budget. |
| Progressive and selective replay | `core/whitemagic/core/memory/session_recorder.py` | Strengthen current `session.replay` with sequence numbers, token budgets, turn types, citations, and restart tests. |
| Session handoff | v26 `session_recorder.py`, `session` pack | Keep `session.continuity` and `session.handoff` in the stable developer profile after exact persistence and privacy checks. |
| Archive instead of silent deletion | `galactic_map.py`, lifecycle and quarantine modules | Make archive, pin, export, forget, and restore explicit user-visible operations. Avoid destructive automatic forgetting. |
| Project-scoped memory | v26 galaxy routing and codebase metadata | Add a project/repository scope so unrelated projects cannot contaminate recall. |
| Diagnostics and onboarding | `wm init`, `wm doctor`, `wm quickstart`, starter packs | Make setup, index health, backup, recovery, and profile selection first-class. |

The XP system from `WHITEMAGIC-CORE` is not recommended literally. Its better
idea is capability packs such as `core`, `session`, `governance`, `coding`, and
`research`, selected by configuration rather than hidden behind gamification.

### Later Developer Product

These are strong candidates once the core release is reliable:

- **Codebase memory:** incremental file scanning, overlapping chunks, content
  hashes, project manifests, and semantic code recall from
  `core/whitemagic/core/memory/codebase_scanner.py`.
- **Code structure graph:** calls, imports, definitions, references, impact
  analysis, communities, and path queries from
  `core/whitemagic/core/intelligence/code_structure_graph.py`. v5 already has
  `code.graph`, `code.query`, `code.affected_by`, and `fragment.search`; the
  next task is correctness, project scoping, and useful client integration, not
  another port.
- **Evidence-backed skills:** `SkillForge` has duplicate detection, execution
  history, evidence thresholds, version history, amendment proposals, and
  rollback. Port the contract only after adding human approval, effect checks,
  reproducibility, and an explicit dry-run mode.
- **Portable skill and memory packages:** signed manifests, schemas, provenance,
  version constraints, and export/import that work across agents and projects.
- **Knowledge and association graph:** temporal relationships, provenance, and
  graph navigation when they demonstrably improve answers rather than merely
  increasing structure.
- **Project starter packs:** coding, research, writing, and migration templates
  that configure memory behavior, prompts, and safe tool profiles.
- **Reproducible evaluation:** LongMemEval, LoCoMo, and project-specific tests
  run through the actual production retrieval path with per-category results.

### Research or Defer

Do not make these public-release dependencies:

- Continuous consciousness, biological interpretations, emotional/neural
  claims, and always-on heartbeat behavior.
- Oracle, prescience, astrology, I Ching, quantum, and topological branding
  unless a narrowly defined empirical use case emerges.
- Autonomous file editing, shell execution, self-modification, or recursive
  code application without human approval and a real rollback boundary.
- Mesh/P2P inference, economies, bounties, marketplaces, and cross-agent
  trading.
- The complete polyglot matrix. Use a native bridge only after profiling proves
  a real bottleneck and the bridge has integration coverage.
- Gardens, Grimoire, war-room, and other naming layers that duplicate memory,
  search, governance, or orchestration.

## What the Benchmarks Actually Say

The archive contains useful evaluation infrastructure and results, but the
results need careful interpretation.

`benchmarks/results/longmemeval_s_full.json` reports 500 questions with:

- Recall@1: 0.858
- Recall@5: 0.936
- Recall@10: 0.966
- MRR: 0.892
- Search p50: 17 ms
- Search p95: 323 ms
- Search p99: 916 ms

That is promising evidence that the memory concepts can work. It is not yet a
v5 release claim because the adapter bypasses parts of the production
enrichment/planner path and v5 has not reproduced the result with its current
store and response contract.

The 50K FTS5 result is equally important: p50 search is only 4.4 ms, but
Recall@1 is 0.435 and Recall@10 is 0.61. Fast retrieval that returns the wrong
memory is not a product advantage. Retrieval quality, conflict handling,
provenance, and abstention matter more than another microbenchmark.

The next evaluation should run the real v5 curated path and report:

- Recall@1, @5, @10, MRR, and answer-supported accuracy.
- Single-session, multi-session, temporal, preference, and knowledge-update
  categories separately.
- Fresh-store, migrated-store, 10K, 50K, and restart conditions.
- p50, p95, p99 latency and index-build time.
- False recall, stale recall, privacy leakage, and unsupported-answer rates.

## v6+ Architecture Direction

Rust and LMDB are not the problem to solve first. The immediate problem is a
clear persistence contract between canonical memory records and derived search
indexes.

### Keep Rust for the Core

Rust remains the best default for:

- A single portable binary.
- Typed effects, bounded resource use, and explicit error handling.
- Local storage and index orchestration.
- MCP transport and security boundaries.
- Optional native acceleration behind small, tested FFI surfaces.

Do not rewrite the core in Go, C++, Julia, or Python for v6. The cost would be
large and the user-visible benefit unclear. Python and TypeScript should remain
thin client, SDK, notebook, or integration layers.

### Reconsider the Storage Boundary, Not the Whole Language

LMDB is a reasonable local canonical store, but its constraints should be
acknowledged:

- One writer and file-lock behavior complicate concurrent processes.
- Map sizing and growth are operational concerns.
- Secondary indexes and Tantivy are separate consistency domains.
- Vector storage and remote/team sync need additional systems.
- Schema evolution and exact multi-galaxy transactions require deliberate
  wrappers.

Before changing storage, introduce a narrow store contract and measure real
workloads. Candidates for a future adapter are:

- **SQLite + FTS5:** easiest backup, migration, inspection, and Python
  interoperability; likely the best simplicity option for small local stores.
- **SQLite plus a vector extension or separate vector index:** attractive if
  one-file operation matters, but requires careful extension portability tests.
- **redb or another pure-Rust embedded store:** worth benchmarking if typed
  transactions and a simpler single-file deployment outweigh ecosystem depth.
- **PostgreSQL plus vector search:** appropriate for an optional team or hosted
  edition, not the default local-first deployment.

The likely v6 architecture is a canonical record/journal layer plus derived
FTS/vector indexes rebuilt from an outbox or journal. That solves correctness
regardless of whether the canonical backend remains LMDB or becomes SQLite.

### A Useful v6 Boundary

If v5 stabilizes, v6 should focus on:

1. Project-scoped memory and a stable memory interchange format.
2. Exact provenance, citations, conflict detection, and user-controlled
   retention.
3. A storage adapter boundary with migration and backup guarantees.
4. Optional encrypted sync or team relay, with authenticated identities.
5. Codebase memory and impact analysis as a first-class developer pack.
6. Public, reproducible memory evaluation.

That is a coherent version. A second rewrite of the cognitive vocabulary is
not.

## Product Ideas Worth Adding

### 1. `memory.wake` as the Core User Experience

The most useful old idea is a bounded context pack. Given a project and session,
return only:

- Where the previous session stopped.
- Recent decisions and unresolved questions.
- Relevant project memories and code references.
- Current branch/commit metadata when available.
- Source IDs, ages, scores, and reasons for every included item.

The caller supplies a token budget and focus. The result is deterministic,
citable, and safe to inject into an agent prompt. This is more valuable than
asking users to understand galaxies, Ganas, or dream phases.

### 2. Trustworthy Memory, Not Silent Memory

Every recalled item should expose provenance and allow the user or agent to
pin, accept, reject, correct, archive, or forget it. Models should not silently
rewrite durable memory. Feedback can improve ranking, but changes to durable
facts should be explicit and auditable.

### 3. Project Memory for Coding Agents

The strongest differentiated path is not general “consciousness.” It is:

> Remember why this code exists, what was tried, what failed, and what should
> happen next.

Combine session continuity, Git-aware decisions, code fragments, code graph
queries, and citations. That gives a developer an immediate reason to install
WhiteMagic.

### 4. Open Evaluation as a Product Asset

Ship `wm eval` or a separate evaluation repository that runs public memory
benchmarks and a small WhiteMagic-specific suite. Honest category-level results
will build more trust than claims about 229 tools or consciousness.

## Usefulness Assessment

Yes, WhiteMagic could be useful to people and AI systems globally, but not by
being the largest agent architecture. It can be useful if it becomes:

- Easy to install in under five minutes.
- Reliable after restart and migration.
- Privacy-preserving by default.
- Compatible with the major MCP clients.
- Better at project/session continuity than plain prompt files.
- Honest when recall is weak or conflicting.
- Small enough that users understand what they installed.

The first likely users are local-AI developers, privacy-conscious teams,
researchers, and coding-agent power users. Global reach comes later through
portable formats, translations, low-resource deployment, and integrations, not
through adding more internal subsystems.

## Solo Developer Business Paths

The fastest route to income is probably not a consumer SaaS product. It is
open-core infrastructure plus applied work:

1. **Paid implementation pilots:** integrate agent memory, MCP, local models,
   retrieval evaluation, or governance into a small team's workflow.
2. **Architecture and safety reviews:** audit agent memory, tool permissions,
   prompt/data boundaries, and MCP deployments.
3. **Supported local distribution:** sell updates, managed installation,
   backups, observability, policy configuration, and response-time support while
   keeping the core local and open.
4. **Developer edition:** add project code memory, Git/IDE integrations, team
   handoff, and a polished UI as paid conveniences around the open core.
5. **Evaluation tooling:** package the memory benchmark harness and regression
   suite for companies building agents.
6. **Sponsorship and grants:** useful for credibility and runway, but not a
   substitute for a paying user with a recurring problem.

Example pilot pricing might be a fixed few-thousand-dollar integration or a
short paid discovery engagement, then a support retainer. The exact number
depends on the buyer and your market; the important milestone is one customer
paying for a concrete outcome, not a large audience applauding the architecture.

### Marketing for an R&D-Oriented Developer

You do not need to become a full-time marketer. Make the technical work carry
the marketing:

- Publish one clear sentence, one 90-second demo, one install command, and one
  benchmark table.
- Demonstrate restart continuity, project code recall, and local privacy.
- Ask 10 target users to install it while you watch where they fail.
- Find three design partners and aim for one paid pilot before expanding scope.
- Write technical notes about retrieval quality, failure modes, and agent
  memory. This attracts the kind of users who value R&D.
- Use consulting to fund the open-source product, then add a customer-facing
  partner only when demand justifies it.

The practical first business is likely “I help teams make local agents retain
useful, auditable context,” with WhiteMagic as the system behind that service.
That lets you stay close to research while selling an outcome customers already
understand.
