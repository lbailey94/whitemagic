use codex_core::{Chunk, Result, CodexError};
use std::collections::HashSet;
use std::path::Path;
use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};

/// Embed all chunks from JSONL files in `input_dir` using local FastEmbed or OpenAI API.
#[allow(clippy::too_many_arguments, unused_variables)]
pub async fn embed_directory(
    input_dir: &Path,
    output_dir: &Path,
    api_key: Option<&str>,
    model_name: &str,
    dimensions: usize,
    batch_size: usize,
    rate_limit_rps: f32,
    max_retries: usize,
    resume: bool,
    base_url: &str,
) -> Result<()> {
    tokio::fs::create_dir_all(output_dir).await.map_err(CodexError::Io)?;

    let checkpoint_path = output_dir.join("checkpoint.json");
    let mut completed: HashSet<String> = if resume && checkpoint_path.exists() {
        let bytes = tokio::fs::read(&checkpoint_path).await.map_err(CodexError::Io)?;
        let ids: Vec<String> = serde_json::from_slice(&bytes)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        println!("Resuming from checkpoint: {} chunks already embedded", ids.len());
        ids.into_iter().collect()
    } else {
        HashSet::new()
    };

    let mut local_model = None;
    #[cfg(feature = "api")]
    let mut api_client = None;

    #[cfg(feature = "api")]
    if let Some(key) = api_key {
        if !key.is_empty() {
            api_client = Some((reqwest::Client::new(), RateLimiter::new(rate_limit_rps)));
            println!("Using OpenAI API with model: {}", model_name);
        }
    }

    let use_api = {
        #[cfg(feature = "api")]
        { api_client.is_some() }
        #[cfg(not(feature = "api"))]
        { false }
    };

    if !use_api {
        #[cfg(feature = "local")]
        {
            use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
            println!("Initializing local FastEmbed model (BGE-Small-EN-v1.5)...");
            let mut options = InitOptions::default();
            options.model_name = EmbeddingModel::BGESmallENV15;
            options.show_download_progress = true;

            let model = TextEmbedding::try_new(options)
                .map_err(|e| CodexError::Embedding(format!("FastEmbed init: {}", e)))?;
            local_model = Some(model);
        }
        #[cfg(not(feature = "local"))]
        {
            return Err(CodexError::Embedding("No API key provided and local feature is disabled".into()).into());
        }
    }

    let mut entries = tokio::fs::read_dir(input_dir).await.map_err(CodexError::Io)?;
    while let Some(entry) = entries.next_entry().await.map_err(CodexError::Io)? {
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("jsonl") {
            continue;
        }

        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("embeddings");
        if stem == "all" || stem.starts_with("all_") {
            continue;
        }
        let output_file = output_dir.join(format!("{}.jsonl", stem));

        let mut output = if resume && output_file.exists() {
            tokio::fs::OpenOptions::new()
                .append(true)
                .open(&output_file).await.map_err(CodexError::Io)?
        } else {
            tokio::fs::File::create(&output_file).await.map_err(CodexError::Io)?
        };

        let chunks = read_chunks_jsonl(&path).await?;
        let total = chunks.len();
        let pending: Vec<&Chunk> = chunks.iter()
            .filter(|c| !completed.contains(&c.id))
            .collect();

        if pending.is_empty() {
            println!("Skipping {} (all {} chunks already embedded)", stem, total);
            continue;
        }

        println!("Embedding {}: {} chunks ({} pending)", stem, total, pending.len());
        let bar = indicatif::ProgressBar::new(pending.len() as u64);
        bar.set_style(
            indicatif::ProgressStyle::default_bar()
                .template("{bar:40} {pos}/{len} {msg}")
                .unwrap()
                .progress_chars("=>-"),
        );

        for batch in pending.chunks(batch_size) {
            let texts: Vec<String> = batch.iter().map(|c| c.content.clone()).collect();
            let chunk_ids: Vec<String> = batch.iter().map(|c| c.id.clone()).collect();

            let vectors = if use_api {
                #[cfg(feature = "api")]
                {
                    let (client, limiter) = api_client.as_mut().unwrap();
                    embed_batch(client, api_key.unwrap(), model_name, dimensions, &texts, max_retries, limiter, base_url).await?
                }
                #[cfg(not(feature = "api"))]
                { unreachable!() }
            } else if let Some(model) = &local_model {
                // local_model is fastembed TextEmbedding
                model.embed(texts, None)
                    .map_err(|e| CodexError::Embedding(format!("FastEmbed error: {}", e)))?
            } else {
                unreachable!()
            };

            for (chunk_id, vector) in chunk_ids.iter().zip(vectors.iter()) {
                let record = EmbeddingRecord {
                    chunk_id: chunk_id.clone(),
                    embedding: vector.clone(),
                };
                let line = serde_json::to_string(&record)
                    .map_err(|e| CodexError::Serialization(e.to_string()))?;
                use tokio::io::AsyncWriteExt;
                output.write_all(line.as_bytes()).await.map_err(CodexError::Io)?;
                output.write_all(b"\n").await.map_err(CodexError::Io)?;
                completed.insert(chunk_id.clone());
            }
            bar.inc(batch.len() as u64);
        }

        bar.finish_with_message("Done");
        save_checkpoint(&checkpoint_path, &completed).await?;
    }

    println!("Embedding complete. Total embedded: {} chunks", completed.len());
    Ok(())
}

async fn read_chunks_jsonl(path: &Path) -> Result<Vec<Chunk>> {
    use tokio::io::AsyncBufReadExt;
    let file = tokio::fs::File::open(path).await.map_err(CodexError::Io)?;
    let reader = tokio::io::BufReader::new(file);
    let mut lines = reader.lines();

    let mut chunks = Vec::new();
    while let Some(line) = lines.next_line().await.map_err(CodexError::Io)? {
        if line.trim().is_empty() { continue; }
        let chunk: Chunk = serde_json::from_str(&line)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        chunks.push(chunk);
    }
    Ok(chunks)
}

