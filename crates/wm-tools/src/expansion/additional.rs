//! Additional tools — count, tags, session_list, citta_coherence, dharma_profiles, nearby.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::{galaxy_name, parse_galaxy, parse_galaxy_or};

pub struct MemoryCountTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryCountTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryCountTool {
    fn name(&self) -> &str {
        "memory.count"
    }
    fn gana(&self) -> Gana {
        Gana::WinnowingBasket
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Count memories in a galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let count = self.store.count(galaxy)?;
        Ok(json!({ "status": "success", "galaxy": galaxy_name(galaxy), "count": count }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.tags` — list all unique tags in a galaxy.
pub struct MemoryTagsTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryTagsTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryTagsTool {
    fn name(&self) -> &str {
        "memory.tags"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List all unique tags in a galaxy"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy = parse_galaxy_or(args.get("galaxy").and_then(|v| v.as_str()), Galaxy::Codex)?;
        let memories = self.store.scan(galaxy, 10_000)?;
        let tags: std::collections::HashSet<String> = memories
            .iter()
            .flat_map(|m| m.metadata.tags.iter().cloned())
            .collect();
        let tag_list: Vec<String> = tags.into_iter().collect();
        Ok(
            json!({ "status": "success", "galaxy": galaxy_name(galaxy), "unique_tags": tag_list.len(), "tags": tag_list }),
        )
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `session.list` — list all sessions.
pub struct SessionListTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl SessionListTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("sessions".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for SessionListTool {
    fn name(&self) -> &str {
        "session.list"
    }
    fn gana(&self) -> Gana {
        Gana::StraddlingLegs
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List session summaries in the Sessions galaxy (turns grouped by session)"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let memories = self.store.scan_all(Galaxy::Sessions)?;

        // Group turns and start markers into session summaries.
        #[derive(Default)]
        struct Summary {
            title: Option<String>,
            turns: u64,
            earliest: Option<chrono::DateTime<chrono::Utc>>,
            latest: Option<chrono::DateTime<chrono::Utc>>,
        }
        let mut summaries: std::collections::HashMap<String, Summary> =
            std::collections::HashMap::new();

        for m in &memories {
            if let Ok(v) = serde_json::from_str::<Value>(&m.content) {
                // session_start: session id lives in the tag.
                if v.get("type").and_then(Value::as_str) == Some("session_start") {
                    if let Some(sid) = m
                        .metadata
                        .tags
                        .iter()
                        .find_map(|t| t.strip_prefix("session:"))
                    {
                        let entry = summaries.entry(sid.to_string()).or_default();
                        entry.title = v.get("title").and_then(Value::as_str).map(String::from);
                    }
                    continue;
                }
                // session_turn (and other session memories): session id in content.
                if let Some(sid) = v.get("session_id").and_then(Value::as_str) {
                    let entry = summaries.entry(sid.to_string()).or_default();
                    let ts = m.metadata.created_at;
                    entry.earliest = Some(entry.earliest.map_or(ts, |e| e.min(ts)));
                    entry.latest = Some(entry.latest.map_or(ts, |l| l.max(ts)));
                    if v.get("sequence").and_then(Value::as_u64).is_some() {
                        entry.turns += 1;
                    }
                }
            }
        }

        let mut sessions: Vec<(String, Summary)> = summaries.into_iter().collect();
        // Most recently active sessions first.
        sessions.sort_by_key(|(_, s)| {
            std::cmp::Reverse(
                s.latest
                    .unwrap_or(chrono::DateTime::<chrono::Utc>::UNIX_EPOCH),
            )
        });
        let total = sessions.len();
        sessions.truncate(100);

        let sessions: Vec<Value> = sessions
            .into_iter()
            .map(|(sid, s)| {
                json!({
                    "session_id": sid,
                    "title": s.title.unwrap_or_else(|| format!("Session {}", &sid[..sid.len().min(8)])),
                    "turns": s.turns,
                    "first_activity": s.earliest.map(|t| t.to_rfc3339()),
                    "last_activity": s.latest.map(|t| t.to_rfc3339()),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "count": total,
            "sessions": sessions,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `citta.coherence` — check coherence threshold.
pub struct CittaCoherenceTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl CittaCoherenceTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for CittaCoherenceTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for CittaCoherenceTool {
    fn name(&self) -> &str {
        "citta.coherence"
    }
    fn gana(&self) -> Gana {
        Gana::Ghost
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Check citta coherence level and whether writes are permitted"
    }
    async fn call(&self, ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        let threshold = 0.3f32;
        let can_write = ctx.citta_coherence >= threshold;
        Ok(json!({
            "status": "success",
            "coherence": ctx.citta_coherence,
            "valence": ctx.citta_valence,
            "write_threshold": threshold,
            "can_write": can_write,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `dharma.profiles` — list available dharma profiles.
pub struct DharmaProfilesTool {
    stats: ToolStats,
    effects: EffectRow,
}

impl DharmaProfilesTool {
    #[must_use]
    pub fn new() -> Self {
        Self {
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

impl Default for DharmaProfilesTool {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
#[async_trait]
impl Tool for DharmaProfilesTool {
    fn name(&self) -> &str {
        "dharma.profiles"
    }
    fn gana(&self) -> Gana {
        Gana::ExtendedNet
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "List available dharma governance profiles"
    }
    async fn call(&self, _ctx: &mut Context, _args: Value) -> wm_core::Result<Value> {
        Ok(json!({
            "status": "success",
            "profiles": [
                { "name": "default", "description": "Standard governance — observe and advise" },
                { "name": "strict", "description": "Strict governance — intervene on writes in low coherence" },
                { "name": "research", "description": "Lenient governance — allow experimental tools" },
                { "name": "production", "description": "Hardened governance — panic on dharma violations" },
            ],
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.nearby` — find memories spatially near a query using 5D coordinates.
pub struct MemoryNearbyTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryNearbyTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("codex".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryNearbyTool {
    fn name(&self) -> &str {
        "memory.nearby"
    }
    fn gana(&self) -> Gana {
        Gana::Star
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Find memories spatially near a query text using 5D holographic coordinates"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
        if query.is_empty() {
            return Err(wm_core::CoreError::InvalidArgs(
                "Missing 'query' parameter".into(),
            ));
        }
        let galaxy_name_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_name_str)?;
        let radius = args
            .get("radius")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.5) as f32;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;

        let center = wm_core::Coordinate5D::encode(query);
        let memories = self.store.scan(galaxy, 1000)?;

        let candidates: Vec<(usize, wm_core::Coordinate5D)> = memories
            .iter()
            .enumerate()
            .map(|(i, m)| (i, m.metadata.coord5d.clone()))
            .collect();

        let nearby = wm_core::find_nearby(&center, &candidates, radius);

        let results: Vec<Value> = nearby
            .iter()
            .filter(|(idx, _)| crate::expansion::common::mcp_visible(&memories[*idx]))
            .filter(|(idx, _)| crate::expansion::common::validity_visible(&memories[*idx]))
            .take(limit)
            .map(|(idx, dist)| {
                let mem = &memories[*idx];
                json!({
                    "id": mem.metadata.id,
                    "content": mem.content.chars().take(100).collect::<String>(),
                    "distance": dist,
                    "zone": mem.metadata.coord5d.zone().name(),
                    "importance": mem.metadata.importance,
                    "tags": mem.metadata.tags,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "query": query,
            "galaxy": galaxy_name_str,
            "radius": radius,
            "center": {
                "x": center.x,
                "y": center.y,
                "z": center.z,
                "w": center.w,
                "v": center.v,
            },
            "found": results.len(),
            "scanned": memories.len(),
            "nearby": results,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}
