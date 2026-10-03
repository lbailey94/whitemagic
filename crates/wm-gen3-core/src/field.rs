//! Dynamic field: minimal relations `e=(w,s,c,t)`, the generic tokenizer, and the
//! pre-declared supersession candidacy rule (`docs/PHASE1_CONTRACTS.md` §2.3).
//!
//! Symbols render; symbols never dispatch — nothing here branches on symbolism.
//! No corpus-shaped vocabulary: the rule uses only shared rare tokens, per-side
//! distinctive rare tokens, and temporal order.

use crate::evidence::EvidenceRecord;

/// The single declared rule id for Phase-1 relation proposals. Ablation A1
/// disables the sweep entirely; this string identifies what proposed a relation.
pub const RULE_ID: &str = "candidacy.v1.shared-rare+value-diff+temporal";

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum RelationKind {
    /// `later → supersedes → earlier`: a later-sourced value replacing an earlier one.
    Supersedes,
    /// `source ↔ target`: Hebbian co-activation / associative link ("neurons that fire together wire together").
    Associates,
    /// `parent → child`: Execution provenance / causal chain (Luna Research: typed execution provenance).
    Causal,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum RelationState {
    Candidate,
    Persistent,
    Cold,
}

/// Epistemic class of a relation. Phase 1: relations are always speculation —
/// they are claims *about* records, never world-evidence (Closure 2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum RelationEpistemic {
    Speculation,
}

/// A field edge `e=(w,s,c,t)` plus the minimum identity/provenance fields.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Relation {
    id: u64,
    kind: RelationKind,
    src: u64,
    dst: u64,
    w: f32,
    s: i8,
    c: f32,
    t: f32,
    class: RelationEpistemic,
    state: RelationState,
    rule_id: String,
    confidence: f32,
    created_sweep: u64,
}

impl Relation {
    #[must_use]
    pub fn id(&self) -> u64 {
        self.id
    }
    #[must_use]
    pub fn kind(&self) -> RelationKind {
        self.kind
    }
    #[must_use]
    pub fn src(&self) -> u64 {
        self.src
    }
    #[must_use]
    pub fn dst(&self) -> u64 {
        self.dst
    }
    #[must_use]
    pub fn weight(&self) -> f32 {
        self.w
    }
    #[must_use]
    pub fn sign(&self) -> i8 {
        self.s
    }
    #[must_use]
    pub fn cost(&self) -> f32 {
        self.c
    }
    #[must_use]
    pub fn trust(&self) -> f32 {
        self.t
    }
    #[must_use]
    pub fn class(&self) -> RelationEpistemic {
        self.class
    }
    #[must_use]
    pub fn state(&self) -> RelationState {
        self.state
    }
    #[must_use]
    pub fn rule_id(&self) -> &str {
        &self.rule_id
    }
    #[must_use]
    pub fn confidence(&self) -> f32 {
        self.confidence
    }
    #[must_use]
    pub fn created_sweep(&self) -> u64 {
        self.created_sweep
    }

    #[must_use]
    pub(crate) fn new(id: u64, src: u64, dst: u64, confidence: f32, sweep: u64) -> Self {
        Self {
            id,
            kind: RelationKind::Supersedes,
            src,
            dst,
            w: 0.5,
            s: 1,
            c: 0.1,
            t: confidence,
            class: RelationEpistemic::Speculation,
            state: RelationState::Candidate,
            rule_id: RULE_ID.to_string(),
            confidence,
            created_sweep: sweep,
        }
    }

    /// Construct a Hebbian associative link between two co-activated records.
    #[must_use]
    pub fn associate(id: u64, src: u64, dst: u64, weight: f32, sweep: u64) -> Self {
        Self {
            id,
            kind: RelationKind::Associates,
            src,
            dst,
            w: weight.clamp(0.0, 1.0),
            s: 1,
            c: 0.05,
            t: weight.clamp(0.0, 1.0),
            class: RelationEpistemic::Speculation,
            state: RelationState::Persistent,
            rule_id: "hebbian.associates.v1".to_string(),
            confidence: weight.clamp(0.0, 1.0),
            created_sweep: sweep,
        }
    }

    /// Construct a causal execution provenance edge from parent event to child outcome.
    #[must_use]
    pub fn causal(id: u64, parent: u64, child: u64, weight: f32, sweep: u64) -> Self {
        Self {
            id,
            kind: RelationKind::Causal,
            src: parent,
            dst: child,
            w: weight.clamp(0.0, 1.0),
            s: 1,
            c: 0.01,
            t: 1.0,
            class: RelationEpistemic::Speculation,
            state: RelationState::Persistent,
            rule_id: "provenance.causal.v1".to_string(),
            confidence: 1.0,
            created_sweep: sweep,
        }
    }

