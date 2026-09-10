//! Session transcript miner — deterministic Rust port of the WindsurfRips
//! `PatternMiner` (`archives/og_whitemagic/core/whitemagic/archaeology/session_miner.py`).
//!
//! Mines five insight kinds from raw session transcripts (markdown or JSONL):
//! decisions, breakthroughs, errors, user directives, and topics.
//!
//! Ported semantics (Python → Rust):
//! - `mine_decisions`   → decision markers (`Decision:`, `Ruling:`, "we decided",
//!   "chose X over Y", "going with", "the plan is")
//! - `mine_breakthroughs` → (`breakthrough`, "eureka", "root cause", "the fix
//!   was", "turns out", "discovered", "solved")
//! - `mine_errors`      → strong error indicators (Python's lesson: never bare
//!   "error", which appears in field names — require `error:`, `traceback`,
//!   `panic`, …) plus a resolution-evidence boost when a nearby line says how
//!   it was fixed
//! - `mine_directives`  → imperative-start lines ("never Y", "always Z",
//!   "please", "make sure", "fix …", "run …"), boosted for `role: user`
//! - `mine_topics`      → stopword-filtered bigram frequency + capitalized
//!   multiword noun phrases, top-K
//!
//! Deferred (present in Python, not ported here): `mine_associations`,
//! `mine_recurring_errors`, `mine_topic_cooccurrence`, `mine_session_similarity`,
//! `mine_tech_timeline`, `mine_emotional_arcs`, `mine_decision_outcomes`,
//! `mine_directive_taxonomy`.
//!
//! # Confidence heuristic (documented per port requirements)
//!
//! Base confidence comes from **marker specificity** — an explicit labeled
//! marker (`Decision:`, `breakthrough`, `traceback`) scores higher than a
//! conversational paraphrase ("turns out", "failed"). Boosts: `+0.2` when an
//! error line has resolution evidence within the resolution window; `+0.15`
//! when a directive line came from a `role: user` JSONL entry; whitemagic
//! typed exports (`turn_type: "decision"` etc.) are authoritative and score
//! `0.95`. Topic confidence scales with frequency relative to the corpus
//! maximum. All values are deterministic; no network, no LLM.

use std::borrow::Cow;
use std::collections::HashMap;
use std::collections::hash_map::{DefaultHasher, Entry};
use std::fs::File;
use std::hash::{Hash, Hasher};
use std::io::{BufRead, BufReader};
use std::path::Path;

use regex::{Regex, RegexBuilder};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Kind of mined insight.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InsightKind {
    /// A decision the session settled on.
    Decision,
    /// A discovery / "aha" moment.
    Breakthrough,
    /// An error occurrence (optionally with resolution evidence).
    Error,
    /// An imperative user directive.
    Directive,
    /// A recurring topic (bigram or capitalized phrase).
    Topic,
}

/// One mined insight from a session transcript.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MinedInsight {
    /// What kind of insight this is.
    pub kind: InsightKind,
    /// Trimmed content, truncated to `MinerConfig::max_content_len` chars.
    pub content: String,
    /// Identifier of the transcript this came from (e.g. file stem or UUID).
    pub source_id: String,
    /// Optional timestamp (epoch seconds) from JSONL entries.
    pub at: Option<i64>,
    /// 1-based source line (JSONL line number, or transcript line index).
    pub source_line: usize,
    /// Deterministic confidence in `[0, 1]` (see module docs for heuristic).
    pub confidence: f64,
}

/// Tunables for the [`SessionMiner`].
#[derive(Debug, Clone)]
pub struct MinerConfig {
    /// Max chars kept per insight's content (Python used `[:500]`).
    pub max_content_len: usize,
    /// Cap per [`InsightKind`] (sorted by confidence, best kept).
    pub max_insights_per_kind: usize,
    /// Insights below this confidence are dropped.
    pub confidence_floor: f64,
    /// Cap on topic insights (bigrams + phrases combined).
    pub max_topics: usize,
    /// How many lines after an error to look for resolution evidence.
    pub resolution_window: usize,
}

impl Default for MinerConfig {
    fn default() -> Self {
        Self {
            max_content_len: 500,
            max_insights_per_kind: 64,
            confidence_floor: 0.5,
            max_topics: 16,
            resolution_window: 3,
        }
    }
}

