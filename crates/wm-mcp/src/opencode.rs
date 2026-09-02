//! opencode session-bridge — digest and export opencode session data.
//!
//! opencode (the coding-agent runtime) records sessions in a SQLite DB
//! (`~/.local/share/opencode/opencode.db`: `session`, `message`, `part`
//! tables). This module makes that corpus a first-class whitemagic input:
//!
//! - `digest` — a one-command per-session summary (title, project, message
//!   counts, tokens, cost, model, topics) as markdown or JSON. Board-ready:
//!   replaces ad-hoc digging with a single call, and works against *another
//!   seat's* lane snapshot too, so fleet members can read each other's
//!   session history without exchanging opaque multi-GB archives by hand.
//! - `export` — emits `session.import`-compatible JSONL (`session_start` +
//!   `session_turn` records), so opencode history can be ingested into a
//!   whitemagic store with provenance.
//!
//! Design decisions:
//!
//! - read-only + one deferred transaction: SQLite WAL readers never block
//!   writers, and a single read transaction gives a consistent snapshot
//!   across scans without copying the DB into RAM (matters: snapshot DBs
//!   can be tens of GB);
//! - lane snapshots (.tar.gz from the fleet snapshot pipeline) are accepted
//!   directly — the first `.db` member is extracted with system `tar
//!   --occurrence=1` (the DB is written first) to a cache dir; this avoids
//!   streaming the whole multi-GB archive;
//! - deterministic identity: session/turn UUIDs are UUIDv5 over a fixed
//!   namespace, so re-exports re-import as idempotent upserts, and the same
//!   DB digests to the same ids everywhere;
//! - provenance: exported turns carry `source: "tool"`, `source_trust: 0.7`
//!   (the tool-ingested-neutral tier) and `source:opencode` tags;
//! - fail-loud: missing DBs, malformed rows and tar failures are reported,
//!   never silently swallowed.

use std::collections::{BinaryHeap, HashMap};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{Context, Result, bail};
use chrono::{DateTime, TimeZone, Utc};
use rusqlite::{Connection, OpenFlags};
use serde_json::json;
use uuid::Uuid;
use wm_core::{Galaxy, HolographicCoords};
use wm_memory::Memory;

/// Namespace seed for all bridge ids. Ids are UUIDv5 over
/// `uuid5(NAMESPACE_URL, NAMESPACE_SEED)` — kept byte-identical with the
/// fleet's Python prototype so both implementations produce the same ids.
const NAMESPACE_SEED: &str = "whitemagic:opencode-bridge";

/// Max chars of text retained per (session, role) for topics and export.
const TEXT_CAP: usize = 120_000;
/// Max chars per exported turn (long tool echoes are clipped, like the
/// prototype's TRUNC).
const TURN_MAX: usize = 8_000;

/// Default opencode session DB location.
#[must_use]
pub fn default_opencode_db() -> PathBuf {
    std::env::var_os("HOME").map_or_else(
        || PathBuf::from(".local/share/opencode/opencode.db"),
        |h| PathBuf::from(h).join(".local/share/opencode/opencode.db"),
    )
}

fn namespace() -> Uuid {
    Uuid::new_v5(&Uuid::NAMESPACE_URL, NAMESPACE_SEED.as_bytes())
}

/// Extract-cache root for lane snapshots.
fn cache_dir() -> PathBuf {
    std::env::temp_dir().join("wm-opencode-cache")
}

// ── DB resolution ────────────────────────────────────────────────────

