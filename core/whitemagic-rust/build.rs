use std::env;
use std::path::PathBuf;
use std::process::Command;

fn maybe_link_python() {
    // Only needed when Python bindings are enabled.
    if env::var("CARGO_FEATURE_PYTHON").is_err() {
        return;
    }

    // Only link libpython when explicitly requested for local test binaries.
    // Maturin extension-module wheels must not link libpython.
    if env::var("WHITEMAGIC_LINK_LIBPYTHON").ok().as_deref() != Some("1") {
        return;
    }

    // Query Python's build config for libdir + ldlibrary.
    let output = Command::new("python3")
        .arg("-c")
        .arg(
            "import sysconfig; \
print(sysconfig.get_config_var('LIBDIR') or ''); \
print(sysconfig.get_config_var('LDLIBRARY') or '')",
        )
        .output();

    let Ok(output) = output else {
        println!("cargo:warning=Could not execute python3 to resolve libpython link flags");
        return;
    };
    if !output.status.success() {
        println!("cargo:warning=python3 config query failed while resolving libpython");
        return;
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut lines = stdout.lines();
    let libdir = lines.next().unwrap_or("").trim();
    let ldlib = lines.next().unwrap_or("").trim();

    if !libdir.is_empty() {
        println!("cargo:rustc-link-search=native={}", libdir);
    }

    // Convert "libpython3.12.so" -> "python3.12" for rustc-link-lib.
    if let Some(name) = ldlib.strip_prefix("lib") {
        let short = name
            .trim_end_matches(".so")
            .trim_end_matches(".a")
            .trim_end_matches(".dylib");
        if !short.is_empty() {
            println!("cargo:rustc-link-lib=dylib={short}");
            return;
        }
    }

    // Safe fallback for Linux dev environments.
    println!("cargo:rustc-link-lib=dylib=python3.12");
}

fn main() {
    let target = env::var("TARGET").unwrap_or_default();

    // Skip Zig linking for WASM targets — wasm-lld doesn't support these flags
    if target.contains("wasm32") {
        println!("cargo:rerun-if-changed=build.rs");
        return;
    }

    let project_root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());

    // Path to the Zig static library
    // In v5.1, we expect whitemagic-zig to be a sibling of the whitemagic repo
    // or at a specific relative path.
    // Correct path: project_root is "whitemagic-rust"
    // We want sibling "whitemagic-zig" in the parent "whitemagic" folder
    let zig_lib_dir = project_root
        .parent()
        .unwrap()
        .join("whitemagic-zig")
        .join("zig-out")
        .join("lib");

    // Fallback: Check if the library is in the root of whitemagic-zig (common in dev/pixi builds)
    let zig_lib_root = project_root.parent().unwrap().join("whitemagic-zig");

    let final_zig_dir = if zig_lib_dir.exists() {
        Some(zig_lib_dir.clone())
    } else if zig_lib_root.join("libwhitemagic.so").exists() {
        Some(zig_lib_root.clone())
    } else {
        None
    };

    // Link Zig static library for query router
    if let Some(ref zig_dir) = final_zig_dir {
        println!("cargo:rustc-link-search=native={}", zig_dir.display());
        println!("cargo:rustc-link-lib=static=whitemagic-zig");
        println!(
            "cargo:rerun-if-changed={}",
            zig_dir.join("libwhitemagic-zig.a").display()
        );

        // Link libc (required by Zig)
        println!("cargo:rustc-link-lib=dylib=c");
    } else {
        println!("cargo:warning=Zig static library not found at {}. Proceeding without Zig acceleration.", zig_lib_dir.display());
    }

    // Rerun if build script changes
    println!("cargo:rerun-if-changed=build.rs");

    // Link libpython only when explicitly opted in.
    maybe_link_python();
}
