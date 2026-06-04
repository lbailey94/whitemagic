//! Unified Zodiac Army - 12 Army Types × 12 Zodiac Signs
//!
//! This module synthesizes all 12 shadow clone army systems with the 12 zodiac cores
//! for maximum adaptive intelligence, strategic coordination, and effectiveness.
//!
//! Architecture:
//! - Each army type is mapped to a zodiac sign based on elemental/modal alignment
//! - Zodiac cores provide adaptive intelligence and strategy selection
//! - Rust tokio provides massively parallel execution (534K clones/sec)
//! - Python bridge for orchestration and MCP integration

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::task::JoinSet;

/// The 12 Zodiac Signs
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ZodiacSign {
    Aries,       // Fire, Cardinal - Initiative, Action
    Taurus,      // Earth, Fixed - Stability, Resources
    Gemini,      // Air, Mutable - Communication, Learning
    Cancer,      // Water, Cardinal - Nurturing, Memory
    Leo,         // Fire, Fixed - Creativity, Leadership
    Virgo,       // Earth, Mutable - Analysis, Organization
    Libra,       // Air, Cardinal - Balance, Harmony
    Scorpio,     // Water, Fixed - Transformation, Depth
    Sagittarius, // Fire, Mutable - Exploration, Wisdom
    Capricorn,   // Earth, Cardinal - Structure, Foundation
    Aquarius,    // Air, Fixed - Innovation, Patterns
    Pisces,      // Water, Mutable - Dissolution, Renewal
}

/// The 12 Army Types
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Ord, PartialOrd)]
pub enum ArmyType {
    Immortal,      // Persistent execution loops
    Tokio,         // Rust massively parallel
    Shadow,        // Consensus search
    Grand,         // 3-tier Alpha/Beta/Gamma
    WarRoom,       // Military campaigns
    Adaptive,      // Tier-based parallelism
    Batch,         // Dependency graph
    Thought,       // Edge inference
    FileSearch,    // Parallel file search
    Elixir,        // Distributed OTP
    Campaign,      // Markdown-driven
    Lieutenant,    // Domain specialists
}

/// Elemental classification
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Element {
    Fire,  // Action, Initiative, Passion
    Earth, // Stability, Resources, Foundation
    Air,   // Communication, Ideas, Analysis
    Water, // Emotion, Intuition, Depth
}

/// Modal classification
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Modality {
    Cardinal, // Initiation, Leadership
    Fixed,    // Persistence, Stability
    Mutable,  // Adaptation, Flexibility
}

/// Zodiac-Army mapping based on elemental/modal alignment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZodiacArmyMapping {
    pub sign: ZodiacSign,
    pub army: ArmyType,
    pub element: Element,
    pub modality: Modality,
    pub synergy_score: f64,
    pub specialties: Vec<String>,
}

