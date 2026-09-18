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
    // timeout_connect caps the TCP/TLS connect phase explicitly: under
    // network saturation the global deadline does not fire while connect
    // rotates candidate IPs (observed 9.1.6: grimoire's release step hung
    // past its 5s global timeout against a saturated link).
    let agent = ureq::config::Config::builder()
        .timeout_global(Some(timeout))
        .timeout_connect(Some(timeout))
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
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
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

/// Target key for the running platform (matches the manifest's target keys).
#[must_use]
pub const fn current_target() -> Option<&'static str> {
    if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
        Some("linux-x86_64-musl")
    } else if cfg!(all(target_os = "macos", target_arch = "x86_64")) {
        Some("macos-x86_64")
    } else if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        Some("macos-aarch64")
    } else if cfg!(all(target_os = "windows", target_arch = "x86_64")) {
        Some("windows-x86_64")
    } else {
        None
    }
}

/// Sibling path for a binary (`/usr/bin/wm` -> `/usr/bin/wm.previous`).
#[must_use]
pub fn sibling(exe: &Path, suffix: &str) -> PathBuf {
    let mut name = exe
        .file_name()
        .map_or_else(|| "wm".into(), std::ffi::OsStr::to_os_string);
    name.push(format!(".{suffix}"));
    exe.with_file_name(name)
}

/// SHA-256 of a file (streaming; no size ceiling).
///
/// # Errors
/// IO failures opening or reading the file.
pub fn sha256_file(path: &Path) -> anyhow::Result<String> {
    use sha2::{Digest, Sha256};
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher)?;
    Ok(format!("{:x}", hasher.finalize()))
}

/// Stream a URL to `dest`, returning the byte count.
///
/// # Errors
/// Network, HTTP, or IO failure.
pub fn download_to(url: &str, dest: &Path, timeout: Duration) -> anyhow::Result<u64> {
    let agent = ureq::config::Config::builder()
        .timeout_global(Some(timeout))
        .timeout_connect(Some(timeout))
        .build()
        .new_agent();
    let response = agent
        .get(url)
        .call()
        .map_err(|e| anyhow::anyhow!("download failed: {e}"))?;
    let mut reader = response.into_body().into_reader();
    let mut file = std::fs::File::create(dest)?;
    let n = std::io::copy(&mut reader, &mut file)?;
    use std::io::Write as _;
    file.flush()?;
    Ok(n)
}

/// Parse the version a binary reports (`wm 9.1.4` -> `9.1.4`).
///
/// # Errors
/// The binary failed to run or exited non-zero.
pub fn version_of(binary: &Path) -> anyhow::Result<String> {
    let out = std::process::Command::new(binary)
        .arg("--version")
        .output()
        .map_err(|e| anyhow::anyhow!("could not run {}: {e}", binary.display()))?;
    if !out.status.success() {
        anyhow::bail!("{} --version exited {}", binary.display(), out.status);
    }
    let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
    Ok(text.split_whitespace().last().unwrap_or(&text).to_string())
}

/// Run the candidate's own `wm selftest --json` and require an explicit pass.
///
/// # Errors
/// The candidate could not be executed.
pub fn candidate_selftest_ok(candidate: &Path) -> anyhow::Result<(bool, String)> {
    let out = std::process::Command::new(candidate)
        .args(["selftest", "--json"])
        .output()
        .map_err(|e| anyhow::anyhow!("could not run candidate selftest: {e}"))?;
    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    let parsed: serde_json::Value = serde_json::from_str(stdout.trim()).unwrap_or_default();
    let passed = out.status.success()
        && parsed.get("passed").and_then(serde_json::Value::as_bool) == Some(true);
    Ok((passed, stdout))
}

/// Result of a transactional install (`wm update install`).
#[derive(Debug, Clone, Serialize)]
pub struct InstallReport {
    pub from: String,
    pub to: String,
    pub backup: Option<String>,
    pub selftest_ok: bool,
    pub dry_run: bool,
    pub swapped: bool,
}

/// Install a verified candidate over `exe`: selftest gate -> backup ->
/// atomic swap -> health check (auto-rollback on failure) -> state update.
///
/// # Errors
/// Selftest refusal, IO failure, or a post-swap health-check failure (which
/// rolls the previous binary back into place before returning).
pub fn install_from_file(
    exe: &Path,
    candidate: &Path,
    new_version: &str,
    state_root: &Path,
    dry_run: bool,
) -> anyhow::Result<InstallReport> {
    let old_version = version_of(exe).unwrap_or_else(|_| env!("CARGO_PKG_VERSION").to_string());
    let (selftest_ok, selftest_out) = candidate_selftest_ok(candidate)?;
    if !selftest_ok {
        anyhow::bail!("candidate failed `wm selftest` — refusing to install:\n{selftest_out}");
    }
    if dry_run {
        return Ok(InstallReport {
            from: old_version,
            to: new_version.to_string(),
            backup: None,
            selftest_ok,
            dry_run: true,
            swapped: false,
        });
    }

    let backup = sibling(exe, "previous");
    std::fs::copy(exe, &backup)?;
    std::fs::rename(candidate, exe).map_err(|e| {
        anyhow::anyhow!(
            "atomic swap failed ({e}); on Windows a running binary cannot be replaced \
             in place — use the platform installer"
        )
    })?;

    let after = match version_of(exe) {
        Ok(v) => v,
        Err(e) => {
            let _ = std::fs::rename(&backup, exe);
            anyhow::bail!("post-swap health check failed ({e}) — rolled back to {old_version}");
        }
    };
    if !after.contains(new_version) {
        let _ = std::fs::rename(&backup, exe);
        anyhow::bail!(
            "post-swap health check: binary reports '{after}', expected {new_version} — \
             rolled back to {old_version}"
        );
    }

    let mut state = read_install_state(state_root).unwrap_or_else(|| InstallState {
        schema: 1,
        installed_via: detect_installed_via(exe).to_string(),
        version: old_version.clone(),
        previous: None,
        channel: "stable".to_string(),
        update_policy: "notify".to_string(),
        last_check: None,
        latest_seen: None,
    });
    state.previous = Some(old_version.clone());
    state.version = new_version.to_string();
    state.last_check = Some(chrono::Utc::now().to_rfc3339());
    state.latest_seen = Some(new_version.to_string());
    let _ = write_install_state(state_root, &state);

    Ok(InstallReport {
        from: old_version,
        to: new_version.to_string(),
        backup: Some(backup.display().to_string()),
        selftest_ok,
        dry_run: false,
        swapped: true,
    })
}