/// Decision markers with explicit labels (highest specificity).
const DECISION_STRONG: &[&str] = &[
    "decision:",
    "ruling:",
    "★ decision",
    "we decided",
    "decided to",
];
/// Decision markers that are conversational paraphrases (lower specificity).
const DECISION_SOFT: &[&str] = &[
    "going with",
    "went with",
    "we will use",
    "the plan is",
    "i'll implement",
    "choosing",
    "we should go with",
];

const BREAKTHROUGH_STRONG: &[&str] = &[
    "breakthrough",
    "eureka",
    "root cause",
    "the key insight",
    "the fix was",
];
const BREAKTHROUGH_SOFT: &[&str] = &[
    "turns out",
    "discovered",
    "solved",
    "figured out",
    "that's it",
    "now it works",
    "the solution is",
];

/// Strong error indicators only — bare "error" is deliberately excluded
/// (it matches field names like `error_message`; the Python port hit this).
const ERROR_STRONG: &[&str] = &[
    "traceback",
    "panic",
    "segfault",
    "exception",
    "error:",
    "error trace",
];
const ERROR_WEAK: &[&str] = &[
    "failed",
    "failure:",
    "timed out",
    "timeout",
    "connection refused",
    "compile error",
    "assertion",
];

/// Resolution evidence searched near error lines (confidence boost).
const RESOLUTION_MARKERS: &[&str] = &[
    "fixed by", "resolved", "fixed:", "the fix", "patched", "hotfix",
];

const STOP_WORDS: &[&str] = &[
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "need",
    "let", "lets", "that", "this", "these", "those", "with", "from", "into", "for", "and", "or",
    "but", "not", "no", "yes", "if", "then", "else", "we", "our", "their", "his", "her", "she",
    "him", "you", "your", "they", "them", "its", "it", "i", "me", "my", "to", "of", "in", "on",
    "at", "by", "as", "so", "up", "out", "about", "what", "how", "why", "when", "where", "who",
    "which", "there", "here", "just", "also", "only", "some", "any", "all", "one", "two", "get",
    "got", "put", "set", "see", "say", "said", "tell", "told", "know", "think", "look", "take",
    "give", "keep", "try", "new", "old", "first", "last", "next", "way", "thing", "things", "make",
    "made", "sure", "thank", "thanks", "please", "okay", "yeah", "yep", "hmm", "oh", "ah",
    "actually", "really", "quite", "pretty", "very", "well", "more", "much", "like", "want",
    "going", "back", "even", "per", "each", "every", "via", "use", "used", "using", "because",
    "than", "too", "both", "either", "neither", "while", "before", "after", "during", "once",
    "twice", "over", "under", "between", "within", "above", "below", "into",
];

/// Patterns compiled once per miner (fast batch parsing: regexes are reused
/// across every line of every transcript fed to this instance).
struct Patterns {
    directive_start: Regex,
    chose_over: Regex,
    capitalized_phrase: Regex,
    word: Regex,
}

