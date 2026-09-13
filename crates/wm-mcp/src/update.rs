//! Release manifest + `wm update check` (notify-only).
//!
//! GitHub Releases are the canonical product version; crates.io, npm, Docker
//! and the MCP registry are mirrors that may lag. Every release publishes a
//! `release-manifest.json` describing per-target artifacts, and an Ed25519
//! signature over the manifest itself (a checksum in a replaceable manifest
//! protects nothing — the signature is the trust anchor).
//!
//! v1 verification: pinned Ed25519 public key (runtime `WM_RELEASE_PUBKEY`,
//! or compiled in via `option_env!`). If neither is present the check can
//! still run with `--insecure-checksum`, which is loud about verifying only
//! transport integrity, never authenticity. TUF-style key rotation and
//! rollback/freeze protection are the documented next step.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

/// One downloadable artifact for a target triple.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TargetArtifact {
    pub url: String,
    pub sha256: String,
    #[serde(default)]
    pub signature: Option<String>,
}

/// The signed release manifest.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReleaseManifest {
    pub schema: u32,
    pub channel: String,
    pub version: String,
    #[serde(default)]
    pub published: Option<String>,
    #[serde(default)]
    pub minimum_store_schema: Option<u32>,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub targets: BTreeMap<String, TargetArtifact>,
}

/// Local update state (`<store-root>/install.json`).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallState {
    pub schema: u32,
    pub installed_via: String,
    pub version: String,
    #[serde(default)]
    pub previous: Option<String>,
    pub channel: String,
    pub update_policy: String,
    #[serde(default)]
    pub last_check: Option<String>,
    #[serde(default)]
    pub latest_seen: Option<String>,
}

/// Default manifest URL (GitHub Release asset; the same static file for every
/// installation — no identifiers are sent).
pub const DEFAULT_MANIFEST_URL: &str =
    "https://github.com/lbailey94/whitemagic/releases/latest/download/release-manifest.json";

/// Where install state lives beside the store.
#[must_use]
pub fn install_state_path(store_root: &Path) -> PathBuf {
    store_root.join("install.json")
}

/// Guess how this binary was installed (package-manager upgrades are the
/// manager's job, never ours).
#[must_use]
pub fn detect_installed_via(exe: &Path) -> &'static str {
    let p = exe.display().to_string();
    if p.contains("/.cargo/bin/") {
        "cargo"
    } else if p.contains("/Cellar/") || p.contains("/homebrew/") {
        "homebrew"
    } else if p.contains("/node_modules/") || p.contains("/npm/") {
        "npm"
    } else {
        "release-binary"
    }
}

/// Read install state if present.
#[must_use]
pub fn read_install_state(store_root: &Path) -> Option<InstallState> {
    let text = std::fs::read_to_string(install_state_path(store_root)).ok()?;
    serde_json::from_str(&text).ok()
}

/// Write install state (creates the store root if needed).
///
/// # Errors
/// IO failures creating the directory or writing the file.
pub fn write_install_state(store_root: &Path, state: &InstallState) -> anyhow::Result<()> {
    std::fs::create_dir_all(store_root)?;
    let rendered = serde_json::to_string_pretty(state)?;
    std::fs::write(install_state_path(store_root), format!("{rendered}\n"))?;
    Ok(())
}

/// Fetch the manifest text with a bounded timeout.
///
/// # Errors
/// Network or HTTP failure.
pub fn fetch_manifest_text(url: &str, timeout: Duration) -> anyhow::Result<String> {
    let agent = ureq::config::Config::builder()
        .timeout_global(Some(timeout))
        .build()
        .new_agent();
    let response = agent
        .get(url)
        .call()
        .map_err(|e| anyhow::anyhow!("manifest fetch failed: {e}"))?;
    response
        .into_body()
        .read_to_string()
        .map_err(|e| anyhow::anyhow!("manifest read failed: {e}"))
}

/// Resolve the pinned release public key (runtime env wins over the
/// compiled-in value).
#[must_use]
pub fn release_public_key() -> Option<String> {
    if let Ok(k) = std::env::var("WM_RELEASE_PUBKEY") {
        if !k.trim().is_empty() {
            return Some(k.trim().to_string());
        }
    }
    option_env!("WM_RELEASE_PUBKEY")
        .filter(|k| !k.trim().is_empty())
        .map(str::to_string)
}

/// Outcome of a manifest verification attempt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SignatureStatus {
    /// Signature verified against the pinned key.
    Verified,
    /// No pinned key in this build/environment.
    NoKey,
    /// Signature missing from the release.
    Missing,
    /// Signature present but invalid.
    Invalid,
}

/// Verify a manifest signature (hex Ed25519 over the raw manifest bytes).
#[must_use]
pub fn verify_manifest(
    manifest_bytes: &[u8],
    signature_hex: Option<&str>,
    public_key_hex: Option<&str>,
) -> SignatureStatus {
    let (Some(sig), Some(key)) = (signature_hex, public_key_hex) else {
        return if signature_hex.is_none() {
            SignatureStatus::Missing
        } else {
            SignatureStatus::NoKey
        };
    };
    if wm_governance::network_profile::verify_signature(key, manifest_bytes, sig) {
        SignatureStatus::Verified
    } else {
        SignatureStatus::Invalid
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manifest_roundtrip() {
        let m = ReleaseManifest {
            schema: 1,
            channel: "stable".into(),
            version: "9.1.3".into(),
            published: Some("2026-09-13T00:30:17Z".into()),
            minimum_store_schema: Some(7),
            notes: None,
            targets: BTreeMap::from([(
                "linux-x86_64-musl".into(),
                TargetArtifact {
                    url: "https://example/wm-linux-x86_64-musl".into(),
                    sha256: "abc".into(),
                    signature: None,
                },
            )]),
        };
        let text = serde_json::to_string(&m).unwrap();
        let back: ReleaseManifest = serde_json::from_str(&text).unwrap();
        assert_eq!(back.version, "9.1.3");
        assert!(back.targets.contains_key("linux-x86_64-musl"));
    }

    #[test]
    fn signature_status_reports_honestly() {
        assert_eq!(
            verify_manifest(b"x", None, Some("aa")),
            SignatureStatus::Missing
        );
        assert_eq!(
            verify_manifest(b"x", Some("bb"), None),
            SignatureStatus::NoKey
        );
        assert_eq!(
            verify_manifest(b"x", Some("bb"), Some("aa")),
            SignatureStatus::Invalid
        );

        // Round-trip with a real keypair.
        let signer = wm_governance::network_profile::AgentKeypair::from_seed([5u8; 32]);
        let msg = b"{\"schema\":1}";
        let sig = signer.sign_hex(msg);
        assert_eq!(
            verify_manifest(msg, Some(&sig), Some(&signer.public_key_hex())),
            SignatureStatus::Verified
        );
    }

    #[test]
    fn installed_via_detection() {
        assert_eq!(
            detect_installed_via(Path::new("/home/x/.cargo/bin/wm")),
            "cargo"
        );
        assert_eq!(
            detect_installed_via(Path::new("/home/x/.local/bin/wm")),
            "release-binary"
        );
    }
}
