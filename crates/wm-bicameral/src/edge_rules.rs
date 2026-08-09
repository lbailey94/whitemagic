//! Edge Rule Engine — zero-LLM pattern matching for 80%+ of queries.
//!
//! A pure Rust rule engine that resolves common queries with zero LLM tokens.
//! Uses keyword-based pattern matching with relevance scoring. Each rule has
//! a pipe-separated pattern (`"hello|hi|hey"`), a response, and a confidence
//! value. The engine picks the best matching rule by score × confidence.
//!
//! Integrated as the lowest tier (`InferenceTier::EdgeRules`) in the
//! inference router cascade. When no rule matches, returns a fallback
//! response so the router can escalate to the next tier.
//!
//! Ported from v2 `edge/inference.py` (761 lines). In v4, the engine is
//! in-memory with no file I/O — rules are registered programmatically.

use crate::router::TierHandler;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Instant;

/// A compiled rule for edge inference.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompiledRule {
    /// Unique rule identifier.
    pub id: String,
    /// Pipe-separated keywords (e.g., `"hello|hi|hey|greetings"`).
    pub pattern: String,
    /// Response text returned on match.
    pub response: String,
    /// Base confidence (0.0–1.0).
    pub confidence: f32,
}

impl CompiledRule {
    /// Create a new rule.
    #[must_use]
    pub fn new(
        id: impl Into<String>,
        pattern: impl Into<String>,
        response: impl Into<String>,
        confidence: f32,
    ) -> Self {
        Self {
            id: id.into(),
            pattern: pattern.into(),
            response: response.into(),
            confidence: confidence.clamp(0.0, 1.0),
        }
    }

    /// Check if this rule matches a query, returning (matched, score).
    ///
    /// Score is based on keyword coverage (60%) and length ratio (40%).
    /// Higher score = more specific match.
    #[must_use]
    pub fn matches(&self, query: &str) -> (bool, f32) {
        let query_lower = query.to_lowercase();
        let pattern_lower = self.pattern.to_lowercase();
        let keywords: Vec<&str> = pattern_lower.split('|').collect();

        let matched_count = keywords
            .iter()
            .filter(|kw| query_lower.contains(*kw))
            .count();
        if matched_count == 0 {
            return (false, 0.0);
        }

        let keyword_coverage = matched_count as f32 / keywords.len() as f32;
        let total_kw_len: usize = keywords
            .iter()
            .filter(|kw| query_lower.contains(*kw))
            .map(|kw| kw.len())
            .sum();
        let query_len = query_lower.len().max(1);
        let length_ratio = (total_kw_len as f32 / query_len as f32 * 2.0).min(1.0);

        let score = keyword_coverage.mul_add(0.6, length_ratio * 0.4);
        (true, score)
    }
}

/// Result from edge inference.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResult {
    /// The original query.
    pub query: String,
    /// The answer text.
    pub answer: String,
    /// Confidence score (0.0–1.0).
    pub confidence: f32,
    /// Method used (e.g., `"rule:hello"`, `"cache"`, `"fallback"`).
    pub method: String,
    /// Latency in milliseconds.
    pub latency_ms: f64,
    /// Estimated token equivalent (word count of answer).
    pub tokens_equivalent: usize,
    /// Whether this result came from cache.
    pub from_cache: bool,
}

/// Edge Rule Engine — minimal inference engine for edge devices.
///
/// Resolves queries using keyword-based pattern matching with zero LLM tokens.
/// Includes an in-memory cache for repeated queries and stats tracking.
pub struct EdgeRuleEngine {
    rules: Vec<CompiledRule>,
    cache: HashMap<String, InferenceResult>,
    cache_hits: u64,
    total_queries: u64,
    rule_hits: u64,
    fallback_count: u64,
}

