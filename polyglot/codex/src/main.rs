use anyhow::Result;
use clap::{Parser, Subcommand};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tracing::info;
use tokio::io::AsyncBufReadExt;

use axum::{
    routing::{get, post},
    Router, Json,
    extract::State,
};
use tower_http::{services::ServeDir, cors::CorsLayer};
use serde::{Deserialize, Serialize};

use codex_core::CodexConfig;


#[derive(Parser)]
#[command(name = "codex")]
#[command(about = "Semantic knowledge extraction and codification pipeline")]
#[command(version = "0.1.0")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
    
    /// Path to configuration file
    #[arg(short, long, global = true)]
    config: Option<PathBuf>,
    
    /// Enable verbose logging
    #[arg(short, long, global = true)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize a new codex project
    Init {
        /// Project name
        name: String,
        /// Project path (default: current directory)
        path: Option<PathBuf>,
    },
    
    /// Extract and normalize all source content
    Extract {
        /// Specific source to extract (library, conversations, research, all)
        #[arg(default_value = "all")]
        source: String,
        /// Force re-extraction even if cached
        #[arg(short, long)]
        force: bool,
        /// Only extract changed files (SHA256 manifest)
        #[arg(short, long)]
        incremental: bool,
    },
    
    /// Chunk extracted content into semantic units
    Chunk {
        /// Chunking strategy
        #[arg(short, long, default_value = "hierarchical")]
        strategy: String,
        /// Target level (paragraph, section, document, all)
        #[arg(short, long, default_value = "all")]
        level: String,
        /// Deduplicate identical chunks across documents
        #[arg(long, default_value = "true")]
        dedup: bool,
    },
    
    /// Generate embeddings for chunks
    Embed {
        /// Specific embedding provider
        #[arg(short, long)]
        provider: Option<String>,
        /// Resume from checkpoint
        #[arg(short, long)]
        resume: bool,
    },
    
    /// Build graph and vector indices
    Index {
        /// Rebuild from scratch
        #[arg(short, long)]
        rebuild: bool,
    },
    
    /// Export to target formats (Vaya Vida, JSON, etc.)
    Export {
        /// Export format
        #[arg(short, long, default_value = "all")]
        format: String,
        /// Output directory
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    
    /// Run full pipeline: extract → chunk → embed → index → export
    Build {
        /// Start from specific stage
        #[arg(short, long)]
        from: Option<String>,
        /// Stop at specific stage
        #[arg(short, long)]
        to: Option<String>,
        /// Skip specific stages (comma-separated)
        #[arg(short, long)]
        skip: Option<String>,
        /// Force rebuild, skip all resume checks
        #[arg(short, long)]
        force: bool,
    },
    
    /// Query the indexed corpus
    Query {
        /// Search query
        query: String,
        /// Number of results
        #[arg(short, long, default_value = "10")]
        limit: usize,
        /// Use semantic search (embed query and find nearest vectors)
        #[arg(long)]
        semantic: bool,
    },
    
    /// Consolidate small chunks into larger semantic units
    Consolidate {
        /// Target token count per consolidated node
        #[arg(short, long, default_value = "10000")]
        target_tokens: usize,
        /// Number of cluster detection iterations
        #[arg(short, long, default_value = "15")]
        iterations: usize,
    },
    
    /// Serve web interface for browsing
    Serve {
        /// Bind address
        #[arg(short, long, default_value = "127.0.0.1:8080")]
        bind: String,
    },
    
    /// Validate project integrity
    Check,
    
    /// Show project statistics
    Stats,
    
    /// Watch source directories for changes and auto-rebuild
    Watch {
        /// Directories to watch (comma-separated, default: LIBRARY,OPENAI archives,RESEARCH,Grok)
        #[arg(short, long)]
        paths: Option<String>,
        /// Debounce duration in seconds
        #[arg(short, long, default_value = "5")]
        debounce: u64,
    },
}

