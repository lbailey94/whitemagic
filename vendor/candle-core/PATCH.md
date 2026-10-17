# Local maintenance patch for `candle-core 0.9.2`

This directory contains the crates.io package source for `candle-core 0.9.2`. The only source manifest change is to its exact `zip` dependency, from `7.2.0` to `9.0.4`. The ZIP 9 API adaptations are limited to `src/npy.rs` and `src/pickle.rs`: the old explicit `FileOptions<()>` type is replaced with ZIP 9's `SimpleFileOptions` alias, and `ZipFile::name()`/`ZipArchive::file_names()` results are propagated as `ZipResult` errors before using the borrowed names. A focused NPZ write/read round-trip regression is added to `tests/serialization_tests.rs`. No other Candle Rust code or API is changed. The same version is used by the runtime's `candle-nn` and `candle-transformers` dependencies, preserving the Candle 0.9 API family.

## Provenance and license

- Package: <https://crates.io/crates/candle-core/0.9.2>
- Upstream repository: <https://github.com/huggingface/candle>
- Upstream source commit: `3b39794c14b1de8ba4c2d10d49354d557a415547` (`candle-core` subdirectory), from registry `.cargo_vcs_info.json`.
- Registry package archive: `candle-core-0.9.2.crate`
- SHA-256 of the cached archive used to seed this directory: `c15b675b80d994b2eadb20a4bbe434eabeb454eac3ee5e2b4cf6f147ee9be091` (matches the original Cargo.lock checksum).
- License: MIT OR Apache-2.0, retained from the package's license files and metadata.

The original exact ZIP 7.2.0 dependency is reachable through Laya's Candle 0.9.2 graph and is affected by RUSTSEC-2026-0367, -0368, and -0369. ZIP 9.0.4 is the patched release identified for this remediation.

## Compatibility and maintenance

The current Candle code uses ZIP archive read/write APIs for NPZ and pickle tensor loading. It does not call archive extraction APIs. The ZIP 9 API adaptations must still be compiled and tested against ZIP 9.0.4, including NPZ read/write and PyTorch pickle loading, before acceptance. If those APIs are incompatible, do not add source changes without a separately reviewed scope. Track upstream Candle's dependency update and remove this local patch once a compatible upstream Candle 0.9 release exists. Keep any local delta manifest-only and review upstream changes before refreshing the vendor copy.
