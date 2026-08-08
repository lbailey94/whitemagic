//! Archaeology & learning tools — archaeology.search, learning.pattern, learning.suggest.
//!
//! Gana::Ox — "Archaeology search, learning, pattern learning"
//!
//! These tools excavate memory layers for patterns, recurring themes,
//! and learning suggestions based on access history and importance decay.

#![forbid(unsafe_code)]

use async_trait::async_trait;

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::{galaxy_name, parse_galaxy};

// ── archaeology.search ───────────────────────────────────────────────

/// Excavate memories by time depth, importance layer, and content patterns.
///
/// Unlike `memory.search` (BM25 keyword match) or `pattern.search` (substring
/// match), `archaeology.search` stratifies memories by age and importance,
/// returning layers that reveal how knowledge evolved over time.
pub struct ArchaeologySearchTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl ArchaeologySearchTool {
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
impl Tool for ArchaeologySearchTool {
    fn name(&self) -> &str {
        "archaeology.search"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Excavate memory layers by time depth and importance stratification"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let keyword = args.get("keyword").and_then(|v| v.as_str()).unwrap_or("");
        let max_layers = args
            .get("max_layers")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(5) as usize;
        let memories_per_layer = args
            .get("memories_per_layer")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(5) as usize;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        // Collect all matching memories
        let mut all_mems: Vec<(Galaxy, wm_memory::Memory)> = Vec::new();
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, 1000)?;
            for mem in mems {
                if keyword.is_empty()
                    || mem.content.to_lowercase().contains(&keyword.to_lowercase())
                {
                    all_mems.push((*galaxy, mem));
                }
            }
        }

        if all_mems.is_empty() {
            return Ok(json!({
                "status": "success",
                "total_memories": 0,
                "layers": [],
            }));
        }

        // Sort by created_at descending (newest first)
        all_mems.sort_by(|a, b| b.1.metadata.created_at.cmp(&a.1.metadata.created_at));

        // Stratify into time layers
        let total = all_mems.len();
        let layer_size = (total / max_layers).max(1);
        let mut layers: Vec<Value> = Vec::new();

        for (layer_idx, chunk) in all_mems.chunks(layer_size).enumerate().take(max_layers) {
            let layer_mems: Vec<Value> = chunk
                .iter()
                .take(memories_per_layer)
                .map(|(galaxy, mem)| {
                    json!({
                        "galaxy": galaxy_name(*galaxy),
                        "id": mem.metadata.id,
                        "content_preview": mem.content.chars().take(120).collect::<String>(),
                        "importance": mem.metadata.importance,
                        "created_at": mem.metadata.created_at.to_rfc3339(),
                        "tags": mem.metadata.tags,
                    })
                })
                .collect();

            let avg_importance: f32 = if chunk.is_empty() {
                0.0
            } else {
                chunk
                    .iter()
                    .map(|(_, m)| m.metadata.importance)
                    .sum::<f32>()
                    / chunk.len() as f32
            };

            layers.push(json!({
                "layer": layer_idx,
                "depth": if layer_idx == 0 { "newest" } else if layer_idx == max_layers - 1 { "oldest" } else { "middle" },
                "count": chunk.len(),
                "avg_importance": (avg_importance * 100.0).round() / 100.0,
                "memories": layer_mems,
            }));
        }