    pub(crate) fn set_state(&mut self, state: RelationState) {
        self.state = state;
    }
}

const STOPWORDS: &[&str] = &[
    "the", "a", "an", "and", "or", "but", "not", "no", "is", "are", "was", "were", "be", "been",
    "being", "am", "do", "does", "did", "have", "has", "had", "i", "im", "ive", "id", "ill", "you",
    "your", "he", "she", "it", "its", "we", "they", "them", "his", "her", "our", "my", "me",
    "mine", "to", "of", "in", "on", "at", "for", "with", "as", "so", "this", "that", "these",
    "those", "there", "here", "about", "into", "over", "just", "really", "very",
    // Interrogatives and auxiliaries are question framing, not content.
    "what", "when", "where", "which", "who", "whom", "whose", "how", "why", "can", "could", "may",
    "might", "shall", "should", "will", "would", "if", "then", "than", "also", "too", "more",
    "most", "some", "any", "all", "each", "other", "such", "only", "same", "ever",
];

/// Deterministic generic tokenizer: lowercase, split on non-alphanumeric, drop
/// stopwords and single characters. Digits with interior dots stay whole
/// (`2.1` is one token); no stemming, no vocabulary tables.
#[must_use]
pub fn tokenize(text: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut current = String::new();
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch.is_alphanumeric() {
            current.extend(ch.to_lowercase());
        } else if ch == '.'
            && !current.is_empty()
            && current.chars().all(|c| c.is_ascii_digit())
            && chars.peek().is_some_and(|n| n.is_ascii_digit())
        {
            current.push('.');
        } else if !current.is_empty() {
            push_token(&mut out, &mut seen, &current);
            current.clear();
        }
    }
    if !current.is_empty() {
        push_token(&mut out, &mut seen, &current);
    }
    out
}

fn push_token(out: &mut Vec<String>, seen: &mut std::collections::HashSet<String>, token: &str) {
    if token.len() >= 2 && !STOPWORDS.contains(&token) && seen.insert(token.to_string()) {
        out.push(token.to_string());
    }
}

/// Token set for co-reference tests.
#[must_use]
pub fn token_set(text: &str) -> std::collections::BTreeSet<String> {
    tokenize(text).into_iter().collect()
}

/// Non-stopword Dice coefficient between two token sets:
/// Dice(A, B) = 2 * |A ∩ B| / (|A| + |B|)
#[must_use]
pub fn dice_coefficient(
    a: &std::collections::BTreeSet<String>,
    b: &std::collections::BTreeSet<String>,
) -> f32 {
    let total = a.len() + b.len();
    if total == 0 {
        return 0.0;
    }
    let intersection = a.intersection(b).count();
    (2.0 * intersection as f32) / (total as f32)
}

/// Anchor coherence criterion (Gate 9C): two records must have sufficient semantic binding
/// to be plausible candidates for supersession, preventing single generic words
/// from creating cross-topic candidate pairs.
/// Returns true if either:
/// 1. Shared rare token count >= 2, OR
/// 2. Non-stopword Dice coefficient >= 0.20
#[must_use]
pub fn anchor_coherence(shared_rare_count: usize, dice: f32) -> bool {
    shared_rare_count >= 2 || dice >= 0.20
}

/// A rare-token lookup: returns the document frequency for a token.
pub type DfLookup<'a> = &'a dyn Fn(&str) -> usize;

