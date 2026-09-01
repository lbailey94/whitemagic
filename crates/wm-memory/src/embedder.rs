//! Local text embedder — generates vector embeddings for semantic search.
//!
//! Ported from v2's `local_embedder.py` (313 lines). Provides a trait-based
//! embedder abstraction with two implementations:
//!
//! - `HttpEmbedder`: Calls llama-server's `/v1/embeddings` endpoint (preferred,
//!   no model download needed — uses the already-running llama-server)
//! - `StubEmbedder`: Hash-based pseudo-embeddings for testing/fallback
//!
//! Future: An `ort` (ONNX Runtime) embedder can implement the same trait for
//! fully local embeddings without a server dependency.
//!
//! # Environment Variables
//!
//! | Variable | Default | Description |
//! |----------|---------|-------------|
//! | `WM_EMBEDDER_ENDPOINT` | — | llama-server HTTP URL (e.g. `http://localhost:8080`) |
//! | `WM_EMBEDDER_MODEL` | `local` | Model name for the embeddings API |
//! | `WM_EMBEDDER_DIM` | `384` | Expected embedding dimensionality |
//! | `WM_EMBEDDER_TIMEOUT_MS` | `30000` | Request timeout in milliseconds |

#![allow(clippy::cast_possible_wrap)]

use serde::{Deserialize, Serialize};
use std::time::Duration;
use wm_core::{CoreError, Result};

/// Trait for text embedding providers.
///
/// Implementations:
/// - `HttpEmbedder` — llama-server `/v1/embeddings` endpoint
/// - `StubEmbedder` — hash-based pseudo-embeddings (for testing)
pub trait Embedder: Send + Sync {
    /// Embed a batch of texts into f32 vectors.
    ///
    /// Returns one vector per input text. All vectors have the same dimensionality.
    fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>>;

    /// Embed a single text.
    fn embed(&self, text: &str) -> Result<Vec<f32>> {
        self.embed_batch(&[text])?
            .into_iter()
            .next()
            .ok_or_else(|| CoreError::Memory("embedder returned empty result".into()))
    }

    /// Embed a single query (alias for `embed`).
    fn embed_query(&self, query: &str) -> Result<Vec<f32>> {
        self.embed(query)
    }

    /// Get the embedding dimensionality.
    fn dimension(&self) -> usize;

    /// Whether this embedder is available (model loaded, server reachable).
    fn is_available(&self) -> bool;

    /// Name of this embedder backend.
    fn backend_name(&self) -> &'static str;

    /// Identity used to namespace the persistent embedding cache.
    ///
    /// Vectors for identical text differ across models, quantization, and
    /// endpoints, so the cache key must carry this — switching models must
    /// never serve stale vectors. Default is the backend name.
    fn cache_namespace(&self) -> String {
        self.backend_name().to_string()
    }

    /// Preferred batch granularity in TEXTS for batch write paths.
    ///
    /// The write path's char-chunking exists for HTTP token limits; local
    /// engines have no such limit and want bigger batches so session
    /// pools fan out efficiently (4-7 texts per call starves each shard).
    /// `usize::MAX` = char-chunking only (the HTTP shape).
    fn preferred_max_batch_texts(&self) -> usize {
        usize::MAX
    }
}

/// Configuration for the HTTP-based embedder.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbedderConfig {
    /// llama-server HTTP API URL (e.g. `http://localhost:8080`).
    pub endpoint: String,
    /// Model name for the embeddings API.
    pub model: String,
    /// Expected embedding dimensionality.
    pub dimension: usize,
    /// Request timeout.
    pub timeout: Duration,
}

impl EmbedderConfig {
    /// Create a config from environment variables.
    ///
    /// Returns `None` if `WM_EMBEDDER_ENDPOINT` is not set or if the endpoint
    /// fails SSRF validation (non-HTTP scheme, metadata endpoint, etc.).
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let endpoint = std::env::var("WM_EMBEDDER_ENDPOINT").ok()?;
        if !is_endpoint_safe(&endpoint) {
            tracing::warn!(
                "embedder endpoint rejected by SSRF validation: {}",
                endpoint
            );
            return None;
        }
        let model = std::env::var("WM_EMBEDDER_MODEL").unwrap_or_else(|_| "local".into());
        let dimension = std::env::var("WM_EMBEDDER_DIM")
            .ok()
            .and_then(|v| v.parse::<usize>().ok())
            .unwrap_or(384);
        let timeout_ms = std::env::var("WM_EMBEDDER_TIMEOUT_MS")
            .ok()
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(30_000);

        Some(Self {
            endpoint,
            model,
            dimension,
            timeout: Duration::from_millis(timeout_ms),
        })
    }
}