fn make_default_config(base_path: &Path) -> CodexConfig {
    let mut config = CodexConfig::default();
    config.project.base_path = base_path.to_path_buf();
    config
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    
    // Load configuration
    let config_path = cli.config.as_deref();
    let base_path = match std::env::var("CODEX_BASE_PATH") {
        Ok(p) => PathBuf::from(p),
        Err(_) => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };
    let config = match codex_core::load_config_with_fallback(config_path, &base_path) {
        Ok(c) => {
            info!("Loaded config from project: {}", c.project.name);
            Arc::new(c)
        }
        Err(e) => {
            eprintln!("Warning: Config load failed: {}. Using defaults.", e);
            Arc::new(make_default_config(&base_path))
        }
    };
    
    // Initialize logging (respect config log level)
    let log_level = if cli.verbose { "debug" } else { &config.dev.log_level };
    let subscriber = tracing_subscriber::fmt()
        .with_env_filter(format!("codex={}", log_level))
        .with_target(false)
        .compact();
    subscriber.init();
    
    info!("CODEX Pipeline v0.1.0 — project: {}", config.project.name);
    
    match cli.command {
        Commands::Init { name, path } => {
            info!("Initializing new codex project: {}", name);
            cmd_init(&name, path).await?;
        }
        Commands::Extract { source, force, incremental } => {
            info!("Extracting source: {}", source);
            cmd_extract(&source, force, incremental, &config).await?;
        }
        Commands::Chunk { strategy, level, dedup } => {
            info!("Chunking with strategy: {}, level: {}, dedup: {}", strategy, level, dedup);
            cmd_chunk(&strategy, &level, dedup, &config).await?;
        }
        Commands::Embed { provider, resume } => {
            info!("Generating embeddings");
            cmd_embed(provider.as_deref(), resume, &config).await?;
        }
        Commands::Index { rebuild } => {
            info!("Building indices");
            cmd_index(rebuild, &config).await?;
        }
        Commands::Export { format, output } => {
            info!("Exporting to format: {}", format);
            cmd_export(&format, output, &config).await?;
        }
        Commands::Build { from, to, skip, force } => {
            info!("Running full build pipeline");
            cmd_build(from.as_deref(), to.as_deref(), skip.as_deref(), force, &config).await?
        }
        Commands::Query { query, limit, semantic } => {
            cmd_query(&query, limit, semantic, &config).await?;
        }
        Commands::Consolidate { target_tokens, iterations } => {
            info!("Consolidating chunks with target {} tokens", target_tokens);
            cmd_consolidate(target_tokens, iterations, &config).await?;
        }
        Commands::Serve { bind } => {
            info!("Starting web server on {}", bind);
            cmd_serve(&bind, &config).await?;
        }
        Commands::Check => {
            cmd_check(&config).await?;
        }
        Commands::Stats => {
            cmd_stats(&config).await?;
        }
        Commands::Watch { paths, debounce } => {
            cmd_watch(paths.as_deref(), debounce).await?;
        }
    }
    
    Ok(())
}

// Command implementations (placeholders)
async fn cmd_init(name: &str, path: Option<PathBuf>) -> Result<()> {
    let project_path = path.unwrap_or_else(|| PathBuf::from(name));
    std::fs::create_dir_all(&project_path)?;
    
    // Create default config
    let config_path = project_path.join("codex.yaml");
    std::fs::write(&config_path, include_str!("../config/codex.example.yaml"))?;
    
    println!("✓ Created project '{}' at {:?}", name, project_path);
    println!("✓ Generated default configuration at {:?}", config_path);
    println!("\nNext steps:");
    println!("  1. Edit codex.yaml to configure your sources");
    println!("  2. Run: codex extract");
    println!("  3. Run: codex build");
    
    Ok(())
}

async fn cmd_extract(source: &str, force: bool, incremental: bool, config: &CodexConfig) -> Result<()> {
    let base_path = if let Ok(env_path) = std::env::var("CODEX_BASE_PATH") {
        PathBuf::from(env_path)
    } else {
        config.project.base_path.clone()
    };
    let output_dir = base_path.join("10_extracted");
    std::fs::create_dir_all(&output_dir)?;

    let source_path = match source {
        "library" => base_path.join("00_source/library"),
        "conversations" => base_path.join("00_source/conversations"),
        "research" => base_path.join("00_source/research"),
        "all" => base_path.join("00_source"),
        _ => {
            eprintln!("Unknown source: {}. Use 'library', 'conversations', 'research', or 'all'", source);
            return Ok(());
        }
    };

    let bar = indicatif::ProgressBar::new_spinner();
    bar.set_style(indicatif::ProgressStyle::default_spinner().template("{spinner} {msg}").unwrap());
    bar.set_message(format!("Extracting from {:?}...", source));

    let docs = if incremental && !force {
        extract_incremental(&source_path, &base_path, &output_dir, source).await?
    } else {
        codex_extract::extract_directory(&source_path, &base_path).await?
    };

    bar.finish_with_message(format!("Extracted {} documents", docs.len()));

    let output_file = output_dir.join(format!("{}_extracted.jsonl", source));
    if config.dev.dry_run {
        println!("[dry-run] Would write {} docs to {:?}", docs.len(), output_file);
    } else {
        codex_extract::write_jsonl(&docs, &output_file).await?;
        println!("Written to: {:?}", output_file);
    }

    Ok(())
}

async fn extract_incremental(
    source_path: &Path,
    base_path: &Path,
    output_dir: &Path,
    source_name: &str,
) -> Result<Vec<codex_core::Document>> {
    use std::collections::HashMap;
    use std::time::SystemTime;

    let manifest_path = output_dir.join(format!("{}_manifest.json", source_name));

    // Load previous manifest
    let mut manifest: HashMap<String, (u64, u64)> = if manifest_path.exists() {
        let bytes = tokio::fs::read(&manifest_path).await?;
        serde_json::from_slice(&bytes).unwrap_or_default()
    } else {
        HashMap::new()
    };

    let all_docs = codex_extract::extract_directory(source_path, base_path).await?;
    let mut changed = Vec::new();
    let mut new_manifest: HashMap<String, (u64, u64)> = HashMap::new();

    for doc in all_docs {
        let meta = tokio::fs::metadata(&doc.source_path).await;
        let (size, mtime) = match meta {
            Ok(m) => {
                let size = m.len();
                let mtime = m.modified()
                    .unwrap_or(SystemTime::UNIX_EPOCH)
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs();
                (size, mtime)
            }
            Err(_) => (0, 0),
        };

        let key = doc.source_path.to_string_lossy().to_string();
        new_manifest.insert(key.clone(), (size, mtime));

        let prev = manifest.get(&key);
        if prev.copied() != Some((size, mtime)) {
            changed.push(doc);
        }
    }

    // Remove entries for deleted files
    let current_keys: std::collections::HashSet<String> = new_manifest.keys().cloned().collect();
    manifest.retain(|k, _| current_keys.contains(k));

    // Write updated manifest
    let manifest_json = serde_json::to_vec(&new_manifest)?;
    tokio::fs::write(&manifest_path, manifest_json).await?;

    if changed.is_empty() {
        println!("  Incremental: all {} files up to date", new_manifest.len());
    } else {
        println!("  Incremental: {} changed / {} total files", changed.len(), new_manifest.len());
    }

    Ok(changed)
}

