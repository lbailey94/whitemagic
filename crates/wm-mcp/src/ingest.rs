//! Knowledge-vault ingestion.
//!
//! Harvests documents and session transcripts from a directory tree into a
//! dedicated store with a resumable ledger. Design decisions are documented
//! in `planning/SESSION_Knowledge_Ingest.md`:
//!
//! - raw sources stay in archives; memories are derived indexes with
//!   provenance tags (`source:...`, `ingest:v1`, `kind:...`);
//! - idempotent: per-file SHA-256 in `ingest_ledger.jsonl`; re-runs are
//!   no-ops for unchanged files, and changed files replace their chunks
//!   (deterministic UUIDv5 chunk ids derived from file hash + index);
//! - fail-loud: unreadable or oversized files are reported with reasons,
//!   never swallowed silently;
//! - credential-shaped files (`.env*`, keys, certs) are never ingested;
//! - one store per ingest run — callers should target the vault store, not
//!   a project store.

use std::collections::BTreeMap;
use std::fs;
use std::io::{BufRead, BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use uuid::Uuid;
use wm_core::Galaxy;
use wm_memory::{Memory, MemoryStore, SearchEngine};

// ── Harvest configuration ────────────────────────────────────────────

/// Directory names never descended into.
pub const EXCLUDED_DIR_NAMES: &[&str] = &[
    ".git",
    "node_modules",
    "target",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    "dist",
    "build",
    ".vercel",
    ".ruff_cache",
    ".pytest_cache",
    ".fragment",
    ".cargo",
    "lmdb",
    "tantivy",
    "models",
    ".windsurf",
    ".vscode",
    ".idea",
    ".codeium",
    ".strata-cache",
    ".fastembed_cache",
];

/// Extensions we ingest (lowercase, no dot).
pub const TEXT_EXTENSIONS: &[&str] = &["md", "markdown", "txt", "jsonl", "ndjson", "llms"];

/// Extensions skipped without reading (binary or deferred formats).
const SKIP_EXTENSIONS: &[&str] = &[
    "db",
    "sqlite",
    "sqlite3",
    "bin",
    "exe",
    "dll",
    "so",
    "dylib",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "ico",
    "svg",
    "bmp",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
    "mp3",
    "wav",
    "flac",
    "ogg",
    "zip",
    "gz",
    "tar",
    "tgz",
    "zst",
    "7z",
    "rar",
    "xz",
    "bz2",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "onnx",
    "gguf",
    "safetensors",
    "pt",
    "pth",
    "whl",
    "wasm",
    "woff",
    "woff2",
    "ttf",
    "otf",
    "eot",
    "jar",
    "class",
    "o",
    "a",
    "rlib",
    "pyc",
    "pyo",
    "pb",
    "lock",
    "log",
];

/// Files whose names mark them as credential-bearing and never ingested.
const CREDENTIAL_NAME_HINTS: &[&str] = &[
    ".env",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "credentials",
    "secrets",
    "password",
    "passwd",
    "token",
];

/// Per-file max size; larger files are skipped with a reason.
const MAX_FILE_BYTES: u64 = 64 * 1024 * 1024;

/// Chunk sizing (characters, not tokens — conservative ~4 chars/token).
const MAX_CHUNK_CHARS: usize = 4_000;
const MIN_PARAGRAPH_CHARS: usize = 256;
const MAX_SINGLE_PARAGRAPH_CHARS: usize = 8_000;

const INGEST_VERSION: &str = "v1";

// ── Source classification ────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SourceKind {
    /// Markdown / plain documentation — chunked at headings and paragraphs.
    Markdown,
    /// Session transcript JSONL (Claude Code, Codex CLI rollout) — chunked
    /// at message boundaries, roles preserved.
    Transcript,
    /// Plain text — paragraph chunking.
    PlainText,
}

impl SourceKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Markdown => "markdown",
            Self::Transcript => "transcript",
            Self::PlainText => "text",
        }
    }
}

/// Detect the source kind from extension + first bytes.
#[must_use]
pub fn detect_kind(path: &Path, head: &str) -> Option<SourceKind> {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or_default()
        .to_lowercase();
    match ext.as_str() {
        "md" | "markdown" | "llms" => Some(SourceKind::Markdown),
        "txt" => Some(SourceKind::PlainText),
        "jsonl" | "ndjson" => {
            let first = head.trim_start();
            if first.starts_with('{') {
                Some(SourceKind::Transcript)
            } else {
                None
            }
        }
        _ => None,
    }
}

/// Heuristic credential-file detection by name (never by content).
#[must_use]
pub fn is_credential_file(name: &str) -> bool {
    let lower = name.to_lowercase();
    CREDENTIAL_NAME_HINTS
        .iter()
        .any(|hint| lower.contains(hint))
}

/// Cheap content check for private-key material. Files containing PEM
/// blocks are skipped — the store must never hold credentials.
#[must_use]
pub fn contains_private_key(text: &str) -> bool {
    text.contains("BEGIN PRIVATE KEY")
        || text.contains("BEGIN RSA PRIVATE KEY")
        || text.contains("BEGIN OPENSSH PRIVATE KEY")
        || text.contains("BEGIN EC PRIVATE KEY")
}

// ── Chunking ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chunk {
    pub content: String,
    pub seq: usize,
    pub role: Option<String>,
}

/// Extract the human-readable text from one transcript JSON line.
fn transcript_line_text(line: &str) -> Option<(String, Option<String>)> {
    let v: serde_json::Value = serde_json::from_str(line).ok()?;
    let role = v
        .get("type")
        .and_then(|t| t.as_str())
        .filter(|t| *t == "user" || *t == "assistant")
        .map(str::to_string);

    // Claude Code style: {"type":"user","message":{"role":"user","content":...}}
    if let Some(content) = v.get("message").and_then(|m| m.get("content")) {
        if let Some(text) = json_content_to_text(content) {
            return Some((text, role));
        }
    }
    // Codex CLI rollout style: {"type":"response_item","payload":{...}}
    if let Some(payload) = v.get("payload") {
        for key in ["content", "text", "output", "message"] {
            if let Some(content) = payload.get(key) {
                if let Some(text) = json_content_to_text(content) {
                    return Some((text, role));
                }
            }
        }
    }
    // Bare transcripts: {"role":"user","content":"..."}
    if let Some(content) = v.get("content") {
        if let Some(text) = json_content_to_text(content) {
            return Some((text, role));
        }
    }
    None
}

/// Convert a JSON content value (string or message-block array) to text.
fn json_content_to_text(content: &serde_json::Value) -> Option<String> {
    match content {
        serde_json::Value::String(s) => {
            let t = s.trim();
            if t.is_empty() {
                None
            } else {
                Some(t.to_string())
            }
        }
        serde_json::Value::Array(blocks) => {
            let mut parts = Vec::new();
            for block in blocks {
                if let Some(text) = block.get("text").and_then(|t| t.as_str()) {
                    let t = text.trim();
                    if !t.is_empty() {
                        parts.push(t.to_string());
                    }
                }
            }
            if parts.is_empty() {
                None
            } else {
                Some(parts.join("\n"))
            }
        }
        _ => None,
    }
}

/// Truncate an over-long unit with a visible marker (mirrors the v26
/// 50k/2k flattening caps, applied per unit instead of per file).
fn cap_unit(text: &str, cap: usize) -> String {
    if text.len() <= cap {
        text.to_string()
    } else {
        let end = (0..=cap)
            .rev()
            .find(|&i| text.is_char_boundary(i))
            .unwrap_or(0);
        let mut out = String::with_capacity(end + 64);
        out.push_str(&text[..end]);
        out.push_str("\n\n[... truncated ...]");
        out
    }
}

/// Merge small paragraphs into the current chunk until the cap is hit.
fn pack_units(units: Vec<String>) -> Vec<String> {
    let mut chunks: Vec<String> = Vec::new();
    let mut current = String::new();
    for unit in units {
        if !current.is_empty() && current.len() + unit.len() + 2 > MAX_CHUNK_CHARS {
            chunks.push(std::mem::take(&mut current));
        }
        if !current.is_empty() {
            current.push_str("\n\n");
        }
        current.push_str(&unit);
    }
    if !current.is_empty() {
        chunks.push(current);
    }
    chunks
}

/// Paragraph split that keeps short paragraphs merged into their
/// neighbors (avoids 340k one-liner chunks).
fn split_paragraphs(text: &str) -> Vec<String> {
    let mut units: Vec<String> = Vec::new();
    let mut pending_small: Vec<String> = Vec::new();

    for raw in text.split("\n\n") {
        let para = raw.trim();
        if para.is_empty() {
            continue;
        }
        if para.len() < MIN_PARAGRAPH_CHARS {
            pending_small.push(para.to_string());
        } else {
            let mut merged = String::new();
            let drained = std::mem::take(&mut pending_small);
            for small in drained {
                if !merged.is_empty() {
                    merged.push_str("\n\n");
                }
                merged.push_str(&small);
            }
            if !merged.is_empty() {
                merged.push_str("\n\n");
            }
            merged.push_str(para);
            units.push(merged);
        }
    }
    if !pending_small.is_empty() {
        units.push(pending_small.join("\n\n"));
    }
    units
}

/// Chunk a markdown/plain-text document at heading + paragraph boundaries.
#[must_use]
pub fn chunk_document(text: &str) -> Vec<String> {
    // Split at heading lines when present (documents), otherwise paragraphs.
    let has_headings = text
        .lines()
        .any(|l| l.starts_with('#') && !l.starts_with("##://"));
    let units: Vec<String> = if has_headings {
        let mut units = Vec::new();
        let mut current = String::new();
        for line in text.lines() {
            if line.starts_with('#') && !current.is_empty() {
                units.push(std::mem::take(&mut current));
            }
            current.push_str(line);
            current.push('\n');
        }
        if !current.is_empty() {
            units.push(current);
        }
        units
    } else {
        split_paragraphs(text)
    };

    let capped: Vec<String> = units
        .into_iter()
        .map(|u| cap_unit(&u, MAX_SINGLE_PARAGRAPH_CHARS))
        .collect();
    pack_units(capped)
}

/// Chunk a transcript into ≤4k-char message groups, preserving role.
#[must_use]
pub fn chunk_transcript(content: &str) -> Vec<Chunk> {
    let mut units: Vec<Chunk> = Vec::new();
    for line in content.lines() {
        if let Some((text, role)) = transcript_line_text(line) {
            let text = cap_unit(&text, MAX_SINGLE_PARAGRAPH_CHARS);
            if !text.trim().is_empty() {
                units.push(Chunk {
                    content: text,
                    seq: units.len(),
                    role,
                });
            }
        }
    }
    if units.is_empty() {
        return Vec::new();
    }
    // Pack messages into chunk-sized groups without merging roles blindly:
    // keep role of the first message in the group.
    let mut groups: Vec<Chunk> = Vec::new();
    let mut current = String::new();
    let mut current_role: Option<String> = None;
    let mut seq = 0usize;
    for unit in units {
        if !current.is_empty() && current.len() + unit.content.len() + 2 > MAX_CHUNK_CHARS {
            groups.push(Chunk {
                content: std::mem::take(&mut current),
                seq,
                role: current_role.take(),
            });
            seq += 1;
        }
        if current_role.is_none() {
            current_role = unit.role;
        }
        if !current.is_empty() {
            current.push_str("\n\n");
        }
        current.push_str(&unit.content);
    }
    if !current.is_empty() {
        groups.push(Chunk {
            content: current,
            seq,
            role: current_role,
        });
    }
    groups
}

// ── Ledger ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEntry {
    pub path: String,
    pub sha256: String,
    pub kind: String,
    pub chunks: usize,
    pub bytes: u64,
    pub ingested_at: String,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct IngestLedger {
    pub entries: BTreeMap<String, LedgerEntry>,
}

impl IngestLedger {
    pub fn load(path: &Path) -> anyhow::Result<Self> {
        let mut ledger = Self::default();
        if !path.exists() {
            return Ok(ledger);
        }
        let file = fs::File::open(path)?;
        for line in std::io::BufReader::new(file).lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            if let Ok(entry) = serde_json::from_str::<LedgerEntry>(&line) {
                ledger.entries.insert(entry.path.clone(), entry);
            }
        }
        Ok(ledger)
    }

    pub fn save(&self, path: &Path) -> anyhow::Result<()> {
        let file = fs::File::create(path)?;
        let mut writer = BufWriter::new(file);
        for entry in self.entries.values() {
            serde_json::to_writer(&mut writer, entry)?;
            writer.write_all(b"\n")?;
        }
        writer.flush()?;
        Ok(())
    }
}

/// Deterministic chunk id: file hash + chunk index → UUIDv5 (stable across
/// runs so re-ingest replaces documents instead of duplicating them).
fn chunk_id(file_sha: &str, seq: usize) -> Uuid {
    Uuid::new_v5(
        &Uuid::NAMESPACE_URL,
        format!("whitemagic-ingest:{file_sha}:{seq}").as_bytes(),
    )
}

// ── Report ───────────────────────────────────────────────────────────

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct IngestReport {
    pub files_found: usize,
    pub files_unchanged: usize,
    pub files_ingested: usize,
    pub chunks_written: usize,
    pub skipped: Vec<(String, String)>,
    pub errors: Vec<(String, String)>,
}

impl IngestReport {
    #[must_use]
    pub fn summary_line(&self) -> String {
        format!(
            "found={} unchanged={} ingested={} chunks={} skipped={} errors={}",
            self.files_found,
            self.files_unchanged,
            self.files_ingested,
            self.chunks_written,
            self.skipped.len(),
            self.errors.len()
        )
    }
}

// ── Harvest ──────────────────────────────────────────────────────────

/// Recursively collect candidate files under `source`.
fn collect_files(
    source: &Path,
    files: &mut Vec<PathBuf>,
    skipped: &mut Vec<(String, String)>,
    limit: usize,
) {
    if files.len() >= limit {
        return;
    }
    let Ok(entries) = fs::read_dir(source) else {
        skipped.push((source.display().to_string(), "unreadable directory".into()));
        return;
    };
    for entry in entries.flatten() {
        if files.len() >= limit {
            return;
        }
        let path = entry.path();
        let file_type = match entry.file_type() {
            Ok(ft) => ft,
            Err(_) => continue,
        };
        let name = entry.file_name().to_string_lossy().to_string();
        if file_type.is_dir() {
            if EXCLUDED_DIR_NAMES.iter().any(|d| *d == name) {
                continue;
            }
            collect_files(&path, files, skipped, limit);
            continue;
        }
        if !file_type.is_file() {
            continue;
        }
        if name == "ingest_ledger.jsonl" {
            continue;
        }
        if is_credential_file(&name) {
            skipped.push((
                path.display().to_string(),
                "credential-shaped filename".into(),
            ));
            continue;
        }
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or_default()
            .to_lowercase();
        if SKIP_EXTENSIONS.iter().any(|e| *e == ext) {
            continue;
        }
        if TEXT_EXTENSIONS.iter().any(|e| *e == ext) {
            files.push(path);
        }
    }
}

// ── v26 heritage export files ────────────────────────────────────────

/// Parsed `<!-- wm-key: value -->` provenance block from a v26 heritage
/// export file (written by `scripts/export_v26_heritage.py`). Field
/// values had `--` escaped to `__` by the exporter; parsing unescapes.
#[derive(Debug, Default)]
struct HeritageHeader {
    fields: BTreeMap<String, String>,
    tags: Vec<String>,
}

/// Recognize a v26 heritage export file and split it into its header
/// block and body. Returns `None` for any file that does not start with
/// the heritage marker — the caller falls back to normal chunking.
fn parse_heritage(text: &str) -> Option<(HeritageHeader, String)> {
    const MARKER: &str = "<!-- WhiteMagic v26 heritage export -->";
    let mut lines = text.lines();
    let first = lines.next()?;
    if first.trim() != MARKER {
        return None;
    }
    let mut hdr = HeritageHeader::default();
    let mut body_line: Option<usize> = None;
    for (i, line) in lines.enumerate() {
        let t = line.trim();
        if t.is_empty() {
            continue;
        }
        let Some(inner) = t
            .strip_prefix("<!-- wm-")
            .and_then(|s| s.strip_suffix("-->"))
        else {
            body_line = Some(i); // first non-header, non-blank line: the body
            break;
        };
        let Some((k, v)) = inner.split_once(':') else {
            body_line = Some(i);
            break;
        };
        let val = v.trim().replace("__", "--");
        if k.trim() == "tags" {
            hdr.tags = val
                .split(',')
                .map(str::trim)
                .filter(|s| !s.is_empty())
                .map(str::to_string)
                .collect();
        } else {
            hdr.fields.insert(k.trim().to_string(), val);
        }
    }
    // Marker line + 0-based body index → lines to skip in the full text.
    let body = match body_line {
        Some(i) => text.lines().skip(i + 1).collect::<Vec<_>>().join("\n"),
        None => String::new(),
    };
    Some((hdr, body))
}

/// Map a v26 heritage export directory name onto a v5 galaxy. Categories
/// that are not native v5 galaxies land in Codex (the knowledge/documents
/// galaxy) with a `heritage-category:<dir>` tag preserving the origin.
#[must_use]
fn heritage_galaxy(dir: &str) -> (Galaxy, Option<String>) {
    match dir {
        "aria" => (Galaxy::Aria, None),
        "citta" => (Galaxy::Citta, None),
        "codex" => (Galaxy::Codex, None),
        "journals" => (Galaxy::Journals, None),
        "dreams" => (Galaxy::Dreams, None),
        "research" => (Galaxy::Research, None),
        "sessions" => (Galaxy::Sessions, None),
        "substrate" => (Galaxy::Substrate, None),
        "universal" => (Galaxy::Universal, None),
        other => (Galaxy::Codex, Some(other.to_string())),
    }
}

/// Recover the v26 memory-id reference from the export filename's
/// trailing 12-hex suffix (`<date>_i<imp>_<title>_<sha12>.md`).
#[must_use]
fn heritage_ref_from_path(path: &Path) -> Option<String> {
    let stem = path.file_stem()?.to_string_lossy();
    let seg = stem.rsplit('_').next()?;
    if seg.len() == 12 && seg.bytes().all(|b| b.is_ascii_hexdigit()) {
        Some(seg.to_ascii_lowercase())
    } else {
        None
    }
}

/// v26 `memory_type` label → v5 [`wm_memory::memory::MemoryType`].
/// Unknown labels fall back to the v5 default (LongTerm) — heritage
/// rows are classified honestly by the tag family instead.
#[must_use]
fn heritage_memory_type(s: &str) -> wm_memory::memory::MemoryType {
    match s.to_ascii_lowercase().as_str() {
        "short_term" | "shortterm" => wm_memory::memory::MemoryType::ShortTerm,
        "emotional" => wm_memory::memory::MemoryType::Emotional,
        "narrative" => wm_memory::memory::MemoryType::Narrative,
        "symbolic" => wm_memory::memory::MemoryType::Symbolic,
        "pattern" => wm_memory::memory::MemoryType::Pattern,
        "procedural" => wm_memory::memory::MemoryType::Procedural,
        "citta" => wm_memory::memory::MemoryType::Citta,
        "hypothesis" => wm_memory::memory::MemoryType::Hypothesis,
        _ => wm_memory::memory::MemoryType::LongTerm,
    }
}

/// Parse a v26 heritage timestamp ("2026-07-28T22:46:35.205434", naive
/// UTC, or RFC 3339). Returns None when absent/unparseable — callers
/// fall back to file mtime and the miss is visible in the record's tags.
#[must_use]
fn heritage_date(s: &str) -> Option<chrono::DateTime<chrono::Utc>> {
    if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&chrono::Utc));
    }
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%.f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S%.f",
    ] {
        if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(s, fmt) {
            return Some(dt.and_utc());
        }
    }
    None
}

/// v26 `source_trust` ("user"/"tool"/"inferred"/"web" or numeric) → v5
/// numeric trust. Semantics per `wm-mcp/src/trust_admin.rs`: 1.0
/// user-confirmed, 0.7 tool-neutral; unknown classes are unverified.
#[must_use]
fn heritage_trust(s: &str) -> f32 {
    match s.to_ascii_lowercase().as_str() {
        "user" => 1.0,
        "tool" => 0.7,
        "inferred" => 0.6,
        "web" => 0.5,
        other => other.parse::<f32>().unwrap_or(0.5).clamp(0.0, 1.0),
    }
}

fn heritage_bool(s: &str) -> bool {
    matches!(s, "1" | "true" | "TRUE" | "True")
}

/// Apply a parsed heritage header onto a freshly built memory: the 1:1
/// metadata mapping required by the unification plan (P3). The body was
/// already placed in `mem.content`; only metadata is overridden here.
fn apply_heritage_header(
    mem: &mut Memory,
    hdr: &HeritageHeader,
    category: Option<&str>,
    heritage_ref: Option<&str>,
    fallback_created: chrono::DateTime<chrono::Utc>,
) {
    let f = |k: &str| hdr.fields.get(k).map(String::as_str);

    let mut tags = vec![
        "source:heritage-v26".to_string(),
        format!("ingest:{INGEST_VERSION}"),
        "heritage:v26".to_string(),
        "chunk:1/1".to_string(),
    ];
    if let Some(c) = category {
        tags.push(format!("heritage-category:{c}"));
    }
    if let Some(r) = heritage_ref {
        tags.push(format!("heritage-ref:{r}"));
    }
    tags.extend(hdr.tags.iter().cloned());
    mem.metadata.tags = tags;

    if let Some(v) = f("memory_type") {
        mem.metadata.memory_type = heritage_memory_type(v);
    }
    if let Some(v) = f("importance") {
        if let Ok(x) = v.parse::<f32>() {
            mem.metadata.importance = x.clamp(0.0, 1.0);
        }
    }
    if let Some(v) = f("neuro_score") {
        if let Ok(x) = v.parse::<f32>() {
            mem.metadata.neuro_score = x.clamp(0.0, 1.0);
        }
    }
    if let Some(v) = f("novelty_score") {
        if let Ok(x) = v.parse::<f32>() {
            mem.metadata.novelty_score = x.clamp(0.0, 1.0);
        }
    }
    if let Some(v) = f("emotional_valence") {
        if let Ok(x) = v.parse::<f32>() {
            mem.metadata.emotional_valence = x.clamp(-1.0, 1.0);
        }
    }
    if let Some(v) = f("half_life_days") {
        if let Ok(x) = v.parse::<f32>() {
            mem.metadata.half_life_days = x.max(0.0);
        }
    }
    if let Some(v) = f("access_count") {
        if let Ok(x) = v.parse::<u64>() {
            mem.metadata.access_count = x;
        }
    }
    if let Some(v) = f("recall_count") {
        if let Ok(x) = v.parse::<u64>() {
            mem.metadata.recall_count = x;
        }
    }
    if let Some(v) = f("is_protected") {
        mem.metadata.is_protected = heritage_bool(v);
    }
    if let Some(v) = f("is_private") {
        mem.metadata.is_private = heritage_bool(v);
    }
    if let Some(v) = f("model_exclude") {
        mem.metadata.model_exclude = heritage_bool(v);
    }
    if let Some(v) = f("source_trust") {
        mem.metadata.source = v.to_string();
        mem.metadata.source_trust = heritage_trust(v);
    }
    if let Some(v) = f("agent_id") {
        mem.metadata.agent_id = v.to_string();
    }
    if let Some(v) = f("title") {
        mem.metadata.title = Some(v.to_string());
    }
    let created = f("created_at")
        .and_then(heritage_date)
        .unwrap_or(fallback_created);
    mem.metadata.created_at = created;
    if let Some(v) = f("accessed_at") {
        mem.metadata.accessed_at = heritage_date(v).unwrap_or(created);
    } else {
        mem.metadata.accessed_at = created;
    }
    // Heritage is born cold (typology §6): RawArchive class + Archival
    // tier. Header importance is preserved 1:1 (the plan's fidelity
    // mandate) — the RawArchive importance ceiling is a dispatch-path
    // write-gate policy, not a store invariant.
    mem.metadata.class = Some(wm_memory::typology::MemoryClass::RawArchive);
    mem.metadata.tier = wm_memory::typology::initial_tier(
        wm_memory::typology::MemoryClass::RawArchive,
    );
    mem.metadata.coords = wm_core::HolographicCoords::new(
        mem.metadata.galaxy,
        mem.metadata.created_at.timestamp().max(0) as u64,
    );
}

// ── Main entry ───────────────────────────────────────────────────────

/// Parse a galaxy name for the `--galaxy` override.
fn parse_galaxy_override(s: &str) -> anyhow::Result<Galaxy> {
    Galaxy::from_db_name(&s.to_lowercase())
        .or_else(|| Galaxy::from_db_name(s))
        .ok_or_else(|| anyhow::anyhow!("unknown galaxy: {s}"))
}

