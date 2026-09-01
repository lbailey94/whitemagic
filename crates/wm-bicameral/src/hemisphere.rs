//! Hemispheres — left (deterministic) and right (pluggable inference).

use serde::{Deserialize, Serialize};

/// Input to a hemisphere analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HemisphereInput {
    /// The topic or question to reason about.
    pub topic: String,
    /// Optional supporting evidence (e.g., memory entries).
    pub evidence: Vec<String>,
    /// Optional context (galaxy, session, etc.).
    pub context: serde_json::Value,
}

impl HemisphereInput {
    /// Create a new input with just a topic.
    #[must_use]
    pub fn new(topic: impl Into<String>) -> Self {
        Self {
            topic: topic.into(),
            evidence: Vec::new(),
            context: serde_json::Value::Null,
        }
    }

    /// Add evidence to the input.
    #[must_use]
    pub fn with_evidence(mut self, evidence: Vec<String>) -> Self {
        self.evidence = evidence;
        self
    }

    /// Add context to the input.
    #[must_use]
    pub fn with_context(mut self, context: serde_json::Value) -> Self {
        self.context = context;
        self
    }
}

/// Output from a hemisphere analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HemisphereOutput {
    /// The hemisphere's conclusion.
    pub conclusion: String,
    /// Confidence in the conclusion (0.0–1.0).
    pub confidence: f32,
    /// Stance: agree, disagree, or uncertain.
    pub stance: Stance,
    /// Key points supporting the conclusion.
    pub key_points: Vec<String>,
    /// Which hemisphere produced this output.
    pub source: HemisphereSource,
}

/// The stance a hemisphere takes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Stance {
    /// Agrees with the proposition.
    Agree,
    /// Disagrees with the proposition.
    Disagree,
    /// Uncertain — needs more information.
    Uncertain,
}

/// Which hemisphere produced an output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HemisphereSource {
    /// Left hemisphere (deterministic Rust).
    Left,
    /// Right hemisphere (pluggable inference).
    Right,
}

/// Trait for a hemisphere's analysis capability.
pub trait Hemisphere: Send + Sync {
    /// Analyze the given input and produce a conclusion.
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput;

    /// Critique another hemisphere's output.
    /// Returns points of disagreement or concerns.
    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String>;

    /// Name of this hemisphere (for logging).
    fn name(&self) -> &'static str;
}

/// Left hemisphere — deterministic Rust logic.
///
/// Performs evidence-based analysis: counts supporting vs opposing evidence,
/// identifies key themes, and produces a structured conclusion.
pub struct LeftHemisphere {
    support_markers: &'static [&'static str],
    opposition_markers: &'static [&'static str],
}

impl LeftHemisphere {
    /// Create a new left hemisphere with default markers.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            support_markers: &[
                "good",
                "great",
                "excellent",
                "pro",
                "positive",
                "benefit",
                "advantage",
                "support",
                "agree",
                "correct",
                "effective",
                "success",
                "strong",
            ],
            opposition_markers: &[
                "however",
                "but",
                "against",
                "con",
                "negative",
                "problem",
                "issue",
                "criticism",
                "drawback",
                "limitation",
                "fail",
                "wrong",
                "disagree",
            ],
        }
    }

    fn classify_evidence<'a>(
        &self,
        evidence: &'a [String],
    ) -> (Vec<&'a str>, Vec<&'a str>, Vec<&'a str>) {
        let mut supporting: Vec<&'a str> = Vec::new();
        let mut opposing: Vec<&'a str> = Vec::new();
        let mut neutral: Vec<&'a str> = Vec::new();

        for item in evidence {
            let lower = item.to_lowercase();
            let has_support = self.support_markers.iter().any(|m| lower.contains(m));
            let has_oppose = self.opposition_markers.iter().any(|m| lower.contains(m));

            if has_support && !has_oppose {
                supporting.push(item.as_str());
            } else if has_oppose && !has_support {
                opposing.push(item.as_str());
            } else {
                neutral.push(item.as_str());
            }
        }

        (supporting, opposing, neutral)
    }
}

impl Default for LeftHemisphere {
    fn default() -> Self {
        Self::new()
    }
}

impl Hemisphere for LeftHemisphere {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        let (supporting, opposing, neutral) = self.classify_evidence(&input.evidence);
        let total = supporting.len() + opposing.len() + neutral.len();

