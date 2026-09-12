//! Non-Destructive Phagic Digestive Cold-Storage Subsystem.
//!
//! # Sacred Rule (the Law of Non-Destructive Phagocytosis)
//! Phagic systems must NEVER delete anything. Irrelevant or distant "outer rim" memories
//! in each galaxy are gently migrated into compressed cold storage, preserving the complete
//! lineage, provenance, vector clocks, and retrievability.
//!
//! # Architecture
//! - **Outer-Rim Metric**: Calculates distance $D(m) \in [0.0, 1.0]$ from the galactic core as:
//!   $D(m) = f(\text{age}, \text{access\_frequency}, \text{harmonic\_resonance}, \text{emotional\_valence}, \text{importance\_weight})$
//! - **Hot Tier**: Active memories in `MemoryStore` and Tantivy `SearchEngine`.
//! - **Cold Tier**: Compressed archive (MessagePack + Gzip/Deflate), preserving all metadata,
//!   vector clocks, content, embeddings, and association graph links.
//! - **Digestion & Condensation**: Synthesizes clusters of outer-rim memories into distilled
//!   thematic nodes (`Tier::Semantic`, `MemoryType::Symbolic`) in the active hot tier,
//!   referencing the cold-stored records, while full original memories rest safely in cold storage.
//! - **Thawing (Warm Restoration)**: Zero data loss — any cold-stored memory can be queried
//!   directly or thawed back into the hot active tier with full fidelity.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;
use wm_core::{CoreError, Galaxy, Result};

use crate::memory::{Memory, MemoryId, MemoryType, Tier};
use crate::search::SearchEngine;
use crate::store::MemoryStore;

// ── Compression Codec ───────────────────────────────────────────────────

/// Compression algorithm used for cold storage payloads.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum CompressionCodec {
    /// Gzip compression (balanced ratio and high compatibility)
    #[default]
    Gzip,
    /// Raw deflate compression
    Deflate,
    /// Uncompressed MessagePack binary representation
    Msgpack,
}

impl CompressionCodec {
    /// String label for display/JSON.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Gzip => "gzip",
            Self::Deflate => "deflate",
            Self::Msgpack => "msgpack",
        }
    }
}

// ── Outer-Rim Distance Metric ───────────────────────────────────────────

/// Breakdown of the factors contributing to a memory's outer-rim distance.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OuterRimFactors {
    /// Age component in [0.0, 1.0]: 1.0 = ancient / past half-life.
    pub age_factor: f32,
    /// Access frequency component in [0.0, 1.0]: 1.0 = unaccessed, 0.0 = frequent.
    pub access_factor: f32,
    /// Harmonic resonance component in [0.0, 1.0]: 1.0 = zero resonance, 0.0 = peak resonance.
    pub resonance_factor: f32,
    /// Emotional valence & salience in [0.0, 1.0]: 1.0 = emotionally flat, 0.0 = charged.
    pub emotional_factor: f32,
    /// Importance component in [0.0, 1.0]: 1.0 = low importance, 0.0 = max importance.
    pub importance_factor: f32,
    /// Composite distance in [0.0, 1.0]: 0.0 = core, 1.0 = deep outer rim.
    pub distance: f32,
}

/// Configuration parameters for the outer-rim metric and digestion process.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhagicConfig {
    /// Weight for age factor (default 0.25).
    pub weight_age: f32,
    /// Weight for access frequency factor (default 0.25).
    pub weight_access: f32,
    /// Weight for harmonic resonance factor (default 0.15).
    pub weight_resonance: f32,
    /// Weight for emotional valence/weight factor (default 0.15).
    pub weight_emotional: f32,
    /// Weight for importance factor (default 0.20).
    pub weight_importance: f32,
    /// Distance threshold above which memories qualify for the outer rim (default 0.70).
    pub outer_rim_threshold: f32,
    /// Maximum memories digested in a single pass per galaxy (default 50).
    pub max_digest_batch: usize,
    /// Minimum memories in a cluster to form a distilled thematic node (default 2).
    pub min_cluster_size: usize,
    /// Preferred compression codec (default Gzip).
    pub compression_codec: CompressionCodec,
}

impl Default for PhagicConfig {
    fn default() -> Self {
        Self {
            weight_age: 0.25,
            weight_access: 0.25,
            weight_resonance: 0.15,
            weight_emotional: 0.15,
            weight_importance: 0.20,
            outer_rim_threshold: 0.70,
            max_digest_batch: 50,
            min_cluster_size: 2,
            compression_codec: CompressionCodec::Gzip,
        }
    }
}

