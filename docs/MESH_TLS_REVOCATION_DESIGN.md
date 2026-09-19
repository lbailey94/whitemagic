# Mesh transport confidentiality + key lifecycle — design decision (W1 residual)

**Status:** design decision recorded 2026-09-19 (W1 security residual;
`HG-S1-7` / `L-S7` family). **No implementation in 9.2.0** — this note fixes
the direction so the assurance wave (Q26) builds one design, not two.
**Related:** `docs/MESH_JOIN_PROTOCOL.md` (§3 identity, §11 limitations),
`docs/SANGHA_SECURITY.md`, V8 backlog item 2 (key material handling),
`docs/Q39_CRYPTO_ERASURE_DESIGN.md` (storage side; do not conflate).

## Problem

v0 mesh traffic is plaintext TCP/UDP on the local link: a passive local
observer can read chat and signals, and (without TLS) any host that can
reach the port can open connections — authentication currently happens at
the *application* layer (signed heartbeats, signed chat, authority grants).
There is no in-transit encryption, no revocation list, and key material is
file/env-based with no rotation procedure.

## What already exists (do not rebuild)

- Ed25519 node identity, stable across restarts with `WM_MESH_KEY` (HKDF
  subkeys) and TOFU/PIN binding in the local registry.
- Local authority grants (`mesh_authority.json`) with pin-or-tofu; a pinned
  grant **reserves its peer ID at the bind seam** (E10, `1cc4cc9`).
- Per-node quarantine (refuse + purge + revoke + drop) enforced at ingest.
- Signed heartbeats/chat with replay windows and envelope dedup.

## Decision

**TLS 1.3 with identity-pinned certificates, keyed from the existing mesh
identity, plus rotation as a first-class operation.** Concretely:

1. **Transport:** `rustls` (workspace-pinned, no OpenSSL) wrapping the mesh
   TCP listener and dialer. UDP multicast discovery stays plaintext — it
   carries only signed announcements (already signature-verified), never
   chat/signals; a beacon is a hint, not a channel.
2. **Node certificates:** each node mints a self-signed certificate whose
   keypair is derived from its mesh identity (`wm/mesh-tls/v1/<peer>` HKDF
   subkey, same discipline as `wm/mesh-identity/v1`). Peers pin the
   **SPKI/certificate fingerprint** observed at bind time — the same
   TOFU-then-pin semantics the registry already uses — and a pinned grant
   additionally pins it by policy. No CA, no PKI, no external dependency:
   certificate verification is "does this match the key I already bound or
   was granted".
3. **Revocation:** three layers, in order of authority:
   - local quarantine (already implemented) refuses the connection at the
     TLS handshake by refusing the pinned fingerprint;
   - pinned-grant reservation (E10) prevents name squatting;
   - **rotation:** a node rotates its mesh key on a documented schedule
     (`wm mesh rotate` — Q26 deliverable). Rotation re-derives the TLS
     cert, re-announces a signed rotation record (old key signs the new
     key), and peers update pins on verification; a rotation without a
     valid old-key signature is treated as a new identity (TOFU), never as
     the same peer.
4. **Migration:** the transport feature-negotiates. In `TLS=required` mode
   (the fleet end-state default for `wm-serve@*`), a plaintext peer is
   refused with a named error; `WM_MESH_TLS=advisory` accepts both during a
   window and logs loudly — the same loud-degrade contract as Firebreak /
   Landlock.

## Alternatives considered

- **Noise protocol (XX/IK):** elegant and pinning-native, but adds a second
  crypto dependency and hand-rolled channel binding; rustls + SPKI pinning
  reuses the identity model we already test. Revisit only if rustls proves
  a packaging burden on musl.
- **Bearer tokens over plaintext:** confuses authentication with
  confidentiality; rejected.
- **WireGuard/tailnet overlay:** deployment burden outside the product;
  keep as an operator option, not a product path.

## Non-goals

- Hiding peer presence from a local observer (beacons stay visible; they
  are signed).
- Post-quantum transport (track upstream; identity algorithm change is a
  separate decision).
- Cross-subnet discovery / relay (unchanged; not a security property).

## Open questions (for the Q26 slice)

1. Certificate lifetime: per-process ephemeral vs keyed (recommend keyed —
   pins must survive restarts).
2. Rotation cadence default (proposal: 90 days, operator-overridable) and
   whether rotation is automatic or explicit.
3. Whether `advisory` TLS should be allowed at all after the Q26 wave, or
   become a build-time feature flag only.
4. Interaction with the Q39 at-rest keys: keep **separate** derivation
   domains (transport ≠ storage) — stated as a hard rule, not a question.
