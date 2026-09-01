//! Drive bias — how drives influence tool selection.
//!
//! The drive bias converts drive state into weights that can influence
//! which tools are preferred. High curiosity → exploration tools,
//! high caution → conservative/read-only tools, low energy → lightweight tools.

use super::drive_state::DriveState;
use serde::{Deserialize, Serialize};

/// Bias weights derived from drive state.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct DriveBias {
    /// Weight for exploration tools (search, think, bicameral).
    pub exploration_weight: f32,
    /// Weight for conservative tools (read, gnosis, snapshot).
    pub conservative_weight: f32,
    /// Weight for lightweight tools (fast, low-resource).
    pub lightweight_weight: f32,
    /// Weight for social/communication tools.
    pub social_weight: f32,
    /// Overall confidence in tool selection (0.0 = uncertain, 1.0 = confident).
    pub confidence: f32,
}

impl DriveBias {
    /// Compute bias weights from drive state.
    #[must_use]
    pub fn from_state(state: &DriveState) -> Self {
        // Curiosity drives exploration
        let exploration_weight = state.curiosity;

        // Caution drives conservative behavior
        let conservative_weight = state.caution;

        // Low energy → prefer lightweight tools
        let lightweight_weight = 1.0 - state.energy;

        // Social drive → social tools
        let social_weight = state.social;

        // Confidence: high satisfaction + high energy → high confidence
        // Low satisfaction + low energy → low confidence
        let confidence = f32::midpoint(state.satisfaction, state.energy);

        Self {
            exploration_weight,
            conservative_weight,
            lightweight_weight,
            social_weight,
            confidence,
        }
    }

    /// Get the bias weight for a tool category.
    #[must_use]
    pub const fn weight(&self, category: ToolCategory) -> f32 {
        match category {
            ToolCategory::Exploration => self.exploration_weight,
            ToolCategory::Conservative => self.conservative_weight,
            ToolCategory::Lightweight => self.lightweight_weight,
            ToolCategory::Social => self.social_weight,
        }
    }

    /// Get the dominant bias category.
    #[must_use]
    pub fn dominant_category(&self) -> ToolCategory {
        let mut best = ToolCategory::Exploration;
        let mut max = self.exploration_weight;
        if self.conservative_weight > max {
            max = self.conservative_weight;
            best = ToolCategory::Conservative;
        }
        if self.lightweight_weight > max {
            max = self.lightweight_weight;
            best = ToolCategory::Lightweight;
        }
        if self.social_weight > max {
            best = ToolCategory::Social;
        }
        best
    }
}

/// Categories of tools for bias weighting.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ToolCategory {
    /// Exploration tools: search, think, bicameral, research.
    Exploration,
    /// Conservative tools: read, gnosis, snapshot, status.
    Conservative,
    /// Lightweight tools: fast, low-resource operations.
    Lightweight,
    /// Social/communication tools: publish, broadcast, agent.
    Social,
}

/// Per-tool bias — a specific tool's bias weighting.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolBias {
    /// Tool name.
    pub tool_name: String,
    /// Tool category.
    pub category: ToolCategory,
    /// Base weight (from NLU or other sources).
    pub base_weight: f32,
    /// Drive-adjusted weight.
    pub adjusted_weight: f32,
}

/// Configuration for drive bias computation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BiasConfig {
    /// How much drives influence tool selection (0.0 = no influence, 1.0 = full).
    pub influence_strength: f32,
    /// Minimum weight floor (so tools aren't completely excluded).
    pub min_weight: f32,
}

impl Default for BiasConfig {
    fn default() -> Self {
        Self {
            influence_strength: 0.3,
            min_weight: 0.1,
        }
    }
}

impl BiasConfig {
    /// Apply drive bias to a base tool weight.
    #[must_use]
    pub fn apply_bias(&self, base_weight: f32, bias: &DriveBias, category: ToolCategory) -> f32 {
        let drive_weight = bias.weight(category);
        let adjusted = base_weight.mul_add(
            1.0 - self.influence_strength,
            drive_weight * self.influence_strength,
        );
        adjusted.max(self.min_weight)
    }
}

