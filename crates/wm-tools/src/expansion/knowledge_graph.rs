//! Knowledge graph tools — kg.extract, kg.query, kg.top.
//!
//! These tools build a knowledge graph on top of the association store.
//! `kg.extract` mines entity-relationship triples from memory content and
//! creates typed associations. `kg.query` retrieves all relationships for a
//! given entity. `kg.top` finds the most-connected entities (hub nodes).

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Gana, Resource, Tool, ToolStats};
use wm_memory::{Association, AssociationStore, LinkType, MemoryStore};

use super::common::{galaxy_name, parse_galaxy};

/// Simple entity extraction: capitalized words and multi-word phrases.
///
/// Returns a list of (entity_text, position) pairs. This is a lightweight
/// NER that doesn't require external models — it uses capitalization
/// heuristics and common relationship patterns.
fn extract_entities(content: &str) -> Vec<String> {
    let mut entities = Vec::new();
    let words: Vec<&str> = content.split_whitespace().collect();

    let mut i = 0;
    while i < words.len() {
        let word = words[i];

        // Single capitalized word (not at sentence start, or is a proper noun)
        if word.chars().next().is_some_and(char::is_uppercase) && word.len() > 1 {
            // Check if it's a multi-word entity (consecutive capitalized words)
            let mut phrase = vec![word];
            let mut j = i + 1;
            while j < words.len() {
                let next = words[j];
                if next.chars().next().is_some_and(char::is_uppercase) && next.len() > 1 {
                    phrase.push(next);
                    j += 1;
                } else {
                    break;
                }
            }
            // Strip leading common words (e.g., "The White Magic" → "White Magic")
            while phrase.len() > 1 && is_common_word(&phrase[0].to_lowercase()) {
                phrase.remove(0);
            }
            let entity = phrase.join(" ");
            // Filter out common words and empty phrases
            let lower = entity.to_lowercase();
            if !entity.is_empty() && !is_common_word(&lower) {
                entities.push(entity);
            }
            i = j;
        } else {
            i += 1;
        }
    }

    entities
}

/// Check if a word is a common English word that shouldn't be an entity.
fn is_common_word(s: &str) -> bool {
    matches!(
        s,
        "the"
            | "a"
            | "an"
            | "this"
            | "that"
            | "these"
            | "those"
            | "it"
            | "is"
            | "was"
            | "are"
            | "were"
            | "be"
            | "been"
            | "we"
            | "they"
            | "he"
            | "she"
            | "i"
            | "you"
            | "in"
            | "on"
            | "at"
            | "to"
            | "for"
            | "of"
            | "with"
            | "and"
            | "or"
            | "but"
            | "not"
            | "if"
            | "then"
            | "when"
            | "where"
            | "what"
            | "who"
            | "how"
            | "why"
            | "there"
            | "here"
            | "so"
            | "no"
            | "yes"
    )
}

/// Detect relationship type between two entities based on connecting words.
fn detect_link_type(content: &str, entity_a: &str, entity_b: &str) -> LinkType {
    let lower = content.to_lowercase();
    let a_lower = entity_a.to_lowercase();
    let b_lower = entity_b.to_lowercase();

    // Find the text between the two entities
    if let Some(pos_a) = lower.find(&a_lower) {
        let after_a = pos_a + a_lower.len();
        if let Some(pos_b) = lower[after_a..].find(&b_lower) {
            let between = &lower[after_a..after_a + pos_b];
            let between_trimmed = between.trim();

            if between_trimmed.contains("because")
                || between_trimmed.contains("causes")
                || between_trimmed.contains("leads to")
                || between_trimmed.contains("results in")
            {
                return LinkType::Causal;
            }
            if between_trimmed.contains("before")
                || between_trimmed.contains("after")
                || between_trimmed.contains("then")
                || between_trimmed.contains("followed by")
            {
                return LinkType::Temporal;
            }
            if between_trimmed.contains("extends")
                || between_trimmed.contains("refines")
                || between_trimmed.contains("builds on")
                || between_trimmed.contains("improves")
            {
                return LinkType::Extends;
            }
            if between_trimmed.contains("contradicts")
                || between_trimmed.contains("but")
                || between_trimmed.contains("however")
                || between_trimmed.contains("opposes")
            {
                return LinkType::Contradicts;
            }
            if between_trimmed.contains("replaces")
                || between_trimmed.contains("supersedes")
                || between_trimmed.contains("instead of")
            {
                return LinkType::Supersedes;
            }
            if between_trimmed.contains("triggers")
                || between_trimmed.contains("cascades")
                || between_trimmed.contains("chain")
            {
                return LinkType::Cascade;
            }
        }
    }
    LinkType::Related
}

