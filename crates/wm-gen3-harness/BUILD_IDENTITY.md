# `wm build-info`

`wm build-info` reports the package version, compilation target, full Git
revision, committed tree ID, checkout state and SHA-256 digest of the running
executable. Use `wm build-info --json` for machine-readable output.

The build script probes Git locally when Cargo detects a change in workspace
source inputs or the relevant Git HEAD/ref/index metadata. This adds a small
number of local Git subprocesses to an invalidated harness build; unchanged
compiler inputs keep Cargo's normal build cache. Runtime `wm build-info` reads
only compile-time metadata and the executable itself. It does not open the
store, access the network or write files.

Checkout state covers tracked and non-ignored untracked files under `crates/`,
`vendor/`, the workspace Cargo manifests/lockfile, `.cargo/`, toolchain file,
Git attributes/ignore rules and Git submodule manifest. `unknown` is reported
when Git or a complete status probe is unavailable, or ignored inputs/index
flags hide checkout changes from an ordinary status check. Git revision and
tree are compile-context labels; they
do not prove that the executable was built from those exact source bytes. The
executable digest identifies the bytes read at command time. Linux reads
`/proc/self/exe`; other platforms hash the path returned by
`std::env::current_exe`.