/// Restore the binary saved by the last `wm update install`.
///
/// # Errors
/// No saved binary, or the restore/health check failed.
pub fn rollback_install(exe: &Path, state_root: &Path) -> anyhow::Result<String> {
    let backup = sibling(exe, "previous");
    if !backup.is_file() {
        anyhow::bail!("no previous binary saved at {}", backup.display());
    }
    std::fs::rename(&backup, exe)?;
    let version = version_of(exe)?;
    let mut state = read_install_state(state_root).unwrap_or_else(|| InstallState {
        schema: 1,
        installed_via: detect_installed_via(exe).to_string(),
        version: version.clone(),
        previous: None,
        channel: "stable".to_string(),
        update_policy: "notify".to_string(),
        last_check: None,
        latest_seen: None,
    });
    state.previous = None;
    state.version.clone_from(&version);
    state.last_check = Some(chrono::Utc::now().to_rfc3339());
    let _ = write_install_state(state_root, &state);
    Ok(version)
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

    /// The funnel classifier lives in `wm-tools` (below `wm-mcp` in the
    /// dependency graph) and duplicates this heuristic by necessity — this
    /// test fails the moment the two drift.
    #[test]
    fn funnel_detection_matches_wm_update() {
        for path in [
            "/home/x/.cargo/bin/wm",
            "/opt/homebrew/Cellar/whitemagic/9.1.9/bin/wm",
            "/usr/local/homebrew/bin/wm",
            "/usr/lib/node_modules/whitemagic-mcp/bin/wm",
            "/home/x/.npm/bin/wm",
            "/home/x/.local/bin/wm",
            "/tmp/target/debug/wm",
        ] {
            let exe = Path::new(path);
            assert_eq!(
                wm_tools::expansion::funnel::installed_via_from_exe(exe),
                detect_installed_via(exe),
                "funnel/exe detection drifted at {path}"
            );
        }
    }

    #[test]
    fn platform_target_mapping_exists_on_supported_builds() {
        #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
        assert_eq!(current_target(), Some("linux-x86_64-musl"));
    }

    #[test]
    fn sha256_matches_known_vector() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("payload");
        std::fs::write(&path, b"abc").unwrap();
        assert_eq!(
            sha256_file(&path).unwrap(),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[cfg(unix)]
    fn fake_binary(path: &Path, version: &str) {
        use std::os::unix::fs::PermissionsExt as _;
        let script = format!(
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo \"wm {version}\"; \
             elif [ \"$1\" = \"selftest\" ]; then echo '{{\"passed\": true}}'; fi\n"
        );
        std::fs::write(path, script).unwrap();
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755)).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn transactional_install_and_rollback_with_selftest_gate() {
        let tmp = tempfile::tempdir().unwrap();
        let exe = tmp.path().join("wm");
        let candidate = tmp.path().join("wm.new");
        let root = tmp.path().join("store-root");
        fake_binary(&exe, "1.0.0");
        fake_binary(&candidate, "2.0.0");

        let report = install_from_file(&exe, &candidate, "2.0.0", &root, false).unwrap();
        assert!(report.swapped && report.selftest_ok);
        assert_eq!(report.from, "1.0.0");
        assert!(sibling(&exe, "previous").is_file());
        assert_eq!(version_of(&exe).unwrap(), "2.0.0");
        let state = read_install_state(&root).unwrap();
        assert_eq!(state.version, "2.0.0");
        assert_eq!(state.previous.as_deref(), Some("1.0.0"));

        let rolled = rollback_install(&exe, &root).unwrap();
        assert_eq!(rolled, "1.0.0");
        assert_eq!(version_of(&exe).unwrap(), "1.0.0");
        assert!(read_install_state(&root).unwrap().previous.is_none());
    }

    #[cfg(unix)]
    #[test]
    fn install_refuses_a_candidate_that_fails_selftest() {
        use std::os::unix::fs::PermissionsExt as _;
        let tmp = tempfile::tempdir().unwrap();
        let exe = tmp.path().join("wm");
        let candidate = tmp.path().join("wm.new");
        let root = tmp.path().join("store-root");
        fake_binary(&exe, "1.0.0");
        std::fs::write(
            &candidate,
            "#!/bin/sh\necho '{\"passed\": false}'\nexit 1\n",
        )
        .unwrap();
        std::fs::set_permissions(&candidate, std::fs::Permissions::from_mode(0o755)).unwrap();

        let err = install_from_file(&exe, &candidate, "9.9.9", &root, false).unwrap_err();
        assert!(err.to_string().contains("selftest"), "{err}");
        assert_eq!(version_of(&exe).unwrap(), "1.0.0", "exe must be untouched");
        assert!(!sibling(&exe, "previous").exists());
    }
}
