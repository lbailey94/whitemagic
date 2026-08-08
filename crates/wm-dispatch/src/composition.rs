//! Tool Composition Discovery — analyzes dispatch sequences to find common patterns.
//!
//! When tools are frequently called in sequence (e.g. `memory.search` →
//! `memory.create` → `memory.associate`), the composition discovery module
//! identifies these patterns and surfaces them as reusable "tool chains".
//!
//! This enables:
//! - Suggesting next tools based on recent dispatch history
//! - Identifying common workflows for documentation or automation
//! - Detecting co-usage patterns that could become composite tools
//!
//! # How it works
//!
//! The `CompositionTracker` records tool names in dispatch order. A sliding
//! window of recent calls is maintained. Periodically, the window is scanned
//! for recurring subsequences of length 2–5. Patterns that appear at least
//! `min_frequency` times are promoted to `CompositionPattern` entries.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A discovered tool composition pattern (a frequent sequence of tool calls).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CompositionPattern {
    /// The ordered sequence of tool names.
    pub sequence: Vec<String>,
    /// How many times this pattern was observed.
    pub frequency: usize,
    /// Average number of seconds between the first and last tool in the pattern.
    pub avg_span_secs: f64,
}

impl CompositionPattern {
    /// A display name for this pattern (tools joined by ` → `).
    #[must_use]
    pub fn display_name(&self) -> String {
        self.sequence.join(" → ")
    }

    /// Pattern length (number of tools).
    #[must_use]
    pub fn len(&self) -> usize {
        self.sequence.len()
    }

    /// Whether this pattern is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.sequence.is_empty()
    }
}

/// Configuration for composition discovery.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompositionConfig {
    /// Maximum window size for recent tool calls (sliding window).
    pub window_size: usize,
    /// Minimum pattern length to detect (default: 2).
    pub min_pattern_len: usize,
    /// Maximum pattern length to detect (default: 5).
    pub max_pattern_len: usize,
    /// Minimum frequency for a pattern to be promoted (default: 3).
    pub min_frequency: usize,
}

impl Default for CompositionConfig {
    fn default() -> Self {
        Self {
            window_size: 200,
            min_pattern_len: 2,
            max_pattern_len: 5,
            min_frequency: 3,
        }
    }
}

/// Tracks tool dispatch sequences and discovers composition patterns.
///
/// Thread-safe via internal mutex (call recording is fast, analysis is
/// done on demand).
pub struct CompositionTracker {
    config: CompositionConfig,
    recent: std::sync::Mutex<Vec<String>>,
    /// All observed patterns with frequencies (updated on `discover()`).
    patterns: std::sync::Mutex<HashMap<Vec<String>, usize>>,
}

impl CompositionTracker {
    /// Create a new composition tracker with the given config.
    #[must_use]
    pub fn new(config: CompositionConfig) -> Self {
        Self {
            config,
            recent: std::sync::Mutex::new(Vec::new()),
            patterns: std::sync::Mutex::new(HashMap::new()),
        }
    }

