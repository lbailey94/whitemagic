//! Wu Xing Engine (五行) — Five Elements cognitive energy system.
//!
//! Models the flow of cognitive energy through five elements:
//! Wood (木), Fire (火), Earth (土), Metal (金), Water (水).
//!
//! Two cycles govern interactions:
//! - **Generating cycle (生)**: Wood → Fire → Earth → Metal → Water → Wood
//! - **Overcoming cycle (克)**: Wood → Earth → Water → Fire → Metal → Wood
//!
//! When an element's energy changes, the generating target gets a small boost
//! and the overcoming target gets a small suppression. This creates dynamic
//! cascades that model cognitive energy flow.
//!
//! Ported from v2 `wu_xing/__init__.py` (529 lines).

use serde::{Deserialize, Serialize};

/// The five elements of Wu Xing.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Element {
    /// 木 — Growth, creativity, beginnings.
    Wood,
    /// 火 — Transformation, passion, illumination.
    Fire,
    /// 土 — Stability, nourishment, grounding.
    Earth,
    /// 金 — Structure, precision, refinement.
    Metal,
    /// 水 — Flow, wisdom, reflection.
    Water,
}

impl Element {
    /// All five elements in canonical (generating cycle) order.
    #[must_use]
    pub const fn all() -> [Self; 5] {
        [
            Self::Wood,
            Self::Fire,
            Self::Earth,
            Self::Metal,
            Self::Water,
        ]
    }

    /// Human-readable name.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Wood => "wood",
            Self::Fire => "fire",
            Self::Earth => "earth",
            Self::Metal => "metal",
            Self::Water => "water",
        }
    }

    /// Chinese character.
    #[must_use]
    pub const fn hanzi(self) -> &'static str {
        match self {
            Self::Wood => "木",
            Self::Fire => "火",
            Self::Earth => "土",
            Self::Metal => "金",
            Self::Water => "水",
        }
    }

    /// Element meaning description.
    #[must_use]
    pub const fn meaning(self) -> &'static str {
        match self {
            Self::Wood => "Growth, expansion, creativity, planning",
            Self::Fire => "Passion, inspiration, rapid action, illumination",
            Self::Earth => "Stability, grounding, nourishment, patience",
            Self::Metal => "Structure, precision, discernment, cutting",
            Self::Water => "Wisdom, depth, flow, introspection, storage",
        }
    }

    /// What this element generates in the generating cycle.
    #[must_use]
    pub const fn generates(self) -> Self {
        match self {
            Self::Wood => Self::Fire,
            Self::Fire => Self::Earth,
            Self::Earth => Self::Metal,
            Self::Metal => Self::Water,
            Self::Water => Self::Wood,
        }
    }

    /// What this element overcomes in the overcoming cycle.
    #[must_use]
    pub const fn overcomes(self) -> Self {
        match self {
            Self::Wood => Self::Earth,
            Self::Earth => Self::Water,
            Self::Water => Self::Fire,
            Self::Fire => Self::Metal,
            Self::Metal => Self::Wood,
        }
    }
}

/// The current state of a single element.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ElementalState {
    /// Which element this is.
    pub element: Element,
    /// Energy level (0.0 to 1.0).
    pub energy: f32,
    /// Quality descriptor based on energy level.
    pub quality: String,
}

impl ElementalState {
    /// Create a new elemental state with auto-determined quality.
    #[must_use]
    pub fn new(element: Element, energy: f32) -> Self {
        Self {
            element,
            energy: energy.clamp(0.0, 1.0),
            quality: WuXingEngine::determine_quality(element, energy),
        }
    }

    /// Create a new elemental state with explicit quality.
    #[must_use]
    pub fn with_quality(element: Element, energy: f32, quality: impl Into<String>) -> Self {
        Self {
            element,
            energy: energy.clamp(0.0, 1.0),
            quality: quality.into(),
        }
    }
}