        Ok(json!({
            "status": "success",
            "total_memories": total,
            "galaxies_searched": galaxies.len(),
            "keyword": keyword,
            "layers": layers,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── learning.pattern ─────────────────────────────────────────────────

/// Detect recurring patterns in memory content across galaxies.
///
/// Analyzes tag co-occurrence and content keyword frequency to identify
/// recurring themes and learning patterns. Returns ranked patterns with
/// supporting memory references.
pub struct LearningPatternTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl LearningPatternTool {
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
impl Tool for LearningPatternTool {
    fn name(&self) -> &str {
        "learning.pattern"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect recurring patterns and themes across memory galaxies"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let min_frequency = args
            .get("min_frequency")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(2) as usize;
        let top_n = args
            .get("top_n")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;
        let scan_limit = args
            .get("scan_limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(500) as usize;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        // Track tag co-occurrence and keyword frequency
        let mut tag_pairs: HashMap<(String, String), u32> = HashMap::new();
        let mut keyword_freq: HashMap<String, u32> = HashMap::new();
        let mut total_memories = 0usize;

        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            for mem in &mems {
                total_memories += 1;
                // Tag co-occurrence
                let tags = &mem.metadata.tags;
                for i in 0..tags.len() {
                    for j in (i + 1)..tags.len() {
                        let pair = if tags[i] < tags[j] {
                            (tags[i].clone(), tags[j].clone())
                        } else {
                            (tags[j].clone(), tags[i].clone())
                        };
                        *tag_pairs.entry(pair).or_default() += 1;
                    }
                }
                // Keyword frequency (simple word tokenization)
                for word in mem.content.split_whitespace() {
                    let w = word
                        .trim_matches(|c: char| !c.is_alphanumeric())
                        .to_lowercase();
                    if w.len() > 3 {
                        *keyword_freq.entry(w).or_default() += 1;
                    }
                }
            }
        }

        // Filter and rank tag co-occurrences
        let mut tag_patterns: Vec<Value> = tag_pairs
            .iter()
            .filter(|&(_, count)| *count >= min_frequency as u32)
            .map(|((t1, t2), count)| {
                json!({
                    "tags": [t1, t2],
                    "co_occurrence": count,
                })
            })
            .collect();
        tag_patterns.sort_by(|a, b| {
            b["co_occurrence"]
                .as_u64()
                .cmp(&a["co_occurrence"].as_u64())
        });
        tag_patterns.truncate(top_n);

        // Filter and rank keywords
        let mut keywords: Vec<(String, u32)> = keyword_freq
            .into_iter()
            .filter(|(_, count)| *count >= min_frequency as u32)
            .collect();
        keywords.sort_by(|a, b| b.1.cmp(&a.1));
        keywords.truncate(top_n);

        let keyword_patterns: Vec<Value> = keywords
            .into_iter()
            .map(|(word, count)| {
                json!({
                    "keyword": word,
                    "frequency": count,
                })
            })
            .collect();

        Ok(json!({
            "status": "success",
            "total_memories": total_memories,
            "galaxies_scanned": galaxies.len(),
            "tag_patterns": tag_patterns,
            "keyword_patterns": keyword_patterns,
            "min_frequency": min_frequency,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

// ── learning.suggest ─────────────────────────────────────────────────

/// Suggest learning paths based on memory gaps and importance clusters.
///
/// Analyzes which topics have high importance but low memory count (gaps)
/// and which have high memory count but low importance (saturation).
/// Returns suggestions for what to learn next.
pub struct LearningSuggestTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl LearningSuggestTool {
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
impl Tool for LearningSuggestTool {
    fn name(&self) -> &str {
        "learning.suggest"
    }
    fn gana(&self) -> Gana {
        Gana::Ox
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Suggest learning paths based on memory gaps and importance clusters"
    }
    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let top_n = args
            .get("top_n")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10) as usize;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![parse_galaxy(g)?],
            None => vec![Galaxy::Codex, Galaxy::Research, Galaxy::Tutorial],
        };

        // Aggregate by tag: count, avg importance, total access
        let mut tag_stats: HashMap<String, (u32, f32, u64)> = HashMap::new(); // (count, avg_importance, total_access)

        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, 1000)?;
            for mem in &mems {
                for tag in &mem.metadata.tags {
                    let entry = tag_stats.entry(tag.clone()).or_insert((0, 0.0, 0));
                    entry.0 += 1;
                    entry.1 += mem.metadata.importance;
                    entry.2 += mem.metadata.access_count;
                }
            }
        }

        // Finalize averages
        let mut tag_data: Vec<(String, u32, f32, u64)> = tag_stats
            .into_iter()
            .map(|(tag, (count, imp_sum, access))| (tag, count, imp_sum / count as f32, access))
            .collect();

        // Gaps: high importance, low count → worth exploring
        let mut gaps: Vec<Value> = tag_data
            .iter()
            .filter(|(_, count, imp, _)| *count <= 3 && *imp > 0.5)
            .map(|(tag, count, imp, access)| {
                json!({
                    "tag": tag,
                    "memory_count": count,
                    "avg_importance": (imp * 100.0).round() / 100.0,
                    "total_access": access,
                    "suggestion": format!("Topic '{}' has high importance but few memories — consider exploring further", tag),
                })
            })
            .collect();
        gaps.sort_by(|a, b| {
            b["avg_importance"]
                .as_f64()
                .partial_cmp(&a["avg_importance"].as_f64())
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        gaps.truncate(top_n);

        // Saturated: high count, low importance → already well-covered
        let mut saturated: Vec<Value> = tag_data
            .iter()
            .filter(|(_, count, imp, _)| *count >= 10 && *imp < 0.4)
            .map(|(tag, count, imp, access)| {
                json!({
                    "tag": tag,
                    "memory_count": count,
                    "avg_importance": (imp * 100.0).round() / 100.0,
                    "total_access": access,
                    "suggestion": format!("Topic '{}' is well-covered with {} memories — consider synthesizing or consolidating", tag, count),
                })
            })
            .collect();
        saturated.sort_by(|a, b| b["memory_count"].as_u64().cmp(&a["memory_count"].as_u64()));
        saturated.truncate(top_n);

        // Hot topics: high count + high importance
        let mut hot: Vec<Value> = tag_data
            .iter()
            .filter(|(_, count, imp, _)| *count >= 5 && *imp > 0.6)
            .map(|(tag, count, imp, access)| {
                json!({
                    "tag": tag,
                    "memory_count": count,
                    "avg_importance": (imp * 100.0).round() / 100.0,
                    "total_access": access,
                })
            })
            .collect();
        hot.sort_by(|a, b| {
            b["avg_importance"]
                .as_f64()
                .partial_cmp(&a["avg_importance"].as_f64())
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        hot.truncate(top_n);

        // Clean up tag_data to avoid clippy warning
        tag_data.clear();

        Ok(json!({
            "status": "success",
            "galaxies_scanned": galaxies.len(),
            "gaps": gaps,
            "saturated": saturated,
            "hot_topics": hot,
            "suggestion_count": gaps.len() + saturated.len(),
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

    fn seed_memories(store: &Arc<MemoryStore>) {
        let galaxies = [Galaxy::Codex, Galaxy::Research, Galaxy::Tutorial];
        let contents = [
            "Rust programming language features and memory safety",
            "Rust ownership model and borrow checker rules",
            "Python async programming with asyncio library",
            "Machine learning fundamentals and neural networks",
            "Quantum computing principles and qubit operations",
            "Database design patterns for scalable systems",
            "Rust trait system and generic constraints",
            "Python data science with pandas and numpy",
        ];
        let tags_sets: Vec<Vec<String>> = vec![
            vec!["rust".into(), "programming".into()],
            vec!["rust".into(), "programming".into(), "memory".into()],
            vec!["python".into(), "programming".into(), "async".into()],
            vec!["ml".into(), "neural".into()],
            vec!["quantum".into(), "physics".into()],
            vec!["database".into(), "design".into()],
            vec!["rust".into(), "programming".into(), "traits".into()],
            vec!["python".into(), "data".into()],
        ];
        let importances = [0.9, 0.8, 0.5, 0.7, 0.6, 0.4, 0.85, 0.3];

        for i in 0..8 {
            let galaxy = galaxies[i % 3];
            let mut mem = wm_memory::Memory::new(galaxy, contents[i].into());
            mem.metadata.tags = tags_sets[i].clone();
            mem.metadata.importance = importances[i];
            store.put(galaxy, &mem).unwrap();
        }
    }

    #[tokio::test]
    async fn archaeology_search_returns_layers() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ArchaeologySearchTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"max_layers": 3}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_memories"].as_u64().unwrap() >= 8);
        let layers = obj["layers"].as_array().unwrap();
        assert!(!layers.is_empty());
        assert!(layers.len() <= 3);
    }

    #[tokio::test]
    async fn archaeology_search_with_keyword() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = ArchaeologySearchTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"keyword": "rust", "max_layers": 2}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_memories"].as_u64().unwrap() >= 3);
    }

    #[tokio::test]
    async fn archaeology_search_empty_galaxy() {
        let (_tmp, store) = open_store();
        let tool = ArchaeologySearchTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["total_memories"], 0);
    }

    #[tokio::test]
    async fn learning_pattern_detects_tag_co_occurrence() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = LearningPatternTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"min_frequency": 2, "top_n": 10}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert!(obj["total_memories"].as_u64().unwrap() >= 8);
        // "rust" appears in 3 memories, "python" in 2
        let tag_patterns = obj["tag_patterns"].as_array().unwrap();
        assert!(!tag_patterns.is_empty());
    }

    #[tokio::test]
    async fn learning_pattern_detects_keywords() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = LearningPatternTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"min_frequency": 2, "top_n": 5}),
            )
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        let keywords = obj["keyword_patterns"].as_array().unwrap();
        assert!(!keywords.is_empty());
        // "rust" should appear as a frequent keyword
        let has_rust = keywords
            .iter()
            .any(|k| k["keyword"].as_str().unwrap_or("") == "rust");
        assert!(has_rust, "Expected 'rust' in keyword patterns");
    }

    #[tokio::test]
    async fn learning_suggest_finds_gaps_and_hot_topics() {
        let (_tmp, store) = open_store();
        seed_memories(&store);

        let tool = LearningSuggestTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"top_n": 5}))
            .await
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        // Should have some suggestions
        let gaps = obj["gaps"].as_array().unwrap();
        let hot = obj["hot_topics"].as_array().unwrap();
        // "rust" has 3 memories with high importance → should be in hot or gaps
        assert!(!gaps.is_empty() || !hot.is_empty());
    }

    #[tokio::test]
    async fn learning_suggest_empty_store() {
        let (_tmp, store) = open_store();
        let tool = LearningSuggestTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).await.unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["gaps"].as_array().unwrap().len(), 0);
        assert_eq!(obj["hot_topics"].as_array().unwrap().len(), 0);
    }
}