/// Calculate the outer-rim distance $D(m) \in [0.0, 1.0]$ for a memory.
///
/// Protected memories (`is_protected == true`) are anchored at the galactic core
/// and always receive a distance of 0.0.
#[must_use]
pub fn calculate_outer_rim_distance(
    mem: &Memory,
    config: &PhagicConfig,
    now: DateTime<Utc>,
) -> OuterRimFactors {
    if mem.metadata.is_protected {
        return OuterRimFactors {
            age_factor: 0.0,
            access_factor: 0.0,
            resonance_factor: 0.0,
            emotional_factor: 0.0,
            importance_factor: 0.0,
            distance: 0.0,
        };
    }

    // 1. Age factor: days elapsed relative to configurable half_life_days
    let seconds_since_access = (now - mem.metadata.accessed_at).num_seconds().max(0);
    let days_since = seconds_since_access as f32 / 86400.0;
    let half_life = mem.metadata.half_life_days.max(1.0);
    let age_factor = (1.0 - 0.5f32.powf(days_since / half_life)).clamp(0.0, 1.0);

    // 2. Access frequency: hyperbolic decay over combined access + recall reads
    let reads = (mem.metadata.access_count + mem.metadata.recall_count) as f32;
    let access_factor = (1.0 / 0.5f32.mul_add(reads, 1.0)).clamp(0.0, 1.0);

    // 3. Harmonic resonance: inverse of neuro_score
    let resonance_factor = (1.0 - mem.metadata.neuro_score.clamp(0.0, 1.0)).clamp(0.0, 1.0);

    // 4. Emotional valence / salience: |valence| * weight
    let salience =
        (mem.metadata.emotional_valence.abs() * mem.metadata.emotional_weight).clamp(0.0, 1.0);
    let emotional_factor = (1.0 - salience).clamp(0.0, 1.0);

    // 5. Importance: inverse of semantic importance
    let importance_factor = (1.0 - mem.metadata.importance.clamp(0.0, 1.0)).clamp(0.0, 1.0);

    // Weighted composite
    let sum_weights = config.weight_age
        + config.weight_access
        + config.weight_resonance
        + config.weight_emotional
        + config.weight_importance;

    let distance = if sum_weights > 0.0 {
        let raw = config.weight_importance.mul_add(
            importance_factor,
            config.weight_emotional.mul_add(
                emotional_factor,
                config.weight_resonance.mul_add(
                    resonance_factor,
                    config
                        .weight_access
                        .mul_add(access_factor, config.weight_age * age_factor),
                ),
            ),
        );
        (raw / sum_weights).clamp(0.0, 1.0)
    } else {
        0.5
    };

    OuterRimFactors {
        age_factor,
        access_factor,
        resonance_factor,
        emotional_factor,
        importance_factor,
        distance,
    }
}

// ── Compression & Decompression Helpers ─────────────────────────────────

/// Compress a memory into a binary payload using the specified codec.
pub fn compress_memory(mem: &Memory, codec: CompressionCodec) -> Result<(Vec<u8>, usize)> {
    let uncompressed = rmp_serde::to_vec_named(mem)
        .map_err(|e| CoreError::Memory(format!("Cold storage serialization error: {e}")))?;
    let uncompressed_size = uncompressed.len();

    let compressed = match codec {
        CompressionCodec::Gzip => {
            use flate2::Compression;
            use flate2::write::GzEncoder;
            use std::io::Write;
            let mut encoder = GzEncoder::new(Vec::new(), Compression::best());
            encoder
                .write_all(&uncompressed)
                .map_err(|e| CoreError::Memory(format!("Gzip compression error: {e}")))?;
            encoder
                .finish()
                .map_err(|e| CoreError::Memory(format!("Gzip finish error: {e}")))?
        }
        CompressionCodec::Deflate => {
            use flate2::Compression;
            use flate2::write::DeflateEncoder;
            use std::io::Write;
            let mut encoder = DeflateEncoder::new(Vec::new(), Compression::best());
            encoder
                .write_all(&uncompressed)
                .map_err(|e| CoreError::Memory(format!("Deflate compression error: {e}")))?;
            encoder
                .finish()
                .map_err(|e| CoreError::Memory(format!("Deflate finish error: {e}")))?
        }
        CompressionCodec::Msgpack => uncompressed,
    };

    Ok((compressed, uncompressed_size))
}