#[cfg(test)]
mod tests {
    use super::super::drive_state::{BASELINE, DriveState};
    use super::*;

    #[test]
    fn bias_from_neutral_state() {
        let state = DriveState::with_baseline(BASELINE);
        let bias = DriveBias::from_state(&state);
        // Curiosity baseline 0.5 → exploration 0.5
        assert!((bias.exploration_weight - 0.5).abs() < 0.01);
        // Caution baseline 0.3 → conservative 0.3
        assert!((bias.conservative_weight - 0.3).abs() < 0.01);
    }

    #[test]
    fn bias_from_high_curiosity() {
        let state = DriveState {
            curiosity: 0.9,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.4,
        };
        let bias = DriveBias::from_state(&state);
        assert!(bias.exploration_weight > 0.8);
        assert_eq!(bias.dominant_category(), ToolCategory::Exploration);
    }

    #[test]
    fn bias_from_high_caution() {
        let state = DriveState {
            curiosity: 0.3,
            satisfaction: 0.5,
            caution: 0.9,
            energy: 0.8,
            social: 0.4,
        };
        let bias = DriveBias::from_state(&state);
        assert!(bias.conservative_weight > 0.8);
        assert_eq!(bias.dominant_category(), ToolCategory::Conservative);
    }

    #[test]
    fn bias_from_low_energy() {
        let state = DriveState {
            curiosity: 0.3,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.1,
            social: 0.4,
        };
        let bias = DriveBias::from_state(&state);
        assert!(bias.lightweight_weight > 0.8);
        assert_eq!(bias.dominant_category(), ToolCategory::Lightweight);
    }

    #[test]
    fn bias_from_high_social() {
        let state = DriveState {
            curiosity: 0.3,
            satisfaction: 0.5,
            caution: 0.3,
            energy: 0.8,
            social: 0.9,
        };
        let bias = DriveBias::from_state(&state);
        assert!(bias.social_weight > 0.8);
        assert_eq!(bias.dominant_category(), ToolCategory::Social);
    }

    #[test]
    fn bias_confidence_from_satisfaction_and_energy() {
        let state = DriveState {
            curiosity: 0.5,
            satisfaction: 0.9,
            caution: 0.3,
            energy: 0.9,
            social: 0.4,
        };
        let bias = DriveBias::from_state(&state);
        assert!((bias.confidence - 0.9).abs() < 0.01);
    }

    #[test]
    fn bias_weight_by_category() {
        let bias = DriveBias {
            exploration_weight: 0.6,
            conservative_weight: 0.3,
            lightweight_weight: 0.2,
            social_weight: 0.4,
            confidence: 0.5,
        };
        assert!((bias.weight(ToolCategory::Exploration) - 0.6).abs() < 0.001);
        assert!((bias.weight(ToolCategory::Conservative) - 0.3).abs() < 0.001);
        assert!((bias.weight(ToolCategory::Lightweight) - 0.2).abs() < 0.001);
        assert!((bias.weight(ToolCategory::Social) - 0.4).abs() < 0.001);
    }

    #[test]
    fn bias_config_apply() {
        let config = BiasConfig::default();
        let bias = DriveBias {
            exploration_weight: 0.8,
            conservative_weight: 0.2,
            lightweight_weight: 0.3,
            social_weight: 0.4,
            confidence: 0.6,
        };
        let adjusted = config.apply_bias(0.5, &bias, ToolCategory::Exploration);
        // 0.5 * 0.7 + 0.8 * 0.3 = 0.35 + 0.24 = 0.59
        assert!((adjusted - 0.59).abs() < 0.01);
    }

    #[test]
    fn bias_config_respects_min_weight() {
        let config = BiasConfig {
            influence_strength: 1.0,
            min_weight: 0.3,
        };
        let bias = DriveBias {
            exploration_weight: 0.0,
            conservative_weight: 0.0,
            lightweight_weight: 0.0,
            social_weight: 0.0,
            confidence: 0.0,
        };
        let adjusted = config.apply_bias(0.5, &bias, ToolCategory::Exploration);
        assert!(adjusted >= 0.3);
    }
}