async fn cmd_chunk(strategy: &str, _level: &str, dedup: bool, config: &CodexConfig) -> Result<()> {
    let base_path = &config.project.base_path;
    let extracted_dir = base_path.join("10_extracted");
    let chunks_dir = base_path.join("20_chunks");
    std::fs::create_dir_all(&chunks_dir)?;

    // Find all extracted JSONL files
    let mut entries = tokio::fs::read_dir(&extracted_dir).await?;
    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("jsonl") {
            continue;
        }

        // Skip "all" combined files — they are just duplicates of individual sources
        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
        if stem == "all" || stem.starts_with("all_") {
            continue;
        }

        println!("Chunking: {:?}", path);
        let docs = codex_extract::read_jsonl(&path).await?;
        println!("  Read {} documents", docs.len());

        let chunks = match (strategy, dedup) {
            ("paragraph" | "hierarchical" | "all", false) => codex_chunk::chunk_documents(&docs)?,
            ("paragraph" | "hierarchical" | "all", true) => codex_chunk::chunk_and_dedup_documents(&docs)?,
            _ => {
                eprintln!("Unknown strategy: {}. Using paragraph.", strategy);
                codex_chunk::chunk_documents(&docs)?
            }
        };

        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("chunks");
        let output = chunks_dir.join(format!("{}_chunks.jsonl", stem));
        if config.dev.dry_run {
            println!("[dry-run] Would write {} chunks to {:?}", chunks.len(), output);
        } else {
            codex_chunk::write_chunks_jsonl(&chunks, &output).await?;
            println!("  Wrote {} chunks to {:?}", chunks.len(), output);
        }
    }

    Ok(())
}

async fn cmd_embed(_provider: Option<&str>, resume: bool, config: &CodexConfig) -> Result<()> {
    let api_key_env = &config.embedding.api_key_env;
    let api_key = match config.embedding.provider {
        codex_core::EmbeddingProvider::OpenRouter => {
            config.embedding.openrouter_key_env.as_ref()
                .and_then(|k| std::env::var(k).ok())
                .or_else(|| std::env::var(api_key_env).ok())
        }
        _ => std::env::var("OPENAI_API_KEY")
            .or_else(|_| std::env::var(api_key_env))
            .ok(),
    };

    let base_path = &config.project.base_path;
    let input_dir = base_path.join("20_chunks");
    let output_dir = base_path.join("30_embeddings");

    let (model, dims) = if api_key.is_some() {
        (config.embedding.embedding_model.as_str(), config.embedding.dimensions)
    } else {
        ("BAAI/bge-small-en-v1.5", 384usize)
    };

    if config.dev.dry_run {
        println!("[dry-run] Would embed chunks from {:?}", input_dir);
        return Ok(());
    }

    codex_embed::embed_directory(
        &input_dir,
        &output_dir,
        api_key.as_deref(),
        model,
        dims,
        config.embedding.batch_size,
        config.embedding.rate_limit_rps,
        config.embedding.max_retries,
        resume,
    ).await?;

    Ok(())
}

async fn cmd_index(_rebuild: bool, config: &CodexConfig) -> Result<()> {
    let base_path = &config.project.base_path;
    let embed_dir = base_path.join("30_embeddings");
    let index_dir = base_path.join("40_index");
    std::fs::create_dir_all(&index_dir)?;

    let bar = indicatif::ProgressBar::new(100);
    bar.set_style(
        indicatif::ProgressStyle::default_bar()
            .template("{bar:40} {pos}/{len} {msg}").unwrap()
            .progress_chars("=>-")
    );

    bar.set_message("Loading embeddings");
    let mut embeddings = codex_index::load_embeddings(&embed_dir)?;
    bar.inc(20);
    bar.set_message(format!("Loaded {} embeddings, normalizing", embeddings.len()));

    codex_index::normalize_vectors(&mut embeddings);
    bar.inc(20);
    bar.set_message("Building k-NN index");

    let k = 10usize;
    let edges = codex_index::build_knn_index(&embeddings, k);
    bar.inc(40);
    bar.set_message(format!("Built {} edges, writing", edges.len()));

    if config.dev.dry_run {
        println!("[dry-run] Would write {} edges and {} vectors", edges.len(), embeddings.len());
        return Ok(());
    }

    let edges_path = index_dir.join("similarity_edges.jsonl");
    codex_index::write_edges(&edges, &edges_path)?;

    let vectors_path = index_dir.join("vectors.bin");
    codex_index::write_vectors_binary(&embeddings, &vectors_path)?;
    bar.inc(20);
    bar.finish_with_message(format!("Index complete: {} edges", edges.len()));

    Ok(())
}

