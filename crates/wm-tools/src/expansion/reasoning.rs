//! Reasoning tools — reasoning.bicameral, think, explain.
//!
//! Gana::ThreeStars — "Explanation, bicameral reasoning, think"
//!
//! These tools provide structured reasoning capabilities: bicameral
//! (pros/cons) analysis, general-purpose thinking with memory context,
//! and explanation generation for memory content.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::{galaxy_name, parse_galaxy};

// ── reasoning.bicameral ──────────────────────────────────────────────

/// Bicameral reasoning: analyze a topic from multiple perspectives.
///
/// Searches memories for supporting and opposing evidence, then structures
/// the analysis as a bicameral (two-chamber) debate with pros, cons, and
/// a synthesis.
pub struct ReasoningBicameralTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ReasoningBicameralTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ReasoningBicameralTool {
    fn name(&self) -> &str {
        "reasoning.bicameral"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Analyze a topic from multiple perspectives using bicameral reasoning"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let topic = args
            .get("topic")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("topic (string) required".into()))?;
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let scan_limit = args
            .get("scan_limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(500) as usize;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        let topic_lower = topic.to_lowercase();
        let topic_words: Vec<&str> = topic_lower.split_whitespace().collect();

        // Collect memories matching the topic
        let mut supporting: Vec<Value> = Vec::new();
        let mut opposing: Vec<Value> = Vec::new();
        let mut neutral: Vec<Value> = Vec::new();

        // Opposition keywords
        let opposition_markers = [
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
        ];
        let support_markers = [
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
        ];

        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            for mem in mems {
                let content_lower = mem.content.to_lowercase();
                if !topic_words.iter().any(|tw| content_lower.contains(tw)) {
                    continue;
                }

                let entry = json!({
                    "galaxy": galaxy_name(*galaxy),
                    "id": mem.metadata.id,
                    "content_preview": mem.content.chars().take(150).collect::<String>(),
                    "importance": mem.metadata.importance,
                    "tags": mem.metadata.tags,
                });

                let has_opposition = opposition_markers.iter().any(|m| content_lower.contains(m));
                let has_support = support_markers.iter().any(|m| content_lower.contains(m));

                if has_opposition && !has_support {
                    opposing.push(entry);
                } else if has_support && !has_opposition {
                    supporting.push(entry);
                } else {
                    neutral.push(entry);
                }
            }
        }

        let total = supporting.len() + opposing.len() + neutral.len();
        let balance = if total == 0 {
            0.0
        } else {
            ((supporting.len() as f64 - opposing.len() as f64) / total as f64 * 100.0).round()
        };

        // Synthesis
        let synthesis = if total == 0 {
            format!(
                "No memories found related to '{topic}'. Consider creating memories on this topic first."
            )
        } else if supporting.len() > opposing.len() * 2 {
            format!(
                "The evidence strongly favors '{}' with {} supporting vs {} opposing memories.",
                topic,
                supporting.len(),
                opposing.len()
            )
        } else if opposing.len() > supporting.len() * 2 {
            format!(
                "The evidence predominantly opposes '{}' with {} opposing vs {} supporting memories.",
                topic,
                opposing.len(),
                supporting.len()
            )
        } else {
            format!(
                "The evidence on '{}' is balanced: {} supporting, {} opposing, {} neutral. Further investigation recommended.",
                topic,
                supporting.len(),
                opposing.len(),
                neutral.len()
            )
        };