/// Ingest coexistence (S4): map a store-open failure into an actionable
/// error. When the underlying error looks like lock contention, point the
/// operator at the writer-handoff protocol instead of a bare error —
/// bulk ingest and a live serve both want exclusive writer locks, and the
/// resolution order is documented in `docs/INGEST_COEXISTENCE.md`.
fn lock_coexistence_error(
    err: &wm_core::CoreError,
    what: &str,
    path: &Path,
    contention_hint: &str,
) -> anyhow::Error {
    let msg = err.to_string();
    if msg.to_lowercase().contains("lock") {
        anyhow::anyhow!(
            "Could not open {what} at {} — {contention_hint}. \
             Writer-handoff protocol (docs/INGEST_COEXISTENCE.md): \
             (1) stop the store's unit (`systemctl --user stop wm-serve@<scope>`), \
             (2) run this ingest to completion, \
             (3) start the unit again — serve startup heals any index drift. \
             For read access during the run, a sidecar `wm serve --readonly` \
             can share the store (readonly search never takes the writer lock). \
             Underlying error: {msg}",
            path.display()
        )
    } else {
        anyhow::anyhow!("{msg}")
    }
}

/// Ingest a source directory into `store_path`.
///
/// `dry_run` reports without opening the store (no writes, no store
/// creation). `limit` caps the number of files considered (first N in walk
/// order — for testing slices, not a selection mechanism).
#[allow(clippy::too_many_arguments)]
pub fn run_ingest(
    source: &Path,
    store_path: &Path,
    dry_run: bool,
    limit: usize,
    galaxy_override: Option<&str>,
) -> anyhow::Result<IngestReport> {
    let limit = if limit == 0 { usize::MAX } else { limit };
    println!("=== WhiteMagic Knowledge Ingest ===");
    println!();
    println!("Source: {}", source.display());
    println!("Store:  {}", store_path.display());
    if dry_run {
        println!("Mode:   DRY RUN (no writes)");
    }
    println!();

    let mut files = Vec::new();
    let mut skipped: Vec<(String, String)> = Vec::new();
    collect_files(source, &mut files, &mut skipped, limit);

    let ledger_path = store_path.join("ingest_ledger.jsonl");
    let mut ledger = IngestLedger::load(&ledger_path)?;
    let source_name = source.file_name().map_or_else(
        || "unknown".to_string(),
        |n| n.to_string_lossy().to_string(),
    );

    let mut report = IngestReport {
        files_found: files.len(),
        ..Default::default()
    };

    let (store, search) = if dry_run {
        (None, None)
    } else {
        // Store layout convention (matching wm serve / doctor / migrate):
        // LMDB at <store>/lmdb, Tantivy at <store>/lmdb/tantivy, JSON state
        // (including this ledger) at <store> root.
        let lmdb_path = store_path.join("lmdb");
        fs::create_dir_all(&lmdb_path)?;
        let store = MemoryStore::open(&lmdb_path, 4 * 1024 * 1024 * 1024).map_err(|e| {
            lock_coexistence_error(&e, "LMDB", &lmdb_path, "a server may be running")
        })?;
        let tantivy_path = lmdb_path.join("tantivy");
        fs::create_dir_all(&tantivy_path)?;
        let search = SearchEngine::open(&tantivy_path).map_err(|e| {
            lock_coexistence_error(
                &e,
                "Tantivy",
                &tantivy_path,
                "a live `wm serve` on this store holds the writer lock",
            )
        })?;
        (Some(store), Some(search))
    };

    let mut writer = if let Some(search) = &search {
        Some(search.writer()?)
    } else {
        None
    };

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or_default()
        .to_string();

    for path in &files {
        let rel = path
            .strip_prefix(source)
            .map_or_else(|_| path.display().to_string(), |p| p.display().to_string());

        let metadata = match fs::metadata(path) {
            Ok(m) => m,
            Err(e) => {
                report
                    .errors
                    .push((rel.clone(), format!("stat failed: {e}")));
                continue;
            }
        };
        if metadata.len() > MAX_FILE_BYTES {
            report
                .skipped
                .push((rel.clone(), format!("oversized ({} bytes)", metadata.len())));
            continue;
        }

        let bytes = match fs::read(path) {
            Ok(b) => b,
            Err(e) => {
                report
                    .errors
                    .push((rel.clone(), format!("read failed: {e}")));
                continue;
            }
        };
        let sha = sha256_hex(&bytes);
        let text = String::from_utf8_lossy(&bytes);

        if contains_private_key(&text) {
            report
                .skipped
                .push((rel.clone(), "credential-bearing content".into()));
            continue;
        }

        if let Some(prev) = ledger.entries.get(&rel) {
            if prev.sha256 == sha {
                report.files_unchanged += 1;
                continue;
            }
        }

        let Some(kind) = detect_kind(path, head_for_detection(&text)) else {
            report
                .skipped
                .push((rel.clone(), "unrecognized format".into()));
            continue;
        };

        // v26 heritage exports carry a `<!-- wm-key: value -->` provenance
        // block (scripts/export_v26_heritage.py). When present, one file is
        // ONE memory and the headers map 1:1 onto memory metadata (P3).
        let heritage = matches!(kind, SourceKind::Markdown | SourceKind::PlainText)
            .then(|| parse_heritage(&text))
            .flatten();
        let heritage_meta = heritage.as_ref().map(|_| {
            // Galaxy category: first path component relative to the source
            // root. When the source IS the galaxy directory itself
            // (single-category run), fall back to the source dir's name.
            let rel_dir = path
                .parent()
                .and_then(|p| p.strip_prefix(source).ok())
                .and_then(|p| p.components().next())
                .map(|c| c.as_os_str().to_string_lossy().to_string())
                .filter(|d| !d.is_empty());
            let dir = rel_dir.or_else(|| {
                source
                    .file_name()
                    .map(|n| n.to_string_lossy().to_string())
            });
            let (galaxy, category) = match dir {
                Some(d) => {
                    let (g, c) = heritage_galaxy(&d);
                    (g, c)
                }
                None => (Galaxy::Codex, Some("root".to_string())),
            };
            (galaxy, category, heritage_ref_from_path(path))
        });

        let chunks: Vec<Chunk> = if heritage.is_some() {
            match heritage.as_ref().map(|(_, b)| b.trim()) {
                Some(b) if !b.is_empty() => vec![Chunk {
                    content: b.to_string(),
                    seq: 0,
                    role: None,
                }],
                _ => {
                    report
                        .skipped
                        .push((rel.clone(), "empty heritage body".into()));
                    continue;
                }
            }
        } else {
            match kind {
                SourceKind::Transcript => chunk_transcript(&text),
                SourceKind::Markdown | SourceKind::PlainText => chunk_document(&text)
                    .into_iter()
                    .enumerate()
                    .map(|(seq, content)| Chunk {
                        content,
                        seq,
                        role: None,
                    })
                    .collect(),
            }
        };

        if chunks.is_empty() {
            report
                .skipped
                .push((rel.clone(), "no ingestible content".into()));
            continue;
        }

        let galaxy = if let Some((g, _, _)) = &heritage_meta {
            *g
        } else {
            match galaxy_override {
                Some(g) => parse_galaxy_override(g)?,
                None => match kind {
                    SourceKind::Transcript => Galaxy::Sessions,
                    SourceKind::Markdown | SourceKind::PlainText => Galaxy::Research,
                },
            }
        };

        if let Some(prev) = ledger.entries.get(&rel) {
            // Remove the previous version: deterministic ids allow deleting
            // both the LMDB rows and the Tantivy documents before re-adding
            // (Tantivy documents are not keyed, and chunk boundaries may
            // shift, changing the id set).
            for seq in 0..prev.chunks {
                let old_id = chunk_id(&prev.sha256, seq);
                if let (Some(search), Some(writer)) = (&search, writer.as_mut()) {
                    search.delete_document(writer, &old_id.to_string())?;
                }
                if let Some(store) = &store {
                    let _ = store.delete(galaxy, old_id);
                }
            }
        }

        if dry_run {
            report.files_ingested += 1;
            report.chunks_written += chunks.len();
            ledger.entries.insert(
                rel.clone(),
                LedgerEntry {
                    path: rel.clone(),
                    sha256: sha.clone(),
                    kind: kind.as_str().to_string(),
                    chunks: chunks.len(),
                    bytes: metadata.len(),
                    ingested_at: now.clone(),
                },
            );
            continue;
        }

        let store = store.as_ref().expect("store open when not dry-run");
        let created_at = metadata
            .modified()
            .ok()
            .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
            .and_then(|d| {
                chrono::DateTime::from_timestamp(i64::try_from(d.as_secs()).unwrap_or(0), 0)
            })
            .unwrap_or_else(chrono::Utc::now);

        let mut mems: Vec<Memory> = Vec::new();
        for chunk in &chunks {
            let mut mem = Memory::new(galaxy, chunk.content.clone());
            mem.metadata.id = chunk_id(&sha, chunk.seq);
            mem.metadata.galaxy = galaxy;
            mem.metadata.content_hash = wm_memory::content_hash(&chunk.content);
            let mut tags = vec![
                format!("source:{source_name}"),
                format!("ingest:{INGEST_VERSION}"),
                format!("kind:{}", kind.as_str()),
            ];
            if let Some(role) = &chunk.role {
                tags.push(format!("role:{role}"));
            }
            tags.push(format!("chunk:{}/{}", chunk.seq + 1, chunks.len()));
            mem.metadata.tags = tags;
            mem.metadata.importance = match kind {
                SourceKind::Transcript => 0.6,
                SourceKind::Markdown | SourceKind::PlainText => 0.4,
            };
            mem.metadata.created_at = created_at;
            mem.metadata.accessed_at = created_at;
            mem.metadata.agent_id = "ingest".to_string();
            mem.metadata.coords =
                wm_core::HolographicCoords::new(galaxy, created_at.timestamp() as u64);
            if chunk.seq == 0 {
                if let (Some((hdr, _)), Some((_, category, href))) =
                    (&heritage, &heritage_meta)
                {
                    apply_heritage_header(
                        &mut mem,
                        hdr,
                        category.as_deref(),
                        href.as_deref(),
                        created_at,
                    );
                }
            }
            mems.push(mem);
        }

        // Batch write + index. Tantivy documents are not keyed, so every
        // add is preceded by a delete for the same id — this keeps the
        // index consistent with LMDB (which IS keyed) when duplicate files
        // across exports map to identical chunk ids.
        store.put_batch(galaxy, &mems)?;
        if let (Some(search), Some(writer)) = (&search, writer.as_mut()) {
            for mem in &mems {
                let id_str = mem.metadata.id.to_string();
                search.delete_document(writer, &id_str)?;
                search.add_document(
                    writer,
                    &id_str,
                    galaxy.db_name(),
                    &mem.content,
                    &mem.metadata.tags,
                    mem.metadata.created_at.timestamp(),
                )?;
            }
        }

        report.files_ingested += 1;
        report.chunks_written += chunks.len();
        ledger.entries.insert(
            rel.clone(),
            LedgerEntry {
                path: rel.clone(),
                sha256: sha,
                kind: kind.as_str().to_string(),
                chunks: chunks.len(),
                bytes: metadata.len(),
                ingested_at: now.clone(),
            },
        );
    }

    // Commit the index, then release the exclusive Tantivy writer lock
    // before the ledger save and report printing.
    if let Some(search) = &search {
        if let Some(mut writer) = writer {
            search.commit(&mut writer)?;
        }
    }

    if !dry_run {
        ledger.save(&ledger_path)?;
    }

    report.skipped.extend(skipped);
    report.skipped.sort();

    println!("Report: {}", report.summary_line());
    if !report.skipped.is_empty() {
        println!("Skipped ({}):", report.skipped.len());
        for (path, reason) in report.skipped.iter().take(20) {
            println!("  - {path}: {reason}");
        }
        if report.skipped.len() > 20 {
            println!("  ... and {} more", report.skipped.len() - 20);
        }
    }
    if !report.errors.is_empty() {
        println!("Errors ({}):", report.errors.len());
        for (path, err) in report.errors.iter().take(10) {
            println!("  - {path}: {err}");
        }
    }
    println!(
        "Ledger: {} ({} entries)",
        ledger_path.display(),
        ledger.entries.len()
    );

    Ok(report)
}