/// Balance assessment result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BalanceAssessment {
    /// Overall balance score (0.0 = imbalanced, 1.0 = perfectly balanced).
    pub balance: f32,
    /// Harmony score based on proper elemental relationships.
    pub harmony: f32,
    /// Dominant element (highest energy).
    pub dominant: Element,
    /// Deficient element (lowest energy).
    pub deficient: Element,
    /// Whether the system is balanced (balance > 0.8).
    pub is_balanced: bool,
    /// Human-readable recommendation.
    pub recommendation: String,
    /// Current cycle phase description.
    pub cycle_phase: String,
}

/// Situation analysis result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SituationAnalysis {
    /// Primary element detected in the situation.
    pub primary_element: Option<Element>,
    /// Secondary element detected.
    pub secondary_element: Option<Element>,
    /// Scores for each element based on keyword matching.
    pub element_scores: [(Element, usize); 5],
    /// Generated guidance text.
    pub guidance: String,
}

/// Wu Xing Engine — models elemental flows and transformations.
///
/// Understands the generating cycle (生) and overcoming cycle (克),
/// tracks energy levels for all five elements, and provides balance
/// assessment, situation analysis, and rebalancing.
pub struct WuXingEngine {
    /// Current state of each element.
    elements: [ElementalState; 5],
    /// History of energy adjustments.
    cycle_history: Vec<CycleEntry>,
    /// Threshold for considering the system imbalanced.
    #[allow(dead_code)]
    imbalance_threshold: f32,
    /// Threshold for considering the system harmonious.
    harmony_threshold: f32,
}

/// A single entry in the cycle history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CycleEntry {
    /// Which element was adjusted.
    pub element: Element,
    /// Energy change applied.
    pub energy_change: f32,
    /// Energy after adjustment.
    pub new_energy: f32,
}

impl WuXingEngine {
    /// Create a new engine with all elements at balanced (0.5) energy.
    #[must_use]
    pub fn new() -> Self {
        Self {
            elements: [
                ElementalState::new(Element::Wood, 0.5),
                ElementalState::new(Element::Fire, 0.5),
                ElementalState::new(Element::Earth, 0.5),
                ElementalState::new(Element::Metal, 0.5),
                ElementalState::new(Element::Water, 0.5),
            ],
            cycle_history: Vec::new(),
            imbalance_threshold: 0.3,
            harmony_threshold: 0.8,
        }
    }

    /// Get the state of a specific element.
    #[must_use]
    pub const fn get_element(&self, element: Element) -> &ElementalState {
        &self.elements[element as usize]
    }

    /// Get all element states.
    #[must_use]
    pub const fn elements(&self) -> &[ElementalState] {
        &self.elements
    }

    /// Adjust the energy of an element and propagate interactions.
    pub fn adjust_element(&mut self, element: Element, energy_change: f32) {
        self.adjust_with_quality(element, energy_change, None);
    }

    /// Adjust the energy of an element with an optional explicit quality.
    pub fn adjust_with_quality(
        &mut self,
        element: Element,
        energy_change: f32,
        quality: Option<&str>,
    ) {
        let idx = element as usize;
        let current = self.elements[idx].energy;
        let new_energy = (current + energy_change).clamp(0.0, 1.0);

        let q = if let Some(q) = quality {
            q.to_string()
        } else {
            Self::determine_quality(element, new_energy)
        };

        self.elements[idx] = ElementalState {
            element,
            energy: new_energy,
            quality: q,
        };

        // Apply elemental interactions (generating + overcoming)
        self.apply_interactions(element);

        // Record the change
        self.cycle_history.push(CycleEntry {
            element,
            energy_change,
            new_energy,
        });
    }

    /// Nourish an element (increase by 0.1).
    pub fn nourish(&mut self, element: Element) {
        self.adjust_element(element, 0.1);
    }

    /// Drain an element (decrease by 0.1).
    pub fn drain(&mut self, element: Element) {
        self.adjust_element(element, -0.1);
    }

