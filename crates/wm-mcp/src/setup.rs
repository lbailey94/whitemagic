//! `wm setup <client>` — safe MCP client configuration.
//!
//! Detects known clients, shows the exact change it would make, and (for
//! every supported format) makes a timestamped backup before patching:
//!
//! - standard JSON (`mcpServers`) — parsed and re-rendered with serde_json;
//! - OpenCode JSONC — comments and formatting are preserved via a small
//!   structural editor (`upsert_member`) rather than a blind re-render;
//! - Codex TOML — edited through `toml_edit`, which preserves comments.
//!
//! Every write is read back and re-parsed before the call returns; a config
//! we cannot parse back is not a config we ship.

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::path::{Path, PathBuf};

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

const fn serve_args() -> [&'static str; 3] {
    ["serve", "--profile", "curated"]
}

/// The standard `mcpServers` entry for this binary.
#[must_use]
pub fn entry(exe: &Path) -> Value {
    json!({
        "command": exe.display().to_string(),
        "args": serve_args(),
    })
}

/// The OpenCode JSONC `mcp.<name>` entry (command is an array).
fn opencode_entry(exe: &Path) -> Value {
    json!({
        "type": "local",
        "command": [exe.display().to_string(), "serve", "--profile", "curated"],
        "enabled": true,
    })
}

/// The exact snippet a user would add for this client.
#[must_use]
pub fn proposal(spec: &ClientSpec, exe: &Path) -> String {
    let exe_display = exe.display().to_string();
    match spec.kind {
        Kind::McpServersJson => json!({
            "mcpServers": { "whitemagic": entry(exe) }
        })
        .to_string(),
        Kind::OpencodeJsonc => json!({
            "mcp": { "whitemagic": opencode_entry(exe) }
        })
        .to_string(),
        Kind::CodexToml => {
            let _ = exe_display;
            format!(
                "[mcp_servers.whitemagic]\ncommand = \"{}\"\nargs = [\"serve\", \"--profile\", \"curated\"]",
                exe.display()
            )
        }
    }
}

fn backup_path(path: &Path) -> PathBuf {
    let ts = chrono::Utc::now().format("%Y%m%d%H%M%S");
    PathBuf::from(format!("{}.bak-{ts}", path.display()))
}

fn ensure_parent(path: &Path) -> anyhow::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    Ok(())
}