        let (conclusion, confidence, stance) = if total == 0 {
            (
                format!(
                    "No evidence available for '{}'. Further investigation needed.",
                    input.topic
                ),
                0.2,
                Stance::Uncertain,
            )
        } else if supporting.len() > opposing.len() * 2 {
            (
                format!(
                    "Evidence strongly supports '{}': {} supporting vs {} opposing.",
                    input.topic,
                    supporting.len(),
                    opposing.len()
                ),
                0.8,
                Stance::Agree,
            )
        } else if opposing.len() > supporting.len() * 2 {
            (
                format!(
                    "Evidence predominantly opposes '{}': {} opposing vs {} supporting.",
                    input.topic,
                    opposing.len(),
                    supporting.len()
                ),
                0.8,
                Stance::Disagree,
            )
        } else {
            (
                format!(
                    "Evidence on '{}' is balanced: {} supporting, {} opposing, {} neutral.",
                    input.topic,
                    supporting.len(),
                    opposing.len(),
                    neutral.len()
                ),
                0.4,
                Stance::Uncertain,
            )
        };

        let key_points: Vec<String> = supporting
            .iter()
            .chain(opposing.iter())
            .take(5)
            .map(std::string::ToString::to_string)
            .collect();

        HemisphereOutput {
            conclusion,
            confidence,
            stance,
            key_points,
            source: HemisphereSource::Left,
        }
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
        "left"
    }
}

/// Right hemisphere — pluggable inference engine.
///
/// This trait allows different backends: LLM via MCP client, embedded model,
/// or heuristic stub. The right hemisphere provides an alternative perspective
/// to the left's deterministic analysis.
pub trait RightHemisphere: Send + Sync {
    /// Analyze the given input and produce a conclusion.
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput;

    /// Critique another hemisphere's output.
    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String>;

    /// Name of this right hemisphere backend.
    fn backend_name(&self) -> &'static str;
}

type CriticFn = Box<dyn Fn(&HemisphereOutput, &HemisphereInput) -> Vec<String> + Send + Sync>;

/// A function-based right hemisphere — allows wrapping a closure.
pub struct RightHemisphereFn {
    analyzer: Box<dyn Fn(&HemisphereInput) -> HemisphereOutput + Send + Sync>,
    critic: CriticFn,
    name: &'static str,
}

impl RightHemisphereFn {
    /// Create a new function-based right hemisphere.
    #[must_use]
    pub fn new(
        analyzer: impl Fn(&HemisphereInput) -> HemisphereOutput + Send + Sync + 'static,
        critic: impl Fn(&HemisphereOutput, &HemisphereInput) -> Vec<String> + Send + Sync + 'static,
        name: &'static str,
    ) -> Self {
        Self {
            analyzer: Box::new(analyzer),
            critic: Box::new(critic),
            name,
        }
    }
}

impl RightHemisphere for RightHemisphereFn {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        (self.analyzer)(input)
    }

    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String> {
        (self.critic)(other, input)
    }

    fn backend_name(&self) -> &'static str {
        self.name
    }
}

/// Stub right hemisphere — heuristic analysis without external dependencies.
///
/// Provides a second perspective using different heuristics than the left
/// hemisphere: looks at evidence length, keyword diversity, and topic complexity.
pub struct RightHemisphereStub {
    complexity_markers: &'static [&'static str],
}

impl RightHemisphereStub {
    /// Create a new stub right hemisphere.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            complexity_markers: &[
                "complex",
                "nuanced",
                "tradeoff",
                "trade-off",
                "multi",
                "interdisciplinary",
                "contextual",
                "conditional",
                "depends",
                "relative",
            ],
        }
    }

    fn estimate_complexity(&self, topic: &str) -> f32 {
        let lower = topic.to_lowercase();
        let marker_count = self
            .complexity_markers
            .iter()
            .filter(|m| lower.contains(*m))
            .count();
        let word_count = topic.split_whitespace().count();
        // More words and complexity markers → higher complexity
        (marker_count as f32)
            .mul_add(0.2, word_count as f32 * 0.05)
            .min(1.0)
    }
}

impl Default for RightHemisphereStub {
    fn default() -> Self {
        Self::new()
    }
}

impl RightHemisphere for RightHemisphereStub {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        let complexity = self.estimate_complexity(&input.topic);
        let evidence_count = input.evidence.len();

        // Heuristic: high complexity with little evidence → uncertain
        // Low complexity with good evidence → confident
        let (stance, confidence) = if complexity > 0.6 && evidence_count < 3 {
            (Stance::Uncertain, 0.3)
        } else if evidence_count == 0 {
            (Stance::Uncertain, 0.2)
        } else if complexity < 0.3 && evidence_count > 5 {
            (Stance::Agree, 0.7)
        } else {
            (Stance::Agree, 0.5)
        };

        let conclusion = format!(
            "Heuristic analysis of '{}' (complexity: {:.1}, evidence: {}): {:?} stance with {:.0}% confidence.",
            input.topic,
            complexity,
            evidence_count,
            stance,
            confidence * 100.0
        );

        let key_points: Vec<String> = input.evidence.iter().rev().take(3).cloned().collect();