/// Validate an embedder endpoint URL for SSRF safety.
///
/// Unlike `wm_core::security::is_url_safe`, this allows localhost and private
/// IPs because the embedder is typically a local llama-server. It blocks:
/// - Non-HTTP(S) schemes (file://, gopher://, ftp://, etc.)
/// - Cloud metadata endpoints (169.254.169.254, metadata.google.internal)
/// - Malformed URLs
#[must_use]
pub fn is_endpoint_safe(endpoint: &str) -> bool {
    // Must start with http:// or https://
    if !endpoint.starts_with("http://") && !endpoint.starts_with("https://") {
        return false;
    }

    // Extract host
    let without_scheme = endpoint
        .strip_prefix("http://")
        .or_else(|| endpoint.strip_prefix("https://"))
        .unwrap_or(endpoint);

    let host_end = without_scheme
        .find(['/', '?', '#'])
        .unwrap_or(without_scheme.len());
    let host_port = &without_scheme[..host_end];

    // Handle IPv6 bracket notation
    let host = if host_port.starts_with('[') {
        if let Some(end) = host_port.find(']') {
            &host_port[1..end]
        } else {
            return false; // Malformed IPv6
        }
    } else {
        host_port.rsplit_once(':').map_or(host_port, |(h, _)| h)
    };

    if host.is_empty() {
        return false;
    }

    // Block cloud metadata endpoints
    let lower = host.to_ascii_lowercase();
    if matches!(
        lower.as_str(),
        "metadata.google.internal"
            | "metadata.aws.internal"
            | "metadata"
            | "169.254.169.254"
            | "169.254.170.2"
    ) {
        return false;
    }

    true
}

/// HTTP-based embedder using llama-server's `/v1/embeddings` endpoint.
///
/// Requires llama-server started with `--embeddings` flag.
/// Dimension depends on the loaded GGUF model (e.g. 384 for bge-small,
/// 768 for bge-base, 1024 for bge-large).
pub struct HttpEmbedder {
    config: EmbedderConfig,
    agent: ureq::Agent,
    available: bool,
}

impl HttpEmbedder {
    /// Create a new HTTP embedder with the given config.
    #[must_use]
    pub fn new(config: EmbedderConfig) -> Self {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(config.timeout))
            .build()
            .new_agent();
        Self {
            config,
            agent,
            available: true,
        }
    }

    /// Create from environment variables, if configured.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        EmbedderConfig::from_env().map(Self::new)
    }

    /// Build the embeddings endpoint URL.
    fn embeddings_url(&self) -> String {
        if self.config.endpoint.ends_with("/v1/embeddings") {
            self.config.endpoint.clone()
        } else if self.config.endpoint.ends_with('/') {
            format!("{}v1/embeddings", self.config.endpoint)
        } else {
            format!("{}/v1/embeddings", self.config.endpoint)
        }
    }
}

impl Embedder for HttpEmbedder {
    fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }

        let url = self.embeddings_url();

        // OpenAI-compatible embeddings request
        let request = EmbeddingsRequest {
            model: &self.config.model,
            input: texts,
        };

        let response = self
            .agent
            .post(&url)
            .header("Content-Type", "application/json")
            .send_json(&request)
            .map_err(|e| CoreError::Memory(format!("Embedder HTTP error: {e}")))?;

        let embed_resp: EmbeddingsResponse = response
            .into_body()
            .read_json()
            .map_err(|e| CoreError::Memory(format!("Embedder response parse error: {e}")))?;

        let vectors: Vec<Vec<f32>> = embed_resp.data.into_iter().map(|d| d.embedding).collect();

        if vectors.len() != texts.len() {
            return Err(CoreError::Memory(format!(
                "Embedder returned {} vectors for {} inputs",
                vectors.len(),
                texts.len()
            )));
        }

        Ok(vectors)
    }

    fn dimension(&self) -> usize {
        self.config.dimension
    }

    fn is_available(&self) -> bool {
        self.available
    }

    fn backend_name(&self) -> &'static str {
        "http"
    }

    fn cache_namespace(&self) -> String {
        format!("http:{}:{}", self.config.endpoint, self.config.model)
    }
}

/// OpenAI-compatible embeddings request.
#[derive(Debug, Serialize)]
struct EmbeddingsRequest<'a> {
    model: &'a str,
    input: &'a [&'a str],
}

/// OpenAI-compatible embeddings response.
#[derive(Debug, Deserialize)]
struct EmbeddingsResponse {
    data: Vec<EmbeddingData>,
}

#[derive(Debug, Deserialize)]
struct EmbeddingData {
    embedding: Vec<f32>,
}

/// Stub embedder — hash-based pseudo-embeddings for testing/fallback.
///
/// Generates deterministic embeddings from text content using SHA-256 hashing.
/// Not useful for real semantic search, but provides a fallback when no
/// embedder is available and allows tests to run without a server.
pub struct StubEmbedder {
    dimension: usize,
}

impl StubEmbedder {
    /// Create a new stub embedder with the given dimensionality.
    #[must_use]
    pub const fn new(dimension: usize) -> Self {
        Self { dimension }
    }
}

impl Default for StubEmbedder {
    fn default() -> Self {
        Self::new(384)
    }
}

impl Embedder for StubEmbedder {
    fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>> {
        use sha2::{Digest, Sha256};

        let mut results = Vec::with_capacity(texts.len());
        for text in texts {
            let mut hasher = Sha256::new();
            hasher.update(text.as_bytes());
            let hash = hasher.finalize();

            // Expand hash to fill the desired dimension
            let mut embedding = Vec::with_capacity(self.dimension);
            for i in 0..self.dimension {
                let byte = f32::from(hash[i % hash.len()]);
                embedding.push(byte.mul_add(2.0 / 255.0, -1.0)); // Normalize to [-1, 1]
            }
            results.push(embedding);
        }
        Ok(results)
    }

