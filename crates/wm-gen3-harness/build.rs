#[path = "src/build_metadata.rs"]
mod build_metadata;

use std::env;
use std::path::PathBuf;

fn main() {
    let manifest_dir = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").expect("manifest dir"));
    let workspace = manifest_dir
        .join("../..")
        .canonicalize()
        .unwrap_or_else(|_| manifest_dir.join("../.."));
    let metadata = build_metadata::collect(&workspace);

    for path in &metadata.watch_paths {
        println!("cargo:rerun-if-changed={}", path.display());
    }
    println!(
        "cargo:rustc-env=WHITEMAGIC_BUILD_REVISION={}",
        metadata.revision
    );
    println!(
        "cargo:rustc-env=WHITEMAGIC_BUILD_TREE={}",
        metadata.commit_tree
    );
    println!(
        "cargo:rustc-env=WHITEMAGIC_BUILD_WORKTREE={}",
        metadata.worktree
    );
    println!(
        "cargo:rustc-env=WHITEMAGIC_BUILD_TARGET={}",
        env::var("TARGET").unwrap_or_else(|_| "unknown".to_string())
    );
}
