# WhiteMagic Core Promotion Checklist

## Purpose

This checklist operationalizes the Labs/Core charter.

Use it whenever code, docs, tests, assets, or examples are considered for promotion from **Whitemagic Labs** into **Whitemagic Core**.

An item should not be promoted into Core unless every required gate below is satisfied or an explicit exception is documented.

## Artifact Identification

- [ ] **Artifact is named clearly**
  - Record the file, directory, or logical surface being promoted.
- [ ] **Source location is known**
  - Note where it currently lives in Labs.
- [ ] **Destination in Core is known**
  - Note where it will land in Core.
- [ ] **Owner/responsible reviewer is known**
  - Identify who is accountable for deciding whether it belongs in Core.

## Core Eligibility Gate

- [ ] **Public value is clear**
  - The artifact helps a public user, contributor, operator, or release workflow.
- [ ] **Artifact is legible**
  - A reader can understand what it is for and whether it is stable, optional, or experimental.
- [ ] **It increases trust rather than confusion**
  - Its presence in Core makes the public repo clearer, safer, or more useful.
- [ ] **It reflects the system that actually ships**
  - The artifact describes or implements current shipped reality rather than a Labs-only aspiration.

## Safety and Privacy Gate

- [ ] **No personal or machine-local paths are embedded**
  - No hard-coded absolute home directory paths or other private machine assumptions remain.
- [ ] **No private operational data is embedded**
  - No private corpora, logs, memories, tokens, or environment-specific state are included.
- [ ] **No accidental runtime state is included**
  - DB files, caches, logs, build outputs, temporary outputs, and profiling residue are excluded.
- [ ] **Secrets and sensitive config are excluded**
  - No API keys, private endpoints, tokens, or unsafe defaults are shipped.

## Portability Gate

- [ ] **State writes are externalized**
  - Writable state resolves through `WM_STATE_ROOT` or another approved non-repo path.
- [ ] **Dependencies are declared or optional**
  - The artifact does not assume undeclared local dependencies.
- [ ] **Graceful degradation exists where needed**
  - Optional accelerators or heavy subsystems fail gracefully when absent.
- [ ] **Core install path remains simple**
  - The artifact does not silently expand the minimum public install burden without an explicit decision.

## Contract and Quality Gate

- [ ] **Surface is classified**
  - Mark as stable, optional, experimental, or Labs-only.
- [ ] **Tool/API behavior is clear**
  - Inputs, outputs, and expectations are intelligible and documented where needed.
- [ ] **Tests or smoke checks exist**
  - There is enough verification to justify shipping the artifact.
- [ ] **Docs are aligned**
  - Related docs describe the same behavior that the promoted artifact actually has.

## Ship-Surface Gate

- [ ] **Artifact belongs in Core by policy**
  - It is not better classified as Labs-only or runtime state.
- [ ] **Ignore and packaging rules are correct**
  - The artifact will be included or excluded intentionally in Git, package, and release outputs.
- [ ] **No one-off helper residue is attached**
  - Ad hoc repair or investigation files are not being promoted accidentally.
- [ ] **Promotion diff is reviewable**
  - The change from Labs to Core is small enough and clear enough to audit.

## Preflight Gate

- [ ] **Path-leak checks pass**
- [ ] **Ship-surface contamination checks pass**
- [ ] **Relevant test lane passes**
- [ ] **Docs delta has been reviewed**
- [ ] **Promotion manifest entry is ready**

## Decision

- [ ] **Promote to Core**
- [ ] **Keep in Labs**
- [ ] **Move to runtime state**
- [ ] **Needs follow-up before decision**

## Decision Notes

- **Reasoning**:
- **Risks**:
- **Follow-up required**:
- **Verification performed**:
- **Docs updated**:
