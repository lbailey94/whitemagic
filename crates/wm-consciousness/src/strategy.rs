//! Strategy synthesis — cluster memories and generate meta-insights.
//!
//! Phase 6.5: Upgrades the dream cycle from duplicate-merging to
//! meta-insight generation. Clusters memories by tag overlap and
//! association overlap, identifies high-value clusters, and synthesizes
//! compressed "strategy memories" promoted to the Codex galaxy with
//! `MemoryType::Pattern`.

use std::collections::{HashMap, HashSet};
use wm_core::{Galaxy, Result};
use wm_memory::{AssociationStore, Memory, MemoryStore, MemoryType};

/// Configuration for strategy synthesis.
#[derive(Debug, Clone)]
pub struct StrategyConfig {
    /// Minimum cluster size to be considered for synthesis
    pub min_cluster_size: usize,
    /// Minimum average importance for a cluster to be "high-value"
    pub min_avg_importance: f32,
    /// Tag Jaccard similarity threshold for clustering
    pub tag_similarity_threshold: f32,
    /// Maximum number of strategy memories to synthesize per run
    pub max_strategies: usize,
}

impl Default for StrategyConfig {
    fn default() -> Self {
        Self {
            min_cluster_size: 3,
            min_avg_importance: 0.5,
            tag_similarity_threshold: 0.3,
            max_strategies: 10,
        }
    }
}

/// A cluster of related memories.
#[derive(Debug, Clone)]
pub struct MemoryCluster {
    /// Memory IDs in the cluster
    pub memory_ids: Vec<uuid::Uuid>,
    /// Shared tags across cluster members
    pub shared_tags: Vec<String>,
    /// Average importance of cluster members
    pub avg_importance: f32,
    /// Average neuro_score of cluster members
    pub avg_neuro_score: f32,
    /// Galaxies represented in the cluster
    pub galaxies: HashSet<Galaxy>,
    /// Dominant theme (most frequent tag or synthesized label)
    pub theme: String,
}

/// Result of a strategy synthesis run.
#[derive(Debug, Clone)]
pub struct SynthesisReport {
    /// Number of memories analyzed
    pub memories_analyzed: usize,
    /// Number of clusters identified
    pub clusters_found: usize,
    /// Number of strategy memories synthesized
    pub strategies_synthesized: usize,
    /// IDs of synthesized strategy memories
    pub strategy_ids: Vec<uuid::Uuid>,
    /// Cluster themes discovered
    pub themes: Vec<String>,
}

impl SynthesisReport {
    /// Create a new empty report.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            memories_analyzed: 0,
            clusters_found: 0,
            strategies_synthesized: 0,
            strategy_ids: Vec::new(),
            themes: Vec::new(),
        }
    }
}

impl Default for SynthesisReport {
    fn default() -> Self {
        Self::new()
    }
}

/// Strategy synthesizer — clusters memories and generates meta-insight memories.
pub struct StrategySynthesizer {
    config: StrategyConfig,
}

impl Default for StrategySynthesizer {
    fn default() -> Self {
        Self::new(StrategyConfig::default())
    }
}

impl StrategySynthesizer {
    /// Create a new synthesizer with the given config.
    #[must_use]
    pub const fn new(config: StrategyConfig) -> Self {
        Self { config }
    }

    /// Run strategy synthesis across all non-system galaxies.
    ///
    /// 1. Collect memories from all content galaxies
    /// 2. Cluster by tag overlap (Jaccard similarity)
    /// 3. Filter clusters by size and average importance
    /// 4. Synthesize compressed strategy memories
    /// 5. Promote to Codex galaxy with `MemoryType::Pattern`
    pub fn synthesize(
        &self,
        store: &MemoryStore,
        _associations: &AssociationStore,
    ) -> Result<SynthesisReport> {
        let mut report = SynthesisReport::new();

        // 1. Collect memories from all non-system galaxies
        let mut all_mems: Vec<(Galaxy, Memory)> = Vec::new();
        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            let mems = store.scan(galaxy, 10_000)?;
            for mem in mems {
                all_mems.push((galaxy, mem));
            }
        }
        report.memories_analyzed = all_mems.len();

        if all_mems.len() < self.config.min_cluster_size {
            return Ok(report);
        }

        // 2. Cluster by tag overlap
        let clusters = self.cluster_by_tags(&all_mems);
        report.clusters_found = clusters.len();

