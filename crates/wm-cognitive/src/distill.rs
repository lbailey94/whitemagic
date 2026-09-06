//! S7 distillation pipeline — deterministic session-file layer +
//! question-addressed topic summaries (`V8_BUILD_PLAN.md` S7,
//! `V8_DISTILLATION_DESIGN.md` §2, `MEMORY_TYPOLOGY_V8.md` classes).
//!
//! The mac-stranger corpus proved a three-tier funnel by hand: raw
//! transcripts → per-session files with provenance headers → atomic
//! catalog entries. This module makes the middle tier native:
//!
//! 1. **Deterministic session-file layer** (LLM-free, reproducible):
//!    every session in the Sessions galaxy becomes a digest record whose
//!    provenance header carries exactly what the §2 keep-list mandates —
//!    session id, date span, workspace, model + cost + token counts
//!    *or an explicit "not tracked" disclosure*, and a statement of what
//!    was dropped next to what was kept.
//! 2. **Question-addressed topic summaries** (the generalization of
//!    `phase_narrative`): cross-session aggregation per topic/entity,
//!    each anchored to the corpus question it answers ("Q: What do the
//!    sessions say about X?"), every evidence line citing its source
//!    session. Topics derive from turn `topic` fields (envelope v2),
//!    non-structural tags, and high-frequency entities.
//! 3. **LLM synthesis only above** the deterministic layer: when an LLM
//!    is configured (`WM_LLM_API_KEY`), a synthesis section is added;
//!    without one the deterministic layer alone is fully functional and
//!    the record discloses `llm: none` — no silent capability claims.
//!
//! Distillates land in the Dreams galaxy (dream-owned outputs), are
//! stamped [`MemoryClass::Knowledge`] explicitly (the dream *knows* it
//! synthesized knowledge — no guessing), and inherit provenance into
//! memory metadata: `distill:session:<id>` tags bind every contributing
//! source session, `source`/`agent_id` name the dream, and importance is
//! an evidence prior (distinct sessions, turns, importance mass) with
//! cost/token mass as a capped nudge — never the sole signal.

use std::collections::HashMap;
use std::fmt::Write as _;

use wm_bicameral::TierHandler as _;
use wm_memory::Memory;
use wm_memory::typology::{MemoryClass, apply_class_policy};

use crate::miner::AssociationMiner;

/// Maximum topic summaries synthesized per dream cycle — bounds rewrite
/// churn while the corpus grows.
pub const MAX_TOPICS_PER_CYCLE: usize = 4;

/// Minimum turns in a session before it earns a digest record.
pub const MIN_TURNS_PER_SESSION: usize = 2;

/// Minimum distinct sessions behind a topic summary (cross-session is the
/// point; single-session questions are answered by the session layer).
pub const MIN_SESSIONS_PER_TOPIC: usize = 2;

/// Maximum LLM synthesis calls per dream cycle — the synthesis layer is
/// bounded so a slow endpoint (see `WM_LLM_TIMEOUT_MS`) cannot stall sleep.
pub const MAX_LLM_SYNTH_PER_CYCLE: usize = 2;

/// Tags that describe the *logging* of a turn rather than its subject —
/// excluded from topic derivation.
const STRUCTURAL_TAGS: [&str; 10] = [
    "session",
    "start",
    "turn",
    "message",
    "summary",
    "checkpoint",
    "error",
    "context",
    "ai",
    "user",
];

// ── Deterministic session-file layer ────────────────────────────────────

/// One source turn, parsed from a `session_turn` record.
#[derive(Debug, Clone)]
pub struct TurnRecord {
    /// Memory id of the turn (provenance pointer).
    pub memory_id: String,
    /// Owning session id (from the record body, `session:` tag fallback).
    pub session_id: String,
    /// `user` or `ai`.
    pub role: String,
    /// `message`, `decision`, `breakthrough`, …
    pub turn_type: String,
    /// Turn timestamp (unix millis; falls back to the memory's own
    /// `created_at` — disclosed in the span line, never invented).
    pub timestamp_ms: i64,
    /// Text-parts-only body.
    pub text: String,
    /// Token count when the source record tracks one; `None` = not tracked.
    pub tokens: Option<u64>,
    /// Cost when the source record tracks one; `None` = not tracked.
    pub cost: Option<f64>,
    /// Turn importance from the source record.
    pub importance: f32,
    /// Explicit `topic` metadata on the source turn (envelope v2), if any.
    pub topic_field: Option<String>,
    /// Non-provenance tags on the source turn (topic candidates).
    pub subject_tags: Vec<String>,
}

