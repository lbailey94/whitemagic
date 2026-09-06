//! Store seal/verify — HMAC-SHA256 integrity manifest for the LMDB store.
//!
//! `wm seal` computes an HMAC-SHA256 digest for every file in the store
//! directory and writes a manifest (`seal.json`).  `wm verify` recomputes
//! the digests and reports any mismatch, missing, or extra files.
//!
//! Key management: a 32-byte per-install secret is stored at
//! `<store>/.seal_key`.  This detects accidental corruption and insider
//! tampering but is not resistant to an adversary with full filesystem
//! access (who could replace both the key and the manifest).

#![forbid(unsafe_code)]

use anyhow::{Context, Result};
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

type HmacSha256 = Hmac<Sha256>;

const SEAL_KEY_FILE: &str = ".seal_key";
const SEAL_MANIFEST_FILE: &str = "seal.json";
const KEY_LEN: usize = 32;

/// One entry per file in the sealed store directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealEntry {
    /// Size in bytes.
    pub size: u64,
    /// HMAC-SHA256 hex digest.
    pub digest: String,
}

/// The full manifest written to `seal.json`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealManifest {
    /// ISO 8601 timestamp of when the seal was created.
    pub sealed_at: String,
    /// Relative path → entry, sorted for deterministic output.
    pub files: BTreeMap<String, SealEntry>,
}

/// Report returned by `verify_store`.
#[derive(Debug)]
pub struct VerifyReport {
    pub matched: usize,
    pub mismatched: Vec<String>,
    pub missing: Vec<String>,
    pub extra: Vec<String>,
}

impl VerifyReport {
    /// True when every file matches and none are missing or extra.
    #[must_use]
    pub fn is_ok(&self) -> bool {
        self.mismatched.is_empty() && self.missing.is_empty() && self.extra.is_empty()
    }
}

// ── Key management ─────────────────────────────────────────────────────

/// Load or generate the per-install seal key.
fn load_or_create_key(store_dir: &Path) -> Result<Vec<u8>> {
    let key_path = store_dir.join(SEAL_KEY_FILE);
    if key_path.exists() {
        let key = std::fs::read(&key_path)
            .with_context(|| format!("reading seal key at {}", key_path.display()))?;
        if key.len() != KEY_LEN {
            anyhow::bail!(
                "seal key at {} is {} bytes, expected {} — delete it and re-seal",
                key_path.display(),
                key.len(),
                KEY_LEN
            );
        }
        Ok(key)
    } else {
        let key = generate_random_bytes(KEY_LEN)?;
        std::fs::write(&key_path, &key)
            .with_context(|| format!("writing seal key to {}", key_path.display()))?;
        // Restrict permissions on the key file
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let _ = std::fs::set_permissions(&key_path, std::fs::Permissions::from_mode(0o600));
        }
        Ok(key)
    }
}

/// Generate `n` random bytes from `/dev/urandom` (Linux) with a fallback
/// to a time+PID hash. Reads exactly `n` bytes — never the whole device.
fn generate_random_bytes(n: usize) -> Result<Vec<u8>> {
    use std::io::Read;
    let mut buf = vec![0u8; n];
    if let Ok(mut file) = std::fs::File::open("/dev/urandom") {
        if file.read_exact(&mut buf).is_ok() {
            return Ok(buf);
        }
    }
    // Fallback: hash of timestamp + PID (low entropy, but better than nothing)
    use sha2::Digest;
    let mut hasher = Sha256::new();
    hasher.update(
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos()
            .to_le_bytes(),
    );
    hasher.update(std::process::id().to_le_bytes());
    let hash = hasher.finalize();
    Ok(hash[..n].to_vec())
}

// ── File walking ───────────────────────────────────────────────────────

/// Recursively walk a directory and return (relative_path, full_path) pairs,
/// excluding the seal key and manifest files themselves.
fn walk_store(dir: &Path) -> Result<Vec<(String, PathBuf)>> {
    let mut files = Vec::new();
    walk_inner(dir, dir, &mut files)?;
    // Exclude seal key and manifest from the sealed set
    files.retain(|(rel, _)| rel != SEAL_KEY_FILE && rel != SEAL_MANIFEST_FILE);
    files.sort_by(|a, b| a.0.cmp(&b.0));
    Ok(files)
}

fn walk_inner(root: &Path, current: &Path, files: &mut Vec<(String, PathBuf)>) -> Result<()> {
    for entry in std::fs::read_dir(current)
        .with_context(|| format!("reading directory {}", current.display()))?
    {
        let entry = entry?;
        let path = entry.path();
        let rel = path
            .strip_prefix(root)
            .unwrap_or(&path)
            .to_string_lossy()
            .to_string();
        if path.is_dir() {
            walk_inner(root, &path, files)?;
        } else if path.is_file() {
            files.push((rel, path));
        }
    }
    Ok(())
}

/// Compute HMAC-SHA256 of a file's contents.
fn hmac_file(path: &Path, key: &[u8]) -> Result<String> {
    let data = std::fs::read(path).with_context(|| format!("reading {}", path.display()))?;
    let mut mac =
        HmacSha256::new_from_slice(key).map_err(|e| anyhow::anyhow!("HMAC key error: {e}"))?;
    mac.update(&data);
    let bytes = mac.finalize().into_bytes();
    use std::fmt::Write as _;
    let mut digest = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut digest, "{byte:02x}").expect("writing to a String cannot fail");
    }
    Ok(digest)
}

// ── Public API ─────────────────────────────────────────────────────────

