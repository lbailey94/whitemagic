//! Association miner — discovers hidden semantic links between memories.
//!
//! Ported from v2's `association_miner.py`. Uses lightweight content
//! analysis (keyword overlap, Jaccard similarity) to propose new
//! associations between memories that aren't already linked.
//!
//! No memory is ever deleted or modified — only new association links
//! are created. New links are bidirectional with initial strength
//! proportional to the semantic overlap score.

use std::collections::HashSet;
use wm_core::{Galaxy, Result};
use wm_memory::{Association, AssociationStore, LinkType, Memory, MemoryStore};

/// Default stop words — common English words that carry no semantic signal.
const STOP_WORDS: &[&str] = &[
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may", "might", "can", "could",
    "must", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "because", "but", "and", "or", "if", "while", "about", "up",
    "out", "off", "over", "this", "that", "these", "those", "it", "its", "my", "your", "his",
    "her", "our", "their", "what", "which", "who", "whom", "me", "him", "them", "we", "you",
    "they", "i", "he", "she", "us", "self", "none", "also", "any", "def", "class", "import",
    "return", "true", "false",
];

/// A proposed association between two memories.
#[derive(Debug, Clone)]
pub struct ProposedLink {
    /// Source memory UUID
    pub source: uuid::Uuid,
    /// Target memory UUID
    pub target: uuid::Uuid,
    /// Semantic overlap score (0.0-1.0)
    pub overlap_score: f32,
    /// Shared keywords that drove the proposal
    pub shared_keywords: Vec<String>,
    /// Human-readable explanation
    pub reason: String,
}

/// Results from an association mining run.
#[derive(Debug, Clone)]
pub struct MiningReport {
    /// Memories sampled for comparison
    pub memories_sampled: usize,
    /// Pairs evaluated
    pub pairs_evaluated: usize,
    /// Links proposed (above threshold)
    pub links_proposed: usize,
    /// Links actually created (after dedup check)
    pub links_created: usize,
    /// Top proposals (sorted by score, capped)
    pub top_proposals: Vec<ProposedLink>,
}

impl MiningReport {
    /// Create a new empty report.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            memories_sampled: 0,
            pairs_evaluated: 0,
            links_proposed: 0,
            links_created: 0,
            top_proposals: Vec::new(),
        }
    }

    /// Convert to JSON for status reporting.
    #[must_use]
    pub fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "memories_sampled": self.memories_sampled,
            "pairs_evaluated": self.pairs_evaluated,
            "links_proposed": self.links_proposed,
            "links_created": self.links_created,
        })
    }
}

impl Default for MiningReport {
    fn default() -> Self {
        Self::new()
    }
}

/// Configuration for the association miner.
#[derive(Debug, Clone)]
pub struct MinerConfig {
    /// Minimum overlap score to propose a link
    pub min_overlap: f32,
    /// Maximum proposals per run
    pub max_proposals: usize,
    /// Minimum shared keywords to propose a link
    pub min_shared_keywords: usize,
    /// Maximum keywords to extract per memory
    pub max_keywords: usize,
    /// Sample size for mining
    pub sample_size: usize,
}

impl Default for MinerConfig {
    fn default() -> Self {
        Self {
            min_overlap: 0.15,
            max_proposals: 50,
            min_shared_keywords: 3,
            max_keywords: 50,
            sample_size: 200,
        }
    }
}

/// Association miner — discovers hidden semantic connections.
///
/// Strategy:
/// 1. Sample memories from non-system galaxies.
/// 2. Extract keyword fingerprints from each memory's content.
/// 3. Compare all pairs for keyword overlap (Jaccard-like).
/// 4. Propose links for pairs above threshold that aren't already associated.
/// 5. Persist new associations to the `AssociationStore`.
pub struct AssociationMiner {
    config: MinerConfig,
}

impl AssociationMiner {
    /// Create a new miner with the given config.
    #[must_use]
    pub const fn new(config: MinerConfig) -> Self {
        Self { config }
    }

    /// Create with default config.
    #[must_use]
    pub fn default_config() -> Self {
        Self::new(MinerConfig::default())
    }

    /// Extract meaningful keywords from text.
    ///
    /// Lowercases, tokenizes on word boundaries, removes stop words
    /// and very short tokens. Returns a set of unique keywords.
    #[must_use]
    pub fn extract_keywords(text: &str, max_keywords: usize) -> HashSet<String> {
        let stop_set: HashSet<&str> = STOP_WORDS.iter().copied().collect();
        let text_lower = text.to_lowercase();
        let words: Vec<&str> = text_lower
            .split(|c: char| !c.is_alphanumeric() && c != '_')
            .filter(|w| w.len() > 2 && !stop_set.contains(*w))
            .collect();

        let mut keywords: HashSet<String> = HashSet::new();
        for w in &words {
            keywords.insert(w.to_string());
            if keywords.len() >= max_keywords {
                break;
            }
        }
        keywords
    }

