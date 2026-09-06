//! Polymorphic Resonant Adaptive Tool (PRAT) & Hongmen / White Lotus Hierarchy.
//!
//! Grounded in the unified meta-tool doctrine:
//! - A single universal server surface exposing all of WhiteMagic through a polymorphic entrypoint.
//! - Hongmen (Tiandihui) numerical ranks:
//!   - 489: Mountain Master (Shan Chu) - Supreme Architect (High Planner)
//!   - 438: Incense Master (Sin Fung) - Vanguard (Wind / Rapid Reconnaissance)
//!   - 415: White Paper Fan (Pak Tsz Sin) - Alchemist (Fire / Strategist & Distillation)
//!   - 426: Red Pole (Hung Kwan) - Sentry (Forest / Military Defense & Dharma Audit)
//!   - 432: Straw Sandal (Cho Hai) - Cartographer (Mountain / Spatial Navigator)
//!   - 49: Brethren (Sze Kau) - Rank-and-File Clone Soldiers
//!   - 25: Infiltrator (Yee Ng Chai) - Dharma Anomaly Detector
//! - White Lotus (Bai Lian Jiao) Cellular Lodges (Tang): autonomous self-healing nodes.

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::sync::Arc;
use std::time::Instant;
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::army::GalacticColdRotateTool;
use super::bagua::BaguaDispatchTool;
use super::captains::{CaptainDeployTool, HologramQueryTool, HologramRebalanceTool};

/// Hongmen (Tiandihui) Numerical Ranks
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum HongmenRank {
    /// 489 - Mountain Master (Shan Chu) - Supreme Architect
    MountainMaster,
    /// 438 - Incense Master / Vanguard (Sin Fung) - Rapid Scout
    IncenseMaster,
    /// 415 - White Paper Fan (Pak Tsz Sin) - Alchemist Strategist
    WhitePaperFan,
    /// 426 - Red Pole (Hung Kwan) - Sentry Enforcer
    RedPole,
    /// 432 - Straw Sandal (Cho Hai) - Cartographer Navigator
    StrawSandal,
    /// 49 - Brethren (Sze Kau) - Parallel Clone Armies
    Brethren,
    /// 25 - Infiltrator (Yee Ng Chai) - Dharma Anomaly
    Infiltrator,
}

impl HongmenRank {
    #[must_use]
    pub const fn code(self) -> u32 {
        match self {
            Self::MountainMaster => 489,
            Self::IncenseMaster => 438,
            Self::WhitePaperFan => 415,
            Self::RedPole => 426,
            Self::StrawSandal => 432,
            Self::Brethren => 49,
            Self::Infiltrator => 25,
        }
    }

    #[must_use]
    pub const fn chinese_title(self) -> &'static str {
        match self {
            Self::MountainMaster => "山主 (Shan Chu / Dragon Head 489)",
            Self::IncenseMaster => "先鋒 (Sin Fung / Incense Master 438)",
            Self::WhitePaperFan => "白紙扇 (Pak Tsz Sin / White Paper Fan 415)",
            Self::RedPole => "紅棍 (Hung Kwan / Red Pole 426)",
            Self::StrawSandal => "草鞋 (Cho Hai / Straw Sandal 432)",
            Self::Brethren => "四九 (Sze Kau / Brethren 49)",
            Self::Infiltrator => "二五仔 (Yee Ng Chai / Infiltrator 25)",
        }
    }

    #[must_use]
    pub const fn role_description(self) -> &'static str {
        match self {
            Self::MountainMaster => "Supreme Architecture: Master guidance and holistic ledger direction.",
            Self::IncenseMaster => "Frontline Pioneer: Traversal of unknown directories, codebases, and perimeters.",
            Self::WhitePaperFan => "Sage Calculation: Transmutation of commits, logs, and turns into golden Geneseeds.",
            Self::RedPole => "Martial Discipline: Whole-store Dharma governance, Landlock defense, and trust auditing.",
            Self::StrawSandal => "Spatial Logistics: Manifold rebalancing, 5D coordinates, and inter-lodge travel.",
            Self::Brethren => "Swarm Execution: Massively parallel Tokio and Rayon work-stealing soldiers.",
            Self::Infiltrator => "Anomaly Sentry: Detection of corrupted memories, stale states, and rule breaches.",
        }
    }
}