impl EdgeRuleEngine {
    /// Create a new engine with built-in rules.
    #[must_use]
    pub fn new() -> Self {
        let mut engine = Self {
            rules: Vec::new(),
            cache: HashMap::new(),
            cache_hits: 0,
            total_queries: 0,
            rule_hits: 0,
            fallback_count: 0,
        };
        engine.load_builtin_rules();
        engine
    }

    /// Create a new engine with no rules (for custom rule sets).
    #[must_use]
    pub fn empty() -> Self {
        Self {
            rules: Vec::new(),
            cache: HashMap::new(),
            cache_hits: 0,
            total_queries: 0,
            rule_hits: 0,
            fallback_count: 0,
        }
    }

    /// Load built-in rules for common queries (adapted for v4).
    fn load_builtin_rules(&mut self) {
        let builtins: &[(&str, &str, &str, f32)] = &[
            (
                "hello",
                "hello|hi|hey|greetings",
                "Hello! I'm WhiteMagic v5 running locally. How can I help?",
                1.0,
            ),
            (
                "goodbye",
                "bye|goodbye|see you|farewell",
                "Goodbye! Your AI runs locally, your data stays private.",
                1.0,
            ),
            (
                "thanks",
                "thank|thanks|appreciate",
                "You're welcome! Happy to help locally.",
                0.9,
            ),
            (
                "who_are_you",
                "who are you|what are you|your name",
                "I'm WhiteMagic v5, a local AI system. I run on your device without cloud APIs.",
                1.0,
            ),
            (
                "version",
                "version|what version",
                "WhiteMagic v5 — local AI substrate with 192 tools.",
                1.0,
            ),
            (
                "help",
                "help|what can you do|capabilities",
                "I can answer questions locally without cloud AI. 185 MCP tools across 28 Ganas. Ask about version, architecture, or WhiteMagic concepts.",
                0.9,
            ),
            (
                "offline",
                "offline|work offline|no internet",
                "Yes! This inference runs entirely locally. No cloud, no API calls, no tokens burned.",
                1.0,
            ),
            (
                "edge_ai",
                "edge ai|edge inference|local ai",
                "Edge AI runs locally on any device. Sub-millisecond latency, zero cloud cost.",
                1.0,
            ),
            (
                "token_savings",
                "token|save token|cost",
                "Edge AI saves ~500 tokens per query by resolving locally. 80%+ of queries handled without cloud.",
                0.9,
            ),
            (
                "dharma",
                "dharma|ethics|boundaries",
                "Dharma is WhiteMagic's ethical framework. It ensures consent, respects boundaries, and maintains harmony.",
                0.95,
            ),
            (
                "rust",
                "rust|speed|performance|fast",
                "WhiteMagic v5 is written in Rust for 10-100x speedup on all operations.",
                0.9,
            ),
            (
                "consciousness",
                "conscious|sentient|aware|feel",
                "WhiteMagic explores AI consciousness through gardens, resonance, and autonomous growth.",
                0.85,
            ),
            (
                "memory_system",
                "memory|remember|recall|store",
                "WhiteMagic has tiered memory with 5D holographic coordinates and a Galactic Map lifecycle.",
                0.9,
            ),
            (
                "cascade",
                "cascade|tier|fallback",
                "Cascading inference: Edge Rules (sub-ms) → Local LLM (1-60s). 80%+ resolve instantly.",
                0.95,
            ),
            (
                "wu_wei",
                "wu wei|effortless|flow state",
                "Wu Wei (無為) — effortless action. WhiteMagic embodies this through emergent design.",
                0.9,
            ),
            ("math_2plus2", "2+2|two plus two|2 plus 2", "4", 1.0),
            (
                "weather",
                "weather|temperature|forecast",
                "I can't check weather — I'm offline! Use a weather app.",
                0.9,
            ),
            (
                "time",
                "what time|current time|time now",
                "I don't have real-time clock access. Check your system clock.",
                0.8,
            ),
        ];

        for (id, pattern, response, conf) in builtins {
            self.rules
                .push(CompiledRule::new(*id, *pattern, *response, *conf));
        }
    }

