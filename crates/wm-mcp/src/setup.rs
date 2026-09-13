//! `wm setup <client>` — safe MCP client configuration.
//!
//! Detects known clients, shows the exact change it would make, and (for
//! standard JSON configs) makes a timestamped backup before patching. JSONC
//! and TOML configs are print-only in v1: the snippet is exact, but the tool
//! never edits a format it cannot parse back — a half-written config is
//! worse than a copy-paste.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::path::PathBuf;

/// How a client's config can be treated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Kind {
    /// JSON file with a `mcpServers` object (Claude, Cursor, Windsurf).
    McpServersJson,
    /// OpenCode `opencode.jsonc` (`mcp` object, `command` is an array).
    OpencodeJsonc,
    /// Codex `config.toml` (`[mcp_servers.<name>]`).
    CodexToml,
}

/// A supported client.
#[derive(Debug, Clone)]
pub struct ClientSpec {
    pub id: &'static str,
    pub label: &'static str,
    pub config_path: PathBuf,
    pub kind: Kind,
}

fn home() -> PathBuf {
    std::env::var_os("HOME").map_or_else(|| PathBuf::from("."), PathBuf::from)
}

fn xdg_config() -> PathBuf {
    std::env::var_os("XDG_CONFIG_HOME").map_or_else(|| home().join(".config"), PathBuf::from)
}

/// All supported clients and their conventional config paths.
#[must_use]
pub fn specs() -> Vec<ClientSpec> {
    vec![
        ClientSpec {
            id: "opencode",
            label: "OpenCode",
            config_path: xdg_config().join("opencode/opencode.jsonc"),
            kind: Kind::OpencodeJsonc,
        },
        ClientSpec {
            id: "claude",
            label: "Claude Desktop",
            config_path: xdg_config().join("Claude/claude_desktop_config.json"),
            kind: Kind::McpServersJson,
        },
        ClientSpec {
            id: "cursor",
            label: "Cursor",
            config_path: home().join(".cursor/mcp.json"),
            kind: Kind::McpServersJson,
        },
        ClientSpec {
            id: "windsurf",
            label: "Windsurf",
            config_path: home().join(".codeium/windsurf/mcp_config.json"),
            kind: Kind::McpServersJson,
        },
        ClientSpec {
            id: "codex",
            label: "Codex CLI",
            config_path: home().join(".codex/config.toml"),
            kind: Kind::CodexToml,
        },
    ]
}

/// Look up a client by id (case-insensitive).
#[must_use]
pub fn find(id: &str) -> Option<ClientSpec> {
    specs()
        .into_iter()
        .find(|s| s.id.eq_ignore_ascii_case(id.trim()))
}

/// The standard `mcpServers` entry for this binary.
#[must_use]
pub fn entry(exe: &std::path::Path) -> Value {
    json!({
        "command": exe.display().to_string(),
        "args": ["serve", "--profile", "curated"]
    })
}

/// The exact snippet a user would add for this client.
#[must_use]
pub fn proposal(spec: &ClientSpec, exe: &std::path::Path) -> String {
    let exe_display = exe.display().to_string();
    match spec.kind {
        Kind::McpServersJson => json!({
            "mcpServers": { "whitemagic": entry(exe) }
        })
        .to_string(),
        Kind::OpencodeJsonc => json!({
            "mcp": {
                "whitemagic": {
                    "type": "local",
                    "command": [exe_display, "serve", "--profile", "curated"],
                    "enabled": true
                }
            }
        })
        .to_string(),
        Kind::CodexToml => format!(
            "[mcp_servers.whitemagic]\ncommand = \"{exe_display}\"\nargs = [\"serve\", \"--profile\", \"curated\"]"
        ),
    }
}