    /// Create a tracker with default configuration.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(CompositionConfig::default())
    }

    /// Record a tool dispatch.
    ///
    /// Call this after each tool is dispatched. The tool name is appended
    /// to the sliding window of recent calls.
    pub fn record(&self, tool_name: &str) {
        let Ok(mut recent) = self.recent.lock() else {
            return;
        };
        recent.push(tool_name.to_string());
        if recent.len() > self.config.window_size {
            recent.remove(0);
        }
    }

    /// Discover composition patterns from the recent dispatch history.
    ///
    /// Scans the sliding window for all subsequences of length
    /// `min_pattern_len`..=`max_pattern_len` and returns those that
    /// appear at least `min_frequency` times.
    ///
    /// Also updates the internal pattern store.
    #[must_use]
    pub fn discover(&self) -> Vec<CompositionPattern> {
        let Ok(recent) = self.recent.lock() else {
            return Vec::new();
        };
        let mut counts: HashMap<Vec<String>, usize> = HashMap::new();

        let max_len = self.config.max_pattern_len.min(recent.len());

        for pattern_len in self.config.min_pattern_len..=max_len {
            for i in 0..=recent.len().saturating_sub(pattern_len) {
                let seq = &recent[i..i + pattern_len];
                *counts.entry(seq.to_vec()).or_insert(0) += 1;
            }
        }

        // Release the `recent` lock before touching `patterns` to avoid
        // holding two locks at once.
        drop(recent);

        // Filter by minimum frequency and sort by frequency (descending)
        let mut patterns: Vec<CompositionPattern> = counts
            .into_iter()
            .filter(|(_, freq)| *freq >= self.config.min_frequency)
            .map(|(sequence, frequency)| CompositionPattern {
                sequence,
                frequency,
                avg_span_secs: 0.0, // We don't track timestamps yet
            })
            .collect();

        patterns.sort_by(|a, b| {
            b.frequency
                .cmp(&a.frequency)
                .then_with(|| b.sequence.len().cmp(&a.sequence.len()))
        });

        // Update internal store
        if let Ok(mut store) = self.patterns.lock() {
            store.clear();
            for p in &patterns {
                store.insert(p.sequence.clone(), p.frequency);
            }
        }

        patterns
    }

    /// Get the most frequent patterns (top N).
    #[must_use]
    pub fn top_patterns(&self, n: usize) -> Vec<CompositionPattern> {
        let patterns = self.discover();
        patterns.into_iter().take(n).collect()
    }

    /// Suggest the next tool(s) based on the recent dispatch history.
    ///
    /// Given the last N tool calls, finds patterns that start with those
    /// tools and returns the most likely continuation.
    #[must_use]
    pub fn suggest_next(&self, last_n: usize) -> Vec<String> {
        let context: Vec<String> = {
            let Ok(recent) = self.recent.lock() else {
                return Vec::new();
            };
            if recent.is_empty() {
                return Vec::new();
            }
            let n = last_n.min(recent.len());
            recent[recent.len() - n..].to_vec()
        };

        let patterns = self.discover();
        let mut suggestions: HashMap<String, usize> = HashMap::new();

        for pattern in &patterns {
            if pattern.sequence.len() <= context.len() {
                continue;
            }
            // Check if the pattern starts with the context
            if &pattern.sequence[..context.len()] == context.as_slice() {
                let next_tool = &pattern.sequence[context.len()];
                *suggestions.entry(next_tool.clone()).or_insert(0) += pattern.frequency;
            }
        }

        let mut sorted: Vec<(String, usize)> = suggestions.into_iter().collect();
        sorted.sort_by(|a, b| b.1.cmp(&a.1));
        sorted.into_iter().map(|(tool, _)| tool).collect()
    }

    /// Get the current number of recorded dispatches in the window.
    #[must_use]
    pub fn window_count(&self) -> usize {
        self.recent.lock().map(|r| r.len()).unwrap_or(0)
    }

    /// Clear all recorded dispatches and discovered patterns.
    pub fn clear(&self) {
        if let Ok(mut recent) = self.recent.lock() {
            recent.clear();
        }
        if let Ok(mut patterns) = self.patterns.lock() {
            patterns.clear();
        }
    }
}