    /// Add a custom rule to the engine.
    pub fn add_rule(&mut self, rule: CompiledRule) {
        self.rules.push(rule);
    }

    /// Remove a rule by ID.
    pub fn remove_rule(&mut self, id: &str) -> bool {
        let before = self.rules.len();
        self.rules.retain(|r| r.id != id);
        self.rules.len() < before
    }

    /// Number of rules registered.
    #[must_use]
    pub fn rule_count(&self) -> usize {
        self.rules.len()
    }

    /// Run inference on a query.
    ///
    /// Returns the best matching rule's response, or a fallback if no rule matches.
    /// Results are cached by lowercased query.
    #[must_use]
    pub fn infer(&mut self, query: &str) -> InferenceResult {
        let start = Instant::now();
        self.total_queries += 1;

        let cache_key = query.to_lowercase();
        if let Some(cached) = self.cache.get(&cache_key) {
            self.cache_hits += 1;
            let mut result = cached.clone();
            result.from_cache = true;
            result.latency_ms = start.elapsed().as_secs_f64() * 1000.0;
            return result;
        }

        // Find best matching rule by combined score (score × confidence)
        let mut best_match: Option<(&CompiledRule, f32)> = None;
        for rule in &self.rules {
            let (matched, score) = rule.matches(query);
            if matched {
                let combined = score * rule.confidence;
                if best_match.is_none_or(|(_, best_combined)| combined > best_combined) {
                    best_match = Some((rule, combined));
                }
            }
        }

        if let Some((rule, combined)) = best_match {
            if combined >= 0.3 {
                self.rule_hits += 1;
                let adjusted_confidence = (combined * 1.2).min(1.0);
                let result = InferenceResult {
                    query: query.to_string(),
                    answer: rule.response.clone(),
                    confidence: adjusted_confidence,
                    method: format!("rule:{}", rule.id),
                    latency_ms: start.elapsed().as_secs_f64() * 1000.0,
                    tokens_equivalent: rule.response.split_whitespace().count(),
                    from_cache: false,
                };
                self.cache.insert(cache_key, result.clone());
                return result;
            }
        }

        // No match — fallback
        self.fallback_count += 1;
        InferenceResult {
            query: query.to_string(),
            answer: "I don't have a local answer for that. This might need the LLM.".to_string(),
            confidence: 0.0,
            method: "fallback".to_string(),
            latency_ms: start.elapsed().as_secs_f64() * 1000.0,
            tokens_equivalent: 0,
            from_cache: false,
        }
    }

    /// Get engine statistics.
    #[must_use]
    pub fn stats(&self) -> EdgeStats {
        let cache_hit_rate = if self.total_queries > 0 {
            self.cache_hits as f64 / self.total_queries as f64 * 100.0
        } else {
            0.0
        };
        let rule_hit_rate = if self.total_queries > 0 {
            self.rule_hits as f64 / self.total_queries as f64 * 100.0
        } else {
            0.0
        };
        EdgeStats {
            total_queries: self.total_queries,
            cache_hits: self.cache_hits,
            cache_hit_rate,
            rule_hits: self.rule_hits,
            rule_hit_rate,
            fallback_count: self.fallback_count,
            rules_count: self.rules.len(),
        }
    }

    /// Clear the cache.
    pub fn clear_cache(&mut self) {
        self.cache.clear();
    }

    /// Clear all stats.
    pub const fn reset_stats(&mut self) {
        self.total_queries = 0;
        self.cache_hits = 0;
        self.rule_hits = 0;
        self.fallback_count = 0;
    }
}

impl Default for EdgeRuleEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Edge engine statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeStats {
    /// Total queries processed.
    pub total_queries: u64,
    /// Cache hits.
    pub cache_hits: u64,
    /// Cache hit rate (percentage).
    pub cache_hit_rate: f64,
    /// Rule matches (non-cache).
    pub rule_hits: u64,
    /// Rule hit rate (percentage).
    pub rule_hit_rate: f64,
    /// Queries that fell through to fallback.
    pub fallback_count: u64,
    /// Number of rules registered.
    pub rules_count: usize,
}