impl Patterns {
    /// Compiles the built-in pattern set.
    ///
    /// # Panics
    ///
    /// Panics only if a built-in pattern fails to compile — a programming
    /// error that is unreachable for the shipped constants.
    fn compile() -> Self {
        let ci = |pat: &str| {
            RegexBuilder::new(pat)
                .case_insensitive(true)
                .build()
                .expect("built-in pattern must compile")
        };
        Self {
            directive_start: ci(
                "^(?:[-*>][ .]?|[0-9]+[.)]?[ ]+)*(?:(?:let's|lets|we need|we should|we must|\
                 please|make sure|ensure|verify|confirm|never|always|do not|don't|must)\\b|\
                 (?:fix|update|create|add|remove|delete|implement|build|test|run|check|review|\
                 configure|start|stop|set up)\\b)",
            ),
            chose_over: ci(r"\bchose\b[^.;]{3,120}\bover\b"),
            capitalized_phrase: Regex::new(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+\b")
                .expect("built-in pattern must compile"),
            word: Regex::new(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b")
                .expect("built-in pattern must compile"),
        }
    }
}

/// Accumulated state for one mining run over one transcript (or one JSONL
/// file): marker insights arrive immediately; topics are counted globally and
/// emitted in `finish`.
struct FeedState<'a> {
    miner: &'a SessionMiner,
    insights: Vec<MinedInsight>,
    bigrams: HashMap<(String, String), TopicHit>,
    phrases: HashMap<String, TopicHit>,
}

#[derive(Debug, Clone, Copy)]
struct TopicHit {
    count: u64,
    first_line: usize,
}

/// Mines decisions, breakthroughs, errors, directives and topics from AI
/// session transcripts (markdown or JSONL). Deterministic; no network, no LLM.
pub struct SessionMiner {
    config: MinerConfig,
    patterns: Patterns,
}

impl Default for SessionMiner {
    fn default() -> Self {
        Self::new(MinerConfig::default())
    }
}

impl SessionMiner {
    /// Creates a miner with the given configuration, compiling patterns once.
    ///
    /// # Panics
    ///
    /// Panics if a built-in pattern fails to compile (unreachable).
    #[must_use]
    pub fn new(config: MinerConfig) -> Self {
        Self {
            config,
            patterns: Patterns::compile(),
        }
    }

    /// Mines a raw markdown/plain-text transcript line by line.
    #[must_use]
    pub fn mine_str(&self, transcript: &str, source_id: &str) -> Vec<MinedInsight> {
        let mut state = FeedState::new(self);
        state.feed(transcript, None, 1, false, None);
        self.finalize(state, source_id)
    }

    /// Mines a JSONL transcript, streaming line by line. Tolerates several
    /// export shapes:
    /// - `{"role": "user", "content": "..."}` (plain)
    /// - `{"message": {"role": "assistant", "content": "..."}}` (opencode /
    ///   Anthropic-style nested messages, `content` may be an array of
    ///   `{text}` parts)
    /// - `{"message": "..."}` (bare string)
    /// - `{"turn_type": "decision", "content": "...", "ts": ...}` (whitemagic
    ///   session exports — typed turns are authoritative, confidence 0.95)
    ///
    /// # Errors
    ///
    /// Returns an error if the file cannot be opened or a read fails
    /// mid-stream. Malformed JSON lines are skipped, never fatal.
    pub fn mine_jsonl(&self, path: &Path) -> std::io::Result<Vec<MinedInsight>> {
        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let source_id = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("jsonl")
            .to_owned();
        let mut state = FeedState::new(self);
        for (idx, line) in reader.lines().enumerate() {
            let line = line?;
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let Ok(value) = serde_json::from_str::<Value>(trimmed) else {
                continue;
            };
            let Some((entry, user_role)) = extract_entry(&value) else {
                continue;
            };
            let typed = typed_turn(&value);
            state.feed(&entry.content, entry.at, idx + 1, user_role, typed);
        }
        Ok(self.finalize(state, &source_id))
    }

    /// Dedupes insights on `(kind, normalized content)`, keeping the highest
    /// confidence (ties keep the earliest line). Preserves first-seen order.
    #[must_use]
    pub fn dedupe(&self, insights: Vec<MinedInsight>) -> Vec<MinedInsight> {
        let mut best_index: HashMap<u64, usize> = HashMap::with_capacity(insights.len());
        let mut kept: Vec<MinedInsight> = Vec::with_capacity(insights.len());
        for insight in insights {
            let key = dedupe_key(&insight);
            if let Some(&slot) = best_index.get(&key) {
                let incumbent = &mut kept[slot];
                if insight.confidence > incumbent.confidence {
                    *incumbent = insight;
                }
            } else {
                best_index.insert(key, kept.len());
                kept.push(insight);
            }
        }
        kept
    }