/// One session rendered in the deterministic session-file shape.
#[derive(Debug, Clone, Default)]
pub struct SessionFile {
    /// Session id (the `session_start` memory id).
    pub session_id: String,
    /// Session title (or `Untitled` — disclosed, not fabricated).
    pub title: String,
    /// Session user / workspace label.
    pub workspace: String,
    /// Project-granularity category (`WM_PROJECT` env, else `general` —
    /// the honest unknown of §2).
    pub category: String,
    /// Turns in session order.
    pub turns: Vec<TurnRecord>,
    /// First-turn timestamp (unix millis; 0 = unknown).
    pub span_start_ms: i64,
    /// Last-turn timestamp (unix millis; 0 = unknown).
    pub span_end_ms: i64,
}

impl SessionFile {
    /// `(user, ai)` turn counts.
    #[must_use]
    pub fn role_counts(&self) -> (usize, usize) {
        let ai = self.turns.iter().filter(|t| t.role == "ai").count();
        let user = self.turns.iter().filter(|t| t.role == "user").count();
        (user, ai)
    }

    /// Turns by `turn_type` (deterministic order of first appearance).
    #[must_use]
    pub fn type_counts(&self) -> Vec<(String, usize)> {
        let mut order: Vec<String> = Vec::new();
        let mut counts: HashMap<String, usize> = HashMap::new();
        for t in &self.turns {
            if !counts.contains_key(&t.turn_type) {
                order.push(t.turn_type.clone());
            }
            *counts.entry(t.turn_type.clone()).or_insert(0) += 1;
        }
        order
            .into_iter()
            .map(|k| {
                let n = counts.get(&k).copied().unwrap_or(0);
                (k, n)
            })
            .collect()
    }

    /// Total tracked tokens across turns (`None` when the corpus does not
    /// track them — the header must disclose absence, not invent a number).
    #[must_use]
    pub fn total_tokens(&self) -> Option<u64> {
        let mut total: u64 = 0;
        let mut any = false;
        for t in &self.turns {
            if let Some(n) = t.tokens {
                any = true;
                total = total.saturating_add(n);
            }
        }
        if any { Some(total) } else { None }
    }

    /// Total tracked cost across turns (`None` when untracked).
    #[must_use]
    pub fn total_cost(&self) -> Option<f64> {
        let mut total: f64 = 0.0;
        let mut any = false;
        for t in &self.turns {
            if let Some(c) = t.cost {
                any = true;
                total += c;
            }
        }
        if any { Some(total) } else { None }
    }

