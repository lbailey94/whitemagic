use rusqlite::{Connection, OpenFlags, Result, params};
use serde_json::Value;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct RawSession {
    pub id: String,
    pub project_id: String,
    pub title: String,
    pub time_created: i64,
    pub time_updated: i64,
    pub cost: f64,
    pub tokens_input: i64,
    pub tokens_output: i64,
}

#[derive(Debug, Clone)]
pub struct NormalizedTurn {
    pub turn_id: String,
    pub session_id: String,
    pub seq: i64,
    pub role: String,
    pub turn_type: String,
    pub clean_text: String,
    pub importance: f64,
    pub valence: f64,
    pub time_created: i64,
    pub raw_message_id: String,
}

pub struct OpencodeExtractor {
    conn: Connection,
}

impl OpencodeExtractor {
    /// Open opencode.db in read-only, non-blocking mode
    pub fn open<P: AsRef<Path>>(path: P) -> Result<Self> {
        let uri = format!("file:{}?mode=ro&immutable=1", path.as_ref().display());
        let conn = Connection::open_with_flags(
            &uri,
            OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_URI,
        )?;

        conn.execute_batch(
            r#"
            PRAGMA query_only = ON;
            PRAGMA mmap_size = 268435456;
            "#,
        )?;

        Ok(Self { conn })
    }

    /// Open an existing connection directly (useful for testing or in-memory DBs)
    pub fn from_connection(conn: Connection) -> Self {
        Self { conn }
    }

    /// Read all sessions from opencode.db
    pub fn list_sessions(&self) -> Result<Vec<RawSession>> {
        let mut stmt = self.conn.prepare(
            r#"
            SELECT id, project_id, title, time_created, time_updated, cost, tokens_input, tokens_output
            FROM session
            ORDER BY time_created ASC
            "#,
        )?;

        let session_iter = stmt.query_map([], |row| {
            Ok(RawSession {
                id: row.get(0)?,
                project_id: row.get(1)?,
                title: row.get(2)?,
                time_created: row.get(3)?,
                time_updated: row.get(4)?,
                cost: row.get(5).unwrap_or(0.0),
                tokens_input: row.get(6).unwrap_or(0),
                tokens_output: row.get(7).unwrap_or(0),
            })
        })?;

        let mut out = Vec::new();
        for s in session_iter {
            out.push(s?);
        }
        Ok(out)
    }

    /// Extract and normalize all turns for a specific session
    pub fn extract_session_turns(&self, session_id: &str) -> Result<Vec<NormalizedTurn>> {
        let mut stmt = self.conn.prepare(
            r#"
            SELECT m.id, m.time_created, m.data, p.id, p.time_created, p.data
            FROM message m
            LEFT JOIN part p ON p.message_id = m.id
            WHERE m.session_id = ?1
            ORDER BY m.time_created ASC, p.time_created ASC
            "#,
        )?;

        let mut rows = stmt.query(params![session_id])?;
        let mut turns = Vec::new();
        let mut seq = 0;

        while let Some(row) = rows.next()? {
            let msg_id: String = row.get(0)?;
            let msg_time: i64 = row.get(1)?;
            let msg_data_str: String = row.get(2)?;
            let _part_id: Option<String> = row.get(3)?;
            let part_time: Option<i64> = row.get(4)?;
            let part_data_str: Option<String> = row.get(5)?;

            let time = part_time.unwrap_or(msg_time);

            // Parse message role
            let msg_data: Value = serde_json::from_str(&msg_data_str).unwrap_or(Value::Null);
            let role = msg_data
                .get("role")
                .and_then(|r| r.as_str())
                .unwrap_or("user")
                .to_string();

            // Extract content from part if present, else message
            let (raw_text, part_type) = if let Some(p_str) = part_data_str {
                let p_data: Value = serde_json::from_str(&p_str).unwrap_or(Value::Null);
                let p_type = p_data
                    .get("type")
                    .and_then(|t| t.as_str())
                    .unwrap_or("text")
                    .to_string();
                let text = if let Some(t) = p_data.get("text").and_then(|t| t.as_str()) {
                    t.to_string()
                } else if let Some(content) = p_data.get("content").and_then(|c| c.as_str()) {
                    content.to_string()
                } else {
                    p_data.to_string()
                };
                (text, p_type)
            } else {
                let text = msg_data
                    .get("content")
                    .and_then(|c| c.as_str())
                    .unwrap_or("")
                    .to_string();
                (text, "text".to_string())
            };

            let clean = sanitize_and_redact(&raw_text);
            if clean.trim().is_empty() {
                continue;
            }

            let turn_type = classify_turn_type(&role, &part_type, &clean);
            let importance = calculate_importance(&turn_type, &clean);
            let valence = calculate_valence(&turn_type, &clean);

            turns.push(NormalizedTurn {
                turn_id: format!("{session_id}-{seq}"),
                session_id: session_id.to_string(),
                seq,
                role,
                turn_type,
                clean_text: clean,
                importance,
                valence,
                time_created: time,
                raw_message_id: msg_id,
            });
            seq += 1;
        }

        Ok(turns)
    }
}