/// White Lotus Cellular Lodge (Tang / 堂)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WhiteLotusLodge {
    pub name: String,
    pub chinese_name: String,
    pub active_galaxies: usize,
    pub resilience_rating: f64,
}

impl WhiteLotusLodge {
    #[must_use]
    pub fn new(name: impl Into<String>, chinese_name: impl Into<String>, active_galaxies: usize) -> Self {
        Self {
            name: name.into(),
            chinese_name: chinese_name.into(),
            active_galaxies,
            resilience_rating: 1.0,
        }
    }
}

// ── PRAT Meta-Tool (Polymorphic Resonant Adaptive Tool) ────────────────

pub struct PratMetaTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PratMetaTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: vec![Resource::Galaxy("*".into())],
                writes: vec![Resource::Galaxy("*".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for PratMetaTool {
    fn name(&self) -> &str {
        "whitemagic"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Polymorphic Resonant Adaptive Tool (PRAT): Unified meta-tool for WhiteMagic substrate operations (scout, query, audit, distill, rebalance, bagua, cold_rotate, hierarchy)."
    }

    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let action = args.get("action").and_then(Value::as_str).unwrap_or("status");
        let params = args.get("params").cloned().unwrap_or_else(|| json!({}));
        let start = Instant::now();

        match action.to_ascii_lowercase().as_str() {
            "scout" | "vanguard" => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let target_path = params.get("target_path").and_then(Value::as_str).unwrap_or(".");
                let query = params.get("query").and_then(Value::as_str).unwrap_or("");
                let army_size = params.get("army_size").and_then(Value::as_u64).unwrap_or(25_000);

                let res = captain.call(ctx, json!({
                    "role": "vanguard",
                    "target_path": target_path,
                    "query": query,
                    "army_size": army_size
                })).await?;

                Ok(json!({
                    "prat_action": "scout",
                    "hongmen_officer": HongmenRank::IncenseMaster.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "audit" | "sentry" => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let army_size = params.get("army_size").and_then(Value::as_u64).unwrap_or(50_000);

                let res = captain.call(ctx, json!({
                    "role": "sentry",
                    "army_size": army_size
                })).await?;

                Ok(json!({
                    "prat_action": "audit",
                    "hongmen_officer": HongmenRank::RedPole.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "distill" | "alchemy" => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let army_size = params.get("army_size").and_then(Value::as_u64).unwrap_or(50_000);

                let res = captain.call(ctx, json!({
                    "role": "alchemist",
                    "army_size": army_size
                })).await?;

                Ok(json!({
                    "prat_action": "distill",
                    "hongmen_officer": HongmenRank::WhitePaperFan.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "rebalance" | "cartographer" => {
                let rebalance = HologramRebalanceTool::new(self.store.clone());
                let apply = params.get("apply").and_then(Value::as_bool).unwrap_or(true);
                let galaxy = params.get("galaxy").and_then(Value::as_str).unwrap_or("all");

                let res = rebalance.call(ctx, json!({
                    "galaxy": galaxy,
                    "apply": apply
                })).await?;

                Ok(json!({
                    "prat_action": "rebalance",
                    "hongmen_officer": HongmenRank::StrawSandal.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "query" | "hologram" => {
                let query_tool = HologramQueryTool::new(self.store.clone());
                let query_str = params.get("query").and_then(Value::as_str).unwrap_or("");
                let k = params.get("k").and_then(Value::as_u64).unwrap_or(10);
                let galaxy = params.get("galaxy").and_then(Value::as_str).unwrap_or("all");

                let res = query_tool.call(ctx, json!({
                    "query": query_str,
                    "galaxy": galaxy,
                    "k": k
                })).await?;

                Ok(json!({
                    "prat_action": "hologram_query",
                    "hongmen_officer": HongmenRank::StrawSandal.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "bagua" | "dispatch" => {
                let bagua = BaguaDispatchTool::new(self.store.clone());
                let res = bagua.call(ctx, params).await?;

                Ok(json!({
                    "prat_action": "bagua_dispatch",
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "cold_rotate" | "denoise" => {
                let rotate_tool = GalacticColdRotateTool::new(self.store.clone());
                let dry_run = params.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
                let galaxy = params.get("galaxy").and_then(Value::as_str).unwrap_or("all");

                let res = rotate_tool.call(ctx, json!({
                    "galaxy": galaxy,
                    "dry_run": dry_run
                })).await?;

                Ok(json!({
                    "prat_action": "cold_rotate",
                    "hongmen_officer": HongmenRank::RedPole.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "hierarchy" | "status" => {
                let ranks = [
                    HongmenRank::MountainMaster,
                    HongmenRank::IncenseMaster,
                    HongmenRank::WhitePaperFan,
                    HongmenRank::RedPole,
                    HongmenRank::StrawSandal,
                    HongmenRank::Brethren,
                    HongmenRank::Infiltrator,
                ];

                let hierarchy_info = ranks.iter().map(|r| {
                    json!({
                        "code": r.code(),
                        "title": r.chinese_title(),
                        "doctrine": r.role_description()
                    })
                }).collect::<Vec<_>>();

                let lodges = [
                    WhiteLotusLodge::new("Lodge of Heaven & Earth", "天地堂 (Primary Codex)", 14),
                    WhiteLotusLodge::new("Lodge of Pure Water", "清水堂 (Consolidation & Dreams)", 4),
                    WhiteLotusLodge::new("Lodge of the Iron Mountain", "鐵山堂 (Dharma Governance)", 3),
                ];

                Ok(json!({
                    "prat_action": "hierarchy_status",
                    "system": "WhiteMagic v8/v9 PRAT Meta-Tool System",
                    "hongmen_ranks": hierarchy_info,
                    "white_lotus_lodges": lodges,
                    "duration_ms": start.elapsed().as_millis() as u64
                }))
            }
            other => Err(CoreError::InvalidArgs(format!(
                "Unknown PRAT action: '{other}'. Valid: scout, audit, distill, rebalance, query, bagua, cold_rotate, hierarchy"
            ))),
        }
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;
    use wm_core::Galaxy;
    use wm_memory::Memory;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[tokio::test]
    async fn test_prat_meta_tool_hierarchy() {
        let (_tmp, store) = open_store();
        let prat = PratMetaTool::new(Arc::new(store));
        let mut ctx = Context::default();

        let res = prat.call(&mut ctx, json!({ "action": "hierarchy" })).await.unwrap();
        assert_eq!(res["prat_action"], "hierarchy_status");
        let ranks = res["hongmen_ranks"].as_array().unwrap();
        assert_eq!(ranks.len(), 7);
        assert_eq!(ranks[0]["code"], 489);
        assert_eq!(ranks[1]["code"], 438);
    }

    #[tokio::test]
    async fn test_prat_meta_tool_scout_and_audit() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m = Memory::new(Galaxy::Codex, "Dharma boundary rule test".into());
        store.put(Galaxy::Codex, &m).unwrap();

        let prat = PratMetaTool::new(store);
        let mut ctx = Context::default();

        let res = prat.call(&mut ctx, json!({ "action": "audit" })).await.unwrap();
        assert_eq!(res["prat_action"], "audit");
        assert_eq!(res["hongmen_officer"], "紅棍 (Hung Kwan / Red Pole 426)");
    }
}