/// The pre-declared candidacy rule. Returns a new relation `later → supersedes →
/// earlier` when: the records share at least one *rare* subject token; at least
/// one rare token differs between the sides (values changed); the pair satisfies
/// lexical anchor coherence; and the source order is strict. Confidence blends
/// shared-key count, anchor coherence Dice, and recency gap.
///
/// Deliberately lexical and structural. If it only works on one corpus's
/// linguistic forms, the genericity property tests below fail by definition.
#[must_use]
pub fn propose_supersedes(
    later: &EvidenceRecord,
    earlier: &EvidenceRecord,
    rare_max_df: usize,
    df: DfLookup<'_>,
) -> Option<(u64, u64, f32)> {
    if later.created_at() <= earlier.created_at() {
        return None;
    }
    let l = token_set(later.content());
    let e = token_set(earlier.content());
    let is_rare = |t: &String| df(t.as_str()) <= rare_max_df;

    let shared: Vec<&String> = l.intersection(&e).filter(|t| is_rare(t)).collect();
    if shared.is_empty() {
        return None;
    }
    let distinctive = l.iter().filter(|t| !e.contains(*t) && is_rare(t)).count()
        + e.iter().filter(|t| !l.contains(*t) && is_rare(t)).count();
    if distinctive == 0 {
        return None;
    }

    let dice = dice_coefficient(&l, &e);
    if !anchor_coherence(shared.len(), dice) {
        return None;
    }

    let gap = later.created_at().saturating_sub(earlier.created_at()) as f32;
    let recency = gap / (gap + 8.0);
    let confidence =
        (0.30 + 0.10 * shared.len().min(3) as f32 + 0.15 * dice + 0.15 * recency).min(0.95);
    Some((later.id(), earlier.id(), confidence))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::EvidenceStore;

    fn record(store: &mut EvidenceStore, text: &str) -> EvidenceRecord {
        let id = store.reported(text, "test");
        store.get(id).expect("record exists").clone()
    }

    /// Genericity property test (contracts §2.3): the *same* code path must link
    /// temporal replacements across unrelated domains with no added vocabulary.
    #[test]
    fn genericity_frozen_examples() {
        let examples: &[(&str, &str, &str, &str)] = &[
            (
                "Alice moved from Atlanta to Denver",
                "Alice currently lives in Denver",
                "atlanta",
                "denver",
            ),
            (
                "the server was upgraded from version 2.1 to 2.2",
                "server version is now 2.2",
                "2.1",
                "2.2",
            ),
            (
                "the car color changed from red to blue",
                "car is blue now",
                "red",
                "blue",
            ),
            (
                "her role changed from engineer to manager",
                "she works as manager",
                "engineer",
                "manager",
            ),
            (
                "he used to own a bike, now he owns a car",
                "car owner since spring",
                "bike",
                "car",
            ),
        ];
        for (earlier_text, later_text, old_tok, new_tok) in examples {
            let mut store = EvidenceStore::new();
            let earlier = record(&mut store, earlier_text);
            let later = record(&mut store, later_text);
            let df = |t: &str| {
                if t == *old_tok || t == *new_tok { 1 } else { 4 }
            };
            let proposal = propose_supersedes(&later, &earlier, 2, &df);
            assert!(
                proposal.is_some(),
                "generic rule must link {earlier_text:?} → {later_text:?}"
            );
        }
    }

    /// Negative control: shared common tokens alone are not enough.
    #[test]
    fn common_shared_token_alone_does_not_propose() {
        let mut store = EvidenceStore::new();
        let earlier = record(&mut store, "I like coffee");
        let later = record(&mut store, "I like coffee and tea");
        let df = |_t: &str| 10; // nothing rare
        assert!(propose_supersedes(&later, &earlier, 2, &df).is_none());
    }

    /// A same-value repetition is not a replacement.
    #[test]
    fn same_value_repetition_does_not_propose() {
        let mut store = EvidenceStore::new();
        let earlier = record(&mut store, "I am vegetarian");
        let later = record(&mut store, "I am vegetarian");
        let df = |t: &str| {
            if t == "vegetarian" { 1 } else { 3 }
        };
        assert!(propose_supersedes(&later, &earlier, 2, &df).is_none());
    }

    #[test]
    fn tokenizer_is_generic_and_deterministic() {
        assert_eq!(
            tokenize("Cookie-Book_genre!"),
            vec!["cookie", "book", "genre"]
        );
        assert!(tokenize("the and of").is_empty());
    }

    #[test]
    fn anchor_coherence_filters_single_token_noise() {
        let mut store = EvidenceStore::new();
        // Two long disparate sentences sharing only one word ("package")
        let earlier = record(
            &mut store,
            "the cargo ship delivered the heavy freight package yesterday",
        );
        let later = record(
            &mut store,
            "remember to update the software npm package in production",
        );
        let df = |t: &str| {
            if t == "package" { 1 } else { 5 }
        };
        // Should be rejected because shared_rare = 1 and Dice < 0.20
        assert!(propose_supersedes(&later, &earlier, 2, &df).is_none());
    }

    #[test]
    fn anchor_coherence_accepts_two_shared_rare_tokens() {
        let mut store = EvidenceStore::new();
        let earlier = record(
            &mut store,
            "the redis cluster node failed unexpectedly in the primary datacenter",
        );
        let later = record(
            &mut store,
            "the redis cluster was successfully restarted after failure",
        );
        let df = |t: &str| {
            if t == "redis" || t == "cluster" || t == "node" || t == "restarted" {
                1
            } else {
                5
            }
        };
        // Should be accepted because shared_rare = 2 ("redis", "cluster") and values changed
        assert!(propose_supersedes(&later, &earlier, 2, &df).is_some());
    }
}
