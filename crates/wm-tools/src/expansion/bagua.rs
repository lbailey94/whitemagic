//! 8-Trigram Bagua Dynamic Cognitive Router
//!
//! Grounded in the ancient I Ching cosmology and Sun Tzu doctrine:
//! - ☰ Qian (Heaven / 乾) - Creative / Sovereign Strategy -> Captain Alchemist (Gold Synthesis)
//! - ☷ Kun (Earth / 坤) - Receptive / Manifold Grounding -> Captain Cartographer (Hologram Dispersion)
//! - ☳ Zhen (Thunder / 震) - Rapid Shock / AST Traversal -> Captain Vanguard (Fast AST Recon)
//! - ☴ Xun (Wind / 巽) - Pervasive Wind / Code Discovery -> Captain Vanguard (Multi-Repo Search)
//! - ☵ Kan (Water / 坎) - Abyssal Ocean / Holographic Retrieval -> Hologram 5D Nearest-Neighbor Query
//! - ☲ Li (Fire / 离) - Illuminating Flame / Geneseed Mining -> Geneseed Miner
//! - ☶ Gen (Mountain / 艮) - Still Mountain / Dharma & Boundary -> Captain Sentry (Dharma Audit)
//! - ☱ Dui (Lake / 兑) - Joyous Exchange / Cross-Galaxy Link -> Associative Discovery

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::str::FromStr;
use std::sync::Arc;
use std::time::Instant;
use wm_core::{Context, CoreError, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::captains::{CaptainDeployTool, HologramQueryTool, HologramRebalanceTool};
use super::geneseed::GeneseedMineTool;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Trigram {
    /// ☰ Heaven (Qian) - Creative, sovereign, highest synthesis
    Qian,
    /// ☷ Earth (Kun) - Receptive, matrix, spatial grounding
    Kun,
    /// ☳ Thunder (Zhen) - Arousing, fast shock, rapid traversal
    Zhen,
    /// ☴ Wind (Xun) - Gentle, pervasive, deep code reconnaissance
    Xun,
    /// ☵ Water (Kan) - Abyssal, unconscious, 5D holographic retrieval
    Kan,
    /// ☲ Fire (Li) - Clinging, illuminating, pattern transmutation
    Li,
    /// ☶ Mountain (Gen) - Keeping still, boundary, Dharma audit
    Gen,
    /// ☱ Lake (Dui) - Joyous, associative, cross-galaxy resonance
    Dui,
}

impl Trigram {
    #[must_use]
    pub const fn symbol(self) -> &'static str {
        match self {
            Self::Qian => "☰",
            Self::Kun => "☷",
            Self::Zhen => "☳",
            Self::Xun => "☴",
            Self::Kan => "☵",
            Self::Li => "☲",
            Self::Gen => "☶",
            Self::Dui => "☱",
        }
    }

    #[must_use]
    pub const fn chinese_name(self) -> &'static str {
        match self {
            Self::Qian => "乾 (Qián - Heaven)",
            Self::Kun => "坤 (Kūn - Earth)",
            Self::Zhen => "震 (Zhèn - Thunder)",
            Self::Xun => "巽 (Xùn - Wind)",
            Self::Kan => "坎 (Kǎn - Water)",
            Self::Li => "离 (Lí - Fire)",
            Self::Gen => "艮 (Gèn - Mountain)",
            Self::Dui => "兑 (Duì - Lake)",
        }
    }

    #[must_use]
    pub const fn doctrine(self) -> &'static str {
        match self {
            Self::Qian => "Sovereign Creation: Synthesis of high-salience realization and alchemical gold.",
            Self::Kun => "Receptive Grounding: Dimensional dispersion and topological manifold equilibrium.",
            Self::Zhen => "Arousing Shock: Lightning traversal through code graphs and AST symbols.",
            Self::Xun => "Pervasive Wind: Deep multi-repository reconnaissance across all workspaces.",
            Self::Kan => "Abyssal Ocean: Holographic 5D geometric retrieval from the unconscious sea.",
            Self::Li => "Illuminating Flame: Mining and transmuting historical git optimization geneseeds.",
            Self::Gen => "Immovable Mountain: Immutability, boundary checks, and Dharma governance.",
            Self::Dui => "Joyous Exchange: Sangha consensus, cross-galaxy links, and harmonic resonance.",
        }
    }

    #[must_use]
    pub fn parse_trigram(s: &str) -> Option<Self> {
        s.parse().ok()
    }

    #[must_use]
    pub fn from_objective(objective: &str) -> Self {
        let lower = objective.to_ascii_lowercase();
        // Note: "ground" is deliberately NOT a Kun trigger — it matches
        // "background" and would turn loose objectives into bulk writes.
        if lower.contains("rebalance") || lower.contains("dispersion") || lower.contains("manifold") {
            Self::Kun
        } else if lower.contains("ast") || lower.contains("lightning") || lower.contains("shock") {
            Self::Zhen
        } else if lower.contains("recon") || lower.contains("search") || lower.contains("scout") || lower.contains("file") {
            Self::Xun
        } else if lower.contains("query") || lower.contains("hologram") || lower.contains("retrieve") || lower.contains("abyss") {
            Self::Kan
        } else if lower.contains("geneseed") || lower.contains("miner") || lower.contains("git") || lower.contains("commit") {
            Self::Li
        } else if lower.contains("dharma") || lower.contains("audit") || lower.contains("boundary") || lower.contains("sentry") || lower.contains("trust") {
            Self::Gen
        } else if lower.contains("associate") || lower.contains("sangha") || lower.contains("link") || lower.contains("lake") {
            Self::Dui
        } else {
            Self::Qian
        }
    }
}

