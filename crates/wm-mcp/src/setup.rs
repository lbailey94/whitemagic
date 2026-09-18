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

/// True when another writable WhiteMagic process (a `wm serve` without
/// `--readonly`, or `wm daemon`) already holds the default store's search
/// writer. A second writable server fails at startup with Tantivy LockBusy;
/// the documented doctrine (`docs/DAEMON_SERVE_COEXISTENCE.md`) is read-only
/// alongside, with writes routed through the holder or the `wm` CLI.
fn store_writer_present() -> bool {
    !crate::store_busy::store_holders(&crate::config::WmConfig::default_store_root()).is_empty()
}

/// Serve args for a new client entry, given whether the store is held.
fn serve_args_for(store_held: bool) -> Vec<&'static str> {
    if store_held {
        vec!["serve", "--profile", "curated", "--readonly"]
    } else {
        vec!["serve", "--profile", "curated"]
    }
}

/// Serve args for this machine: `--readonly` when the store is already held,
/// so the configured entry actually starts.
fn serve_args() -> Vec<&'static str> {
    serve_args_for(store_writer_present())
}

/// Disclosure for `wm connect` / `wm setup` when entries were configured
/// read-only because another server holds the store.
#[must_use]
pub fn read_only_note() -> Option<String> {
    store_writer_present().then(|| {
        format!(
            "a writable wm serve/daemon already holds {} — new client entries are \
             read-only; route writes through that server or the wm CLI",
            crate::config::WmConfig::default_store_root().display()
        )
    })
}

/// Walk up from `start` looking for a `.git` directory or worktree file.
fn git_root_of(start: &std::path::Path) -> Option<std::path::PathBuf> {
    let mut dir = Some(start);
    while let Some(d) = dir {
        if d.join(".git").exists() {
            return Some(d.to_path_buf());
        }
        dir = d.parent();
    }
    None
}

/// True when the repository root carries its own project-scoped whitemagic
/// wiring (so the client-global entries are not the only scope).
fn project_wired(root: &std::path::Path) -> bool {
    [
        root.join("opencode.jsonc"),
        root.join(".opencode").join("opencode.jsonc"),
        root.join(".mcp.json"),
    ]
    .iter()
    .any(|p| std::fs::read_to_string(p).is_ok_and(|t| t.contains("whitemagic")))
}

/// Warning for the easy onboarding path: client-global wiring points every
/// project at the same store, so sessions and memories cross projects silently.
///
/// `wm connect` / `wm setup <client>` call this with the working directory:
/// inside a git repository without project-scoped wiring it names the repo
/// and the remedy. Returns `None` outside a repository and inside one that is
/// already project-wired.
#[must_use]
pub fn project_isolation_note(cwd: &std::path::Path) -> Option<String> {
    let root = git_root_of(cwd)?;
    if project_wired(&root) {
        return None;
    }
    Some(format!(
        "Project detected: {}\n\
         These client entries use the global store ({}), so sessions from every project \
         share it — continuity can return another project's memories. If you work across \
         projects, prefer a project-scoped store: one store per project \
         (see docs/MULTI_PROJECT_MEMORY.md).",
        root.display(),
        crate::config::WmConfig::default_store_root().display()
    ))
}