    fn finalize(&self, mut state: FeedState, source_id: &str) -> Vec<MinedInsight> {
        state.emit_topics(&self.config);
        let floor = self.config.confidence_floor;
        let mut out = Vec::new();
        for kind in [
            InsightKind::Decision,
            InsightKind::Breakthrough,
            InsightKind::Error,
            InsightKind::Directive,
            InsightKind::Topic,
        ] {
            let mut group: Vec<MinedInsight> = state
                .insights
                .iter()
                .filter(|i| i.kind == kind && i.confidence >= floor)
                .cloned()
                .collect();
            group.sort_by(|a, b| {
                b.confidence
                    .partial_cmp(&a.confidence)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then(a.source_line.cmp(&b.source_line))
                    .then(a.content.cmp(&b.content))
            });
            let cap = if kind == InsightKind::Topic {
                self.config
                    .max_topics
                    .min(self.config.max_insights_per_kind)
            } else {
                self.config.max_insights_per_kind
            };
            out.extend(group.into_iter().take(cap));
        }
        self.dedupe(out)
            .into_iter()
            .map(|mut insight| {
                insight.content =
                    truncate_chars(&insight.content, self.config.max_content_len).into_owned();
                source_id.clone_into(&mut insight.source_id);
                insight
            })
            .collect()
    }
}

fn dedupe_key(insight: &MinedInsight) -> u64 {
    let mut hasher = DefaultHasher::new();
    insight.kind.hash(&mut hasher);
    normalize(&insight.content).hash(&mut hasher);
    hasher.finish()
}

fn normalize(content: &str) -> String {
    content.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn truncate_chars(s: &str, max: usize) -> Cow<'_, str> {
    if s.chars().count() <= max {
        Cow::Borrowed(s)
    } else {
        Cow::Owned(s.chars().take(max).collect())
    }
}

/// True if `lower` contains any of the lowercase markers.
fn has_marker(lower: &str, markers: &[&str]) -> bool {
    markers.iter().any(|m| lower.contains(m))
}

/// Builds one insight; content is truncated to the config limit in
/// `finalize` (single truncation point keeps call sites cheap).
fn insight(
    kind: InsightKind,
    content: &str,
    at: Option<i64>,
    line: usize,
    confidence: f64,
) -> MinedInsight {
    MinedInsight {
        kind,
        content: content.trim().to_owned(),
        source_id: String::new(),
        at,
        source_line: line,
        confidence,
    }
}

/// whitemagic typed exports: `turn_type` in `decision`/`breakthrough`/`error`
/// is authoritative evidence.
fn typed_turn(value: &Value) -> Option<InsightKind> {
    match value.get("turn_type").and_then(Value::as_str)? {
        "decision" => Some(InsightKind::Decision),
        "breakthrough" => Some(InsightKind::Breakthrough),
        "error" => Some(InsightKind::Error),
        _ => None,
    }
}

struct JsonEntry {
    content: String,
    at: Option<i64>,
}

/// Flattens a JSONL entry into its text content, tolerating the export shapes
/// listed on [`SessionMiner::mine_jsonl`]. Returns the content plus timestamp.
fn extract_entry(value: &Value) -> Option<(JsonEntry, bool)> {
    let message = value.get("message");
    let content = value
        .get("content")
        .and_then(text_from_value)
        .or_else(|| {
            message
                .and_then(Value::as_str)
                .filter(|s| !s.trim().is_empty())
                .map(str::to_owned)
        })
        .or_else(|| message.and_then(text_from_value))
        .or_else(|| {
            message
                .and_then(|m| m.get("content"))
                .and_then(text_from_value)
        })?;
    if content.trim().is_empty() {
        return None;
    }
    let role = value
        .get("role")
        .and_then(Value::as_str)
        .or_else(|| message.and_then(|m| m.get("role")).and_then(Value::as_str));
    let user_role =
        role.is_some_and(|r| r.eq_ignore_ascii_case("user") || r.eq_ignore_ascii_case("human"));
    let at = value
        .get("ts")
        .or_else(|| value.get("timestamp"))
        .or_else(|| value.get("created_at"))
        .or_else(|| value.get("at"))
        .or_else(|| message.and_then(|m| m.get("ts")))
        .and_then(timestamp_from_value);
    Some((JsonEntry { content, at }, user_role))
}

fn text_from_value(value: &Value) -> Option<String> {
    match value {
        Value::String(s) if !s.trim().is_empty() => Some(s.clone()),
        Value::Array(items) => {
            let parts: Vec<String> = items
                .iter()
                .filter_map(|item| {
                    item.as_str().map(str::to_owned).or_else(|| {
                        item.get("text")
                            .or_else(|| item.get("content"))
                            .and_then(text_from_value)
                    })
                })
                .collect();
            (!parts.is_empty()).then_some(parts.join("\n"))
        }
        _ => None,
    }
}

#[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss)]
fn timestamp_from_value(value: &Value) -> Option<i64> {
    if let Some(i) = value.as_i64() {
        return Some(i);
    }
    value
        .as_str()
        .and_then(|s| s.parse::<i64>().ok().or_else(|| parse_rfc3339(s)))
}

fn parse_rfc3339(s: &str) -> Option<i64> {
    chrono::DateTime::parse_from_rfc3339(s)
        .ok()
        .map(|dt| dt.timestamp())
}

impl<'a> FeedState<'a> {
    fn new(miner: &'a SessionMiner) -> Self {
        Self {
            miner,
            insights: Vec::new(),
            bigrams: HashMap::new(),
            phrases: HashMap::new(),
        }
    }

