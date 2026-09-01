//! `WhiteMagic` v4 Memory — LMDB + Tantivy + `LanceDB`
//!
//! Replaces the v2 `SQLite` + FTS5 + Python HNSW stack with:
//! - LMDB for key-value storage (mmap'd, zero-copy reads)
//! - Tantivy for full-text search (Rust, Lucene-class performance)
//! - `LanceDB` for vector similarity search (disk-based HNSW)

#![forbid(unsafe_code)]

pub mod associations;
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
pub mod predictive_cache;
pub mod query_planner;
pub mod recall;
pub mod recall_conformal;
pub mod recovery;
pub mod reindex;
pub mod search;
pub mod semantic;
pub mod store;
pub mod typology;
pub mod validator;
pub mod vector;

pub use associations::{Association, AssociationStore, LinkType};
pub use conversational::{
    ConversationalConfig, ConversationalResult, ConversationalSearch, QueryClassification,
    SearchMetrics,
};
pub use credentials::{ADVICE as CREDENTIAL_ADVICE, credential_shaped_content};
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
pub use search::{
    IndexHealth, MAX_INDEX_CONTENT_LEN, MIN_PRINTABLE_RATIO, STOPWORDS, SearchEngine,
    SearchOptions, SearchResult, sanitize_content_for_index, sanitize_tantivy_query, scrub_text,
    strip_stopwords,
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
