# WhiteMagic Labs and Core Charter

## Purpose

This charter defines the operating boundary between **Whitemagic Labs** and **Whitemagic Core**.

It exists to preserve a healthy research space without letting research entropy define the public release. The release program assumes that the system which ships publicly should be smaller, calmer, more legible, and more governable than the system that is still evolving in private.

## Canonical Roles

### Whitemagic Labs

`/path/to/whitemagic-core`

Labs is the private development and research environment.

Labs may contain:

- active feature work
- architectural experiments
- migration scaffolding
- historical archives
- campaign artifacts
- one-off repair scripts
- internal notes and analysis
- incomplete or unstable subsystems
- broader operational context than is suitable for public release

Labs is allowed to be broader and higher-entropy than Core, but it is not exempt from discipline. If something remains in Labs, it should still be traceable, classifiable, and reviewable.

### Whitemagic Core

`/path/to/whitemagic-public`

Core is the sanitized public contract and release staging environment.

Core should contain only:

- approved source code
- public-facing documentation
- tests needed to validate the public contract
- packaging and release assets
- intentionally curated examples and sample data
- stable interfaces and clearly labeled optional surfaces

Core must optimize for:

- clarity
- portability
- safety
- public trust
- contributor legibility
- reproducible release operations

### Runtime State

Runtime state belongs to neither Labs nor Core.

Runtime state includes:

- memory databases
- logs
- caches
- local models
- generated benchmark outputs
- temporary files
- machine-local configuration
- local campaign residue
- personal or operational artifacts

Runtime state should be externalized through `WM_STATE_ROOT` or another explicitly documented, non-repo location.

## Core Eligibility Rules

An artifact is eligible for Core only if all of the following are true:

- [ ] **Public value is clear**
  - The artifact supports installation, use, contribution, testing, packaging, or public understanding.
- [ ] **No private or operational data is embedded**
  - The artifact does not expose local corpora, personal paths, logs, or runtime memory state.
- [ ] **Portability is acceptable**
  - The artifact does not rely on machine-specific paths, private infrastructure, or undeclared local dependencies.
- [ ] **Its contract is legible**
  - A contributor or external AI can understand what it does and whether it is stable, optional, or experimental.
- [ ] **Its inclusion is intentional**
  - The artifact belongs in the public ship surface by policy, not by accident.
- [ ] **It passes release hygiene**
  - It survives preflight, diff review, and the relevant validation lane.

If any of these fail, the artifact stays in Labs or moves to runtime state.

## Labs-Only Categories

The following categories are Labs-only unless explicitly promoted later:

- one-off `patch_*` and `fix_*` scripts
- investigation logs and local run logs
- raw archives and excavation artifacts
- experimental subsystems without a stable public contract
- campaign working material
- local benchmark scratch output
- backup tarballs and emergency snapshots
- machine-local models and heavyweight binary assets not required for Core
- internal migration helpers and repair scaffolding

## Runtime-State Exclusions

The following should not ship in Core and should not live in-repo unless intentionally curated as examples:

- `.db`, `.db-wal`, `.db-shm`, `.sqlite*`
- logs and profiling dumps
- `.venv/`, build outputs, caches, compiled artifacts
- private memory corpora
- ad hoc benchmark results tied to a local machine
- temporary outputs from evaluation or release scripts

## Promotion Rules: Labs -> Core

Promotion from Labs to Core is allowed only when:

- [ ] **The artifact is classified**
  - It has been identified as Core-eligible rather than Labs-only or runtime state.
- [ ] **Preflight passes**
  - Path hygiene, ship-surface cleanliness, and release checks pass.
- [ ] **Diff review passes**
  - The movement from Labs into Core is auditable and intentional.
- [ ] **Validation passes**
  - The appropriate Core test or smoke lane passes for the promoted surface.
- [ ] **Docs match the shipped reality**
  - Public docs describe the system that actually ships, not an aspirational or Labs-only variant.

## Documentation Rule

When there is tension between fast-moving innovation and public explanation, use this rule:

- **It is better to document the system that actually ships than to rewrite public docs too early.**

That means structural stabilization should generally precede broad public narrative cleanup.

## Decision Heuristic

Use this simple question set when classifying anything:

1. Is this necessary for a public user, contributor, or release process?
2. Is it portable and safe?
3. Is it stable enough to defend publicly?
4. Can it be explained clearly without private context?
5. Would its presence in Core increase trust rather than confusion?

If the answer is not clearly yes, it does not belong in Core yet.

## Success Condition

This charter is functioning correctly when:

- Labs remains free to innovate rapidly
- Core remains smaller and cleaner than Labs
- runtime state is consistently externalized
- promotion decisions are policy-driven and auditable
- public docs and public code describe the same system
