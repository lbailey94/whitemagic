//! Git checkout metadata embedded by the harness build script.
//!
//! The status describes tracked and non-ignored untracked files within the
//! workspace's compiler-input paths. It is a checkout observation, not proof
//! that a particular executable was built from those source bytes.

use std::path::{Path, PathBuf};
use std::process::Command;

const BUILD_INPUT_PATHS: &[&str] = &[
    "crates",
    "vendor",
    "Cargo.toml",
    "Cargo.lock",
    "build.rs",
    "rust-toolchain.toml",
    ".cargo",
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildMetadata {
    pub revision: String,
    pub commit_tree: String,
    pub worktree: &'static str,
    pub watch_paths: Vec<PathBuf>,
}

impl BuildMetadata {
    fn unknown(watch_paths: Vec<PathBuf>) -> Self {
        Self {
            revision: "unknown".to_string(),
            commit_tree: "unknown".to_string(),
            worktree: "unknown",
            watch_paths,
        }
    }
}

/// Collect a full commit, its committed tree, and checkout state for the
/// harness workspace. Git failures yield explicit unknown values.
pub fn collect(workspace: &Path) -> BuildMetadata {
    let watch_paths = git_watch_paths(workspace);
    let Some(revision) = git_output(workspace, &["rev-parse", "--verify", "HEAD"]) else {
        return BuildMetadata::unknown(watch_paths);
    };
    let Some(commit_tree) = git_output(workspace, &["rev-parse", "--verify", "HEAD^{tree}"]) else {
        return BuildMetadata::unknown(watch_paths);
    };
    let Some(status) = git_status(workspace, false) else {
        return BuildMetadata::unknown(watch_paths);
    };
    let Some(ignored_status) = git_status(workspace, true) else {
        return BuildMetadata::unknown(watch_paths);
    };
    let Some(index_flags) = git_index_flags(workspace) else {
        return BuildMetadata::unknown(watch_paths);
    };
    let ignored_inputs = ignored_status
        .split(|byte| *byte == 0)
        .filter(|record| record.len() >= 2)
        .any(|record| &record[..2] == b"!!");
    let hidden_index_state = index_flags
        .split(|byte| *byte == 0)
        .filter(|record| !record.is_empty())
        .any(|record| record[0] == b'S' || record[0].is_ascii_lowercase());
    let worktree = if !status.is_empty() {
        "dirty"
    } else if ignored_inputs || hidden_index_state {
        "unknown"
    } else {
        "clean"
    };

    BuildMetadata {
        revision,
        commit_tree,
        worktree,
        watch_paths,
    }
}

/// Inputs Cargo should watch so branch movement and workspace code changes
/// refresh the compile-time identity on the next build.
pub fn git_watch_paths(workspace: &Path) -> Vec<PathBuf> {
    let mut paths = BUILD_INPUT_PATHS
        .iter()
        .map(|input| workspace.join(input))
        .collect::<Vec<_>>();
    let dot_git = workspace.join(".git");
    if !dot_git.is_dir() {
        paths.push(dot_git);
    }

    let git_dir = git_output(workspace, &["rev-parse", "--absolute-git-dir"]).map(PathBuf::from);
    let common_dir = git_output(workspace, &["rev-parse", "--git-common-dir"])
        .map(|path| resolve_path(workspace, Path::new(&path)));
    if let Some(git_dir) = &git_dir {
        paths.push(git_dir.join("HEAD"));
        paths.push(git_dir.join("index"));
        paths.push(git_dir.join("config"));
    }
    if let Some(common_dir) = &common_dir {
        paths.push(common_dir.join("packed-refs"));
        paths.push(common_dir.join("refs"));
        paths.push(common_dir.join("config"));
        paths.push(common_dir.join("info/exclude"));
    }
    if let Some(excludes) = git_output(
        workspace,
        &["config", "--path", "--get", "core.excludesfile"],
    ) {
        let exclude_path = PathBuf::from(excludes);
        let exclude_path = if exclude_path.is_absolute() {
            exclude_path
        } else if let Some(home) = std::env::var_os("HOME") {
            PathBuf::from(home).join(exclude_path)
        } else {
            workspace.join(exclude_path)
        };
        paths.push(exclude_path);
    }
    if let (Some(common_dir), Some(reference)) = (
        common_dir,
        git_output(workspace, &["symbolic-ref", "-q", "HEAD"]),
    ) {
        paths.push(common_dir.join(reference));
    }

    paths.sort();
    paths.dedup();
    paths
}

fn git_output(workspace: &Path, args: &[&str]) -> Option<String> {
    let output = git_output_bytes(workspace, args)?;
    String::from_utf8(output).ok().map(|s| s.trim().to_string())
}

fn git_output_bytes(workspace: &Path, args: &[&str]) -> Option<Vec<u8>> {
    let output = Command::new("git")
        .arg("-C")
        .arg(workspace)
        .args(args)
        .output()
        .ok()?;
    output.status.success().then_some(output.stdout)
}

fn git_status(workspace: &Path, include_ignored: bool) -> Option<Vec<u8>> {
    let mut args = vec!["status", "--porcelain=v1", "-z", "--untracked-files=all"];
    if include_ignored {
        args.push("--ignored=matching");
    }
    args.push("--");
    args.extend_from_slice(BUILD_INPUT_PATHS);
    git_output_bytes(workspace, &args)
}

fn git_index_flags(workspace: &Path) -> Option<Vec<u8>> {
    let mut args = vec!["ls-files", "-v", "-z", "--"];
    args.extend_from_slice(BUILD_INPUT_PATHS);
    git_output_bytes(workspace, &args)
}

fn resolve_path(base: &Path, path: &Path) -> PathBuf {
    if path.is_absolute() {
        path.to_path_buf()
    } else {
        base.join(path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TempRepo(PathBuf);

    impl TempRepo {
        fn new(name: &str) -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("clock after epoch")
                .as_nanos();
            let path = std::env::temp_dir().join(format!("wm-build-metadata-{name}-{nonce}"));
            fs::create_dir_all(&path).expect("create temporary repo root");
            Self(path)
        }

        fn git(&self, args: &[&str]) -> String {
            let output = Command::new("git")
                .arg("-C")
                .arg(&self.0)
                .args(args)
                .output()
                .expect("run git test fixture");
            assert!(
                output.status.success(),
                "git {args:?} failed: {}",
                String::from_utf8_lossy(&output.stderr)
            );
            String::from_utf8(output.stdout)
                .expect("git output UTF-8")
                .trim()
                .to_string()
        }
    }

    impl Drop for TempRepo {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn source_archive_without_git_metadata_is_explicitly_unknown() {
        let source = TempRepo::new("archive");
        let metadata = collect(&source.0);
        assert_eq!(metadata.revision, "unknown");
        assert_eq!(metadata.commit_tree, "unknown");
        assert_eq!(metadata.worktree, "unknown");
    }

    #[test]
    fn dirty_and_untracked_inputs_are_reported() {
        let repo = TempRepo::new("dirty");
        repo.git(&["init", "--initial-branch=main"]);
        repo.git(&["config", "user.email", "test@example.invalid"]);
        repo.git(&["config", "user.name", "Build Metadata Test"]);
        fs::create_dir_all(repo.0.join("crates/input/src")).expect("create input tree");
        fs::write(
            repo.0.join("crates/input/src/lib.rs"),
            "pub fn value() {}\n",
        )
        .expect("write source fixture");
        repo.git(&["add", "crates/input/src/lib.rs"]);
        repo.git(&["commit", "-m", "fixture"]);
        assert_eq!(collect(&repo.0).worktree, "clean");

        fs::write(
            repo.0.join("crates/input/src/lib.rs"),
            "pub fn value() { }\n",
        )
        .expect("modify tracked input");
        assert_eq!(collect(&repo.0).worktree, "dirty");

        repo.git(&["checkout", "--", "crates/input/src/lib.rs"]);
        fs::write(
            repo.0.join("crates/input/src/new.rs"),
            "pub fn new_input() {}\n",
        )
        .expect("add untracked source fixture");
        assert_eq!(collect(&repo.0).worktree, "dirty");
    }

    #[test]
    fn ignored_or_index_hidden_inputs_are_never_reported_clean() {
        let repo = TempRepo::new("hidden-input");
        repo.git(&["init", "--initial-branch=main"]);
        repo.git(&["config", "user.email", "test@example.invalid"]);
        repo.git(&["config", "user.name", "Build Metadata Test"]);
        fs::create_dir_all(repo.0.join("crates/input/src")).expect("create input tree");
        fs::write(repo.0.join(".gitignore"), "crates/input/src/hidden.rs\n")
            .expect("write ignore rule");
        fs::write(
            repo.0.join("crates/input/src/lib.rs"),
            "pub fn value() {}\n",
        )
        .expect("write source fixture");
        repo.git(&["add", ".gitignore", "crates/input/src/lib.rs"]);
        repo.git(&["commit", "-m", "fixture"]);

        fs::write(
            repo.0.join("crates/input/src/hidden.rs"),
            "pub fn hidden() {}\n",
        )
        .expect("write ignored compiler input");
        assert_eq!(collect(&repo.0).worktree, "unknown");
        fs::remove_file(repo.0.join("crates/input/src/hidden.rs")).expect("remove ignored input");

        repo.git(&["update-index", "--skip-worktree", "crates/input/src/lib.rs"]);
        assert_eq!(collect(&repo.0).worktree, "unknown");
        repo.git(&[
            "update-index",
            "--no-skip-worktree",
            "crates/input/src/lib.rs",
        ]);

        repo.git(&[
            "update-index",
            "--assume-unchanged",
            "crates/input/src/lib.rs",
        ]);
        fs::write(
            repo.0.join("crates/input/src/lib.rs"),
            "pub fn hidden_change() {}\n",
        )
        .expect("modify assume-unchanged input");
        assert_eq!(collect(&repo.0).worktree, "unknown");
        repo.git(&[
            "update-index",
            "--no-assume-unchanged",
            "crates/input/src/lib.rs",
        ]);
    }

    #[test]
    fn branch_and_linked_worktree_heads_are_watched() {
        let repo = TempRepo::new("worktree");
        repo.git(&["init", "--initial-branch=main"]);
        repo.git(&["config", "user.email", "test@example.invalid"]);
        repo.git(&["config", "user.name", "Build Metadata Test"]);
        fs::create_dir_all(repo.0.join("crates/input")).expect("create input tree");
        fs::write(repo.0.join("crates/input/source.rs"), "one\n").expect("write source");
        repo.git(&["add", "crates/input/source.rs"]);
        repo.git(&["commit", "-m", "first"]);
        let first_head = collect(&repo.0).revision;

        repo.git(&["checkout", "-b", "alternate"]);
        fs::write(repo.0.join("crates/input/source.rs"), "two\n").expect("modify source");
        repo.git(&["commit", "-am", "second"]);
        let alternate = collect(&repo.0);
        assert_ne!(alternate.revision, first_head);
        assert!(
            alternate
                .watch_paths
                .iter()
                .any(|path| path.ends_with("HEAD"))
        );
        assert!(
            alternate
                .watch_paths
                .iter()
                .any(|path| path.ends_with("refs/heads/alternate"))
        );

        let linked = repo.0.with_file_name(format!(
            "{}-linked",
            repo.0.file_name().unwrap().to_string_lossy()
        ));
        repo.git(&[
            "worktree",
            "add",
            "--detach",
            linked.to_str().unwrap(),
            "HEAD",
        ]);
        let linked_metadata = collect(&linked);
        assert_eq!(linked_metadata.revision, alternate.revision);
        assert!(
            linked_metadata
                .watch_paths
                .iter()
                .any(|path| path.ends_with("HEAD"))
        );
        let _ = fs::remove_dir_all(&linked);
        repo.git(&["worktree", "prune"]);
    }
}
