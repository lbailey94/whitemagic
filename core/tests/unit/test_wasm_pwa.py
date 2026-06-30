"""Tests for WASM module structure and PWA shell assets.

These tests verify that the WASM Rust source defines the expected
types and methods, and that the PWA shell files exist with correct
structure. They don't require a WASM build — they check the Rust
source and static files.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
WASM_RS = REPO_ROOT / "core" / "whitemagic-rust" / "src" / "wasm.rs"
SDK_LOCAL = REPO_ROOT / "sdk" / "typescript" / "src" / "local_transport.ts"
PWA_MANIFEST = REPO_ROOT / "apps" / "site" / "public" / "manifest.json"
PWA_SW = REPO_ROOT / "apps" / "site" / "public" / "sw.js"
PWA_HTML = REPO_ROOT / "apps" / "site" / "public" / "app" / "index.html"


class TestWasmRsStructure:
    """Verify wasm.rs defines the expected WASM bindings."""

    def test_file_exists(self):
        assert WASM_RS.exists(), f"wasm.rs not found at {WASM_RS}"

    def test_version_is_23_2_0(self):
        content = WASM_RS.read_text()
        assert "23.2.0" in content, "wasm_version should return 23.2.0"

    def test_memory_store_defined(self):
        content = WASM_RS.read_text()
        assert "pub struct MemoryStore" in content
        assert "pub fn create" in content
        assert "pub fn read" in content
        assert "pub fn update" in content
        assert "pub fn delete" in content
        assert "pub fn search" in content
        assert "pub fn list" in content
        assert "pub fn count" in content
        assert "pub fn export_json" in content
        assert "pub fn import_json" in content

    def test_indexeddb_persistence_methods(self):
        content = WASM_RS.read_text()
        assert "pub async fn hydrate" in content
        assert "pub async fn persist" in content
        assert "pub async fn persist_one" in content
        assert "pub async fn delete_persisted" in content
        assert "fn idb_open_db" in content
        assert "fn idb_request_to_promise" in content
        assert "fn idb_transaction_to_promise" in content
        assert "web_sys::IdbDatabase" in content
        assert "Closure::wrap" in content
        assert "put_with_key" in content
        assert "wasm_bindgen_futures::JsFuture" in content

    def test_wasm_bindgen_futures_dep(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        assert "wasm-bindgen-futures" in cargo

    def test_dharma_engine_defined(self):
        content = WASM_RS.read_text()
        assert "pub struct DharmaEngine" in content
        assert "pub fn evaluate" in content
        assert "pub fn add_rule" in content
        assert "pub fn remove_rule" in content
        assert "pub fn list_rules" in content
        assert "pub fn rule_count" in content

    def test_karma_ledger_defined(self):
        content = WASM_RS.read_text()
        assert "pub struct KarmaLedger" in content
        assert "pub fn record" in content
        assert "pub fn balance" in content
        assert "pub fn count" in content
        assert "pub fn recent_json" in content
        assert "pub fn export_json" in content

    def test_gnosis_snapshot_defined(self):
        content = WASM_RS.read_text()
        assert "pub struct GnosisSnapshot" in content
        assert "pub fn gnosis_snapshot" in content
        assert "memory_count" in content
        assert "karma_balance" in content
        assert "maturity_stage" in content

    def test_edge_engine_has_updated_rules(self):
        content = WASM_RS.read_text()
        assert "23.2.0" in content
        assert "2,564" in content

    def test_wasm_memory_struct(self):
        content = WASM_RS.read_text()
        assert "pub struct WasmMemory" in content
        assert "pub fn new" in content
        assert "pub fn add_tag" in content
        assert "pub fn remove_tag" in content
        assert "pub fn to_json" in content

    def test_rust_tests_exist(self):
        content = WASM_RS.read_text()
        assert "fn test_memory_store_crud" in content
        assert "fn test_dharma_block_rule" in content
        assert "fn test_karma_ledger_record" in content
        assert "fn test_gnosis_snapshot" in content

    def test_init_wasm_panic_hook(self):
        content = WASM_RS.read_text()
        assert "init_wasm" in content
        assert "console_error_panic_hook::set_once" in content
        assert "#[wasm_bindgen(start)]" in content

    def test_get_stats_uses_serde_json(self):
        content = WASM_RS.read_text()
        # get_stats should use serde_json::json! not format!
        stats_section = content[
            content.index("pub fn get_stats") : content.index("pub fn get_stats") + 300
        ]
        assert "serde_json::json!" in stats_section
        assert "format!" not in stats_section


class TestCargoTomlWasmGating:
    """Verify Cargo.toml properly gates native-only deps from WASM builds."""

    def test_rayon_is_optional(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        assert "rayon = { version" in cargo
        assert 'rayon = "1.8"' not in cargo  # Should NOT be non-optional

    def test_memmap2_is_optional(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        assert "memmap2 = { version" in cargo

    def test_walkdir_is_optional(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        assert "walkdir = { version" in cargo

    def test_libc_is_optional(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        assert "libc = { version" in cargo

    def test_python_feature_includes_native_deps(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        # The python feature should list rayon, memmap2, walkdir, libc
        python_line = [
            line for line in cargo.splitlines() if line.startswith("python = ")
        ][0]
        assert "rayon" in python_line
        assert "memmap2" in python_line
        assert "walkdir" in python_line
        assert "libc" in python_line

    def test_wasm_feature_does_not_include_native_deps(self):
        cargo = (REPO_ROOT / "core" / "whitemagic-rust" / "Cargo.toml").read_text()
        wasm_line = [line for line in cargo.splitlines() if line.startswith("wasm = ")][
            0
        ]
        assert "rayon" not in wasm_line
        assert "memmap2" not in wasm_line
        assert "walkdir" not in wasm_line
        assert "libc" not in wasm_line

    def test_inference_module_gated(self):
        lib_rs = (REPO_ROOT / "core" / "whitemagic-rust" / "src" / "lib.rs").read_text()
        # inference module should be gated with #[cfg(not(feature = "wasm"))]
        assert '#[cfg(not(feature = "wasm"))]' in lib_rs
        assert "pub mod inference;" in lib_rs


class TestLocalTransport:
    """Verify the TypeScript LocalTransport structure."""

    def test_file_exists(self):
        assert SDK_LOCAL.exists(), f"local_transport.ts not found at {SDK_LOCAL}"

    def test_class_exported(self):
        content = SDK_LOCAL.read_text()
        assert "export class LocalTransport" in content

    def test_connect_method(self):
        content = SDK_LOCAL.read_text()
        assert "async connect" in content

    def test_call_tool_method(self):
        content = SDK_LOCAL.read_text()
        assert "async callTool" in content

    def test_disconnect_method(self):
        content = SDK_LOCAL.read_text()
        assert "disconnect" in content

    def test_handles_all_namespaces(self):
        content = SDK_LOCAL.read_text()
        for ns in [
            "memory",
            "dharma",
            "karma",
            "gnosis",
            "edge",
            "similarity",
            "search",
            "system",
        ]:
            assert f'"{ns}"' in content, f"LocalTransport should handle namespace: {ns}"


_PWA_AVAILABLE = PWA_MANIFEST.exists() and PWA_SW.exists() and PWA_HTML.exists()


@pytest.mark.skipif(not _PWA_AVAILABLE, reason="PWA shell files not in this repo")
class TestPWAShell:
    """Verify PWA shell files exist and have correct structure.

    PWA assets live in the public repo (apps/site/public/). These tests
    skip gracefully when running against the private repo where apps/
    is not present.
    """

    def test_manifest_exists(self):
        assert PWA_MANIFEST.exists(), f"manifest.json not found at {PWA_MANIFEST}"

    def test_manifest_valid_json(self):
        import json

        manifest = json.loads(PWA_MANIFEST.read_text())
        assert manifest["name"] == "WhiteMagic — Local Memory OS"
        assert manifest["display"] == "standalone"
        assert manifest["start_url"] == "/app"
        assert "icons" in manifest

    def test_service_worker_exists(self):
        assert PWA_SW.exists(), f"sw.js not found at {PWA_SW}"

    def test_service_worker_caches_wasm(self):
        content = PWA_SW.read_text()
        assert "whitemagic_rs" in content
        assert "WASM_CACHE" in content
        assert "install" in content
        assert "activate" in content
        assert "fetch" in content

    def test_pwa_html_exists(self):
        assert PWA_HTML.exists(), f"PWA index.html not found at {PWA_HTML}"

    def test_pwa_html_loads_wasm(self):
        content = PWA_HTML.read_text()
        assert "whitemagic_rs" in content
        assert "MemoryStore" in content
        assert "DharmaEngine" in content
        assert "KarmaLedger" in content
        assert "gnosis_snapshot" in content

    def test_pwa_html_registers_sw(self):
        content = PWA_HTML.read_text()
        assert "serviceWorker" in content
        assert "/sw.js" in content

    def test_pwa_html_has_privacy_indicator(self):
        content = PWA_HTML.read_text()
        assert "privacy-indicator" in content
        assert "0 bytes sent" in content

    def test_pwa_html_manifest_link(self):
        content = PWA_HTML.read_text()
        assert 'rel="manifest"' in content
        assert "/manifest.json" in content


class TestSdkIndexExport:
    """Verify LocalTransport is exported from SDK index."""

    def test_exported_from_index(self):
        index = (REPO_ROOT / "sdk" / "typescript" / "src" / "index.ts").read_text()
        assert "LocalTransport" in index
        assert "local_transport" in index