    fn dimension(&self) -> usize {
        self.dimension
    }

    fn is_available(&self) -> bool {
        true
    }

    fn backend_name(&self) -> &'static str {
        "stub"
    }
}

/// ONNX Runtime-based embedder using `fastembed-rs`.
///
/// Provides fully local embeddings without a server dependency.
/// Downloads model files on first use (cached thereafter).
///
/// Requires the `onnx` feature to be enabled:
/// ```toml
/// wm-memory = { features = ["onnx"] }
/// ```
///
/// Default model: BAAI/bge-small-en-v1.5 (384 dimensions, ~130MB).
///
/// # Environment Variables
///
/// | Variable | Default | Description |
/// |----------|---------|-------------|
/// | `WM_EMBEDDER_ORT_MODEL` | `BAAI/bge-small-en-v1.5` | Model name (`-q` suffixes select INT8-quantized variants, e.g. `bge-small-q`) |
/// | `WM_EMBEDDER_CACHE_DIR` | — | Cache directory for model files |
/// | `WM_EMBEDDER_ORT_THREADS` | min(logical cores, 4) | Number of intra-op threads |
#[cfg(feature = "onnx")]
pub struct OrtEmbedder {
    /// Sharded session pool (v26 `parallel/pools.py` idea, finally wired):
    /// one ORT session per shard, mutex per shard — a batch fans out
    /// across shards concurrently instead of serializing on one session.
    /// Ingest-scale workloads are the target; single-text calls use
    /// shard 0 directly.
    shards: Vec<std::sync::Mutex<Option<fastembed::TextEmbedding>>>,
    model_name: String,
    cache_dir: Option<std::path::PathBuf>,
    threads: usize,
    dimension: usize,
    available: std::sync::atomic::AtomicBool,
    /// Pinned fastembed batch_size (32–64 band per the ship list).
    batch_size: usize,
}

/// Default ORT intra-op thread count.
///
/// Defaulting to every logical core (hyperthreads included) saturates small
/// machines — on a 4C/8T laptop the FP32 embedder at 8 threads drove the
/// box into swap thrash and OOM (see `docs/POLYGLOT_SIMD_MEMORY_STRATEGY.md`).
/// Physical-core count is not exposed by std; `min(logical, 4)` approximates
/// it and stays conservative on both small and large machines. Explicit
/// `WM_EMBEDDER_ORT_THREADS` always wins over this default (values above 4
/// are honored explicitly — they raise the TOTAL intra-op budget).
#[cfg(feature = "onnx")]
fn default_intra_threads() -> usize {
    std::thread::available_parallelism()
        .map(std::num::NonZero::get)
        .unwrap_or(4)
        .min(4)
}

#[cfg(feature = "onnx")]
impl OrtEmbedder {
    /// Create a new ONNX embedder with the given configuration.
    #[must_use]
    pub fn new(
        model_name: &str,
        cache_dir: Option<std::path::PathBuf>,
        threads: usize,
        dimension: usize,
    ) -> Self {
        let threads = threads.max(1);
        // Total intra-op budget = `threads`, distributed across the pool.
        // MEASURED on the reference machine (2026-09-01, ingest probe +
        // pool-shape microbench): in-server, 2 shards × intra/2 ≈ parity
        // with the legacy single session, while full fan-out (4×1) LOSES
        // ~11% to tokio-worker contention, and 1 shard pays the cache's
        // small tax. So the default halves the budget into shards,
        // capped at 4; `WM_EMBEDDER_ORT_SHARDS` overrides explicitly
        // (1 = legacy single-session shape, higher = fuller fan-out for
        // batch-heavy hosts).
        let shard_count = (threads / 2).clamp(1, 4);
        let shards = (0..shard_count)
            .map(|_| std::sync::Mutex::new(None))
            .collect();
        Self {
            shards,
            model_name: model_name.to_string(),
            cache_dir,
            threads,
            dimension,
            available: std::sync::atomic::AtomicBool::new(false),
            batch_size: 32,
        }
    }

    /// Create from environment variables.
    ///
    /// Returns `None` if the `onnx` feature is not enabled or model cannot be loaded.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let model_name = std::env::var("WM_EMBEDDER_ORT_MODEL")
            .unwrap_or_else(|_| "BAAI/bge-small-en-v1.5".into());
        let cache_dir = std::env::var("WM_EMBEDDER_CACHE_DIR")
            .ok()
            .map(std::path::PathBuf::from);
        let threads = std::env::var("WM_EMBEDDER_ORT_THREADS")
            .ok()
            .and_then(|v| v.parse::<usize>().ok())
            .unwrap_or_else(default_intra_threads);
        let dimension = std::env::var("WM_EMBEDDER_DIM")
            .ok()
            .and_then(|v| v.parse::<usize>().ok())
            .unwrap_or(384);

