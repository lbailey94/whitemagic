//! Semantic coordinate encoding — Tantivy TF-IDF bridge.
//!
//! Replaces the SHA-256 hash-based `Coordinate5D::encode()` with semantically
//! meaningful coordinates derived from anchor-based term frequency analysis.
//!
//! Three semantic axes (ported from v2's anchor embedding + PCA concept):
//! - **x**: Logic ↔ Emotion
//! - **y**: Micro ↔ Macro
//! - **z**: Time ↔ Space
//!
//! For each axis, two poles of anchor terms are defined. The encoder tokenizes
//! the input text using Tantivy's `SimpleTokenizer` + `LowerCaser` (consistent
//! with the search index), computes term frequencies, and projects to [0, 1]
//! per axis using a smoothed ratio of pole scores.

use ahash::AHashMap;
use tantivy::tokenizer::{LowerCaser, SimpleTokenizer, TextAnalyzer, TokenStream};

use wm_core::Coordinate5D;

/// Semantic scores for the three content-derived axes.
#[derive(Debug, Clone, PartialEq)]
pub struct SemanticScores {
    /// Logic (0.0) ↔ Emotion (1.0)
    pub x: f32,
    /// Micro (0.0) ↔ Macro (1.0)
    pub y: f32,
    /// Time (0.0) ↔ Space (1.0)
    pub z: f32,
}

impl SemanticScores {
    /// Neutral scores (all axes at 0.5 — no semantic signal).
    #[must_use]
    pub const fn neutral() -> Self {
        Self {
            x: 0.5,
            y: 0.5,
            z: 0.5,
        }
    }
}

/// Anchor term sets for the three semantic axes.
#[derive(Debug, Clone)]
struct SemanticAnchors {
    logic: &'static [&'static str],
    emotion: &'static [&'static str],
    micro: &'static [&'static str],
    macro_: &'static [&'static str],
    time: &'static [&'static str],
    space: &'static [&'static str],
}

impl Default for SemanticAnchors {
    fn default() -> Self {
        Self {
            logic: &[
                "algorithm",
                "code",
                "data",
                "function",
                "method",
                "system",
                "process",
                "structure",
                "analysis",
                "compute",
                "parameter",
                "model",
                "formula",
                "theorem",
                "proof",
                "derive",
                "calculate",
                "measure",
                "metric",
                "logic",
                "rational",
                "objective",
                "systematic",
                "technical",
                "engineering",
            ],
            emotion: &[
                "feel",
                "feeling",
                "emotion",
                "love",
                "fear",
                "joy",
                "sad",
                "happy",
                "angry",
                "hope",
                "care",
                "beauty",
                "art",
                "soul",
                "heart",
                "passion",
                "dream",
                "wonder",
                "intuition",
                "empathy",
                "spirit",
                "subjective",
                "personal",
                "emotional",
                "expressive",
            ],
            micro: &[
                "detail",
                "specific",
                "small",
                "local",
                "individual",
                "element",
                "atom",
                "bit",
                "byte",
                "cell",
                "node",
                "token",
                "word",
                "line",
                "step",
                "tiny",
                "precise",
                "exact",
                "narrow",
                "component",
                "unit",
                "instance",
            ],
            macro_: &[
                "global",
                "universe",
                "network",
                "architecture",
                "framework",
                "theory",
                "paradigm",
                "concept",
                "abstract",
                "broad",
                "general",
                "whole",
                "total",
                "infinite",
                "cosmic",
                "universal",
                "grand",
                "scale",
                "overview",
                "ecosystem",
                "pattern",
                "horizon",
            ],
            time: &[
                "time",
                "when",
                "before",
                "after",
                "now",
                "then",
                "past",
                "future",
                "present",
                "moment",
                "duration",
                "temporal",
                "chronological",
                "history",
                "timeline",
                "schedule",
                "deadline",
                "period",
                "phase",
                "cycle",
                "event",
                "sequence",
            ],
            space: &[
                "space",
                "where",
                "here",
                "there",
                "location",
                "position",
                "area",
                "region",
                "zone",
                "place",
                "distance",
                "spatial",
                "coordinate",
                "map",
                "geometry",
                "layout",
                "boundary",
                "field",
                "domain",
                "environment",
                "context",
            ],
        }
    }
}