/// `kg.extract` — extract entities from memory content and create typed associations.
///
/// Scans memories in a galaxy, extracts entities (capitalized phrases),
/// and creates typed associations between memories that share entities.
/// The relationship type is inferred from connecting words.
pub struct KgExtractTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KgExtractTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow {
                writes: vec![Resource::Galaxy("associations".into())],
                reads: vec![Resource::Galaxy("codex".into())],
                ..Default::default()
            },
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for KgExtractTool {
    fn name(&self) -> &str {
        "kg.extract"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Extract entities from memory content and create typed associations (knowledge graph)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(200) as usize;

        let memories = self.store.scan(galaxy, limit)?;
        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Build entity → memory index
        let mut entity_index: HashMap<String, Vec<uuid::Uuid>> = HashMap::new();

        for mem in &memories {
            let entities = extract_entities(&mem.content);
            for entity in entities {
                entity_index
                    .entry(entity.to_lowercase())
                    .or_default()
                    .push(mem.metadata.id);
            }
        }

        // Create associations between memories sharing entities
        let mut created = 0u32;
        let mut skipped = 0u32;
        for mem_ids in entity_index.values() {
            if mem_ids.len() < 2 {
                continue;
            }
            for i in 0..mem_ids.len() {
                for j in (i + 1)..mem_ids.len() {
                    let src = mem_ids[i];
                    let tgt = mem_ids[j];

                    // Skip if association already exists
                    if assoc_store.get(env, src, tgt).unwrap_or(None).is_some() {
                        skipped += 1;
                        continue;
                    }

                    // Detect link type from content
                    let src_mem = memories.iter().find(|m| m.metadata.id == src);
                    let tgt_mem = memories.iter().find(|m| m.metadata.id == tgt);
                    let link_type = if let (Some(s), Some(t)) = (src_mem, tgt_mem) {
                        // Use the source content to detect relationship
                        detect_link_type(&s.content, &s.content, &t.content)
                    } else {
                        LinkType::Related
                    };

                    let weight = 0.5f32.mul_add((mem_ids.len() - 2).min(5) as f32, 0.5);
                    let assoc = Association::new(src, tgt, link_type, weight.min(1.0));
                    let _ = assoc_store.put(env, &assoc);
                    created += 1;
                }
            }
        }

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "scanned": memories.len(),
            "entities_found": entity_index.len(),
            "associations_created": created,
            "associations_skipped_existing": skipped,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `kg.query` — query the knowledge graph for a given entity.
///
/// Finds all memories containing the entity, then retrieves all associations
/// for those memories. Returns the subgraph around the entity.
pub struct KgQueryTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KgQueryTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![
                Resource::Galaxy("codex".into()),
                Resource::Galaxy("associations".into()),
            ]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for KgQueryTool {
    fn name(&self) -> &str {
        "kg.query"
    }
    fn gana(&self) -> Gana {
        Gana::Net
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Query the knowledge graph for an entity (find memories and associations)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let entity = args
            .get("entity")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("Missing 'entity' parameter".into()))?;
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(50) as usize;

        let memories = self.store.scan(galaxy, limit)?;
        let entity_lower = entity.to_lowercase();

        // Find memories containing the entity
        let matching: Vec<_> = memories
            .iter()
            .filter(|m| m.content.to_lowercase().contains(&entity_lower))
            .collect();

        let env = self.store.env();
        let assoc_store = AssociationStore::open(env)?;

        // Collect all associations for matching memories
        let mut edges = Vec::new();
        let mut connected_ids: std::collections::HashSet<uuid::Uuid> =
            std::collections::HashSet::new();

        for mem in &matching {
            let from = assoc_store
                .find_from(env, mem.metadata.id)
                .unwrap_or_default();
            let to = assoc_store
                .find_to(env, mem.metadata.id)
                .unwrap_or_default();

            for a in &from {
                edges.push(json!({
                    "source": a.source,
                    "target": a.target,
                    "link_type": a.link_type.as_str(),
                    "weight": a.weight,
                }));
                connected_ids.insert(a.target);
            }
            for a in &to {
                edges.push(json!({
                    "source": a.source,
                    "target": a.target,
                    "link_type": a.link_type.as_str(),
                    "weight": a.weight,
                }));
                connected_ids.insert(a.source);
            }
        }

        let node_mems: Vec<Value> = matching
            .iter()
            .map(|m| {
                json!({
                    "id": m.metadata.id,
                    "content_preview": m.content.chars().take(200).collect::<String>(),
                    "tags": m.metadata.tags,
                    "galaxy": galaxy_name(galaxy),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "entity": entity,
            "galaxy": galaxy_name(galaxy),
            "matching_memories": matching.len(),
            "nodes": node_mems,
            "edges": edges,
            "edge_count": edges.len(),
            "connected_entities": connected_ids.len(),
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// `kg.top` — find top entities by connection count (hub/god nodes).
///
/// Scans memories, extracts entities, and ranks them by the number of
/// memories they appear in. Returns the top N entities with their
/// connection counts and sample memories.
pub struct KgTopTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl KgTopTool {
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
impl Tool for KgTopTool {
    fn name(&self) -> &str {
        "kg.top"
    }
    fn gana(&self) -> Gana {
        Gana::HairyHead
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Find top entities by connection count (hub/god nodes in the knowledge graph)"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args
            .get("galaxy")
            .and_then(|v| v.as_str())
            .unwrap_or("codex");
        let galaxy = parse_galaxy(galaxy_str)?;
        let limit = args
            .get("limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(500) as usize;
        let top_n = args
            .get("top_n")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;

        let memories = self.store.scan(galaxy, limit)?;

        // Build entity frequency map
        let mut entity_freq: HashMap<String, Vec<uuid::Uuid>> = HashMap::new();
        for mem in &memories {
            let entities = extract_entities(&mem.content);
            for entity in entities {
                let entry = entity_freq.entry(entity.to_lowercase()).or_default();
                if !entry.contains(&mem.metadata.id) {
                    entry.push(mem.metadata.id);
                }
            }
        }

        // Sort by connection count (descending)
        let mut ranked: Vec<(String, Vec<uuid::Uuid>)> = entity_freq.into_iter().collect();
        ranked.sort_by_key(|entry| std::cmp::Reverse(entry.1.len()));

        let top: Vec<Value> = ranked
            .iter()
            .take(top_n)
            .map(|(entity, ids)| {
                json!({
                    "entity": entity,
                    "memory_count": ids.len(),
                    "sample_memory_ids": ids.iter().take(5).map(std::string::ToString::to_string).collect::<Vec<_>>(),
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "galaxy": galaxy_name(galaxy),
            "scanned": memories.len(),
            "total_entities": ranked.len(),
            "top_entities": top,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn open_store() -> (tempfile::TempDir, MemoryStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, store)
    }

    #[tokio::test]
    async fn extract_entities_finds_capitalized_words() {
        let entities = extract_entities("Rust is a language. Python is also great.");
        assert!(entities.contains(&"Rust".to_string()));
        assert!(entities.contains(&"Python".to_string()));
    }

    #[tokio::test]
    async fn extract_entities_finds_multi_word_phrases() {
        let entities = extract_entities("The White Magic project uses LMDB storage.");
        assert!(entities.contains(&"White Magic".to_string()));
        assert!(entities.contains(&"LMDB".to_string()));
    }

    #[tokio::test]
    async fn extract_entities_ignores_common_words() {
        let entities = extract_entities("The quick brown fox jumps over the lazy dog.");
        // "The" at sentence start should be filtered
        assert!(!entities.iter().any(|e| e == "The"));
    }

    #[tokio::test]
    async fn detect_link_type_causal() {
        let lt = detect_link_type(
            "Rust causes fast performance because of zero-cost abstractions",
            "Rust",
            "zero-cost abstractions",
        );
        assert_eq!(lt, LinkType::Causal);
    }

    #[tokio::test]
    async fn detect_link_type_temporal() {
        let lt = detect_link_type(
            "First we tried Python, then we switched to Rust",
            "Python",
            "Rust",
        );
        assert_eq!(lt, LinkType::Temporal);
    }

    #[tokio::test]
    async fn detect_link_type_related_default() {
        let lt = detect_link_type("Rust and Python are languages", "Rust", "Python");
        assert_eq!(lt, LinkType::Related);
    }

    #[tokio::test]
    async fn kg_extract_creates_associations() {
        let (_tmp, store) = open_store();
        let store = Arc::new(store);

        let mem1 = wm_memory::Memory::new(wm_core::Galaxy::Codex, "Rust is a fast language".into());
        let mem2 = wm_memory::Memory::new(
            wm_core::Galaxy::Codex,
            "Rust is also a great language".into(),
        );
        store.put(wm_core::Galaxy::Codex, &mem1).unwrap();
        store.put(wm_core::Galaxy::Codex, &mem2).unwrap();

        let tool = KgExtractTool::new(store.clone());
        let result = tool
            .call(&mut Context::default(), json!({"galaxy": "codex"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["scanned"], 2);
        // "Rust" appears in both memories, so at least 1 entity
        assert!(obj["entities_found"].as_u64().unwrap() >= 1);

        // Verify associations were created (Rust links the two memories)
        let env = store.env();
        let assoc_store = AssociationStore::open(env).unwrap();
        let count = assoc_store.count(env).unwrap();
        assert!(count > 0, "should have created at least one association");
    }

    #[tokio::test]
    async fn kg_query_finds_entity() {
        let (_tmp, store) = open_store();

        let mem = wm_memory::Memory::new(
            wm_core::Galaxy::Codex,
            "Rust is a systems programming language".into(),
        );
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        let tool = KgQueryTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"entity": "Rust", "galaxy": "codex"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["matching_memories"], 1);
        assert_eq!(obj["entity"], "Rust");
    }

    #[tokio::test]
    async fn kg_query_missing_entity_param_errors() {
        let (_tmp, store) = open_store();
        let tool = KgQueryTool::new(Arc::new(store));
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn kg_top_ranks_entities() {
        let (_tmp, store) = open_store();

        // Create memories with a shared entity
        for i in 0..5 {
            let content = format!("Rust is mentioned in memory number {i}");
            let mem = wm_memory::Memory::new(wm_core::Galaxy::Codex, content);
            store.put(wm_core::Galaxy::Codex, &mem).unwrap();
        }
        // One memory without Rust
        let mem = wm_memory::Memory::new(wm_core::Galaxy::Codex, "Python is great".into());
        store.put(wm_core::Galaxy::Codex, &mem).unwrap();

        let tool = KgTopTool::new(Arc::new(store));
        let result = tool
            .call(
                &mut Context::default(),
                json!({"galaxy": "codex", "top_n": 5}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["scanned"], 6);
        let top = obj["top_entities"].as_array().unwrap();
        assert!(!top.is_empty());
        // Rust should be the top entity (appears in 5 memories)
        let top_entity = top[0]["entity"].as_str().unwrap();
        assert_eq!(top_entity, "rust");
        assert_eq!(top[0]["memory_count"], 5);
    }

    #[tokio::test]
    async fn kg_tool_names_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(KgExtractTool::new(store.clone()).name(), "kg.extract");
        assert_eq!(KgQueryTool::new(store.clone()).name(), "kg.query");
        assert_eq!(KgTopTool::new(store).name(), "kg.top");
    }

    #[tokio::test]
    async fn kg_tool_ganas_are_correct() {
        let store = Arc::new(open_store().1);
        assert_eq!(KgExtractTool::new(store.clone()).gana(), Gana::Net);
        assert_eq!(KgQueryTool::new(store.clone()).gana(), Gana::Net);
        assert_eq!(KgTopTool::new(store).gana(), Gana::HairyHead);
    }
}