/// First ≤4KB of `text` at a valid UTF-8 char boundary (for format sniffing).
fn head_for_detection(text: &str) -> &str {
    let end = text.len().min(4096);
    let boundary = (0..=end).rev().find(|&i| text.is_char_boundary(i));
    &text[..boundary.unwrap_or(0)]
}

/// Hex-encode a SHA-256 digest (stable across versions of the `sha2` crate).
#[must_use]
pub fn sha256_hex(bytes: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

// ── Tests ────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn heritage_header_parses_fields_tags_and_body() {
        let text = "<!-- WhiteMagic v26 heritage export -->\n\
                    <!-- wm-memory_type: SHORT_TERM -->\n\
                    <!-- wm-created_at: 2026-07-28T22:46:35.205434 -->\n\
                    <!-- wm-importance: 0.5 -->\n\
                    <!-- wm-source_trust: user -->\n\
                    <!-- wm-title: fact_00117 -->\n\
                    <!-- wm-tags: alpha,beta -->\n\
                    \n\
                    entity_023 has project Beta.\n";
        let (hdr, body) = parse_heritage(text).expect("heritage file must parse");
        assert_eq!(hdr.fields.get("memory_type").map(String::as_str), Some("SHORT_TERM"));
        assert_eq!(hdr.fields.get("title").map(String::as_str), Some("fact_00117"));
        assert_eq!(hdr.fields.get("source_trust").map(String::as_str), Some("user"));
        assert_eq!(hdr.tags, vec!["alpha", "beta"]);
        assert_eq!(body, "entity_023 has project Beta.");
    }

    #[test]
    fn heritage_parse_rejects_non_heritage_and_unescapes_values() {
        assert!(parse_heritage("# just a doc\n").is_none());
        let text = "<!-- WhiteMagic v26 heritage export -->\n\
                    <!-- wm-title: has--dashes -->\n\
                    \n\
                    body\n";
        let (hdr, _) = parse_heritage(text).unwrap();
        // The exporter escaped `--` to `__`; parsing unescapes it back.
        assert_eq!(hdr.fields.get("title").map(String::as_str), Some("has--dashes"));
    }

    #[test]
    fn heritage_galaxy_maps_native_dirs_and_tags_the_rest() {
        assert_eq!(heritage_galaxy("codex"), (Galaxy::Codex, None));
        assert_eq!(heritage_galaxy("sessions"), (Galaxy::Sessions, None));
        assert_eq!(heritage_galaxy("substrate"), (Galaxy::Substrate, None));
        let (g, cat) = heritage_galaxy("meta");
        assert_eq!(g, Galaxy::Codex);
        assert_eq!(cat.as_deref(), Some("meta"));
    }

    #[test]
    fn heritage_mapping_covers_types_trust_and_dates() {
        assert_eq!(
            heritage_memory_type("SHORT_TERM"),
            wm_memory::memory::MemoryType::ShortTerm
        );
        assert_eq!(
            heritage_memory_type("nonsense"),
            wm_memory::memory::MemoryType::LongTerm
        );
        assert_eq!(heritage_trust("user"), 1.0);
        assert_eq!(heritage_trust("tool"), 0.7);
        assert_eq!(heritage_trust("0.9"), 0.9);
        let dt = heritage_date("2026-07-28T22:46:35.205434").expect("naive parse");
        assert_eq!(dt.timestamp(), 1_785_278_795);
    }

    #[test]
    fn heritage_apply_maps_metadata_one_to_one() {
        let text = "<!-- WhiteMagic v26 heritage export -->\n\
                    <!-- wm-memory_type: SHORT_TERM -->\n\
                    <!-- wm-created_at: 2026-07-28T22:46:35.205434 -->\n\
                    <!-- wm-importance: 0.8 -->\n\
                    <!-- wm-access_count: 7 -->\n\
                    <!-- wm-source_trust: user -->\n\
                    <!-- wm-agent_id: lucas -->\n\
                    <!-- wm-title: the crown jewel -->\n\
                    <!-- wm-tags: provenance-test -->\n\
                    \n\
                    body text here\n";
        let (hdr, body) = parse_heritage(text).unwrap();
        let mut mem = Memory::new(Galaxy::Codex, body);
        mem.metadata.galaxy = Galaxy::Codex;
        apply_heritage_header(&mut mem, &hdr, Some("meta"), Some("abc123def456"), chrono::Utc::now());
        assert_eq!(mem.content, "body text here");
        assert_eq!(mem.metadata.importance, 0.8);
        assert_eq!(mem.metadata.access_count, 7);
        assert_eq!(mem.metadata.source, "user");
        assert_eq!(mem.metadata.source_trust, 1.0);
        assert_eq!(mem.metadata.agent_id, "lucas");
        assert_eq!(mem.metadata.title.as_deref(), Some("the crown jewel"));
        assert_eq!(
            mem.metadata.memory_type,
            wm_memory::memory::MemoryType::ShortTerm
        );
        assert_eq!(mem.metadata.created_at.timestamp(), 1_785_278_795);
        assert_eq!(
            mem.metadata.class,
            Some(wm_memory::typology::MemoryClass::RawArchive)
        );
        assert_eq!(mem.metadata.tier, wm_memory::memory::Tier::Archival);
        assert!(mem.metadata.tags.contains(&"heritage-category:meta".to_string()));
        assert!(mem.metadata.tags.contains(&"heritage-ref:abc123def456".to_string()));
        assert!(mem.metadata.tags.contains(&"provenance-test".to_string()));
    }

    fn write_tree(root: &Path) {
        fs::create_dir_all(root.join("docs")).unwrap();
        fs::write(
            root.join("docs/a.md"),
            "# Title\n\nShort intro.\n\nA second paragraph with enough length to stand alone.\n\nAnother paragraph.\n\n\n",
        )
        .unwrap();
        fs::write(
            root.join("docs/b.jsonl"),
            "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"hello world\"}}\n{\"type\":\"assistant\",\"message\":{\"role\":\"assistant\",\"content\":\"hi there\"}}\n{\"type\":\"file-history-snapshot\",\"snapshot\":{}}\n",
        )
        .unwrap();
        fs::write(root.join("docs/c.txt"), "plain text document here").unwrap();
        fs::write(root.join("docs/.env"), "SECRET=1").unwrap();
        fs::create_dir_all(root.join("node_modules/x")).unwrap();
        fs::write(root.join("node_modules/x/y.md"), "# should be skipped").unwrap();
    }

    #[test]
    fn credential_file_detection() {
        assert!(is_credential_file(".env"));
        assert!(is_credential_file(".env.production"));
        assert!(is_credential_file("id_rsa"));
        assert!(is_credential_file("credentials.json"));
        assert!(!is_credential_file("notes.md"));
        assert!(contains_private_key(
            "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
        ));
        assert!(!contains_private_key("ordinary session notes"));
    }

    #[test]
    fn kind_detection() {
        assert_eq!(
            detect_kind(Path::new("a.md"), "# hi"),
            Some(SourceKind::Markdown)
        );
        assert_eq!(
            detect_kind(Path::new("b.jsonl"), "{\"type\":\"user\"}"),
            Some(SourceKind::Transcript)
        );
        assert_eq!(
            detect_kind(Path::new("c.txt"), "hello"),
            Some(SourceKind::PlainText)
        );
        assert_eq!(detect_kind(Path::new("d.bin"), "\u{0}\u{1}"), None);
    }

    #[test]
    fn transcript_chunking_extracts_messages_and_preserves_role() {
        let lines = [
            r#"{"type":"user","message":{"role":"user","content":"question one"}}"#,
            r#"{"type":"assistant","message":{"role":"assistant","content":"answer one"}}"#,
            r#"{"type":"file-history-snapshot","snapshot":{}}"#,
            r#"{"type":"response_item","payload":{"content":"codex rollout text"}}"#,
        ]
        .join("\n");
        let chunks = chunk_transcript(&lines);
        assert_eq!(chunks.len(), 1);
        assert!(chunks[0].content.contains("question one"));
        assert!(chunks[0].content.contains("codex rollout text"));
        assert_eq!(chunks[0].role.as_deref(), Some("user"));
    }

    #[test]
    fn transcript_chunking_packs_multiple_chunks() {
        let mut lines = Vec::new();
        for i in 0..200 {
            lines.push(format!(
                r#"{{"type":"user","message":{{"role":"user","content":"message {i} {}"}}}}"#,
                "x".repeat(200)
            ));
        }
        let chunks = chunk_transcript(&lines.join("\n"));
        assert!(chunks.len() > 1);
        for c in &chunks {
            assert!(c.content.len() <= MAX_CHUNK_CHARS + 128, "chunk too large");
        }
    }

    #[test]
    fn document_chunking_merges_small_paragraphs() {
        let text = "one\n\ntwo\n\nthree\n\nfour";
        let chunks = chunk_document(text);
        assert_eq!(chunks.len(), 1, "small paragraphs should merge");
        assert!(chunks[0].contains("four"));
    }

    #[test]
    fn document_chunking_caps_huge_paragraphs() {
        let text = "x".repeat(20_000);
        let chunks = chunk_document(&text);
        assert_eq!(chunks.len(), 1);
        assert!(chunks[0].len() < 9_000);
        assert!(chunks[0].contains("[... truncated ...]"));
    }

    #[test]
    fn chunk_ids_are_deterministic() {
        let a = chunk_id("abc123", 4);
        let b = chunk_id("abc123", 4);
        assert_eq!(a, b);
        assert_ne!(a, chunk_id("abc123", 5));
        assert_ne!(a, chunk_id("other", 4));
    }

    #[test]
    fn ledger_roundtrip_and_unchanged_skip() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        write_tree(root);
        let store_path = tmp.path().join("store");

        let first = run_ingest(root, &store_path, false, 0, None).unwrap();
        assert_eq!(first.files_found, 3, "md + jsonl + txt (env excluded)");
        assert_eq!(first.files_ingested, 3);
        assert!(first.chunks_written >= 3);
        assert!(first.skipped.iter().any(|(p, _)| p.contains(".env")));

        // Second run: everything unchanged → no-op.
        let second = run_ingest(root, &store_path, false, 0, None).unwrap();
        assert_eq!(second.files_unchanged, 3);
        assert_eq!(second.files_ingested, 0);
        assert_eq!(second.chunks_written, 0);

        // Verify the store: research + sessions galaxies populated.
        let store = MemoryStore::open_default(store_path.join("lmdb")).unwrap();
        assert!(store.count(Galaxy::Research).unwrap() >= 1);
        assert!(store.count(Galaxy::Sessions).unwrap() >= 1);

        // Verify searchable index exists and re-ingest replaces documents.
        let search_path = store_path.join("lmdb").join("tantivy");
        let search = SearchEngine::open(&search_path).unwrap();
        let total = search.count_docs_in_galaxy("research").unwrap()
            + search.count_docs_in_galaxy("sessions").unwrap();
        assert!(total >= 3);
    }

    #[test]
    fn changed_file_replaces_old_chunks() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path();
        fs::create_dir_all(root).unwrap();
        let f = root.join("a.md");
        fs::write(&f, "# One\n\nFirst version paragraph of some length here.").unwrap();
        let store_path = tmp.path().join("store");

        let first = run_ingest(root, &store_path, false, 0, None).unwrap();
        assert_eq!(first.chunks_written, 1);

        // New version: two long sections → two chunks (different id set).
        let long = "A long second section here. ".repeat(200);
        fs::write(&f, format!("# One\n\nRevised version.\n\n# Two\n\n{long}")).unwrap();
        let second = run_ingest(root, &store_path, false, 0, None).unwrap();
        assert_eq!(second.files_ingested, 1);
        assert_eq!(second.chunks_written, 2);

        let store = MemoryStore::open_default(store_path.join("lmdb")).unwrap();
        let count = store.count(Galaxy::Research).unwrap();
        assert_eq!(
            count as usize, second.chunks_written,
            "old chunks must be replaced, not duplicated"
        );

        // Old content must be gone from the store entirely.
        let all = store.scan_all(Galaxy::Research).unwrap();
        let texts: Vec<&str> = all.iter().map(|m| m.content.as_str()).collect();
        assert!(
            !texts.iter().any(|t| t.contains("First version")),
            "superseded chunk content must be removed"
        );

        // Dry-run must not create a store.
        let dry_store = tmp.path().join("never-created");
        let report = run_ingest(root, &dry_store, true, 0, None).unwrap();
        assert!(report.files_ingested >= 1);
        assert!(!dry_store.exists(), "dry run must not create the store");
    }
}