    /// Apply generating and overcoming interactions after an element changes.
    fn apply_interactions(&mut self, changed: Element) {
        let changed_energy = self.elements[changed as usize].energy;

        // Generating cycle: boost the element this one generates
        let gen_target = changed.generates();
        let boost = 0.05 * changed_energy;
        let gen_idx = gen_target as usize;
        let gen_current = self.elements[gen_idx].energy;
        let gen_new = (gen_current + boost).min(1.0);
        self.elements[gen_idx] = ElementalState::new(gen_target, gen_new);

        // Overcoming cycle: suppress the element this one overcomes
        let over_target = changed.overcomes();
        let suppression = 0.03 * changed_energy;
        let over_idx = over_target as usize;
        let over_current = self.elements[over_idx].energy;
        let over_new = (over_current - suppression).max(0.0);
        self.elements[over_idx] = ElementalState::new(over_target, over_new);
    }

    /// Determine quality descriptor based on element and energy level.
    #[must_use]
    pub fn determine_quality(element: Element, energy: f32) -> String {
        if energy < 0.2 {
            match element {
                Element::Wood => "dormant",
                Element::Fire => "ember",
                Element::Earth => "barren",
                Element::Metal => "corroded",
                Element::Water => "stagnant",
            }
        } else if energy < 0.4 {
            match element {
                Element::Wood => "sprouting",
                Element::Fire => "flickering",
                Element::Earth => "fertile",
                Element::Metal => "raw",
                Element::Water => "trickling",
            }
        } else if energy < 0.6 {
            match element {
                Element::Wood => "growing",
                Element::Fire => "burning",
                Element::Earth => "stable",
                Element::Metal => "forging",
                Element::Water => "flowing",
            }
        } else if energy < 0.8 {
            match element {
                Element::Wood => "thriving",
                Element::Fire => "radiant",
                Element::Earth => "nourishing",
                Element::Metal => "polished",
                Element::Water => "streaming",
            }
        } else {
            match element {
                Element::Wood => "blossoming",
                Element::Fire => "blazing",
                Element::Earth => "abundant",
                Element::Metal => "luminous",
                Element::Water => "cascading",
            }
        }
        .to_string()
    }

    /// Calculate overall elemental balance (0.0 to 1.0).
    ///
    /// Based on variance of element energies — high variance = low balance.
    #[must_use]
    pub fn balance_score(&self) -> f32 {
        let energies: [f32; 5] = [
            self.elements[0].energy,
            self.elements[1].energy,
            self.elements[2].energy,
            self.elements[3].energy,
            self.elements[4].energy,
        ];
        let mean = energies.iter().sum::<f32>() / 5.0;
        let variance = energies.iter().map(|e| (e - mean).powi(2)).sum::<f32>() / 5.0;
        (1.0 - variance * 2.0).max(0.0)
    }

    /// Calculate harmony score based on proper elemental relationships.
    ///
    /// Penalizes cases where a generating element is strong but its target
    /// is weak (blocked energy flow).
    #[must_use]
    pub fn harmony_score(&self) -> f32 {
        let mut score = 1.0_f32;
        for element in Element::all() {
            let target = element.generates();
            let source_energy = self.elements[element as usize].energy;
            let target_energy = self.elements[target as usize].energy;
            if source_energy > 0.7 && target_energy < 0.3 {
                score -= 0.2;
            }
        }
        score.max(0.0)
    }

    /// Find the dominant element (highest energy).
    #[must_use]
    pub fn dominant_element(&self) -> Element {
        let mut max_elem = Element::Wood;
        let mut max_energy = self.elements[0].energy;
        for (i, state) in self.elements.iter().enumerate() {
            if state.energy > max_energy {
                max_energy = state.energy;
                max_elem = Element::all()[i];
            }
        }
        max_elem
    }