    /// Feeds one text block (a transcript, or one JSONL entry's content) into
    /// the mining state. `base_line` is the 1-based line number the block
    /// starts at; insights produced here keep `at` from the entry.
    fn feed(
        &mut self,
        text: &str,
        at: Option<i64>,
        base_line: usize,
        user_role: bool,
        typed: Option<InsightKind>,
    ) {
        let lines: Vec<&str> = text.lines().collect();
        let lowered: Vec<String> = lines.iter().map(|l| l.to_lowercase()).collect();
        let window = self.miner.config.resolution_window;

        if let Some(kind) = typed {
            if let Some(first) = lines.iter().find(|l| !l.trim().is_empty()) {
                self.insights
                    .push(insight(kind, first.trim(), at, base_line, 0.95));
            }
        }

        for (offset, line) in lines.iter().enumerate() {
            let line_num = base_line + offset;
            let lower = lowered[offset].as_str();
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            // Errors first: strongest claim on an error-indicating line.
            if let Some(conf) = error_confidence(lower) {
                let boost = resolution_evidence(&lowered, offset, window);
                self.insights.push(insight(
                    InsightKind::Error,
                    trimmed,
                    at,
                    line_num,
                    (conf + boost).clamp(0.0, 1.0),
                ));
            }

            // Decisions: labeled markers > "chose X over Y" > paraphrase.
            if let Some(conf) = decision_confidence(lower, &self.miner.patterns) {
                self.insights
                    .push(insight(InsightKind::Decision, trimmed, at, line_num, conf));
            }

            if let Some(conf) = breakthrough_confidence(lower) {
                self.insights.push(insight(
                    InsightKind::Breakthrough,
                    trimmed,
                    at,
                    line_num,
                    conf,
                ));
            }

            if let Some(conf) = directive_confidence(
                &self.miner.patterns,
                trimmed,
                user_role,
                self.miner.config.max_content_len,
            ) {
                self.insights
                    .push(insight(InsightKind::Directive, trimmed, at, line_num, conf));
            }

            self.collect_topics(line, line_num);
        }
    }

    fn collect_topics(&mut self, line: &str, line_num: usize) {
        for m in self.miner.patterns.capitalized_phrase.find_iter(line) {
            let phrase = m.as_str().to_owned();
            Self::bump(&mut self.phrases, phrase, line_num);
        }
        let tokens: Vec<String> = self
            .miner
            .patterns
            .word
            .find_iter(line)
            .filter_map(|m| {
                let w = m.as_str().to_lowercase();
                (!STOP_WORDS.contains(&w.as_str())).then_some(w)
            })
            .collect();
        for pair in tokens.windows(2) {
            Self::bump(
                &mut self.bigrams,
                (pair[0].clone(), pair[1].clone()),
                line_num,
            );
        }
    }

    fn bump<K: Eq + Hash>(map: &mut HashMap<K, TopicHit>, key: K, line_num: usize) {
        match map.entry(key) {
            Entry::Vacant(v) => {
                v.insert(TopicHit {
                    count: 1,
                    first_line: line_num,
                });
            }
            Entry::Occupied(mut o) => {
                let hit = o.get_mut();
                hit.count += 1;
                hit.first_line = hit.first_line.min(line_num);
            }
        }
    }