impl Default for CompositionTracker {
    fn default() -> Self {
        Self::with_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn record_and_window_count() {
        let tracker = CompositionTracker::with_defaults();
        assert_eq!(tracker.window_count(), 0);
        tracker.record("memory.search");
        tracker.record("memory.create");
        assert_eq!(tracker.window_count(), 2);
    }

    #[test]
    fn discover_finds_pairs() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 2,
        });

        // Record: A B A B A B → pair "A B" appears 3 times, "B A" appears 2 times
        for tool in &["A", "B", "A", "B", "A", "B"] {
            tracker.record(tool);
        }

        let patterns = tracker.discover();
        assert!(
            patterns
                .iter()
                .any(|p| p.sequence == ["A".to_string(), "B".to_string()] && p.frequency == 3)
        );
        assert!(
            patterns
                .iter()
                .any(|p| p.sequence == ["B".to_string(), "A".to_string()] && p.frequency == 2)
        );
    }

    #[test]
    fn discover_finds_triples() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 3,
            max_pattern_len: 3,
            min_frequency: 2,
        });

        // Record: A B C A B C → triple "A B C" appears 2 times
        for tool in &["A", "B", "C", "A", "B", "C"] {
            tracker.record(tool);
        }

        let patterns = tracker.discover();
        assert!(patterns.iter().any(|p| p.sequence
            == ["A".to_string(), "B".to_string(), "C".to_string()]
            && p.frequency == 2));
    }

    #[test]
    fn discover_filters_by_min_frequency() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 5, // high threshold
        });

        for tool in &["A", "B", "A", "B"] {
            tracker.record(tool);
        }

        let patterns = tracker.discover();
        // "A B" appears 2 times, "B A" appears 1 time — neither meets threshold of 5
        assert!(patterns.is_empty());
    }

    #[test]
    fn discover_sorted_by_frequency_descending() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 2,
        });

        // "A B" appears 3 times, "B C" appears 2 times
        for tool in &["A", "B", "A", "B", "A", "B", "C", "B", "C"] {
            tracker.record(tool);
        }

        let patterns = tracker.discover();
        assert!(!patterns.is_empty());
        // Most frequent should be first
        assert!(patterns[0].frequency >= patterns[1].frequency);
    }

    #[test]
    fn suggest_next_finds_continuation() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 3,
            min_frequency: 2,
        });

        // Record: A B C A B C A B
        for tool in &["A", "B", "C", "A", "B", "C", "A", "B"] {
            tracker.record(tool);
        }

        // After "A B", the next tool should be "C"
        let suggestions = tracker.suggest_next(2);
        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0], "C");
    }

    #[test]
    fn suggest_next_empty_when_no_history() {
        let tracker = CompositionTracker::with_defaults();
        let suggestions = tracker.suggest_next(3);
        assert!(suggestions.is_empty());
    }

    #[test]
    fn suggest_next_empty_when_no_patterns() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 10, // high threshold — no patterns will match
        });

        tracker.record("A");
        tracker.record("B");
        let suggestions = tracker.suggest_next(1);
        assert!(suggestions.is_empty());
    }

    #[test]
    fn window_size_evicts_old_entries() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 3,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 1,
        });

        tracker.record("A");
        tracker.record("B");
        tracker.record("C");
        tracker.record("D"); // should evict "A"
        assert_eq!(tracker.window_count(), 3);

        let patterns = tracker.discover();
        // Should find "B C", "C D" but not "A B"
        assert!(
            patterns
                .iter()
                .any(|p| p.sequence == ["C".to_string(), "D".to_string()])
        );
        assert!(
            !patterns
                .iter()
                .any(|p| p.sequence == ["A".to_string(), "B".to_string()])
        );
    }

    #[test]
    fn clear_resets_everything() {
        let tracker = CompositionTracker::with_defaults();
        tracker.record("A");
        tracker.record("B");
        assert_eq!(tracker.window_count(), 2);

        tracker.clear();
        assert_eq!(tracker.window_count(), 0);

        let patterns = tracker.discover();
        assert!(patterns.is_empty());
    }

    #[test]
    fn top_patterns_limits_results() {
        let tracker = CompositionTracker::new(CompositionConfig {
            window_size: 100,
            min_pattern_len: 2,
            max_pattern_len: 2,
            min_frequency: 1,
        });

        for tool in &["A", "B", "C", "D", "A", "B"] {
            tracker.record(tool);
        }

        let top = tracker.top_patterns(1);
        assert_eq!(top.len(), 1);
    }

    #[test]
    fn display_name_joins_with_arrow() {
        let p = CompositionPattern {
            sequence: vec!["memory.search".to_string(), "memory.create".to_string()],
            frequency: 5,
            avg_span_secs: 1.2,
        };
        assert_eq!(p.display_name(), "memory.search → memory.create");
    }

    #[test]
    fn pattern_len_and_empty() {
        let p = CompositionPattern {
            sequence: vec!["A".to_string(), "B".to_string(), "C".to_string()],
            frequency: 2,
            avg_span_secs: 0.0,
        };
        assert_eq!(p.len(), 3);
        assert!(!p.is_empty());

        let empty = CompositionPattern {
            sequence: vec![],
            frequency: 0,
            avg_span_secs: 0.0,
        };
        assert!(empty.is_empty());
    }

    #[test]
    fn realistic_tool_sequence() {
        let tracker = CompositionTracker::with_defaults();

        // Simulate a realistic workflow: search → create → associate
        for _ in 0..5 {
            tracker.record("memory.search");
            tracker.record("memory.create");
            tracker.record("memory.associate");
        }

        let patterns = tracker.discover();
        assert!(!patterns.is_empty());

        // The full triple should be the most frequent
        let top = &patterns[0];
        assert_eq!(
            top.sequence,
            vec![
                "memory.search".to_string(),
                "memory.create".to_string(),
                "memory.associate".to_string()
            ]
        );
        assert_eq!(top.frequency, 5);
    }

    #[test]
    fn suggest_next_with_realistic_sequence() {
        let tracker = CompositionTracker::with_defaults();

        for _ in 0..5 {
            tracker.record("memory.search");
            tracker.record("memory.create");
            tracker.record("memory.associate");
        }

        // The last recorded call is "memory.associate"; the recurring
        // cycle is search → create → associate → search...
        let suggestions = tracker.suggest_next(1);
        assert_eq!(suggestions[0], "memory.search");

        // The last two calls are "create → associate"; the cycle
        // continues with "memory.search"
        let suggestions = tracker.suggest_next(2);
        assert_eq!(suggestions[0], "memory.search");

        // After recording another "memory.search", the cycle continues
        // with "memory.create"
        tracker.record("memory.search");
        let suggestions = tracker.suggest_next(1);
        assert_eq!(suggestions[0], "memory.create");
    }
}
