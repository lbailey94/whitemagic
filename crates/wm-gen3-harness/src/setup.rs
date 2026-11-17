//! `wm setup <client>` — Backup-verified, comment-preserving MCP client configuration.
//!
//! Ported cleanly from Gen 2 (`setup.rs`) with Gen 3 invariants:
//! - Always expands paths (never emits literal `$HOME` or `~/`).
//! - Emits `["--store", "<abs-store>", "serve", "--profile", "cyberbrain"]` (plus `--readonly`
//!   when requested or when another writable `wm serve` client is already configured).
//! - Creates collision-safe timestamped backups before mutating any existing config.
//! - Preserves comments in OpenCode JSONC (`opencode.jsonc`) and Codex TOML (`config.toml`).
//! - Reads back and re-parses every written config before returning.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConfigKind {
    McpServersJson,
    OpencodeJsonc,
    CodexToml,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClientSpec {
    pub id: &'static str,
    pub label: &'static str,
    pub config_path: PathBuf,
    pub kind: ConfigKind,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupOutcome {
    pub id: String,
    pub label: String,
    pub config_path: String,
    pub action: String,
    pub readonly: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub backup_path: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SetupReport {
    pub version: &'static str,
    pub write_mode: bool,
    pub remove_mode: bool,
    pub binary_path: String,
    pub store_path: String,
    pub outcomes: Vec<SetupOutcome>,
}

fn home_in(home: Option<&Path>) -> PathBuf {
    home.map_or_else(
        || std::env::var_os("HOME").map_or_else(|| PathBuf::from("."), PathBuf::from),
        Path::to_path_buf,
    )
}

fn xdg_config_in(home: Option<&Path>) -> PathBuf {
    if home.is_none() {
        if let Some(xdg) = std::env::var_os("XDG_CONFIG_HOME") {
            if !xdg.is_empty() {
                return PathBuf::from(xdg);
            }
        }
    }
    home_in(home).join(".config")
}

/// Supported MCP client targets rooted at an explicit `home` (or `$HOME`).
#[must_use]
pub fn specs_in(home: Option<&Path>) -> Vec<ClientSpec> {
    let h = home_in(home);
    let xdg = xdg_config_in(home);
    vec![
        ClientSpec {
            id: "opencode",
            label: "OpenCode",
            config_path: xdg.join("opencode/opencode.jsonc"),
            kind: ConfigKind::OpencodeJsonc,
        },
        ClientSpec {
            id: "claude",
            label: "Claude Code",
            config_path: h.join(".claude.json"),
            kind: ConfigKind::McpServersJson,
        },
        ClientSpec {
            id: "claude-desktop",
            label: "Claude Desktop",
            config_path: xdg.join("Claude/claude_desktop_config.json"),
            kind: ConfigKind::McpServersJson,
        },
        ClientSpec {
            id: "cursor",
            label: "Cursor",
            config_path: h.join(".cursor/mcp.json"),
            kind: ConfigKind::McpServersJson,
        },
        ClientSpec {
            id: "windsurf",
            label: "Windsurf",
            config_path: h.join(".codeium/windsurf/mcp_config.json"),
            kind: ConfigKind::McpServersJson,
        },
        ClientSpec {
            id: "codex",
            label: "Codex CLI",
            config_path: h.join(".codex/config.toml"),
            kind: ConfigKind::CodexToml,
        },
        ClientSpec {
            id: "antigravity",
            label: "Antigravity CLI",
            config_path: h.join(".gemini/antigravity-cli/settings.json"),
            kind: ConfigKind::McpServersJson,
        },
    ]
}

#[must_use]
pub fn find_in(home: Option<&Path>, id: &str) -> Option<ClientSpec> {
    let needle = id.trim();
    specs_in(home)
        .into_iter()
        .find(|s| s.id.eq_ignore_ascii_case(needle))
}

#[must_use]
pub fn installed(spec: &ClientSpec) -> bool {
    installed_in(None, spec)
}

#[must_use]
pub fn installed_in(home: Option<&Path>, spec: &ClientSpec) -> bool {
    if spec.config_path.exists() {
        return true;
    }
    if spec.id == "claude" {
        return home_in(home).join(".claude").exists();
    }
    spec.config_path
        .parent()
        .is_some_and(std::path::Path::exists)
}

fn serve_args(store_path: &Path, readonly: bool) -> Vec<String> {
    let mut args = vec![
        "--store".to_string(),
        store_path.display().to_string(),
        "serve".to_string(),
        "--profile".to_string(),
        "cyberbrain".to_string(),
    ];
    if readonly {
        args.push("--readonly".to_string());
    }
    args
}

fn mcp_servers_entry(exe: &Path, store_path: &Path, readonly: bool) -> Value {
    json!({
        "command": exe.display().to_string(),
        "args": serve_args(store_path, readonly),
    })
}

fn opencode_entry(exe: &Path, store_path: &Path, readonly: bool) -> Value {
    let mut cmd = vec![exe.display().to_string()];
    cmd.extend(serve_args(store_path, readonly));
    json!({
        "type": "local",
        "command": cmd,
        "enabled": true,
    })
}

fn create_backup_at(path: &Path, ts: &str) -> Result<PathBuf, String> {
    let base = format!("{}.bak-{ts}", path.display());
    for attempt in 0u32.. {
        let candidate = if attempt == 0 {
            PathBuf::from(&base)
        } else {
            PathBuf::from(format!("{base}-{attempt}"))
        };
        match std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&candidate)
        {
            Ok(mut dest) => {
                let res = (|| -> std::io::Result<()> {
                    let mut src = std::fs::File::open(path)?;
                    std::io::copy(&mut src, &mut dest)?;
                    let perms = src.metadata()?.permissions();
                    drop(src);
                    std::fs::set_permissions(&candidate, perms)
                })();
                if let Err(e) = res {
                    let _ = std::fs::remove_file(&candidate);
                    return Err(format!(
                        "backup write failed ({}): {e}",
                        candidate.display()
                    ));
                }
                return Ok(candidate);
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
            Err(e) => {
                return Err(format!(
                    "backup create failed ({}): {e}",
                    candidate.display()
                ));
            }
        }
    }
    unreachable!("free backup suffix exists within u32 attempts")
}

fn create_backup(path: &Path) -> Result<PathBuf, String> {
    create_backup_at(path, &chrono::Utc::now().format("%Y%m%d%H%M%S").to_string())
}

fn ensure_parent(path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("failed to create parent {}: {e}", parent.display()))?;
    }
    Ok(())
}