/// Patch a standard `mcpServers` JSON config. Returns a status message and
/// the backup path when one was made.
///
/// # Errors
/// Any IO or parse failure (the file is never modified on error).
pub fn write_mcp_servers_json(
    spec: &ClientSpec,
    exe: &Path,
) -> anyhow::Result<(String, Option<PathBuf>)> {
    if spec.kind != Kind::McpServersJson {
        anyhow::bail!("write_mcp_servers_json called with the wrong config kind");
    }

    let existing = spec.config_path.exists();
    let mut config: Value = if existing {
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

    let backup = if existing {
        let bak = backup_path(&spec.config_path);
        std::fs::copy(&spec.config_path, &bak)?;
        Some(bak)
    } else {
        ensure_parent(&spec.config_path)?;
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

// ── JSONC structural editing ───────────────────────────────────────────────
//
// A tiny byte scanner good enough to: skip comments, find a member's value
// span in an object, and splice a member in without disturbing the rest of
// the document. It never allocates a full CST; the only guarantee is that the
// edited text re-parses to the same value (verified by the caller).

/// Byte offset just past the string literal starting at `i` (a `"`).
fn string_end(text: &str, i: usize) -> Option<usize> {
    let bytes = text.as_bytes();
    if bytes.get(i) != Some(&b'"') {
        return None;
    }
    let mut j = i + 1;
    while j < bytes.len() {
        match bytes[j] {
            b'\\' => j += 2,
            b'"' => return Some(j + 1),
            _ => j += 1,
        }
    }
    None
}

/// Skip whitespace and JSONC comments; returns the next significant offset.
const fn skip_trivia(text: &str, mut i: usize) -> usize {
    let bytes = text.as_bytes();
    loop {
        while i < bytes.len() && bytes[i].is_ascii_whitespace() {
            i += 1;
        }
        if i + 1 < bytes.len() && bytes[i] == b'/' {
            match bytes[i + 1] {
                b'/' => {
                    i += 2;
                    while i < bytes.len() && bytes[i] != b'\n' {
                        i += 1;
                    }
                }
                b'*' => {
                    i += 2;
                    while i + 1 < bytes.len() && !(bytes[i] == b'*' && bytes[i + 1] == b'/') {
                        i += 1;
                    }
                    i = if i + 1 < bytes.len() {
                        i + 2
                    } else {
                        bytes.len()
                    };
                }
                _ => return i,
            }
        } else {
            return i;
        }
    }
}

/// End (exclusive) of the value starting at `i` (bracket/string aware).
fn value_end(text: &str, i: usize) -> Option<usize> {
    match text.as_bytes().get(i)? {
        b'{' => matching_delim(text, i, b'{', b'}'),
        b'[' => matching_delim(text, i, b'[', b']'),
        b'"' => string_end(text, i),
        _ => {
            let bytes = text.as_bytes();
            let mut j = i;
            while j < bytes.len() {
                match bytes[j] {
                    b',' | b'}' | b']' => break,
                    b'/' if j + 1 < bytes.len() && matches!(bytes[j + 1], b'/' | b'*') => break,
                    _ => j += 1,
                }
            }
            Some(j)
        }
    }
}

/// Offset just past the delimiter that closes the one opening at `i`.
fn matching_delim(text: &str, i: usize, open: u8, close: u8) -> Option<usize> {
    let bytes = text.as_bytes();
    let mut depth = 0usize;
    let mut j = i;
    while j < bytes.len() {
        match bytes[j] {
            b'"' => j = string_end(text, j)?,
            b'/' if j + 1 < bytes.len() && matches!(bytes[j + 1], b'/' | b'*') => {
                j = skip_trivia(text, j);
            }
            b if b == open => {
                depth += 1;
                j += 1;
            }
            b if b == close => {
                depth -= 1;
                if depth == 0 {
                    return Some(j + 1);
                }
                j += 1;
            }
            _ => j += 1,
        }
    }
    None
}

/// True when the document contains a line or block comment outside strings.
fn has_comments(text: &str) -> bool {
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'"' => match string_end(text, i) {
                Some(end) => i = end,
                None => return false,
            },
            b'/' if i + 1 < bytes.len() && matches!(bytes[i + 1], b'/' | b'*') => return true,
            _ => i += 1,
        }
    }
    false
}

/// Strip comments and trailing commas so serde_json can parse the document.
fn strip_jsonc(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'"' => {
                let end = string_end(text, i).unwrap_or(bytes.len());
                out.extend_from_slice(&bytes[i..end]);
                i = end;
            }
            b'/' if i + 1 < bytes.len() && bytes[i + 1] == b'/' => {
                i += 2;
                while i < bytes.len() && bytes[i] != b'\n' {
                    i += 1;
                }
            }
            b'/' if i + 1 < bytes.len() && bytes[i + 1] == b'*' => {
                i += 2;
                while i + 1 < bytes.len() && !(bytes[i] == b'*' && bytes[i + 1] == b'/') {
                    i += 1;
                }
                i = (i + 2).min(bytes.len());
            }
            b',' => {
                let next = skip_trivia(text, i + 1);
                if !matches!(bytes.get(next), Some(b'}' | b']')) {
                    out.push(b',');
                }
                i += 1;
            }
            byte => {
                out.push(byte);
                i += 1;
            }
        }
    }
    String::from_utf8(out).unwrap_or_default()
}

/// Parse a JSONC document into a serde value. Empty documents are `{}`.
fn parse_jsonc(text: &str) -> anyhow::Result<Value> {
    let stripped = strip_jsonc(text);
    if stripped.trim().is_empty() {
        return Ok(json!({}));
    }
    serde_json::from_str(&stripped).map_err(|e| anyhow::anyhow!("{e}"))
}