    /// Emits topic insights: stopword-filtered bigrams and capitalized
    /// multiword phrases, ranked by frequency relative to the corpus maximum.
    fn emit_topics(&mut self, config: &MinerConfig) {
        let mut candidates: Vec<(f64, MinedInsight)> = Vec::new();
        if let Some(max) = self.bigrams.values().map(|h| h.count).max() {
            let bigrams: Vec<((String, String), TopicHit)> = self.bigrams.drain().collect();
            for ((a, b), hit) in bigrams {
                let conf = topic_conf(hit.count, max, 0.45, 0.45);
                let content = format!("{a} {b}");
                let candidate = insight(InsightKind::Topic, &content, None, hit.first_line, conf);
                candidates.push((conf, candidate));
            }
        }
        if let Some(max) = self.phrases.values().map(|h| h.count).max() {
            let phrases: Vec<(String, TopicHit)> = self.phrases.drain().collect();
            for (phrase, hit) in phrases {
                let conf = topic_conf(hit.count, max, 0.55, 0.35);
                let candidate = insight(InsightKind::Topic, &phrase, None, hit.first_line, conf);
                candidates.push((conf, candidate));
            }
        }
        candidates.sort_by(|a, b| {
            b.0.partial_cmp(&a.0)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.1.source_line.cmp(&b.1.source_line))
                .then(a.1.content.cmp(&b.1.content))
        });
        self.insights.extend(
            candidates
                .into_iter()
                .map(|(_, i)| i)
                .take(config.max_topics.max(1)),
        );
    }
}

#[allow(clippy::cast_precision_loss)]
fn ratio(count: u64, max: u64) -> f64 {
    if max == 0 {
        0.0
    } else {
        count as f64 / max as f64
    }
}

// mul_add changes float rounding (documented crate allow, as elsewhere).
#[allow(clippy::suboptimal_flops)]
fn topic_conf(count: u64, max: u64, base: f64, spread: f64) -> f64 {
    base + spread * ratio(count, max)
}

/// Error confidence from marker specificity: strong indicators (`traceback`,
/// `panic`, `exception`, `error:`) 0.7, weaker evidence (`failed`, `timeout`)
/// 0.6. Bare "error" is deliberately not a marker (field-name false positives).
fn error_confidence(lower: &str) -> Option<f64> {
    if has_marker(lower, ERROR_STRONG) {
        Some(0.7)
    } else if has_marker(lower, ERROR_WEAK) {
        Some(0.6)
    } else {
        None
    }
}

/// `+0.2` when resolution evidence ("fixed by", "resolved", …) appears within
/// `window` lines after (or on the line immediately before) an error.
fn resolution_evidence(lowered: &[String], offset: usize, window: usize) -> f64 {
    let after = lowered[offset + 1..(offset + 1 + window).min(lowered.len())]
        .iter()
        .any(|l| has_marker(l, RESOLUTION_MARKERS));
    let before = offset > 0 && has_marker(&lowered[offset - 1], RESOLUTION_MARKERS);
    if after || before { 0.2 } else { 0.0 }
}

/// Decision confidence: labeled markers 0.9, explicit "chose X over Y" 0.85,
/// conversational paraphrase 0.7.
fn decision_confidence(lower: &str, patterns: &Patterns) -> Option<f64> {
    if has_marker(lower, DECISION_STRONG) {
        Some(0.9)
    } else if patterns.chose_over.is_match(lower) {
        Some(0.85)
    } else if has_marker(lower, DECISION_SOFT) {
        Some(0.7)
    } else {
        None
    }
}

/// Breakthrough confidence: explicit markers 0.9, conversational 0.7.
fn breakthrough_confidence(lower: &str) -> Option<f64> {
    if has_marker(lower, BREAKTHROUGH_STRONG) {
        Some(0.9)
    } else if has_marker(lower, BREAKTHROUGH_SOFT) {
        Some(0.7)
    } else {
        None
    }
}