// ── JSONC structural helpers ──────────────────────────────────────────────

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

fn strip_jsonc(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
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

fn parse_jsonc(text: &str) -> Result<Value, String> {
    let stripped = strip_jsonc(text);
    if stripped.trim().is_empty() {
        return Ok(json!({}));
    }
    serde_json::from_str(&stripped).map_err(|e| format!("{e}"))
}

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
        let vs = skip_trivia(text, j + 1);
        let ve = value_end(text, vs)?;
        if member_key == key {
            return Some((vs, ve));
        }
        j = skip_trivia(text, ve);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }
    None
}

fn line_indent(text: &str, pos: usize) -> String {
    let start = text[..pos].rfind('\n').map_or(0, |nl| nl + 1);
    let prefix = &text[start..pos];
    if prefix.chars().all(|c| c == ' ' || c == '\t') {
        prefix.to_string()
    } else {
        String::new()
    }
}

fn line_leading_ws(text: &str, pos: usize) -> String {
    let start = text[..pos].rfind('\n').map_or(0, |nl| nl + 1);
    text[start..]
        .chars()
        .take_while(|c| *c == ' ' || *c == '\t')
        .collect()
}

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
        let vs = skip_trivia(text, j + 1);
        let Some(ve) = value_end(text, vs) else {
            break;
        };
        last_value_end = Some(ve);
        j = skip_trivia(text, ve);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }
    let close_indent = {
        let ind = line_indent(text, close_brace);
        if ind.is_empty() && !text[..close_brace].ends_with('\n') {
            line_leading_ws(text, close_brace)
        } else {
            ind
        }
    };
    let member_indent = last_key_start.map_or_else(
        || format!("{close_indent}  "),
        |k| {
            let ind = line_indent(text, k);
            if ind.is_empty() && !text[..k].ends_with('\n') {
                format!("{close_indent}  ")
            } else {
                ind
            }
        },
    );
    let (from, separator) = match last_value_end {
        Some(ve) => (ve, ","),
        None => (skip_trivia(text, open + 1), ""),
    };
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