/// Accept a raw `.db` or a lane snapshot `.tar.gz`. Snapshots are extracted
/// (first `.db` member) into a cache keyed by stem+size, then reused.
fn resolve_db(path: &Path) -> Result<PathBuf> {
    let is_tar = path
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("gz"));
    if !is_tar {
        return Ok(path.to_path_buf());
    }
    let cache = cache_dir();
    std::fs::create_dir_all(&cache).context("creating snapshot cache dir")?;
    let size = path
        .metadata()
        .with_context(|| format!("stat {}", path.display()))?
        .len();
    let stem = path.file_stem().map_or_else(
        || "snapshot".to_string(),
        |s| s.to_string_lossy().into_owned(),
    );
    let key: String = {
        // size + mtime: a re-snapshot of identical size must not serve stale
        let mtime = path
            .metadata()
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |d| d.as_secs());
        format!("{stem}-{size}-{mtime}")
    }
    .chars()
    .map(|c| {
        if c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-') {
            c
        } else {
            '_'
        }
    })
    .collect();
    let cached = cache.join(format!("{}.db", key.trim_end_matches(".tar")));
    if cached.exists() && cached.metadata().is_ok_and(|m| m.len() > 0) {
        return Ok(cached);
    }
    // The snapshot pipeline writes the .db member first; --occurrence=1
    // lets tar stop right after it instead of streaming the whole archive.
    // create_new (O_EXCL) + rename: refuse to follow a pre-planted symlink
    // at the predictable cache path, then move atomically into place.
    let staging = cached.with_extension("db.part");
    let _ = std::fs::remove_file(&staging);
    let out = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&staging)
        .with_context(|| format!("creating cache file {}", staging.display()))?;
    let status = Command::new("tar")
        .args([
            "-xzf",
            &path.to_string_lossy(),
            "-O",
            "--wildcards",
            "--occurrence=1",
            "*.db",
        ])
        .stdout(out)
        .stderr(std::process::Stdio::null())
        .status()
        .context("spawning system tar (is it installed?)")?;
    if !status.success() || !staging.exists() || !staging.metadata().is_ok_and(|m| m.len() > 0) {
        let _ = std::fs::remove_file(&staging);
        bail!("failed to extract .db from snapshot {}", path.display());
    }
    std::fs::rename(&staging, &cached)
        .with_context(|| format!("finalizing cache file {}", cached.display()))?;
    Ok(cached)
}

/// Open the (resolved) DB read-only and verify it looks like an opencode
/// session DB.
fn open_ro(path: &Path) -> Result<Connection> {
    if !path.exists() {
        bail!("opencode db not found: {}", path.display());
    }
    let conn = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)
        .with_context(|| format!("opening {}", path.display()))?;
    let tables = conn
        .query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE name IN ('session','message','part')",
            [],
            |r| r.get::<_, i64>(0),
        )
        .context("reading sqlite_master")?;
    if tables < 3 {
        bail!(
            "not an opencode session DB (missing session/message/part tables): {}",
            path.display()
        );
    }
    Ok(conn)
}

// ── Stats aggregation ────────────────────────────────────────────────

#[derive(Default)]
struct SessionStat {
    n_user: u64,
    n_ai: u64,
    n_tools: u64,
    tokens: u64,
    cost: f64,
    models: HashMap<String, u64>,
    model: String,
    user_texts: Vec<String>,
    ai_texts: Vec<String>,
}