    /// Compute Jaccard-like overlap between two keyword sets.
    ///
    /// Returns (score, `shared_keywords`). The score is a weighted Jaccard
    /// that boosts pairs with many shared keywords (absolute count matters).
    #[must_use]
    pub fn compute_overlap(kw_a: &HashSet<String>, kw_b: &HashSet<String>) -> (f32, Vec<String>) {
        if kw_a.is_empty() || kw_b.is_empty() {
            return (0.0, vec![]);
        }

        let shared: Vec<String> = kw_a.intersection(kw_b).cloned().collect();
        if shared.is_empty() {
            return (0.0, vec![]);
        }

        let union_size = kw_a.union(kw_b).count();
        if union_size == 0 {
            return (0.0, vec![]);
        }

        // Weighted Jaccard: penalize very small shared sets
        let raw_jaccard = shared.len() as f32 / union_size as f32;
        // Boost if many shared keywords (absolute count matters)
        let count_bonus = (shared.len() as f32 / 5.0).min(1.0) * 0.3;
        let score = (raw_jaccard + count_bonus).min(1.0);
        (score, shared)
    }

    /// Run a single association mining pass across non-system galaxies.
    ///
    /// Samples memories, extracts keywords, compares pairs, and creates
    /// new associations for pairs above the overlap threshold.
    pub fn mine(
        &self,
        store: &MemoryStore,
        assoc_store: &AssociationStore,
    ) -> Result<MiningReport> {
        let mut report = MiningReport::new();

        // Collect memories from non-system galaxies
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
            let mems = store.scan(galaxy, self.config.sample_size)?;
            for mem in mems {
                all_mems.push((galaxy, mem));
            }
        }

        if all_mems.len() < 2 {
            return Ok(report);
        }

        report.memories_sampled = all_mems.len();

        // Extract keywords for each memory
        let fingerprints: Vec<(Galaxy, uuid::Uuid, HashSet<String>)> = all_mems
            .iter()
            .map(|(galaxy, mem)| {
                let kws = Self::extract_keywords(&mem.content, self.config.max_keywords);
                (*galaxy, mem.metadata.id, kws)
            })
            .collect();

        // Compare all pairs
        let mut proposals: Vec<ProposedLink> = Vec::new();
        for i in 0..fingerprints.len() {
            for j in (i + 1)..fingerprints.len() {
                report.pairs_evaluated += 1;
                let (score, shared) = Self::compute_overlap(&fingerprints[i].2, &fingerprints[j].2);

                if score >= self.config.min_overlap
                    && shared.len() >= self.config.min_shared_keywords
                {
                    // Check if association already exists
                    let src = fingerprints[i].1;
                    let tgt = fingerprints[j].1;
                    let exists = assoc_store
                        .get(store.env(), src, tgt)
                        .map(|o| o.is_some())
                        .unwrap_or(false);

                    if !exists {
                        let top_kw: Vec<String> = shared.iter().take(5).cloned().collect();
                        let reason = format!(
                            "Semantic overlap ({} shared keywords: {})",
                            shared.len(),
                            top_kw.join(", ")
                        );
                        proposals.push(ProposedLink {
                            source: src,
                            target: tgt,
                            overlap_score: score,
                            shared_keywords: shared,
                            reason,
                        });
                    }
                }
            }
        }

        report.links_proposed = proposals.len();

