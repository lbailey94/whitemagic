use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Unique identifier for any codex entity
pub type EntityId = String;

/// Central metadata for all extracted content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: EntityId,
    pub source_path: PathBuf,
    pub source_type: SourceType,
    pub title: Option<String>,
    pub author: Option<String>,
    pub created: Option<chrono::DateTime<chrono::Utc>>,
    pub modified: Option<chrono::DateTime<chrono::Utc>>,
    pub content: String,
    pub raw_content: Option<String>, // Original before processing
    pub tags: Vec<String>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub word_count: usize,
    pub token_count: usize,
    pub language: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SourceType {
    Text,
    Markdown,
    Conversation,      // OpenAI archives
    Image,
    Pdf,
    Unknown,
}

/// A semantic chunk of content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Chunk {
    pub id: EntityId,
    pub document_id: EntityId,
    pub content: String,
    pub token_count: usize,
    pub char_count: usize,
    pub parent_id: Option<EntityId>,
    pub children_ids: Vec<EntityId>,
    pub level: ChunkLevel,
    pub position: usize,  // Ordinal position in document
    pub tags: Vec<String>,
    pub embedding: Option<Vec<f32>>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ChunkLevel {
    Paragraph,      // ~100-500 tokens
    Section,        // ~500-1500 tokens
    Document,       // ~1000-5000 tokens
}