fn jsonc_upsert_whitemagic(text: &str, entry: &Value) -> Result<String, String> {
    let root_open = skip_trivia(text, 0);
    if text.as_bytes().get(root_open) != Some(&b'{') {
        return Err("config root is not an object".to_string());
    }
    let root_close = matching_delim(text, root_open, b'{', b'}')
        .ok_or_else(|| "unbalanced braces in config".to_string())?;
    if let Some((mcp_start, mcp_end)) = find_member(text, root_open, root_close, "mcp") {
        if text.as_bytes().get(mcp_start) != Some(&b'{') {
            return Err("existing \"mcp\" is not an object — refusing to overwrite".to_string());
        }
        Ok(upsert_member(text, mcp_start, mcp_end, "whitemagic", entry))
    } else {
        let mcp = json!({ "whitemagic": entry });
        Ok(upsert_member(text, root_open, root_close, "mcp", &mcp))
    }
}

fn splice_member_out(
    text: &str,
    key_start: usize,
    value_end: usize,
    prev_value_end: Option<usize>,
) -> String {
    let line_start = text[..key_start].rfind('\n').map_or(0, |nl| nl + 1);
    let from = if text[line_start..key_start]
        .chars()
        .all(|c| c == ' ' || c == '\t')
    {
        line_start
    } else {
        key_start
    };
    let after = skip_trivia(text, value_end);
    if text.as_bytes().get(after) == Some(&b',') {
        let end = text[after..]
            .find('\n')
            .map_or(text.len(), |nl| after + nl + 1);
        let mut out = String::with_capacity(text.len());
        out.push_str(&text[..from]);
        out.push_str(&text[end..]);
        return out;
    }
    if let Some(pve) = prev_value_end {
        let comma = skip_trivia(text, pve);
        if text.as_bytes().get(comma) == Some(&b',') {
            let mut out = String::with_capacity(text.len().saturating_sub(value_end - from + 1));
            out.push_str(&text[..comma]);
            out.push_str(&text[comma + 1..from]);
            out.push_str(&text[value_end..]);
            return out;
        }
    }
    let mut out = String::with_capacity(text.len());
    out.push_str(&text[..from]);
    out.push_str(&text[value_end..]);
    out
}

fn remove_member(text: &str, open: usize, close: usize, key: &str) -> Option<String> {
    let bytes = text.as_bytes();
    let mut j = skip_trivia(text, open + 1);
    let mut prev_value_end: Option<usize> = None;
    while j < close {
        if bytes.get(j) != Some(&b'"') {
            return None;
        }
        let key_end = string_end(text, j)?;
        let member_key = &text[j + 1..key_end - 1];
        let colon = skip_trivia(text, key_end);
        if bytes.get(colon) != Some(&b':') {
            return None;
        }
        let vs = skip_trivia(text, colon + 1);
        let ve = value_end(text, vs)?;
        if member_key == key {
            return Some(splice_member_out(text, j, ve, prev_value_end));
        }
        prev_value_end = Some(ve);
        j = skip_trivia(text, ve);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }
    None
}

fn jsonc_remove_whitemagic(text: &str) -> Result<Option<String>, String> {
    let root_open = skip_trivia(text, 0);
    if text.as_bytes().get(root_open) != Some(&b'{') {
        return Err("config root is not an object".to_string());
    }
    let root_close = matching_delim(text, root_open, b'{', b'}')
        .ok_or_else(|| "unbalanced braces in config".to_string())?;
    let Some((mcp_start, mcp_end)) = find_member(text, root_open, root_close, "mcp") else {
        return Ok(None);
    };
    if text.as_bytes().get(mcp_start) != Some(&b'{') {
        return Err("existing \"mcp\" is not an object".to_string());
    }
    Ok(remove_member(text, mcp_start, mcp_end, "whitemagic"))
}

// ── Codex TOML comment-preserving section editor ─────────────────────────

fn render_toml_string(s: &str) -> String {
    serde_json::to_string(s).unwrap_or_else(|_| format!("\"{s}\""))
}

fn render_codex_section(exe: &Path, store_path: &Path, readonly: bool) -> String {
    let args = serve_args(store_path, readonly)
        .into_iter()
        .map(|a| render_toml_string(&a))
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "[mcp_servers.whitemagic]\ncommand = {}\nargs = [{args}]\n",
        render_toml_string(&exe.display().to_string())
    )
}

fn find_toml_section_span(text: &str, header: &str) -> Option<(usize, usize)> {
    let mut pos = 0usize;
    let mut start: Option<usize> = None;
    for line in text.split_inclusive('\n') {
        let trimmed = line.trim();
        if start.is_none() {
            if trimmed == header {
                start = Some(pos);
            }
        } else if trimmed.starts_with('[') && trimmed.ends_with(']') {
            return start.map(|s| (s, pos));
        }
        pos += line.len();
    }
    start.map(|s| (s, text.len()))
}