/// `(value_start, value_end)` for `key` inside the object starting at `open`.
fn find_member(text: &str, open: usize, close: usize, key: &str) -> Option<(usize, usize)> {
    let bytes = text.as_bytes();
    let mut j = skip_trivia(text, open + 1);
    while j < close {
        if bytes.get(j) != Some(&b'"') {
            return None;
        }
        let key_end = string_end(text, j)?;
        let member_key = &text[j + 1..key_end - 1];
        j = skip_trivia(text, key_end);
        if bytes.get(j) != Some(&b':') {
            return None;
        }
        let value_start = skip_trivia(text, j + 1);
        let value_end = value_end(text, value_start)?;
        if member_key == key {
            return Some((value_start, value_end));
        }
        j = skip_trivia(text, value_end);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }
    None
}

/// The whitespace indentation of the line containing `pos` (`""` when the
/// line has other content before `pos`).
fn line_indent(text: &str, pos: usize) -> String {
    let start = text[..pos].rfind('\n').map_or(0, |nl| nl + 1);
    let prefix = &text[start..pos];
    if prefix.chars().all(|c| c == ' ' || c == '\t') {
        prefix.to_string()
    } else {
        String::new()
    }
}

/// Insert (or replace) `key: value` in the object `text[open..close]`,
/// preserving comments elsewhere in the document. Returns the edited text.
fn upsert_member(text: &str, open: usize, close: usize, key: &str, value: &Value) -> String {
    let value_json = serde_json::to_string(value).unwrap_or_else(|_| "null".to_string());
    if let Some((vs, ve)) = find_member(text, open, close, key) {
        let mut out = String::with_capacity(text.len() + value_json.len());
        out.push_str(&text[..vs]);
        out.push_str(&value_json);
        out.push_str(&text[ve..]);
        return out;
    }
    let entry = format!(
        "{}: {value_json}",
        serde_json::to_string(key).unwrap_or_else(|_| "\"?\"".to_string())
    );

    let bytes = text.as_bytes();
    let close_brace = close - 1;
    let mut last_key_start: Option<usize> = None;
    let mut last_value_end: Option<usize> = None;
    let mut j = skip_trivia(text, open + 1);
    while j < close {
        if bytes.get(j) != Some(&b'"') {
            break;
        }
        let Some(key_end) = string_end(text, j) else {
            break;
        };
        last_key_start = Some(j);
        j = skip_trivia(text, key_end);
        if bytes.get(j) != Some(&b':') {
            break;
        }
        let value_start = skip_trivia(text, j + 1);
        let Some(value_end) = value_end(text, value_start) else {
            break;
        };
        last_value_end = Some(value_end);
        j = skip_trivia(text, value_end);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }

    let close_indent = line_indent(text, close_brace);
    let member_indent =
        last_key_start.map_or_else(|| format!("{close_indent}  "), |k| line_indent(text, k));
    let (from, separator) = match last_value_end {
        Some(ve) => (ve, ","),
        None => (skip_trivia(text, open + 1), ""),
    };
    // Preserve any comment that trails the last member.
    let trailing = &text[from..close_brace];
    let comment = if has_comments(trailing) {
        format!(" {}", trailing.trim())
    } else {
        String::new()
    };
    let replacement = format!("{separator}\n{member_indent}{entry}{comment}\n{close_indent}");

    let mut out = String::with_capacity(text.len() + replacement.len());
    out.push_str(&text[..from]);
    out.push_str(&replacement);
    out.push_str(&text[close_brace..]);
    out
}

/// Structural upsert of `mcp.whitemagic` in an OpenCode JSONC document.
fn jsonc_upsert_whitemagic(text: &str, entry: &Value) -> anyhow::Result<String> {
    let root_open = skip_trivia(text, 0);
    if text.as_bytes().get(root_open) != Some(&b'{') {
        anyhow::bail!("config root is not an object");
    }
    let root_close = matching_delim(text, root_open, b'{', b'}')
        .ok_or_else(|| anyhow::anyhow!("unbalanced braces in config"))?;
    if let Some((mcp_start, mcp_end)) = find_member(text, root_open, root_close, "mcp") {
        if text.as_bytes().get(mcp_start) != Some(&b'{') {
            anyhow::bail!("existing \"mcp\" is not an object — refusing to overwrite it");
        }
        Ok(upsert_member(text, mcp_start, mcp_end, "whitemagic", entry))
    } else {
        let mcp = json!({ "whitemagic": entry });
        Ok(upsert_member(text, root_open, root_close, "mcp", &mcp))
    }
}

