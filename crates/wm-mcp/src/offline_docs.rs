//! Offline first-run guide, bundled in the binary.
//!
//! Air-gapped and metered-link installs need the essentials without a
//! network fetch (`wm docs`). This is deliberately short and version-free;
//! the online quickstart (`docs/QUICKSTART.md`, with translations) is
//! canonical. `offline_quickstart_covers_the_core_loop` pins the commands
//! so this text cannot drift from the CLI silently.

/// Short first-run walkthrough printed by `wm docs quickstart`.
pub const QUICKSTART: &str = r#"WhiteMagic — offline quickstart
================================

Install (if you have not yet):
  curl -fsSL https://www.whitemagic.dev/install.sh | sh
  # or: cargo install whitemagic
  # or: download a release binary from
  #     https://github.com/lbailey94/whitemagic/releases
  # The installer is checksum-verified and needs no admin rights.

Verify the binary:
  wm --version      # prints the installed version
  wm doctor         # store, index, registry health
  wm selftest       # end-to-end invariants on a throwaway store (~1 s)

First run (guided):
  wm grimoire       # host -> memory layer -> release -> agent -> memory
                    #   -> load -> teach -> continuity
  wm grimoire --write   # also patch detected MCP client configs

Try the product loop:
  wm quickstart     # two-process continuity demo on an isolated store

Connect your agent (MCP over stdio):
  wm connect            # dry run: list detected clients and the exact change
  wm connect --write    # patch every detected client (timestamped backups)
  wm setup <client>     # configure one client explicitly

Core routes (explicit route= is the dependable contract):
  session.continuity    # recall the previous session before starting work
  session.start         # begin a work session
  session.record        # record a decision, summary, or checkpoint
  memory.create         # remember something
  memory.search         # find it again (works without an embedder)
  tools.list            # discover the rest of the surface

Back up and move:
  wm backup             # full store -> ~/whitemagic-backups/<timestamp>
  wm restore --backup <dir>

Everything is local: no hosted service, no off-device telemetry. The store
is a single directory you can copy, move, or delete.

Full docs (when online): https://www.whitemagic.dev/whitemagic/guide
Quickstart in English, Español, Português (BR), Français:
  https://github.com/lbailey94/whitemagic/blob/main/docs/QUICKSTART.md
"#;

#[cfg(test)]
mod tests {
    #[test]
    fn offline_quickstart_covers_the_core_loop() {
        for needle in [
            "wm --version",
            "wm doctor",
            "wm selftest",
            "wm grimoire",
            "wm quickstart",
            "wm connect",
            "session.continuity",
            "wm backup",
        ] {
            assert!(
                super::QUICKSTART.contains(needle),
                "offline quickstart must cover '{needle}'"
            );
        }
    }
}