/// Two-pass aggregation (messages, then text/tool parts). Per-session
/// rescans would be quadratic on multi-GB snapshot DBs; this is linear.
/// Returns per-session stats keyed by opencode session id plus the number
/// of malformed rows skipped (surfaced, never silent).
fn bulk_stats(conn: &Connection) -> Result<(HashMap<String, SessionStat>, u64)> {
    let mut by_session: HashMap<String, SessionStat> = HashMap::new();
    let mut skipped_malformed: u64 = 0;
    let mut role_of: HashMap<String, (String, String)> = HashMap::new();
    let mut stmt = conn.prepare("SELECT id, session_id, data FROM message")?;
    let mut rows = stmt.query([])?;
    while let Some(row) = rows.next()? {
        let id: String = row.get(0)?;
        let sid: String = row.get(1)?;
        let data: String = row.get(2)?;
        let Ok(v) = serde_json::from_str::<serde_json::Value>(&data) else {
            skipped_malformed += 1;
            continue;
        };
        let s = by_session.entry(sid.clone()).or_default();
        match v.get("role").and_then(serde_json::Value::as_str) {
            Some("user") => {
                s.n_user += 1;
                role_of.insert(id, (sid, "user".into()));
            }
            Some("assistant") => {
                s.n_ai += 1;
                role_of.insert(id, (sid.clone(), "assistant".into()));
                let tokens = v.get("tokens");
                let input = tokens
                    .and_then(|t| t.get("input"))
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0);
                let output = tokens
                    .and_then(|t| t.get("output"))
                    .and_then(serde_json::Value::as_u64)
                    .unwrap_or(0);
                s.tokens += input + output;
                s.cost += v
                    .get("cost")
                    .and_then(serde_json::Value::as_f64)
                    .unwrap_or(0.0);
                if let Some(m) = v.get("modelID").and_then(serde_json::Value::as_str) {
                    *s.models.entry(m.to_string()).or_insert(0) += 1;
                }
            }
            _ => {}
        }
    }
    drop(rows);
    drop(stmt);

    // The JSON1 filter keeps huge tool-output blobs out of serde entirely;
    // the fallback (sqlite without JSON1) parses in Rust — correct, slower.
    let json1 = conn
        .query_row("SELECT json_extract('{}','$.type')", [], |r| {
            r.get::<_, String>(0)
        })
        .is_ok();
    let part_query = if json1 {
        "SELECT message_id, data FROM part \
         WHERE json_extract(data, '$.type') IN ('text','tool')"
    } else {
        "SELECT message_id, data FROM part"
    };
    let mut caps: HashMap<(String, String), usize> = HashMap::new();
    let mut stmt = conn.prepare(part_query)?;
    let mut rows = stmt.query([])?;
    while let Some(row) = rows.next()? {
        let mid: String = row.get(0)?;
        let data: String = row.get(1)?;
        let Some((sid, role)) = role_of.get(&mid) else {
            continue;
        };
        let Ok(v) = serde_json::from_str::<serde_json::Value>(&data) else {
            skipped_malformed += 1;
            continue;
        };
        match v.get("type").and_then(serde_json::Value::as_str) {
            Some("tool") => {
                by_session.entry(sid.clone()).or_default().n_tools += 1;
            }
            Some("text") => {
                let Some(txt) = v.get("text").and_then(serde_json::Value::as_str) else {
                    continue;
                };
                if txt.trim().is_empty() {
                    continue;
                }
                let cap = caps.entry((sid.clone(), role.clone())).or_insert(0);
                if *cap >= TEXT_CAP {
                    continue;
                }
                *cap += txt.len();
                by_session
                    .entry(sid.clone())
                    .or_default()
                    .texts_for(role)
                    .push(txt.to_string());
            }
            _ => {}
        }
    }
    for s in by_session.values_mut() {
        if let Some((m, _)) = s.models.iter().max_by_key(|(_, n)| **n) {
            s.model = m.clone();
        }
    }
    Ok((by_session, skipped_malformed))
}

impl SessionStat {
    fn texts_for(&mut self, role: &str) -> &mut Vec<String> {
        if role == "user" {
            &mut self.user_texts
        } else {
            &mut self.ai_texts
        }
    }
}

// ── Topics ───────────────────────────────────────────────────────────

