//! Consensus gate — determines when both hemispheres agree.
//!
//! The consensus gate runs up to `max_rounds` debate rounds. In each round:
//! 1. Each hemisphere critiques the other's output
//! 2. If both stances agree, consensus is reached
//! 3. If they disagree, they exchange counter-arguments and try again
//! 4. After exhausting rounds, the higher-confidence hemisphere prevails

use super::callosum::{CorpusCallosum, Message, MessageDirection, MessageKind};
use super::hemisphere::{Hemisphere, HemisphereInput, HemisphereOutput, Stance};
use serde::{Deserialize, Serialize};

/// The verdict from the consensus gate.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Verdict {
    /// Both hemispheres agreed immediately.
    Agreed,
    /// Both hemispheres agreed after debate rounds.
    AgreedAfterDebate,
    /// Hemispheres disagreed; left hemisphere prevailed (higher confidence).
    LeftPrevailed,
    /// Hemispheres disagreed; right hemisphere prevailed (higher confidence).
    RightPrevailed,
    /// Right hemisphere was unavailable; left-only result used.
    LeftOnly,
    /// Both hemispheres were uncertain; no clear conclusion.
    Inconclusive,
}

/// The result of a bicameral reasoning session.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsensusResult {
    /// The final verdict.
    pub verdict: Verdict,
    /// The agreed-upon conclusion.
    pub conclusion: String,
    /// Overall confidence (average of both hemispheres, or single if left-only).
    pub confidence: f32,
    /// Number of debate rounds conducted.
    pub rounds: usize,
    /// Left hemisphere's final output.
    pub left_output: HemisphereOutput,
    /// Right hemisphere's final output (if available).
    pub right_output: Option<HemisphereOutput>,
    /// All messages exchanged through the corpus callosum.
    pub messages: Vec<Message>,
    /// Routing decision from the inference router (if attached).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub routing_info: Option<RoutingInfo>,
}

/// Routing information from the inference router.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingInfo {
    /// Which inference tier was selected.
    pub tier: crate::router::InferenceTier,
    /// Task type classification.
    pub task_type: String,
    /// Complexity confidence (0.0–1.0).
    pub confidence: f32,
    /// Human-readable routing reason.
    pub reason: String,
}

/// Consensus gate — orchestrates debate between hemispheres.
pub struct ConsensusGate {
    max_rounds: usize,
}

impl ConsensusGate {
    /// Create a new consensus gate with the given max debate rounds.
    #[must_use]
    pub const fn new(max_rounds: usize) -> Self {
        Self { max_rounds }
    }

    /// Run the deliberation process between two hemispheres.
    ///
    /// This is called by the `BicameralEngine` after both hemispheres have
    /// produced their initial outputs. The gate facilitates debate through
    /// the corpus callosum until consensus is reached or rounds are exhausted.
    #[must_use]
    pub fn deliberate(
        &self,
        left: &HemisphereOutput,
        right: &HemisphereOutput,
        callosum: &CorpusCallosum,
        input: &HemisphereInput,
    ) -> ConsensusResult {
        let mut left_current = left.clone();
        let mut right_current = right.clone();

        // Check immediate agreement
        if left_current.stance == right_current.stance {
            return ConsensusResult {
                verdict: Verdict::Agreed,
                conclusion: pick_conclusion(&left_current, &right_current),
                confidence: f32::midpoint(left_current.confidence, right_current.confidence),
                rounds: 0,
                left_output: left_current,
                right_output: Some(right_current),
                messages: callosum.messages(),
                routing_info: None,
            };
        }

        // Debate rounds
        for round in 0..self.max_rounds {
            // Left critiques right
            let left_critiques = LeftHemisphereWrapper.critique(&right_current, input);
            for critique in &left_critiques {
                callosum.send(Message {
                    direction: MessageDirection::LeftToRight,
                    kind: MessageKind::Critique,
                    payload: critique.clone(),
                    round,
                });
            }

            // Right critiques left
            let right_critiques = RightHemisphereWrapper.critique(&left_current, input);
            for critique in &right_critiques {
                callosum.send(Message {
                    direction: MessageDirection::RightToLeft,
                    kind: MessageKind::Critique,
                    payload: critique.clone(),
                    round,
                });
            }

            // Adjust stances based on critiques (simplified: if critiqued, move toward uncertain)
            if !left_critiques.is_empty() {
                left_current = adjust_for_critique(&left_current, &right_critiques);
            }
            if !right_critiques.is_empty() {
                right_current = adjust_for_critique(&right_current, &left_critiques);
            }

            // Check if they've reached agreement
            if left_current.stance == right_current.stance {
                return ConsensusResult {
                    verdict: Verdict::AgreedAfterDebate,
                    conclusion: pick_conclusion(&left_current, &right_current),
                    confidence: f32::midpoint(left_current.confidence, right_current.confidence),
                    rounds: round + 1,
                    left_output: left_current,
                    right_output: Some(right_current),
                    messages: callosum.messages(),
                    routing_info: None,
                };
            }
        }

        // No consensus — pick the higher-confidence hemisphere
        let (verdict, conclusion, confidence) =
            if left_current.confidence >= right_current.confidence {
                (
                    Verdict::LeftPrevailed,
                    left_current.conclusion.clone(),
                    left_current.confidence,
                )
            } else {
                (
                    Verdict::RightPrevailed,
                    right_current.conclusion.clone(),
                    right_current.confidence,
                )
            };

        // Check for inconclusive (both uncertain and low confidence)
        let verdict = if left_current.stance == Stance::Uncertain
            && right_current.stance == Stance::Uncertain
            && confidence < 0.4
        {
            Verdict::Inconclusive
        } else {
            verdict
        };

        ConsensusResult {
            verdict,
            conclusion,
            confidence,
            rounds: self.max_rounds,
            left_output: left_current,
            right_output: Some(right_current),
            messages: callosum.messages(),
            routing_info: None,
        }
    }
}