/// Decompress a binary payload back into the original memory.
pub fn decompress_memory(payload: &[u8], codec: CompressionCodec) -> Result<Memory> {
    let uncompressed = match codec {
        CompressionCodec::Gzip => {
            use flate2::read::GzDecoder;
            use std::io::Read;
            let mut decoder = GzDecoder::new(payload);
            let mut buf = Vec::new();
            decoder
                .read_to_end(&mut buf)
                .map_err(|e| CoreError::Memory(format!("Gzip decompression error: {e}")))?;
            buf
        }
        CompressionCodec::Deflate => {
            use flate2::read::DeflateDecoder;
            use std::io::Read;
            let mut decoder = DeflateDecoder::new(payload);
            let mut buf = Vec::new();
            decoder
                .read_to_end(&mut buf)
                .map_err(|e| CoreError::Memory(format!("Deflate decompression error: {e}")))?;
            buf
        }
        CompressionCodec::Msgpack => payload.to_vec(),
    };

    crate::codec::decode(&uncompressed)
        .map_err(|e| CoreError::Memory(format!("Cold storage deserialization error: {e}")))
}

fn create_snippet(content: &str) -> String {
    let trimmed = content.trim();
    if trimmed.chars().count() <= 120 {
        trimmed.to_string()
    } else {
        let mut s: String = trimmed.chars().take(117).collect();
        s.push_str("...");
        s
    }
}

// ── Cold Storage Records & Summaries ────────────────────────────────────

/// A persistent record stored in the cold archive.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ColdRecord {
    /// Memory UUID.
    pub id: MemoryId,
    /// Original galaxy this memory belonged to.
    pub galaxy: Galaxy,
    /// Content hash (SHA-256) for integrity verification.
    pub content_hash: String,
    /// Timestamp when this memory was migrated into cold storage.
    pub cold_stored_at: DateTime<Utc>,
    /// Outer-rim distance calculated at freezing time.
    pub outer_rim_distance: f32,
    /// Factor breakdown at freezing time.
    pub distance_factors: OuterRimFactors,
    /// ID of the distilled thematic node (if synthesized during digestion).
    pub digest_id: Option<MemoryId>,
    /// Lineage & provenance notes.
    pub lineage_notes: Option<String>,
    /// Compression codec used.
    pub codec: CompressionCodec,
    /// Uncompressed payload size in bytes.
    pub uncompressed_size: usize,
    /// Compressed binary payload containing the full original Memory.
    pub compressed_payload: Vec<u8>,
    /// Vector clock / version at freezing time.
    pub version: u64,
    /// Fast-search tags preserved in cold header.
    pub tags: Vec<String>,
    /// Title preserved in cold header.
    pub title: Option<String>,
    /// Text snippet for rapid search without decompression.
    pub snippet: String,
}

impl ColdRecord {
    /// Create a new cold record by compressing a hot memory.
    pub fn new(
        mem: &Memory,
        outer_rim_distance: f32,
        distance_factors: OuterRimFactors,
        digest_id: Option<MemoryId>,
        lineage_notes: Option<String>,
        codec: CompressionCodec,
    ) -> Result<Self> {
        let (compressed_payload, uncompressed_size) = compress_memory(mem, codec)?;
        let snippet = create_snippet(&mem.content);

        Ok(Self {
            id: mem.metadata.id,
            galaxy: mem.metadata.galaxy,
            content_hash: mem.metadata.content_hash.clone(),
            cold_stored_at: Utc::now(),
            outer_rim_distance,
            distance_factors,
            digest_id,
            lineage_notes,
            codec,
            uncompressed_size,
            compressed_payload,
            version: mem.metadata.version,
            tags: mem.metadata.tags.clone(),
            title: mem.metadata.title.clone(),
            snippet,
        })
    }

    /// Extract a lightweight summary without decompressing the full memory payload.
    #[must_use]
    pub fn summary(&self) -> ColdRecordSummary {
        ColdRecordSummary {
            id: self.id,
            galaxy: self.galaxy,
            content_hash: self.content_hash.clone(),
            cold_stored_at: self.cold_stored_at,
            outer_rim_distance: self.outer_rim_distance,
            digest_id: self.digest_id,
            uncompressed_size: self.uncompressed_size,
            compressed_size: self.compressed_payload.len(),
            codec: self.codec,
            tags: self.tags.clone(),
            title: self.title.clone(),
            snippet: self.snippet.clone(),
        }
    }

    /// Decompress and restore the complete original `Memory`.
    pub fn decompress(&self) -> Result<Memory> {
        decompress_memory(&self.compressed_payload, self.codec)
    }
}