/// Semantic encoder using Tantivy tokenization and anchor-based TF projection.
///
/// Tokenizes text with `SimpleTokenizer` + `LowerCaser` (same pipeline as the
/// Tantivy search index), then computes term frequencies against anchor term
/// sets for each semantic axis. Produces `SemanticScores` in [0, 1] per axis.
pub struct SemanticEncoder {
    anchors: SemanticAnchors,
}

impl Default for SemanticEncoder {
    fn default() -> Self {
        Self::new()
    }
}

impl SemanticEncoder {
    /// Create a new encoder with default anchor terms and Tantivy tokenization.
    #[must_use]
    pub fn new() -> Self {
        Self {
            anchors: SemanticAnchors::default(),
        }
    }

    /// Encode text into semantic scores (x, y, z) in [0, 1].
    ///
    /// Each axis is computed as:
    /// `axis = (pos_pole + smoothing) / (neg_pole + pos_pole + 2 * smoothing)`
    ///
    /// With smoothing = 0.5, neutral text (no anchor terms) returns 0.5.
    #[must_use]
    pub fn encode(&self, text: &str) -> SemanticScores {
        let freqs = self.term_frequencies(text);
        let x = self.axis_score(&freqs, self.anchors.logic, self.anchors.emotion);
        let y = self.axis_score(&freqs, self.anchors.micro, self.anchors.macro_);
        let z = self.axis_score(&freqs, self.anchors.time, self.anchors.space);
        SemanticScores { x, y, z }
    }

    /// Encode text into a full `Coordinate5D` with temporal and importance context.
    #[must_use]
    pub fn encode_coordinate(
        &self,
        text: &str,
        temporal_weight: f32,
        importance: f32,
    ) -> Coordinate5D {
        let scores = self.encode(text);
        Coordinate5D::from_semantic(scores.x, scores.y, scores.z, temporal_weight, importance)
    }

    /// Compute term frequencies from text using Tantivy tokenization.
    fn term_frequencies(&self, text: &str) -> AHashMap<String, f32> {
        let mut freqs: AHashMap<String, f32> = AHashMap::new();
        let mut analyzer = TextAnalyzer::builder(SimpleTokenizer::default())
            .filter(LowerCaser)
            .build();
        let mut stream = analyzer.token_stream(text);
        while stream.advance() {
            *freqs.entry(stream.token().text.clone()).or_insert(0.0) += 1.0;
        }
        freqs
    }

    /// Compute axis score from term frequencies and two anchor poles.
    fn axis_score(
        &self,
        freqs: &AHashMap<String, f32>,
        neg_pole: &[&str],
        pos_pole: &[&str],
    ) -> f32 {
        let neg = self.pole_score(freqs, neg_pole);
        let pos = self.pole_score(freqs, pos_pole);
        let smoothing = 0.5;
        (pos + smoothing) / 2.0f32.mul_add(smoothing, neg + pos)
    }