    /// Render the deterministic session file (the §2 provenance-header
    /// format, adapted to native session records).
    #[must_use]
    pub fn to_markdown(&self) -> String {
        let (users, ais) = self.role_counts();
        let types = self
            .type_counts()
            .iter()
            .map(|(k, n)| format!("{k}:{n}"))
            .collect::<Vec<_>>()
            .join(", ");
        let tokens = self.total_tokens().map_or_else(
            || "not tracked in source records".to_string(),
            |n| n.to_string(),
        );
        let cost = self.total_cost().map_or_else(
            || "not tracked in source records".to_string(),
            |c| format!("${c:.4}"),
        );

        let mut md = String::new();
        write!(md, "## distill:session {}\n\n", self.session_id)
            .expect("writing to a String cannot fail");
        writeln!(md, "- title: {}", self.title).expect("writing to a String cannot fail");
        writeln!(
            md,
            "- span: {} .. {}",
            fmt_millis(self.span_start_ms),
            fmt_millis(self.span_end_ms)
        )
        .expect("writing to a String cannot fail");
        writeln!(md, "- turns: {} (user {users}, ai {ais})", self.turns.len())
            .expect("writing to a String cannot fail");
        if !types.is_empty() {
            writeln!(md, "- turn types: {types}").expect("writing to a String cannot fail");
        }
        writeln!(md, "- tokens: {tokens}").expect("writing to a String cannot fail");
        writeln!(md, "- cost: {cost}").expect("writing to a String cannot fail");
        writeln!(md, "- category: {}", self.category).expect("writing to a String cannot fail");
        writeln!(md, "- workspace: {}", self.workspace).expect("writing to a String cannot fail");
        md.push_str(
            "- provenance: deterministic distillation by the dream Narrative phase (S7);\n\
             \x20 what was dropped: tool payloads and embeddings — text parts only.\n\
             \x20 Raw turns remain in the sessions galaxy (ids listed under sources).\n",
        );
        writeln!(
            md,
            "- sources: {}",
            self.turns
                .iter()
                .map(|t| t.memory_id.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        )
        .expect("writing to a String cannot fail");
        md.push('\n');
        for t in &self.turns {
            write!(md, "### {} / {}\n\n", t.role, t.turn_type)
                .expect("writing to a String cannot fail");
            md.push_str(t.text.trim());
            md.push_str("\n\n");
        }
        md
    }
}

/// Parse a `session_start` memory into a `SessionFile` skeleton.
#[must_use]
pub fn session_file_from_start(mem: &Memory) -> Option<SessionFile> {
    let v: serde_json::Value = serde_json::from_str(&mem.content).ok()?;
    if v.get("type").and_then(serde_json::Value::as_str) != Some("session_start") {
        return None;
    }
    let title = v
        .get("title")
        .and_then(serde_json::Value::as_str)
        .unwrap_or("Untitled")
        .to_string();
    let workspace = v
        .get("user")
        .and_then(serde_json::Value::as_str)
        .unwrap_or("unknown")
        .to_string();
    Some(SessionFile {
        session_id: mem.metadata.id.to_string(),
        title,
        workspace,
        category: project_category(),
        turns: Vec::new(),
        span_start_ms: 0,
        span_end_ms: 0,
    })
}

/// Parse a `session_turn` memory into a `TurnRecord`.
#[must_use]
pub fn turn_record_from_memory(mem: &Memory) -> Option<TurnRecord> {
    let v: serde_json::Value = serde_json::from_str(&mem.content).ok()?;
    if v.get("type").and_then(serde_json::Value::as_str) != Some("session_turn") {
        return None;
    }
    let text = v
        .get("content")
        .and_then(serde_json::Value::as_str)
        .unwrap_or("")
        .to_string();
    let subject_tags = mem
        .metadata
        .tags
        .iter()
        .filter(|t| {
            !STRUCTURAL_TAGS.contains(&t.as_str())
                && !t.starts_with("session:")
                && !t.starts_with("supersedes:")
                && !t.starts_with("superseded-by:")
        })
        .cloned()
        .collect();
    let session_id = v
        .get("session_id")
        .and_then(serde_json::Value::as_str)
        .map(str::to_string)
        .or_else(|| {
            mem.metadata
                .tags
                .iter()
                .find(|t| t.starts_with("session:"))
                .map(|t| t.trim_start_matches("session:").to_string())
        })
        .unwrap_or_default();
    Some(TurnRecord {
        memory_id: mem.metadata.id.to_string(),
        session_id,
        role: v
            .get("role")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("unknown")
            .to_string(),
        turn_type: v
            .get("turn_type")
            .and_then(serde_json::Value::as_str)
            .unwrap_or("message")
            .to_string(),
        timestamp_ms: v
            .get("timestamp")
            .and_then(serde_json::Value::as_i64)
            .unwrap_or_else(|| mem.metadata.created_at.timestamp_millis()),
        text,
        tokens: v.get("tokens").and_then(serde_json::Value::as_u64),
        cost: v.get("cost").and_then(serde_json::Value::as_f64),
        importance: mem.metadata.importance,
        topic_field: mem.metadata.topic.clone(),
        subject_tags,
    })
}

/// Project-granularity category: the store is per-project by
/// construction, so `WM_PROJECT` (when set) *is* the category; its
/// absence is the honest unknown (`general`), never a guess.
#[must_use]
pub fn project_category() -> String {
    std::env::var("WM_PROJECT")
        .ok()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| "general".to_string())
}