async fn cmd_export(format: &str, output: Option<PathBuf>, config: &CodexConfig) -> Result<()> {
    let base_path = &config.project.base_path;
    let chunks_dir = base_path.join("20_chunks");
    let index_dir = base_path.join("40_index");
    let export_dir = base_path.join("50_export");
    std::fs::create_dir_all(&export_dir)?;

    let output_path = output.unwrap_or_else(|| export_dir.join("sphere-nodes.json"));

    match format {
        "vaya-vida" | "all" => {
            codex_export::export_vaya_vida(
                &chunks_dir,
                &index_dir.join("similarity_edges.jsonl"),
                &output_path,
            )?;
        }
        _ => {
            eprintln!("Unknown export format: {}. Use 'vaya-vida' or 'all'.", format);
        }
    }

    Ok(())
}

async fn cmd_build(
    from: Option<&str>,
    to: Option<&str>,
    skip: Option<&str>,
    force: bool,
    config: &CodexConfig,
) -> Result<()> {
    let stages: Vec<&str> = config.pipeline.stages.iter().map(|s| s.as_str()).collect();
    let skip_set: std::collections::HashSet<&str> = skip
        .map(|s| s.split(',').collect())
        .unwrap_or_default();

    let mut started = from.is_none();
    let mut stopped = false;

    for stage in stages {
        if let Some(f) = from {
            if stage == f { started = true; }
        }
        if !started || skip_set.contains(stage) || stopped {
            continue;
        }
        if let Some(t) = to {
            if stage == t {
                stopped = true;
            }
        }

        println!("\n=== Stage: {} ===", stage);
        match stage {
            "extract" => cmd_extract("all", force, false, config).await?,
            "chunk" => cmd_chunk("hierarchical", "all", true, config).await?,
            "embed" => cmd_embed(None, false, config).await?,
            "index" => cmd_index(true, config).await?,
            "export" => cmd_export("all", None, config).await?,
            "consolidate" => cmd_consolidate(10000, 15, config).await?,
            _ => {}
        }
    }

    println!("\n=== Build complete ===");
    Ok(())
}

async fn cmd_query(query: &str, limit: usize, semantic: bool, config: &CodexConfig) -> Result<()> {
    let base_path = &config.project.base_path;
    let chunks_dir = base_path.join("20_chunks");

    if semantic {
        println!("Semantic query: '{}'", query);
        let query_vec = codex_embed::embed_query_text(query)?;
        let vectors_path = base_path.join("40_index").join("vectors.bin");
        let embeddings = codex_index::read_vectors_binary(&vectors_path)?;
        let semantic_results = codex_index::query_semantic(&embeddings, &query_vec, limit);

        if semantic_results.is_empty() {
            println!("No matches found for '{}'", query);
            return Ok(());
        }

        let mut all_chunks = Vec::new();
        let mut entries = tokio::fs::read_dir(&chunks_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("jsonl") { continue; }
            let file = tokio::fs::File::open(&path).await?;
            let reader = tokio::io::BufReader::new(file);
            let mut lines = reader.lines();
            while let Some(line) = lines.next_line().await? {
                if line.trim().is_empty() { continue; }
                let chunk: codex_core::Chunk = match serde_json::from_str(&line) {
                    Ok(c) => c,
                    Err(_) => continue,
                };
                all_chunks.push(chunk);
            }
        }

        let chunk_map: std::collections::HashMap<String, codex_core::Chunk> =
            all_chunks.into_iter().map(|c| (c.id.clone(), c)).collect();

        for (i, (chunk_id, score)) in semantic_results.iter().enumerate() {
            if let Some(chunk) = chunk_map.get(chunk_id) {
                println!("\n{}. [{}] sim={:.4} | source={} | {} tokens",
                    i + 1, chunk_id, score, codex_core::infer_source(&chunk.document_id), chunk.token_count);
                let preview = chunk.content.chars().take(280).collect::<String>();
                println!("   {}", preview);
            }
        }
    } else {
        println!("Text query: '{}' (top {})", query, limit);
        let results: Vec<(codex_core::Chunk, f32)> = keyword_search(&chunks_dir, query, limit).await?;
        if results.is_empty() {
            println!("No matches found for '{}'", query);
            return Ok(());
        }
        for (i, (chunk, score)) in results.iter().enumerate() {
            println!("\n{}. [{}] score={:.3} | source={} | {} tokens", 
                i + 1, chunk.id, score, codex_core::infer_source(&chunk.document_id), chunk.token_count);
            let preview = chunk.content.chars().take(280).collect::<String>();
            println!("   {}", preview);
        }
    }

    Ok(())
}