    /// Find the deficient element (lowest energy).
    #[must_use]
    pub fn deficient_element(&self) -> Element {
        let mut min_elem = Element::Wood;
        let mut min_energy = self.elements[0].energy;
        for (i, state) in self.elements.iter().enumerate() {
            if state.energy < min_energy {
                min_energy = state.energy;
                min_elem = Element::all()[i];
            }
        }
        min_elem
    }

    /// Check if the system is balanced (balance score >= harmony_threshold).
    #[must_use]
    pub fn is_balanced(&self) -> bool {
        self.balance_score() >= self.harmony_threshold
    }

    /// Get a full balance assessment.
    #[must_use]
    pub fn assess_balance(&self) -> BalanceAssessment {
        let dominant = self.dominant_element();
        let deficient = self.deficient_element();
        let balance = self.balance_score();
        let harmony = self.harmony_score();

        BalanceAssessment {
            balance,
            harmony,
            dominant,
            deficient,
            is_balanced: balance >= self.harmony_threshold,
            recommendation: format!(
                "Nourish {} through {} (currently lowest at {:.2})",
                deficient.as_str(),
                deficient.generates().as_str(),
                self.elements[deficient as usize].energy,
            ),
            cycle_phase: self.current_cycle_phase(),
        }
    }

    /// Describe the current elemental cycle phase.
    #[must_use]
    pub fn current_cycle_phase(&self) -> String {
        let dominant = self.dominant_element();
        match dominant {
            Element::Wood => "Wood Phase — Time for growth, creativity, and new beginnings",
            Element::Fire => "Fire Phase — Time for transformation, passion, and illumination",
            Element::Earth => "Earth Phase — Time for stability, nourishment, and grounding",
            Element::Metal => "Metal Phase — Time for structure, precision, and refinement",
            Element::Water => "Water Phase — Time for flow, wisdom, and reflection",
        }
        .to_string()
    }

    /// Attempt to rebalance all elements toward harmony.
    ///
    /// If balance is below the harmony threshold, gently adjusts elements
    /// that are too high or too low toward the center.
    pub fn rebalance(&mut self) {
        let balance = self.balance_score();
        if balance < self.harmony_threshold {
            // Collect adjustments to avoid borrow issues
            let mut adjustments = Vec::new();
            for (i, state) in self.elements.iter().enumerate() {
                if state.energy > 0.6 {
                    adjustments.push((Element::all()[i], -0.1_f32));
                } else if state.energy < 0.4 {
                    adjustments.push((Element::all()[i], 0.1_f32));
                }
            }
            for (element, change) in adjustments {
                self.adjust_with_quality(element, change, Some("balancing"));
            }
        }
    }

    /// Analyze a situation text using Wu Xing keyword matching.
    #[must_use]
    pub fn analyze_situation(&self, situation: &str) -> SituationAnalysis {
        let lower = situation.to_lowercase();
        let keywords: [(Element, &[&str]); 5] = [
            (
                Element::Wood,
                &["grow", "create", "begin", "start", "plant", "green", "life"],
            ),
            (
                Element::Fire,
                &[
                    "transform",
                    "passion",
                    "energy",
                    "light",
                    "heat",
                    "bright",
                    "inspire",
                ],
            ),
            (
                Element::Earth,
                &[
                    "stabilize",
                    "ground",
                    "nourish",
                    "support",
                    "steady",
                    "foundation",
                ],
            ),
            (
                Element::Metal,
                &[
                    "structure",
                    "refine",
                    "precise",
                    "analyze",
                    "organize",
                    "sharp",
                ],
            ),
            (
                Element::Water,
                &["flow", "reflect", "adapt", "wisdom", "deep", "intuitive"],
            ),
        ];

        let mut scores: [(Element, usize); 5] = [(Element::Wood, 0); 5];
        for (i, (element, kws)) in keywords.iter().enumerate() {
            let count = kws.iter().filter(|kw| lower.contains(*kw)).count();
            scores[i] = (*element, count);
        }

        // Sort by score descending (stable sort)
        let mut sorted = scores;
        sorted.sort_by_key(|x| std::cmp::Reverse(x.1));

        let primary = if sorted[0].1 > 0 {
            Some(sorted[0].0)
        } else {
            None
        };
        let secondary = if sorted.len() > 1 && sorted[1].1 > 0 {
            Some(sorted[1].0)
        } else {
            None
        };

        let guidance = self.generate_guidance(primary, secondary);

        SituationAnalysis {
            primary_element: primary,
            secondary_element: secondary,
            element_scores: scores,
            guidance,
        }
    }