/// Patch OpenCode's `opencode.jsonc`, preserving comments and formatting.
///
/// # Errors
/// Any IO or parse failure; the original file is never modified on error.
pub fn write_opencode_jsonc(
    spec: &ClientSpec,
    exe: &Path,
) -> anyhow::Result<(String, Option<PathBuf>)> {
    if spec.kind != Kind::OpencodeJsonc {
        anyhow::bail!("write_opencode_jsonc called with the wrong config kind");
    }
    let desired = opencode_entry(exe);
    let existing = spec.config_path.exists();

    if !existing {
        ensure_parent(&spec.config_path)?;
        let doc = json!({ "mcp": { "whitemagic": desired } });
        let rendered = serde_json::to_string_pretty(&doc)?;
        std::fs::write(&spec.config_path, format!("{rendered}\n"))?;
        let verify = std::fs::read_to_string(&spec.config_path)?;
        parse_jsonc(&verify)
            .map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;
        return Ok((format!("created {}", spec.config_path.display()), None));
    }

    let text = std::fs::read_to_string(&spec.config_path)?;
    let parsed = parse_jsonc(&text).map_err(|e| {
        anyhow::anyhow!(
            "existing config is not valid JSONC ({}): {e}",
            spec.config_path.display()
        )
    })?;

    let mut merged = parsed;
    let root = merged
        .as_object_mut()
        .ok_or_else(|| anyhow::anyhow!("config root is not an object"))?;
    let mcp = root
        .entry("mcp")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| anyhow::anyhow!("existing \"mcp\" is not an object"))?;
    if mcp.get("whitemagic") == Some(&desired) {
        return Ok(("already configured".to_string(), None));
    }
    mcp.insert("whitemagic".to_string(), desired.clone());

    let edited = if has_comments(&text) {
        jsonc_upsert_whitemagic(&text, &desired)?
    } else {
        format!("{}\n", serde_json::to_string_pretty(&merged)?)
    };

    // The edited document must re-parse to the merged value before we write.
    let check = parse_jsonc(&edited)
        .map_err(|e| anyhow::anyhow!("internal error: edited JSONC does not parse: {e}"))?;
    if check != merged {
        anyhow::bail!("internal error: edited JSONC does not round-trip to the intended value");
    }

    let backup = backup_path(&spec.config_path);
    std::fs::copy(&spec.config_path, &backup)?;
    std::fs::write(&spec.config_path, &edited)?;
    let verify = std::fs::read_to_string(&spec.config_path)?;
    parse_jsonc(&verify).map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;

    Ok((
        format!("updated {}", spec.config_path.display()),
        Some(backup),
    ))
}

// ── Codex TOML ─────────────────────────────────────────────────────────────

fn codex_entry(exe: &Path) -> toml_edit::Table {
    let mut table = toml_edit::Table::new();
    table["command"] = toml_edit::value(exe.display().to_string());
    let mut args = toml_edit::Array::new();
    for arg in serve_args() {
        args.push(arg);
    }
    table["args"] = toml_edit::value(args);
    table
}

fn codex_entry_matches(item: &toml_edit::Item, exe: &Path) -> bool {
    let Some(table) = item.as_table() else {
        return false;
    };
    let expected_command = exe.display().to_string();
    let command_ok =
        table.get("command").and_then(toml_edit::Item::as_str) == Some(expected_command.as_str());
    let args: Option<Vec<&str>> = table
        .get("args")
        .and_then(toml_edit::Item::as_array)
        .map(|array| array.iter().filter_map(toml_edit::Value::as_str).collect());
    command_ok && args == Some(serve_args().to_vec())
}