async fn save_checkpoint(path: &Path, completed: &HashSet<String>) -> Result<()> {
    let ids: Vec<String> = completed.iter().cloned().collect();
    let bytes = serde_json::to_vec(&ids)
        .map_err(|e| CodexError::Serialization(e.to_string()))?;
    tokio::fs::write(path, bytes).await.map_err(CodexError::Io)?;
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct EmbeddingRecord {
    pub chunk_id: String,
    pub embedding: Vec<f32>,
}

#[cfg(feature = "api")]
#[derive(Debug, Serialize)]
struct OpenAiRequest {
    model: String,
    input: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    dimensions: Option<usize>,
}

#[cfg(feature = "api")]
#[derive(Debug, Deserialize)]
struct OpenAiResponse {
    data: Vec<OpenAiEmbedding>,
}

#[cfg(feature = "api")]
#[derive(Debug, Deserialize)]
struct OpenAiEmbedding {
    index: usize,
    embedding: Vec<f32>,
}

#[cfg(feature = "api")]
async fn embed_batch(
    client: &reqwest::Client,
    api_key: &str,
    model: &str,
    dimensions: usize,
    texts: &[String],
    max_retries: usize,
    rate_limiter: &mut RateLimiter,
    base_url: &str,
) -> Result<Vec<Vec<f32>>> {
    let request = OpenAiRequest {
        model: model.to_string(),
        input: texts.to_vec(),
        dimensions: if dimensions > 0 { Some(dimensions) } else { None },
    };

    let mut last_err = None;
    for attempt in 0..max_retries {
        rate_limiter.acquire().await;

        let response = client
            .post(format!("{}/embeddings", base_url))
            .header("Authorization", format!("Bearer {}", api_key))
            .header("HTTP-Referer", "https://github.com/codex")
            .header("X-Title", "CODEX")
            .json(&request)
            .send()
            .await;

        match response {
            Ok(resp) => {
                let status = resp.status();
                let body = resp.text().await;
                match body {
                    Ok(text) => {
                        if status.is_success() {
                            let parsed: OpenAiResponse = serde_json::from_str(&text)
                                .map_err(|e| CodexError::Embedding(format!("JSON parse: {}", e)))?;
                            // Sort by index to match input order
                            let mut results: Vec<(usize, Vec<f32>)> = parsed.data
                                .into_iter()
                                .map(|d| (d.index, d.embedding))
                                .collect();
                            results.sort_by_key(|(idx, _)| *idx);
                            return Ok(results.into_iter().map(|(_, v)| v).collect());
                        } else {
                            let delay = Duration::from_secs(2u64.pow(attempt as u32));
                            last_err = Some(CodexError::Embedding(format!(
                                "HTTP {}: {} (retry in {:?})", status, text, delay
                            )));
                            if attempt + 1 < max_retries {
                                tokio::time::sleep(delay).await;
                            }
                        }
                    }
                    Err(e) => {
                        last_err = Some(CodexError::Embedding(e.to_string()));
                        if attempt + 1 < max_retries {
                            tokio::time::sleep(Duration::from_secs(2u64.pow(attempt as u32))).await;
                        }
                    }
                }
            }
            Err(e) => {
                last_err = Some(CodexError::Embedding(e.to_string()));
                if attempt + 1 < max_retries {
                    tokio::time::sleep(Duration::from_secs(2u64.pow(attempt as u32))).await;
                }
            }
        }
    }

    Err(last_err.unwrap_or_else(|| CodexError::Embedding("All retries exhausted".to_string())))
}

#[allow(dead_code)]
struct RateLimiter {
    delay: Duration,
    last_request: Option<Instant>,
}

#[allow(dead_code)]
impl RateLimiter {
    fn new(rps: f32) -> Self {
        Self {
            delay: Duration::from_secs_f32(1.0 / rps),
            last_request: None,
        }
    }

    async fn acquire(&mut self) {
        if let Some(last) = self.last_request {
            let elapsed = last.elapsed();
            if elapsed < self.delay {
                tokio::time::sleep(self.delay - elapsed).await;
            }
        }
        self.last_request = Some(Instant::now());
    }
}


#[cfg(feature = "local")]
/// Embed a single query string using the local FastEmbed model.
pub fn embed_query_text(text: &str) -> Result<Vec<f32>> {
    use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
    let mut options = InitOptions::default();
    options.model_name = EmbeddingModel::BGESmallENV15;
    options.show_download_progress = false;

    let model = TextEmbedding::try_new(options)
        .map_err(|e| CodexError::Embedding(format!("FastEmbed init: {}", e)))?;

    let embeddings = model.embed(vec![text.to_string()], None)
        .map_err(|e| CodexError::Embedding(format!("FastEmbed error: {}", e)))?;

    embeddings.into_iter().next()
        .ok_or_else(|| CodexError::Embedding("No embedding returned".to_string()))
}

/// Embed a single query string — always available, with graceful fallback.
/// Uses local FastEmbed when the `local` feature is enabled, otherwise
/// returns an error instructing the user to rebuild with `--features local`.
pub fn embed_query(text: &str) -> Result<Vec<f32>> {
    #[cfg(feature = "local")]
    {
        embed_query_text(text)
    }
    #[cfg(not(feature = "local"))]
    {
        Err(CodexError::Embedding(
            "Semantic search is not available: rebuild with `--features local` to enable local embeddings, \
             or provide an API key for API-based embeddings.".into()
        ))
    }
}