        // Sort by score descending and cap
        proposals.sort_by(|a, b| {
            b.overlap_score
                .partial_cmp(&a.overlap_score)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        proposals.truncate(self.config.max_proposals);

        // Create associations
        for prop in &proposals {
            let assoc = Association::new(
                prop.source,
                prop.target,
                LinkType::Related,
                prop.overlap_score,
            );
            if matches!(assoc_store.put(store.env(), &assoc), Ok(())) {
                report.links_created += 1;
            }
            // Bidirectional: also create reverse link
            let reverse = Association::new(
                prop.target,
                prop.source,
                LinkType::Related,
                prop.overlap_score,
            );
            let _ = assoc_store.put(store.env(), &reverse);
        }

        report.top_proposals = proposals;
        Ok(report)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn extract_keywords_basic() {
        let kws =
            AssociationMiner::extract_keywords("The Rust memory system uses LMDB for storage", 50);
        assert!(kws.contains("rust"));
        assert!(kws.contains("memory"));
        assert!(kws.contains("system"));
        assert!(kws.contains("lmdb"));
        assert!(kws.contains("storage"));
        // Stop words should be excluded
        assert!(!kws.contains("the"));
        assert!(!kws.contains("for"));
    }

    #[test]
    fn extract_keywords_empty() {
        let kws = AssociationMiner::extract_keywords("", 50);
        assert!(kws.is_empty());
    }

    #[test]
    fn extract_keywords_max_limit() {
        let text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu";
        let kws = AssociationMiner::extract_keywords(text, 5);
        assert!(kws.len() <= 5);
    }

    #[test]
    fn compute_overlap_identical() {
        let kw_a: HashSet<String> = ["rust", "memory", "lmdb"]
            .iter()
            .map(std::string::ToString::to_string)
            .collect();
        let kw_b = kw_a.clone();
        let (score, shared) = AssociationMiner::compute_overlap(&kw_a, &kw_b);
        assert!((score - 1.0).abs() < 0.01 || score > 0.9);
        assert_eq!(shared.len(), 3);
    }

    #[test]
    fn compute_overlap_disjoint() {
        let kw_a: HashSet<String> = ["rust", "memory"]
            .iter()
            .map(std::string::ToString::to_string)
            .collect();
        let kw_b: HashSet<String> = ["python", "django"]
            .iter()
            .map(std::string::ToString::to_string)
            .collect();
        let (score, shared) = AssociationMiner::compute_overlap(&kw_a, &kw_b);
        assert_eq!(score, 0.0);
        assert!(shared.is_empty());
    }

    #[test]
    fn compute_overlap_partial() {
        let kw_a: HashSet<String> = ["rust", "memory", "lmdb", "store"]
            .iter()
            .map(std::string::ToString::to_string)
            .collect();
        let kw_b: HashSet<String> = ["rust", "memory", "sqlite", "db"]
            .iter()
            .map(std::string::ToString::to_string)
            .collect();
        let (score, shared) = AssociationMiner::compute_overlap(&kw_a, &kw_b);
        assert!(score > 0.0);
        assert!(shared.contains(&"rust".to_string()));
        assert!(shared.contains(&"memory".to_string()));
    }

    #[test]
    fn mine_creates_associations() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc_store = AssociationStore::open(store.env()).unwrap();

        // Create memories with overlapping keywords
        let mem1 = Memory::new(
            Galaxy::Codex,
            "Rust memory system with LMDB storage backend".into(),
        );
        let mem2 = Memory::new(
            Galaxy::Research,
            "Rust memory LMDB performance benchmarks".into(),
        );
        let mem3 = Memory::new(Galaxy::Codex, "Python web framework Django tutorial".into());

        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Research, &mem2).unwrap();
        store.put(Galaxy::Codex, &mem3).unwrap();

        let miner = AssociationMiner::new(MinerConfig {
            min_overlap: 0.1,
            min_shared_keywords: 2,
            max_proposals: 50,
            max_keywords: 50,
            sample_size: 200,
        });

        let report = miner.mine(&store, &assoc_store).unwrap();

        assert!(report.memories_sampled >= 3);
        assert!(report.pairs_evaluated >= 3);
        // mem1 and mem2 share "rust", "memory", "lmdb" — should get linked
        assert!(report.links_created > 0);

        // Verify association was created
        let assoc = assoc_store
            .get(store.env(), mem1.metadata.id, mem2.metadata.id)
            .unwrap();
        assert!(assoc.is_some());
    }

    #[test]
    fn mine_skips_existing_associations() {
        let tmp = tempdir().unwrap();
        let store = MemoryStore::open_default(tmp.path()).unwrap();
        let assoc_store = AssociationStore::open(store.env()).unwrap();

        let mem1 = Memory::new(Galaxy::Codex, "Rust memory LMDB".into());
        let mem2 = Memory::new(Galaxy::Research, "Rust memory LMDB".into());
        store.put(Galaxy::Codex, &mem1).unwrap();
        store.put(Galaxy::Research, &mem2).unwrap();

        // Pre-create the association
        let existing = Association::new(mem1.metadata.id, mem2.metadata.id, LinkType::Related, 0.5);
        assoc_store.put(store.env(), &existing).unwrap();

        let miner = AssociationMiner::default_config();
        let _report = miner.mine(&store, &assoc_store).unwrap();

        // Should not create a duplicate
        let all_from = assoc_store
            .find_from(store.env(), mem1.metadata.id)
            .unwrap();
        // Should have the original + possibly the reverse, but not a duplicate forward link
        let forward_count = all_from
            .iter()
            .filter(|a| a.target == mem2.metadata.id)
            .count();
        assert_eq!(
            forward_count, 1,
            "should not create duplicate forward association"
        );
    }

    #[test]
    fn mining_report_to_json() {
        let report = MiningReport {
            memories_sampled: 10,
            pairs_evaluated: 45,
            links_proposed: 5,
            links_created: 3,
            top_proposals: vec![],
        };
        let json = report.to_json();
        assert_eq!(json["memories_sampled"], 10);
        assert_eq!(json["links_created"], 3);
    }
}