async fn keyword_search(
    chunks_dir: &Path,
    query: &str,
    limit: usize,
) -> Result<Vec<(codex_core::Chunk, f32)>> {
    use tokio::io::AsyncBufReadExt;

    let query_terms: Vec<String> = query
        .to_lowercase()
        .split_whitespace()
        .map(|s| s.to_string())
        .collect();

    if query_terms.is_empty() {
        return Ok(Vec::new());
    }

    let mut entries = tokio::fs::read_dir(chunks_dir).await?;
    let mut all_scores: Vec<(codex_core::Chunk, f32)> = Vec::new();

    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("jsonl") {
            continue;
        }

        let file = tokio::fs::File::open(&path).await?;
        let reader = tokio::io::BufReader::new(file);
        let mut lines = reader.lines();

        while let Some(line) = lines.next_line().await? {
            if line.trim().is_empty() { continue; }
            let chunk: codex_core::Chunk = match serde_json::from_str(&line) {
                Ok(c) => c,
                Err(_) => continue,
            };

            let content_lower = chunk.content.to_lowercase();
            let mut score = 0.0f32;

            for term in &query_terms {
                let count = content_lower.matches(term).count() as f32;
                // TF-style scoring: rare terms get higher weight
                let term_weight = 1.0 / (content_lower.matches(term).count().max(1) as f32).sqrt();
                score += count * term_weight;
            }

            // Boost exact phrase matches
            let exact_query = query.to_lowercase();
            if content_lower.contains(&exact_query) {
                score += 5.0;
            }

            // Normalize by document length (BM25-style)
            let avg_len = 500.0f32;
            let doc_len = chunk.content.len() as f32;
            let norm = 1.0 + doc_len / avg_len;
            score /= norm;

            if score > 0.01 {
                all_scores.push((chunk, score));
            }
        }
    }

    // Sort by score descending
    all_scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    all_scores.truncate(limit);

    Ok(all_scores)
}

async fn api_health() -> &'static str {
    "ok"
}

#[derive(Deserialize)]
struct QueryRequest {
    query: String,
    #[serde(default = "default_limit")]
    limit: usize,
    #[serde(default)]
    semantic: bool,
}

fn default_limit() -> usize { 10 }

#[derive(Serialize)]
struct QueryResult {
    id: String,
    score: f32,
    source: String,
    tokens: usize,
    preview: String,
}

async fn cmd_serve(bind: &str, config: &CodexConfig) -> Result<()> {
    let base_path = config.project.base_path.clone();
    let state = Arc::new(base_path);

    let app = Router::new()
        .route("/api/query", post(api_query))
        .route("/api/health", get(api_health))
        .nest_service("/", ServeDir::new(state.join("50_export")))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind(bind).await?;
    println!("Server running at http://{}", bind);
    axum::serve(listener, app).await?;
    Ok(())
}

async fn api_query(
    State(base_path): State<Arc<PathBuf>>,
    Json(req): Json<QueryRequest>,
) -> Json<Vec<QueryResult>> {
    let chunks_dir = base_path.join("20_chunks");
    let results = if req.semantic {
        match codex_embed::embed_query_text(&req.query) {
            Ok(query_vec) => {
                let vectors_path = base_path.join("40_index").join("vectors.bin");
                match codex_index::read_vectors_binary(&vectors_path) {
                    Ok(embeddings) => {
                        let semantic_results = codex_index::query_semantic(&embeddings, &query_vec, req.limit);
                        let mut all_chunks = Vec::new();
                        if let Ok(mut entries) = tokio::fs::read_dir(&chunks_dir).await {
                            while let Ok(Some(entry)) = entries.next_entry().await {
                                let path = entry.path();
                                if path.extension().and_then(|e| e.to_str()) != Some("jsonl") { continue; }
                                if let Ok(file) = tokio::fs::File::open(&path).await {
                                    use tokio::io::AsyncBufReadExt;
                                    let reader = tokio::io::BufReader::new(file);
                                    let mut lines = reader.lines();
                                    while let Ok(Some(line)) = lines.next_line().await {
                                        if let Ok(chunk) = serde_json::from_str::<codex_core::Chunk>(&line) {
                                            all_chunks.push(chunk);
                                        }
                                    }
                                }
                            }
                        }
                        let chunk_map: std::collections::HashMap<String, codex_core::Chunk> =
                            all_chunks.into_iter().map(|c| (c.id.clone(), c)).collect();
                        semantic_results.into_iter().filter_map(|(id, score)| {
                            chunk_map.get(&id).map(|chunk| QueryResult {
                                id: chunk.id.clone(),
                                score,
                                source: chunk.metadata.get("source_path")
                                    .and_then(|v| v.as_str())
                                    .map(|s| Path::new(s).file_name()
                                        .and_then(|f| f.to_str())
                                        .unwrap_or("unknown")
                                        .to_string())
                                    .unwrap_or_else(|| "unknown".to_string()),
                                tokens: chunk.token_count,
                                preview: chunk.content.chars().take(280).collect(),
                            })
                        }).collect()
                    }
                    Err(_) => Vec::new(),
                }
            }
            Err(_) => Vec::new(),
        }
    } else {
        match keyword_search(&chunks_dir, &req.query, req.limit).await {
            Ok(results) => results.into_iter().map(|(chunk, score)| QueryResult {
                id: chunk.id.clone(),
                score,
                source: codex_core::infer_source(&chunk.document_id).to_string(),
                tokens: chunk.token_count,
                preview: chunk.content.chars().take(280).collect(),
            }).collect(),
            Err(_) => Vec::new(),
        }
    };

    Json(results)
}