impl FromStr for Trigram {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_ascii_lowercase().as_str() {
            "qian" | "heaven" | "creative" | "gold" | "synthesis" => Ok(Self::Qian),
            "kun" | "earth" | "receptive" | "grounding" | "manifold" => Ok(Self::Kun),
            "zhen" | "thunder" | "shock" | "ast" | "traversal" => Ok(Self::Zhen),
            "xun" | "wind" | "pervasive" | "scout" | "recon" => Ok(Self::Xun),
            "kan" | "water" | "abyss" | "query" | "retrieval" => Ok(Self::Kan),
            "li" | "fire" | "flame" | "geneseed" | "mining" => Ok(Self::Li),
            "gen" | "mountain" | "stillness" | "dharma" | "sentry" | "audit" => Ok(Self::Gen),
            "dui" | "lake" | "joy" | "sangha" | "associate" => Ok(Self::Dui),
            other => Err(format!("Unknown trigram: {other}")),
        }
    }
}

// ── Bagua Dispatch Tool ────────────────────────────────────────────────

pub struct BaguaDispatchTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BaguaDispatchTool {
    #[must_use]
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                // Truthful outer surface: scouts read files, the Kun branch
                // rewrites coordinates, Li shells out to git.
                reads: vec![Resource::Galaxy("*".into()), Resource::Filesystem],
                writes: vec![Resource::Galaxy("*".into()), Resource::Filesystem],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for BaguaDispatchTool {
    fn name(&self) -> &str {
        "bagua.dispatch"
    }

    fn gana(&self) -> Gana {
        Gana::Ghost
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn description(&self) -> &str {
        "Dispatch cognitive goals through the 8-Trigram Bagua router to autonomous Subagent Captains and clone armies."
    }

    async fn call(&self, ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let objective = args.get("objective").and_then(Value::as_str).unwrap_or("general_synthesis");
        let trigram = if let Some(t_str) = args.get("trigram").and_then(Value::as_str) {
            Trigram::parse_trigram(t_str).ok_or_else(|| {
                CoreError::InvalidArgs(format!("Unknown trigram: {t_str}. Valid: qian, kun, zhen, xun, kan, li, gen, dui"))
            })?
        } else {
            Trigram::from_objective(objective)
        };

        let soldier_count = args.get("army_size").and_then(Value::as_u64).unwrap_or(25_000);
        let start = Instant::now();

        let (captain_dispatched, result) = match trigram {
            Trigram::Qian => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let res = captain.call(ctx, json!({
                    "role": "alchemist",
                    "objective": objective,
                    "army_size": soldier_count
                })).await?;
                ("Captain Alchemist (Huo)", res)
            }
            Trigram::Kun => {
                let rebalance = HologramRebalanceTool::new(self.store.clone());
                // Preserve the child's dry-run default and honor the
                // caller's scope: a keyword match must never become an
                // all-galaxy bulk write on its own.
                let apply = args.get("apply").and_then(Value::as_bool).unwrap_or(false);
                let galaxy = args.get("galaxy").and_then(Value::as_str).unwrap_or("all");
                let mut child_args = json!({
                    "galaxy": galaxy,
                    "apply": apply
                });
                if let Some(limit) = args.get("limit").and_then(Value::as_u64) {
                    child_args["limit"] = json!(limit);
                }
                let res = rebalance.call(ctx, child_args).await?;
                ("Captain Cartographer (Shan)", res)
            }
            Trigram::Zhen => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let target_path = args.get("target_path").and_then(Value::as_str).unwrap_or(".");
                let res = captain.call(ctx, json!({
                    "role": "vanguard",
                    "objective": objective,
                    "target_path": target_path,
                    "query": args.get("query").and_then(Value::as_str).unwrap_or("fn "),
                    "army_size": soldier_count
                })).await?;
                ("Captain Vanguard (Feng - AST Shock)", res)
            }
            Trigram::Xun => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let target_path = args.get("target_path").and_then(Value::as_str).unwrap_or(".");
                let res = captain.call(ctx, json!({
                    "role": "vanguard",
                    "objective": objective,
                    "target_path": target_path,
                    "query": args.get("query").and_then(Value::as_str).unwrap_or("tokio"),
                    "army_size": soldier_count
                })).await?;
                ("Captain Vanguard (Feng - Pervasive Recon)", res)
            }
            Trigram::Kan => {
                let query_tool = HologramQueryTool::new(self.store.clone());
                let query = args.get("query").and_then(Value::as_str).unwrap_or(objective);
                let k = args.get("k").and_then(Value::as_u64).unwrap_or(10);
                let res = query_tool.call(ctx, json!({
                    "query": query,
                    "k": k
                })).await?;
                ("Holographic 5D Abyss (Kan)", res)
            }
            Trigram::Li => {
                let mine_tool = GeneseedMineTool::new(self.store.clone());
                let repo_path = args.get("target_path").and_then(Value::as_str).unwrap_or(".");
                let res = mine_tool.call(ctx, json!({
                    "repo_path": repo_path,
                    "min_confidence": 0.5,
                    "max_commits": 100
                })).await?;
                ("Captain Alchemist (Huo - Geneseed Mining)", res)
            }
            Trigram::Gen => {
                let captain = CaptainDeployTool::new(self.store.clone());
                let res = captain.call(ctx, json!({
                    "role": "sentry",
                    "objective": objective,
                    "army_size": soldier_count
                })).await?;
                ("Captain Sentry (Lin - Mountain Dharma)", res)
            }
            Trigram::Dui => {
                // Cross-galaxy associative resonance
                let query_tool = HologramQueryTool::new(self.store.clone());
                let query = args.get("query").and_then(Value::as_str).unwrap_or(objective);
                let res = query_tool.call(ctx, json!({
                    "query": query,
                    "k": 5,
                    "semantic_only": true
                })).await?;
                ("Sangha Harmonizer (Dui)", res)
            }
        };