/// Patch a standard `mcpServers` JSON config. Returns a status message and
/// the backup path when one was made.
///
/// # Errors
/// Any IO or parse failure (the file is never modified on error).
pub fn write_mcp_servers_json(
    spec: &ClientSpec,
    exe: &std::path::Path,
) -> anyhow::Result<(String, Option<PathBuf>)> {
    if spec.kind != Kind::McpServersJson {
        anyhow::bail!(
            "{} uses {} — print-only in v1; the snippet above is exact",
            spec.label,
            match spec.kind {
                Kind::OpencodeJsonc => "JSONC (comments)",
                Kind::CodexToml => "TOML",
                Kind::McpServersJson => unreachable!(),
            }
        );
    }

    let mut config: Value = if spec.config_path.exists() {
        let text = std::fs::read_to_string(&spec.config_path)?;
        serde_json::from_str(&text).map_err(|e| {
            anyhow::anyhow!(
                "existing config is not valid JSON ({}): {e}",
                spec.config_path.display()
            )
        })?
    } else {
        json!({})
    };

    let obj = config
        .as_object_mut()
        .ok_or_else(|| anyhow::anyhow!("config root is not an object"))?;
    let servers = obj
        .entry("mcpServers")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| anyhow::anyhow!("mcpServers is not an object"))?;

    let desired = entry(exe);
    if servers.get("whitemagic") == Some(&desired) {
        return Ok(("already configured".to_string(), None));
    }
    servers.insert("whitemagic".to_string(), desired);

    let backup = if spec.config_path.exists() {
        let ts = chrono::Utc::now().format("%Y%m%d%H%M%S");
        let bak = PathBuf::from(format!("{}.bak-{ts}", spec.config_path.display()));
        std::fs::copy(&spec.config_path, &bak)?;
        Some(bak)
    } else {
        if let Some(parent) = spec.config_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        None
    };

    let rendered = serde_json::to_string_pretty(&config)?;
    std::fs::write(&spec.config_path, format!("{rendered}\n"))?;
    // Read it back: a config we cannot re-parse is not a config we ship.
    let verify = std::fs::read_to_string(&spec.config_path)?;
    serde_json::from_str::<Value>(&verify)
        .map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;

    Ok((format!("updated {}", spec.config_path.display()), backup))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proposal_shapes_are_parseable() {
        let exe = std::path::Path::new("/opt/wm");
        let specs = specs();
        let claude = specs.iter().find(|s| s.id == "claude").unwrap();
        let p: Value = serde_json::from_str(&proposal(claude, exe)).unwrap();
        assert_eq!(p["mcpServers"]["whitemagic"]["command"], "/opt/wm");
        assert_eq!(p["mcpServers"]["whitemagic"]["args"][1], "--profile");

        let opencode = specs.iter().find(|s| s.id == "opencode").unwrap();
        let p: Value = serde_json::from_str(&proposal(opencode, exe)).unwrap();
        assert_eq!(p["mcp"]["whitemagic"]["type"], "local");
        assert_eq!(p["mcp"]["whitemagic"]["command"][0], "/opt/wm");

        let codex = specs.iter().find(|s| s.id == "codex").unwrap();
        let snippet = proposal(codex, exe);
        assert!(snippet.contains("[mcp_servers.whitemagic]"));
    }

    #[test]
    fn json_merge_is_idempotent_and_backs_up() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("mcp.json");
        std::fs::write(&path, r#"{"mcpServers":{"other":{"command":"x"}}}"#).unwrap();
        let spec = ClientSpec {
            id: "cursor",
            label: "Cursor",
            config_path: path.clone(),
            kind: Kind::McpServersJson,
        };
        let exe = std::path::Path::new("/opt/wm");

        let (msg, backup) = write_mcp_servers_json(&spec, exe).unwrap();
        assert!(msg.contains("updated"));
        assert!(backup.unwrap().exists());
        let v: Value = serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(v["mcpServers"]["whitemagic"]["command"], "/opt/wm");
        assert_eq!(v["mcpServers"]["other"]["command"], "x");

        let (msg2, backup2) = write_mcp_servers_json(&spec, exe).unwrap();
        assert!(msg2.contains("already configured"));
        assert!(backup2.is_none());
    }

    #[test]
    fn print_only_kinds_refuse_write() {
        let tmp = tempfile::tempdir().unwrap();
        let spec = ClientSpec {
            id: "codex",
            label: "Codex CLI",
            config_path: tmp.path().join("config.toml"),
            kind: Kind::CodexToml,
        };
        assert!(write_mcp_servers_json(&spec, std::path::Path::new("/opt/wm")).is_err());
    }
}
