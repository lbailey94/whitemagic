//! Anti-loop & boundary tools — anti_loop.check, boundary.enforce.
//!
//! Gana::Wall — "Loop prevention, boundary enforcement, safety checks"
//!
//! `anti_loop.check` detects repetitive patterns in tool calls or memory
//! creation that may indicate infinite loops or stuck states.
//! `boundary.enforce` validates that operations stay within defined
//! resource limits (memory count, galaxy size, tag sprawl).

#![forbid(unsafe_code)]

use serde_json::{Value, json};
use std::collections::HashMap;
use std::sync::Arc;
use wm_core::{Context, EffectRow, Galaxy, Gana, Resource, Tool, ToolStats};
use wm_memory::MemoryStore;

use super::common::galaxy_name;

// ── anti_loop.check ──────────────────────────────────────────────────

/// Detect repetitive patterns that may indicate loops or stuck states.
///
/// Analyzes recent memories for:
/// - Duplicate content (exact or near-duplicate)
/// - Repetitive tag patterns
/// - Burst creation patterns (many memories in short time)
/// - Content similarity clusters
pub struct AntiLoopCheckTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl AntiLoopCheckTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

impl Tool for AntiLoopCheckTool {
    fn name(&self) -> &str {
        "anti_loop.check"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Detect repetitive patterns indicating loops or stuck states"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let galaxy_str = args.get("galaxy").and_then(|v| v.as_str());
        let scan_limit = args
            .get("scan_limit")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(200) as usize;
        let similarity_threshold = args
            .get("similarity_threshold")
            .and_then(serde_json::Value::as_f64)
            .unwrap_or(0.8) as f32;

        let galaxies: Vec<Galaxy> = match galaxy_str {
            Some(g) => vec![super::common::parse_galaxy(g)?],
            None => Galaxy::memory_galaxies().to_vec(),
        };

        let mut all_mems: Vec<(Galaxy, wm_memory::Memory)> = Vec::new();
        for galaxy in &galaxies {
            let mems = self.store.scan(*galaxy, scan_limit)?;
            all_mems.extend(mems.into_iter().map(|m| (*galaxy, m)));
        }

        if all_mems.is_empty() {
            return Ok(json!({
                "status": "success",
                "total_memories": 0,
                "loop_detected": false,
                "warnings": [],
            }));
        }

        // Sort by created_at descending (most recent first)
        all_mems.sort_by(|a, b| b.1.metadata.created_at.cmp(&a.1.metadata.created_at));

        let mut warnings: Vec<Value> = Vec::new();

        // 1. Check for exact duplicates
        let mut content_map: HashMap<String, u32> = HashMap::new();
        for (_, mem) in &all_mems {
            *content_map.entry(mem.content.clone()).or_default() += 1;
        }
        for (content, count) in &content_map {
            if *count > 1 {
                warnings.push(json!({
                    "type": "exact_duplicate",
                    "content_preview": content.chars().take(80).collect::<String>(),
                    "count": count,
                    "severity": if *count > 3 { "high" } else { "medium" },
                }));
            }
        }

        // 2. Check for near-duplicates (content prefix similarity)
        let recent: Vec<&(Galaxy, wm_memory::Memory)> = all_mems.iter().take(50).collect();
        for i in 0..recent.len() {
            for j in (i + 1)..recent.len().min(i + 10) {
                let a = &recent[i].1.content;
                let b = &recent[j].1.content;
                let similarity = content_similarity(a, b);
                if similarity > similarity_threshold && a != b {
                    warnings.push(json!({
                        "type": "near_duplicate",
                        "similarity": (similarity * 100.0).round() / 100.0,
                        "memory_a": recent[i].1.metadata.id,
                        "memory_b": recent[j].1.metadata.id,
                        "content_preview": a.chars().take(60).collect::<String>(),
                        "severity": "medium",
                    }));
                }
            }
        }

        // 3. Check for burst creation (many memories within short time)
        if all_mems.len() >= 10 {
            let recent_10 = &all_mems[..10];
            if let (Some(first), Some(last)) = (recent_10.last(), recent_10.first()) {
                let duration = last.1.metadata.created_at - first.1.metadata.created_at;
                if duration.num_seconds() < 60 {
                    warnings.push(json!({
                        "type": "burst_creation",
                        "memories_in_burst": 10,
                        "duration_seconds": duration.num_seconds(),
                        "severity": "high",
                        "message": "10+ memories created within 60 seconds — possible loop",
                    }));
                }
            }
        }

        // 4. Check for repetitive tag patterns
        let mut tag_pattern_count: HashMap<Vec<String>, u32> = HashMap::new();
        for (_, mem) in &all_mems {
            let mut tags = mem.metadata.tags.clone();
            tags.sort();
            *tag_pattern_count.entry(tags).or_default() += 1;
        }
        for (tags, count) in &tag_pattern_count {
            if *count > 5 {
                warnings.push(json!({
                    "type": "repetitive_tags",
                    "tags": tags,
                    "count": count,
                    "severity": if *count > 10 { "high" } else { "medium" },
                }));
            }
        }

        let loop_detected = warnings
            .iter()
            .any(|w| w["severity"].as_str().is_some_and(|s| s == "high"));

        Ok(json!({
            "status": "success",
            "total_memories": all_mems.len(),
            "galaxies_checked": galaxies.len(),
            "loop_detected": loop_detected,
            "warning_count": warnings.len(),
            "warnings": warnings,
        }))
    }
    fn stats(&self) -> &ToolStats {
        &self.stats
    }
}