/// Format a unix-millis timestamp for provenance spans (`unknown` when 0).
#[must_use]
pub fn fmt_millis(ms: i64) -> String {
    if ms <= 0 {
        return "unknown".to_string();
    }
    chrono::DateTime::from_timestamp_millis(ms)
        .map_or_else(|| "unknown".to_string(), |dt| dt.to_rfc3339())
}

// ── Question-addressed topic layer ──────────────────────────────────────

/// Evidence accumulated for one topic across sessions.
#[derive(Debug, Clone)]
pub struct TopicEvidence {
    /// The topic/entity label.
    pub topic: String,
    /// Distinct source sessions contributing evidence.
    pub sessions: Vec<String>,
    /// Total source turns.
    pub turn_count: usize,
    /// Sum of source-turn importance (mass, averaged on read).
    pub importance_mass: f32,
    /// Tracked token mass across contributing turns (`None` = untracked).
    pub tokens: Option<u64>,
    /// Tracked cost mass (`None` = untracked).
    pub cost: Option<f64>,
    /// Evidence lines: (session id, timestamp ms, excerpt ≤200 chars).
    pub evidence: Vec<(String, i64, String)>,
}

impl TopicEvidence {
    /// Cross-session strength prior in [0,1]: evidence counts dominate;
    /// cost/token mass may only nudge (capped at +0.05 each), never decide.
    #[allow(clippy::suboptimal_flops)] // deterministic scorer convention
    #[must_use]
    pub fn importance_prior(&self) -> f32 {
        let session_term = 0.12 * self.sessions.len().min(5) as f32;
        let turn_term = 0.03 * self.turn_count.min(10) as f32;
        let mass_term = 0.2 * (self.importance_mass / self.turn_count.max(1) as f32);
        let token_bonus = self.tokens.map_or(0.0, |n| {
            (0.05f32 * (n as f32 / 100_000.0).ln_1p()).min(0.05)
        });
        let cost_bonus = self
            .cost
            .map_or(0.0, |c| (0.05f32 * (c as f32).ln_1p()).min(0.05));
        (0.3 + session_term + turn_term + mass_term + token_bonus + cost_bonus).clamp(0.0, 1.0)
    }

    /// Fingerprint of the evidence set — when unchanged between dream
    /// cycles the topic summary is skipped (no rewrite churn).
    #[must_use]
    pub fn fingerprint(&self) -> u64 {
        let mut ids = self.sessions.clone();
        ids.sort();
        let material = format!(
            "{}|{}|{}|{:?}",
            ids.join(","),
            self.turn_count,
            self.evidence.len(),
            self.evidence
                .iter()
                .map(|(s, t, _)| (s.clone(), *t))
                .collect::<Vec<_>>()
        );
        // FNV-1a-style fold over a seeded constant — deterministic, cheap.
        material.bytes().fold(0xcbf2_9ce4_8422_2325u64, |acc, b| {
            (acc ^ u64::from(b))
                .wrapping_mul(0x0000_0100_0000_01b3)
                .wrapping_add(0x9e37_79b9_7f4a_7c15)
        })
    }

    /// Render the question-addressed topic summary (deterministic layer).
    ///
    /// `llm_synthesis` carries the LLM paragraph when a real LLM is
    /// configured — it is added ABOVE the deterministic evidence, never
    /// instead of it.
    #[must_use]
    pub fn to_markdown(&self, llm_synthesis: Option<&str>) -> String {
        let mut md = String::new();
        write!(md, "## distill:topic {}\n\n", self.topic).expect("writing to a String cannot fail");
        write!(
            md,
            "Q: What do the sessions say about \"{}\" across {} sessions?\n\n",
            self.topic,
            self.sessions.len()
        )
        .expect("writing to a String cannot fail");
        md.push_str("A (deterministic, session-grounded):\n\n");
        for (sid, ts, excerpt) in &self.evidence {
            writeln!(md, "- [{sid} | {}] {excerpt}", fmt_millis(*ts))
                .expect("writing to a String cannot fail");
        }
        md.push('\n');
        if let Some(para) = llm_synthesis {
            write!(md, "Synthesis (LLM):\n\n{para}\n\n").expect("writing to a String cannot fail");
        } else {
            md.push_str("Synthesis (LLM): none configured — deterministic layer only.\n\n");
        }
        writeln!(
            md,
            "Provenance: {} session turns from sessions {}; span {} .. {}; \
             importance prior {:.2} (evidence-based; cost/token mass as capped prior).",
            self.turn_count,
            self.sessions.join(", "),
            fmt_millis(self.evidence.first().map_or(0, |(s, t, _)| {
                let _ = s;
                *t
            })),
            fmt_millis(self.evidence.last().map_or(0, |(s, t, _)| {
                let _ = s;
                *t
            })),
            self.importance_prior()
        )
        .expect("writing to a String cannot fail");
        md
    }
}