fn verify_codex_toml_entry(
    text: &str,
    exe: &Path,
    store_path: &Path,
    readonly: bool,
) -> Result<bool, String> {
    let Some((s, e)) = find_toml_section_span(text, "[mcp_servers.whitemagic]") else {
        return Ok(false);
    };
    let sec = &text[s..e];
    let expected_cmd = format!(
        "command = {}",
        render_toml_string(&exe.display().to_string())
    );
    let args = serve_args(store_path, readonly)
        .into_iter()
        .map(|a| render_toml_string(&a))
        .collect::<Vec<_>>()
        .join(", ");
    let expected_args = format!("args = [{args}]");
    Ok(sec.lines().any(|l| l.trim() == expected_cmd)
        && sec.lines().any(|l| l.trim() == expected_args))
}

// ── Per-format read/write/remove ─────────────────────────────────────────

fn write_mcp_servers_json(
    spec: &ClientSpec,
    exe: &Path,
    store_path: &Path,
    readonly: bool,
) -> Result<(String, Option<PathBuf>), String> {
    let desired = mcp_servers_entry(exe, store_path, readonly);
    let existing = spec.config_path.exists();
    let mut config: Value = if existing {
        let text = std::fs::read_to_string(&spec.config_path)
            .map_err(|e| format!("read {} failed: {e}", spec.config_path.display()))?;
        serde_json::from_str(&text).map_err(|e| {
            format!(
                "existing JSON invalid ({}): {e}",
                spec.config_path.display()
            )
        })?
    } else {
        json!({})
    };

    if config.get("mcpServers").and_then(|s| s.get("whitemagic")) == Some(&desired) {
        return Ok(("already configured".to_string(), None));
    }

    let obj = config
        .as_object_mut()
        .ok_or_else(|| "config root is not a JSON object".to_string())?;
    let servers = obj
        .entry("mcpServers")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| "mcpServers is not a JSON object".to_string())?;
    servers.insert("whitemagic".to_string(), desired);

    let backup = if existing {
        Some(create_backup(&spec.config_path)?)
    } else {
        ensure_parent(&spec.config_path)?;
        None
    };

    let rendered =
        serde_json::to_string_pretty(&config).map_err(|e| format!("JSON serialize failed: {e}"))?;
    std::fs::write(&spec.config_path, format!("{rendered}\n"))
        .map_err(|e| format!("write {} failed: {e}", spec.config_path.display()))?;

    let verify = std::fs::read_to_string(&spec.config_path)
        .map_err(|e| format!("read-back {} failed: {e}", spec.config_path.display()))?;
    serde_json::from_str::<Value>(&verify)
        .map_err(|e| format!("written JSON failed parse-back: {e}"))?;

    let verb = if existing { "updated" } else { "created" };
    Ok((format!("{verb} {}", spec.config_path.display()), backup))
}

fn write_opencode_jsonc(
    spec: &ClientSpec,
    exe: &Path,
    store_path: &Path,
    readonly: bool,
) -> Result<(String, Option<PathBuf>), String> {
    let desired = opencode_entry(exe, store_path, readonly);
    let existing = spec.config_path.exists();

    if !existing {
        ensure_parent(&spec.config_path)?;
        let doc = json!({ "mcp": { "whitemagic": desired } });
        let rendered = serde_json::to_string_pretty(&doc)
            .map_err(|e| format!("JSON serialize failed: {e}"))?;
        std::fs::write(&spec.config_path, format!("{rendered}\n"))
            .map_err(|e| format!("write {} failed: {e}", spec.config_path.display()))?;
        let verify = std::fs::read_to_string(&spec.config_path)
            .map_err(|e| format!("read-back failed: {e}"))?;
        parse_jsonc(&verify).map_err(|e| format!("written JSONC failed validation: {e}"))?;
        return Ok((format!("created {}", spec.config_path.display()), None));
    }

    let text = std::fs::read_to_string(&spec.config_path)
        .map_err(|e| format!("read {} failed: {e}", spec.config_path.display()))?;
    let mut merged = parse_jsonc(&text).map_err(|e| {
        format!(
            "existing JSONC invalid ({}): {e}",
            spec.config_path.display()
        )
    })?;
    let root = merged
        .as_object_mut()
        .ok_or_else(|| "config root is not an object".to_string())?;
    let mcp = root
        .entry("mcp")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| "existing \"mcp\" is not an object".to_string())?;
    if mcp.get("whitemagic") == Some(&desired) {
        return Ok(("already configured".to_string(), None));
    }
    mcp.insert("whitemagic".to_string(), desired.clone());

    let edited = if has_comments(&text) {
        jsonc_upsert_whitemagic(&text, &desired)?
    } else {
        let pretty = serde_json::to_string_pretty(&merged)
            .map_err(|e| format!("JSON serialize failed: {e}"))?;
        format!("{pretty}\n")
    };

    let check = parse_jsonc(&edited)
        .map_err(|e| format!("internal error: edited JSONC does not parse: {e}"))?;
    if check != merged {
        return Err("internal error: edited JSONC failed round-trip parity".to_string());
    }

    let backup = create_backup(&spec.config_path)?;
    std::fs::write(&spec.config_path, &edited)
        .map_err(|e| format!("write {} failed: {e}", spec.config_path.display()))?;
    let verify =
        std::fs::read_to_string(&spec.config_path).map_err(|e| format!("read-back failed: {e}"))?;
    parse_jsonc(&verify).map_err(|e| format!("written JSONC failed validation: {e}"))?;

    Ok((
        format!("updated {}", spec.config_path.display()),
        Some(backup),
    ))
}

