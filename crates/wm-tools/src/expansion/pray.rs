//! Polymorphic Resonant Adaptive Yoga (PRAY) & Hongmen / White Lotus Hierarchy.
//! Formerly PRAT (Polymorphic Resonant Adaptive Tools), renamed in v9.2.
//! Yoga (Skt. √yuj, "to yoke, join"): that which ties together — one serve
//! folding a thousand or more tools and systems into a single entrypoint.
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
use wm_memory::{AssociationStore, MemoryStore, SearchEngine};

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

// ── PRAY Meta-Tool (Polymorphic Resonant Adaptive Yoga) ────────────────

pub struct PrayMetaTool {
    store: Arc<MemoryStore>,
    search: Option<Arc<SearchEngine>>,
    associations: Option<Arc<AssociationStore>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl PrayMetaTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            search: None,
            associations: None,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Truthful outer surface: scouts read files, cold rotation
                // writes archives, queries read stores. Children invoked
                // through this router inherit these declarations.
                reads: vec![Resource::Galaxy("*".into()), Resource::Filesystem],
                writes: vec![Resource::Galaxy("*".into()), Resource::Filesystem],
                ..Default::default()
            },
        }
    }

    /// Attach full-text de-indexing for the cold-rotation child.
    #[must_use]
    pub fn with_search(mut self, search: Arc<SearchEngine>) -> Self {
        self.search = Some(search);
        self
    }

    /// Attach association cleanup for the cold-rotation child.
    #[must_use]
    pub fn with_associations(mut self, associations: Arc<AssociationStore>) -> Self {
        self.associations = Some(associations);
        self
    }
}