        Some(Self::new(&model_name, cache_dir, threads, dimension))
    }

    /// Override the derived shard count (`WM_EMBEDDER_ORT_SHARDS`).
    ///
    /// The derived count (min(threads, logical cores)) is a reasonable
    /// default, but ORT scaling is model- and workload-dependent — this
    /// explicit override exists so the pool shape can be tuned per
    /// machine without recompiling (1 = legacy single-session shape).
    #[must_use]
    pub fn with_shard_override(mut self, shards: usize) -> Self {
        self.shards = (0..shards.max(1))
            .map(|_| std::sync::Mutex::new(None))
            .collect();
        self
    }

    /// Map model name string to fastembed EmbeddingModel enum.
    ///
    /// Names ending in `-q` select INT8-quantized variants: ~75% smaller
    /// weights and lower memory bandwidth than FP32, executing via CPU INT8
    /// SIMD. Prefer them on modest hardware (see
    /// `docs/POLYGLOT_SIMD_MEMORY_STRATEGY.md` — FP32 + unbounded threads
    /// OOM-crashed a 16GB machine during benchmark runs).
    fn resolve_model(&self) -> Option<fastembed::EmbeddingModel> {
        match self.model_name.as_str() {
            "BAAI/bge-small-en-v1.5" | "bge-small-en-v1.5" | "bge-small" => {
                Some(fastembed::EmbeddingModel::BGESmallENV15)
            }
            "BAAI/bge-small-en-v1.5-q" | "bge-small-en-v1.5-q" | "bge-small-q" => {
                Some(fastembed::EmbeddingModel::BGESmallENV15Q)
            }
            "BAAI/bge-base-en-v1.5" | "bge-base-en-v1.5" | "bge-base" => {
                Some(fastembed::EmbeddingModel::BGEBaseENV15)
            }
            "BAAI/bge-base-en-v1.5-q" | "bge-base-en-v1.5-q" | "bge-base-q" => {
                Some(fastembed::EmbeddingModel::BGEBaseENV15Q)
            }
            "BAAI/bge-large-en-v1.5" | "bge-large-en-v1.5" | "bge-large" => {
                Some(fastembed::EmbeddingModel::BGELargeENV15)
            }
            "sentence-transformers/all-MiniLM-L6-v2" | "all-MiniLM-L6-v2" | "minilm" => {
                Some(fastembed::EmbeddingModel::AllMiniLML6V2)
            }
            "sentence-transformers/all-MiniLM-L6-v2-q" | "all-MiniLM-L6-v2-q" | "minilm-q" => {
                Some(fastembed::EmbeddingModel::AllMiniLML6V2Q)
            }
            "sentence-transformers/all-MiniLM-L12-v2" | "all-MiniLM-L12-v2" => {
                Some(fastembed::EmbeddingModel::AllMiniLML12V2)
            }
            "nomic-ai/nomic-embed-text-v1.5" | "nomic-embed-text-v1.5" | "nomic" => {
                Some(fastembed::EmbeddingModel::NomicEmbedTextV15)
            }
            _ => {
                tracing::warn!(
                    "unknown embedder model '{}', falling back to bge-small-en-v1.5",
                    self.model_name
                );
                Some(fastembed::EmbeddingModel::BGESmallENV15)
            }
        }
    }

    /// Number of intra-op threads configured for inference (the TOTAL
    /// budget across the session pool).
    #[cfg(feature = "onnx")]
    #[must_use]
    pub const fn threads(&self) -> usize {
        self.threads
    }

    /// Number of ORT sessions in the pool.
    #[cfg(feature = "onnx")]
    #[must_use]
    pub fn shard_count(&self) -> usize {
        self.shards.len()
    }

    /// Intra-op threads per session (the budget divided across the pool).
    #[cfg(feature = "onnx")]
    #[must_use]
    fn intra_per_shard(&self) -> usize {
        (self.threads / self.shards.len().max(1)).max(1)
    }

    /// Lazy-load the pool on first use: every shard gets its own session
    /// over the shared on-disk model files.
    fn ensure_loaded(&self) -> bool {
        // Fast path: already loaded
        if self.available.load(std::sync::atomic::Ordering::Relaxed) {
            return true;
        }

        let intra = self.intra_per_shard();
        let mut loaded = Vec::with_capacity(self.shards.len());
        for _ in 0..self.shards.len() {
            let Some(embedding_model) = self.resolve_model() else {
                self.available
                    .store(false, std::sync::atomic::Ordering::Relaxed);
                return false;
            };
            let mut options = fastembed::TextInitOptions::new(embedding_model)
                .with_show_download_progress(false)
                .with_intra_threads(intra);

            if let Some(ref cache_dir) = self.cache_dir {
                options = options.with_cache_dir(cache_dir.clone());
            }

            match fastembed::TextEmbedding::try_new(options) {
                Ok(model) => loaded.push(Some(model)),
                Err(e) => {
                    tracing::warn!("failed to load ONNX embedding model: {e}");
                    self.available
                        .store(false, std::sync::atomic::Ordering::Relaxed);
                    return false;
                }
            }
        }

        {
            for (shard, model) in self.shards.iter().zip(loaded) {
                let mut guard = shard.lock().expect("shard mutex poisoned");
                *guard = model;
            }
        }
        self.available
            .store(true, std::sync::atomic::Ordering::Relaxed);
        tracing::info!(
            "ONNX embedding model loaded: {} ({} session shards × {} intra threads, dim={})",
            self.model_name,
            self.shards.len(),
            intra,
            self.dimension
        );
        true
    }
}