/// Compute simple content similarity based on character-level Jaccard on n-grams.
fn content_similarity(a: &str, b: &str) -> f32 {
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    let ngrams_a: std::collections::HashSet<&str> = a
        .as_bytes()
        .windows(3)
        .map(|w| std::str::from_utf8(w).unwrap_or(""))
        .collect();
    let ngrams_b: std::collections::HashSet<&str> = b
        .as_bytes()
        .windows(3)
        .map(|w| std::str::from_utf8(w).unwrap_or(""))
        .collect();
    let intersection = ngrams_a.intersection(&ngrams_b).count();
    let union = ngrams_a.union(&ngrams_b).count();
    if union == 0 {
        0.0
    } else {
        intersection as f32 / union as f32
    }
}

// ── boundary.enforce ─────────────────────────────────────────────────

/// Enforce resource boundaries and report violations.
///
/// Checks galaxy memory counts, tag sprawl, and content size against
/// configurable limits. Returns violations and recommendations.
pub struct BoundaryEnforceTool {
    store: Arc<MemoryStore>,
    stats: ToolStats,
    effects: EffectRow,
}

impl BoundaryEnforceTool {
    pub fn new(store: Arc<MemoryStore>) -> Self {
        Self {
            store,
            stats: ToolStats::default(),
            effects: EffectRow::read_only(vec![Resource::Galaxy("universal".into())]),
        }
    }
}