/// Candidate topics ranked by evidence strength, capped at
/// [`MAX_TOPICS_PER_CYCLE`].
///
/// Derivation sources (all deterministic): turn `topic` metadata (envelope
/// v2), non-structural tags, session-title subjects, and high-frequency
/// entities extracted from turn text. A topic must span at least
/// [`MIN_SESSIONS_PER_TOPIC`] sessions and [`MIN_TURNS_PER_SESSION`] turns.
#[must_use]
pub fn derive_topics(files: &[SessionFile]) -> Vec<TopicEvidence> {
    let mut by_topic: HashMap<String, TopicEvidence> = HashMap::new();

    for file in files {
        for turn in &file.turns {
            let mut candidates: Vec<String> = Vec::new();
            if let Some(t) = turn
                .topic_field
                .as_deref()
                .map(str::trim)
                .filter(|t| !t.is_empty())
            {
                candidates.push(t.to_string());
            }
            candidates.extend(turn.subject_tags.iter().cloned());
            if candidates.is_empty() {
                // Entity fallback: high-frequency keywords from the text.
                candidates.extend(
                    AssociationMiner::extract_keywords(&turn.text, 2)
                        .into_iter()
                        .filter(|kw| !STRUCTURAL_TAGS.contains(&kw.as_str())),
                );
            }
            candidates.dedup();
            for topic in candidates {
                bump_topic(&mut by_topic, &topic, file, turn);
            }
        }
    }

    // Session titles are themselves subject labels — bind title subjects
    // to the session (evidence, not turns).
    for file in files {
        let title = file.title.trim();
        if title.len() > 3 {
            for kw in AssociationMiner::extract_keywords(title, 2) {
                if STRUCTURAL_TAGS.contains(&kw.as_str()) {
                    continue;
                }
                if let Some(entry) = by_topic.get_mut(&kw) {
                    if !entry.sessions.contains(&file.session_id) {
                        entry.sessions.push(file.session_id.clone());
                    }
                }
            }
        }
    }

    let mut topics: Vec<TopicEvidence> = by_topic
        .into_values()
        .filter(|t| {
            t.sessions.len() >= MIN_SESSIONS_PER_TOPIC && t.turn_count >= MIN_TURNS_PER_SESSION
        })
        .collect();
    topics.sort_by(|a, b| {
        b.importance_prior()
            .partial_cmp(&a.importance_prior())
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    topics.truncate(MAX_TOPICS_PER_CYCLE);
    topics
}

fn bump_topic(
    by_topic: &mut HashMap<String, TopicEvidence>,
    topic: &str,
    file: &SessionFile,
    turn: &TurnRecord,
) {
    let entry = by_topic
        .entry(topic.to_string())
        .or_insert_with(|| TopicEvidence {
            topic: topic.to_string(),
            sessions: Vec::new(),
            turn_count: 0,
            importance_mass: 0.0,
            tokens: None,
            cost: None,
            evidence: Vec::new(),
        });
    entry.turn_count += 1;
    entry.importance_mass += turn.importance;
    if let Some(n) = turn.tokens {
        *entry.tokens.get_or_insert(0) += n;
    }
    if let Some(c) = turn.cost {
        *entry.cost.get_or_insert(0.0) += c;
    }
    if !entry.sessions.contains(&file.session_id) {
        entry.sessions.push(file.session_id.clone());
    }
    if entry.evidence.len() < 6 && !turn.text.trim().is_empty() {
        let excerpt: String = turn.text.trim().chars().take(200).collect();
        entry
            .evidence
            .push((file.session_id.clone(), turn.timestamp_ms, excerpt));
    }
}

/// Build the per-run distillation index (the `index.json` analog of §2 —
/// a cheap machine-readable catalog of what was distilled).
#[must_use]
pub fn index_markdown(files: &[SessionFile], topics: &[TopicEvidence]) -> String {
    let mut md = String::from("## distill:index\n\n");
    md.push_str("| session | category | title | turns | span end |\n|---|---|---|---|---|\n");
    for f in files {
        writeln!(
            md,
            "| {} | {} | {} | {} | {} |",
            f.session_id,
            f.category,
            f.title,
            f.turns.len(),
            fmt_millis(f.span_end_ms)
        )
        .expect("writing to a String cannot fail");
    }
    md.push_str("\nTopics this run:\n\n");
    for t in topics {
        writeln!(
            md,
            "- {} ({} sessions, {} turns, prior {:.2})",
            t.topic,
            t.sessions.len(),
            t.turn_count,
            t.importance_prior()
        )
        .expect("writing to a String cannot fail");
    }
    md
}

/// Build the memory for a distillate (Dreams galaxy, `Knowledge` class).
///
/// Stamps provenance explicitly: `distill:session:<id>` tags bind every
/// contributing source session, `source`/`agent_id` name the dream, and
/// title/topic metadata carry the envelope-v2 subject fields.
#[must_use]
pub fn distill_memory(
    content: String,
    title: String,
    topic: String,
    namespace: &str,
    source_sessions: &[String],
    importance: f32,
) -> Memory {
    let mut mem = Memory::new(wm_core::Galaxy::Dreams, content);
    mem.metadata.memory_type = wm_memory::MemoryType::Narrative;
    mem.metadata.class = Some(MemoryClass::Knowledge);
    // Class policy applied, not bypassed (S5p1 rules): Knowledge is
    // identity in v0 — the call documents intent at the stamp site.
    mem.metadata.importance = apply_class_policy(MemoryClass::Knowledge, importance);
    mem.metadata.title = Some(title);
    mem.metadata.topic = Some(topic);
    mem.metadata.source = "dream:distill".to_string();
    mem.metadata.source_trust = 0.7;
    mem.metadata.agent_id = "dream-cycle".to_string();
    let mut tags = vec!["distill".to_string(), namespace.to_string()];
    for sid in source_sessions {
        tags.push(format!("distill:session:{sid}"));
    }
    tags.dedup();
    mem.metadata.tags = tags;
    mem
}

/// Slugify a topic label for tag namespaces (`distill:topic:<slug>`):
/// lowercase, non-alphanumeric runs collapse to `-`. Deterministic.
#[must_use]
pub fn slug(topic: &str) -> String {
    let mut out = String::new();
    let mut prev_dash = true; // suppress leading dash
    for ch in topic.chars() {
        if ch.is_alphanumeric() {
            out.extend(ch.to_lowercase());
            prev_dash = false;
        } else if !prev_dash {
            out.push('-');
            prev_dash = true;
        }
    }
    while out.ends_with('-') {
        out.pop();
    }
    if out.is_empty() {
        "unnamed".to_string()
    } else {
        out
    }
}

/// LLM synthesis ABOVE the deterministic layer: ground the model in the
/// evidence lines and return the disclosed synthesis paragraph.
///
/// Errors are disclosed, never swallowed — the deterministic layer stands
/// either way. Returns `None` when the caller passed no LLM.
#[must_use]
pub fn synthesize_with_llm(
    llm: &wm_bicameral::LlmTierHandler,
    topic: &TopicEvidence,
) -> Option<String> {
    let evidence = topic
        .evidence
        .iter()
        .take(6)
        .map(|(sid, _, excerpt)| format!("- [{sid}] {excerpt}"))
        .collect::<Vec<_>>()
        .join("\n");
    let prompt = format!(
        "You are distilling WhiteMagic session memory. Question: What do the \
         sessions say about \"{}\"? Evidence from {} sessions:\n{}\n\nWrite 2-3 \
         sentences of grounded synthesis. Use only the evidence above.",
        topic.topic,
        topic.sessions.len(),
        evidence
    );
    match llm.handle(&prompt, 300) {
        Ok((text, confidence)) => {
            let text = text.trim();
            if text.is_empty() {
                Some("llm returned empty synthesis — deterministic layer stands.".to_string())
            } else {
                Some(format!("{text}\n\n(llm confidence {confidence:.2})"))
            }
        }
        Err(e) => Some(format!(
            "llm synthesis failed ({e}) — deterministic layer stands."
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Galaxy;

    fn turn(
        role: &str,
        turn_type: &str,
        text: &str,
        ts_ms: i64,
        topic: Option<&str>,
    ) -> TurnRecord {
        TurnRecord {
            memory_id: uuid::Uuid::new_v4().to_string(),
            session_id: "a".to_string(),
            role: role.to_string(),
            turn_type: turn_type.to_string(),
            timestamp_ms: ts_ms,
            text: text.to_string(),
            tokens: None,
            cost: None,
            importance: 0.5,
            topic_field: topic.map(str::to_string),
            subject_tags: Vec::new(),
        }
    }

    fn session(id: &str, title: &str, turns: Vec<TurnRecord>) -> SessionFile {
        let span_start = turns.first().map_or(0, |t| t.timestamp_ms);
        let span_end = turns.last().map_or(0, |t| t.timestamp_ms);
        SessionFile {
            session_id: id.to_string(),
            title: title.to_string(),
            workspace: "default".to_string(),
            category: "test-project".to_string(),
            turns,
            span_start_ms: span_start,
            span_end_ms: span_end,
        }
    }

    #[test]
    fn slug_is_deterministic_and_tag_safe() {
        assert_eq!(slug("Topic X"), "topic-x");
        assert_eq!(slug("  weird!!tag__name  "), "weird-tag-name");
        assert_eq!(slug("!!!"), "unnamed");
        assert_eq!(slug("distillation"), "distillation");
    }

    #[test]
    fn session_file_markdown_carries_provenance_header() {
        let f = session(
            "sess-1",
            "distillation design",
            vec![
                turn(
                    "user",
                    "message",
                    "how should distillation work?",
                    1_700_000_000_000,
                    None,
                ),
                turn(
                    "ai",
                    "decision",
                    "deterministic layer first, LLM above",
                    1_700_000_100_000,
                    None,
                ),
            ],
        );
        let md = f.to_markdown();
        assert!(md.contains("## distill:session sess-1"));
        assert!(md.contains("- title: distillation design"));
        assert!(md.contains("- span: "));
        assert!(md.contains("- tokens: not tracked in source records"));
        assert!(md.contains("what was dropped: tool payloads"));
        assert!(md.contains("- category: test-project"));
        assert!(md.contains("- sources: "));
        assert!(md.contains("deterministic layer first"));
    }

    #[test]
    fn token_cost_tracking_sums_when_present() {
        let mut f = session(
            "sess-2",
            "costly session",
            vec![turn("ai", "message", "expensive reasoning", 1, None)],
        );
        f.turns[0].tokens = Some(7_900_000);
        f.turns[0].cost = Some(3.39);
        let md = f.to_markdown();
        assert!(md.contains("- tokens: 7900000"));
        assert!(md.contains("- cost: $3.3900"));
        assert_eq!(f.total_tokens(), Some(7_900_000));
    }

    #[test]
    fn topics_require_cross_session_evidence() {
        let files = vec![
            session(
                "a",
                "topic x exploration",
                vec![
                    turn(
                        "user",
                        "question",
                        "what about topic x?",
                        1,
                        Some("topic x"),
                    ),
                    turn(
                        "ai",
                        "answer",
                        "topic x works via yama gating",
                        2,
                        Some("topic x"),
                    ),
                ],
            ),
            session(
                "b",
                "more topic x",
                vec![
                    turn("user", "message", "topic x again", 3, Some("topic x")),
                    turn("ai", "breakthrough", "topic x accepted", 4, Some("topic x")),
                ],
            ),
            session(
                "c",
                "unrelated single mention",
                vec![turn(
                    "user",
                    "message",
                    "one-off other thing",
                    5,
                    Some("solo"),
                )],
            ),
        ];
        let topics = derive_topics(&files);
        assert!(!topics.is_empty());
        let tx = topics
            .iter()
            .find(|t| t.topic == "topic x")
            .expect("topic x derived");
        assert_eq!(tx.sessions.len(), 2, "cross-session requirement");
        assert_eq!(tx.turn_count, 4);
        // 'solo' appears in one session with one turn — must not qualify.
        assert!(topics.iter().all(|t| t.topic != "solo"));
    }

    #[test]
    fn topic_summary_is_question_addressed_with_provenance() {
        let mut f = session(
            "a",
            "t",
            vec![turn(
                "ai",
                "decision",
                "yama gates dream writes",
                1,
                Some("yama"),
            )],
        );
        f.turns[0].tokens = Some(50_000);
        let files = vec![
            f,
            session(
                "b",
                "t2",
                vec![turn(
                    "user",
                    "message",
                    "yama budget shared",
                    2,
                    Some("yama"),
                )],
            ),
        ];
        let topics = derive_topics(&files);
        let yama = topics.iter().find(|t| t.topic == "yama").unwrap();
        let md = yama.to_markdown(None);
        assert!(md.contains("Q: What do the sessions say about \"yama\" across 2 sessions?"));
        assert!(md.contains("- [a | "));
        assert!(md.contains("Synthesis (LLM): none configured — deterministic layer only."));
        assert!(md.contains("distill:session:a") || md.contains("sessions a, b"));
        // Token prior nudges but cannot decide: prior stays in [0,1] and
        // evidence dominates the shape of the number.
        let prior = yama.importance_prior();
        assert!((0.0..=1.0).contains(&prior));
        // Fingerprint stable and evidence-sensitive.
        assert_eq!(yama.fingerprint(), yama.fingerprint());
        let mut changed = yama.clone();
        changed.turn_count += 1;
        assert_ne!(yama.fingerprint(), changed.fingerprint());
    }

    #[test]
    fn distill_memory_stamps_knowledge_class_and_session_tags() {
        let mem = distill_memory(
            "## distill:topic t\nQ: ...".to_string(),
            "Distill: t".to_string(),
            "t".to_string(),
            "distill:topic:t",
            &["s1".to_string(), "s2".to_string()],
            0.62,
        );
        assert_eq!(mem.metadata.galaxy, Galaxy::Dreams);
        assert_eq!(mem.metadata.class, Some(MemoryClass::Knowledge));
        assert_eq!(mem.metadata.source, "dream:distill");
        assert_eq!(mem.metadata.agent_id, "dream-cycle");
        assert_eq!(mem.metadata.topic.as_deref(), Some("t"));
        assert!(
            mem.metadata
                .tags
                .contains(&"distill:session:s1".to_string())
        );
        assert!(
            mem.metadata
                .tags
                .contains(&"distill:session:s2".to_string())
        );
    }

    #[test]
    fn roundtrip_parse_from_store_records() {
        let mut start = Memory::new(
            Galaxy::Sessions,
            r#"{"type":"session_start","title":"S7 work","user":"lucas"}"#.to_string(),
        );
        start.metadata.tags = vec!["session".into(), "start".into()];
        let sf = session_file_from_start(&start).unwrap();
        assert_eq!(sf.title, "S7 work");
        assert_eq!(sf.workspace, "lucas");

        let mut tm = Memory::new(
            Galaxy::Sessions,
            r#"{"type":"session_turn","session_id":"x","sequence":1,"role":"ai","turn_type":"decision","importance":0.8,"content":"the yama hook lands","timestamp":1700000000000}"#.to_string(),
        );
        tm.metadata.tags = vec![
            "session".into(),
            "turn".into(),
            "ai".into(),
            "decision".into(),
        ];
        tm.metadata.topic = Some("yama".to_string());
        let tr = turn_record_from_memory(&tm).unwrap();
        assert_eq!(tr.role, "ai");
        assert_eq!(tr.session_id, "x");
        assert_eq!(tr.turn_type, "decision");
        assert_eq!(tr.timestamp_ms, 1_700_000_000_000);
        assert_eq!(tr.topic_field.as_deref(), Some("yama"));
        assert!(tr.subject_tags.contains(&"decision".to_string()));
        // Non-turn content parses to None — no fabricated records.
        assert!(turn_record_from_memory(&start).is_none());
    }

    #[test]
    fn index_lists_sessions_and_topics() {
        let files = vec![session(
            "s1",
            "alpha",
            vec![turn("ai", "message", "hi", 1, None)],
        )];
        let idx = index_markdown(&files, &[]);
        assert!(idx.contains("## distill:index"));
        assert!(idx.contains("| s1 |"));
    }
}