        Ok(json!({
            "status": "success",
            "topic": topic,
            "total_evidence": total,
            "supporting": supporting,
            "opposing": opposing,
            "neutral": neutral,
            "balance_score": balance,
            "synthesis": synthesis,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── think ────────────────────────────────────────────────────────────

/// General-purpose thinking tool that gathers relevant memories and
/// produces a structured analysis with key insights.
///
/// Unlike single-purpose tools, `think` performs a holistic analysis:
/// gathers context from memories, identifies key themes, and produces
/// a structured response with observations and questions.
pub struct ThinkTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ThinkTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ThinkTool {
    fn name(&self) -> &str {
        "think"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Gather memory context and produce structured analysis with insights"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let query = args
            .get("query")
            .and_then(|v| v.as_str())
            .ok_or_else(|| wm_core::CoreError::InvalidArgs("query (string) required".into()))?;
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let depth = args
            .get("depth")
            .and_then(|v| v.as_str())
            .unwrap_or("standard");
        let max_memories = match depth {
            "shallow" => 10usize,
            "deep" => 100,
            _ => 50,
        };

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        let query_lower = query.to_lowercase();
        let query_words: Vec<&str> = query_lower.split_whitespace().collect();

        // Gather relevant memories
        let mut relevant: Vec<(Galaxy, wm_memory::Memory, u32)> = Vec::new(); // (galaxy, memory, match_score)

        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, max_memories)?;
            for mem in mems {
                let content_lower = mem.content.to_lowercase();
                let mut score = 0u32;
                for word in &query_words {
                    if content_lower.contains(word) {
                        score += 1;
                    }
                }
                // Also check tag matches
                for tag in &mem.metadata.tags {
                    if query_words.iter().any(|w| tag.contains(w)) {
                        score += 2;
                    }
                }
                if score > 0 {
                    relevant.push((*galaxy, mem, score));
                }
            }
        }

        // Sort by match score descending, then by importance
        relevant.sort_by(|a, b| {
            b.2.cmp(&a.2).then_with(|| {
                b.1.metadata
                    .importance
                    .partial_cmp(&a.1.metadata.importance)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
        });

        let total_matches = relevant.len();
        let top_memories: Vec<Value> = relevant
            .iter()
            .take(10)
            .map(|(galaxy, mem, score)| {
                json!({
                    "galaxy": galaxy_name(*galaxy),
                    "id": mem.metadata.id,
                    "content_preview": mem.content.chars().take(200).collect::<String>(),
                    "match_score": score,
                    "importance": mem.metadata.importance,
                    "tags": mem.metadata.tags,
                })
            })
            .collect();

        // Extract key themes from matched memories
        let mut theme_tags: std::collections::HashMap<String, u32> =
            std::collections::HashMap::new();
        for (_, mem, _) in &relevant {
            for tag in &mem.metadata.tags {
                *theme_tags.entry(tag.clone()).or_default() += 1;
            }
        }
        let mut themes: Vec<(String, u32)> = theme_tags.into_iter().collect();
        themes.sort_by(|a, b| b.1.cmp(&a.1));
        let key_themes: Vec<String> = themes.iter().take(5).map(|(t, _)| t.clone()).collect();

        // Generate observations
        let mut observations: Vec<String> = Vec::new();
        if total_matches == 0 {
            observations.push(format!(
                "No existing memories match '{query}'. This appears to be a novel topic."
            ));
        } else {
            observations.push(format!(
                "Found {} relevant memories across {} galaxies.",
                total_matches,
                galaxies.len()
            ));
            if !key_themes.is_empty() {
                observations.push(format!("Key themes: {}", key_themes.join(", ")));
            }
            let avg_importance: f32 = relevant
                .iter()
                .map(|(_, m, _)| m.metadata.importance)
                .sum::<f32>()
                / total_matches as f32;
            observations.push(format!(
                "Average importance of matched memories: {avg_importance:.2}"
            ));
            if total_matches > 20 {
                observations
                    .push("High memory density — consider consolidation or synthesis.".into());
            } else if total_matches < 3 {
                observations.push(
                    "Low memory density — this topic may benefit from further exploration.".into(),
                );
            }
        }

        // Generate questions for further inquiry
        let questions: Vec<String> = if total_matches == 0 {
            vec![format!("What existing knowledge relates to '{}'?", query)]
        } else {
            vec![
                format!(
                    "What patterns emerge from these {} memories about '{}'?",
                    total_matches, query
                ),
                "Are there contradictions or gaps in the existing knowledge?".into(),
                "What connections exist between these memories and other topics?".into(),
            ]
        };

        Ok(json!({
            "status": "success",
            "query": query,
            "depth": depth,
            "total_matches": total_matches,
            "key_themes": key_themes,
            "observations": observations,
            "questions": questions,
            "relevant_memories": top_memories,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── explain ──────────────────────────────────────────────────────────

/// Explain a memory or topic by gathering context from related memories.
///
/// Given a memory ID or topic string, finds related memories and produces
/// a structured explanation with context, relationships, and summary.
pub struct ExplainTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ExplainTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

#[async_trait]
#[async_trait]
impl Tool for ExplainTool {
    fn name(&self) -> &str {
        "explain"
    }
    fn gana(&self) -> Gana {
        Gana::ThreeStars
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Explain a memory or topic by gathering context from related memories"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        // Accept either a memory_id or a topic string
        let memory_id = args.get("memory_id").and_then(|v| v.as_str());
        let topic = args.get("topic").and_then(|v| v.as_str());

        if memory_id.is_none() && topic.is_none() {
            return Err(wm_core::CoreError::InvalidArgs(
                "Either memory_id (string) or topic (string) required".into(),
            ));
        }

        let max_context = args
            .get("max_context")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;

        // Find the target memory if memory_id is provided
        let mut target_memory: Option<(Galaxy, wm_memory::Memory)> = None;
        if let Some(id_str) = memory_id {
            let uuid = uuid::Uuid::parse_str(id_str)
                .map_err(|e| wm_core::CoreError::InvalidArgs(format!("Invalid UUID: {e}")))?;
            for galaxy in Galaxy::memory_galaxies() {
                if let Ok(Some(mem)) = self.store.get(galaxy, uuid) {
                    target_memory = Some((galaxy, mem));
                    break;
                }
            }
            if target_memory.is_none() {
                return Err(wm_core::CoreError::NotFound(format!(
                    "Memory {id_str} not found in any galaxy"
                )));
            }
        }

        // Determine search terms from target memory or topic
        let (search_text, target_info): (String, Option<Value>) = match &target_memory {
            Some((galaxy, mem)) => (
                mem.content.clone(),
                Some(json!({
                    "galaxy": galaxy_name(*galaxy),
                    "id": mem.metadata.id,
                    "content": mem.content,
                    "importance": mem.metadata.importance,
                    "tags": mem.metadata.tags,
                    "created_at": mem.metadata.created_at.to_rfc3339(),
                })),
            ),
            None => (topic.unwrap().to_string(), None),
        };

        let search_lower = search_text.to_lowercase();
        let search_words: Vec<&str> = search_lower.split_whitespace().collect();

        // Find related memories
        let mut related: Vec<(Galaxy, wm_memory::Memory, u32)> = Vec::new();
        let target_id = target_memory.as_ref().map(|(_, m)| m.metadata.id);

        for galaxy in Galaxy::all() {
            let mems = self.store.scan(galaxy, 500)?;
            for mem in mems {
                // Skip the target memory itself
                if Some(mem.metadata.id) == target_id {
                    continue;
                }
                let content_lower = mem.content.to_lowercase();
                let mut score = 0u32;
                for word in &search_words {
                    if content_lower.contains(word) {
                        score += 1;
                    }
                }
                // Tag overlap
                if let Some((_, target_mem)) = &target_memory {
                    for tag in &mem.metadata.tags {
                        if target_mem.metadata.tags.contains(tag) {
                            score += 3;
                        }
                    }
                }
                if score > 0 {
                    related.push((galaxy, mem, score));
                }
            }
        }

        related.sort_by(|a, b| b.2.cmp(&a.2));
        let total_related = related.len();

        let context_memories: Vec<Value> = related
            .iter()
            .take(max_context)
            .map(|(galaxy, mem, score)| {
                json!({
                    "galaxy": galaxy_name(*galaxy),
                    "id": mem.metadata.id,
                    "content_preview": mem.content.chars().take(150).collect::<String>(),
                    "relevance_score": score,
                    "tags": mem.metadata.tags,
                })
            })
            .collect();

        // Build explanation summary
        let summary = if total_related == 0 {
            "This memory/topic appears to be isolated with no related memories. Consider creating connections.".into()
        } else {
            let galaxies_involved: std::collections::HashSet<&str> = related
                .iter()
                .take(max_context)
                .map(|(g, _, _)| galaxy_name(*g))
                .collect();
            format!(
                "Found {} related memories across {} galaxies. The topic connects to multiple knowledge areas.",
                total_related,
                galaxies_involved.len()
            )
        };

        Ok(json!({
            "status": "success",
            "target": target_info,
            "topic": topic,
            "total_related": total_related,
            "context_memories": context_memories,
            "summary": summary,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn open_store() -> (tempfile::TempDir, Arc<MemoryStore>) {
        let tmp = tempfile::tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        (tmp, Arc::new(store))
    }

    fn seed_memories(store: &Arc<MemoryStore>) -> Vec<uuid::Uuid> {
        let mut ids = Vec::new();
        let entries = [
            (
                Galaxy::Codex,
                "Rust is a great systems programming language with memory safety",
                vec!["rust", "programming"],
                0.9,
            ),
            (
                Galaxy::Codex,
                "However Rust has a steep learning curve for beginners",
                vec!["rust", "programming"],
                0.6,
            ),
            (
                Galaxy::Research,
                "Python is excellent for data science and rapid prototyping",
                vec!["python", "data"],
                0.8,
            ),
            (
                Galaxy::Research,
                "But Python performance is a problem for compute-intensive tasks",
                vec!["python", "performance"],
                0.5,
            ),
            (
                Galaxy::Codex,
                "Rust ownership model prevents memory leaks at compile time",
                vec!["rust", "memory"],
                0.85,
            ),
            (
                Galaxy::Tutorial,
                "Rust traits enable polymorphism without runtime overhead",
                vec!["rust", "traits"],
                0.7,
            ),
        ];

        for (galaxy, content, tags, imp) in entries {
            let mut mem = wm_memory::Memory::new(galaxy, content.into());
            mem.metadata.tags = tags.iter().map(std::string::ToString::to_string).collect();
            mem.metadata.importance = imp;
            ids.push(mem.metadata.id);
            store.put(galaxy, &mem).unwrap();
        }
        ids
    }

    #[tokio::test]
    async fn bicameral_finds_supporting_and_opposing() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ReasoningBicameralTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"topic": "rust"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_evidence"].as_u64().unwrap() >= 4);
        let supporting = obj["supporting"].as_array().unwrap();
        let opposing = obj["opposing"].as_array().unwrap();
        assert!(!supporting.is_empty() || !opposing.is_empty());
        assert!(obj["synthesis"].as_str().unwrap().contains("rust"));
    }

    #[tokio::test]
    async fn bicameral_no_matches() {
        let (_tmp, store) = open_store();
        let tool = ReasoningBicameralTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"topic": "nonexistent"}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_evidence"], 0);
        assert!(obj["synthesis"].as_str().unwrap().contains("No memories"));
    }

    #[tokio::test]
    async fn bicameral_missing_topic() {
        let (_tmp, store) = open_store();
        let tool = ReasoningBicameralTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn think_gathers_context() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ThinkTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"query": "rust programming", "depth": "standard"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_matches"].as_u64().unwrap() >= 4);
        let themes = obj["key_themes"].as_array().unwrap();
        assert!(!themes.is_empty());
        let observations = obj["observations"].as_array().unwrap();
        assert!(!observations.is_empty());
        let questions = obj["questions"].as_array().unwrap();
        assert!(!questions.is_empty());
    }

    #[tokio::test]
    async fn think_shallow_depth() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ThinkTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"query": "rust", "depth": "shallow"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["depth"], "shallow");
    }

    #[tokio::test]
    async fn think_missing_query() {
        let (_tmp, store) = open_store();
        let tool = ThinkTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn explain_by_memory_id() {
        let (_tmp, store) = open_store();
        let ids = seed_memories(&store);

        let tool = ExplainTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"memory_id": ids[0].to_string()}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["target"].is_object());
        assert!(obj["total_related"].as_u64().unwrap() >= 3);
        assert!(
            obj["summary"]
                .as_str()
                .unwrap()
                .contains("related memories")
        );
    }

    #[tokio::test]
    async fn explain_by_topic() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ExplainTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"topic": "rust memory safety"}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_related"].as_u64().unwrap() >= 2);
    }

    #[tokio::test]
    async fn explain_missing_args() {
        let (_tmp, store) = open_store();
        let tool = ExplainTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn explain_invalid_uuid() {
        let (_tmp, store) = open_store();
        let tool = ExplainTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"memory_id": "not-a-uuid"}))
            .await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn explain_not_found() {
        let (_tmp, store) = open_store();
        let tool = ExplainTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"memory_id": "00000000-0000-0000-0000-000000000000"}),
            )
            .await;
        assert!(result.is_err());
    }
}