fn top_topics(texts: &[String], k: usize) -> Vec<String> {
    const STOP: &[&str] = &[
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has", "have", "i",
        "if", "in", "is", "it", "its", "of", "on", "or", "our", "so", "that", "the", "this", "to",
        "was", "we", "what", "when", "where", "which", "who", "will", "with", "you", "your", "can",
        "could", "should", "would", "do", "does", "did", "not", "no", "yes", "ok", "okay", "hey",
        "hi", "hello", "let", "lets", "make", "made", "need", "want", "use", "using", "used",
        "get", "got", "go", "going", "there", "here", "them", "they", "their", "then", "than",
        "just", "like", "more", "most", "some", "any", "all", "about", "now",
    ];
    let mut freq: HashMap<String, u64> = HashMap::new();
    for text in texts {
        let mut w = String::new();
        for c in text.chars() {
            if c.is_ascii_alphanumeric() || c == '_' || c == '-' {
                if w.is_empty() && !c.is_ascii_alphabetic() {
                    continue; // tokens start with a letter (prototype parity)
                }
                w.push(c.to_ascii_lowercase());
            } else {
                if w.len() >= 3 && !w.starts_with("ses_") {
                    *freq.entry(w.clone()).or_insert(0) += 1;
                }
                w.clear();
            }
        }
        if w.len() >= 3 && !w.starts_with("ses_") {
            *freq.entry(w).or_insert(0) += 1;
        }
    }
    let mut heap: BinaryHeap<(u64, String)> = freq
        .into_iter()
        .filter(|(w, _)| !STOP.contains(&w.as_str()))
        .map(|(w, n)| (n, w))
        .collect();
    let mut out = Vec::with_capacity(k);
    while out.len() < k {
        let Some((_, w)) = heap.pop() else {
            break;
        };
        out.push(w);
    }
    out
}

// ── Sessions ─────────────────────────────────────────────────────────

struct SessionRow {
    id: String,
    slug: String,
    directory: String,
    title: String,
    created_ms: i64,
    updated_ms: i64,
}

fn load_sessions(conn: &Connection, since: Option<&str>) -> Result<Vec<SessionRow>> {
    let mut sql = String::from(
        "SELECT id, slug, directory, title, time_created, time_updated \
         FROM session WHERE parent_id IS NULL",
    );
    if let Some(since) = since {
        let ts = DateTime::parse_from_rfc3339(&format!("{since}T00:00:00Z"))?.timestamp_millis();
        sql.push_str(" AND time_updated >= ");
        sql.push_str(&ts.to_string());
    }
    sql.push_str(" ORDER BY time_updated DESC");
    let mut stmt = conn.prepare(&sql)?;
    let mut rows = stmt.query([])?;
    let mut out = Vec::new();
    while let Some(r) = rows.next()? {
        out.push(SessionRow {
            id: r.get(0)?,
            slug: r.get::<_, Option<String>>(1)?.unwrap_or_default(),
            directory: r.get::<_, Option<String>>(2)?.unwrap_or_default(),
            title: r.get::<_, Option<String>>(3)?.unwrap_or_default(),
            created_ms: r.get::<_, Option<i64>>(4)?.unwrap_or(0),
            updated_ms: r.get::<_, Option<i64>>(5)?.unwrap_or(0),
        });
    }
    Ok(out)
}

fn utc(ms: i64) -> String {
    DateTime::<Utc>::from_timestamp_millis(ms)
        .unwrap_or_else(|| Utc.timestamp_opt(0, 0).unwrap())
        .format("%Y-%m-%d %H:%M")
        .to_string()
}

fn format_int(n: u64) -> String {
    let s = n.to_string();
    let mut out = String::with_capacity(s.len() + s.len() / 3);
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(c);
    }
    out
}

fn project_name(directory: &str) -> String {
    Path::new(directory)
        .file_name()
        .map_or_else(|| "/".to_string(), |p| p.to_string_lossy().into_owned())
}

// ── Digest ───────────────────────────────────────────────────────────