    /// Sum of sublinearly-scaled term frequencies for anchor terms.
    fn pole_score(&self, freqs: &AHashMap<String, f32>, terms: &[&str]) -> f32 {
        let mut score = 0.0f32;
        for term in terms {
            if let Some(&freq) = freqs.get(*term) {
                // Sublinear scaling: 1 + ln(freq) to avoid dominance by repeated terms
                score += 1.0 + freq.ln();
            }
        }
        score
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn neutral_text_returns_midpoint() {
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode("the quick brown fox jumps over the lazy dog");
        // No anchor terms in this text — all axes should be near 0.5
        assert!((scores.x - 0.5).abs() < 0.01);
        assert!((scores.y - 0.5).abs() < 0.01);
        assert!((scores.z - 0.5).abs() < 0.01);
    }

    #[test]
    fn empty_text_returns_neutral() {
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode("");
        assert_eq!(scores, SemanticScores::neutral());
    }

    #[test]
    fn logic_text_scores_toward_zero_x() {
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode(
            "The algorithm computes data using a systematic method with precise parameters",
        );
        // Logic-heavy text → x should be below 0.5
        assert!(
            scores.x < 0.5,
            "x = {} should be < 0.5 for logic text",
            scores.x
        );
    }

    #[test]
    fn emotion_text_scores_toward_one_x() {
        let encoder = SemanticEncoder::new();
        let scores = encoder
            .encode("I feel love and joy in my heart, a deep passion and empathy for beauty");
        // Emotion-heavy text → x should be above 0.5
        assert!(
            scores.x > 0.5,
            "x = {} should be > 0.5 for emotion text",
            scores.x
        );
    }

    #[test]
    fn micro_text_scores_toward_zero_y() {
        let encoder = SemanticEncoder::new();
        let scores = encoder
            .encode("Each individual element and tiny detail of the specific component matters");
        // Micro-heavy text → y should be below 0.5
        assert!(
            scores.y < 0.5,
            "y = {} should be < 0.5 for micro text",
            scores.y
        );
    }

    #[test]
    fn macro_text_scores_toward_one_y() {
        let encoder = SemanticEncoder::new();
        let scores =
            encoder.encode("The global architecture is a universal framework on a cosmic scale");
        // Macro-heavy text → y should be above 0.5
        assert!(
            scores.y > 0.5,
            "y = {} should be > 0.5 for macro text",
            scores.y
        );
    }

    #[test]
    fn time_text_scores_toward_zero_z() {
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode(
            "Before and after that moment, the timeline showed a chronological sequence of events",
        );
        // Time-heavy text → z should be below 0.5
        assert!(
            scores.z < 0.5,
            "z = {} should be < 0.5 for time text",
            scores.z
        );
    }

    #[test]
    fn space_text_scores_toward_one_z() {
        let encoder = SemanticEncoder::new();
        let scores = encoder.encode(
            "The spatial layout of the region defines the boundary and geometry of the area",
        );
        // Space-heavy text → z should be above 0.5
        assert!(
            scores.z > 0.5,
            "z = {} should be > 0.5 for space text",
            scores.z
        );
    }

    #[test]
    fn encode_is_deterministic() {
        let encoder = SemanticEncoder::new();
        let a = encoder.encode("The algorithm processes data with logic and analysis");
        let b = encoder.encode("The algorithm processes data with logic and analysis");
        assert_eq!(a, b);
    }

    #[test]
    fn similar_texts_produce_similar_coordinates() {
        let encoder = SemanticEncoder::new();
        let a = encoder.encode_coordinate(
            "The algorithm computes data using a systematic method",
            0.5,
            0.5,
        );
        let b = encoder.encode_coordinate(
            "The algorithm processes data using a systematic approach",
            0.5,
            0.5,
        );
        let c = encoder.encode_coordinate(
            "I feel love and joy in my heart with deep passion",
            0.5,
            0.5,
        );

        let dist_ab = a.semantic_distance_to(&b);
        let dist_ac = a.semantic_distance_to(&c);

        // Similar texts should be closer than dissimilar texts
        assert!(
            dist_ab < dist_ac,
            "dist(a,b)={dist_ab:.4} should be < dist(a,c)={dist_ac:.4}"
        );
    }

    #[test]
    fn encode_coordinate_produces_valid_range() {
        let encoder = SemanticEncoder::new();
        let coord = encoder.encode_coordinate("test content", 0.7, 0.9);
        assert!(coord.x >= 0.0 && coord.x <= 1.0);
        assert!(coord.y >= 0.0 && coord.y <= 1.0);
        assert!(coord.z >= 0.0 && coord.z <= 1.0);
        assert!((coord.w - 0.7).abs() < f32::EPSILON);
        assert!((coord.v - 0.9).abs() < f32::EPSILON);
    }

    #[test]
    fn mixed_content_produces_intermediate_scores() {
        let encoder = SemanticEncoder::new();
        let scores = encoder
            .encode("The algorithm processes data with emotional passion and systematic beauty");
        // Mixed logic + emotion → x should be somewhere in the middle
        assert!(
            (0.3..=0.7).contains(&scores.x),
            "x = {} should be in [0.3, 0.7] for mixed text",
            scores.x
        );
    }

    #[test]
    fn case_insensitive_matching() {
        let encoder = SemanticEncoder::new();
        let lower = encoder.encode("the algorithm computes data");
        let upper = encoder.encode("The ALGORITHM COMPUTES DATA");
        assert_eq!(lower, upper);
    }

    #[test]
    fn semantic_scores_neutral() {
        assert_eq!(
            SemanticScores::neutral(),
            SemanticScores {
                x: 0.5,
                y: 0.5,
                z: 0.5
            }
        );
    }
}