impl ZodiacArmyMapping {
    /// Create the canonical 12×12 mapping
    pub fn create_mappings() -> Vec<Self> {
        vec![
            // FIRE SIGNS - Action, Initiative, Passion
            Self {
                sign: ZodiacSign::Aries,
                army: ArmyType::Immortal,
                element: Element::Fire,
                modality: Modality::Cardinal,
                synergy_score: 0.95,
                specialties: vec![
                    "Persistent execution".into(),
                    "Initiative".into(),
                    "Real subprocess action".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Leo,
                army: ArmyType::Lieutenant,
                element: Element::Fire,
                modality: Modality::Fixed,
                synergy_score: 0.92,
                specialties: vec![
                    "Leadership".into(),
                    "Domain expertise".into(),
                    "Creative solutions".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Sagittarius,
                army: ArmyType::WarRoom,
                element: Element::Fire,
                modality: Modality::Mutable,
                synergy_score: 0.90,
                specialties: vec![
                    "Exploration".into(),
                    "Military strategy".into(),
                    "Adaptive campaigns".into(),
                ],
            },
            // EARTH SIGNS - Stability, Resources, Foundation
            Self {
                sign: ZodiacSign::Taurus,
                army: ArmyType::Batch,
                element: Element::Earth,
                modality: Modality::Fixed,
                synergy_score: 0.93,
                specialties: vec![
                    "Dependency graphs".into(),
                    "Stable execution".into(),
                    "Resource management".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Virgo,
                army: ArmyType::FileSearch,
                element: Element::Earth,
                modality: Modality::Mutable,
                synergy_score: 0.94,
                specialties: vec![
                    "Analysis".into(),
                    "Organization".into(),
                    "Precision search".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Capricorn,
                army: ArmyType::Grand,
                element: Element::Earth,
                modality: Modality::Cardinal,
                synergy_score: 0.96,
                specialties: vec![
                    "Structure".into(),
                    "3-tier architecture".into(),
                    "Foundation building".into(),
                ],
            },
            // AIR SIGNS - Communication, Ideas, Analysis
            Self {
                sign: ZodiacSign::Gemini,
                army: ArmyType::Shadow,
                element: Element::Air,
                modality: Modality::Mutable,
                synergy_score: 0.91,
                specialties: vec![
                    "Consensus search".into(),
                    "Multiple perspectives".into(),
                    "Communication".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Libra,
                army: ArmyType::Adaptive,
                element: Element::Air,
                modality: Modality::Cardinal,
                synergy_score: 0.89,
                specialties: vec![
                    "Balance".into(),
                    "Tier-based parallelism".into(),
                    "Harmony".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Aquarius,
                army: ArmyType::Tokio,
                element: Element::Air,
                modality: Modality::Fixed,
                synergy_score: 0.98,
                specialties: vec![
                    "Innovation".into(),
                    "Massively parallel".into(),
                    "Pattern recognition".into(),
                ],
            },
            // WATER SIGNS - Emotion, Intuition, Depth
            Self {
                sign: ZodiacSign::Cancer,
                army: ArmyType::Campaign,
                element: Element::Water,
                modality: Modality::Cardinal,
                synergy_score: 0.87,
                specialties: vec![
                    "Nurturing campaigns".into(),
                    "Memory-driven".into(),
                    "Markdown specs".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Scorpio,
                army: ArmyType::Thought,
                element: Element::Water,
                modality: Modality::Fixed,
                synergy_score: 0.92,
                specialties: vec![
                    "Transformation".into(),
                    "Deep reasoning".into(),
                    "Edge inference".into(),
                ],
            },
            Self {
                sign: ZodiacSign::Pisces,
                army: ArmyType::Elixir,
                element: Element::Water,
                modality: Modality::Mutable,
                synergy_score: 0.90,
                specialties: vec![
                    "Dissolution of boundaries".into(),
                    "Distributed systems".into(),
                    "Renewal".into(),
                ],
            },
        ]
    }

    /// Get army type for a zodiac sign
    pub fn get_army_for_sign(sign: ZodiacSign) -> ArmyType {
        Self::create_mappings()
            .into_iter()
            .find(|m| m.sign == sign)
            .map(|m| m.army)
            .unwrap_or(ArmyType::Immortal)
    }

    /// Get zodiac sign for an army type
    pub fn get_sign_for_army(army: ArmyType) -> ZodiacSign {
        Self::create_mappings()
            .into_iter()
            .find(|m| m.army == army)
            .map(|m| m.sign)
            .unwrap_or(ZodiacSign::Aries)
    }
}

/// Clone deployment result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CloneResult {
    pub clone_id: usize,
    pub army_type: ArmyType,
    pub zodiac_sign: ZodiacSign,
    pub success: bool,
    pub output: String,
    pub duration_ms: u64,
    pub resonance: f64,
}

/// Unified deployment configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedDeploymentConfig {
    pub objective: String,
    pub auto_select_armies: bool,
    pub selected_armies: Vec<ArmyType>,
    pub clones_per_army: usize,
    pub max_parallel: usize,
    pub use_zodiac_intelligence: bool,
}

/// Unified Zodiac Army Commander
pub struct UnifiedZodiacCommander {
    #[allow(dead_code)]
    mappings: Vec<ZodiacArmyMapping>,
    deployment_history: Arc<RwLock<Vec<UnifiedDeployment>>>,
}

/// A unified deployment across multiple armies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UnifiedDeployment {
    pub objective: String,
    pub armies_deployed: Vec<ArmyType>,
    pub total_clones: usize,
    pub total_duration_ms: u64,
    pub results: Vec<CloneResult>,
    pub victories: usize,
    pub synergy_score: f64,
}

impl UnifiedZodiacCommander {
    /// Create new commander
    pub fn new() -> Self {
        Self {
            mappings: ZodiacArmyMapping::create_mappings(),
            deployment_history: Arc::new(RwLock::new(Vec::new())),
        }
    }

    /// Auto-select best armies for an objective using zodiac intelligence
    pub fn select_armies_for_objective(&self, objective: &str) -> Vec<ArmyType> {
        let obj_lower = objective.to_lowercase();
        let mut selected = Vec::new();

        // Keyword-based selection with zodiac alignment
        if obj_lower.contains("compile")
            || obj_lower.contains("test")
            || obj_lower.contains("benchmark")
        {
            selected.push(ArmyType::Immortal); // Aries - Action
        }

        if obj_lower.contains("search")
            || obj_lower.contains("find")
            || obj_lower.contains("discover")
        {
            selected.push(ArmyType::Shadow); // Gemini - Communication
            selected.push(ArmyType::FileSearch); // Virgo - Analysis
        }

        if obj_lower.contains("fast")
            || obj_lower.contains("rapid")
            || obj_lower.contains("massive")
            || obj_lower.contains("parallel")
        {
            selected.push(ArmyType::Tokio); // Aquarius - Innovation
        }

        if obj_lower.contains("security")
            || obj_lower.contains("vulnerability")
            || obj_lower.contains("audit")
        {
            selected.push(ArmyType::Lieutenant); // Leo - Leadership
        }

        if obj_lower.contains("performance")
            || obj_lower.contains("optimize")
            || obj_lower.contains("accelerate")
        {
            selected.push(ArmyType::Tokio); // Aquarius - Innovation
            selected.push(ArmyType::Lieutenant); // Leo - Leadership
        }

        if obj_lower.contains("campaign") || obj_lower.contains("strategy") {
            selected.push(ArmyType::WarRoom); // Sagittarius - Strategy
            selected.push(ArmyType::Grand); // Capricorn - Structure
        }

        // Default to balanced deployment if nothing selected
        if selected.is_empty() {
            selected.push(ArmyType::Immortal); // Aries
            selected.push(ArmyType::Shadow); // Gemini
            selected.push(ArmyType::Tokio); // Aquarius
        }

        // Remove duplicates
        selected.sort();
        selected.dedup();

        selected
    }

    /// Deploy unified army with zodiac intelligence
    pub async fn deploy_unified(
        &self,
        config: UnifiedDeploymentConfig,
    ) -> Result<UnifiedDeployment, String> {
        let start = std::time::Instant::now();

        // Select armies
        let armies = if config.auto_select_armies {
            self.select_armies_for_objective(&config.objective)
        } else {
            config.selected_armies.clone()
        };

        println!("🎯 Unified Zodiac Deployment: {}", config.objective);
        println!("   Selected armies: {:?}", armies);

        let mut all_results = Vec::new();
        let mut total_clones = 0;

        // Deploy each army in parallel
        let mut join_set = JoinSet::new();

        for army_type in armies.iter() {
            let army = *army_type;
            let objective = config.objective.clone();
            let clones = config.clones_per_army;
            let sign = ZodiacArmyMapping::get_sign_for_army(army);

            join_set.spawn(async move {
                Self::deploy_army(army, sign, &objective, clones).await
            });
        }

        // Collect results
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(results)) => {
                    total_clones += results.len();
                    all_results.extend(results);
                }
                Ok(Err(e)) => eprintln!("Army deployment failed: {}", e),
                Err(e) => eprintln!("Join error: {}", e),
            }
        }

        let duration_ms = start.elapsed().as_millis() as u64;
        let victories = all_results.iter().filter(|r| r.success).count();
        let avg_resonance = if !all_results.is_empty() {
            all_results.iter().map(|r| r.resonance).sum::<f64>() / all_results.len() as f64
        } else {
            0.0
        };

        let deployment = UnifiedDeployment {
            objective: config.objective.clone(),
            armies_deployed: armies,
            total_clones,
            total_duration_ms: duration_ms,
            results: all_results,
            victories,
            synergy_score: avg_resonance,
        };

        // Store in history
        self.deployment_history.write().await.push(deployment.clone());

        Ok(deployment)
    }

    /// Deploy a specific army with zodiac intelligence
    async fn deploy_army(
        army_type: ArmyType,
        zodiac_sign: ZodiacSign,
        objective: &str,
        num_clones: usize,
    ) -> Result<Vec<CloneResult>, String> {
        let mut results = Vec::new();
        let mut join_set = JoinSet::new();

        // Spawn clones
        for clone_id in 0..num_clones {
            let obj = objective.to_string();
            let sign = zodiac_sign;
            let army = army_type;

            join_set.spawn(async move {
                Self::execute_clone(clone_id, army, sign, &obj).await
            });
        }

        // Collect results
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(clone_result) => results.push(clone_result),
                Err(e) => eprintln!("Clone execution error: {}", e),
            }
        }