#[async_trait]
impl Tool for PrayMetaTool {
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
        "Polymorphic Resonant Adaptive Yoga (PRAY): Unified meta-tool for WhiteMagic substrate operations (scout, query, audit, distill, rebalance, bagua, cold_rotate, hierarchy)."
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
                    "pray_action": "scout",
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
                    "pray_action": "audit",
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
                    "pray_action": "distill",
                    "hongmen_officer": HongmenRank::WhitePaperFan.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "rebalance" | "cartographer" => {
                let rebalance = HologramRebalanceTool::new(self.store.clone());
                // Preserve the child's dry-run default: routing through PRAY
                // must never flip a read into a bulk write.
                let apply = params.get("apply").and_then(Value::as_bool).unwrap_or(false);
                let galaxy = params.get("galaxy").and_then(Value::as_str).unwrap_or("all");

                let mut child_args = json!({
                    "galaxy": galaxy,
                    "apply": apply
                });
                if let Some(limit) = params.get("limit").and_then(Value::as_u64) {
                    child_args["limit"] = json!(limit);
                }
                let res = rebalance.call(ctx, child_args).await?;

                Ok(json!({
                    "pray_action": "rebalance",
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
                    "pray_action": "hologram_query",
                    "hongmen_officer": HongmenRank::StrawSandal.chinese_title(),
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "bagua" | "dispatch" => {
                let bagua = BaguaDispatchTool::new(self.store.clone());
                let res = bagua.call(ctx, params).await?;

                Ok(json!({
                    "pray_action": "bagua_dispatch",
                    "duration_ms": start.elapsed().as_millis() as u64,
                    "result": res
                }))
            }
            "cold_rotate" | "denoise" => {
                let mut rotate_tool = GalacticColdRotateTool::new(self.store.clone());
                if let Some(search) = &self.search {
                    rotate_tool = rotate_tool.with_search(search.clone());
                }
                if let Some(associations) = &self.associations {
                    rotate_tool = rotate_tool.with_associations(associations.clone());
                }
                let dry_run = params.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
                let galaxy = params.get("galaxy").and_then(Value::as_str).unwrap_or("all");

                // Forward caller bounds instead of dropping them: a wrapper
                // must not silently widen scope.
                let mut child_args = json!({
                    "galaxy": galaxy,
                    "dry_run": dry_run
                });
                for key in ["limit", "output_dir", "project_name"] {
                    if let Some(value) = params.get(key) {
                        child_args[key] = value.clone();
                    }
                }
                let res = rotate_tool.call(ctx, child_args).await?;

                Ok(json!({
                    "pray_action": "cold_rotate",
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
                    "pray_action": "hierarchy_status",
                    "system": "WhiteMagic v9 PRAY Meta-Tool System",
                    "hongmen_ranks": hierarchy_info,
                    "white_lotus_lodges": lodges,
                    "duration_ms": start.elapsed().as_millis() as u64
                }))
            }
            other => Err(CoreError::InvalidArgs(format!(
                "Unknown PRAY action: '{other}'. Valid: scout, audit, distill, rebalance, query, bagua, cold_rotate, hierarchy"
            ))),
        }
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Deprecated alias kept for back-compat — renamed to [`PrayMetaTool`] in v9.2.
#[deprecated(since = "9.2.0", note = "renamed to PrayMetaTool")]
pub use self::PrayMetaTool as PratMetaTool;

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
    async fn test_pray_meta_tool_hierarchy() {
        let (_tmp, store) = open_store();
        let pray = PrayMetaTool::new(Arc::new(store));
        let mut ctx = Context::default();

        let res = pray.call(&mut ctx, json!({ "action": "hierarchy" })).await.unwrap();
        assert_eq!(res["pray_action"], "hierarchy_status");
        let ranks = res["hongmen_ranks"].as_array().unwrap();
        assert_eq!(ranks.len(), 7);
        assert_eq!(ranks[0]["code"], 489);
        assert_eq!(ranks[1]["code"], 438);
    }

    #[tokio::test]
    async fn test_pray_meta_tool_scout_and_audit() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m = Memory::new(Galaxy::Codex, "Dharma boundary rule test".into());
        store.put(Galaxy::Codex, &m).unwrap();

        let pray = PrayMetaTool::new(store);
        let mut ctx = Context::default();

        let res = pray.call(&mut ctx, json!({ "action": "audit" })).await.unwrap();
        assert_eq!(res["pray_action"], "audit");
        assert_eq!(res["hongmen_officer"], "紅棍 (Hung Kwan / Red Pole 426)");
    }

    #[tokio::test]
    async fn pray_rebalance_preserves_dry_run_default() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m = Memory::new(Galaxy::Codex, "Logic algorithm compute binary structure".into());
        let before = format!("{:?}", m.metadata.coord5d);
        store.put(Galaxy::Codex, &m).unwrap();

        // No `apply` param: routing through PRAY must not flip the child's
        // dry-run default into a bulk write.
        let pray = PrayMetaTool::new(store.clone());
        let mut ctx = Context::default();
        let res = pray
            .call(&mut ctx, json!({ "action": "rebalance" }))
            .await
            .unwrap();
        assert_eq!(res["pray_action"], "rebalance");
        assert_eq!(res["result"]["apply"], false);

        let after = store.get(Galaxy::Codex, m.metadata.id).unwrap().unwrap();
        assert_eq!(
            format!("{:?}", after.metadata.coord5d),
            before,
            "dry-run rebalance through PRAY must not rewrite coordinates"
        );
    }

    #[tokio::test]
    async fn pray_cold_rotate_forwards_caller_bounds() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        for i in 0..3 {
            let mut mem =
                Memory::new(Galaxy::Codex, format!("{{\"turn_type\": \"ping{i}\"}}").into());
            mem.metadata.tags = vec!["telemetry".into()];
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // `limit` must reach the child instead of being silently dropped:
        // with limit=1 only one record may rotate.
        let pray = PrayMetaTool::new(store.clone());
        let cold_dir = tempfile::tempdir().unwrap();
        let mut ctx = Context::default();
        let res = pray
            .call(
                &mut ctx,
                json!({
                    "action": "cold_rotate",
                    "params": {
                        "dry_run": false,
                        "output_dir": cold_dir.path().to_str().unwrap(),
                        "limit": 1
                    }
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["result"]["deleted_confirmed"], 1);
        assert_eq!(res["result"]["archived_confirmed"], 1);
    }

    #[tokio::test]
    async fn pray_cold_rotate_reports_cleanup_wiring() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);
        let cold_dir = tempfile::tempdir().unwrap();
        let mut ctx = Context::default();

        // Unwired wrapper: cleanup honestly reported as skipped.
        let bare = PrayMetaTool::new(store.clone());
        let res = bare
            .call(
                &mut ctx,
                json!({
                    "action": "cold_rotate",
                    "params": {
                        "dry_run": true,
                        "output_dir": cold_dir.path().to_str().unwrap()
                    }
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["result"]["search_cleanup_skipped"], true);
        assert_eq!(res["result"]["assoc_cleanup_skipped"], true);

        // Wired wrapper: cleanup active.
        let tantivy_dir = cold_dir.path().join("tantivy");
        std::fs::create_dir_all(&tantivy_dir).unwrap();
        let search = Arc::new(wm_memory::SearchEngine::open(&tantivy_dir).unwrap());
        let assoc_store =
            Arc::new(wm_memory::AssociationStore::open(store.env()).expect("assoc store"));
        let wired = PrayMetaTool::new(store)
            .with_search(search)
            .with_associations(assoc_store);
        let res = wired
            .call(
                &mut ctx,
                json!({
                    "action": "cold_rotate",
                    "params": {
                        "dry_run": true,
                        "output_dir": cold_dir.path().to_str().unwrap()
                    }
                }),
            )
            .await
            .unwrap();
        assert_eq!(res["result"]["search_cleanup_skipped"], false);
        assert_eq!(res["result"]["assoc_cleanup_skipped"], false);
    }
}