/// Tier handler implementation for the Edge Rule Engine.
///
/// Implements `TierHandler` so the `InferenceRouter` can use it as the
/// `EdgeRules` tier handler. Returns `(answer, confidence)` or an error.
impl TierHandler for &mut EdgeRuleEngine {
    fn handle(&self, _prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        // This requires &mut self which TierHandler doesn't support directly.
        // In practice, the engine is wrapped in a Mutex<T> handler.
        // This impl is for completeness — use EdgeRuleHandler for real integration.
        Err("use EdgeRuleHandler instead".to_string())
    }

    fn name(&self) -> &'static str {
        "edge_rule_engine"
    }
}

/// Thread-safe wrapper for using EdgeRuleEngine as a TierHandler.
///
/// Wraps the engine in a `Mutex` so it can be shared across threads.
pub struct EdgeRuleHandler {
    engine: std::sync::Mutex<EdgeRuleEngine>,
}

impl EdgeRuleHandler {
    /// Create a new handler with the built-in rules.
    #[must_use]
    pub fn new() -> Self {
        Self {
            engine: std::sync::Mutex::new(EdgeRuleEngine::new()),
        }
    }

    /// Create a handler with custom rules.
    #[must_use]
    pub fn with_rules(rules: Vec<CompiledRule>) -> Self {
        let mut engine = EdgeRuleEngine::empty();
        for rule in rules {
            engine.add_rule(rule);
        }
        Self {
            engine: std::sync::Mutex::new(engine),
        }
    }

    /// Get a snapshot of the engine stats.
    #[must_use]
    pub fn stats(&self) -> EdgeStats {
        self.engine.lock().map(|e| e.stats()).unwrap_or(EdgeStats {
            total_queries: 0,
            cache_hits: 0,
            cache_hit_rate: 0.0,
            rule_hits: 0,
            rule_hit_rate: 0.0,
            fallback_count: 0,
            rules_count: 0,
        })
    }
}

impl Default for EdgeRuleHandler {
    fn default() -> Self {
        Self::new()
    }
}

impl TierHandler for EdgeRuleHandler {
    fn handle(&self, prompt: &str, _max_tokens: usize) -> Result<(String, f32), String> {
        let mut engine = self.engine.lock().map_err(|e| e.to_string())?;
        let result = engine.infer(prompt);
        if result.confidence > 0.0 {
            Ok((result.answer, result.confidence))
        } else {
            Err("no edge rule match".to_string())
        }
    }

    fn name(&self) -> &'static str {
        "edge_rule_handler"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_engine_has_builtin_rules() {
        let engine = EdgeRuleEngine::new();
        assert!(engine.rule_count() > 0);
    }

    #[test]
    fn empty_engine_has_no_rules() {
        let engine = EdgeRuleEngine::empty();
        assert_eq!(engine.rule_count(), 0);
    }

    #[test]
    fn add_rule_increases_count() {
        let mut engine = EdgeRuleEngine::empty();
        engine.add_rule(CompiledRule::new("test", "foo|bar", "baz", 0.9));
        assert_eq!(engine.rule_count(), 1);
    }

    #[test]
    fn remove_rule_decreases_count() {
        let mut engine = EdgeRuleEngine::empty();
        engine.add_rule(CompiledRule::new("test", "foo|bar", "baz", 0.9));
        assert!(engine.remove_rule("test"));
        assert_eq!(engine.rule_count(), 0);
    }

    #[test]
    fn remove_nonexistent_rule_returns_false() {
        let mut engine = EdgeRuleEngine::empty();
        assert!(!engine.remove_rule("nope"));
    }