/// Seal the store directory: compute HMAC digests for all files and write
/// the manifest.
pub fn seal_store(store_dir: &Path) -> Result<SealManifest> {
    let key = load_or_create_key(store_dir)?;
    let files = walk_store(store_dir)?;

    let mut entries = BTreeMap::new();
    for (rel, full) in &files {
        let size = std::fs::metadata(full)?.len();
        let digest = hmac_file(full, &key)?;
        entries.insert(rel.clone(), SealEntry { size, digest });
    }

    let manifest = SealManifest {
        sealed_at: chrono::Utc::now().to_rfc3339(),
        files: entries,
    };

    let manifest_path = store_dir.join(SEAL_MANIFEST_FILE);
    let json = serde_json::to_string_pretty(&manifest).context("serializing seal manifest")?;
    std::fs::write(&manifest_path, json)
        .with_context(|| format!("writing seal manifest to {}", manifest_path.display()))?;

    Ok(manifest)
}

/// Verify the store directory against a previously written seal manifest.
pub fn verify_store(store_dir: &Path) -> Result<VerifyReport> {
    let key_path = store_dir.join(SEAL_KEY_FILE);
    if !key_path.exists() {
        anyhow::bail!(
            "No seal key found at {}. Run 'wm seal' first.",
            key_path.display()
        );
    }
    let key = std::fs::read(&key_path)
        .with_context(|| format!("reading seal key at {}", key_path.display()))?;

    let manifest_path = store_dir.join(SEAL_MANIFEST_FILE);
    if !manifest_path.exists() {
        anyhow::bail!(
            "No seal manifest found at {}. Run 'wm seal' first.",
            manifest_path.display()
        );
    }
    let manifest_json = std::fs::read_to_string(&manifest_path)
        .with_context(|| format!("reading seal manifest at {}", manifest_path.display()))?;
    let manifest: SealManifest =
        serde_json::from_str(&manifest_json).context("parsing seal manifest")?;

    let current_files = walk_store(store_dir)?;
    let current_set: std::collections::HashSet<&String> =
        current_files.iter().map(|(rel, _)| rel).collect();

    let mut matched = 0;
    let mut mismatched = Vec::new();
    let mut missing = Vec::new();

    for (rel, entry) in &manifest.files {
        if !current_set.contains(rel) {
            missing.push(rel.clone());
            continue;
        }
        let full = store_dir.join(rel);
        let digest = hmac_file(&full, &key)?;
        if digest == entry.digest {
            matched += 1;
        } else {
            mismatched.push(rel.clone());
        }
    }

    let manifest_set: std::collections::HashSet<&String> = manifest.files.keys().collect();
    let extra: Vec<String> = current_files
        .iter()
        .filter(|(rel, _)| !manifest_set.contains(rel))
        .map(|(rel, _)| rel.clone())
        .collect();

    Ok(VerifyReport {
        matched,
        mismatched,
        missing,
        extra,
    })
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn seal_then_verify_passes() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"hello world").unwrap();
        std::fs::write(dir.path().join("lock.mdb"), b"lock").unwrap();
        std::fs::create_dir_all(dir.path().join("tantivy")).unwrap();
        std::fs::write(dir.path().join("tantivy/meta.json"), b"{}").unwrap();

        let manifest = seal_store(dir.path()).unwrap();
        assert_eq!(manifest.files.len(), 3);

        let report = verify_store(dir.path()).unwrap();
        assert!(report.is_ok());
        assert_eq!(report.matched, 3);
    }

    #[test]
    fn verify_detects_modification() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"original").unwrap();

        seal_store(dir.path()).unwrap();

        // Tamper with the file
        std::fs::write(dir.path().join("data.mdb"), b"tampered").unwrap();

        let report = verify_store(dir.path()).unwrap();
        assert!(!report.is_ok());
        assert_eq!(report.mismatched, vec!["data.mdb".to_string()]);
    }

    #[test]
    fn verify_detects_missing_file() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"original").unwrap();
        std::fs::write(dir.path().join("meta.json"), b"{}").unwrap();

        seal_store(dir.path()).unwrap();

        std::fs::remove_file(dir.path().join("meta.json")).unwrap();

        let report = verify_store(dir.path()).unwrap();
        assert!(!report.is_ok());
        assert_eq!(report.missing, vec!["meta.json".to_string()]);
    }

    #[test]
    fn verify_detects_extra_file() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"original").unwrap();

        seal_store(dir.path()).unwrap();

        std::fs::write(dir.path().join("sneaky.mdb"), b"injected").unwrap();

        let report = verify_store(dir.path()).unwrap();
        assert!(!report.is_ok());
        assert_eq!(report.extra, vec!["sneaky.mdb".to_string()]);
    }

    #[test]
    fn seal_excludes_key_and_manifest() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"hello").unwrap();

        let manifest = seal_store(dir.path()).unwrap();
        assert!(!manifest.files.contains_key(SEAL_KEY_FILE));
        assert!(!manifest.files.contains_key(SEAL_MANIFEST_FILE));
    }

    #[test]
    fn seal_is_deterministic_for_same_key() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"hello").unwrap();

        let manifest1 = seal_store(dir.path()).unwrap();
        let manifest2 = seal_store(dir.path()).unwrap();

        // Same key → same digests
        for (rel, entry1) in &manifest1.files {
            let entry2 = manifest2.files.get(rel).unwrap();
            assert_eq!(entry1.digest, entry2.digest);
        }
    }

    #[test]
    fn verify_fails_without_seal() {
        let dir = tempdir().unwrap();
        std::fs::write(dir.path().join("data.mdb"), b"hello").unwrap();

        let err = verify_store(dir.path()).unwrap_err();
        assert!(err.to_string().contains("No seal key"));
    }
}