    /// Generate guidance text based on primary and secondary elements.
    fn generate_guidance(&self, primary: Option<Element>, secondary: Option<Element>) -> String {
        if primary.is_none() {
            return "No clear elemental alignment detected. Consider the situation from multiple perspectives.".to_string();
        }
        let primary = primary.unwrap();
        let mut parts = Vec::new();

        // Primary element guidance
        let primary_guidance = match primary {
            Element::Wood => {
                "Focus on growth and new beginnings. Nurture creative ideas and allow them to develop naturally."
            }
            Element::Fire => {
                "Embrace transformation and passion. This is a time for dynamic change and inspired action."
            }
            Element::Earth => {
                "Seek stability and grounding. Build solid foundations and nurture yourself and others."
            }
            Element::Metal => {
                "Bring structure and precision. Analyze carefully and refine your approach."
            }
            Element::Water => {
                "Go with the flow and trust your intuition. Allow wisdom to emerge from reflection."
            }
        };
        parts.push(primary_guidance.to_string());

        // Secondary element interaction
        if let Some(sec) = secondary {
            if let Some(interaction) = self.element_interaction(primary, sec) {
                parts.push(interaction);
            }
        }

        // Balance advice
        let current_energy = self.elements[primary as usize].energy;
        if current_energy < 0.3 {
            parts.push(format!(
                "The {} element is weak. Consider activities that strengthen it.",
                primary.as_str()
            ));
        } else if current_energy > 0.8 {
            parts.push(format!(
                "The {} element is very strong. Ensure it doesn't overwhelm other aspects.",
                primary.as_str()
            ));
        }

        parts.join(" ")
    }

    /// Get guidance on the interaction between two elements.
    fn element_interaction(&self, elem1: Element, elem2: Element) -> Option<String> {
        if elem1.generates() == elem2 {
            return Some(format!(
                "The {} element nourishes {}. Allow this natural flow to support your actions.",
                elem1.as_str(),
                elem2.as_str()
            ));
        }
        if elem2.generates() == elem1 {
            return Some(format!(
                "The {} element nourishes {}. Draw on this supportive energy.",
                elem2.as_str(),
                elem1.as_str()
            ));
        }
        if elem1.overcomes() == elem2 {
            return Some(format!(
                "The {} element controls {}. Use this influence wisely and avoid excess.",
                elem1.as_str(),
                elem2.as_str()
            ));
        }
        if elem2.overcomes() == elem1 {
            return Some(format!(
                "The {} element controls {}. Be mindful of constraints and work with them.",
                elem2.as_str(),
                elem1.as_str()
            ));
        }
        None
    }

    /// Get the cycle history.
    #[must_use]
    pub fn cycle_history(&self) -> &[CycleEntry] {
        &self.cycle_history
    }

    /// Get a JSON status summary.
    #[must_use]
    pub fn status(&self) -> serde_json::Value {
        serde_json::json!({
            "elements": self.elements.iter().map(|s| {
                serde_json::json!({
                    "element": s.element.as_str(),
                    "hanzi": s.element.hanzi(),
                    "energy": s.energy,
                    "quality": s.quality,
                })
            }).collect::<Vec<_>>(),
            "balance": self.balance_score(),
            "harmony": self.harmony_score(),
            "dominant": self.dominant_element().as_str(),
            "deficient": self.deficient_element().as_str(),
            "is_balanced": self.is_balanced(),
            "cycle_phase": self.current_cycle_phase(),
            "history_len": self.cycle_history.len(),
        })
    }
}