impl Tool for BoundaryEnforceTool {
    fn name(&self) -> &str {
        "boundary.enforce"
    }
    fn gana(&self) -> Gana {
        Gana::Wall
    }
    fn effects(&self) -> &EffectRow {
        &self.effects
    }
    fn description(&self) -> &str {
        "Enforce resource boundaries and report violations"
    }
    fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let max_memories_per_galaxy = args
            .get("max_memories_per_galaxy")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10000);
        let max_tag_sprawl = args
            .get("max_tag_sprawl")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(100);
        let max_content_length = args
            .get("max_content_length")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(10000) as usize;
        let max_tags_per_memory = args
            .get("max_tags_per_memory")
            .and_then(serde_json::Value::as_u64)
            .unwrap_or(20) as usize;

        let mut violations: Vec<Value> = Vec::new();
        let mut galaxy_reports: Vec<Value> = Vec::new();
        let mut total_memories = 0u64;
        let mut total_tags: std::collections::HashSet<String> = std::collections::HashSet::new();

        for galaxy in Galaxy::memory_galaxies() {
            let mems = self.store.scan(galaxy, 100000)?;
            let count = mems.len() as u64;
            total_memories += count;

            let mut galaxy_tags: std::collections::HashSet<String> =
                std::collections::HashSet::new();
            let mut oversized_count = 0u64;
            let mut overtagged_count = 0u64;

            for mem in &mems {
                for tag in &mem.metadata.tags {
                    galaxy_tags.insert(tag.clone());
                    total_tags.insert(tag.clone());
                }
                if mem.content.len() > max_content_length {
                    oversized_count += 1;
                }
                if mem.metadata.tags.len() > max_tags_per_memory {
                    overtagged_count += 1;
                }
            }

            // Check galaxy memory limit
            if count > max_memories_per_galaxy {
                violations.push(json!({
                    "type": "galaxy_overflow",
                    "galaxy": galaxy_name(galaxy),
                    "count": count,
                    "limit": max_memories_per_galaxy,
                    "severity": "high",
                    "recommendation": format!("Galaxy '{}' has {} memories (limit: {}) — consider consolidation or pruning", galaxy_name(galaxy), count, max_memories_per_galaxy),
                }));
            }

            // Check oversized memories
            if oversized_count > 0 {
                violations.push(json!({
                    "type": "oversized_memories",
                    "galaxy": galaxy_name(galaxy),
                    "count": oversized_count,
                    "max_length": max_content_length,
                    "severity": "medium",
                    "recommendation": format!("{} memories in '{}' exceed max content length ({})", oversized_count, galaxy_name(galaxy), max_content_length),
                }));
            }

            // Check over-tagged memories
            if overtagged_count > 0 {
                violations.push(json!({
                    "type": "overtagged_memories",
                    "galaxy": galaxy_name(galaxy),
                    "count": overtagged_count,
                    "max_tags": max_tags_per_memory,
                    "severity": "low",
                }));
            }

            galaxy_reports.push(json!({
                "galaxy": galaxy_name(galaxy),
                "count": count,
                "unique_tags": galaxy_tags.len(),
                "oversized": oversized_count,
                "overtagged": overtagged_count,
            }));
        }

        // Check global tag sprawl
        if total_tags.len() as u64 > max_tag_sprawl {
            violations.push(json!({
                "type": "tag_sprawl",
                "total_unique_tags": total_tags.len(),
                "limit": max_tag_sprawl,
                "severity": "medium",
                "recommendation": format!("{} unique tags across all galaxies (limit: {}) — consider tag consolidation", total_tags.len(), max_tag_sprawl),
            }));
        }

        let all_clear = violations.is_empty();

        Ok(json!({
            "status": "success",
            "all_clear": all_clear,
            "total_memories": total_memories,
            "total_unique_tags": total_tags.len(),
            "violation_count": violations.len(),
            "violations": violations,
            "galaxy_reports": galaxy_reports,
            "limits": {
                "max_memories_per_galaxy": max_memories_per_galaxy,
                "max_tag_sprawl": max_tag_sprawl,
                "max_content_length": max_content_length,
                "max_tags_per_memory": max_tags_per_memory,
            },
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

    fn seed_normal(store: &Arc<MemoryStore>) {
        for i in 0..5 {
            let mut mem =
                wm_memory::Memory::new(Galaxy::Codex, format!("Unique memory content number {i}"));
            mem.metadata.tags = vec!["tag1".into(), "tag2".into()];
            mem.metadata.importance = 0.5;
            store.put(Galaxy::Codex, &mem).unwrap();
        }
    }

    fn seed_duplicates(store: &Arc<MemoryStore>) {
        for _ in 0..4 {
            let mut mem =
                wm_memory::Memory::new(Galaxy::Codex, "Duplicate content same text".into());
            mem.metadata.tags = vec!["dup".into()];
            store.put(Galaxy::Codex, &mem).unwrap();
        }
    }

    #[test]
    fn anti_loop_detects_exact_duplicates() {
        let (_tmp, store) = open_store();
        seed_duplicates(&store);

        let tool = AntiLoopCheckTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        let warnings = obj["warnings"].as_array().unwrap();
        let has_dup = warnings.iter().any(|w| w["type"] == "exact_duplicate");
        assert!(has_dup, "Should detect exact duplicates");
    }

    #[test]
    fn anti_loop_no_issues() {
        let (_tmp, store) = open_store();
        seed_normal(&store);

        let tool = AntiLoopCheckTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["loop_detected"], false);
    }

    #[test]
    fn anti_loop_empty_store() {
        let (_tmp, store) = open_store();
        let tool = AntiLoopCheckTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["total_memories"], 0);
        assert_eq!(obj["loop_detected"], false);
    }

    #[test]
    fn anti_loop_detects_near_duplicates() {
        let (_tmp, store) = open_store();
        let mut mem1 =
            wm_memory::Memory::new(Galaxy::Codex, "Rust programming language features".into());
        mem1.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &mem1).unwrap();
        let mut mem2 =
            wm_memory::Memory::new(Galaxy::Codex, "Rust programming language basics".into());
        mem2.metadata.importance = 0.8;
        store.put(Galaxy::Codex, &mem2).unwrap();

        let tool = AntiLoopCheckTool::new(store);
        let result = tool
            .call(
                &mut Context::default(),
                json!({"similarity_threshold": 0.5}),
            )
            .unwrap();
        let obj = result.as_object().unwrap();
        let warnings = obj["warnings"].as_array().unwrap();
        let has_near = warnings.iter().any(|w| w["type"] == "near_duplicate");
        assert!(has_near, "Should detect near-duplicates");
    }

    #[test]
    fn boundary_enforce_all_clear() {
        let (_tmp, store) = open_store();
        seed_normal(&store);

        let tool = BoundaryEnforceTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["status"], "success");
        assert_eq!(obj["all_clear"], true);
        assert_eq!(obj["violation_count"], 0);
    }

    #[test]
    fn boundary_enforce_detects_oversized() {
        let (_tmp, store) = open_store();
        let mut mem = wm_memory::Memory::new(Galaxy::Codex, "A".repeat(100));
        mem.metadata.importance = 0.5;
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = BoundaryEnforceTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"max_content_length": 50}))
            .unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["all_clear"], false);
        let violations = obj["violations"].as_array().unwrap();
        let has_oversized = violations.iter().any(|v| v["type"] == "oversized_memories");
        assert!(has_oversized, "Should detect oversized memories");
    }

    #[test]
    fn boundary_enforce_detects_overtagged() {
        let (_tmp, store) = open_store();
        let mut mem = wm_memory::Memory::new(Galaxy::Codex, "Test memory".into());
        mem.metadata.tags = (0..25).map(|i| format!("tag{i}")).collect();
        store.put(Galaxy::Codex, &mem).unwrap();

        let tool = BoundaryEnforceTool::new(store);
        let result = tool
            .call(&mut Context::default(), json!({"max_tags_per_memory": 20}))
            .unwrap();
        let obj = result.as_object().unwrap();
        let violations = obj["violations"].as_array().unwrap();
        let has_overtagged = violations
            .iter()
            .any(|v| v["type"] == "overtagged_memories");
        assert!(has_overtagged, "Should detect over-tagged memories");
    }

    #[test]
    fn boundary_enforce_empty_store() {
        let (_tmp, store) = open_store();
        let tool = BoundaryEnforceTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        assert_eq!(obj["all_clear"], true);
        assert_eq!(obj["total_memories"], 0);
    }

    #[test]
    fn boundary_enforce_galaxy_reports() {
        let (_tmp, store) = open_store();
        seed_normal(&store);

        let tool = BoundaryEnforceTool::new(store);
        let result = tool.call(&mut Context::default(), json!({})).unwrap();
        let obj = result.as_object().unwrap();
        let reports = obj["galaxy_reports"].as_array().unwrap();
        let codex = reports.iter().find(|r| r["galaxy"] == "codex");
        assert!(codex.is_some());
        assert_eq!(codex.unwrap()["count"], 5);
    }
}