        let duration_ms = start.elapsed().as_millis() as u64;

        Ok(json!({
            "status": "completed",
            "trigram": {
                "name": format!("{trigram:?}").to_lowercase(),
                "symbol": trigram.symbol(),
                "chinese_name": trigram.chinese_name(),
                "doctrine": trigram.doctrine()
            },
            "objective": objective,
            "captain_dispatched": captain_dispatched,
            "duration_ms": duration_ms,
            "execution_receipt": result
        }))
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use wm_core::Galaxy;
    use wm_memory::Memory;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[tokio::test]
    async fn test_bagua_dispatch_gen_audit() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let m1 = Memory::new(Galaxy::Codex, "Immutable Dharma rule boundary".into());
        store.put(Galaxy::Codex, &m1).unwrap();

        let bagua = BaguaDispatchTool::new(store.clone());
        let mut ctx = Context::default();

        let res = bagua.call(&mut ctx, json!({
            "trigram": "gen",
            "objective": "audit_dharma_boundaries"
        })).await.unwrap();

        assert_eq!(res["status"], "completed");
        assert_eq!(res["trigram"]["symbol"], "☶");
        assert_eq!(res["captain_dispatched"], "Captain Sentry (Lin - Mountain Dharma)");
        assert_eq!(res["execution_receipt"]["memories_audited"], 1);
    }

    #[test]
    fn background_objective_does_not_route_to_kun() {
        // "ground" matched "background" and turned loose objectives into
        // bulk writes. The keyword is removed; only explicit rebalancing
        // language selects the write-capable trigram.
        assert_ne!(
            Trigram::from_objective("background task cleanup"),
            Trigram::Kun
        );
        assert_eq!(Trigram::from_objective("rebalance the store"), Trigram::Kun);
        assert_eq!(
            Trigram::from_objective("dispersion manifold check"),
            Trigram::Kun
        );
    }

    #[tokio::test]
    async fn kun_preserves_dry_run_and_caller_scope() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let codex_mem = Memory::new(Galaxy::Codex, "Logic algorithm compute binary structure".into());
        let journals_mem =
            Memory::new(Galaxy::Journals, "Dream consolidation nightly summary".into());
        let journals_before = format!("{:?}", journals_mem.metadata.coord5d);
        store.put(Galaxy::Codex, &codex_mem).unwrap();
        store.put(Galaxy::Journals, &journals_mem).unwrap();

        let bagua = BaguaDispatchTool::new(store.clone());
        let mut ctx = Context::default();

        // No `apply`: keyword routing must stay a dry run.
        let res = bagua
            .call(&mut ctx, json!({ "trigram": "kun" }))
            .await
            .unwrap();
        assert_eq!(res["status"], "completed");
        assert_eq!(res["execution_receipt"]["apply"], false);

        // Scoped apply: only the requested galaxy may be rewritten.
        let res = bagua
            .call(
                &mut ctx,
                json!({ "trigram": "kun", "galaxy": "codex", "apply": true }),
            )
            .await
            .unwrap();
        assert_eq!(res["execution_receipt"]["apply"], true);
        let journals_after = store.get(Galaxy::Journals, journals_mem.metadata.id).unwrap().unwrap();
        assert_eq!(
            format!("{:?}", journals_after.metadata.coord5d),
            journals_before,
            "a codex-scoped rebalance must leave other galaxies pristine"
        );
    }
}