/// One-line variant of [`project_isolation_note`] for summaries such as
/// `wm grimoire`.
#[must_use]
pub fn project_isolation_short(cwd: &std::path::Path) -> Option<String> {
    project_isolation_note(cwd).map(|_| {
        format!(
            "project detected ({}) — global-store wiring mixes projects; see docs/MULTI_PROJECT_MEMORY.md",
            git_root_of(cwd)
                .map(|r| r.display().to_string())
                .unwrap_or_default()
        )
    })
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
    let mut command = vec![exe.display().to_string()];
    command.extend(serve_args().into_iter().map(str::to_string));
    json!({
        "type": "local",
        "command": command,
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

/// Leading whitespace of the line containing `pos`, regardless of whether
/// anything else appears on that line (used for inline empty objects).
fn line_leading_ws(text: &str, pos: usize) -> String {
    let start = text[..pos].rfind('\n').map_or(0, |nl| nl + 1);
    text[start..]
        .chars()
        .take_while(|c| *c == ' ' || *c == '\t')
        .collect()
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

    let close_indent = {
        let ind = line_indent(text, close_brace);
        if ind.is_empty() && !text[..close_brace].ends_with('\n') {
            // Inline empty object (`"mcp": {}`): the closing brace shares a
            // line, so take that line's leading whitespace instead of the
            // (non-whitespace) prefix before the brace.
            line_leading_ws(text, close_brace)
        } else {
            ind
        }
    };
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

/// Remove `key` from the object `text[open..close]`, preserving comments
/// elsewhere. Returns `None` when the key is absent.
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
        let value_start = skip_trivia(text, colon + 1);
        let value_end = value_end(text, value_start)?;
        if member_key == key {
            return Some(splice_member_out(text, j, value_end, prev_value_end));
        }
        prev_value_end = Some(value_end);
        j = skip_trivia(text, value_end);
        if bytes.get(j) == Some(&b',') {
            j = skip_trivia(text, j + 1);
        }
    }
    None
}

/// Splice one member out of a JSONC object: the member's own line, plus the
/// comma that binds it to its neighbors (the trailing one when present, the
/// preceding one when the member is last). Comments outside the member span
/// survive.
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
        // Not the last member: the comma and the rest of the line go too.
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
            // Last member: drop the preceding member's trailing comma.
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

/// Structural removal of `mcp.whitemagic` in an OpenCode JSONC document.
/// Returns `None` when the entry is absent; the `mcp` object itself (and
/// any comments) is left in place.
fn jsonc_remove_whitemagic(text: &str) -> anyhow::Result<Option<String>> {
    let root_open = skip_trivia(text, 0);
    if text.as_bytes().get(root_open) != Some(&b'{') {
        anyhow::bail!("config root is not an object");
    }
    let root_close = matching_delim(text, root_open, b'{', b'}')
        .ok_or_else(|| anyhow::anyhow!("unbalanced braces in config"))?;
    let Some((mcp_start, mcp_end)) = find_member(text, root_open, root_close, "mcp") else {
        return Ok(None);
    };
    if text.as_bytes().get(mcp_start) != Some(&b'{') {
        anyhow::bail!("existing \"mcp\" is not an object");
    }
    Ok(remove_member(text, mcp_start, mcp_end, "whitemagic"))
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
    command_ok && args.as_deref() == Some(serve_args().as_slice())
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

/// Remove WhiteMagic's own entry from a client config (`wm setup <client>
/// --remove`) — the reversible counterpart of [`write`].
///
/// Only the `whitemagic` member is removed: unrelated servers, settings,
/// and comments survive, and a timestamped backup is written before any
/// change. A config that is not wired returns "not configured" without
/// touching the file.
///
/// # Errors
/// Any IO or parse failure; the original file is never modified on error.
pub fn remove(spec: &ClientSpec) -> anyhow::Result<(String, Option<PathBuf>)> {
    match spec.kind {
        Kind::McpServersJson => remove_mcp_servers_json(spec),
        Kind::OpencodeJsonc => remove_opencode_jsonc(spec),
        Kind::CodexToml => remove_codex_toml(spec),
    }
}

fn backup_and_write(spec: &ClientSpec, text: &str) -> anyhow::Result<PathBuf> {
    let backup = backup_path(&spec.config_path);
    std::fs::copy(&spec.config_path, &backup)?;
    std::fs::write(&spec.config_path, text)?;
    Ok(backup)
}

fn remove_mcp_servers_json(spec: &ClientSpec) -> anyhow::Result<(String, Option<PathBuf>)> {
    let text = std::fs::read_to_string(&spec.config_path)?;
    let mut config: Value = serde_json::from_str(&text).map_err(|e| {
        anyhow::anyhow!(
            "existing config is not valid JSON ({}): {e}",
            spec.config_path.display()
        )
    })?;
    let Some(servers) = config.get_mut("mcpServers").and_then(Value::as_object_mut) else {
        return Ok(("not configured".to_string(), None));
    };
    if servers.remove("whitemagic").is_none() {
        return Ok(("not configured".to_string(), None));
    }
    let rendered = format!("{}\n", serde_json::to_string_pretty(&config)?);
    let backup = backup_and_write(spec, &rendered)?;
    let verify = std::fs::read_to_string(&spec.config_path)?;
    serde_json::from_str::<Value>(&verify)
        .map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;
    Ok((
        format!("removed from {}", spec.config_path.display()),
        Some(backup),
    ))
}

fn remove_opencode_jsonc(spec: &ClientSpec) -> anyhow::Result<(String, Option<PathBuf>)> {
    let text = std::fs::read_to_string(&spec.config_path)?;
    let parsed = parse_jsonc(&text).map_err(|e| {
        anyhow::anyhow!(
            "existing config is not valid JSONC ({}): {e}",
            spec.config_path.display()
        )
    })?;
    let mut merged = parsed;
    let present = merged
        .get_mut("mcp")
        .and_then(Value::as_object_mut)
        .and_then(|mcp| mcp.remove("whitemagic"))
        .is_some();
    if !present {
        return Ok(("not configured".to_string(), None));
    }
    let edited = if has_comments(&text) {
        jsonc_remove_whitemagic(&text)?.ok_or_else(|| {
            anyhow::anyhow!("internal error: entry present but not found structurally")
        })?
    } else {
        format!("{}\n", serde_json::to_string_pretty(&merged)?)
    };
    let check = parse_jsonc(&edited)
        .map_err(|e| anyhow::anyhow!("internal error: edited JSONC does not parse: {e}"))?;
    if check != merged {
        anyhow::bail!("internal error: edited JSONC does not round-trip to the intended value");
    }
    let backup = backup_and_write(spec, &edited)?;
    let verify = std::fs::read_to_string(&spec.config_path)?;
    parse_jsonc(&verify).map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;
    Ok((
        format!("removed from {}", spec.config_path.display()),
        Some(backup),
    ))
}

fn remove_codex_toml(spec: &ClientSpec) -> anyhow::Result<(String, Option<PathBuf>)> {
    let text = std::fs::read_to_string(&spec.config_path)?;
    let mut doc: toml_edit::DocumentMut = text.parse().map_err(|e| {
        anyhow::anyhow!(
            "existing config is not valid TOML ({}): {e}",
            spec.config_path.display()
        )
    })?;
    let Some(servers) = doc
        .get_mut("mcp_servers")
        .and_then(toml_edit::Item::as_table_mut)
    else {
        return Ok(("not configured".to_string(), None));
    };
    if servers.remove("whitemagic").is_none() {
        return Ok(("not configured".to_string(), None));
    }
    let rendered = doc.to_string();
    toml::from_str::<toml::Value>(&rendered)
        .map_err(|e| anyhow::anyhow!("written config failed validation: {e}"))?;
    let backup = backup_and_write(spec, &rendered)?;
    Ok((
        format!("removed from {}", spec.config_path.display()),
        Some(backup),
    ))
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

/// True when the client's whitemagic entry is exactly what this binary would
/// write right now — args included.
///
/// `configured` alone only proves the text mentions whitemagic; it cannot see
/// a stale `--readonly` (written while another writer held the store) or an
/// old binary path. `connect` reconciles on this predicate so a client that
/// was wired read-only becomes writable again once the holder stops, and an
/// entry that is already current never grows a backup.
#[must_use]
pub fn entry_matches(spec: &ClientSpec, exe: &Path) -> bool {
    match spec.kind {
        Kind::McpServersJson => std::fs::read_to_string(&spec.config_path)
            .ok()
            .and_then(|t| serde_json::from_str::<Value>(&t).ok())
            .is_some_and(|v| v["mcpServers"]["whitemagic"] == entry(exe)),
        Kind::OpencodeJsonc => std::fs::read_to_string(&spec.config_path)
            .ok()
            .and_then(|t| parse_jsonc(&t).ok())
            .is_some_and(|v| v["mcp"]["whitemagic"] == opencode_entry(exe)),
        Kind::CodexToml => std::fs::read_to_string(&spec.config_path)
            .ok()
            .and_then(|t| t.parse::<toml_edit::DocumentMut>().ok())
            .and_then(|doc| {
                doc.get("mcp_servers")
                    .and_then(|servers| servers.get("whitemagic"))
                    .map(|item| codex_entry_matches(item, exe))
            })
            .unwrap_or(false),
    }
}

/// Wire every detected client, reconciling entries that drifted.
///
/// A client whose entry already matches this binary exactly is left alone;
/// a client that references whitemagic with a stale entry (for example a
/// `--readonly` written while another writer held the store, or an old
/// binary path) is rewritten to the current entry — the comparison is at
/// entry level, not `text.contains("whitemagic")`.
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
            if entry_matches(spec, exe) {
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

/// End-to-end connection proof: spawn `binary serve --profile curated` in a
/// throwaway HOME and perform a real MCP handshake (`initialize` →
/// `tools/list`).
///
/// Returns the exposed tool count. The isolated HOME means the check can
/// never create or mutate the user's store.
pub fn verify_mcp_session(binary: &Path) -> Result<usize, String> {
    use std::io::{BufRead, BufReader};
    use std::process::{Command, Stdio};
    use std::sync::mpsc;
    use std::thread;

    let home = tempfile::tempdir().map_err(|e| format!("temp home: {e}"))?;
    let mut child = Command::new(binary)
        .args(["serve", "--profile", "curated"])
        .env("HOME", home.path())
        .env("XDG_DATA_HOME", home.path().join(".local/share"))
        .env("XDG_CONFIG_HOME", home.path().join(".config"))
        .env("RUST_LOG", "error")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("spawn {}: {e}", binary.display()))?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "no stdout pipe".to_string())?;
    let (tx, rx) = mpsc::channel::<String>();
    let reader = thread::spawn(move || {
        for line in BufReader::new(stdout).lines() {
            let Ok(line) = line else { break };
            if tx.send(line).is_err() {
                break;
            }
        }
    });

    let session = run_session(&mut child, &rx);

    let _ = child.kill();
    let _ = child.wait();
    let _ = reader.join();
    session
}

/// Drive the handshake on a spawned server; split out so `child` stays a
/// plain `&mut` (a captured closure cannot move `stdin` out of it).
fn run_session(
    child: &mut std::process::Child,
    rx: &std::sync::mpsc::Receiver<String>,
) -> Result<usize, String> {
    use std::io::Write;
    use std::time::Duration;

    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| "no stdin pipe".to_string())?;
    let init = json!({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "wm-connect-verify", "version": env!("CARGO_PKG_VERSION")}
        }
    });
    writeln!(stdin, "{init}").map_err(|e| format!("initialize write: {e}"))?;
    stdin
        .flush()
        .map_err(|e| format!("initialize flush: {e}"))?;
    wait_for_id(rx, 1, Duration::from_secs(10))?;

    writeln!(
        stdin,
        r#"{{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{{}}}}"#
    )
    .map_err(|e| format!("tools/list write: {e}"))?;
    stdin
        .flush()
        .map_err(|e| format!("tools/list flush: {e}"))?;
    let line = wait_for_id(rx, 2, Duration::from_secs(10))?;
    let value: Value = serde_json::from_str(&line).map_err(|e| format!("tools/list parse: {e}"))?;
    let count = value["result"]["tools"].as_array().map_or(0, Vec::len);
    if count == 0 {
        return Err(format!(
            "handshake succeeded but tools/list was empty: {value}"
        ));
    }
    Ok(count)
}