/// Run the digest: per-session summary table (markdown, or JSON).
///
/// # Errors
/// Fails loudly on missing/foreign DBs, tar failures, or SQLite errors.
pub fn run_digest(db: &Path, since: Option<&str>, as_json: bool) -> Result<()> {
    let resolved = resolve_db(db)?;
    let conn = open_ro(&resolved)?;
    // One deferred transaction = one WAL snapshot across both scans; a
    // read transaction never blocks a live opencode's writers.
    conn.execute_batch("BEGIN")?;
    let sessions = load_sessions(&conn, since)?;
    let (stats, skipped_malformed) = bulk_stats(&conn)?;
    conn.execute_batch("COMMIT")?;

    if as_json {
        let arr: Vec<serde_json::Value> = sessions
            .iter()
            .map(|r| {
                let s = stats.get(&r.id);
                json!({
                    "opencode_id": r.id,
                    "slug": r.slug,
                    "title": r.title,
                    "directory": r.directory,
                    "wm_session_id": namespace_uuid(&r.id).to_string(),
                    "created": utc(r.created_ms),
                    "updated": utc(r.updated_ms),
                    "user_msgs": s.map_or(0, |s| s.n_user),
                    "ai_msgs": s.map_or(0, |s| s.n_ai),
                    "tool_calls": s.map_or(0, |s| s.n_tools),
                    "tokens": s.map_or(0, |s| s.tokens),
                    "cost_usd": (s.map_or(0.0, |s| s.cost) * 10_000.0).round() / 10_000.0,
                    "model": s.map_or("?", |s| s.model.as_str()),
                    "topics": s.map_or(Vec::new(), |s| {
                        let mut all = s.user_texts.clone();
                        all.extend(s.ai_texts.iter().cloned());
                        top_topics(&all, 6)
                    }),
                })
            })
            .collect();
        println!(
            "{}",
            serde_json::to_string_pretty(&json!({
                "generated": utc(Utc::now().timestamp_millis()),
                "device_sessions": arr.len(),
                "skipped_malformed_rows": skipped_malformed,
                "sessions": arr,
            }))?
        );
        return Ok(());
    }

    println!(
        "| updated (UTC) | title | project | msgs (u/ai/tools) | tokens | cost | model | topics |"
    );
    println!("|---|---|---|---|---|---|---|---|");
    for r in &sessions {
        let empty = SessionStat::default();
        let s = stats.get(&r.id).unwrap_or(&empty);
        let title: String = {
            let t = if r.title.is_empty() {
                &r.slug
            } else {
                &r.title
            };
            t.chars().take(46).collect()
        };
        let mut corpus = s.user_texts.clone();
        corpus.extend(s.ai_texts.iter().cloned());
        let topics = top_topics(&corpus, 4).join(", ");
        println!(
            "| {} | {} | {} | {}/{}/{} | {} | ${:.2} | {} | {} |",
            utc(r.updated_ms),
            title,
            project_name(&r.directory),
            s.n_user,
            s.n_ai,
            s.n_tools,
            format_int(s.tokens),
            s.cost,
            if s.model.is_empty() { "?" } else { &s.model },
            topics
        );
    }
    if skipped_malformed > 0 {
        println!("\n_{skipped_malformed} malformed row(s) skipped (counted, not silent)_");
    }
    Ok(())
}

fn clip_turn(text: &str) -> String {
    if text.len() <= TURN_MAX {
        return text.to_string();
    }
    let truncated = text.len() - TURN_MAX;
    let mut out: String = text.chars().take(TURN_MAX).collect();
    out.push_str("\n… [truncated ");
    out.push_str(&truncated.to_string());
    out.push_str(" chars]");
    out
}

fn namespace_uuid(session_id: &str) -> Uuid {
    Uuid::new_v5(&namespace(), format!("opencode:{session_id}").as_bytes())
}

/// Holographic-coords galaxy ordinal for the Sessions galaxy — derived
/// from the enum, never hand-maintained.
const SESSIONS_COORD_GALAXY: u8 = Galaxy::Sessions as i32 as u8;

// ── Export ───────────────────────────────────────────────────────────