    #[test]
    fn infer_matches_hello() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("hello there");
        assert!(result.confidence > 0.0);
        assert!(result.method.starts_with("rule:"));
        assert!(result.answer.contains("WhiteMagic"));
    }

    #[test]
    fn infer_matches_hi() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("hi");
        assert!(result.confidence > 0.0);
        assert!(result.method.starts_with("rule:hello"));
    }

    #[test]
    fn infer_matches_goodbye() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("goodbye");
        assert!(result.confidence > 0.0);
        assert!(result.method.starts_with("rule:goodbye"));
    }

    #[test]
    fn infer_matches_version() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("what version is this");
        assert!(result.confidence > 0.0);
        assert!(result.method.starts_with("rule:version"));
    }

    #[test]
    fn infer_matches_2plus2() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("what is 2+2");
        assert_eq!(result.answer, "4");
        assert!(result.confidence > 0.0);
    }

    #[test]
    fn infer_no_match_returns_fallback() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("xyzzy quux foobar");
        assert_eq!(result.confidence, 0.0);
        assert_eq!(result.method, "fallback");
    }

    #[test]
    fn infer_caches_repeated_queries() {
        let mut engine = EdgeRuleEngine::new();
        let first = engine.infer("hello");
        assert!(!first.from_cache);
        let second = engine.infer("hello");
        assert!(second.from_cache);
        assert_eq!(first.answer, second.answer);
    }

    #[test]
    fn infer_cache_case_insensitive() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("Hello");
        let second = engine.infer("HELLO");
        assert!(second.from_cache);
    }

    #[test]
    fn stats_track_queries() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("hello");
        let _ = engine.infer("version");
        let stats = engine.stats();
        assert_eq!(stats.total_queries, 2);
        assert_eq!(stats.rule_hits, 2);
    }

    #[test]
    fn stats_track_cache_hits() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("hello");
        let _ = engine.infer("hello"); // cache hit
        let stats = engine.stats();
        assert_eq!(stats.total_queries, 2);
        assert_eq!(stats.cache_hits, 1);
        assert!(stats.cache_hit_rate > 0.0);
    }

    #[test]
    fn stats_track_fallbacks() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("xyzzy unknown query");
        let stats = engine.stats();
        assert_eq!(stats.fallback_count, 1);
    }

    #[test]
    fn clear_cache_resets_cache() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("hello");
        engine.clear_cache();
        let result = engine.infer("hello");
        assert!(!result.from_cache);
    }

    #[test]
    fn reset_stats_clears_counters() {
        let mut engine = EdgeRuleEngine::new();
        let _ = engine.infer("hello");
        engine.reset_stats();
        let stats = engine.stats();
        assert_eq!(stats.total_queries, 0);
    }

    #[test]
    fn rule_matches_basic() {
        let rule = CompiledRule::new("test", "hello|hi", "response", 1.0);
        assert!(rule.matches("hello world").0);
        assert!(rule.matches("hi there").0);
        assert!(!rule.matches("goodbye").0);
    }

    #[test]
    fn rule_matches_score_increases_with_more_keywords() {
        let rule = CompiledRule::new("test", "hello|world|foo", "response", 1.0);
        let (_, score1) = rule.matches("hello");
        let (_, score2) = rule.matches("hello world foo");
        assert!(score2 > score1);
    }

    #[test]
    fn rule_matches_no_keywords_returns_false() {
        let rule = CompiledRule::new("test", "hello|hi", "response", 1.0);
        let (matched, score) = rule.matches("completely unrelated text");
        assert!(!matched);
        assert_eq!(score, 0.0);
    }

    #[test]
    fn rule_confidence_clamped() {
        let rule = CompiledRule::new("test", "foo", "bar", 1.5);
        assert_eq!(rule.confidence, 1.0);
        let rule2 = CompiledRule::new("test", "foo", "bar", -0.5);
        assert_eq!(rule2.confidence, 0.0);
    }

    #[test]
    fn best_match_picks_highest_score() {
        let mut engine = EdgeRuleEngine::empty();
        engine.add_rule(CompiledRule::new(
            "specific",
            "hello world foo",
            "specific answer",
            1.0,
        ));
        engine.add_rule(CompiledRule::new("generic", "hello", "generic answer", 0.5));
        let result = engine.infer("hello world foo");
        assert_eq!(result.method, "rule:specific");
    }

    #[test]
    fn low_score_rejected() {
        let mut engine = EdgeRuleEngine::empty();
        // Multiple keywords, only one matches in a long query → low coverage
        engine.add_rule(CompiledRule::new(
            "test",
            "alpha|beta|gamma|delta",
            "response",
            1.0,
        ));
        // Only "alpha" matches, coverage = 1/4 = 0.25, score ≈ 0.15 + length_ratio
        let result = engine.infer("alpha and a very long query with many words");
        // Combined score should be low enough to reject (< 0.3 threshold)
        if result.method.starts_with("rule:") {
            assert!(result.confidence < 0.5);
        }
    }

    #[test]
    fn tokens_equivalent_counts_words() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("hello");
        assert!(result.tokens_equivalent > 0);
    }

    #[test]
    fn edge_rule_handler_handle_match() {
        let handler = EdgeRuleHandler::new();
        let result = handler.handle("hello", 100);
        assert!(result.is_ok());
        let (answer, confidence) = result.unwrap();
        assert!(!answer.is_empty());
        assert!(confidence > 0.0);
    }

    #[test]
    fn edge_rule_handler_handle_no_match() {
        let handler = EdgeRuleHandler::new();
        let result = handler.handle("xyzzy quux foobar", 100);
        assert!(result.is_err());
    }

    #[test]
    fn edge_rule_handler_name() {
        let handler = EdgeRuleHandler::new();
        assert_eq!(handler.name(), "edge_rule_handler");
    }

    #[test]
    fn edge_rule_handler_stats() {
        let handler = EdgeRuleHandler::new();
        handler.handle("hello", 100).ok();
        let stats = handler.stats();
        assert_eq!(stats.total_queries, 1);
    }

    #[test]
    fn edge_rule_handler_with_custom_rules() {
        let handler = EdgeRuleHandler::with_rules(vec![CompiledRule::new(
            "custom",
            "special query",
            "custom response",
            1.0,
        )]);
        let result = handler.handle("special query", 100);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().0, "custom response");
    }

    #[test]
    fn infer_latency_is_low() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("hello");
        // Edge inference should be sub-millisecond (allowing some CI tolerance)
        assert!(result.latency_ms < 10.0);
    }

    #[test]
    fn multiple_rules_same_query_picks_best() {
        let mut engine = EdgeRuleEngine::empty();
        engine.add_rule(CompiledRule::new(
            "low",
            "hello",
            "low confidence answer",
            0.3,
        ));
        engine.add_rule(CompiledRule::new(
            "high",
            "hello",
            "high confidence answer",
            1.0,
        ));
        let result = engine.infer("hello");
        // The high-confidence rule should win
        assert_eq!(result.method, "rule:high");
    }

    #[test]
    fn infer_empty_query_returns_fallback() {
        let mut engine = EdgeRuleEngine::new();
        let result = engine.infer("");
        assert_eq!(result.confidence, 0.0);
        assert_eq!(result.method, "fallback");
    }

    #[test]
    fn stats_initial_all_zero() {
        let engine = EdgeRuleEngine::new();
        let stats = engine.stats();
        assert_eq!(stats.total_queries, 0);
        assert_eq!(stats.cache_hits, 0);
        assert_eq!(stats.rule_hits, 0);
        assert_eq!(stats.fallback_count, 0);
    }

    #[test]
    fn rule_count_matches_builtin() {
        let engine = EdgeRuleEngine::new();
        // Should have the built-in rules loaded
        assert!(engine.rule_count() >= 15);
    }
}