/// Configuration for the entire codex pipeline
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodexConfig {
    pub project: ProjectConfig,
    pub extraction: ExtractionConfig,
    pub chunking: ChunkingConfig,
    pub embedding: EmbeddingConfig,
    pub indexing: IndexingConfig,
    pub export: ExportConfig,
    #[serde(default)]
    pub pipeline: PipelineConfig,
    #[serde(default)]
    pub dev: DevConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectConfig {
    pub name: String,
    pub version: String,
    pub description: String,
    pub base_path: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractionConfig {
    pub source_paths: Vec<PathBuf>,
    pub include_patterns: Vec<String>,
    pub exclude_patterns: Vec<String>,
    pub image_processing: ImageProcessingConfig,
    pub preserve_raw: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageProcessingConfig {
    pub enabled: bool,
    pub ocr_enabled: bool,
    #[serde(default)]
    pub multimodal_api: Option<String>, // "openai", "anthropic", etc.
    #[serde(default)]
    pub api_key_env: Option<String>,
    #[serde(default = "default_batch_size")]
    pub batch_size: usize,
    #[serde(default = "default_max_dimension")]
    pub max_dimension: u32,
    #[serde(default = "default_image_formats")]
    pub formats: Vec<String>,
    #[serde(default)]
    pub prompt_template: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkingConfig {
    pub strategy: ChunkStrategy,
    #[serde(default = "default_250")]
    pub paragraph_target_tokens: usize,
    #[serde(default = "default_1000")]
    pub section_target_tokens: usize,
    #[serde(default = "default_4000")]
    pub document_target_tokens: usize,
    #[serde(default = "default_50")]
    pub overlap_tokens: usize,
    #[serde(default = "default_true")]
    pub preserve_frontmatter: bool,
    #[serde(default = "default_true")]
    pub respect_headers: bool,
    #[serde(default)]
    pub conversation: ConversationChunkConfig,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ChunkStrategy {
    #[serde(rename = "paragraph")]
    Paragraph,
    #[serde(rename = "semantic")]
    Semantic,
    #[serde(rename = "hierarchical")]
    Hierarchical,
    #[serde(rename = "conversation")]
    Conversation,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EmbeddingProvider {
    #[serde(rename = "openai")]
    OpenAI,
    #[serde(rename = "openrouter")]
    OpenRouter,
    #[serde(rename = "anthropic")]
    Anthropic,
    LocalOnnx,
    LocalCandle,
}

impl EmbeddingProvider {
    /// Returns the base URL for API-based embedding providers.
    pub fn embedding_url(&self) -> &'static str {
        match self {
            EmbeddingProvider::OpenAI => "https://api.openai.com/v1",
            EmbeddingProvider::OpenRouter => "https://openrouter.ai/api/v1",
            EmbeddingProvider::Anthropic => "https://api.anthropic.com/v1",
            EmbeddingProvider::LocalOnnx | EmbeddingProvider::LocalCandle => "",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddingConfig {
    pub provider: EmbeddingProvider,
    #[serde(default = "default_api_key_env")]
    pub api_key_env: String,
    #[serde(default = "default_openrouter_key_env")]
    pub openrouter_key_env: Option<String>,
    #[serde(default = "default_embedding_model")]
    pub model: String,
    #[serde(default = "default_embedding_model_name")]
    pub embedding_model: String,
    #[serde(default = "default_3072")]
    pub dimensions: usize,
    #[serde(default = "default_100")]
    pub batch_size: usize,
    #[serde(default = "default_10_rps")]
    pub rate_limit_rps: f32,
    #[serde(default = "default_3")]
    pub max_retries: usize,
    #[serde(default = "default_1000_u64")]
    pub retry_delay_ms: u64,
    #[serde(default)]
    pub local_model_path: Option<PathBuf>,
    #[serde(default = "default_4")]
    pub local_threads: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexingConfig {
    #[serde(default = "default_true")]
    pub graph_enabled: bool,
    #[serde(default = "default_true")]
    pub vector_index_enabled: bool,
    #[serde(default = "default_true")]
    pub tag_index_enabled: bool,
    #[serde(default = "default_0_85")]
    pub connection_threshold: f32,
    #[serde(default = "default_10")]
    pub max_connections_per_node: usize,
    #[serde(default)]
    pub database_url: Option<String>,
    #[serde(default)]
    pub tag_clustering: TagClusteringConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportConfig {
    #[serde(default = "default_export_formats")]
    pub formats: Vec<String>,
    #[serde(default)]
    pub vaya_vida: VayaVidaConfig,
    #[serde(default = "default_export_path")]
    pub output_path: PathBuf,
}


#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VayaVidaConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_sphere_version")]
    pub sphere_version: String,
    #[serde(default)]
    pub output_file: Option<String>,
    #[serde(default = "default_true")]
    pub include_library: bool,
    #[serde(default = "default_true")]
    pub include_conversations: bool,
    #[serde(default = "default_true")]
    pub include_research: bool,
    #[serde(default = "default_200")]
    pub max_nodes: usize,
    #[serde(default = "default_fibonacci")]
    pub coordinate_algorithm: String,
    #[serde(default)]
    pub styling: Option<VayaVidaStyling>,
}

impl Default for VayaVidaConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            sphere_version: default_sphere_version(),
            output_file: None,
            include_library: true,
            include_conversations: true,
            include_research: true,
            max_nodes: 200,
            coordinate_algorithm: default_fibonacci(),
            styling: None,
        }
    }
}

impl Default for ProjectConfig {
    fn default() -> Self {
        Self {
            name: "codex".into(),
            version: "0.1.0".into(),
            description: String::new(),
            base_path: PathBuf::from("."),
        }
    }
}

impl Default for ExtractionConfig {
    fn default() -> Self {
        Self {
            source_paths: vec![PathBuf::from("00_source")],
            include_patterns: vec!["*.txt".into(), "*.md".into()],
            exclude_patterns: vec![],
            image_processing: ImageProcessingConfig::default(),
            preserve_raw: false,
        }
    }
}

impl Default for ImageProcessingConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            ocr_enabled: false,
            multimodal_api: None,
            api_key_env: None,
            batch_size: default_batch_size(),
            max_dimension: default_max_dimension(),
            formats: default_image_formats(),
            prompt_template: None,
        }
    }
}

impl Default for ChunkingConfig {
    fn default() -> Self {
        Self {
            strategy: ChunkStrategy::Paragraph,
            paragraph_target_tokens: 250,
            section_target_tokens: 1000,
            document_target_tokens: 4000,
            overlap_tokens: 50,
            preserve_frontmatter: true,
            respect_headers: true,
            conversation: ConversationChunkConfig::default(),
        }
    }
}

impl Default for EmbeddingConfig {
    fn default() -> Self {
        Self {
            provider: EmbeddingProvider::OpenRouter,
            api_key_env: default_api_key_env(),
            openrouter_key_env: default_openrouter_key_env(),
            model: default_embedding_model(),
            embedding_model: default_embedding_model_name(),
            dimensions: 3072,
            batch_size: 100,
            rate_limit_rps: 10.0,
            max_retries: 3,
            retry_delay_ms: 1000,
            local_model_path: None,
            local_threads: 4,
        }
    }
}

impl Default for IndexingConfig {
    fn default() -> Self {
        Self {
            graph_enabled: true,
            vector_index_enabled: true,
            tag_index_enabled: true,
            connection_threshold: 0.85,
            max_connections_per_node: 10,
            database_url: None,
            tag_clustering: TagClusteringConfig::default(),
        }
    }
}

impl Default for ExportConfig {
    fn default() -> Self {
        Self {
            formats: default_export_formats(),
            vaya_vida: VayaVidaConfig::default(),
            output_path: default_export_path(),
        }
    }
}

impl Default for CodexConfig {
    fn default() -> Self {
        Self {
            project: ProjectConfig::default(),
            extraction: ExtractionConfig::default(),
            chunking: ChunkingConfig::default(),
            embedding: EmbeddingConfig::default(),
            indexing: IndexingConfig::default(),
            export: ExportConfig::default(),
            pipeline: PipelineConfig::default(),
            dev: DevConfig::default(),
        }
    }
}

/// Error types for the codex system
#[derive(thiserror::Error, Debug)]
pub enum CodexError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(String),
    
    #[error("Extraction failed for {path}: {reason}")]
    Extraction { path: PathBuf, reason: String },
    
    #[error("Embedding failed: {0}")]
    Embedding(String),
    
    #[error("Configuration error: {0}")]
    Config(String),
    
    #[error("Not found: {0}")]
    NotFound(String),
}

pub type Result<T> = std::result::Result<T, CodexError>;

// --- New config sub-types ---

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationChunkConfig {
    #[serde(default = "default_true")]
    pub preserve_speaker: bool,
    #[serde(default)]
    pub chunk_by_turns: bool,
    #[serde(default = "default_5")]
    pub max_turns_per_chunk: usize,
}

impl Default for ConversationChunkConfig {
    fn default() -> Self {
        Self {
            preserve_speaker: true,
            chunk_by_turns: false,
            max_turns_per_chunk: 5,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TagClusteringConfig {
    #[serde(default = "default_true")]
    pub enabled: bool,
    #[serde(default = "default_louvain")]
    pub algorithm: String,
}

impl Default for TagClusteringConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            algorithm: "louvain".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VayaVidaStyling {
    #[serde(default = "default_library_color")]
    pub library_color: String,
    #[serde(default = "default_conversation_color")]
    pub conversation_color: String,
    #[serde(default = "default_research_color")]
    pub research_color: String,
    #[serde(default = "default_library_char")]
    pub library_char: String,
    #[serde(default = "default_conversation_char")]
    pub conversation_char: String,
    #[serde(default = "default_research_char")]
    pub research_char: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineConfig {
    #[serde(default = "default_pipeline_stages")]
    pub stages: Vec<String>,
    #[serde(default = "default_100")]
    pub checkpoint_interval: usize,
    #[serde(default = "default_true")]
    pub resume_enabled: bool,
    #[serde(default = "default_8")]
    pub workers: usize,
    #[serde(default = "default_4")]
    pub rayon_threads: usize,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            stages: default_pipeline_stages(),
            checkpoint_interval: 100,
            resume_enabled: true,
            workers: 8,
            rayon_threads: 4,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DevConfig {
    #[serde(default = "default_info")]
    pub log_level: String,
    #[serde(default = "default_true")]
    pub progress_bars: bool,
    #[serde(default)]
    pub dry_run: bool,
    #[serde(default)]
    pub sample_size: Option<usize>,
}

impl Default for DevConfig {
    fn default() -> Self {
        Self {
            log_level: "info".to_string(),
            progress_bars: true,
            dry_run: false,
            sample_size: None,
        }
    }
}

// --- Default value functions ---

fn default_true() -> bool { true }
fn default_3() -> usize { 3 }
fn default_4() -> usize { 4 }
fn default_5() -> usize { 5 }
fn default_8() -> usize { 8 }
fn default_10() -> usize { 10 }
fn default_50() -> usize { 50 }
fn default_100() -> usize { 100 }
fn default_200() -> usize { 200 }
fn default_250() -> usize { 250 }
fn default_1000() -> usize { 1000 }
fn default_4000() -> usize { 4000 }
fn default_3072() -> usize { 3072 }
fn default_1000_u64() -> u64 { 1000 }
fn default_batch_size() -> usize { 10 }
fn default_max_dimension() -> u32 { 2048 }
fn default_image_formats() -> Vec<String> { vec!["png".into(), "jpg".into(), "jpeg".into(), "webp".into()] }
fn default_api_key_env() -> String { "ANTHROPIC_API_KEY".into() }
fn default_openrouter_key_env() -> Option<String> { Some("OPENROUTER_API_KEY".into()) }
fn default_embedding_model() -> String { "claude-3-sonnet-20240229".into() }
fn default_embedding_model_name() -> String { "text-embedding-3-large".into() }
fn default_10_rps() -> f32 { 10.0 }
fn default_0_85() -> f32 { 0.85 }
fn default_sphere_version() -> String { "v5.1.0".into() }
fn default_fibonacci() -> String { "fibonacci".into() }
fn default_louvain() -> String { "louvain".into() }
fn default_info() -> String { "info".into() }
fn default_export_path() -> PathBuf { PathBuf::from("50_export") }
fn default_export_formats() -> Vec<String> { vec!["jsonl".into(), "json".into(), "yaml".into()] }
fn default_pipeline_stages() -> Vec<String> { vec!["extract".into(), "chunk".into(), "embed".into(), "index".into(), "consolidate".into(), "export".into()] }
fn default_library_color() -> String { "#8b5cf6".into() }
fn default_conversation_color() -> String { "#06b6d4".into() }
fn default_research_color() -> String { "#f59e0b".into() }
fn default_library_char() -> String { "◆".into() }
fn default_conversation_char() -> String { "◇".into() }
fn default_research_char() -> String { "○".into() }

// --- Config loading ---

/// Load configuration from a YAML file.
pub fn load_config(path: &Path) -> Result<CodexConfig> {
    let contents = std::fs::read_to_string(path)
        .map_err(|e| CodexError::Config(format!("Failed to read config {:?}: {}", path, e)))?;
    let config: CodexConfig = serde_yaml::from_str(&contents)
        .map_err(|e| CodexError::Config(format!("Failed to parse config {:?}: {}", path, e)))?;
    Ok(config)
}

/// Load configuration with fallback: try given path, then `config/codex.yaml` relative to base_path.
/// If no config file is found, returns a default config with the given base_path.
pub fn load_config_with_fallback(config_path: Option<&Path>, base_path: &Path) -> Result<CodexConfig> {
    if let Some(path) = config_path {
        return load_config(path);
    }
    let default_path = base_path.join("config").join("codex.yaml");
    if default_path.exists() {
        load_config(&default_path)
    } else {
        let mut config = CodexConfig::default();
        config.project.base_path = base_path.to_path_buf();
        Ok(config)
    }
}

// --- Utility functions ---

/// Infer the source corpus from a document/chunk ID prefix.
pub fn infer_source(id: &str) -> &'static str {
    if id.starts_with("conv-") || id.starts_with("doc-conv-") {
        "conversations"
    } else if id.starts_with("research-") || id.starts_with("doc-research-") {
        "research"
    } else {
        "library"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_document_creation() {
        let doc = Document {
            id: "test-123".to_string(),
            source_path: PathBuf::from("test.md"),
            source_type: SourceType::Markdown,
            title: Some("Test Title".to_string()),
            author: None,
            created: None,
            modified: None,
            content: "Test content".to_string(),
            raw_content: None,
            tags: vec!["test".to_string()],
            metadata: HashMap::new(),
            word_count: 2,
            token_count: 3,
            language: Some("en".to_string()),
        };
        assert_eq!(doc.id, "test-123");
        assert_eq!(doc.title.as_ref().unwrap(), "Test Title");
        assert_eq!(doc.word_count, 2);
    }

    #[test]
    fn test_chunk_creation() {
        let chunk = Chunk {
            id: "chunk-1".to_string(),
            document_id: "doc-1".to_string(),
            content: "Test chunk content".to_string(),
            token_count: 3,
            char_count: 18,
            parent_id: None,
            children_ids: vec![],
            level: ChunkLevel::Paragraph,
            position: 0,
            tags: vec![],
            embedding: None,
            metadata: HashMap::new(),
        };
        assert_eq!(chunk.level, ChunkLevel::Paragraph);
        assert_eq!(chunk.position, 0);
    }

    #[test]
    fn test_source_type_serialization() {
        let text = SourceType::Text;
        let json = serde_json::to_string(&text).unwrap();
        assert_eq!(json, "\"text\"");

        let de: SourceType = serde_json::from_str("\"markdown\"").unwrap();
        assert_eq!(de, SourceType::Markdown);
    }

    #[test]
    fn test_chunk_level_serialization() {
        let level = ChunkLevel::Section;
        let json = serde_json::to_string(&level).unwrap();
        assert_eq!(json, "\"section\"");
    }

    #[test]
    fn test_error_display() {
        let err = CodexError::NotFound("test.txt".to_string());
        assert_eq!(err.to_string(), "Not found: test.txt");
    }

    #[test]
    fn test_config_defaults() {
        let config = CodexConfig::default();
        assert_eq!(config.project.name, "codex");
        assert_eq!(config.project.version, "0.1.0");
        assert_eq!(config.embedding.dimensions, 3072);
        assert_eq!(config.pipeline.stages.len(), 6);
        assert_eq!(config.dev.log_level, "info");
    }

    #[test]
    fn test_load_config_with_fallback() {
        let base = PathBuf::from("/home/lucas/Desktop/CODEX");
        let config = load_config_with_fallback(None, &base).unwrap();
        assert_eq!(config.project.name, "Lucas Research Codex");
        assert_eq!(config.embedding.embedding_model, "text-embedding-3-large");
        assert_eq!(config.export.vaya_vida.enabled, true);
    }

    #[test]
    fn test_infer_source() {
        assert_eq!(infer_source("conv-123"), "conversations");
        assert_eq!(infer_source("doc-conv-456"), "conversations");
        assert_eq!(infer_source("research-abc"), "research");
        assert_eq!(infer_source("doc-research-xyz"), "research");
        assert_eq!(infer_source("lib-foo"), "library");
        assert_eq!(infer_source("anything-else"), "library");
    }
}