fn memory_envelope(
    record_key: &str,
    content: String,
    tags: &[String],
    importance: f32,
    ts_ms: i64,
) -> Result<Memory> {
    let mut mem = Memory::new(Galaxy::Sessions, content);
    mem.metadata.id = Uuid::new_v5(&namespace(), record_key.as_bytes());
    let dt = DateTime::<Utc>::from_timestamp_millis(ts_ms)
        .unwrap_or_else(|| Utc.timestamp_opt(0, 0).unwrap());
    mem.metadata.created_at = dt;
    mem.metadata.accessed_at = dt;
    mem.metadata.importance = importance;
    mem.metadata.tags = tags.to_vec();
    mem.metadata.source = "tool".into();
    mem.metadata.source_trust = 0.7;
    mem.metadata.coords = HolographicCoords {
        galaxy: SESSIONS_COORD_GALAXY,
        sector: 0,
        radial: 0.5,
        angular: 0.0,
        temporal: u64::try_from(ts_ms.max(0))
            .unwrap_or(0)
            .saturating_mul(1000), // µs
        consciousness: 0.5,
    };
    Ok(mem)
}

/// Run the export: `session.import`-compatible JSONL of opencode sessions.
///
/// # Errors
/// Fails loudly on missing/foreign DBs, tar failures, or SQLite errors.
pub fn run_export(
    db: &Path,
    sessions_filter: &[String],
    out: Option<&Path>,
    device: &str,
) -> Result<()> {
    let resolved = resolve_db(db)?;
    let conn = open_ro(&resolved)?;
    conn.execute_batch("BEGIN")?;
    let mut rows = load_sessions(&conn, None)?;
    if !sessions_filter.is_empty() {
        rows.retain(|r| {
            sessions_filter
                .iter()
                .any(|f| r.id.starts_with(f.as_str()) || r.slug.starts_with(f.as_str()))
        });
    }
    let (stats, skipped_malformed) = bulk_stats(&conn)?;
    conn.execute_batch("COMMIT")?;

    let stdout = std::io::stdout();
    let mut w: Box<dyn Write> = match out {
        Some(p) => Box::new(std::io::BufWriter::new(
            std::fs::File::create(p).with_context(|| format!("creating {}", p.display()))?,
        )),
        None => Box::new(stdout.lock()),
    };
    let mut n_turns = 0usize;
    for r in &rows {
        let wm_sid = namespace_uuid(&r.id).to_string();
        let project = project_name(&r.directory);
        let tags = vec![
            "source:opencode".to_string(),
            format!("project:{project}"),
            format!("device:{device}"),
            "session".to_string(),
        ];
        let title = if r.title.is_empty() {
            &r.slug
        } else {
            &r.title
        };
        let start = json!({
            "type": "session_start",
            "session_id": wm_sid,
            "title": format!("[opencode:{device}] {title}"),
            "user": "opencode-bridge",
            "timestamp": r.created_ms,
        });
        let mem = memory_envelope(
            &format!("opencode:{}:start", r.id),
            start.to_string(),
            &tags,
            0.5,
            r.created_ms,
        )?;
        writeln!(w, "{}", serde_json::to_string(&mem)?)?;

        let empty = SessionStat::default();
        let s = stats.get(&r.id).unwrap_or(&empty);
        for (seq, (text, role)) in s
            .user_texts
            .iter()
            .map(|t| (t, "user"))
            .chain(s.ai_texts.iter().map(|t| (t, "ai")))
            .enumerate()
        {
            let seq = seq + 1; // 1-based sequence, prototype parity
            let content = clip_turn(text);
            let turn = json!({
                "type": "session_turn",
                "session_id": wm_sid,
                "sequence": seq,
                "timestamp": r.created_ms + i64::try_from(seq).unwrap_or(i64::MAX),
                "role": role,
                "turn_type": "message",
                "content": content,
                "importance": 0.4,
            });
            let mem = memory_envelope(
                &format!("opencode:{}:turn:{}", r.id, seq),
                turn.to_string(),
                &tags,
                0.4,
                r.created_ms + i64::try_from(seq).unwrap_or(i64::MAX),
            )?;
            writeln!(w, "{}", serde_json::to_string(&mem)?)?;
            n_turns += 1;
        }
    }
    if let Some(p) = out {
        println!(
            "exported {} sessions / {n_turns} turns -> {} (skipped_malformed: {skipped_malformed})",
            rows.len(),
            p.display()
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Synthetic opencode DB exercising the columns the bridge reads.
    fn fixture_db(dir: &Path) -> PathBuf {
        let path = dir.join("opencode-test.db");
        let conn = Connection::open(&path).unwrap();
        conn.execute_batch(
            "CREATE TABLE session (id TEXT PRIMARY KEY, parent_id TEXT, slug TEXT,
                 directory TEXT, title TEXT, time_created INTEGER, time_updated INTEGER);
             CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT);
             CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, data TEXT);",
        )
        .unwrap();
        let base: i64 = 1_788_115_774_412; // fixed ms timestamp
        conn.execute(
            "INSERT INTO session VALUES ('ses_test1234', NULL, 'test-slug',
             '/home/lucas/Desktop/inspiron-games', 'Test session title', ?1, ?2)",
            [base, base + 60_000],
        )
        .unwrap();
        let msgs: &[(&str, &str, &str)] = &[
            (
                "m1",
                "ses_test1234",
                r#"{"role":"user","time":{"created":1}}"#,
            ),
            (
                "m2",
                "ses_test1234",
                r#"{"role":"assistant","tokens":{"input":100,"output":50},"cost":0.0125,"modelID":"test-model"}"#,
            ),
            ("m3", "ses_other", r#"{"role":"user"}"#),
            // malformed row: counted as skipped, never silently dropped
            ("m4", "ses_test1234", "not-json{{"),
        ];
        for (id, sid, data) in msgs {
            conn.execute("INSERT INTO message VALUES (?1, ?2, ?3)", [id, sid, data])
                .unwrap();
        }
        let parts: &[(&str, &str, &str)] = &[
            (
                "p1",
                "m1",
                r#"{"type":"text","text":"please check the battery bios kernel settings"}"#,
            ),
            (
                "p2",
                "m2",
                r#"{"type":"text","text":"The bios reports trickle charging now"}"#,
            ),
            (
                "p3",
                "m2",
                r#"{"type":"tool","state":{"status":"completed"}}"#,
            ),
            (
                "p4",
                "m1",
                r#"{"type":"text","text":"ses_ignored and now and battery"}"#,
            ),
            (
                "p5",
                "m3",
                r#"{"type":"text","text":"unrelated session text"}"#,
            ),
        ];
        for (id, mid, data) in parts {
            conn.execute("INSERT INTO part VALUES (?1, ?2, ?3)", [id, mid, data])
                .unwrap();
        }
        path
    }

    #[test]
    fn deterministic_ids_match_fleet_prototype() {
        // Golden values generated by the Python prototype:
        //   ns = uuid5(NAMESPACE_URL, "whitemagic:opencode-bridge")
        //   session = uuid5(ns, "opencode:ses_test1234")  etc.
        assert_eq!(
            namespace().to_string(),
            "b289fafa-a50c-564e-a55a-a702c555e81d"
        );
        assert_eq!(
            namespace_uuid("ses_test1234").to_string(),
            "1e5bfe69-0c33-5d56-a8cb-214113db53a1"
        );
        assert_eq!(
            Uuid::new_v5(&namespace(), b"opencode:ses_test1234:start").to_string(),
            "0c842a1c-e3c9-52fd-b404-b934e6b3471c"
        );
        assert_eq!(
            Uuid::new_v5(&namespace(), b"opencode:ses_test1234:turn:1").to_string(),
            "e0feea04-f52f-5dcd-92b4-2a4fb7782b50"
        );
    }

    #[test]
    fn digest_counts_tokens_cost_and_topics() {
        let dir = tempfile::tempdir().unwrap();
        let db = fixture_db(dir.path());
        let conn = open_ro(&db).unwrap();
        let sessions = load_sessions(&conn, None).unwrap();
        assert_eq!(sessions.len(), 1, "child session must be excluded");
        let (stats, skipped) = bulk_stats(&conn).unwrap();
        assert_eq!(skipped, 1, "malformed rows must be counted, not silent");
        let s = stats.get("ses_test1234").unwrap();
        assert_eq!(s.n_user, 1);
        assert_eq!(s.n_ai, 1);
        assert_eq!(s.n_tools, 1);
        assert_eq!(s.tokens, 150);
        assert!((s.cost - 0.0125).abs() < 1e-9);
        assert_eq!(s.model, "test-model");
        assert_eq!(s.user_texts.len(), 2);
        let other = stats.get("ses_other").unwrap();
        assert_eq!(other.n_user, 1, "cross-session separation");
        assert_eq!(other.n_ai, 0);
        let mut corpus = s.user_texts.clone();
        corpus.extend(s.ai_texts.iter().cloned());
        let topics = top_topics(&corpus, 6);
        assert!(
            topics.contains(&"battery".to_string()),
            "topics: {topics:?}"
        );
        assert!(!topics.contains(&"now".to_string()));
    }

    #[test]
    fn export_emits_importable_memory_envelopes() {
        let dir = tempfile::tempdir().unwrap();
        let db = fixture_db(dir.path());
        let out = dir.path().join("out.jsonl");
        run_export(&db, &[], Some(&out), "testseat").unwrap();
        let text = std::fs::read_to_string(&out).unwrap();
        let lines: Vec<&str> = text.lines().collect();
        assert_eq!(lines.len(), 4, "start + 2 user turns + 1 ai turn");

        for (i, line) in lines.iter().enumerate() {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            assert_eq!(v["metadata"]["galaxy"], "Sessions", "line {i}");
            let content: serde_json::Value =
                serde_json::from_str(v["content"].as_str().unwrap()).unwrap();
            assert_eq!(
                content["session_id"],
                "1e5bfe69-0c33-5d56-a8cb-214113db53a1"
            );
            if i == 0 {
                assert_eq!(content["type"], "session_start");
                assert_eq!(content["title"], "[opencode:testseat] Test session title");
            } else {
                assert_eq!(content["type"], "session_turn");
                assert_eq!(content["sequence"], i as u64);
                let want_role = if i <= 2 { "user" } else { "ai" };
                assert_eq!(content["role"], want_role, "line {i}");
            }
            assert_eq!(v["metadata"]["source"], "tool");
            assert_eq!(v["metadata"]["source_trust"], 0.7);
            assert_eq!(v["metadata"]["coords"]["galaxy"], 6);
            assert_eq!(v["metadata"]["importance"], if i == 0 { 0.5 } else { 0.4 });
        }
        // tags carry provenance
        let first: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
        let tags = first["metadata"]["tags"].as_array().unwrap();
        assert!(tags.iter().any(|t| t == "source:opencode"));
        assert!(tags.iter().any(|t| t == "device:testseat"));
    }

    #[test]
    fn digest_rejects_foreign_db() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("not-opencode.db");
        Connection::open(&path)
            .unwrap()
            .execute("CREATE TABLE x (a)", [])
            .unwrap();
        let err = run_digest(&path, None, false).unwrap_err();
        assert!(
            err.to_string().contains("not an opencode session DB"),
            "{err}"
        );
    }

    #[test]
    fn digest_since_filters_by_updated() {
        let dir = tempfile::tempdir().unwrap();
        let db = fixture_db(dir.path());
        let conn = open_ro(&db).unwrap();
        let future = "2087-01-01";
        let sessions = load_sessions(&conn, Some(future)).unwrap();
        assert!(sessions.is_empty(), "future filter must exclude fixture");
        let past = "2019-01-01";
        let sessions = load_sessions(&conn, Some(past)).unwrap();
        assert_eq!(sessions.len(), 1);
    }

    #[test]
    fn turn_truncation_clips_long_parts() {
        let long = "x".repeat(TURN_MAX + 5_000);
        let clipped = clip_turn(&long);
        assert_eq!(
            clipped.chars().count(),
            TURN_MAX + "\n… [truncated 5000 chars]".chars().count()
        );
        assert!(clipped.ends_with("[truncated 5000 chars]"));
        assert_eq!(clip_turn("short"), "short");
    }
}