/// Wait for a JSON-RPC line carrying `id`, skipping log noise and
/// notifications; bounded so a wedged server cannot hang the caller.
fn wait_for_id(
    rx: &std::sync::mpsc::Receiver<String>,
    id: u64,
    timeout: std::time::Duration,
) -> Result<String, String> {
    let deadline = std::time::Instant::now() + timeout;
    loop {
        let remaining = deadline.saturating_duration_since(std::time::Instant::now());
        if remaining.is_zero() {
            return Err(format!("timed out waiting for response id {id}"));
        }
        let line = rx
            .recv_timeout(remaining)
            .map_err(|_| format!("timed out waiting for response id {id}"))?;
        if let Ok(value) = serde_json::from_str::<Value>(&line) {
            if value.get("id").and_then(Value::as_u64) == Some(id) {
                return Ok(line);
            }
        }
    }
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
    fn held_store_switches_serve_args_to_readonly() {
        assert_eq!(
            serve_args_for(false),
            ["serve", "--profile", "curated"],
            "a free store gets a writable server"
        );
        assert_eq!(
            serve_args_for(true),
            ["serve", "--profile", "curated", "--readonly"],
            "a held store gets a read-only server so the entry can start"
        );

        // The generated entries reflect whichever mode this machine is in and
        // must stay parseable in both.
        let exe = Path::new("/opt/wm");
        let entry_args = entry(exe);
        let args = entry_args["args"].as_array().unwrap();
        assert_eq!(args[0], "serve");
        assert!(args.iter().any(|a| a == "--profile"));
        if store_writer_present() {
            assert!(args.iter().any(|a| a == "--readonly"));
        }
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

    /// The review-round-2 bug: `connect` used `text.contains("whitemagic")`,
    /// so an entry wired `--readonly` while another writer held the store
    /// was reported "already configured" forever. Reconciliation is now at
    /// entry level for all three client shapes.
    #[test]
    fn connect_reconciles_stale_entries_at_entry_level() {
        let tmp = tempfile::tempdir().unwrap();
        let exe = Path::new("/opt/wm");

        let json_path = tmp.path().join("cursor/mcp.json");
        std::fs::create_dir_all(json_path.parent().unwrap()).unwrap();
        let mut stale_json = entry(exe);
        stale_json["args"]
            .as_array_mut()
            .unwrap()
            .push(json!("--readonly"));
        std::fs::write(
            &json_path,
            serde_json::json!({"mcpServers": {"whitemagic": stale_json}}).to_string(),
        )
        .unwrap();
        let json_spec = spec(Kind::McpServersJson, json_path.clone());

        let jsonc_path = tmp.path().join("opencode.jsonc");
        let mut stale_jsonc = opencode_entry(exe);
        stale_jsonc["command"]
            .as_array_mut()
            .unwrap()
            .push(json!("--readonly"));
        std::fs::write(
            &jsonc_path,
            serde_json::json!({"mcp": {"whitemagic": stale_jsonc}}).to_string(),
        )
        .unwrap();
        let jsonc_spec = spec(Kind::OpencodeJsonc, jsonc_path);

        let toml_path = tmp.path().join("codex/config.toml");
        std::fs::create_dir_all(toml_path.parent().unwrap()).unwrap();
        std::fs::write(
            &toml_path,
            "[mcp_servers.whitemagic]\ncommand = \"/opt/wm\"\n\
             args = [\"serve\", \"--profile\", \"curated\", \"--marker\"]\n",
        )
        .unwrap();
        let toml_spec = spec(Kind::CodexToml, toml_path);

        let list = vec![json_spec.clone(), jsonc_spec.clone(), toml_spec.clone()];

        // Dry run proposes the reconciliation and changes nothing.
        let dry = connect_with(&list, exe, false);
        assert!(
            dry.iter()
                .all(|o| matches!(o.action, ConnectAction::Proposed)),
            "{dry:?}"
        );
        assert!(
            std::fs::read_to_string(&json_path)
                .unwrap()
                .contains("--readonly")
        );

        // Apply rewrites every entry to the current shape, with backups.
        let applied = connect_with(&list, exe, true);
        assert!(
            applied
                .iter()
                .all(|o| matches!(o.action, ConnectAction::Written)),
            "{applied:?}"
        );
        assert!(
            applied
                .iter()
                .all(|o| o.backup.as_ref().is_some_and(|b| b.exists()))
        );
        assert!(entry_matches(&json_spec, exe));
        assert!(entry_matches(&jsonc_spec, exe));
        assert!(entry_matches(&toml_spec, exe));

        // Second pass: exact entries are left alone, no backup spam.
        let again = connect_with(&list, exe, false);
        assert!(
            again
                .iter()
                .all(|o| matches!(o.action, ConnectAction::Configured)),
            "{again:?}"
        );
    }

    #[test]
    fn project_isolation_note_fires_only_for_unwired_repos() {
        let tmp = tempfile::tempdir().unwrap();

        // Outside a repository: nothing to warn about.
        assert!(project_isolation_note(tmp.path()).is_none());

        // A repository without project-scoped wiring gets the warning.
        let repo = tmp.path().join("repo");
        std::fs::create_dir_all(repo.join(".git")).unwrap();
        let note = project_isolation_note(&repo).expect("unwired repo must warn");
        assert!(note.contains("project-scoped store"), "{note}");
        assert!(note.contains("MULTI_PROJECT_MEMORY"), "{note}");

        // Nested directories resolve to the repository root.
        let nested = repo.join("crates/deep");
        std::fs::create_dir_all(&nested).unwrap();
        assert!(project_isolation_note(&nested).is_some());

        // A project-wired repo is left alone (opencode.jsonc names whitemagic).
        std::fs::write(repo.join("opencode.jsonc"), r#"{"mcp":{"whitemagic":{}}}"#).unwrap();
        assert!(project_isolation_note(&repo).is_none());
    }

    #[test]
    fn remove_strips_only_whitemagic_entry() {
        let tmp = tempfile::tempdir().unwrap();
        let exe = Path::new("/opt/wm");

        // JSON: sibling server survives.
        let json_path = tmp.path().join("mcp.json");
        let mut wired = entry(exe);
        wired["args"]
            .as_array_mut()
            .unwrap()
            .push(json!("--marker"));
        std::fs::write(
            &json_path,
            serde_json::json!({
                "mcpServers": {"whitemagic": wired, "other": {"command": "x"}}
            })
            .to_string(),
        )
        .unwrap();
        let json_spec = spec(Kind::McpServersJson, json_path.clone());
        let (msg, backup) = remove(&json_spec).unwrap();
        assert!(msg.contains("removed from"), "{msg}");
        assert!(backup.unwrap().exists(), "removal takes a backup");
        let v: Value = serde_json::from_str(&std::fs::read_to_string(&json_path).unwrap()).unwrap();
        assert!(v["mcpServers"].get("whitemagic").is_none());
        assert_eq!(v["mcpServers"]["other"]["command"], "x");
        assert_eq!(remove(&json_spec).unwrap().0, "not configured");

        // JSONC with comments: sibling member and comments survive.
        let jsonc_path = tmp.path().join("opencode.jsonc");
        std::fs::write(
            &jsonc_path,
            "{\n  // editor\n  \"mcp\": {\n    \"other\": { \"type\": \"local\" },\n    \
             \"whitemagic\": { \"type\": \"local\", \"command\": [\"/opt/wm\", \"serve\"] }\n  },\n  \
             \"theme\": \"dark\"\n}\n",
        )
        .unwrap();
        let jsonc_spec = spec(Kind::OpencodeJsonc, jsonc_path.clone());
        let (msg, backup) = remove(&jsonc_spec).unwrap();
        assert!(msg.contains("removed from"), "{msg}");
        assert!(backup.unwrap().exists());
        let text = std::fs::read_to_string(&jsonc_path).unwrap();
        assert!(!text.contains("whitemagic"), "{text}");
        assert!(text.contains("// editor"), "{text}");
        assert!(text.contains("\"other\""), "{text}");
        assert!(text.contains("theme"), "{text}");
        let parsed = parse_jsonc(&text).unwrap();
        assert_eq!(parsed["theme"], "dark");
        assert_eq!(parsed["mcp"]["other"]["type"], "local");
        assert_eq!(remove(&jsonc_spec).unwrap().0, "not configured");

        // TOML: unrelated settings and comments survive.
        let toml_path = tmp.path().join("config.toml");
        std::fs::write(
            &toml_path,
            "# codex\nmodel = \"o3\"\n\n[mcp_servers.whitemagic]\ncommand = \"/opt/wm\"\n\
             \n[mcp_servers.other]\ncommand = \"x\"\n",
        )
        .unwrap();
        let toml_spec = spec(Kind::CodexToml, toml_path.clone());
        let (msg, backup) = remove(&toml_spec).unwrap();
        assert!(msg.contains("removed from"), "{msg}");
        assert!(backup.unwrap().exists());
        let text = std::fs::read_to_string(&toml_path).unwrap();
        assert!(!text.contains("whitemagic"), "{text}");
        assert!(text.contains("# codex"), "{text}");
        assert!(text.contains("model = \"o3\""), "{text}");
        assert!(text.contains("[mcp_servers.other]"), "{text}");
        assert_eq!(remove(&toml_spec).unwrap().0, "not configured");
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
    fn jsonc_insert_into_an_empty_mcp_object_is_cleanly_indented() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("opencode.jsonc");
        let original = "\
{
  // keep me
  \"mcp\": {}
}
";
        std::fs::write(&path, original).unwrap();
        let spec = spec(Kind::OpencodeJsonc, path.clone());
        write_opencode_jsonc(&spec, Path::new("/opt/wm")).unwrap();

        let edited = std::fs::read_to_string(&path).unwrap();
        assert!(edited.contains("// keep me"), "comment lost: {edited}");
        assert!(
            edited.contains("\n    \"whitemagic\""),
            "member should be indented under mcp: {edited}"
        );
        assert!(
            edited.contains("\n  }\n}"),
            "mcp closing brace should keep its indent: {edited}"
        );
        let v = parse_jsonc(&edited).unwrap();
        assert_eq!(v["mcp"]["whitemagic"]["command"][0], "/opt/wm");
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