/// Patch Codex's `config.toml` (`[mcp_servers.whitemagic]`), preserving
/// comments and unrelated keys.
///
/// # Errors
/// Any IO or parse failure; the original file is never modified on error.
pub fn write_codex_toml(
    spec: &ClientSpec,
    exe: &Path,
) -> anyhow::Result<(String, Option<PathBuf>)> {
    if spec.kind != Kind::CodexToml {
        anyhow::bail!("write_codex_toml called with the wrong config kind");
    }
    let existing = spec.config_path.exists();
    let text = if existing {
        std::fs::read_to_string(&spec.config_path)?
    } else {
        String::new()
    };
    let mut doc: toml_edit::DocumentMut = text.parse().map_err(|e| {
        anyhow::anyhow!(
            "existing config is not valid TOML ({}): {e}",
            spec.config_path.display()
        )
    })?;

    if let Some(item) = doc
        .get("mcp_servers")
        .and_then(|servers| servers.get("whitemagic"))
    {
        if codex_entry_matches(item, exe) {
            return Ok(("already configured".to_string(), None));
        }
    }

    if doc.get("mcp_servers").is_none() {
        let mut servers = toml_edit::Table::new();
        servers.set_implicit(true);
        doc["mcp_servers"] = toml_edit::Item::Table(servers);
    }
    let servers = doc["mcp_servers"]
        .as_table_mut()
        .ok_or_else(|| anyhow::anyhow!("existing \"mcp_servers\" is not a table"))?;
    servers["whitemagic"] = toml_edit::Item::Table(codex_entry(exe));

    let rendered = doc.to_string();
    toml::from_str::<toml::Value>(&rendered)
        .map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;

    let backup = if existing {
        let bak = backup_path(&spec.config_path);
        std::fs::copy(&spec.config_path, &bak)?;
        Some(bak)
    } else {
        ensure_parent(&spec.config_path)?;
        None
    };
    std::fs::write(&spec.config_path, rendered)?;

    let (verb, path) = if existing {
        ("updated", spec.config_path.display().to_string())
    } else {
        ("created", spec.config_path.display().to_string())
    };
    Ok((format!("{verb} {path}"), backup))
}

/// Patch the client config in its native format.
///
/// # Errors
/// Any IO or parse failure (the file is never modified on error).
pub fn write(spec: &ClientSpec, exe: &Path) -> anyhow::Result<(String, Option<PathBuf>)> {
    match spec.kind {
        Kind::McpServersJson => write_mcp_servers_json(spec, exe),
        Kind::OpencodeJsonc => write_opencode_jsonc(spec, exe),
        Kind::CodexToml => write_codex_toml(spec, exe),
    }
}

/// What `connect` did (or would do) for one detected client.
#[derive(Debug, Clone)]
pub enum ConnectAction {
    /// Client is installed and already references whitemagic.
    Configured,
    /// Client config was patched (write mode).
    Written,
    /// Client is installed; dry run only proposed the change.
    Proposed,
    /// Client is installed but the write failed.
    Failed(String),
}

/// One detected client and the outcome for it.
#[derive(Debug, Clone)]
pub struct ConnectOutcome {
    pub id: &'static str,
    pub label: &'static str,
    pub action: ConnectAction,
    pub backup: Option<PathBuf>,
}

/// A client counts as installed when its config file exists or its config
/// directory does (the app has written something there at least once).
#[must_use]
pub fn installed(spec: &ClientSpec) -> bool {
    spec.config_path.exists()
        || spec
            .config_path
            .parent()
            .is_some_and(std::path::Path::exists)
}

/// True when the config already references whitemagic.
#[must_use]
pub fn configured(spec: &ClientSpec) -> bool {
    std::fs::read_to_string(&spec.config_path).is_ok_and(|t| t.contains("whitemagic"))
}

/// Wire every detected client that is not already configured.
///
/// Dry run (`apply == false`) never touches a file; apply mode uses the
/// same backup + read-back path as `wm setup <client> --write`.
#[must_use]
pub fn connect(exe: &Path, apply: bool) -> Vec<ConnectOutcome> {
    connect_with(&specs(), exe, apply)
}

