//! Build and executable identity reported by the `wm build-info` command.

use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{self, Read};
#[cfg(target_os = "linux")]
use std::path::Path;

#[derive(Debug, Serialize)]
pub struct BuildIdentity {
    pub package_version: &'static str,
    pub target: &'static str,
    pub revision: &'static str,
    pub commit_tree: &'static str,
    pub worktree: &'static str,
    pub executable_sha256: Option<String>,
    pub executable_sha256_error: Option<String>,
    pub identity_scope: &'static str,
}

impl BuildIdentity {
    pub fn current() -> Self {
        match executable_sha256() {
            Ok(hash) => Self {
                package_version: env!("CARGO_PKG_VERSION"),
                target: option_env!("WHITEMAGIC_BUILD_TARGET").unwrap_or("unknown"),
                revision: option_env!("WHITEMAGIC_BUILD_REVISION").unwrap_or("unknown"),
                commit_tree: option_env!("WHITEMAGIC_BUILD_TREE").unwrap_or("unknown"),
                worktree: option_env!("WHITEMAGIC_BUILD_WORKTREE").unwrap_or("unknown"),
                executable_sha256: Some(hash),
                executable_sha256_error: None,
                identity_scope: IDENTITY_SCOPE,
            },
            Err(error) => Self {
                package_version: env!("CARGO_PKG_VERSION"),
                target: option_env!("WHITEMAGIC_BUILD_TARGET").unwrap_or("unknown"),
                revision: option_env!("WHITEMAGIC_BUILD_REVISION").unwrap_or("unknown"),
                commit_tree: option_env!("WHITEMAGIC_BUILD_TREE").unwrap_or("unknown"),
                worktree: option_env!("WHITEMAGIC_BUILD_WORKTREE").unwrap_or("unknown"),
                executable_sha256: None,
                executable_sha256_error: Some(error.to_string()),
                identity_scope: IDENTITY_SCOPE,
            },
        }
    }
}

const IDENTITY_SCOPE: &str = "Executable SHA-256 identifies the bytes read from this executable (Linux uses /proc/self/exe; other platforms use current_exe). Git revision/tree and worktree state are compile-context metadata, not proof that these source bytes produced this executable. Worktree state covers tracked and non-ignored untracked files under crates/, vendor/, and workspace build manifests/configuration/ignore rules.";

/// Hash the running executable without opening the store or consulting the
/// network. Linux uses procfs so atomic replacement of the on-disk path does
/// not redirect the hash to a different executable.
pub fn executable_sha256() -> io::Result<String> {
    #[cfg(target_os = "linux")]
    let path = Path::new("/proc/self/exe");
    #[cfg(not(target_os = "linux"))]
    let path = std::env::current_exe()?;

    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    let digest = hasher.finalize();
    let mut encoded = String::with_capacity(digest.len() * 2);
    for &byte in digest.iter() {
        use std::fmt::Write as _;
        write!(&mut encoded, "{byte:02x}").expect("writing into String cannot fail");
    }
    Ok(encoded)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn executable_sha256_is_a_sha256_hex_digest() {
        let digest = executable_sha256().expect("test executable should be readable");
        assert_eq!(digest.len(), 64);
        assert!(digest.bytes().all(|byte| byte.is_ascii_hexdigit()));
    }

    #[test]
    fn unavailable_compile_provenance_is_rendered_as_unknown() {
        assert!(
            !option_env!("WHITEMAGIC_BUILD_REVISION")
                .unwrap_or("unknown")
                .is_empty()
        );
        assert!(
            !option_env!("WHITEMAGIC_BUILD_TREE")
                .unwrap_or("unknown")
                .is_empty()
        );
        assert!(matches!(
            option_env!("WHITEMAGIC_BUILD_WORKTREE").unwrap_or("unknown"),
            "clean" | "dirty" | "unknown"
        ));
    }
}
