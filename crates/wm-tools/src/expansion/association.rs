//! Association tools — associate_mine.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{Association, AssociationStore, LinkType, MemoryStore};

use super::common::parse_galaxy;

pub struct MemoryAssociateMineTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryAssociateMineTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryAssociateMineTool {
    fn name(&self) -> &str {
        "memory.associate_mine"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Mine associations across galaxies using keyword overlap"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_name_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_name_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;
        let memories = self.store.scan(galaxy, limit)?;
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;
        let mut proposed = 0u32;
        for i in 0..memories.len() {
            for j in (i + 1)..memories.len() {
                let a = &memories[i];
                let b = &memories[j];
                let a_words: std::collections::HashSet<&str> =
                    a.content.split_whitespace().collect();
                let b_words: std::collections::HashSet<&str> =
                    b.content.split_whitespace().collect();
                let intersection = a_words.intersection(&b_words).count();
                let union = a_words.union(&b_words).count();
                if union > 0 && intersection > 2 {
                    let strength = intersection as f32 / union as f32;
                    if strength > 0.3 {
                        let assoc = Association::new(
                            a.metadata.id,
                            b.metadata.id,
                            LinkType::Related,
                            strength,
                        );
                        let _ = assoc_store.put(env, &assoc);
                        proposed += 1;
                    }
                }
            }
        }
        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name_str,
            "scanned": memories.len(),
            "proposed_associations": proposed,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `memory.relate` — typed-edge tool over the existing [`AssociationStore`]
/// (V8 S6: thin tool, not a new store).
///
/// Two actions:
/// - **relate** (default): create or re-activate a typed edge between two
///   memories. Existing edges are Hebbian-activated (`co_activation_count`
///   bumps, weight strengthens) instead of duplicated. The `follows`
///   link type maps onto `LinkType::Temporal` with the `follows`
///   association-type marker — session --follows--> session semantics.
/// - **derive_follows**: scan the Sessions galaxy (optionally filtered by
///   a workspace tag), sort session starts by creation time, and link
///   each consecutive pair with a `follows` edge — weight reflects the
///   shared tags (provenance signal), capped at 0.9.
///
/// Edges decay/prune via the store's existing Hebbian dynamics; the read
/// surface is `graph.walk` (and, with `WM_RECALL_GRAPH_WEIGHT > 0`, the
/// recall fusion itself).
pub struct MemoryRelateTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryRelateTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                ..Default::default()
            },
        }
    }

    /// Resolve a memory id across the memory galaxies.
    fn memory_exists(&self, id: uuid::Uuid) -> bool {
        wm_core::Galaxy::memory_galaxies()
            .iter()
            .any(|g| self.store.get(*g, id).ok().flatten().is_some())
    }

    fn relate_pair(
        &self,
        source: uuid::Uuid,
        target: uuid::Uuid,
        link_type: LinkType,
        marker: &str,
        weight: f32,
    ) -> wm_core::Result<Value> {
        if source == target {
            return Err(wm_core::CoreError::InvalidArgs(
                "source and target must differ".into(),
            ));
        }
        if !self.memory_exists(source) {
            return Err(wm_core::CoreError::NotFound(format!(
                "source memory {source} not found in any memory galaxy"
            )));
        }
        if !self.memory_exists(target) {
            return Err(wm_core::CoreError::NotFound(format!(
                "target memory {target} not found in any memory galaxy"
            )));
        }
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;
        if let Some(mut existing) = assoc_store.get(env, source, target)? {
            // Hebbian re-activation: the edge strengthens with co-use.
            existing.activate();
            if existing.link_type != link_type {
                existing.link_type = link_type;
                existing.association_type = marker.to_string();
            }
            assoc_store.put(env, &existing)?;
            return Ok(json!({
                "status": "activated",
                "source": source.to_string(),
                "target": target.to_string(),
                "link_type": existing.link_type.as_str(),
                "weight": existing.weight,
                "co_activation_count": existing.co_activation_count,
            }));
        }
        let mut assoc = Association::new(source, target, link_type, weight.clamp(0.0, 1.0));
        // `follows` rides the temporal type with its own marker (the
        // constructor derives the string from the type — override it).
        if marker != assoc.association_type {
            assoc.association_type = marker.to_string();
        }
        assoc_store.put(env, &assoc)?;
        Ok(json!({
            "status": "created",
            "source": source.to_string(),
            "target": target.to_string(),
            "link_type": assoc.link_type.as_str(),
            "association_type": assoc.association_type,
            "weight": assoc.weight,
        }))
    }

    fn derive_follows(&self, workspace_tag: Option<&str>) -> wm_core::Result<Value> {
        // Session start markers carry the `start` tag; sort by creation.
        let mut sessions: Vec<wm_memory::Memory> = self
            .store
            .scan_all(wm_core::Galaxy::Sessions)?
            .into_iter()
            .filter(|m| m.metadata.tags.contains(&"start".to_string()))
            .filter(|m| workspace_tag.is_none_or(|w| m.metadata.tags.contains(&w.to_string())))
            .collect();
        sessions.sort_by_key(|m| m.metadata.created_at);

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;
        let mut linked = 0usize;
        let mut activated = 0usize;
        for pair in sessions.windows(2) {
            let (earlier, later) = (&pair[0], &pair[1]);
            // Shared tags = the provenance signal for the follow.
            let shared = earlier
                .metadata
                .tags
                .iter()
                .filter(|t| later.metadata.tags.contains(t))
                .count();
            // Documented allow: mul_add changes float rounding; the weight is a
            // deterministic provenance signal, not a hot-path score.
            #[allow(clippy::suboptimal_flops)]
            let weight = (0.5 + 0.05 * shared as f32).min(0.9);
            let source = earlier.metadata.id;
            let target = later.metadata.id;
            if let Some(mut existing) = assoc_store.get(env, source, target)? {
                existing.activate();
                assoc_store.put(env, &existing)?;
                activated += 1;
            } else {
                let mut assoc = Association::new(source, target, LinkType::Temporal, weight);
                assoc.association_type = "follows".to_string();
                assoc_store.put(env, &assoc)?;
                linked += 1;
            }
        }
        Ok(json!({
            "status": "success",
            "sessions": sessions.len(),
            "workspace_tag": workspace_tag,
            "follows_created": linked,
            "follows_activated": activated,
        }))
    }
}