        // 3. Filter and 4. Synthesize
        let mut strategies_created = 0;
        for cluster in &clusters {
            if strategies_created >= self.config.max_strategies {
                break;
            }
            if cluster.memory_ids.len() < self.config.min_cluster_size {
                continue;
            }
            if cluster.avg_importance < self.config.min_avg_importance {
                continue;
            }

            // Synthesize a strategy memory
            let strategy_mem = self.synthesize_strategy_memory(cluster, &all_mems);
            report.themes.push(cluster.theme.clone());

            // Promote to Codex with Pattern type
            let strategy_id = strategy_mem.metadata.id;
            if store.put(Galaxy::Codex, &strategy_mem).is_ok() {
                report.strategy_ids.push(strategy_id);
                strategies_created += 1;
            }
        }
        report.strategies_synthesized = strategies_created;

        Ok(report)
    }

    /// Cluster memories by tag overlap using Jaccard similarity.
    fn cluster_by_tags(&self, mems: &[(Galaxy, Memory)]) -> Vec<MemoryCluster> {
        // Build tag sets
        let tag_sets: Vec<HashSet<String>> = mems
            .iter()
            .map(|(_, m)| m.metadata.tags.iter().cloned().collect())
            .collect();

        // Union-find for clustering
        let n = mems.len();
        let mut parent: Vec<usize> = (0..n).collect();
        let mut rank = vec![0usize; n];

        for i in 0..n {
            for j in (i + 1)..n {
                let sim = jaccard_similarity(&tag_sets[i], &tag_sets[j]);
                if sim >= self.config.tag_similarity_threshold {
                    union(&mut parent, &mut rank, i, j);
                }
            }
        }

        // Group by root
        let mut groups: HashMap<usize, Vec<usize>> = HashMap::new();
        for i in 0..n {
            let root = find(&mut parent, i);
            groups.entry(root).or_default().push(i);
        }

        // Build clusters
        let mut clusters = Vec::new();
        for indices in groups.values() {
            if indices.len() < 2 {
                continue;
            }
            let cluster_mems: Vec<&Memory> = indices.iter().map(|&i| &mems[i].1).collect();
            let cluster = self.build_cluster(&cluster_mems, mems, indices);
            clusters.push(cluster);
        }

        // Sort by cluster size (largest first)
        clusters.sort_by(|a, b| b.memory_ids.len().cmp(&a.memory_ids.len()));
        clusters
    }

    /// Build a MemoryCluster from a set of memories.
    fn build_cluster(
        &self,
        mems: &[&Memory],
        all_mems: &[(Galaxy, Memory)],
        indices: &[usize],
    ) -> MemoryCluster {
        let memory_ids: Vec<uuid::Uuid> = mems.iter().map(|m| m.metadata.id).collect();
        let galaxies: HashSet<Galaxy> = indices.iter().map(|&i| all_mems[i].0).collect();

        // Find shared tags (intersection of all tag sets)
        let mut shared_tags: Vec<String> = Vec::new();
        if let Some(first) = mems.first() {
            for tag in &first.metadata.tags {
                if mems.iter().all(|m| m.metadata.tags.contains(tag)) {
                    shared_tags.push(tag.clone());
                }
            }
        }

        let avg_importance: f32 =
            mems.iter().map(|m| m.metadata.importance).sum::<f32>() / mems.len() as f32;
        let avg_neuro_score: f32 =
            mems.iter().map(|m| m.metadata.neuro_score).sum::<f32>() / mems.len() as f32;

        // Theme: use most frequent tag, or "untagged" if none
        let theme = shared_tags
            .first()
            .cloned()
            .unwrap_or_else(|| "untagged".to_string());

        MemoryCluster {
            memory_ids,
            shared_tags,
            avg_importance,
            avg_neuro_score,
            galaxies,
            theme,
        }
    }

    /// Synthesize a compressed strategy memory from a cluster.
    fn synthesize_strategy_memory(
        &self,
        cluster: &MemoryCluster,
        all_mems: &[(Galaxy, Memory)],
    ) -> Memory {
        let id_map: HashMap<uuid::Uuid, &Memory> =
            all_mems.iter().map(|(_, m)| (m.metadata.id, m)).collect();

        // Collect content snippets from cluster members
        let snippets: Vec<&str> = cluster
            .memory_ids
            .iter()
            .filter_map(|id| id_map.get(id).map(|m| m.content.as_str()))
            .collect();

        // Compress: take first 100 chars of each, join with separators
        let compressed: Vec<String> = snippets
            .iter()
            .map(|s| {
                if s.len() > 100 {
                    format!("{}…", &s[..100])
                } else {
                    s.to_string()
                }
            })
            .collect();

        let content = format!(
            "Strategy [{}]: {} memories (avg importance: {:.2}, avg neuro: {:.2}). \
             Themes: {}. Snippets: {}",
            cluster.theme,
            cluster.memory_ids.len(),
            cluster.avg_importance,
            cluster.avg_neuro_score,
            cluster.shared_tags.join(", "),
            compressed.join(" | ")
        );

        let mut mem = Memory::new(Galaxy::Codex, content)
            .with_tags(cluster.shared_tags.clone())
            .with_importance(cluster.avg_importance)
            .with_memory_type(MemoryType::Pattern);

        mem.metadata.neuro_score = cluster.avg_neuro_score;
        mem.metadata.source = "strategy_synthesis".to_string();
        mem
    }

    /// Sleep consolidation — transfer important memories across galaxies.
    ///
    /// Routes:
    /// - sessions → codex (episodic → semantic)
    /// - citta → aria (emotional → identity)
    /// - dreams → research (creative → knowledge)
    /// - universal → codex (reclassification)
    pub fn sleep_consolidation(&self, store: &MemoryStore) -> Result<()> {
        let pathways = [
            (Galaxy::Sessions, Galaxy::Codex, 0.6),
            (Galaxy::Citta, Galaxy::Aria, 0.6),
            (Galaxy::Dreams, Galaxy::Research, 0.5),
            (Galaxy::Universal, Galaxy::Codex, 0.6),
        ];

        for (source, target, min_importance) in pathways {
            let source_mems = store.scan(source, 10_000).unwrap_or_default();
            for mem in &source_mems {
                if mem.metadata.importance >= min_importance {
                    let exists = store
                        .find_by_content_hash(target, &mem.metadata.content_hash)
                        .unwrap_or(None)
                        .is_some();
                    if !exists {
                        let mut transfer_mem = mem.clone();
                        transfer_mem.metadata.galaxy = target;
                        store.put_dedup(target, &transfer_mem)?;
                    }
                }
            }
        }
        Ok(())
    }
}