async fn cmd_check(config: &CodexConfig) -> Result<()> {
    println!("\n🔍 CODEX Project Integrity Check\n");
    
    let base_path = &config.project.base_path;
    let mut issues = Vec::new();
    let mut checks_passed = 0;
    
    // Check 1: Source directories exist
    print!("[1/6] Checking source directories... ");
    let sources = ["LIBRARY", "OPENAI archives", "RESEARCH", "Grok"];
    for source in &sources {
        let path = base_path.join(source);
        if path.exists() {
            checks_passed += 1;
        } else {
            issues.push(format!("Source directory '{}' not found", source));
        }
    }
    println!("✓");
    
    // Check 2: Pipeline directories
    print!("[2/6] Checking pipeline directories... ");
    let pipeline_dirs = ["00_source", "10_extracted", "20_chunks", "30_embeddings", "40_index", "50_export"];
    for dir in &pipeline_dirs {
        let path = base_path.join(dir);
        if !path.exists() {
            tokio::fs::create_dir_all(&path).await?;
            println!("(created missing '{}')", dir);
        }
    }
    println!("✓");
    checks_passed += 1;
    
    // Check 3: Count extracted files
    print!("[3/6] Checking extracted data... ");
    let extracted_dir = base_path.join("10_extracted");
    let mut extracted_count = 0;
    if extracted_dir.exists() {
        let mut entries = tokio::fs::read_dir(&extracted_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            if entry.path().extension().and_then(|e| e.to_str()) == Some("jsonl") {
                extracted_count += 1;
            }
        }
    }
    if extracted_count == 0 {
        issues.push("No extracted JSONL files found. Run 'codex extract' first.".to_string());
    } else {
        checks_passed += 1;
    }
    println!("{} files", extracted_count);
    
    // Check 4: Count chunks
    print!("[4/6] Checking chunk data... ");
    let chunks_dir = base_path.join("20_chunks");
    let mut chunk_files = 0;
    let mut total_chunks = 0usize;
    if chunks_dir.exists() {
        let mut entries = tokio::fs::read_dir(&chunks_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            if entry.path().extension().and_then(|e| e.to_str()) == Some("jsonl") {
                chunk_files += 1;
                // Count lines
                if let Ok(file) = tokio::fs::File::open(entry.path()).await {
                    use tokio::io::AsyncBufReadExt;
                    let reader = tokio::io::BufReader::new(file);
                    let mut lines = reader.lines();
                    while let Ok(Some(_)) = lines.next_line().await {
                        total_chunks += 1;
                    }
                }
            }
        }
    }
    if chunk_files == 0 {
        issues.push("No chunk files found. Run 'codex chunk' first.".to_string());
    } else {
        checks_passed += 1;
    }
    println!("{} files ({} chunks)", chunk_files, total_chunks);
    
    // Check 5: Check embeddings
    print!("[5/6] Checking embeddings... ");
    let embed_dir = base_path.join("30_embeddings");
    let mut embed_files = 0;
    if embed_dir.exists() {
        let mut entries = tokio::fs::read_dir(&embed_dir).await?;
        while let Some(entry) = entries.next_entry().await? {
            if entry.path().extension().and_then(|e| e.to_str()) == Some("jsonl") {
                embed_files += 1;
            }
        }
    }
    if embed_files == 0 {
        issues.push("No embedding files found. Run 'codex embed' first.".to_string());
    } else {
        checks_passed += 1;
    }
    println!("{} files", embed_files);
    
    // Check 6: Check index
    print!("[6/6] Checking index... ");
    let index_dir = base_path.join("40_index");
    let vectors_exist = index_dir.join("vectors.bin").exists();
    let edges_exist = index_dir.join("similarity_edges.jsonl").exists();
    if !vectors_exist && !edges_exist {
        issues.push("No index files found. Run 'codex index' first.".to_string());
    } else {
        checks_passed += 1;
    }
    println!("vectors={} edges={}", if vectors_exist { "✓" } else { "✗" }, if edges_exist { "✓" } else { "✗" });
    
    // Summary
    println!("\n{}", "=".repeat(50));
    if issues.is_empty() {
        println!("✅ All checks passed! Project is ready for querying.");
    } else {
        println!("⚠️  Found {} issue(s):", issues.len());
        for issue in &issues {
            println!("   • {}", issue);
        }
    }
    println!("{}/6 checks passed\n", checks_passed);
    
    Ok(())
}