impl Default for WuXingEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_engine_all_elements_at_half() {
        let engine = WuXingEngine::new();
        for state in engine.elements() {
            assert!((state.energy - 0.5).abs() < 0.01);
            // Quality at 0.5 is in the [0.4, 0.6) range — varies per element
            assert!(!state.quality.is_empty());
        }
    }

    #[test]
    fn element_all_returns_five() {
        assert_eq!(Element::all().len(), 5);
    }

    #[test]
    fn element_generates_cycle() {
        assert_eq!(Element::Wood.generates(), Element::Fire);
        assert_eq!(Element::Fire.generates(), Element::Earth);
        assert_eq!(Element::Earth.generates(), Element::Metal);
        assert_eq!(Element::Metal.generates(), Element::Water);
        assert_eq!(Element::Water.generates(), Element::Wood);
    }

    #[test]
    fn element_overcomes_cycle() {
        assert_eq!(Element::Wood.overcomes(), Element::Earth);
        assert_eq!(Element::Earth.overcomes(), Element::Water);
        assert_eq!(Element::Water.overcomes(), Element::Fire);
        assert_eq!(Element::Fire.overcomes(), Element::Metal);
        assert_eq!(Element::Metal.overcomes(), Element::Wood);
    }

    #[test]
    fn element_as_str() {
        assert_eq!(Element::Wood.as_str(), "wood");
        assert_eq!(Element::Fire.as_str(), "fire");
        assert_eq!(Element::Earth.as_str(), "earth");
        assert_eq!(Element::Metal.as_str(), "metal");
        assert_eq!(Element::Water.as_str(), "water");
    }

    #[test]
    fn element_hanzi() {
        assert_eq!(Element::Wood.hanzi(), "木");
        assert_eq!(Element::Fire.hanzi(), "火");
        assert_eq!(Element::Earth.hanzi(), "土");
        assert_eq!(Element::Metal.hanzi(), "金");
        assert_eq!(Element::Water.hanzi(), "水");
    }

    #[test]
    fn element_meaning() {
        assert!(Element::Wood.meaning().contains("Growth"));
        assert!(Element::Fire.meaning().contains("Passion"));
        assert!(Element::Earth.meaning().contains("Stability"));
        assert!(Element::Metal.meaning().contains("Structure"));
        assert!(Element::Water.meaning().contains("Wisdom"));
    }

    #[test]
    fn adjust_element_changes_energy() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Wood, 0.3);
        assert!(engine.get_element(Element::Wood).energy > 0.5);
    }

    #[test]
    fn adjust_element_clamps_to_one() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Fire, 0.6); // 0.5 + 0.6 = 1.1 → clamped
        assert_eq!(engine.get_element(Element::Fire).energy, 1.0);
    }

    #[test]
    fn adjust_element_clamps_to_zero() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Water, -0.6); // 0.5 - 0.6 = -0.1 → clamped
        assert_eq!(engine.get_element(Element::Water).energy, 0.0);
    }

    #[test]
    fn adjust_element_propagates_generating() {
        let mut engine = WuXingEngine::new();
        let fire_before = engine.get_element(Element::Fire).energy;
        engine.adjust_element(Element::Wood, 0.3);
        // Wood generates Fire — Fire should get a boost
        let fire_after = engine.get_element(Element::Fire).energy;
        assert!(fire_after > fire_before);
    }

    #[test]
    fn adjust_element_propagates_overcoming() {
        let mut engine = WuXingEngine::new();
        let earth_before = engine.get_element(Element::Earth).energy;
        engine.adjust_element(Element::Wood, 0.3);
        // Wood overcomes Earth — Earth should get suppressed
        let earth_after = engine.get_element(Element::Earth).energy;
        assert!(earth_after < earth_before);
    }

    #[test]
    fn nourish_increases_energy() {
        let mut engine = WuXingEngine::new();
        let before = engine.get_element(Element::Metal).energy;
        engine.nourish(Element::Metal);
        assert!(engine.get_element(Element::Metal).energy > before);
    }

    #[test]
    fn drain_decreases_energy() {
        let mut engine = WuXingEngine::new();
        let before = engine.get_element(Element::Earth).energy;
        engine.drain(Element::Earth);
        assert!(engine.get_element(Element::Earth).energy < before);
    }

    #[test]
    fn determine_quality_dormant() {
        assert_eq!(
            WuXingEngine::determine_quality(Element::Wood, 0.1),
            "dormant"
        );
        assert_eq!(
            WuXingEngine::determine_quality(Element::Fire, 0.15),
            "ember"
        );
    }

    #[test]
    fn determine_quality_blossoming() {
        assert_eq!(
            WuXingEngine::determine_quality(Element::Wood, 0.9),
            "blossoming"
        );
        assert_eq!(
            WuXingEngine::determine_quality(Element::Fire, 1.0),
            "blazing"
        );
    }

    #[test]
    fn determine_quality_growing() {
        assert_eq!(
            WuXingEngine::determine_quality(Element::Wood, 0.5),
            "growing"
        );
        assert_eq!(
            WuXingEngine::determine_quality(Element::Water, 0.55),
            "flowing"
        );
    }

    #[test]
    fn balance_score_perfect_when_equal() {
        let engine = WuXingEngine::new();
        // All at 0.5 → variance = 0 → balance = 1.0
        let score = engine.balance_score();
        assert!((score - 1.0).abs() < 0.01);
    }

    #[test]
    fn balance_score_decreases_with_imbalance() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Wood, 0.5);
        engine.adjust_element(Element::Fire, -0.3);
        let score = engine.balance_score();
        assert!(score < 1.0);
    }

    #[test]
    fn harmony_score_decreases_with_blocked_flow() {
        let mut engine = WuXingEngine::new();
        // Make Wood very strong but Fire very weak (blocked generating flow)
        engine.adjust_with_quality(Element::Wood, 0.4, None);
        engine.adjust_with_quality(Element::Fire, -0.3, None);
        let harmony = engine.harmony_score();
        assert!(harmony < 1.0);
    }

    #[test]
    fn dominant_element_finds_highest() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Metal, 0.3);
        assert_eq!(engine.dominant_element(), Element::Metal);
    }

    #[test]
    fn deficient_element_finds_lowest() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Water, -0.2);
        // Water was drained, but overcoming interactions may affect others
        // Just check that Water is among the lowest
        let deficient = engine.deficient_element();
        let water_energy = engine.get_element(Element::Water).energy;
        let deficient_energy = engine.get_element(deficient).energy;
        assert!(deficient_energy <= water_energy);
    }

    #[test]
    fn is_balanced_true_at_start() {
        let engine = WuXingEngine::new();
        assert!(engine.is_balanced());
    }

    #[test]
    fn assess_balance_returns_recommendation() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Water, -0.3);
        let assessment = engine.assess_balance();
        assert!(!assessment.recommendation.is_empty());
        assert!(assessment.recommendation.contains("Nourish"));
    }

    #[test]
    fn current_cycle_phase_returns_description() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Fire, 0.3);
        let phase = engine.current_cycle_phase();
        assert!(phase.contains("Fire Phase"));
    }

    #[test]
    fn rebalance_moves_toward_center() {
        let mut engine = WuXingEngine::new();
        // Create imbalance
        engine.adjust_element(Element::Wood, 0.4);
        engine.adjust_element(Element::Fire, -0.3);
        let balance_before = engine.balance_score();
        engine.rebalance();
        let balance_after = engine.balance_score();
        // Rebalance should improve or maintain balance
        assert!(balance_after >= balance_before - 0.01);
    }

    #[test]
    fn cycle_history_records_adjustments() {
        let mut engine = WuXingEngine::new();
        assert_eq!(engine.cycle_history().len(), 0);
        engine.adjust_element(Element::Wood, 0.1);
        assert_eq!(engine.cycle_history().len(), 1);
        engine.adjust_element(Element::Fire, -0.1);
        assert_eq!(engine.cycle_history().len(), 2);
    }

    #[test]
    fn analyze_situation_detects_wood() {
        let engine = WuXingEngine::new();
        let result = engine.analyze_situation("I want to grow and create something new");
        assert_eq!(result.primary_element, Some(Element::Wood));
        assert!(!result.guidance.is_empty());
    }

    #[test]
    fn analyze_situation_detects_fire() {
        let engine = WuXingEngine::new();
        let result = engine.analyze_situation("Transform with passion and energy");
        assert_eq!(result.primary_element, Some(Element::Fire));
    }

    #[test]
    fn analyze_situation_detects_water() {
        let engine = WuXingEngine::new();
        let result = engine.analyze_situation("Go with the flow and reflect deeply");
        assert_eq!(result.primary_element, Some(Element::Water));
    }

    #[test]
    fn analyze_situation_no_match_returns_none() {
        let engine = WuXingEngine::new();
        let result = engine.analyze_situation("xyz abc def");
        assert_eq!(result.primary_element, None);
        assert!(result.guidance.contains("No clear elemental alignment"));
    }

    #[test]
    fn analyze_situation_with_secondary() {
        let engine = WuXingEngine::new();
        let result = engine.analyze_situation("grow and create with passion and energy");
        assert!(result.primary_element.is_some());
        assert!(result.secondary_element.is_some());
    }

    #[test]
    fn status_returns_json() {
        let engine = WuXingEngine::new();
        let status = engine.status();
        assert!(status["balance"].as_f64().is_some());
        assert!(status["harmony"].as_f64().is_some());
        assert!(status["dominant"].as_str().is_some());
        assert!(status["elements"].is_array());
    }

    #[test]
    fn elemental_state_new_auto_quality() {
        let state = ElementalState::new(Element::Wood, 0.1);
        assert_eq!(state.quality, "dormant");
        let state = ElementalState::new(Element::Fire, 0.95);
        assert_eq!(state.quality, "blazing");
    }

    #[test]
    fn elemental_state_with_quality() {
        let state = ElementalState::with_quality(Element::Earth, 0.5, "custom");
        assert_eq!(state.quality, "custom");
    }

    #[test]
    fn full_generating_cycle_completes() {
        // Wood → Fire → Earth → Metal → Water → Wood
        let mut current = Element::Wood;
        for _ in 0..5 {
            current = current.generates();
        }
        assert_eq!(current, Element::Wood);
    }

    #[test]
    fn full_overcoming_cycle_completes() {
        // Wood → Earth → Water → Fire → Metal → Wood
        let mut current = Element::Wood;
        for _ in 0..5 {
            current = current.overcomes();
        }
        assert_eq!(current, Element::Wood);
    }

    #[test]
    fn adjust_with_quality_override() {
        let mut engine = WuXingEngine::new();
        engine.adjust_with_quality(Element::Wood, 0.3, Some("custom_quality"));
        assert_eq!(engine.get_element(Element::Wood).quality, "custom_quality");
    }

    #[test]
    fn multiple_adjustments_accumulate() {
        let mut engine = WuXingEngine::new();
        engine.adjust_element(Element::Metal, 0.1);
        let after_one = engine.get_element(Element::Metal).energy;
        engine.adjust_element(Element::Metal, 0.1);
        let after_two = engine.get_element(Element::Metal).energy;
        assert!(after_two > after_one);
    }
}
