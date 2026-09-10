//! Build provenance, generated without reading credentials or arbitrary environment values.
use sha2::{Digest, Sha256};
use std::{env, fs, path::PathBuf, process::Command};
fn main() {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let git = |args: &[&str]| {
        Command::new("git")
            .args(args)
            .current_dir(&root)
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
    };
    for p in ["crates", "Cargo.toml", "Cargo.lock", ".cargo"] {
        println!("cargo:rerun-if-changed={}", root.join(p).display());
    }
    for p in ["HEAD", "index"] {
        if let Some(path) = git(&["rev-parse", "--git-path", p]) {
            println!("cargo:rerun-if-changed={}", root.join(path).display());
        }
    }
    if let Some(reference) = git(&["symbolic-ref", "-q", "HEAD"]) {
        if let Some(path) = git(&["rev-parse", "--git-path", &reference]) {
            println!("cargo:rerun-if-changed={}", root.join(path).display());
        }
    }
    let paths = git(&[
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "crates",
        "Cargo.toml",
        "Cargo.lock",
        ".cargo",
    ]);
    let source_hash = paths.map(|paths| {
        let mut paths: Vec<_> = paths.lines().collect();
        paths.sort_unstable();
        paths.dedup();
        let mut hash = Sha256::new();
        for path in paths {
            if let Ok(bytes) = fs::read(root.join(path)) {
                hash.update(path.as_bytes());
                hash.update([0]);
                hash.update((bytes.len() as u64).to_le_bytes());
                hash.update(bytes);
            }
        }
        format!("{:x}", hash.finalize())
    });
    let mut features: Vec<_> = env::vars()
        .filter_map(|(k, _)| k.strip_prefix("CARGO_FEATURE_").map(str::to_string))
        .collect();
    features.sort();
    let rustc = Command::new(env::var("RUSTC").unwrap_or_else(|_| "rustc".into()))
        .arg("--version")
        .output()
        .ok()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string());
    let value = serde_json::json!({
        "schema": "wm-build-provenance-v1", "package_version": env::var("CARGO_PKG_VERSION").ok(),
        "git_commit": git(&["rev-parse", "HEAD"]),
        "dirty_build_inputs": git(&["status", "--porcelain", "--untracked-files=all", "--", "crates", "Cargo.toml", "Cargo.lock", ".cargo"]).map(|s| !s.is_empty()),
        "source_sha256": source_hash, "source_hash_scope": "sorted repository crates + Cargo.toml + Cargo.lock + .cargo; path NUL length-le64 bytes",
        "cargo_lock_sha256": fs::read(root.join("Cargo.lock")).ok().map(|b| format!("{:x}", Sha256::digest(b))),
        "package_features": features, "features_scope": "wm-mcp Cargo package features, not a transitive-feature inventory",
        "target": env::var("TARGET").ok(), "profile": env::var("PROFILE").ok(), "rustc": rustc,
    });
    fs::write(
        PathBuf::from(env::var("OUT_DIR").unwrap()).join("build-provenance.json"),
        serde_json::to_vec_pretty(&value).unwrap(),
    )
    .unwrap();
}