#[async_trait]
#[async_trait]
impl Tool for MemoryRelateTool {
    fn name(&self) -> &str {
        "memory.relate"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn input_schema(&self) -> Value {
        super::common::schema(
            &json!({
                "action": super::common::str_prop("relate (default) | derive_follows"),
                "source": super::common::str_prop("Source memory UUID (relate action)"),
                "target": super::common::str_prop("Target memory UUID (relate action)"),
                "link_type": super::common::str_prop("related | extends | contradicts | supersedes | temporal | causal | cascade | follows (default related; follows = temporal + follows marker)"),
                "weight": super::common::str_prop("Edge weight 0.0-1.0 (default 0.6; follows derivation derives it from shared tags)"),
                "workspace_tag": super::common::str_prop("derive_follows: only link sessions carrying this tag"),
            }),
            &[],
        )
    }
    fn description(&self) -> &str {
        "Relate two memories with a typed, Hebbian edge (related/extends/contradicts/supersedes/temporal/causal/cascade/follows), or derive session --follows--> session threads (action: derive_follows). Edges feed graph.walk and the recall fusion graph phase."
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        match args
            .get("action")
            .and_then(Value::as_str)
            .unwrap_or("relate")
        {
            "derive_follows" => {
                let workspace_tag = args
                    .get("workspace_tag")
                    .and_then(Value::as_str)
                    .filter(|s| !s.is_empty());
                self.derive_follows(workspace_tag)
            }
            "relate" => {
                let source_str = args.get("source").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("source (UUID string) required".into())
                })?;
                let target_str = args.get("target").and_then(Value::as_str).ok_or_else(|| {
                    wm_core::CoreError::InvalidArgs("target (UUID string) required".into())
                })?;
                let source = uuid::Uuid::parse_str(source_str).map_err(|e| {
                    wm_core::CoreError::InvalidArgs(format!("invalid source UUID: {e}"))
                })?;
                let target = uuid::Uuid::parse_str(target_str).map_err(|e| {
                    wm_core::CoreError::InvalidArgs(format!("invalid target UUID: {e}"))
                })?;
                let weight = args
                    .get("weight")
                    .and_then(Value::as_f64)
                    .map_or(0.6, |w| w as f32);
                let link_str = args
                    .get("link_type")
                    .and_then(Value::as_str)
                    .unwrap_or("related");
                // `follows` is a semantic marker on the temporal type.
                let (link_type, marker) = if link_str == "follows" {
                    (LinkType::Temporal, "follows")
                } else {
                    (LinkType::from_str_lossy(link_str), link_str)
                };
                self.relate_pair(source, target, link_type, marker, weight)
            }
            other => Err(wm_core::CoreError::InvalidArgs(format!(
                "unknown action '{other}' (relate | derive_follows)"
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
    use wm_memory::Memory;

    fn test_store() -> Arc<MemoryStore> {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("lmdb");
        std::fs::create_dir_all(&path).unwrap();
        // Leak the tempdir for the test's lifetime (store outlives it).
        std::mem::forget(dir);
        Arc::new(MemoryStore::open_default(path).unwrap())
    }

    #[tokio::test]
    async fn relate_creates_then_activates_the_same_edge() {
        let store = test_store();
        let a = Memory::new(wm_core::Galaxy::Codex, "decision alpha".into());
        let b = Memory::new(wm_core::Galaxy::Codex, "decision beta extends alpha".into());
        store.put(wm_core::Galaxy::Codex, &a).unwrap();
        store.put(wm_core::Galaxy::Codex, &b).unwrap();

        let tool = MemoryRelateTool::new(store.clone());
        let mut ctx = Context::default();
        let args = json!({
            "source": a.metadata.id.to_string(),
            "target": b.metadata.id.to_string(),
            "link_type": "extends",
            "weight": 0.7,
        });
        let first = tool.call(&mut ctx, args.clone()).await.unwrap();
        assert_eq!(first["status"], "created");
        assert_eq!(first["link_type"], "extends");
        assert!((first["weight"].as_f64().unwrap() - 0.7).abs() < 1e-6);

        let second = tool.call(&mut ctx, args).await.unwrap();
        assert_eq!(second["status"], "activated");
        assert_eq!(second["co_activation_count"], 1);
        // Hebbian re-activation strengthened the edge.
        assert!(second["weight"].as_f64().unwrap() > 0.7);

        // Exactly one edge exists.
        let env = store.env();
        let assocs = AssociationStore::open(env).unwrap();
        assert_eq!(assocs.count(env).unwrap(), 1);
    }

    #[tokio::test]
    async fn relate_follows_maps_to_temporal_with_marker() {
        let store = test_store();
        let s1 = Memory::new(wm_core::Galaxy::Sessions, "session one start".into());
        let s2 = Memory::new(wm_core::Galaxy::Sessions, "session two start".into());
        store.put(wm_core::Galaxy::Sessions, &s1).unwrap();
        store.put(wm_core::Galaxy::Sessions, &s2).unwrap();

        let tool = MemoryRelateTool::new(store);
        let mut ctx = Context::default();
        let out = tool
            .call(
                &mut ctx,
                json!({
                    "source": s1.metadata.id.to_string(),
                    "target": s2.metadata.id.to_string(),
                    "link_type": "follows",
                }),
            )
            .await
            .unwrap();
        assert_eq!(out["link_type"], "temporal");
        assert_eq!(out["association_type"], "follows");
    }

    #[tokio::test]
    async fn relate_validates_endpoints() {
        let store = test_store();
        let a = Memory::new(wm_core::Galaxy::Codex, "existing memory".into());
        store.put(wm_core::Galaxy::Codex, &a).unwrap();
        let tool = MemoryRelateTool::new(store);
        let mut ctx = Context::default();
        let err = tool
            .call(
                &mut ctx,
                json!({
                    "source": a.metadata.id.to_string(),
                    "target": uuid::Uuid::new_v4().to_string(),
                }),
            )
            .await
            .unwrap_err();
        assert!(err.to_string().contains("target memory"), "{err}");

        // Self-edges are refused.
        let err2 = tool
            .call(
                &mut ctx,
                json!({
                    "source": a.metadata.id.to_string(),
                    "target": a.metadata.id.to_string(),
                }),
            )
            .await
            .unwrap_err();
        assert!(err2.to_string().contains("must differ"), "{err2}");
    }

    #[tokio::test]
    async fn derive_follows_links_consecutive_sessions_in_order() {
        let store = test_store();
        // Three sessions, deliberately created out of chronological order.
        let mk = |content: &str, offset_days: i64, workspace: Option<&str>| {
            let mut m = Memory::new(wm_core::Galaxy::Sessions, content.to_string());
            m.metadata.tags = vec!["start".to_string(), "session".to_string()];
            if let Some(w) = workspace {
                m.metadata.tags.push(w.to_string());
            }
            m.metadata.created_at = chrono::Utc::now() - chrono::Duration::days(offset_days);
            m.metadata.accessed_at = m.metadata.created_at;
            m
        };
        let s1 = mk("first session", 3, Some("wmv5"));
        let s2 = mk("second session", 2, Some("wmv5"));
        let s3 = mk("third session", 1, None);
        // Insert out of order; the derivation sorts by created_at.
        for m in [&s3, &s1, &s2] {
            store.put(wm_core::Galaxy::Sessions, m).unwrap();
        }

        let tool = MemoryRelateTool::new(store.clone());
        let mut ctx = Context::default();

        // Workspace-filtered: only s1 --follows--> s2 (both carry "wmv5").
        let out = tool
            .call(
                &mut ctx,
                json!({"action": "derive_follows", "workspace_tag": "wmv5"}),
            )
            .await
            .unwrap();
        assert_eq!(out["sessions"], 2);
        assert_eq!(out["follows_created"], 1);

        let env = store.env();
        let assocs = AssociationStore::open(env).unwrap();
        let from_s1 = assocs.find_from(env, s1.metadata.id).unwrap();
        assert_eq!(from_s1.len(), 1);
        assert_eq!(from_s1[0].target, s2.metadata.id);
        assert_eq!(from_s1[0].link_type, LinkType::Temporal);
        assert_eq!(from_s1[0].association_type, "follows");

        // Unfiltered re-run: s2 --follows--> s3 is new; s1→s2 re-activates.
        let out2 = tool
            .call(&mut ctx, json!({"action": "derive_follows"}))
            .await
            .unwrap();
        assert_eq!(out2["sessions"], 3);
        assert_eq!(out2["follows_created"], 1);
        assert_eq!(out2["follows_activated"], 1);
        assert_eq!(assocs.count(env).unwrap(), 2);

        // The acceptance query: "what led to s3" walks back through the
        // follows chain to s1.
        let chain = assocs.find_to(env, s3.metadata.id).unwrap();
        assert_eq!(chain[0].source, s2.metadata.id);
        let earlier = assocs.find_to(env, chain[0].source).unwrap();
        assert_eq!(earlier[0].source, s1.metadata.id);
    }
}
