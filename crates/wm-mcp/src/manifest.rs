//! Generated build and runtime surface disclosure. This is not a usefulness audit.
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{io::Read, sync::OnceLock};

#[must_use]
pub fn build_info() -> Value {
    static INFO: OnceLock<Value> = OnceLock::new();
    INFO.get_or_init(|| {
        let mut value: Value = serde_json::from_str(include_str!(concat!(env!("OUT_DIR"), "/build-provenance.json"))).expect("generated build JSON");
        // Linux procfs refers to this running inode even if its launch path is replaced.
        let executable = if cfg!(target_os = "linux") { Some(std::path::PathBuf::from("/proc/self/exe")) } else { std::env::current_exe().ok() };
        let digest = executable.and_then(|p| {
            let mut file = std::fs::File::open(p).ok()?;
            let mut h = Sha256::new(); let mut buf = [0; 8192];
            loop { let n = file.read(&mut buf).ok()?; if n == 0 { break; } h.update(&buf[..n]); }
            Some(format!("{:x}", h.finalize()))
        });
        value["executable_sha256"] = json!(digest);
        value["executable_hash_source"] = json!(if cfg!(target_os = "linux") { "/proc/self/exe" } else { "current_exe path; running-inode binding unavailable" });
        value["memory_wire_format"] = json!({"new_writes":"named MessagePack fields", "legacy_read_compatibility":"exact S11 30-field metadata fallback", "global_migration_version":null, "migration_version_status":"no global version ledger; per-format compatibility only"});
        value
    }).clone()
}

#[must_use]
pub fn registered_routes(registry: &wm_dispatch::ToolRegistry) -> Vec<Value> {
    let mut routes: Vec<_> = registry.all_ref().iter().map(|t| json!({
        "name":t.name(), "description":t.description(), "effects":t.effects(),
        "parameters":t.input_schema(),
        "canonical_route": if t.name() == "memory.hybrid_recall" { "memory.search" } else { t.name() },
        "alias_kind": if t.name() == "memory.hybrid_recall" { "shared implementation compatibility name" } else { "not declared as alias" },
    })).collect();
    routes.sort_by(|a, b| a["name"].as_str().cmp(&b["name"].as_str()));
    routes
}

/// Redact URL userinfo, query and fragment in configured backend disclosures.
/// Raw transport errors can echo credentials; expose only their presence here.
pub fn redact_federation(value: &mut Value) {
    if let Some(scopes) = value.get_mut("scopes").and_then(Value::as_array_mut) {
        for scope in scopes {
            if let Some(url) = scope.get("endpoint").and_then(Value::as_str) {
                let safe = url.split(['?', '#']).next().unwrap_or("");
                let safe = safe.split_once("://").map_or_else(
                    || "[invalid endpoint]".to_string(),
                    |(scheme, rest)| {
                        let rest = rest.rsplit_once('@').map_or(rest, |(_, host)| host);
                        format!("{scheme}://{rest}")
                    },
                );
                scope["endpoint"] = json!(safe);
            }
            if !scope["error"].is_null() {
                scope["error"] = json!("backend probe failed; details withheld");
            }
        }
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn backend_credentials_and_error_text_are_not_disclosed() {
        let mut value = serde_json::json!({"scopes":[{"endpoint":"https://user:secret@example.test/mcp?key=secret#secret","error":"secret"}]});
        super::redact_federation(&mut value);
        assert!(!value.to_string().contains("secret"));
        assert_eq!(value["scopes"][0]["endpoint"], "https://example.test/mcp");
    }
    #[test]
    fn build_identity_has_explicit_unknowns_and_scoped_features() {
        let b = super::build_info();
        assert_eq!(b["schema"], "wm-build-provenance-v1");
        assert!(b["package_features"].is_array());
        assert!(b["memory_wire_format"]["global_migration_version"].is_null());
        assert_eq!(b["executable_sha256"].as_str().unwrap().len(), 64);
    }
}