        HemisphereOutput {
            conclusion,
            confidence,
            stance,
            key_points,
            source: HemisphereSource::Right,
        }
    }

    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String> {
        let mut critiques = Vec::new();
        let complexity = self.estimate_complexity(&input.topic);

        if complexity > 0.5 && other.stance != Stance::Uncertain {
            critiques.push("Topic appears complex — consider a more nuanced stance.".into());
        }
        if other.key_points.len() < 3 && input.evidence.len() > 5 {
            critiques.push("More key points could strengthen the analysis.".into());
        }
        if other.confidence > 0.8 && complexity > 0.5 {
            critiques.push("High confidence on a complex topic may be premature.".into());
        }

        if critiques.is_empty() {
            critiques.push("Heuristic review finds no major concerns.".into());
        }

        critiques
    }

    fn backend_name(&self) -> &'static str {
        "stub"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn left_hemisphere_classifies_evidence() {
        let left = LeftHemisphere::new();
        let input = HemisphereInput::new("rust").with_evidence(vec![
            "Rust is great for systems".into(),
            "However Rust has steep learning curve".into(),
            "Rust ownership prevents memory leaks".into(),
        ]);
        let output = left.analyze(&input);
        assert!(!output.conclusion.is_empty());
        assert!(output.confidence > 0.0);
        assert!(!output.key_points.is_empty());
    }

    #[test]
    fn left_hemisphere_no_evidence() {
        let left = LeftHemisphere::new();
        let input = HemisphereInput::new("unknown topic");
        let output = left.analyze(&input);
        assert_eq!(output.stance, Stance::Uncertain);
        assert!(output.confidence < 0.5);
    }

    #[test]
    fn left_hemisphere_strong_support() {
        let left = LeftHemisphere::new();
        let input = HemisphereInput::new("rust").with_evidence(vec![
            "Rust is great".into(),
            "Rust is excellent".into(),
            "Rust is positive".into(),
            "Rust is effective".into(),
            "But one minor issue".into(),
        ]);
        let output = left.analyze(&input);
        assert_eq!(output.stance, Stance::Agree);
        assert!(output.confidence > 0.5);
    }

    #[test]
    fn left_hemisphere_strong_opposition() {
        let left = LeftHemisphere::new();
        let input = HemisphereInput::new("rust").with_evidence(vec![
            "Rust is a problem".into(),
            "Rust has issues".into(),
            "Rust is wrong".into(),
            "Rust fails".into(),
            "One good thing about Rust".into(),
        ]);
        let output = left.analyze(&input);
        assert_eq!(output.stance, Stance::Disagree);
        assert!(output.confidence > 0.5);
    }

    #[test]
    fn left_hemisphere_critique() {
        let left = LeftHemisphere::new();
        let input = HemisphereInput::new("test");
        let high_conf = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.95,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };
        let critiques = left.critique(&high_conf, &input);
        assert!(!critiques.is_empty());
    }

    #[test]
    fn stub_right_hemisphere_analyzes() {
        let right = RightHemisphereStub::new();
        let input = HemisphereInput::new("simple topic").with_evidence(vec![
            "evidence 1".into(),
            "evidence 2".into(),
            "evidence 3".into(),
            "evidence 4".into(),
            "evidence 5".into(),
            "evidence 6".into(),
        ]);
        let output = right.analyze(&input);
        assert_eq!(output.source, HemisphereSource::Right);
        assert!(output.confidence > 0.0);
    }

    #[test]
    fn stub_right_hemisphere_complex_topic() {
        let right = RightHemisphereStub::new();
        let input = HemisphereInput::new("complex nuanced tradeoff topic");
        let output = right.analyze(&input);
        assert_eq!(output.stance, Stance::Uncertain);
    }

    #[test]
    fn stub_right_hemisphere_critique() {
        let right = RightHemisphereStub::new();
        let input = HemisphereInput::new("complex nuanced topic");
        let other = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.9,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Left,
        };
        let critiques = right.critique(&other, &input);
        assert!(!critiques.is_empty());
    }

    #[test]
    fn function_based_right_hemisphere() {
        let right = RightHemisphereFn::new(
            |input| HemisphereOutput {
                conclusion: format!("Custom analysis of {}", input.topic),
                confidence: 0.6,
                stance: Stance::Agree,
                key_points: vec!["custom point".into()],
                source: HemisphereSource::Right,
            },
            |_other, _input| vec!["Custom critique".into()],
            "custom",
        );
        let input = HemisphereInput::new("test");
        let output = right.analyze(&input);
        assert!(output.conclusion.contains("Custom analysis"));
        assert_eq!(right.backend_name(), "custom");
    }

    #[test]
    fn hemisphere_input_builder() {
        let input = HemisphereInput::new("test")
            .with_evidence(vec!["evidence".into()])
            .with_context(serde_json::json!({"galaxy": "codex"}));
        assert_eq!(input.topic, "test");
        assert_eq!(input.evidence.len(), 1);
        assert_eq!(input.context["galaxy"], "codex");
    }
}
