//! D6 Novelty Emergence Gate — hypothesis predicate deduplication and telemetry exclusion.
//!
//! Provides strict predicate-level deduplication to prevent runaway hypothesis minting
//! and recursive telemetry self-talk. Evaluates candidate hypotheses by:
//! 1. Excision of telemetry/raw-archive classes (D1/D5/D8 hygiene rules).
//! 2. Stripping boilerplate and extracting the core propositional predicate.
//! 3. Hashing the normalized predicate to reject exact duplicate verdicts.
//! 4. Jaccard semantic distance gating (floor > 0.15) to reject near-duplicate templates.

use std::collections::HashSet;
use wm_memory::Memory;
use wm_memory::memory::content_hash;

/// Stop words excluded during predicate semantic distance calculation.
const PREDICATE_STOP_WORDS: &[&str] = &[
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "and", "or", "if", "it", "its", "this", "that", "these", "those", "may", "can",
    "will",
];

/// The result of evaluating a candidate hypothesis through the D6 Novelty Gate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NoveltyVerdict {
    /// The hypothesis is genuinely novel and accepted for persistence.
    Accepted {
        /// Extracted core predicate claim.
        predicate: String,
        /// SHA-256 hash of the normalized predicate.
        predicate_hash: String,
    },
    /// The hypothesis was rejected by the novelty gate.
    Rejected {
        /// Reason for rejection.
        reason: String,
    },
}

impl NoveltyVerdict {
    /// Whether the candidate was accepted.
    #[must_use]
    pub const fn is_accepted(&self) -> bool {
        matches!(self, Self::Accepted { .. })
    }
}

/// Extracts the core propositional predicate from hypothesis text.
///
/// Strips boilerplate prefixes, quotes, parenthesized parameters,
/// and trailing rationale clauses to isolate the underlying claim.
#[must_use]
pub fn extract_predicate(content: &str) -> String {
    let mut text = content.trim();

    // 1. Strip common boilerplate prefixes
    let prefixes = [
        "Hypothesis (counterfactual):",
        "Hypothesis (counterfactual) -",
        "Hypothesis:",
        "Hypothesis -",
        "Proposal:",
        "Insight:",
        "Observation:",
    ];

    for prefix in &prefixes {
        if let Some(rest) = text.strip_prefix(prefix) {
            text = rest.trim();
            break;
        }
    }

    // 2. Remove parenthesized metadata like (reach=5) or (score=0.92)
    let mut without_parens = String::with_capacity(text.len());
    let mut paren_depth = 0usize;
    for c in text.chars() {
        match c {
            '(' => paren_depth += 1,
            ')' => {
                paren_depth = paren_depth.saturating_sub(1);
            }
            _ if paren_depth == 0 => without_parens.push(c),
            _ => {}
        }
    }

    // 3. Remove single and double quoted segments (e.g. memory snippets '...')
    let mut without_quotes = String::with_capacity(without_parens.len());
    let mut in_single = false;
    let mut in_double = false;
    for c in without_parens.chars() {
        match c {
            '\'' if !in_double => in_single = !in_single,
            '"' if !in_single => in_double = !in_double,
            _ if !in_single && !in_double => without_quotes.push(c),
            _ => {}
        }
    }

    // 4. Split on rationale / delimiter markers to isolate the claim clause
    let claim = if let Some((first, _)) = without_quotes.split_once(" — ") {
        first
    } else if let Some((first, _)) = without_quotes.split_once(" - ") {
        first
    } else if let Some((first, _)) = without_quotes.split_once(" Lesson: ") {
        first
    } else if let Some((first, _)) = without_quotes.split_once(" because ") {
        first
    } else {
        &without_quotes
    };

    // 5. Normalize whitespace and lowercase
    let words: Vec<&str> = claim.split_whitespace().collect();
    words.join(" ").to_lowercase()
}

/// Compute SHA-256 hash of a normalized predicate string.
#[must_use]
pub fn compute_predicate_hash(predicate: &str) -> String {
    content_hash(predicate)
}

/// Extract keyword set from predicate for semantic distance calculation.
#[must_use]
pub fn extract_predicate_keywords(predicate: &str) -> HashSet<String> {
    let stop_set: HashSet<&str> = PREDICATE_STOP_WORDS.iter().copied().collect();
    predicate
        .split(|c: char| !c.is_alphanumeric() && c != '_')
        .filter(|w| w.len() > 2 && !stop_set.contains(*w))
        .map(str::to_lowercase)
        .collect()
}

/// Compute Jaccard semantic distance (0.0 to 1.0) between two keyword sets.
/// Distance = 1.0 - Jaccard Similarity.
#[must_use]
pub fn predicate_semantic_distance<S>(a: &HashSet<String, S>, b: &HashSet<String, S>) -> f32
where
    S: std::hash::BuildHasher,
{
    if a.is_empty() || b.is_empty() {
        return 1.0;
    }
    let intersection = a.intersection(b).count();
    let union = a.union(b).count();
    if union == 0 {
        return 1.0;
    }
    1.0 - (intersection as f32 / union as f32)
}

/// D6 Novelty Emergence Gate.
///
/// Ensures hypotheses minted during dream consolidation and cognitive cycles
/// are non-telemetry, non-duplicate, and exceed a 0.15 semantic novelty floor.
#[derive(Debug, Default, Clone)]
pub struct NoveltyGate {
    /// Known predicate hashes (exact duplicate prevention)
    seen_hashes: HashSet<String>,
    /// Known predicate keyword sets for near-duplicate distance checking
    known_predicates: Vec<(String, HashSet<String>)>,
}