fn write_codex_toml(
    spec: &ClientSpec,
    exe: &Path,
    store_path: &Path,
    readonly: bool,
) -> Result<(String, Option<PathBuf>), String> {
    let existing = spec.config_path.exists();
    let text = if existing {
        std::fs::read_to_string(&spec.config_path)
            .map_err(|e| format!("read {} failed: {e}", spec.config_path.display()))?
    } else {
        String::new()
    };

    if verify_codex_toml_entry(&text, exe, store_path, readonly)? {
        return Ok(("already configured".to_string(), None));
    }

    let section = render_codex_section(exe, store_path, readonly);
    let edited = if let Some((s, e)) = find_toml_section_span(&text, "[mcp_servers.whitemagic]") {
        let mut out = String::with_capacity(text.len() + section.len());
        out.push_str(&text[..s]);
        out.push_str(&section);
        if e < text.len() && !section.ends_with("\n\n") && !text[e..].starts_with('\n') {
            out.push('\n');
        }
        out.push_str(&text[e..]);
        out
    } else if text.is_empty() {
        section
    } else if text.ends_with("\n\n") {
        format!("{text}{section}")
    } else if text.ends_with('\n') {
        format!("{text}\n{section}")
    } else {
        format!("{text}\n\n{section}")
    };

    if !verify_codex_toml_entry(&edited, exe, store_path, readonly)? {
        return Err("internal error: generated TOML section failed verification".to_string());
    }

    let backup = if existing {
        Some(create_backup(&spec.config_path)?)
    } else {
        ensure_parent(&spec.config_path)?;
        None
    };
    std::fs::write(&spec.config_path, &edited)
        .map_err(|e| format!("write {} failed: {e}", spec.config_path.display()))?;
    let verify =
        std::fs::read_to_string(&spec.config_path).map_err(|e| format!("read-back failed: {e}"))?;
    if !verify_codex_toml_entry(&verify, exe, store_path, readonly)? {
        return Err("written Codex TOML failed read-back verification".to_string());
    }

    let verb = if existing { "updated" } else { "created" };
    Ok((format!("{verb} {}", spec.config_path.display()), backup))
}