/// Testable core of [`connect`] with an explicit spec list.
#[must_use]
pub fn connect_with(list: &[ClientSpec], exe: &Path, apply: bool) -> Vec<ConnectOutcome> {
    list.iter()
        .filter(|spec| installed(spec))
        .map(|spec| {
            let outcome = |action, backup| ConnectOutcome {
                id: spec.id,
                label: spec.label,
                action,
                backup,
            };
            if configured(spec) {
                return outcome(ConnectAction::Configured, None);
            }
            if !apply {
                return outcome(ConnectAction::Proposed, None);
            }
            match write(spec, exe) {
                Ok((_, backup)) => outcome(ConnectAction::Written, backup),
                Err(e) => outcome(ConnectAction::Failed(e.to_string()), None),
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn spec(kind: Kind, path: PathBuf) -> ClientSpec {
        ClientSpec {
            id: "test",
            label: "Test",
            config_path: path,
            kind,
        }
    }

    #[test]
    fn proposal_shapes_are_parseable() {
        let exe = Path::new("/opt/wm");
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
    fn connect_wires_detected_clients_only() {
        let tmp = tempfile::tempdir().unwrap();
        let installed_path = tmp.path().join("a/mcp.json");
        std::fs::create_dir_all(installed_path.parent().unwrap()).unwrap();
        std::fs::write(&installed_path, r#"{"mcpServers":{}}"#).unwrap();
        let missing = tmp.path().join("missing/mcp.json");
        let list = vec![
            spec(Kind::McpServersJson, installed_path.clone()),
            spec(Kind::McpServersJson, missing),
        ];
        let exe = Path::new("/opt/wm");

        let dry = connect_with(&list, exe, false);
        assert_eq!(dry.len(), 1, "only the installed client is a target");
        assert!(matches!(dry[0].action, ConnectAction::Proposed));

        let written = connect_with(&list, exe, true);
        assert!(matches!(written[0].action, ConnectAction::Written));
        assert!(written[0].backup.as_ref().unwrap().exists());
        let v: Value =
            serde_json::from_str(&std::fs::read_to_string(&installed_path).unwrap()).unwrap();
        assert_eq!(v["mcpServers"]["whitemagic"]["command"], "/opt/wm");

        let again = connect_with(&list, exe, false);
        assert!(matches!(again[0].action, ConnectAction::Configured));
    }

    #[test]
    fn json_merge_is_idempotent_and_backs_up() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("mcp.json");
        std::fs::write(&path, r#"{"mcpServers":{"other":{"command":"x"}}}"#).unwrap();
        let spec = spec(Kind::McpServersJson, path.clone());
        let exe = Path::new("/opt/wm");

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
    fn jsonc_scanner_ignores_comments_inside_strings() {
        let text = r#"{"a": "http://x // not a comment", "b": "esc\" // no"}"#;
        assert!(!has_comments(text));
        let v = parse_jsonc(text).unwrap();
        assert_eq!(v["a"], "http://x // not a comment");
    }

    #[test]
    fn jsonc_insert_preserves_comments() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("opencode.jsonc");
        let original = "\
{
  // my editor setup
  \"mcp\": {
    \"other\": {
      \"type\": \"local\", /* keep me */
      \"command\": [\"other\"]
    }
  },
  \"theme\": \"dark\"
}
";
        std::fs::write(&path, original).unwrap();
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        let exe = Path::new("/opt/wm");

        let (msg, backup) = write_opencode_jsonc(&spec, exe).unwrap();
        assert!(msg.contains("updated"), "{msg}");
        assert!(backup.unwrap().exists());

        let edited = std::fs::read_to_string(&path).unwrap();
        assert!(edited.contains("// my editor setup"), "line comment lost");
        assert!(edited.contains("/* keep me */"), "block comment lost");
        let v = parse_jsonc(&edited).unwrap();
        assert_eq!(v["mcp"]["whitemagic"]["command"][0], "/opt/wm");
        assert_eq!(v["mcp"]["other"]["command"][0], "other");
        assert_eq!(v["theme"], "dark");

        let (msg2, backup2) = write_opencode_jsonc(&spec, exe).unwrap();
        assert!(msg2.contains("already configured"));
        assert!(backup2.is_none());
    }

    #[test]
    fn jsonc_replaces_existing_entry_and_handles_trailing_comma() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("opencode.jsonc");
        let original = "\
{
  \"mcp\": {
    // the old path
    \"whitemagic\": {\"type\": \"local\", \"command\": [\"/old/wm\"]},
  },
}
";
        std::fs::write(&path, original).unwrap();
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        write_opencode_jsonc(&spec, Path::new("/new/wm")).unwrap();

        let edited = std::fs::read_to_string(&path).unwrap();
        assert!(edited.contains("// the old path"), "comment lost");
        let v = parse_jsonc(&edited).unwrap();
        assert_eq!(v["mcp"]["whitemagic"]["command"][0], "/new/wm");
    }

    #[test]
    fn jsonc_without_comments_is_rendered_pretty() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("opencode.jsonc");
        std::fs::write(&path, r#"{"mcp":{"other":{"type":"local"}}}"#).unwrap();
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        write_opencode_jsonc(&spec, Path::new("/opt/wm")).unwrap();
        let edited = std::fs::read_to_string(&path).unwrap();
        assert!(edited.contains('\n'), "expected pretty output");
        let v = parse_jsonc(&edited).unwrap();
        assert_eq!(v["mcp"]["whitemagic"]["enabled"], true);
        assert_eq!(v["mcp"]["other"]["type"], "local");
    }

    #[test]
    fn jsonc_creates_missing_file() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("nested/opencode.jsonc");
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        let (msg, backup) = write_opencode_jsonc(&spec, Path::new("/opt/wm")).unwrap();
        assert!(msg.contains("created"));
        assert!(backup.is_none());
        let v = parse_jsonc(&std::fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(v["mcp"]["whitemagic"]["command"][0], "/opt/wm");
    }

    #[test]
    fn jsonc_refuses_to_clobber_a_non_object_mcp() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("opencode.jsonc");
        std::fs::write(&path, r#"{"mcp": 42}"#).unwrap();
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        let err = write_opencode_jsonc(&spec, Path::new("/opt/wm")).unwrap_err();
        assert!(err.to_string().contains("not an object"));
        assert_eq!(std::fs::read_to_string(&path).unwrap(), r#"{"mcp": 42}"#);
    }

    #[test]
    fn codex_toml_preserves_comments_and_is_idempotent() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("config.toml");
        let original = "\
# my codex config
model = \"o3\"

[mcp_servers.other]
command = \"other\"
args = [\"serve\"]
";
        std::fs::write(&path, original).unwrap();
        let spec = spec(Kind::CodexToml, path.clone());
        let exe = Path::new("/opt/wm");

        let (msg, backup) = write_codex_toml(&spec, exe).unwrap();
        assert!(msg.contains("updated"), "{msg}");
        assert!(backup.unwrap().exists());

        let edited = std::fs::read_to_string(&path).unwrap();
        assert!(edited.contains("# my codex config"), "comment lost");
        assert!(edited.contains("[mcp_servers.other]"));
        let parsed: toml::Value = toml::from_str(&edited).unwrap();
        assert_eq!(
            parsed["mcp_servers"]["whitemagic"]["command"].as_str(),
            Some("/opt/wm")
        );
        assert_eq!(
            parsed["mcp_servers"]["whitemagic"]["args"][1].as_str(),
            Some("--profile")
        );
        assert_eq!(parsed["model"].as_str(), Some("o3"));

        let (msg2, backup2) = write_codex_toml(&spec, exe).unwrap();
        assert!(msg2.contains("already configured"));
        assert!(backup2.is_none());
    }

    #[test]
    fn codex_toml_creates_missing_file() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("codex/config.toml");
        let spec = spec(Kind::CodexToml, path.clone());
        let (msg, backup) = write_codex_toml(&spec, Path::new("/opt/wm")).unwrap();
        assert!(msg.contains("created"));
        assert!(backup.is_none());
        let parsed: toml::Value = toml::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        assert_eq!(
            parsed["mcp_servers"]["whitemagic"]["command"].as_str(),
            Some("/opt/wm")
        );
    }

    #[test]
    fn codex_toml_refuses_non_table_mcp_servers() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("config.toml");
        std::fs::write(&path, "mcp_servers = 3\n").unwrap();
        let spec = spec(Kind::CodexToml, path.clone());
        let err = write_codex_toml(&spec, Path::new("/opt/wm")).unwrap_err();
        assert!(err.to_string().contains("not a table"));
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "mcp_servers = 3\n");
    }
}