/// Lightweight summary of a cold-stored memory for listings and queries.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ColdRecordSummary {
    /// Memory UUID.
    pub id: MemoryId,
    /// Original Galaxy.
    pub galaxy: Galaxy,
    /// Content hash.
    pub content_hash: String,
    /// Cold storage timestamp.
    pub cold_stored_at: DateTime<Utc>,
    /// Outer-rim distance at freeze time.
    pub outer_rim_distance: f32,
    /// Associated digest node ID (if any).
    pub digest_id: Option<MemoryId>,
    /// Uncompressed bytes.
    pub uncompressed_size: usize,
    /// Compressed bytes.
    pub compressed_size: usize,
    /// Codec used.
    pub codec: CompressionCodec,
    /// Tags preserved in cold header.
    pub tags: Vec<String>,
    /// Title preserved in cold header.
    pub title: Option<String>,
    /// Text snippet.
    pub snippet: String,
}

// ── Cold Query Filter ───────────────────────────────────────────────────

/// Filter for querying cold-stored memories.
#[derive(Debug, Clone, Default)]
pub struct ColdQuery {
    /// Optional galaxy filter.
    pub galaxy: Option<Galaxy>,
    /// Must contain all specified tags.
    pub tags: Vec<String>,
    /// Minimum outer-rim distance filter.
    pub min_distance: Option<f32>,
    /// Stored after this timestamp.
    pub stored_after: Option<DateTime<Utc>>,
    /// Stored before this timestamp.
    pub stored_before: Option<DateTime<Utc>>,
    /// Substring match over title or snippet.
    pub content_substring: Option<String>,
    /// Maximum results to return.
    pub limit: usize,
}

impl ColdQuery {
    /// Create a new query matching all cold records (limit 100).
    #[must_use]
    pub fn new() -> Self {
        Self {
            limit: 100,
            ..Default::default()
        }
    }

    /// Filter by galaxy.
    #[must_use]
    pub const fn with_galaxy(mut self, galaxy: Galaxy) -> Self {
        self.galaxy = Some(galaxy);
        self
    }

    /// Filter by tags.
    #[must_use]
    pub fn with_tags(mut self, tags: Vec<String>) -> Self {
        self.tags = tags;
        self
    }

    /// Filter by minimum distance.
    #[must_use]
    pub const fn with_min_distance(mut self, min_dist: f32) -> Self {
        self.min_distance = Some(min_dist);
        self
    }

    /// Filter by result limit.
    #[must_use]
    pub const fn with_limit(mut self, limit: usize) -> Self {
        self.limit = limit;
        self
    }

    /// Filter by substring.
    #[must_use]
    pub fn with_content_substring(mut self, substring: impl Into<String>) -> Self {
        self.content_substring = Some(substring.into().to_lowercase());
        self
    }

    /// Check if a cold record summary satisfies this query.
    #[must_use]
    pub fn matches(&self, summary: &ColdRecordSummary) -> bool {
        if let Some(g) = self.galaxy {
            if summary.galaxy != g {
                return false;
            }
        }
        if let Some(min_d) = self.min_distance {
            if summary.outer_rim_distance < min_d {
                return false;
            }
        }
        if let Some(after) = self.stored_after {
            if summary.cold_stored_at < after {
                return false;
            }
        }
        if let Some(before) = self.stored_before {
            if summary.cold_stored_at > before {
                return false;
            }
        }
        for tag in &self.tags {
            if !summary.tags.iter().any(|t| t == tag) {
                return false;
            }
        }
        if let Some(sub) = &self.content_substring {
            let in_title = summary
                .title
                .as_ref()
                .is_some_and(|t| t.to_lowercase().contains(sub));
            let in_snippet = summary.snippet.to_lowercase().contains(sub);
            if !in_title && !in_snippet {
                return false;
            }
        }
        true
    }
}

// ── Phagic Digest Result Report ─────────────────────────────────────────

/// Telemetry report of a phagic digestion pass on a galaxy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhagicDigestReport {
    /// Galaxy processed.
    pub galaxy: Galaxy,
    /// Total memories scanned in the galaxy.
    pub memories_examined: usize,
    /// Outer-rim memories identified above the distance threshold.
    pub outer_rim_candidates: usize,
    /// Memories migrated into cold storage.
    pub memories_digested: usize,
    /// ID of the synthesized thematic digest node placed in the active tier.
    pub digest_memory_id: Option<MemoryId>,
    /// Uncompressed raw bytes across all digested memories.
    pub total_raw_bytes: usize,
    /// Compressed bytes stored in cold archive.
    pub total_cold_bytes: usize,
    /// Space compression ratio: `total_cold_bytes / total_raw_bytes`.
    pub compression_ratio: f32,
    /// Average outer-rim distance of the digested memories.
    pub average_outer_rim_distance: f32,
}