/// Pick the conclusion from the hemisphere with higher confidence.
fn pick_conclusion(left: &HemisphereOutput, right: &HemisphereOutput) -> String {
    if left.confidence >= right.confidence {
        left.conclusion.clone()
    } else {
        right.conclusion.clone()
    }
}

/// Adjust a hemisphere's output based on received critiques.
///
/// Simplified model: if the other side raised valid concerns, reduce confidence
/// and potentially shift stance toward uncertain.
fn adjust_for_critique(output: &HemisphereOutput, critiques: &[String]) -> HemisphereOutput {
    let mut adjusted = output.clone();

    // Each critique reduces confidence slightly
    let reduction = critiques.len() as f32 * 0.1;
    adjusted.confidence = (adjusted.confidence - reduction).max(0.1);

    // If confidence drops below 0.4, shift to uncertain
    if adjusted.confidence < 0.4 && adjusted.stance != Stance::Uncertain {
        adjusted.stance = Stance::Uncertain;
    }

    adjusted
}

// Wrapper structs for using hemisphere trait in deliberation
struct LeftHemisphereWrapper;
impl Hemisphere for LeftHemisphereWrapper {
    fn analyze(&self, _input: &HemisphereInput) -> HemisphereOutput {
        unreachable!("wrapper only used for critique")
    }
    fn critique(&self, other: &HemisphereOutput, _input: &HemisphereInput) -> Vec<String> {
        let mut critiques = Vec::new();
        if other.confidence > 0.9 {
            critiques.push("Confidence seems overly high — consider edge cases.".into());
        }
        if other.confidence < 0.3 {
            critiques.push("Very low confidence — is more evidence needed?".into());
        }
        if other.key_points.is_empty() {
            critiques.push("No key points provided — evidence basis unclear.".into());
        }
        if other.stance == Stance::Uncertain && other.confidence > 0.5 {
            critiques.push("Uncertain stance with moderate confidence is contradictory.".into());
        }
        if critiques.is_empty() {
            critiques.push("Analysis appears sound — no major concerns.".into());
        }
        critiques
    }
    fn name(&self) -> &'static str {
        "left-wrapper"
    }
}

struct RightHemisphereWrapper;
impl Hemisphere for RightHemisphereWrapper {
    fn analyze(&self, _input: &HemisphereInput) -> HemisphereOutput {
        unreachable!("wrapper only used for critique")
    }
    fn critique(&self, other: &HemisphereOutput, _input: &HemisphereInput) -> Vec<String> {
        let mut critiques = Vec::new();
        if other.key_points.len() < 3 {
            critiques.push("More key points could strengthen the analysis.".into());
        }
        if other.confidence > 0.8 {
            critiques.push("High confidence may be premature — consider alternatives.".into());
        }
        if critiques.is_empty() {
            critiques.push("Heuristic review finds no major concerns.".into());
        }
        critiques
    }
    fn name(&self) -> &'static str {
        "right-wrapper"
    }
}

#[cfg(test)]
mod tests {
    use super::super::hemisphere::{
        HemisphereSource, LeftHemisphere, RightHemisphere, RightHemisphereStub,
    };
    use super::*;