/// Jaccard similarity between two sets.
fn jaccard_similarity<T>(a: &HashSet<T>, b: &HashSet<T>) -> f32
where
    T: std::hash::Hash + Eq,
{
    if a.is_empty() && b.is_empty() {
        return 0.0;
    }
    let intersection = a.intersection(b).count();
    let union = a.union(b).count();
    if union == 0 {
        0.0
    } else {
        intersection as f32 / union as f32
    }
}

/// Union-find: find with path compression.
fn find(parent: &mut [usize], x: usize) -> usize {
    if parent[x] != x {
        parent[x] = find(parent, parent[x]);
    }
    parent[x]
}

/// Union-find: union by rank.
fn union(parent: &mut [usize], rank: &mut [usize], x: usize, y: usize) {
    let px = find(parent, x);
    let py = find(parent, y);
    if px == py {
        return;
    }
    match rank[px].cmp(&rank[py]) {
        std::cmp::Ordering::Less => parent[px] = py,
        std::cmp::Ordering::Greater => parent[py] = px,
        std::cmp::Ordering::Equal => {
            parent[py] = px;
            rank[px] += 1;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn test_store() -> (tempfile::TempDir, MemoryStore, AssociationStore) {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc = AssociationStore::open(store.env()).unwrap();
        (tmp, store, assoc)
    }

    #[test]
    fn synthesis_empty_store() {
        let (_tmp, store, assoc) = test_store();
        let synth = StrategySynthesizer::default();
        let report = synth.synthesize(&store, &assoc).unwrap();
        assert_eq!(report.memories_analyzed, 0);
        assert_eq!(report.strategies_synthesized, 0);
    }

    #[test]
    fn synthesis_creates_strategy_from_cluster() {
        let (_tmp, store, assoc) = test_store();

        // Create a cluster of 3+ memories with shared tags and decent importance
        for i in 0..4 {
            let mem = Memory::new(Galaxy::Codex, format!("Rust memory system design {i}"))
                .with_tags(vec!["rust".into(), "memory".into()])
                .with_importance(0.7);
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        // Add an unrelated memory
        let mem = Memory::new(Galaxy::Research, "cooking recipe for pasta".to_string())
            .with_importance(0.3);
        store.put(Galaxy::Research, &mem).unwrap();

        let synth = StrategySynthesizer::default();
        let report = synth.synthesize(&store, &assoc).unwrap();

        assert!(
            report.clusters_found > 0,
            "should find at least one cluster"
        );
        assert!(
            report.strategies_synthesized > 0,
            "should synthesize at least one strategy"
        );
        assert!(!report.themes.is_empty());

        // Verify strategy memory was stored in Codex
        let codex_mems = store.scan(Galaxy::Codex, 100).unwrap();
        let has_strategy = codex_mems.iter().any(|m| {
            m.metadata.memory_type == MemoryType::Pattern
                && m.metadata.source == "strategy_synthesis"
        });
        assert!(has_strategy, "strategy memory should be in Codex");
    }

    #[test]
    fn synthesis_skips_small_clusters() {
        let (_tmp, store, assoc) = test_store();

        // Only 2 memories with shared tags — below min_cluster_size
        let mem1 =
            Memory::new(Galaxy::Codex, "rust memory".to_string()).with_tags(vec!["rust".into()]);
        let mem2 =
            Memory::new(Galaxy::Codex, "rust data".to_string()).with_tags(vec!["rust".into()]);
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Codex, &mem2).unwrap();

        let synth = StrategySynthesizer::default();
        let report = synth.synthesize(&store, &assoc).unwrap();

        assert_eq!(
            report.strategies_synthesized, 0,
            "should not synthesize from clusters smaller than min_cluster_size"
        );
    }

    #[test]
    fn synthesis_skips_low_importance_clusters() {
        let (_tmp, store, assoc) = test_store();

        for i in 0..4 {
            let mem = Memory::new(Galaxy::Codex, format!("trivial note {i}"))
                .with_tags(vec!["trivial".into()])
                .with_importance(0.1);
            store.put(Galaxy::Codex, &mem).unwrap();
        }

        let synth = StrategySynthesizer::default();
        let report = synth.synthesize(&store, &assoc).unwrap();

        assert_eq!(
            report.strategies_synthesized, 0,
            "should not synthesize from low-importance clusters"
        );
    }

    #[test]
    fn sleep_consolidation_transfers_sessions_to_codex() {
        let (_tmp, store, assoc) = test_store();

        let session_mem =
            Memory::new(Galaxy::Sessions, "important session handoff".into()).with_importance(0.8);
        store.put(Galaxy::Sessions, &session_mem).unwrap();

        let synth = StrategySynthesizer::default();
        synth.synthesize(&store, &assoc).unwrap();
        synth.sleep_consolidation(&store).unwrap();

        let codex_mems = store.scan(Galaxy::Codex, 100).unwrap();
        let found = codex_mems
            .iter()
            .any(|m| m.content == "important session handoff");
        assert!(found, "session memory should be transferred to Codex");
    }

    #[test]
    fn sleep_consolidation_skips_low_importance() {
        let (_tmp, store, assoc) = test_store();

        let session_mem =
            Memory::new(Galaxy::Sessions, "trivial session note".into()).with_importance(0.2);
        store.put(Galaxy::Sessions, &session_mem).unwrap();

        let synth = StrategySynthesizer::default();
        synth.synthesize(&store, &assoc).unwrap();

        let codex_mems = store.scan(Galaxy::Codex, 100).unwrap();
        let found = codex_mems
            .iter()
            .any(|m| m.content == "trivial session note");
        assert!(!found, "low-importance session should not transfer");
    }

    #[test]
    fn jaccard_similarity_identical_sets() {
        let a: HashSet<&str> = ["a", "b", "c"].iter().copied().collect();
        let b: HashSet<&str> = ["a", "b", "c"].iter().copied().collect();
        assert!((jaccard_similarity(&a, &b) - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn jaccard_similarity_disjoint_sets() {
        let a: HashSet<&str> = ["a", "b"].iter().copied().collect();
        let b: HashSet<&str> = ["c", "d"].iter().copied().collect();
        assert!((jaccard_similarity(&a, &b) - 0.0).abs() < f32::EPSILON);
    }

    #[test]
    fn jaccard_similarity_partial_overlap() {
        let a: HashSet<&str> = ["a", "b", "c"].iter().copied().collect();
        let b: HashSet<&str> = ["b", "c", "d"].iter().copied().collect();
        // intersection = 2 (b, c), union = 4 (a, b, c, d)
        assert!((jaccard_similarity(&a, &b) - 0.5).abs() < f32::EPSILON);
    }

    #[test]
    fn synthesis_report_new_is_empty() {
        let report = SynthesisReport::new();
        assert_eq!(report.memories_analyzed, 0);
        assert_eq!(report.clusters_found, 0);
        assert_eq!(report.strategies_synthesized, 0);
    }

    #[test]
    fn synthesis_respects_max_strategies() {
        let (_tmp, store, assoc) = test_store();

        // Create 5 distinct clusters, each with 3+ memories
        for tag_idx in 0..5 {
            let tag = format!("tag{tag_idx}");
            for i in 0..3 {
                let mem = Memory::new(Galaxy::Codex, format!("{tag} content {i}"))
                    .with_tags(vec![tag.clone()])
                    .with_importance(0.7);
                store.put(Galaxy::Codex, &mem).unwrap();
            }
        }

        let config = StrategyConfig {
            max_strategies: 2,
            ..Default::default()
        };
        let synth = StrategySynthesizer::new(config);
        let report = synth.synthesize(&store, &assoc).unwrap();

        assert!(
            report.strategies_synthesized <= 2,
            "should respect max_strategies limit"
        );
    }
}