// ── Phagic Digester Engine ──────────────────────────────────────────────

/// Non-destructive digestive processor.
pub struct PhagicDigester {
    config: PhagicConfig,
}

impl PhagicDigester {
    /// Create a new digester with the specified configuration.
    #[must_use]
    pub const fn new(config: PhagicConfig) -> Self {
        Self { config }
    }

    /// Create with default configuration.
    #[must_use]
    pub fn default_config() -> Self {
        Self::new(PhagicConfig::default())
    }

    /// Access configuration.
    #[must_use]
    pub const fn config(&self) -> &PhagicConfig {
        &self.config
    }

    /// Calculate distance factors for a memory.
    #[must_use]
    pub fn calculate_distance(&self, mem: &Memory, now: DateTime<Utc>) -> OuterRimFactors {
        calculate_outer_rim_distance(mem, &self.config, now)
    }

    /// Scan a galaxy and identify outer-rim memories sorted by distance descending.
    pub fn scan_outer_rim(
        &self,
        store: &MemoryStore,
        galaxy: Galaxy,
    ) -> Result<Vec<(Memory, OuterRimFactors)>> {
        let memories = store.scan(galaxy, 10_000)?;
        let now = Utc::now();
        let mut candidates = Vec::new();

        for mem in memories {
            // Protected memories are immune to outer rim drift
            if mem.metadata.is_protected {
                continue;
            }

            let factors = self.calculate_distance(&mem, now);
            if factors.distance >= self.config.outer_rim_threshold {
                candidates.push((mem, factors));
            }
        }

        // Sort descending by distance (furthest memories first)
        candidates.sort_by(|a, b| {
            b.1.distance
                .partial_cmp(&a.1.distance)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        Ok(candidates)
    }

    /// Synthesize a cluster of outer-rim memories into a distilled thematic node in the hot tier,
    /// and gently migrate the original memories into the cold storage tier.
    pub fn digest_cluster(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
        galaxy: Galaxy,
        cluster: &[(Memory, OuterRimFactors)],
    ) -> Result<PhagicDigestReport> {
        if cluster.is_empty() {
            return Ok(PhagicDigestReport {
                galaxy,
                memories_examined: 0,
                outer_rim_candidates: 0,
                memories_digested: 0,
                digest_memory_id: None,
                total_raw_bytes: 0,
                total_cold_bytes: 0,
                compression_ratio: 0.0,
                average_outer_rim_distance: 0.0,
            });
        }

        let cluster_id = Uuid::new_v4();
        let now = Utc::now();

        // Compute tag frequency and shared topics
        let mut tag_counts: HashMap<String, usize> = HashMap::new();
        let mut total_distance = 0.0;
        let mut min_time = now;
        let mut max_time = DateTime::<Utc>::MIN_UTC;

        for (mem, factors) in cluster {
            total_distance += factors.distance;
            if mem.metadata.created_at < min_time {
                min_time = mem.metadata.created_at;
            }
            if mem.metadata.created_at > max_time {
                max_time = mem.metadata.created_at;
            }
            for tag in &mem.metadata.tags {
                if !tag.starts_with("phagic:") && !tag.starts_with("cold_source:") {
                    *tag_counts.entry(tag.clone()).or_insert(0) += 1;
                }
            }
        }

        let avg_distance = total_distance / cluster.len() as f32;

        let mut top_tags: Vec<(String, usize)> = tag_counts.into_iter().collect();
        top_tags.sort_by_key(|a| std::cmp::Reverse(a.1));
        let prominent_tags: Vec<String> =
            top_tags.into_iter().take(6).map(|(tag, _)| tag).collect();

        // 1. Synthesize thematic digest memory for active hot tier
        let mut digest_content = format!(
            "# Phagic Thematic Digest: {} Outer-Rim Condensation\n\n\
             **Cluster ID**: `{cluster_id}`\n\
             **Galaxy**: `{}`\n\
             **Digested Memories**: {} items safely migrated to Cold Storage\n\
             **Temporal Span**: {} to {}\n\
             **Average Outer-Rim Distance**: {:.3}\n\
             **Prominent Themes**: {}\n\n\
             ## Distilled Semantic Abstract\n\
             This thematic node preserves the collective semantic essence of {} outer-rim memories\n\
             from galaxy {}. The original memories have been gently transitioned into compressed\n\
             cold storage without data loss, retaining complete lineage and full thawability.\n\n\
             ## Lineage Pointers (Thawable Cold Records)\n",
            galaxy.db_name(),
            galaxy.db_name(),
            cluster.len(),
            min_time.format("%Y-%m-%d %H:%M:%S UTC"),
            max_time.format("%Y-%m-%d %H:%M:%S UTC"),
            avg_distance,
            if prominent_tags.is_empty() {
                "none".to_string()
            } else {
                prominent_tags.join(", ")
            },
            cluster.len(),
            galaxy.db_name(),
        );

        use std::fmt::Write as _;
        for (mem, factors) in cluster {
            let snippet = create_snippet(&mem.content);
            let _ = writeln!(
                digest_content,
                "- **[Memory `{}`]** (Distance: {:.2}): {snippet}",
                mem.metadata.id, factors.distance
            );
        }

        let mut digest_tags = prominent_tags;
        digest_tags.push("phagic:digest".to_string());
        digest_tags.push(format!("phagic:cluster:{cluster_id}"));

        let digest_title = format!(
            "Phagic Digest: {} ({} items)",
            galaxy.db_name(),
            cluster.len()
        );
        let mut digest_mem = Memory::new(galaxy, digest_content)
            .with_tags(digest_tags)
            .with_importance(0.65)
            .with_memory_type(MemoryType::Symbolic)
            .with_source("phagic:digestion".to_string(), 0.9);
        digest_mem.metadata.tier = Tier::Semantic;
        digest_mem.metadata.title = Some(digest_title);
        digest_mem.metadata.topic = Some(format!("{}:phagic_digest", galaxy.db_name()));

        // Store thematic digest memory in the hot store
        store.put(galaxy, &digest_mem)?;

        // Index the thematic digest node in Tantivy search if available
        if let Some(engine) = search {
            if let Ok(mut writer_guard) = engine.writer() {
                let _ = engine.add_document(
                    &mut writer_guard,
                    &digest_mem.metadata.id.to_string(),
                    galaxy.db_name(),
                    &digest_mem.content,
                    &digest_mem.metadata.tags,
                    digest_mem.metadata.created_at.timestamp(),
                );
                let _ = engine.commit(&mut writer_guard);
            }
        }

        let digest_id = digest_mem.metadata.id;

        // 2. Freeze each original memory into cold storage
        let mut total_raw_bytes = 0;
        let mut total_cold_bytes = 0;

        for (mem, factors) in cluster {
            let notes = format!("Digested in phagic cluster {cluster_id} (digest_id: {digest_id})");
            let cold_rec = store.freeze_to_cold(
                search,
                mem.metadata.id,
                factors.distance,
                factors.clone(),
                Some(digest_id),
                Some(notes),
                self.config.compression_codec,
            )?;
            total_raw_bytes += cold_rec.uncompressed_size;
            total_cold_bytes += cold_rec.compressed_payload.len();
        }

        let compression_ratio = if total_raw_bytes > 0 {
            total_cold_bytes as f32 / total_raw_bytes as f32
        } else {
            0.0
        };

        Ok(PhagicDigestReport {
            galaxy,
            memories_examined: cluster.len(),
            outer_rim_candidates: cluster.len(),
            memories_digested: cluster.len(),
            digest_memory_id: Some(digest_id),
            total_raw_bytes,
            total_cold_bytes,
            compression_ratio,
            average_outer_rim_distance: avg_distance,
        })
    }

    /// Perform a full non-destructive digestive pass on a galaxy.
    pub fn digest_galaxy(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
        galaxy: Galaxy,
    ) -> Result<PhagicDigestReport> {
        let candidates = self.scan_outer_rim(store, galaxy)?;
        let count = store.count(galaxy).unwrap_or(0);

        if candidates.is_empty() {
            return Ok(PhagicDigestReport {
                galaxy,
                memories_examined: count,
                outer_rim_candidates: 0,
                memories_digested: 0,
                digest_memory_id: None,
                total_raw_bytes: 0,
                total_cold_bytes: 0,
                compression_ratio: 0.0,
                average_outer_rim_distance: 0.0,
            });
        }

        // Bound to max_digest_batch
        let batch_size = candidates.len().min(self.config.max_digest_batch);
        let batch = &candidates[..batch_size];

        let mut report = self.digest_cluster(store, search, galaxy, batch)?;
        report.memories_examined = count;
        report.outer_rim_candidates = candidates.len();
        Ok(report)
    }

    /// Perform phagic digestion across all memory galaxies.
    pub fn digest_all(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
    ) -> Result<Vec<PhagicDigestReport>> {
        let mut reports = Vec::new();
        for galaxy in Galaxy::all() {
            match galaxy {
                Galaxy::Substrate
                | Galaxy::Dharma
                | Galaxy::Karma
                | Galaxy::Embeddings
                | Galaxy::Associations => continue,
                _ => {}
            }
            if store.count(galaxy).unwrap_or(0) == 0 {
                continue;
            }
            reports.push(self.digest_galaxy(store, search, galaxy)?);
        }
        Ok(reports)
    }

    /// Thaw a cold-stored memory back into the active hot tier.
    pub fn thaw(
        &self,
        store: &MemoryStore,
        search: Option<&SearchEngine>,
        id: MemoryId,
    ) -> Result<Memory> {
        store.thaw_from_cold(search, id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    fn test_store() -> MemoryStore {
        let tmp = tempdir().unwrap();
        MemoryStore::open_default(tmp.path()).unwrap()
    }

    #[test]
    fn outer_rim_distance_calculation_monotonic() {
        let config = PhagicConfig::default();
        let now = Utc::now();

        // 1. Core memory: recent, high importance, high resonance, high emotion, accessed
        let mut core_mem = Memory::new(Galaxy::Codex, "Vital core memory".into())
            .with_importance(0.95)
            .with_neuro_score(0.9)
            .with_emotional_valence(0.8, 0.9);
        core_mem.metadata.access_count = 10;
        core_mem.metadata.accessed_at = now;

        let core_factors = calculate_outer_rim_distance(&core_mem, &config, now);
        assert!(
            core_factors.distance < 0.25,
            "Core memory distance should be low: {}",
            core_factors.distance
        );

        // 2. Outer-rim memory: ancient, 0 accesses, low importance, low resonance, neutral emotion
        let mut rim_mem = Memory::new(Galaxy::Codex, "Faded distant note".into())
            .with_importance(0.05)
            .with_neuro_score(0.1)
            .with_emotional_valence(0.0, 0.0);
        rim_mem.metadata.access_count = 0;
        rim_mem.metadata.recall_count = 0;
        rim_mem.metadata.accessed_at = now - chrono::Duration::days(120);

        let rim_factors = calculate_outer_rim_distance(&rim_mem, &config, now);
        assert!(
            rim_factors.distance >= config.outer_rim_threshold,
            "Rim memory distance should exceed threshold: {}",
            rim_factors.distance
        );
        assert!(
            rim_factors.distance > core_factors.distance,
            "Rim memory must be strictly further out than core memory"
        );
    }

    #[test]
    fn protected_memory_is_anchored_at_core() {
        let config = PhagicConfig::default();
        let now = Utc::now();

        let mut protected_mem = Memory::new(Galaxy::Codex, "Protected sacred memory".into())
            .with_protection(true)
            .with_importance(0.01); // low importance, but protected
        protected_mem.metadata.accessed_at = now - chrono::Duration::days(365);

        let factors = calculate_outer_rim_distance(&protected_mem, &config, now);
        assert_eq!(
            factors.distance, 0.0,
            "Protected memory must always have distance 0.0"
        );
    }

    #[test]
    fn cold_record_compression_roundtrip() {
        let mem = Memory::new(
            Galaxy::Research,
            "Extensive research logs on cosmic non-destructive phagocytosis and entropy reversal"
                .into(),
        )
        .with_tags(vec!["physics".into(), "entropy".into(), "phagic".into()])
        .with_importance(0.3);

        for codec in [
            CompressionCodec::Gzip,
            CompressionCodec::Deflate,
            CompressionCodec::Msgpack,
        ] {
            let factors = OuterRimFactors {
                age_factor: 0.8,
                access_factor: 0.9,
                resonance_factor: 0.7,
                emotional_factor: 0.9,
                importance_factor: 0.7,
                distance: 0.81,
            };

            let cold = ColdRecord::new(&mem, 0.81, factors, None, Some("test notes".into()), codec)
                .unwrap();
            assert_eq!(cold.id, mem.metadata.id);
            assert_eq!(cold.galaxy, Galaxy::Research);

            let decompressed = cold.decompress().unwrap();
            assert_eq!(decompressed.metadata.id, mem.metadata.id);
            assert_eq!(decompressed.content, mem.content);
            assert_eq!(decompressed.metadata.tags, mem.metadata.tags);
            assert_eq!(decompressed.metadata.importance, mem.metadata.importance);
        }
    }

    #[test]
    fn freeze_and_thaw_zero_data_loss() {
        let store = test_store();
        let galaxy = Galaxy::Codex;

        let content = "Detailed architectural blueprint for WhiteMagic non-destructive storage";
        let mem = Memory::new(galaxy, content.into())
            .with_tags(vec!["architecture".into(), "v9".into()])
            .with_importance(0.2);
        let id = mem.metadata.id;

        store.put(galaxy, &mem).unwrap();
        assert!(store.get(galaxy, id).unwrap().is_some());

        // Freeze to cold storage
        let digester = PhagicDigester::default_config();
        let factors = digester.calculate_distance(&mem, Utc::now());
        let cold_record = store
            .freeze_to_cold(
                None,
                id,
                factors.distance,
                factors,
                None,
                Some("unit test freeze".into()),
                CompressionCodec::Gzip,
            )
            .unwrap();

        assert_eq!(cold_record.id, id);

        // Hot store should no longer contain the memory
        assert!(store.get(galaxy, id).unwrap().is_none());

        // But cold store DOES contain it
        let cold_found = store.get_cold_record(id).unwrap();
        assert!(cold_found.is_some());
        let cold_rec = cold_found.unwrap();
        assert_eq!(cold_rec.content_hash, mem.metadata.content_hash);

        // find_anywhere should find it with is_cold = true
        let (found_galaxy, found_mem, is_cold) = store.find_anywhere(id).unwrap().unwrap();
        assert_eq!(found_galaxy, galaxy);
        assert_eq!(found_mem.content, content);
        assert!(is_cold);

        // Thaw it back into the hot store
        let thawed = store.thaw_from_cold(None, id).unwrap();
        assert_eq!(thawed.metadata.id, id);
        assert_eq!(thawed.content, content);
        assert_eq!(
            thawed.metadata.tags,
            vec!["architecture", "v9", "thawed:phagic"]
        );
        assert_eq!(thawed.metadata.tier, Tier::Episodic);

        // Hot store now contains it again
        assert!(store.get(galaxy, id).unwrap().is_some());

        // Cold store no longer contains it
        assert!(store.get_cold_record(id).unwrap().is_none());

        // find_anywhere now returns is_cold = false
        let (_, _, is_cold_after) = store.find_anywhere(id).unwrap().unwrap();
        assert!(!is_cold_after);
    }

    #[test]
    fn phagic_digest_cluster_synthesizes_thematic_node() {
        let store = test_store();
        let galaxy = Galaxy::Journals;
        let now = Utc::now();

        // Populate with 3 distant outer-rim memories
        let mut ids = Vec::new();
        for i in 1..=3 {
            let mut mem = Memory::new(
                galaxy,
                format!("Ancient journal reflection #{i} about distant journeys"),
            )
            .with_tags(vec!["travel".into(), "reflection".into()])
            .with_importance(0.05);
            mem.metadata.accessed_at = now - chrono::Duration::days(150);
            mem.metadata.access_count = 0;
            store.put(galaxy, &mem).unwrap();
            ids.push(mem.metadata.id);
        }

        let digester = PhagicDigester::default_config();
        let report = digester.digest_galaxy(&store, None, galaxy).unwrap();

        assert_eq!(report.memories_digested, 3);
        assert!(report.digest_memory_id.is_some());
        assert!(report.total_cold_bytes > 0);
        assert!(report.total_raw_bytes > report.total_cold_bytes);

        // All 3 original memories are in cold storage, removed from hot galaxy
        for id in &ids {
            assert!(store.get(galaxy, *id).unwrap().is_none());
            assert!(store.get_cold_record(*id).unwrap().is_some());
        }

        // Thematic digest memory is present in hot galaxy
        let digest_id = report.digest_memory_id.unwrap();
        let digest_mem = store.get(galaxy, digest_id).unwrap().unwrap();
        assert_eq!(digest_mem.metadata.tier, Tier::Semantic);
        assert!(digest_mem.content.contains("Phagic Thematic Digest"));
        assert!(
            digest_mem
                .metadata
                .tags
                .contains(&"phagic:digest".to_string())
        );

        // Thaw one of the cold memories back to hot
        let thawed = digester.thaw(&store, None, ids[0]).unwrap();
        assert_eq!(thawed.metadata.id, ids[0]);
        assert!(store.get(galaxy, ids[0]).unwrap().is_some());
        assert!(store.get_cold_record(ids[0]).unwrap().is_none());
    }
}
