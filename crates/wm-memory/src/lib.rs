//! `WhiteMagic` memory — LMDB + Tantivy + `LanceDB`
//!
//! Replaces the v2 `SQLite` + FTS5 + Python HNSW stack with:
//! - LMDB for key-value storage (mmap'd, zero-copy reads)
//! - Tantivy for full-text search (Rust, Lucene-class performance)
//! - `LanceDB` for vector similarity search (disk-based HNSW)

#![forbid(unsafe_code)]

pub mod associations;
pub mod at_rest;
pub mod attestation;
mod codec;
pub mod cold_storage;
pub mod consistency;
pub mod conversational;
pub mod credentials;
pub mod embedder;
pub mod enrichment;
pub mod envelope;
pub mod episodic;
pub mod episodic_keys;
pub mod galaxy_registry;
pub mod indexes;
pub mod lifecycle;
pub mod mandala;
pub mod memory;
pub mod migration;
pub mod predictive_cache;
pub mod query_planner;
pub mod recall;
pub mod recall_conformal;
pub mod recovery;
pub mod redact;
pub mod reindex;
pub mod release_manifest;
pub mod revision;
pub mod search;
pub mod semantic;
pub mod store;
pub mod typology;
pub mod validator;
pub mod vector;

pub use associations::{Association, AssociationStore, LinkType};
pub use at_rest::{
    AT_REST_KEY_FILE, Argon2Params, AtRestConfig, AtRestMode, AtRestState, AtRestStatus,
    AtRestStatusPresent, DEK_KEY_PREFIX, KEYRING_DB, KEYRING_FORMAT_VERSION, KEYRING_META_KEY,
    KeyringMeta, MIGRATION_LEDGER_KEY, MigrationGalaxyState, MigrationLedger, RK_CHECK_INFO,
    RK_CHECK_KEY, RK_CHECK_PLAINTEXT, generated_key_path,
};
pub use attestation::{
    ATTESTATION_DOMAIN, ATTESTATION_KEY_ENV, ATTESTATIONS_DB, AttestationReport, RecordAttestation,
    anchor_leaf_input, attestation_key, attestation_payload, attestation_prefix, merkle_root_hex,
    sha256_hex, sign_attestation, verify_attestation,
};
pub use cold_storage::{
    ColdQuery, ColdRecord, ColdRecordSummary, CompressionCodec, OuterRimFactors, PhagicConfig,
    PhagicDigestReport, PhagicDigester, calculate_outer_rim_distance, compress_memory,
    decompress_memory,
};
pub use consistency::{
    CoherenceReceipt, CoherenceSnapshot, ConflictReport, ConsistencyError, CrossMemoryConsistency,
    CrossMemoryConsistencyManager, Resolution, VectorClock, WriteOp,
};
pub use conversational::{
    ConversationalConfig, ConversationalResult, ConversationalSearch, QueryClassification,
    SearchMetrics,
};
pub use credentials::{
    ADVICE as CREDENTIAL_ADVICE, credential_shaped_content, redact_credential_content,
};
#[cfg(feature = "onnx")]
pub use embedder::OrtEmbedder;
pub use embedder::{Embedder, EmbedderConfig, HttpEmbedder, StubEmbedder, create_embedder};
pub use enrichment::VocabularyEnrichment;
pub use episodic::{EpisodicSearchResult, EpisodicStore};
pub use episodic_keys::{
    AdaptiveAliases, EpisodicKey, KeyCategory, entity_key_terms, extract_episodic_keys,
    key_index_terms, key_index_terms_with_aliases,
};
pub use galaxy_registry::{GalaxyMetadata, GalaxyRegistry};
pub use lifecycle::{ConsolidationResult, ForgettingResult, Lifecycle, LifecycleConfig};
pub use mandala::{Compartment, CompartmentConfig, MandalaLevel, MandalaManager};
pub use memory::{
    Memory, MemoryId, MemoryMetadata, MemoryType, Tier, content_hash, decode_embedding,
    encode_embedding, trust_weighted_score,
};
pub use migration::{
    AtRestMigrationReport, DEFAULT_MIGRATION_BATCH, GalaxyAtRestCounts, GalaxyMigrationReport,
    RECORD_GALAXIES, at_rest_record_counts, migrate_at_rest_records, migration_ledger,
};
pub use predictive_cache::{CacheStats, PredictiveCache};
pub use query_planner::{QueryClass, QueryPlan};
pub use recall::{RecallConfig, RecallEngine, RecallResult};
pub use recovery::{
    GalaxyIntegrity, IntegrityReport, QuarantineEntry, RecoveryStrategy, RepairReport,
    check_integrity, grow_map_size, open_with_recovery, repair,
};
pub use reindex::{
    ConsistencyReport, ContentRepairReport, DriftClassification, GalaxyConsistency,
    GalaxyContentRepairStats, GalaxyDriftClass, GalaxyRebuildStats, IndexRebuildReport,
    check_consistency, classify_drift, heal_index_drift, rebuild_index, repair_content,
};
pub use release_manifest::{
    KEY_LINEAGE_MESH_ERA, RELEASE_MANIFEST_DOMAIN, ReleaseArtifact, ReleaseManifest,
    release_payload, sign_release, verify_release,
};
pub use revision::{MemoryRevision, RevisionActor, RevisionChainReport};
pub use search::{
    IndexHealth, MAX_INDEX_CONTENT_LEN, MIN_PRINTABLE_RATIO, STOPWORDS, SearchEngine,
    SearchOptions, SearchResult, printable_ratio, sanitize_content_for_index,
    sanitize_tantivy_query, scrub_text, strip_stopwords, token_coverage,
};
pub use semantic::{SemanticEncoder, SemanticScores};
pub use store::MemoryQuery;
pub use store::MemoryStore;
pub use validator::{MemoryValidator, ValidationVerdict, ValidatorConfig, detect_injection};
pub use vector::{VectorSearchEngine, VectorSearchResult, VectorStore};

#[cfg(feature = "lancedb")]
pub mod lance_vector;
#[cfg(feature = "lancedb")]
pub use lance_vector::LanceVectorStore;