/// Sanitize text and redact secrets, excessive base64, and token noise
pub fn sanitize_and_redact(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    for line in input.lines() {
        // Redact potential API keys
        let redacted_line = redact_sensitive_patterns(line);
        out.push_str(&redacted_line);
        out.push('\n');
    }
    // Truncate overly long single outputs to prevent context pollution (max 4000 chars per turn)
    if out.len() > 4000 {
        let truncated = crate::safe_truncate(&out, 3900);
        let dropped = out.len() - truncated.len();
        format!("{}... [TRUNCATED {} BYTES]", truncated, dropped)
    } else {
        out
    }
}

fn redact_sensitive_patterns(line: &str) -> String {
    let mut s = line.to_string();
    // OpenAI / general sk- keys
    if s.contains("sk-") {
        s = regex_redact(&s, "sk-[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]");
    }
    // Google API Keys
    if s.contains("AIza") {
        s = regex_redact(&s, "AIza[a-zA-Z0-9_-]{35}", "[REDACTED_GOOGLE_KEY]");
    }
    if s.contains("BEGIN PRIVATE KEY") {
        return "[REDACTED_PRIVATE_KEY]".to_string();
    }
    s
}

fn regex_redact(text: &str, _pattern: &str, replacement: &str) -> String {
    // Basic fast string replacement for known security prefixes with punctuation preservation
    let mut result = String::new();
    let parts: Vec<&str> = text.split_whitespace().collect();
    for (i, word) in parts.iter().enumerate() {
        if i > 0 {
            result.push(' ');
        }
        let (core, trailing) = match word.chars().last() {
            Some(c) if c == '?' || c == '.' || c == '!' || c == ',' || c == ':' || c == ';' => {
                (&word[..word.len() - c.len_utf8()], Some(c))
            }
            _ => (*word, None),
        };

        if (core.starts_with("sk-") && core.len() > 20)
            || (core.starts_with("AIza") && core.len() > 30)
        {
            result.push_str(replacement);
            if let Some(c) = trailing {
                result.push(c);
            }
        } else {
            result.push_str(word);
        }
    }
    if result.is_empty() {
        text.to_string()
    } else {
        result
    }
}

/// Classify turn type into one of the 9 canonical WhiteMagic turn types
pub fn classify_turn_type(role: &str, part_type: &str, text: &str) -> String {
    let lower = text.to_lowercase();

    if part_type == "tool" || part_type == "tool_use" {
        if lower.contains("write") || lower.contains("replace") || lower.contains("patch") {
            return "code_change".to_string();
        } else if lower.contains("error") || lower.contains("failed") || lower.contains("panic") {
            return "error".to_string();
        } else {
            return "context".to_string();
        }
    }

    if role == "user" {
        if lower.contains('?')
            || lower.starts_with("how")
            || lower.starts_with("why")
            || lower.starts_with("what")
            || lower.starts_with("can we")
            || lower.starts_with("could we")
        {
            "question".to_string()
        } else {
            "message".to_string()
        }
    } else if role == "assistant" {
        if lower.contains("test result: ok")
            || lower.contains("tests pass")
            || lower.contains("breakthrough")
            || lower.contains("verified")
            || lower.contains("closure 1")
            || lower.contains("100% green")
        {
            "breakthrough".to_string()
        } else if lower.contains("i will")
            || lower.contains("we should")
            || lower.contains("ratified")
            || lower.contains("architectural decision")
            || lower.contains("directive")
        {
            "decision".to_string()
        } else if lower.contains("summary") || lower.contains("checkpoint") {
            "summary".to_string()
        } else {
            "answer".to_string()
        }
    } else {
        "context".to_string()
    }
}

/// Heuristic importance score calculation (0.0 to 1.0)
pub fn calculate_importance(turn_type: &str, text: &str) -> f64 {
    let mut score = match turn_type {
        "breakthrough" => 0.95,
        "decision" => 0.85,
        "question" => 0.70,
        "code_change" => 0.65,
        "error" => 0.60,
        "summary" => 0.75,
        "answer" => 0.55,
        "message" => 0.50,
        _ => 0.40,
    };

    let lower = text.to_lowercase();
    // Keywords indicating foundational architectural relevance
    let keywords = [
        "covenant",
        "charter",
        "mandala",
        "landlock",
        "shm",
        "geth",
        "stigmergy",
        "linda",
        "tuple",
        "sub-symbolic",
        "lucas",
        "kadag",
        "lhun-grub",
        "citta",
        "dream",
        "ganying",
        "scitt",
    ];

    for kw in &keywords {
        if lower.contains(kw) {
            score = (score + 0.05f64).min(1.0f64);
        }
    }

    score
}

/// Heuristic affective valence score (-1.0 to 1.0)
pub fn calculate_valence(turn_type: &str, text: &str) -> f64 {
    let lower = text.to_lowercase();
    if turn_type == "breakthrough"
        || lower.contains("success")
        || lower.contains("triumph")
        || lower.contains("incredible")
    {
        0.8
    } else if turn_type == "error"
        || lower.contains("panic")
        || lower.contains("deadlock")
        || lower.contains("failed")
    {
        -0.7
    } else {
        0.0
    }
}