/// Directive confidence: imperative-start line (Python's mine_directives
/// pattern list) 0.7, `+0.15` when the entry came from a user role.
fn directive_confidence(
    patterns: &Patterns,
    trimmed: &str,
    user_role: bool,
    max_len: usize,
) -> Option<f64> {
    if trimmed.chars().count() > max_len {
        return None;
    }
    if patterns.directive_start.is_match(trimmed) {
        Some(if user_role { 0.85 } else { 0.7 })
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn kinds(insights: &[MinedInsight], kind: InsightKind) -> Vec<&MinedInsight> {
        insights.iter().filter(|i| i.kind == kind).collect()
    }

    #[test]
    fn decisions_detected_with_tiers() {
        let t = "\
Decision: we use LMDB for durable storage.
We discussed options at length.
Chose Tantivy over Lucene because BM25 was faster.
we decided to drop the in-process cache.
";
        let insights = SessionMiner::default().mine_str(t, "s1");
        let decisions = kinds(&insights, InsightKind::Decision);
        assert_eq!(decisions.len(), 3, "{decisions:?}");
        assert!(decisions[0].confidence > decisions[2].confidence);
        assert!(decisions.iter().all(|d| d.content.ends_with('.')));
    }

    #[test]
    fn breakthroughs_detected() {
        let t = "\
Breakthrough: the segfault came from a stale LMDB handle.
turns out the cache was already warm.
nothing interesting on this line at all.
";
        let insights = SessionMiner::default().mine_str(t, "s2");
        let bts = kinds(&insights, InsightKind::Breakthrough);
        assert_eq!(bts.len(), 2, "{bts:?}");
        assert!(bts[0].confidence > bts[1].confidence);
    }

    #[test]
    fn errors_with_resolution_boost() {
        let t = "\
Build failed: E0432 unresolved import somewhere else entirely.
Reviewed the module graph for a while.
No resolution evidence on these filler lines.
thread 'main' panicked at crates/x/src/lib.rs:12:3:
Fixed by re-initializing the LMDB handle after compaction.
";
        let miner = SessionMiner::default();
        let insights = miner.mine_str(t, "s3");
        let errors = kinds(&insights, InsightKind::Error);
        assert_eq!(errors.len(), 2, "{errors:?}");
        let boosted = errors
            .iter()
            .find(|e| e.content.contains("panicked"))
            .unwrap();
        let plain = errors.iter().find(|e| e.content.contains("E0432")).unwrap();
        assert!(
            (boosted.confidence - 0.9).abs() < f64::EPSILON,
            "{boosted:?}"
        );
        assert!((plain.confidence - 0.6).abs() < f64::EPSILON, "{plain:?}");
    }

    #[test]
    fn bare_error_word_is_not_an_error_marker() {
        let t = "read the error_message field carefully before dispatching.";
        let insights = SessionMiner::default().mine_str(t, "s3b");
        assert!(
            kinds(&insights, InsightKind::Error).is_empty(),
            "{insights:?}"
        );
    }

    #[test]
    fn directives_detected() {
        let t = "\
Never store plaintext tokens in the repo.
Always run cargo fmt before committing.
- fix the parser first
Please update the documentation.
We chatted about the weather for a while.
";
        let insights = SessionMiner::default().mine_str(t, "s4");
        let dirs = kinds(&insights, InsightKind::Directive);
        assert_eq!(dirs.len(), 4, "{dirs:?}");
        assert!(dirs.iter().all(|d| d.confidence >= 0.7));
    }

    #[test]
    fn bigram_topics_ranked_by_frequency() {
        let t = "\
memory store memory store memory store
topic rank topic rank
the compiler accepted the patch today
";
        let insights = SessionMiner::default().mine_str(t, "s5");
        let topics = kinds(&insights, InsightKind::Topic);
        assert!(!topics.is_empty(), "{insights:?}");
        assert_eq!(topics[0].content, "memory store");
        assert!(topics[0].confidence > topics.last().unwrap().confidence);
        // Single-occurrence bigrams fall below the default floor.
        assert!(topics.iter().all(|t| t.confidence >= 0.5));
    }

    #[test]
    fn jsonl_multi_shape_parsing() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("transcript.jsonl");
        std::fs::write(
            &path,
            concat!(
                "{\"role\":\"user\",\"content\":\"Never store plaintext tokens\"}\n",
                "{\"message\":{\"role\":\"assistant\",\"content\":\"Breakthrough: found the race condition\"}}\n",
                "{\"turn_type\":\"decision\",\"content\":\"Decision: adopt LMDB\",\"ts\":1700000000}\n",
                "not json at all\n",
                "{\"message\":[{\"type\":\"text\",\"text\":\"Error: trace shows the race\"}]}\n"
            ),
        )
        .unwrap();
        let insights = SessionMiner::default().mine_jsonl(&path).unwrap();
        assert!(!kinds(&insights, InsightKind::Directive).is_empty());
        assert!(!kinds(&insights, InsightKind::Breakthrough).is_empty());
        assert!(!kinds(&insights, InsightKind::Decision).is_empty());
        assert!(!kinds(&insights, InsightKind::Error).is_empty());
        let decision = kinds(&insights, InsightKind::Decision)[0];
        assert_eq!(decision.at, Some(1_700_000_000));
        assert_eq!(decision.source_id, "transcript");
        assert_eq!(decision.confidence, 0.95);
        // user-role directive got the role boost
        let directive = kinds(&insights, InsightKind::Directive)[0];
        assert!(
            (directive.confidence - 0.85).abs() < f64::EPSILON,
            "{directive:?}"
        );
    }

    #[test]
    fn dedupe_keeps_highest_confidence() {
        let miner = SessionMiner::default();
        let low = insight(InsightKind::Decision, "Decision: use LMDB.", None, 2, 0.7);
        let high = insight(InsightKind::Decision, "Decision:  use  LMDB.", None, 9, 0.9);
        let other = insight(InsightKind::Error, "panic: bad thing", None, 3, 0.7);
        let deduped = miner.dedupe(vec![low, high, other]);
        assert_eq!(deduped.len(), 2);
        let decision = deduped
            .iter()
            .find(|i| i.kind == InsightKind::Decision)
            .unwrap();
        assert!((decision.confidence - 0.9).abs() < f64::EPSILON);
        assert_eq!(decision.source_line, 9);
    }

    #[test]
    fn confidence_floor_filters_everything() {
        let config = MinerConfig {
            confidence_floor: 0.99,
            ..MinerConfig::default()
        };
        let miner = SessionMiner::new(config);
        let insights = miner.mine_str(
            "Decision: use LMDB for storage.\nwe failed to parse the file.",
            "s6",
        );
        assert!(insights.is_empty(), "{insights:?}");
    }

    #[test]
    fn max_per_kind_cap() {
        let config = MinerConfig {
            max_insights_per_kind: 1,
            ..MinerConfig::default()
        };
        let miner = SessionMiner::new(config);
        let t =
            "Decision: use LMDB.\nDecision: drop the cache.\nwe decided to rewrite the parser.\n";
        let insights = miner.mine_str(t, "s7");
        assert_eq!(
            kinds(&insights, InsightKind::Decision).len(),
            1,
            "{insights:?}"
        );
    }

    #[test]
    fn empty_and_garbage_input_never_panic() {
        let miner = SessionMiner::default();
        assert!(miner.mine_str("", "empty").is_empty());
        assert!(miner.mine_str("!!! &&& ??? 123  \n", "garbage").is_empty());
        assert!(
            miner
                .mine_str("a b a b a b\n\t\n", "short-tokens")
                .is_empty()
        );
        let insights = miner.mine_str("this is a plain sentence about weather", "plain");
        assert!(insights.iter().all(|i| i.kind == InsightKind::Topic));
    }

    #[test]
    fn insight_content_truncated_to_config() {
        let config = MinerConfig {
            max_content_len: 10,
            ..MinerConfig::default()
        };
        let miner = SessionMiner::new(config);
        let long = format!("Decision: {}", "x".repeat(200));
        let insights = miner.mine_str(&long, "s8");
        assert_eq!(insights[0].content.chars().count(), 10);
    }

    #[test]
    fn serde_roundtrip() {
        let i = insight(
            InsightKind::Breakthrough,
            "root cause found",
            Some(42),
            7,
            0.9,
        );
        let json = serde_json::to_string(&i).unwrap();
        let back: MinedInsight = serde_json::from_str(&json).unwrap();
        assert_eq!(back, i);
    }
}