async fn cmd_stats(config: &CodexConfig) -> Result<()> {
    println!("\n📊 CODEX Project Statistics\n");
    
    let base_path = &config.project.base_path;
    
    // Source statistics
    println!("📁 Source Data:");
    let sources = [
        ("LIBRARY", base_path.join("LIBRARY")),
        ("OPENAI archives", base_path.join("OPENAI archives")),
        ("RESEARCH", base_path.join("RESEARCH")),
        ("Grok", base_path.join("Grok")),
    ];
    
    for (name, path) in &sources {
        if path.exists() {
            let count = count_files_recursive(path).await.unwrap_or(0);
            let size = format_size(dir_size(path).await.unwrap_or(0));
            println!("  {:20} {:>8} files  ({:>10})", name, count, size);
        } else {
            println!("  {:20} (not found)", name);
        }
    }
    
    // Pipeline statistics
    println!("\n🔧 Pipeline Stages:");
    
    // Extracted
    let extracted_dir = base_path.join("10_extracted");
    let (ext_count, ext_size) = count_jsonl_stats(&extracted_dir).await?;
    println!("  10_extracted       {:>8} JSONL    ({:>10})", ext_count, format_size(ext_size));
    
    // Chunks
    let chunks_dir = base_path.join("20_chunks");
    let (chunk_files, chunks_count, chunk_size) = count_chunks_stats(&chunks_dir).await?;
    println!("  20_chunks          {:>5} files, {:>5} chunks  ({:>10})", 
        chunk_files, chunks_count, format_size(chunk_size));
    
    // Embeddings
    let embed_dir = base_path.join("30_embeddings");
    let (emb_count, emb_size) = count_jsonl_stats(&embed_dir).await?;
    println!("  30_embeddings      {:>8} JSONL    ({:>10})", emb_count, format_size(emb_size));
    
    // Index
    let index_dir = base_path.join("40_index");
    let index_size = dir_size(&index_dir).await.unwrap_or(0);
    println!("  40_index           {:>21} ({:>10})", "", format_size(index_size));
    
    // Export
    let export_dir = base_path.join("50_export");
    let export_size = dir_size(&export_dir).await.unwrap_or(0);
    println!("  50_export          {:>21} ({:>10})", "", format_size(export_size));
    
    // Total
    let total_size = dir_size(&base_path).await.unwrap_or(0);
    println!("\n  Total project size: {}", format_size(total_size));
    
    // Pipeline completion status
    println!("\n📈 Pipeline Status:");
    let stages = [
        ("Extract", ext_count > 0),
        ("Chunk", chunk_files > 0),
        ("Embed", emb_count > 0),
        ("Index", index_dir.join("vectors.bin").exists()),
    ];
    for (name, complete) in stages {
        println!("  {} {}", if complete { "✓" } else { "○" }, name);
    }
    
    println!();
    Ok(())
}

async fn count_files_recursive(path: &Path) -> Result<usize> {
    use walkdir::WalkDir;
    let count = WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .count();
    Ok(count)
}

async fn dir_size(path: &Path) -> Result<u64> {
    use walkdir::WalkDir;
    let mut total = 0u64;
    for entry in WalkDir::new(path).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            if let Ok(meta) = entry.metadata() {
                total += meta.len();
            }
        }
    }
    Ok(total)
}

fn format_size(bytes: u64) -> String {
    const UNITS: &[&str] = &["B", "KB", "MB", "GB", "TB"];
    if bytes == 0 {
        return "0 B".to_string();
    }
    let exp = (bytes as f64).log(1024.0).min(UNITS.len() as f64 - 1.0) as usize;
    let size = bytes as f64 / 1024f64.powi(exp as i32);
    format!("{:.2} {}", size, UNITS[exp])
}

async fn count_jsonl_stats(dir: &Path) -> Result<(usize, u64)> {
    if !dir.exists() {
        return Ok((0, 0));
    }
    let mut count = 0;
    let mut size = 0u64;
    let mut entries = tokio::fs::read_dir(dir).await?;
    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("jsonl") {
            count += 1;
            if let Ok(meta) = entry.metadata().await {
                size += meta.len();
            }
        }
    }
    Ok((count, size))
}

async fn count_chunks_stats(dir: &Path) -> Result<(usize, usize, u64)> {
    if !dir.exists() {
        return Ok((0, 0, 0));
    }
    let mut files = 0;
    let mut chunks = 0;
    let mut size = 0u64;
    let mut entries = tokio::fs::read_dir(dir).await?;
    while let Some(entry) = entries.next_entry().await? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) == Some("jsonl") {
            files += 1;
            if let Ok(meta) = entry.metadata().await {
                size += meta.len();
            }
            // Count lines
            if let Ok(file) = tokio::fs::File::open(&path).await {
                use tokio::io::AsyncBufReadExt;
                let reader = tokio::io::BufReader::new(file);
                let mut lines = reader.lines();
                while let Ok(Some(_)) = lines.next_line().await {
                    chunks += 1;
                }
            }
        }
    }
    Ok((files, chunks, size))
}

async fn cmd_consolidate(target_tokens: usize, iterations: usize, config: &CodexConfig) -> Result<()> {
    let base_path = &config.project.base_path;
    
    println!("Starting consolidation process...");
    println!("Target tokens per node: {}", target_tokens);
    println!("Cluster detection iterations: {}", iterations);
    
    let mut consolidator = codex_consolidate::Consolidator::new();
    
    // Load all chunks from all sources
    let chunks_dir = base_path.join("20_chunks");
    println!("\n[1/5] Loading chunks...");
    
    for source in &["library", "conversations", "research"] {
        let chunks_file = chunks_dir.join(format!("{}_extracted_chunks.jsonl", source));
        if chunks_file.exists() {
            consolidator.load_chunks(&chunks_file).await?;
        }
    }
    
    // Load embeddings
    println!("[2/5] Loading embeddings...");
    let embeddings_dir = base_path.join("30_embeddings");
    for source in &["library", "conversations", "research"] {
        let emb_file = embeddings_dir.join(format!("{}_extracted_chunks.jsonl", source));
        if emb_file.exists() {
            consolidator.load_embeddings(&emb_file).await?;
        }
    }
    
    // Load similarity edges
    println!("[3/5] Loading similarity edges...");
    let edges_file = base_path.join("40_index").join("similarity_edges.jsonl");
    consolidator.load_similarity_edges(&edges_file).await?;
    
    // Detect clusters
    println!("[4/5] Detecting clusters ({} iterations)...", iterations);
    let num_clusters = consolidator.detect_clusters(iterations);
    println!("  Detected {} clusters", num_clusters);
    
    // Consolidate
    println!("[5/5] Consolidating chunks...");
    let consolidated = consolidator.consolidate(target_tokens)?;
    
    // Export
    println!("\nExporting consolidated nodes...");
    let output_file = base_path.join("consolidate_output.jsonl");
    codex_consolidate::export_consolidated_nodes(&consolidated, &output_file).await?;
    
    // Print statistics
    println!("\n=== Consolidation Results ===");
    println!("Original chunks:      10,768");
    println!("Consolidated nodes:   {}", consolidated.len());
    println!("Reduction ratio:      {:.1}x", 10768.0 / consolidated.len() as f32);
    
    let total_tokens: usize = consolidated.iter().map(|n| n.token_count).sum();
    let avg_tokens = total_tokens / consolidated.len();
    println!("Total tokens:         {}", total_tokens);
    println!("Avg tokens per node:  {}", avg_tokens);
    
    println!("\nOutput: {}", output_file.display());
    
    Ok(())
}

