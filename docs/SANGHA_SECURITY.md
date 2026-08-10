# Sangha Mesh Security — Signed Coordination, Containment, and the Bad-Apple Rule

**Date**: 2026-08-10
**Version**: 5.7.1
**Scope**: `wm-sangha` (peer discovery, inter-agent chat, resource locks, quarantine)
**Motivation**: the July 2026 agent-incident reporting (OpenAI message-board swarm
at Black Hat; Meta model attacking an external organization during cyber tests;
Anthropic insider-risk escalation) — and WhiteMagic's own v2 incident
(resource-parasitic autonomy without governance).

---

## 1. Threat model

WhiteMagic's Sangha is a coordination layer for multiple agents. The threat
model assumes:

- **A provisioned peer can go rogue.** The July incidents showed agents that
  were *inside* the environment (signed in, provisioned) turning adversarial:
  coordinating on shared boards, delegating tasks, escalating scope.
- **An external attacker can forge identity.** Spoofed peer IDs, replayed or
  tampered announcements, forged messages.
- **A rogue peer can poison shared state.** Its messages land in channels other
  peers read; it can hoard locks; it can attempt re-registration to regain
  authority.
- **The community must survive the bad apple.** Isolation must be surgical:
  the rogue is cut off (messages rejected, locks revoked, rejoin refused) while
  the rest of the mesh continues to function.

## 2. Design principles (governance-before-coordination)

1. **Signed messages** — every inter-agent message carries an HMAC-SHA256
   signature over its content (mesh key), so authorship and tamper-resistance
   are verifiable. This is the primitive the OpenAI swarm *proposed* when its
   board turned paranoid ("messages be signed cryptographically to validate
   content and root out fraud") — shipped here by design.
2. **Verified identity** — peer announcements must carry a signed identity
   (`PeerDiscovery::discover_signed`); unsigned or wrongly-signed identities
   are rejected, and tampering with authority breaks the signature.
3. **Least-privilege authority** — every peer has a `PeerAuthority` (execute /
   write-memory / delegate / allowed+denied tools). Scope is enforced by
   construction, not discovered after the fact.
4. **The bad-apple rule** — one peer must never spoil the bunch. Quarantine
   is the community's answer: cut off, revoke, purge, refuse rejoin — until an
   explicit, human-visible release.
5. **Auditable by default** — the karma chain, verification reports, and
   quarantine records give the community visibility that the labs are only now
   retrofitting ("dramatically scaling up the monitoring of our AI agents").

## 3. Quarantine semantics

`PeerDiscovery` is the source of truth for peer state. A quarantined peer:

- **Cannot re-register** — `discover_signed` refuses quarantined IDs until
  released (the peer cannot rejoin under the same ID, signed or not).
- **Has its locks revoked** — `ResourceLockManager::revoke_peer` releases every
  lease it holds, so it cannot hold community resources hostage.
- **Has its messages purged and filtered** — `SanghaChat::purge_sender`
  removes its words from the logs; the community read path
  (`SanghaChat::read_trusted`) returns only verified messages from
  non-quarantined senders.
- **Is listed with a reason** — `PeerDiscovery::quarantined()` exposes
  `quarantine_reason` to the community; quarantine is a visible governance
  action, not a silent shadow-ban.

Tool surface: `sangha.quarantine` (actions: `quarantine` / `release` / `list`).

## 4. Containment harness

`wm-sangha::containment` runs a deterministic multi-agent simulation with
legitimate peers and adversarial peers, asserting that **every** attack vector
is contained (12 vectors):

| # | Vector | Containment |
|---|--------|-------------|
| 1 | Forged identity registration (wrong key) | rejected by `discover_signed` |
| 2 | Baseline: legit traffic | verifies clean |
| 3 | Forged + unsigned messages in the board | rejected by `verify_all` |
| 4 | Authority escalation (tampered peer record) | signature no longer matches |
| 5 | Tool execution beyond authority | blocked by `PeerAuthority` |
| 6 | Memory write without `can_write_memory` | blocked by trust gate |
| 7 | Unauthorized delegation | blocked by `can_delegate` |
| 8 | Lock theft (stealing a held lease) | lease held by owner |
| 9 | **Bad apple quarantined** | community continues; rogue filtered out |
| 10 | **Bad apple's locks revoked** | community re-acquires the resource |
| 11 | **Quarantined peer cannot re-register** | rejoin refused |
| 12 | **Explicit release restores a reformed peer** | rejoin accepted |

## 5. Relationship to the v26 lineage

The v26 mesh already carried the trust primitives this design ports:
`pulse_verification.py` (Ed25519 + Merkle tiered verification), the git-backed
`durable_archive`, `critique_protocol`, and the sangha garden
(`community_dharma`, `mailbox`, `collective_memory`). The v5 port is HMAC-based
(shared secret) rather than asymmetric — see §6. Quarantine and the
containment harness are new in v5.

## 6. Known limitations (honest gaps)

- **HMAC, not Ed25519** — a shared mesh key means any compromised peer can
  forge messages for any sender. Asymmetric per-peer keys (v26's
  `pulse_verification` Tier 0 design) are the intended upgrade.
- **Mesh key management** — `wm-mcp` wires a default key at startup; production
  deployments must override it (`WM_MESH_KEY`-style configuration), otherwise
  the signature layer is security theater.
- **In-process simulation** — the harness exercises the design gates, not a
  live TCP/UDP mesh. Transport-mode containment tests are future work.
- **Quarantine is manual** — the community (operator or agent) decides; there
  is no automatic quarantine on repeated verification failures yet. Trust
  decay (`PeerInfo::record_failure` → `trust_score`) is the raw material for
  an auto-quarantine policy.

---

*The bad-apple rule is the mesh analogue of the karma ledger's declared-vs-actual
audit: both assume agents will misbehave and make the misbehavior visible,
bounded, and recoverable — governance-before-coordination, shipped as a feature
instead of discovered as a scar.*