#[cfg(feature = "onnx")]
impl Embedder for OrtEmbedder {
    fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(Vec::new());
        }

        if !self.ensure_loaded() {
            return Err(CoreError::Memory(
                "ONNX embedder model not available".into(),
            ));
        }

        let owned_texts: Vec<String> = texts.iter().map(|t| (*t).to_string()).collect();

        // Single text (the query path): no fan-out machinery, shard 0.
        if owned_texts.len() == 1 {
            let mut guard = self.shards[0].lock().expect("shard mutex poisoned");
            let Some(ref mut model) = guard.as_mut() else {
                return Err(CoreError::Memory("ONNX embedder model not loaded".into()));
            };
            let embeddings = model
                .embed(owned_texts, Some(self.batch_size))
                .map_err(|e| CoreError::Memory(format!("ONNX embedding error: {e}")))?;
            return Ok(embeddings);
        }

        // Fan out: round-robin split across shards, each embedding its
        // subset concurrently on its own session (no cross-shard locks).
        let shard_count = self.shards.len();
        let mut split: Vec<Vec<String>> = vec![Vec::new(); shard_count];
        for (i, text) in owned_texts.into_iter().enumerate() {
            split[i % shard_count].push(text);
        }

        let results: Vec<Result<Vec<Vec<f32>>>> = std::thread::scope(|scope| {
            let handles: Vec<_> = split
                .into_iter()
                .zip(&self.shards)
                .map(|(subset, shard)| {
                    scope.spawn(move || {
                        let mut guard = shard.lock().expect("shard mutex poisoned");
                        let Some(ref mut model) = guard.as_mut() else {
                            return Err(CoreError::Memory("ONNX embedder model not loaded".into()));
                        };
                        model
                            .embed(subset, Some(self.batch_size))
                            .map_err(|e| CoreError::Memory(format!("ONNX embedding error: {e}")))
                    })
                })
                .collect();
            handles
                .into_iter()
                .map(|h| h.join().expect("shard worker panicked"))
                .collect()
        });

        // Reassemble in the original order: position i came from shard
        // i % shard_count (round-robin split is deterministic, so the
        // interleave is too).
        let mut per_shard: Vec<std::collections::VecDeque<Vec<f32>>> = results
            .into_iter()
            .map(|r| {
                r.map(|vectors| {
                    vectors
                        .into_iter()
                        .collect::<std::collections::VecDeque<_>>()
                })
            })
            .collect::<Result<Vec<_>>>()?;
        let mut out: Vec<Vec<f32>> = Vec::with_capacity(texts.len());
        for i in 0..texts.len() {
            let shard_idx = i % shard_count;
            let Some(vector) = per_shard[shard_idx].pop_front() else {
                return Err(CoreError::Memory(format!(
                    "embed_batch shard {shard_idx} returned too few vectors"
                )));
            };
            out.push(vector);
        }

        if out.len() != texts.len() {
            return Err(CoreError::Memory(format!(
                "embed_batch returned {} vectors for {} inputs",
                out.len(),
                texts.len()
            )));
        }
        Ok(out)
    }

    fn dimension(&self) -> usize {
        self.dimension
    }

    fn is_available(&self) -> bool {
        self.ensure_loaded()
    }

    fn backend_name(&self) -> &'static str {
        "onnx"
    }

    fn cache_namespace(&self) -> String {
        // Dimension included: quantization or an unknown-name fallback can
        // change the effective model under the same requested name.
        format!("onnx:{}:{}", self.model_name, self.dimension)
    }

    fn preferred_max_batch_texts(&self) -> usize {
        // Big enough that each session shard sees a real batch (32+ texts)
        // after the round-robin split.
        128
    }
}