impl NoveltyGate {
    /// Create a new empty novelty gate.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Pre-populate the novelty gate with existing hypotheses from the store.
    #[must_use]
    pub fn from_existing_hypotheses(hypotheses: &[Memory]) -> Self {
        let mut gate = Self::new();
        for mem in hypotheses {
            // Exclude telemetry memories from being the baseline comparison corpus
            if mem.is_telemetry_or_noise() {
                continue;
            }
            let pred = extract_predicate(&mem.content);
            if pred.is_empty() {
                continue;
            }
            let hash = compute_predicate_hash(&pred);
            let kws = extract_predicate_keywords(&pred);
            gate.seen_hashes.insert(hash);
            gate.known_predicates.push((pred, kws));
        }
        gate
    }

    /// Evaluate a candidate hypothesis content.
    pub fn evaluate(&mut self, content: &str, is_telemetry: bool) -> NoveltyVerdict {
        // 1. Exclude by class first (D1/D5/D8 rule)
        if is_telemetry {
            return NoveltyVerdict::Rejected {
                reason: "excluded by class: source is telemetry/raw-archive".into(),
            };
        }

        // Check if content itself is a raw telemetry payload
        if (content.starts_with('{') || content.starts_with('['))
            && (content.contains("\"turn_type\"")
                || content.contains("\"friction\"")
                || content.contains("\"latency_ms\""))
        {
            return NoveltyVerdict::Rejected {
                reason: "excluded by class: candidate contains raw telemetry json".into(),
            };
        }

        // 2. Extract normalized propositional predicate
        let predicate = extract_predicate(content);
        if predicate.len() < 5 {
            return NoveltyVerdict::Rejected {
                reason: "insufficient predicate length".into(),
            };
        }

        // 3. Predicate-level exact duplicate hash check
        let hash = compute_predicate_hash(&predicate);
        if self.seen_hashes.contains(&hash) {
            return NoveltyVerdict::Rejected {
                reason: format!("duplicate predicate hash: {hash}"),
            };
        }

        // 4. Semantic distance check (> 0.15 floor against existing hypotheses)
        let candidate_kws = extract_predicate_keywords(&predicate);
        if !candidate_kws.is_empty() {
            for (existing_pred, existing_kws) in &self.known_predicates {
                let dist = predicate_semantic_distance(&candidate_kws, existing_kws);
                if dist <= 0.15 {
                    return NoveltyVerdict::Rejected {
                        reason: format!(
                            "near-duplicate predicate (distance {dist:.2} <= 0.15) against: '{existing_pred}'"
                        ),
                    };
                }
            }
        }

        // Passed novelty gate: record and accept
        self.seen_hashes.insert(hash.clone());
        self.known_predicates
            .push((predicate.clone(), candidate_kws));

        NoveltyVerdict::Accepted {
            predicate,
            predicate_hash: hash,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_predicate_strips_boilerplate_and_snippets() {
        let text1 = "Hypothesis: Hub memory 'turn 42: user asked about rust' (reach=7) confirmed as cross-cutting pattern — current consolidation is appropriate.";
        let pred1 = extract_predicate(text1);
        assert_eq!(pred1, "hub memory confirmed as cross-cutting pattern");

        let text2 = "Hypothesis: Hub memory 'different query about python' (reach=12) confirmed as cross-cutting pattern — current consolidation is appropriate.";
        let pred2 = extract_predicate(text2);
        assert_eq!(pred2, "hub memory confirmed as cross-cutting pattern");

        // The predicates match exactly despite different memory contents!
        assert_eq!(
            compute_predicate_hash(&pred1),
            compute_predicate_hash(&pred2)
        );
    }

    #[test]
    fn test_falsification_1042_identical_verdicts() {
        // The August 30 runaway autonomy regression test:
        // 1,042 templated verdicts with different turn references.
        let mut gate = NoveltyGate::new();
        let mut accepted = 0;
        let mut rejected = 0;

        for i in 0..1042 {
            let content = format!(
                "Hypothesis: Hub memory 'turn {i}: message payload' (reach={}) confirmed as cross-cutting pattern — current consolidation is appropriate.",
                5 + (i % 10)
            );
            match gate.evaluate(&content, false) {
                NoveltyVerdict::Accepted { .. } => accepted += 1,
                NoveltyVerdict::Rejected { .. } => rejected += 1,
            }
        }

        // Only the first instance is accepted; all subsequent 1041 are rejected!
        assert_eq!(accepted, 1);
        assert_eq!(rejected, 1041);
    }

    #[test]
    fn test_telemetry_source_rejected_by_class() {
        let mut gate = NoveltyGate::new();
        let content = "Hypothesis: Some genuinely novel insight that would otherwise pass";
        let verdict = gate.evaluate(content, true);
        assert!(!verdict.is_accepted());
        assert!(
            matches!(verdict, NoveltyVerdict::Rejected { ref reason } if reason.contains("excluded by class"))
        );
    }

    #[test]
    fn test_near_duplicate_distance_threshold() {
        let mut gate = NoveltyGate::new();
        let verdict1 = gate.evaluate(
            "Hypothesis: Distributed raft consensus protocol requires strict quorum lease verification for linearizability.",
            false,
        );
        assert!(verdict1.is_accepted());

        // Highly overlapping near-duplicate (90% overlap, distance 0.10 <= 0.15)
        let verdict2 = gate.evaluate(
            "Hypothesis: Distributed raft consensus protocol requires strict quorum lease verification for linearizability guarantees.",
            false,
        );
        assert!(!verdict2.is_accepted());
        assert!(
            matches!(verdict2, NoveltyVerdict::Rejected { ref reason } if reason.contains("near-duplicate"))
        );

        // Truly novel claim
        let verdict3 = gate.evaluate(
            "Hypothesis: Zero-copy deserialization using rmp_serde reduces LMDB transaction latency.",
            false,
        );
        assert!(verdict3.is_accepted());
    }
}