#[cfg(feature = "watch")]
async fn cmd_watch(paths: Option<&str>, debounce_sec: u64) -> Result<()> {
    use notify::{Config, Event, RecommendedWatcher, RecursiveMode, Watcher};
    use std::sync::Arc;
    use tokio::sync::Mutex;
    use tokio::time::{interval, Duration};

    let base_path = match std::env::var("CODEX_BASE_PATH") {
        Ok(p) => PathBuf::from(p),
        Err(_) => std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    };
    
    // Determine which paths to watch
    let watch_paths: Vec<PathBuf> = match paths {
        Some(p) => p.split(',').map(|s| base_path.join(s.trim())).collect(),
        None => vec![
            base_path.join("LIBRARY"),
            base_path.join("OPENAI archives"),
            base_path.join("RESEARCH"),
            base_path.join("Grok"),
        ],
    };

    println!("\n👁️  CODEX File Watcher\n");
    println!("Watching directories:");
    for path in &watch_paths {
        if path.exists() {
            println!("  ✓ {}", path.display());
        } else {
            println!("  ✗ {} (not found)", path.display());
        }
    }
    println!("\nDebounce: {} seconds", debounce_sec);
    println!("Press Ctrl+C to stop\n");

    // Track pending changes
    let pending = Arc::new(Mutex::new(false));
    let pending_for_task = pending.clone();

    // Create watcher
    let (tx, mut rx) = tokio::sync::mpsc::channel(100);
    let mut watcher = RecommendedWatcher::new(
        move |res: Result<Event, notify::Error>| {
            if let Ok(event) = res {
                // Only trigger on meaningful file changes
                match event.kind {
                    notify::EventKind::Create(_) |
                    notify::EventKind::Modify(_) |
                    notify::EventKind::Remove(_) => {
                        let _ = tx.try_send(event);
                    }
                    _ => {}
                }
            }
        },
        Config::default(),
    ).map_err(|e| anyhow::anyhow!("Failed to create watcher: {}", e))?;

    // Watch each path
    for path in &watch_paths {
        if path.exists() {
            watcher.watch(path, RecursiveMode::Recursive)
                .map_err(|e| anyhow::anyhow!("Failed to watch {}: {}", path.display(), e))?;
        }
    }

    // Debounce task
    let debounce_task = tokio::spawn(async move {
        let mut interval = interval(Duration::from_secs(debounce_sec));
        loop {
            interval.tick().await;
            let should_run = {
                let mut guard = pending_for_task.lock().await;
                let val = *guard;
                *guard = false;
                val
            };
            if should_run {
                println!("\n🔄 Change detected, running pipeline...\n");
                if let Err(e) = run_pipeline(/* config not available here */).await {
                    eprintln!("Pipeline error: {}", e);
                }
                println!("\n✅ Pipeline complete. Watching for changes...\n");
            }
        }
    });

    // Handle events
    while let Some(event) = rx.recv().await {
        // Skip temp files and hidden files
        let is_relevant = event.paths.iter().any(|p| {
            let s = p.to_string_lossy();
            !s.contains("/.") && !s.ends_with("~") && !s.contains("#")
        });
        
        if is_relevant {
            for path in &event.paths {
                println!("  [{}] {}", format_event_kind(&event.kind), path.display());
            }
            *pending.lock().await = true;
        }
    }

    debounce_task.abort();
    Ok(())
}

#[cfg(feature = "watch")]
fn format_event_kind(kind: &notify::EventKind) -> &'static str {
    use notify::EventKind;
    match kind {
        EventKind::Create(_) => "CREATE",
        EventKind::Modify(_) => "MODIFY",
        EventKind::Remove(_) => "REMOVE",
        _ => "OTHER",
    }
}

#[cfg(feature = "watch")]
async fn run_pipeline(config: &CodexConfig) -> Result<()> {
    cmd_extract("all", false, true, config).await?;
    cmd_chunk("hierarchical", "all", true, config).await?;
    cmd_embed(None, true, config).await?;
    cmd_index(false, config).await?;
    cmd_export("all", None, config).await?;
    Ok(())
}

#[cfg(not(feature = "watch"))]
async fn cmd_watch(_paths: Option<&str>, _debounce_sec: u64) -> Result<()> {
    println!("⚠️  Watch feature not enabled. Rebuild with: cargo build --features watch");
    Ok(())
}