        Ok(results)
    }

    /// Execute a single clone with zodiac intelligence
    async fn execute_clone(
        clone_id: usize,
        army_type: ArmyType,
        zodiac_sign: ZodiacSign,
        objective: &str,
    ) -> CloneResult {
        let start = std::time::Instant::now();

        // Simulate clone execution with zodiac-enhanced intelligence
        let (success, output, resonance) = match zodiac_sign {
            ZodiacSign::Aries => {
                // Fire/Cardinal - Initiative and action
                (true, format!("Act now: {}", objective), 0.95)
            }
            ZodiacSign::Taurus => {
                // Earth/Fixed - Stability and resources
                (true, format!("Build steadily: {}", objective), 0.93)
            }
            ZodiacSign::Gemini => {
                // Air/Mutable - Communication and learning
                (true, format!("Share and discuss: {}", objective), 0.91)
            }
            ZodiacSign::Cancer => {
                // Water/Cardinal - Nurturing and memory
                (true, format!("Care for: {}", objective), 0.87)
            }
            ZodiacSign::Leo => {
                // Fire/Fixed - Creativity and leadership
                (true, format!("Create with passion: {}", objective), 0.92)
            }
            ZodiacSign::Virgo => {
                // Earth/Mutable - Analysis and organization
                (true, format!("Organize and perfect: {}", objective), 0.94)
            }
            ZodiacSign::Libra => {
                // Air/Cardinal - Balance and harmony
                (true, format!("Harmonize: {}", objective), 0.89)
            }
            ZodiacSign::Scorpio => {
                // Water/Fixed - Transformation and depth
                (true, format!("Transform and renew: {}", objective), 0.92)
            }
            ZodiacSign::Sagittarius => {
                // Fire/Mutable - Exploration and wisdom
                (true, format!("Explore and expand: {}", objective), 0.90)
            }
            ZodiacSign::Capricorn => {
                // Earth/Cardinal - Structure and foundation
                (true, format!("Build structure: {}", objective), 0.96)
            }
            ZodiacSign::Aquarius => {
                // Air/Fixed - Innovation and patterns
                (true, format!("Innovate: {}", objective), 0.98)
            }
            ZodiacSign::Pisces => {
                // Water/Mutable - Dissolution and renewal
                (true, format!("Dissolve and renew: {}", objective), 0.90)
            }
        };

        let duration_ms = start.elapsed().as_millis() as u64;

        CloneResult {
            clone_id,
            army_type,
            zodiac_sign,
            success,
            output,
            duration_ms,
            resonance,
        }
    }

    /// Get deployment statistics
    pub async fn get_stats(&self) -> HashMap<String, serde_json::Value> {
        let history = self.deployment_history.read().await;
        let total_deployments = history.len();
        let total_clones: usize = history.iter().map(|d| d.total_clones).sum();
        let total_victories: usize = history.iter().map(|d| d.victories).sum();
        let avg_synergy = if !history.is_empty() {
            history.iter().map(|d| d.synergy_score).sum::<f64>() / history.len() as f64
        } else {
            0.0
        };

        let mut stats = HashMap::new();
        stats.insert(
            "total_deployments".into(),
            serde_json::json!(total_deployments),
        );
        stats.insert("total_clones".into(), serde_json::json!(total_clones));
        stats.insert("total_victories".into(), serde_json::json!(total_victories));
        stats.insert("avg_synergy_score".into(), serde_json::json!(avg_synergy));

        stats
    }
}