fn remove_client(spec: &ClientSpec) -> Result<(String, Option<PathBuf>), String> {
    if !spec.config_path.exists() {
        return Ok(("not configured".to_string(), None));
    }
    match spec.kind {
        ConfigKind::McpServersJson => {
            let text = std::fs::read_to_string(&spec.config_path)
                .map_err(|e| format!("read failed: {e}"))?;
            let mut config: Value =
                serde_json::from_str(&text).map_err(|e| format!("existing JSON invalid: {e}"))?;
            let Some(servers) = config.get_mut("mcpServers").and_then(Value::as_object_mut) else {
                return Ok(("not configured".to_string(), None));
            };
            if servers.remove("whitemagic").is_none() {
                return Ok(("not configured".to_string(), None));
            }
            let rendered = serde_json::to_string_pretty(&config)
                .map_err(|e| format!("JSON serialize failed: {e}"))?;
            let backup = create_backup(&spec.config_path)?;
            std::fs::write(&spec.config_path, format!("{rendered}\n"))
                .map_err(|e| format!("write failed: {e}"))?;
            let verify = std::fs::read_to_string(&spec.config_path)
                .map_err(|e| format!("read-back failed: {e}"))?;
            serde_json::from_str::<Value>(&verify)
                .map_err(|e| format!("written JSON invalid: {e}"))?;
            Ok((
                format!("removed from {}", spec.config_path.display()),
                Some(backup),
            ))
        }
        ConfigKind::OpencodeJsonc => {
            let text = std::fs::read_to_string(&spec.config_path)
                .map_err(|e| format!("read failed: {e}"))?;
            let mut merged = parse_jsonc(&text)?;
            let present = merged
                .get_mut("mcp")
                .and_then(Value::as_object_mut)
                .and_then(|mcp| mcp.remove("whitemagic"))
                .is_some();
            if !present {
                return Ok(("not configured".to_string(), None));
            }
            let edited = if has_comments(&text) {
                jsonc_remove_whitemagic(&text)?
                    .ok_or_else(|| "internal error: entry missing in JSONC".to_string())?
            } else {
                let pretty = serde_json::to_string_pretty(&merged)
                    .map_err(|e| format!("JSON serialize failed: {e}"))?;
                format!("{pretty}\n")
            };
            let backup = create_backup(&spec.config_path)?;
            std::fs::write(&spec.config_path, &edited).map_err(|e| format!("write failed: {e}"))?;
            let verify = std::fs::read_to_string(&spec.config_path)
                .map_err(|e| format!("read-back failed: {e}"))?;
            parse_jsonc(&verify)?;
            Ok((
                format!("removed from {}", spec.config_path.display()),
                Some(backup),
            ))
        }
        ConfigKind::CodexToml => {
            let text = std::fs::read_to_string(&spec.config_path)
                .map_err(|e| format!("read failed: {e}"))?;
            let Some((s, e)) = find_toml_section_span(&text, "[mcp_servers.whitemagic]") else {
                return Ok(("not configured".to_string(), None));
            };
            let mut edited = String::with_capacity(text.len());
            edited.push_str(text[..s].trim_end_matches('\n'));
            if !edited.is_empty() && e < text.len() {
                edited.push_str("\n\n");
            } else if !edited.is_empty() {
                edited.push('\n');
            }
            edited.push_str(text[e..].trim_start_matches('\n'));
            let backup = create_backup(&spec.config_path)?;
            std::fs::write(&spec.config_path, &edited).map_err(|e| format!("write failed: {e}"))?;
            Ok((
                format!("removed from {}", spec.config_path.display()),
                Some(backup),
            ))
        }
    }
}

fn entry_matches(spec: &ClientSpec, exe: &Path, store_path: &Path, readonly: bool) -> bool {
    let Ok(text) = std::fs::read_to_string(&spec.config_path) else {
        return false;
    };
    match spec.kind {
        ConfigKind::McpServersJson => serde_json::from_str::<Value>(&text).is_ok_and(|v| {
            v["mcpServers"]["whitemagic"] == mcp_servers_entry(exe, store_path, readonly)
        }),
        ConfigKind::OpencodeJsonc => parse_jsonc(&text)
            .is_ok_and(|v| v["mcp"]["whitemagic"] == opencode_entry(exe, store_path, readonly)),
        ConfigKind::CodexToml => {
            verify_codex_toml_entry(&text, exe, store_path, readonly).unwrap_or(false)
        }
    }
}

fn has_active_writable_whitemagic_server(spec: &ClientSpec) -> bool {
    let Ok(raw) = std::fs::read_to_string(&spec.config_path) else {
        return false;
    };
    let fragment = match spec.kind {
        ConfigKind::McpServersJson => serde_json::from_str::<Value>(&raw)
            .ok()
            .and_then(|v| {
                v.get("mcpServers")
                    .and_then(|m| m.get("whitemagic"))
                    .cloned()
            })
            .and_then(|v| serde_json::to_string(&v).ok()),
        ConfigKind::OpencodeJsonc => parse_jsonc(&raw)
            .ok()
            .and_then(|v| v.get("mcp").and_then(|m| m.get("whitemagic")).cloned())
            .and_then(|v| serde_json::to_string(&v).ok()),
        ConfigKind::CodexToml => find_toml_section_span(&raw, "[mcp_servers.whitemagic]")
            .map(|(s, e)| raw[s..e].to_string()),
    };
    let Some(frag) = fragment else {
        return false;
    };
    let low = frag.to_ascii_lowercase();
    low.contains("serve")
        && !low.contains("--readonly")
        && !low.contains("enabled = false")
        && !low.contains("\"enabled\": false")
        && !low.contains("\"enabled\":false")
}