/// Create an embedder from environment configuration, with fallback chain.
///
/// Priority (when `onnx` feature is enabled):
/// 1. `OrtEmbedder` — if `WM_EMBEDDER_ORT_MODEL` is set or `onnx` feature is on
/// 2. `HttpEmbedder` — if `WM_EMBEDDER_ENDPOINT` is set
/// 3. `StubEmbedder` — always available fallback
///
/// Without `onnx` feature:
/// 1. `HttpEmbedder` — if `WM_EMBEDDER_ENDPOINT` is set
/// 2. `StubEmbedder` — fallback
#[must_use]
pub fn create_embedder() -> Box<dyn Embedder> {
    #[cfg(feature = "onnx")]
    {
        let prefer_ort = std::env::var("WM_EMBEDDER_BACKEND")
            .map(|v| v == "onnx" || v == "ort")
            .unwrap_or(false);

        if prefer_ort {
            if let Some(mut ort) = OrtEmbedder::from_env() {
                if let Ok(shards) = std::env::var("WM_EMBEDDER_ORT_SHARDS") {
                    if let Ok(n) = shards.parse::<usize>() {
                        ort = ort.with_shard_override(n);
                    }
                }
                tracing::info!(
                    "onnx embedder configured (dim={}, shards={})",
                    ort.dimension(),
                    ort.shard_count()
                );
                return Box::new(ort);
            }
        }
    }

    if let Some(http) = HttpEmbedder::from_env() {
        tracing::info!("http embedder configured (dim={})", http.dimension());
        return Box::new(http);
    }

    #[cfg(feature = "onnx")]
    {
        // Try ONNX as default when feature is enabled and no HTTP endpoint
        if let Some(ort) = OrtEmbedder::from_env() {
            tracing::info!(
                "onnx embedder configured as default (dim={})",
                ort.dimension()
            );
            return Box::new(ort);
        }
    }

    tracing::info!("no embedder endpoint configured, using stub embedder");
    Box::new(StubEmbedder::default())
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- StubEmbedder tests ---

    #[test]
    fn stub_embedder_dimension() {
        let embedder = StubEmbedder::new(128);
        assert_eq!(embedder.dimension(), 128);
    }

    #[test]
    fn stub_embedder_single() {
        let embedder = StubEmbedder::new(64);
        let vec = embedder.embed("hello world").unwrap();
        assert_eq!(vec.len(), 64);
        // Values should be in [-1, 1]
        for v in &vec {
            assert!(*v >= -1.0 && *v <= 1.0);
        }
    }

    #[test]
    fn stub_embedder_batch() {
        let embedder = StubEmbedder::new(32);
        let texts = ["hello", "world", "test"];
        let vectors = embedder.embed_batch(&texts).unwrap();
        assert_eq!(vectors.len(), 3);
        for v in &vectors {
            assert_eq!(v.len(), 32);
        }
    }

    #[test]
    fn stub_embedder_deterministic() {
        let embedder = StubEmbedder::new(64);
        let v1 = embedder.embed("same text").unwrap();
        let v2 = embedder.embed("same text").unwrap();
        assert_eq!(v1, v2);
    }

    #[test]
    fn stub_embedder_different_texts_differ() {
        let embedder = StubEmbedder::new(64);
        let v1 = embedder.embed("hello").unwrap();
        let v2 = embedder.embed("world").unwrap();
        assert_ne!(v1, v2);
    }

    #[test]
    fn stub_embedder_empty_batch() {
        let embedder = StubEmbedder::new(64);
        let vectors = embedder.embed_batch(&[]).unwrap();
        assert!(vectors.is_empty());
    }

    #[test]
    fn stub_embedder_is_available() {
        let embedder = StubEmbedder::new(64);
        assert!(embedder.is_available());
    }

    #[test]
    fn stub_embedder_backend_name() {
        let embedder = StubEmbedder::new(64);
        assert_eq!(embedder.backend_name(), "stub");
    }

    #[test]
    fn stub_embedder_default_dimension() {
        let embedder = StubEmbedder::default();
        assert_eq!(embedder.dimension(), 384);
    }

    // --- HttpEmbedder tests ---

    #[test]
    fn http_embedder_config_from_env_absent() {
        // Test the config struct directly
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(30),
        };
        assert_eq!(config.endpoint, "http://localhost:8080");
        assert_eq!(config.model, "local");
        assert_eq!(config.dimension, 384);
    }

    #[test]
    fn http_embedder_embeddings_url() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(30),
        };
        let embedder = HttpEmbedder::new(config);
        assert_eq!(
            embedder.embeddings_url(),
            "http://localhost:8080/v1/embeddings"
        );
    }

    #[test]
    fn http_embedder_embeddings_url_trailing_slash() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080/".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(30),
        };
        let embedder = HttpEmbedder::new(config);
        assert_eq!(
            embedder.embeddings_url(),
            "http://localhost:8080/v1/embeddings"
        );
    }

    #[test]
    fn http_embedder_embeddings_url_full_path() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080/v1/embeddings".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(30),
        };
        let embedder = HttpEmbedder::new(config);
        assert_eq!(
            embedder.embeddings_url(),
            "http://localhost:8080/v1/embeddings"
        );
    }

    #[test]
    fn http_embedder_dimension() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080".into(),
            model: "local".into(),
            dimension: 768,
            timeout: Duration::from_secs(10),
        };
        let embedder = HttpEmbedder::new(config);
        assert_eq!(embedder.dimension(), 768);
    }

    #[test]
    fn http_embedder_backend_name() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(10),
        };
        let embedder = HttpEmbedder::new(config);
        assert_eq!(embedder.backend_name(), "http");
    }

    #[test]
    fn http_embedder_is_available() {
        let config = EmbedderConfig {
            endpoint: "http://localhost:8080".into(),
            model: "local".into(),
            dimension: 384,
            timeout: Duration::from_secs(10),
        };
        let embedder = HttpEmbedder::new(config);
        assert!(embedder.is_available());
    }

    // --- create_embedder tests ---

    #[test]
    fn create_embedder_falls_back_to_stub() {
        // Without WM_EMBEDDER_ENDPOINT set, should return stub (or onnx if feature enabled)
        let embedder = create_embedder();
        let name = embedder.backend_name();
        assert!(name == "stub" || name == "http" || name == "onnx");
    }

    // --- Embedder trait tests ---

    #[test]
    fn embedder_trait_object() {
        let embedder: Box<dyn Embedder> = Box::new(StubEmbedder::new(128));
        assert_eq!(embedder.dimension(), 128);
        let vec = embedder.embed("test").unwrap();
        assert_eq!(vec.len(), 128);
    }

    #[test]
    fn embedder_embed_query() {
        let embedder = StubEmbedder::new(64);
        let v1 = embedder.embed("hello").unwrap();
        let v2 = embedder.embed_query("hello").unwrap();
        assert_eq!(v1, v2);
    }

    // --- OrtEmbedder tests (only when onnx feature is enabled) ---

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_backend_name() {
        let embedder = OrtEmbedder::new("bge-small", None, 2, 384);
        assert_eq!(embedder.backend_name(), "onnx");
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_resolves_quantized_models() {
        // INT8 variants must resolve to their Q enum counterparts, not
        // silently fall back to FP32 bge-small.
        let q = OrtEmbedder::new("bge-small-q", None, 2, 384);
        assert!(matches!(
            q.resolve_model(),
            Some(fastembed::EmbeddingModel::BGESmallENV15Q)
        ));
        let q_full = OrtEmbedder::new("BAAI/bge-small-en-v1.5-q", None, 2, 384);
        assert!(matches!(
            q_full.resolve_model(),
            Some(fastembed::EmbeddingModel::BGESmallENV15Q)
        ));
        let minilm_q = OrtEmbedder::new("minilm-q", None, 2, 384);
        assert!(matches!(
            minilm_q.resolve_model(),
            Some(fastembed::EmbeddingModel::AllMiniLML6V2Q)
        ));
        // FP32 names keep resolving to the FP32 variants.
        let fp32 = OrtEmbedder::new("bge-small", None, 2, 384);
        assert!(matches!(
            fp32.resolve_model(),
            Some(fastembed::EmbeddingModel::BGESmallENV15)
        ));
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_default_threads_are_capped() {
        // The default must never exceed 4 threads regardless of logical
        // core count — unbounded ORT threads OOM-crash small machines
        // (docs/POLYGLOT_SIMD_MEMORY_STRATEGY.md).
        assert!(
            default_intra_threads() <= 4,
            "default threads must be capped at 4, got {}",
            default_intra_threads()
        );
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_dimension() {
        let embedder = OrtEmbedder::new("bge-small", None, 2, 384);
        assert_eq!(embedder.dimension(), 384);
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_dimension_custom() {
        let embedder = OrtEmbedder::new("minilm", None, 1, 256);
        assert_eq!(embedder.dimension(), 256);
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_pool_shards_the_thread_budget() {
        // V8 ship list #3: the pool distributes the TOTAL intra-op budget
        // across session shards. Threads=1 keeps the legacy single-session
        // shape; larger budgets fan out without exceeding the total.
        for threads in [1usize, 2, 4, 8] {
            let embedder = OrtEmbedder::new("bge-small", None, threads, 384);
            assert_eq!(
                embedder.threads(),
                threads,
                "total budget must be preserved"
            );
            let shards = embedder.shard_count();
            assert!(shards >= 1, "at least one session");
            assert!(
                shards <= threads,
                "shards ({shards}) must not exceed the total budget ({threads})"
            );
        }
        let single = OrtEmbedder::new("bge-small", None, 1, 384);
        assert_eq!(single.shard_count(), 1, "threads=1 is the legacy shape");
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_namespace_carries_model_and_dimension() {
        // Cache keys must change when the effective model changes.
        let small = OrtEmbedder::new("bge-small", None, 2, 384);
        let large = OrtEmbedder::new("bge-large", None, 2, 1024);
        assert_ne!(
            small.cache_namespace(),
            large.cache_namespace(),
            "different models must not share cache entries"
        );
        assert!(small.cache_namespace().contains("bge-small"));
    }

    /// Pool-shape microbench: run explicitly, it loads the real model
    /// (`cargo test -p wm-memory --features onnx ort_pool_shape_microbench
    /// -- --ignored --nocapture`). Measures embed_batch wall time for one
    /// ingest-shaped call per (threads, shards) config on realistic text.
    #[cfg(feature = "onnx")]
    #[test]
    #[ignore = "loads the real ONNX model; run explicitly for pool tuning"]
    fn ort_pool_shape_microbench() {
        let texts: Vec<String> = (0..128)
            .map(|i| {
                format!(
                    "Session {i} of the deployment retrospective covered the rollout \
                     schedule for the telemetry agent, the budget review outcomes, and \
                     the follow-up decisions about the quarterly report timeline {i}."
                )
            })
            .collect();
        let refs: Vec<&str> = texts.iter().map(String::as_str).collect();

        // (threads, shard_override) — shard_override None = derived.
        let configs: Vec<(usize, Option<usize>)> = vec![
            (1, Some(1)),
            (2, Some(1)),
            (4, Some(1)),
            (4, None),
            (4, Some(2)),
            (8, None),
            (8, Some(4)),
        ];
        for (threads, shards) in configs {
            let mut embedder = OrtEmbedder::new("bge-small-q", None, threads, 384);
            if let Some(n) = shards {
                embedder = embedder.with_shard_override(n);
            }
            // Warm the pool (model load) before timing.
            let warm = embedder.embed_batch(&refs[..1]).unwrap();
            assert_eq!(warm.len(), 1);
            let t0 = std::time::Instant::now();
            let out = embedder.embed_batch(&refs).unwrap();
            let dt = t0.elapsed();
            assert_eq!(out.len(), refs.len());
            println!(
                "pool shape: threads={threads} shards={} intra={} → {} texts in {:.2?} ({:.1} texts/s)",
                embedder.shard_count(),
                embedder.intra_per_shard(),
                refs.len(),
                dt,
                refs.len() as f64 / dt.as_secs_f64()
            );

            // Ingest shape: ~30-text chunks, many calls (the write path
            // chunks by chars, so embed_batch sees small slices).
            let t1 = std::time::Instant::now();
            let mut total = 0usize;
            for chunk in refs.chunks(30) {
                total += embedder.embed_batch(chunk).unwrap().len();
            }
            let dt1 = t1.elapsed();
            assert_eq!(total, refs.len());
            println!(
                "  ingest shape (30-text chunks): {:.2?} ({:.1} texts/s)",
                dt1,
                refs.len() as f64 / dt1.as_secs_f64()
            );
        }
    }

    /// Determinism across pool shapes: the same text must produce the same
    /// vector whether embedded on the single-session shape or the fanned
    /// out pool (intra/shard parallelism must not change the math).
    #[cfg(feature = "onnx")]
    #[test]
    #[ignore = "loads the real ONNX model; run explicitly as a pool-identity gate"]
    fn ort_pool_shapes_produce_identical_vectors() {
        let text = "determinism probe across session pool shapes";
        let single = OrtEmbedder::new("bge-small-q", None, 1, 384).with_shard_override(1);
        let pooled = OrtEmbedder::new("bge-small-q", None, 4, 384);
        let v1 = single.embed(text).unwrap();
        let v2 = pooled.embed(text).unwrap();
        assert_eq!(v1.len(), v2.len());
        let max_diff = v1
            .iter()
            .zip(v2.iter())
            .map(|(a, b)| (a - b).abs())
            .fold(0.0f32, f32::max);
        assert!(
            max_diff < 1e-6,
            "pool shape changed the vector math (max diff {max_diff})"
        );
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_empty_batch() {
        let embedder = OrtEmbedder::new("bge-small", None, 2, 384);
        let result = embedder.embed_batch(&[]).unwrap();
        assert!(result.is_empty());
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_trait_object() {
        let embedder: Box<dyn Embedder> = Box::new(OrtEmbedder::new("bge-small", None, 2, 384));
        assert_eq!(embedder.dimension(), 384);
        assert_eq!(embedder.backend_name(), "onnx");
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_resolve_model_known() {
        let embedder = OrtEmbedder::new("bge-small-en-v1.5", None, 2, 384);
        assert!(embedder.resolve_model().is_some());
    }

    #[cfg(feature = "onnx")]
    #[test]
    fn ort_embedder_resolve_model_unknown_falls_back() {
        let embedder = OrtEmbedder::new("some-unknown-model", None, 2, 384);
        // Should fall back to bge-small
        assert!(embedder.resolve_model().is_some());
    }

    // --- SSRF validation tests ---

    #[test]
    fn endpoint_safe_allows_localhost() {
        assert!(is_endpoint_safe("http://localhost:8080"));
        assert!(is_endpoint_safe("http://127.0.0.1:8080"));
        assert!(is_endpoint_safe("http://localhost:11434/v1/embeddings"));
    }

    #[test]
    fn endpoint_safe_allows_private_ip() {
        assert!(is_endpoint_safe("http://10.0.0.2:8080"));
        assert!(is_endpoint_safe("http://192.168.1.100:8080"));
        assert!(is_endpoint_safe("http://172.16.0.5:8080"));
    }

    #[test]
    fn endpoint_safe_blocks_non_http_schemes() {
        assert!(!is_endpoint_safe("file:///etc/passwd"));
        assert!(!is_endpoint_safe("gopher://localhost:8080"));
        assert!(!is_endpoint_safe("ftp://example.com"));
        assert!(!is_endpoint_safe("javascript:alert(1)"));
        assert!(!is_endpoint_safe("data:text/plain,hello"));
    }

    #[test]
    fn endpoint_safe_blocks_metadata_endpoints() {
        assert!(!is_endpoint_safe("http://169.254.169.254/latest/meta-data"));
        assert!(!is_endpoint_safe("http://169.254.170.2/v2/metadata"));
        assert!(!is_endpoint_safe(
            "http://metadata.google.internal/computeMetadata"
        ));
        assert!(!is_endpoint_safe("http://metadata.aws.internal"));
        assert!(!is_endpoint_safe("http://metadata"));
    }

    #[test]
    fn endpoint_safe_blocks_empty_host() {
        assert!(!is_endpoint_safe("http://"));
        assert!(!is_endpoint_safe("http:///path"));
    }

    #[test]
    fn endpoint_safe_blocks_malformed_ipv6() {
        assert!(!is_endpoint_safe("http://[::1:8080"));
    }

    #[test]
    fn endpoint_safe_allows_https() {
        assert!(is_endpoint_safe("https://localhost:8080"));
        assert!(is_endpoint_safe("https://example.com/api"));
    }

    #[test]
    fn endpoint_safe_allows_ipv6_loopback() {
        assert!(is_endpoint_safe("http://[::1]:8080"));
    }
}
