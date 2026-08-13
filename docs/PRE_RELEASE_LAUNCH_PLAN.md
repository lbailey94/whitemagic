# Pre-Release Launch Plan

**Prepared:** 2026-08-13
**Source:** exploration of `/home/lucas/Desktop/WMdocs` (retired v26 documentation vault)
**Status:** candidate actions, not yet scheduled

This plan distills the v26 documentation vault into concrete pre-release
actions for the v5.8 curated release. Items are marked reusable, port-worthy,
or skipped.

## Directly Reusable Assets

1. **Release checklist structure** (`docs/RELEASE_READINESS_CHECKLIST.md` in WMdocs):
   v26's 10-section checklist. The gates that actually caught v26 bugs were
   fresh-install verification, a clean MCP handshake, and SBOM/attestation.
   v5 should mirror these as cargo-oriented gates: fresh-store install on a
   clean machine, MCP handshake with a real client, and a
   `cargo about`/attestation step. Port structure into
   `docs/RELEASE_READINESS.md`.
2. **Legal kit** (`docs/legal/`): SECURITY.md, PRIVACY_POLICY.md,
   TERMS_OF_SERVICE.md, CODE_OF_CONDUCT.md, CITATION.cff. Nearly complete;
   needs v5 versioning and contact refresh. Ship these with the release.
3. **Voice and tone guide** (`docs-2/VOICE_TONE_GUIDE.md`): precision over
   hype, epistemic tags ([Proven]/[Speculative]), do/don't table. Use for all
   v5 launch copy.
4. **MCP config cookbook** (`docs/public/MCP_CONFIG_EXAMPLES.md`): per-client
   configs with schema-adaptation notes for weaker clients. Rewrite entry
   points as `wm serve --profile curated`.
5. **Quickstart template** (`QUICKSTART.md`): 30-second path, verify step,
   MCP connect JSON, troubleshooting. Adapt to cargo install + `wm serve`.
6. **MCP registry listing kit** (`docs/MCP_REGISTRY_LISTING_GUIDE.md`): one-line
   description, feature bullets, tags, and the quality-prep checklist. Note the
   MCP tool annotations (readOnlyHint/destructiveHint/idempotentHint) — v5 can
   derive these automatically from `EffectRow` in `tools.list`.

## Port-Worthy Ideas

7. **Distribution strategy** (`docs-2/message_board/DISTRIBUTION_STRATEGY.md`):
   the official MCP registry is the meta-registry everything crawls; `llms.txt`
   is hygiene, not strategy; monetization is MIT core + optional hosted
   endpoint later. Adopt for v5.
8. **Public-claims discipline** (`docs/STRATEGY_TRUE_RELEASE_2026.md`): every
   benchmark/feature claim on README/site must cite a fresh run against the
   release commit with config + date. Add to `docs/RELEASE_READINESS.md` gates.
9. **Session UX positioning** (`docs/message_board/NEXT_SESSION_ONBOARDING.md`,
   `docs/MODEL_GUIDE.md`): auto-record + continuity + selective replay was
   v26's highest-value addition (21,357 session memories). v5 already has the
   tools and now the restored history — make session continuity the lead story
   of the curated release, with a trimmed MODEL_GUIDE as the curated primer.
10. **Token-economics framing** (`docs/WHITEMAGIC_EFFECT.md`): "models don't
    need to be bigger, they need to stop wasting tokens on housekeeping."
    Usable launch thesis for a Rust memory server.
11. **WMV5_ANALYSIS P1 shortlist** (`docs/message_board/WMV5_ANALYSIS.md`):
    externally-scoped pre-release improvements — `context.inject`/`memory.wake`,
    usage analytics, an audit-pack generator, and a firebreak for the claims
    ledger. `memory.wake` is already the top UX item in
    `docs/ARCHIVE_CAPABILITY_MAP.md`; the others are candidates after release.
12. **Dormant-systems audit** (`docs/DORMANT_SYSTEMS_AUDIT_2026-07-30.md`): the
    wiring-audit pattern (handlers without dispatch, registry orphans). Run the
    same pattern over v5's 229 tools as a pre-release gate — extends the effect
    inventory audit already tracked in RELEASE_READINESS.

## Skipped

- META_STRATEGY / XPRIZE / macro-economics essays — separate writing project,
  not launch content.
- v26 Python-specific engineering backlog — superseded by Rust.
- Grimoire/prescience/consciousness branding — off-brand for a memory server.
- Python/PyPI distribution mechanics — superseded by cargo + `wm serve`.

## Suggested Execution Order

1. Derive MCP tool annotations from EffectRow and surface them in tools.list
   (small, standards-aligned, registry-ready).
2. Port the release checklist gates (fresh-install, MCP handshake, SBOM) into
   RELEASE_READINESS and add the public-claims discipline.
3. Port the legal kit + voice guide + MCP config cookbook + quickstart
   template into the v5 tree.
4. Prepare the MCP registry listing (one-liner, bullets, tags).
5. Write the launch story around session continuity + token economics, citing
   fresh benchmark runs only.
6. Post-release: memory.wake, usage analytics, claims firebreak.