fn count_existing_writable_clients(home: Option<&Path>, exclude_id: &str) -> usize {
    specs_in(home)
        .into_iter()
        .filter(|s| s.id != exclude_id && has_active_writable_whitemagic_server(s))
        .count()
}

/// Run `wm setup` (dry-run proposal by default; `--write` creates backups & verifies parse-back).
pub fn run_setup(
    store_path: &Path,
    client_filter: Option<&str>,
    write_mode: bool,
    readonly_flag: bool,
    remove_mode: bool,
    json_mode: bool,
) -> Result<SetupReport, String> {
    let exe = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("wm"));
    let abs_store = std::fs::canonicalize(store_path).unwrap_or_else(|_| store_path.to_path_buf());
    run_setup_with_home(
        &abs_store,
        &exe,
        None,
        client_filter,
        write_mode,
        readonly_flag,
        remove_mode,
        json_mode,
    )
}

/// Testable core with explicit `home` and `exe`.
#[allow(clippy::too_many_arguments)]
pub fn run_setup_with_home(
    store_path: &Path,
    exe: &Path,
    home: Option<&Path>,
    client_filter: Option<&str>,
    write_mode: bool,
    readonly_flag: bool,
    remove_mode: bool,
    json_mode: bool,
) -> Result<SetupReport, String> {
    let targets: Vec<ClientSpec> = if let Some(cid) = client_filter {
        let spec = find_in(home, cid).ok_or_else(|| {
            format!(
                "unknown client '{cid}' (supported: opencode, claude, claude-desktop, cursor, windsurf, codex, antigravity)"
            )
        })?;
        vec![spec]
    } else {
        specs_in(home)
            .into_iter()
            .filter(|s| installed_in(home, s))
            .collect()
    };

    let mut outcomes = Vec::new();
    let mut writable_assigned = false;

    for spec in targets {
        if remove_mode {
            let (action, backup) = if write_mode {
                remove_client(&spec)?
            } else if spec.config_path.exists() {
                (
                    format!("would remove entry from {}", spec.config_path.display()),
                    None,
                )
            } else {
                ("not configured".to_string(), None)
            };
            outcomes.push(SetupOutcome {
                id: spec.id.to_string(),
                label: spec.label.to_string(),
                config_path: spec.config_path.display().to_string(),
                action,
                readonly: readonly_flag,
                backup_path: backup.map(|b| b.display().to_string()),
            });
            continue;
        }

        // Single-writer LMDB law: at most one configured client runs writable unless overridden.
        let other_writable = count_existing_writable_clients(home, spec.id) > 0;
        let use_readonly = readonly_flag || writable_assigned || other_writable;
        if !use_readonly {
            writable_assigned = true;
        }

        let (action, backup) = if entry_matches(&spec, exe, store_path, use_readonly) {
            ("already configured".to_string(), None)
        } else if !write_mode {
            (
                format!(
                    "would write {} (use --write to apply)",
                    spec.config_path.display()
                ),
                None,
            )
        } else {
            match spec.kind {
                ConfigKind::McpServersJson => {
                    write_mcp_servers_json(&spec, exe, store_path, use_readonly)?
                }
                ConfigKind::OpencodeJsonc => {
                    write_opencode_jsonc(&spec, exe, store_path, use_readonly)?
                }
                ConfigKind::CodexToml => write_codex_toml(&spec, exe, store_path, use_readonly)?,
            }
        };

        outcomes.push(SetupOutcome {
            id: spec.id.to_string(),
            label: spec.label.to_string(),
            config_path: spec.config_path.display().to_string(),
            action,
            readonly: use_readonly,
            backup_path: backup.map(|b| b.display().to_string()),
        });
    }

    let report = SetupReport {
        version: env!("CARGO_PKG_VERSION"),
        write_mode,
        remove_mode,
        binary_path: exe.display().to_string(),
        store_path: store_path.display().to_string(),
        outcomes,
    };

    if json_mode {
        let out = serde_json::to_string_pretty(&report)
            .map_err(|e| format!("setup JSON serialization failed: {e}"))?;
        println!("{out}");
    } else {
        println!("==================================================");
        println!("      WhiteMagic Gen3 Client Setup (v{})", report.version);
        println!("==================================================");
        println!("Binary: {}", report.binary_path);
        println!("Store:  {}", report.store_path);
        println!(
            "Mode:   {}",
            if report.remove_mode {
                if report.write_mode {
                    "remove (--write)"
                } else {
                    "remove (dry-run)"
                }
            } else if report.write_mode {
                "write (backup + parse-back verified)"
            } else {
                "dry-run (pass --write to apply)"
            }
        );
        println!("--------------------------------------------------");
        if report.outcomes.is_empty() {
            println!("No supported MCP client directories detected under HOME.");
        }
        for o in &report.outcomes {
            let ro = if o.readonly { " [readonly]" } else { "" };
            println!("  * {:<15}{} : {}", o.label, ro, o.action);
            if let Some(ref bak) = o.backup_path {
                println!("    Backup: {bak}");
            }
        }
        println!("==================================================");
    }

    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn setup_writes_json_jsonc_and_toml_with_comments_backups_and_parse_back() {
        let root = std::env::temp_dir().join(format!("wm-setup-test-{}", uuid::Uuid::new_v4()));
        let home = root.join("home");
        let store = root.join("gen3-store");
        let exe = PathBuf::from("/usr/local/bin/wm3");
        std::fs::create_dir_all(home.join(".cursor")).expect("mkdir cursor");
        std::fs::create_dir_all(home.join(".config/opencode")).expect("mkdir opencode");
        std::fs::create_dir_all(home.join(".codex")).expect("mkdir codex");

        let cursor_path = home.join(".cursor/mcp.json");
        std::fs::write(&cursor_path, r#"{"mcpServers":{"other":{"command":"x"}}}"#)
            .expect("seed cursor");
        let oc_path = home.join(".config/opencode/opencode.jsonc");
        std::fs::write(
            &oc_path,
            "// Keep my top comment\n{\n  \"mcp\": {\n    \"peer\": {\"type\": \"local\", \"command\": [\"echo\"]}\n  }\n}\n",
        )
        .expect("seed opencode");
        let codex_path = home.join(".codex/config.toml");
        std::fs::write(
            &codex_path,
            "# Codex comment stays intact\n[mcp_servers.other]\ncommand = \"other\"\n",
        )
        .expect("seed codex");

        // 1. Dry-run leaves files untouched
        let dry = run_setup_with_home(&store, &exe, Some(&home), None, false, false, false, false)
            .expect("dry run");
        assert!(!dry.outcomes.is_empty());
        assert!(
            !std::fs::read_to_string(&cursor_path)
                .unwrap()
                .contains("whitemagic")
        );

        // 2. Write mode patches all three, creates backups, expands paths, preserves comments & single-writer
        let written =
            run_setup_with_home(&store, &exe, Some(&home), None, true, false, false, false)
                .expect("write run");
        assert!(written.outcomes.iter().all(|o| o.backup_path.is_some()));

        let oc_after = std::fs::read_to_string(&oc_path).unwrap();
        assert!(oc_after.contains("// Keep my top comment"));
        assert!(!oc_after.contains("$HOME"));
        let oc_parsed = parse_jsonc(&oc_after).expect("opencode re-parses");
        assert_eq!(
            oc_parsed["mcp"]["whitemagic"]["command"][0],
            "/usr/local/bin/wm3"
        );
        assert_eq!(oc_parsed["mcp"]["peer"]["command"][0], "echo");

        let codex_after = std::fs::read_to_string(&codex_path).unwrap();
        assert!(codex_after.contains("# Codex comment stays intact"));
        assert!(codex_after.contains("[mcp_servers.other]"));
        assert!(codex_after.contains("[mcp_servers.whitemagic]"));
        assert!(codex_after.contains("--readonly"));

        // 3. Re-running is idempotent (already configured, no extra backups)
        let second =
            run_setup_with_home(&store, &exe, Some(&home), None, true, false, false, false)
                .expect("idempotent run");
        assert!(
            second
                .outcomes
                .iter()
                .all(|o| o.action == "already configured" && o.backup_path.is_none())
        );

        // 4. Collision-safe backup inside same timestamp
        let b1 = create_backup_at(&cursor_path, "20261116180000").expect("bak 1");
        let b2 = create_backup_at(&cursor_path, "20261116180000").expect("bak 2");
        assert_ne!(b1, b2);

        // 5. Remove mode restores cleanliness while preserving comments and siblings
        let removed =
            run_setup_with_home(&store, &exe, Some(&home), None, true, false, true, false)
                .expect("remove run");
        assert!(
            removed
                .outcomes
                .iter()
                .all(|o| o.action.starts_with("removed"))
        );
        let oc_final = std::fs::read_to_string(&oc_path).unwrap();
        assert!(oc_final.contains("// Keep my top comment"));
        assert!(parse_jsonc(&oc_final).unwrap()["mcp"]["whitemagic"].is_null());

        std::fs::remove_dir_all(root).ok();
    }
}