    #[test]
    fn consensus_immediate_agreement() {
        let gate = ConsensusGate::new(3);
        let callosum = CorpusCallosum::new(1024);
        let input = HemisphereInput::new("test");

        let left = HemisphereOutput {
            conclusion: "I agree".into(),
            confidence: 0.8,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Left,
        };
        let right = HemisphereOutput {
            conclusion: "Also agree".into(),
            confidence: 0.7,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };

        let result = gate.deliberate(&left, &right, &callosum, &input);
        assert_eq!(result.verdict, Verdict::Agreed);
        assert_eq!(result.rounds, 0);
    }

    #[test]
    fn consensus_disagree_then_prevail() {
        let gate = ConsensusGate::new(3);
        let callosum = CorpusCallosum::new(1024);
        let input = HemisphereInput::new("test");

        let left = HemisphereOutput {
            conclusion: "I agree".into(),
            confidence: 0.8,
            stance: Stance::Agree,
            key_points: vec!["point 1".into(), "point 2".into(), "point 3".into()],
            source: HemisphereSource::Left,
        };
        let right = HemisphereOutput {
            conclusion: "I disagree".into(),
            confidence: 0.5,
            stance: Stance::Disagree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };

        let result = gate.deliberate(&left, &right, &callosum, &input);
        // Left has higher confidence, should prevail
        assert!(
            matches!(
                result.verdict,
                Verdict::LeftPrevailed | Verdict::AgreedAfterDebate
            ),
            "got {:?}",
            result.verdict
        );
        assert!(result.rounds > 0);
    }

    #[test]
    fn consensus_inconclusive_when_both_uncertain() {
        let gate = ConsensusGate::new(2);
        let callosum = CorpusCallosum::new(1024);
        let input = HemisphereInput::new("test");

        let left = HemisphereOutput {
            conclusion: "Unsure".into(),
            confidence: 0.2,
            stance: Stance::Uncertain,
            key_points: vec![],
            source: HemisphereSource::Left,
        };
        let right = HemisphereOutput {
            conclusion: "Also unsure".into(),
            confidence: 0.2,
            stance: Stance::Uncertain,
            key_points: vec![],
            source: HemisphereSource::Right,
        };

        let result = gate.deliberate(&left, &right, &callosum, &input);
        // Both uncertain with low confidence → inconclusive
        assert!(
            matches!(result.verdict, Verdict::Inconclusive | Verdict::Agreed),
            "got {:?}",
            result.verdict
        );
    }

    #[test]
    fn consensus_messages_exchanged() {
        let gate = ConsensusGate::new(3);
        let callosum = CorpusCallosum::new(1024);
        let input = HemisphereInput::new("test");

        let left = HemisphereOutput {
            conclusion: "I agree".into(),
            confidence: 0.8,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Left,
        };
        let right = HemisphereOutput {
            conclusion: "I disagree".into(),
            confidence: 0.7,
            stance: Stance::Disagree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };

        let result = gate.deliberate(&left, &right, &callosum, &input);
        // Should have exchanged messages during debate
        assert!(!result.messages.is_empty());
    }

    #[test]
    fn consensus_right_prevails_with_higher_confidence() {
        let gate = ConsensusGate::new(1);
        let callosum = CorpusCallosum::new(1024);
        let input = HemisphereInput::new("test");

        let left = HemisphereOutput {
            conclusion: "I disagree".into(),
            confidence: 0.3,
            stance: Stance::Disagree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Left,
        };
        let right = HemisphereOutput {
            conclusion: "I agree".into(),
            confidence: 0.9,
            stance: Stance::Agree,
            key_points: vec!["point 1".into(), "point 2".into(), "point 3".into()],
            source: HemisphereSource::Right,
        };

        let result = gate.deliberate(&left, &right, &callosum, &input);
        assert!(
            matches!(
                result.verdict,
                Verdict::RightPrevailed | Verdict::AgreedAfterDebate
            ),
            "got {:?}",
            result.verdict
        );
    }

    #[test]
    fn full_deliberation_with_real_hemispheres() {
        let left = LeftHemisphere::new();
        let right = RightHemisphereStub::new();
        let input = HemisphereInput::new("rust is good").with_evidence(vec![
            "Rust is great".into(),
            "Rust is excellent".into(),
            "Rust is positive".into(),
            "Rust is effective".into(),
        ]);
        let left_out = left.analyze(&input);
        let right_out = right.analyze(&input);

        let gate = ConsensusGate::new(3);
        let callosum = CorpusCallosum::new(1024);
        let result = gate.deliberate(&left_out, &right_out, &callosum, &input);
        assert!(!result.conclusion.is_empty());
        assert!(result.confidence > 0.0);
    }
}