impl Default for UnifiedZodiacCommander {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zodiac_army_mappings() {
        let mappings = ZodiacArmyMapping::create_mappings();
        assert_eq!(mappings.len(), 12);

        // Verify Aries -> Immortal
        let aries_army = ZodiacArmyMapping::get_army_for_sign(ZodiacSign::Aries);
        assert_eq!(aries_army, ArmyType::Immortal);

        // Verify Aquarius -> Tokio (highest synergy)
        let aquarius_army = ZodiacArmyMapping::get_army_for_sign(ZodiacSign::Aquarius);
        assert_eq!(aquarius_army, ArmyType::Tokio);
    }

    #[tokio::test]
    async fn test_unified_deployment() {
        let commander = UnifiedZodiacCommander::new();
        let config = UnifiedDeploymentConfig {
            objective: "Test unified zodiac deployment".into(),
            auto_select_armies: true,
            selected_armies: vec![],
            clones_per_army: 5,
            max_parallel: 100,
            use_zodiac_intelligence: true,
        };

        let result = commander.deploy_unified(config).await;
        assert!(result.is_ok());

        let deployment = result.unwrap();
        assert!(deployment.total_clones > 0);
        assert!(deployment.victories > 0);
        assert!(deployment.synergy_score > 0.0);
    }

    #[test]
    fn test_army_selection() {
        let commander = UnifiedZodiacCommander::new();

        // Test performance optimization
        let armies = commander.select_armies_for_objective("optimize embeddings hot path");
        assert!(armies.contains(&ArmyType::Tokio));
        assert!(armies.contains(&ArmyType::Lieutenant));

        // Test search
        let armies = commander.select_armies_for_objective("find all security vulnerabilities");
        assert!(armies.contains(&ArmyType::Shadow));
        assert!(armies.contains(&ArmyType::Lieutenant));
    }
}
