use anyhow::Result;
use codex_core::Chunk;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, BTreeMap};
use std::path::Path;
use tokio::io::AsyncBufReadExt;
use tracing::info;

/// A consolidated node combining multiple related chunks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsolidatedNode {
    pub id: String,
    pub cluster_id: usize,
    pub content: String,
    pub token_count: usize,
    pub source_chunks: Vec<String>, // Track which chunks were merged
    pub sources: Vec<String>,       // e.g., ["library", "conversations"]
    pub average_similarity: f32,
}

/// Manages chunk consolidation within clusters
pub struct Consolidator {
    chunks: HashMap<String, (Chunk, Vec<f32>)>,
    similarity_links: HashMap<String, Vec<(String, f32)>>,
    clusters: HashMap<String, usize>,
}

impl Default for Consolidator {
    fn default() -> Self {
        Self::new()
    }
}

impl Consolidator {
    pub fn new() -> Self {
        Self {
            chunks: HashMap::new(),
            similarity_links: HashMap::new(),
            clusters: HashMap::new(),
        }
    }

    /// Load chunks with their embeddings
    pub async fn load_chunks(&mut self, chunks_path: &Path) -> Result<usize> {
        let file = tokio::fs::File::open(chunks_path).await?;
        let reader = tokio::io::BufReader::new(file);
        let mut lines = reader.lines();

        let mut count = 0;
        while let Some(line) = lines.next_line().await? {
            if let Ok(chunk) = serde_json::from_str::<Chunk>(&line) {
                self.chunks.insert(chunk.id.clone(), (chunk, Vec::new()));
                count += 1;
            }
        }

        info!("Loaded {} chunks from {:?}", count, chunks_path);
        Ok(count)
    }

    /// Load embeddings
    pub async fn load_embeddings(&mut self, embeddings_path: &Path) -> Result<usize> {
        let file = tokio::fs::File::open(embeddings_path).await?;
        let reader = tokio::io::BufReader::new(file);
        let mut lines = reader.lines();

        let mut count = 0;
        while let Some(line) = lines.next_line().await? {
            let data: serde_json::Value = serde_json::from_str(&line)?;
            if let (Some(chunk_id), Some(emb_arr)) =
                (data.get("chunk_id").and_then(|v| v.as_str()),
                 data.get("embedding").and_then(|v| v.as_array()))
            {
                let embedding: Vec<f32> = emb_arr
                    .iter()
                    .filter_map(|v| v.as_f64().map(|f| f as f32))
                    .collect();

                if let Some((_, ref mut chunk_emb)) = self.chunks.get_mut(chunk_id) {
                    *chunk_emb = embedding;
                    count += 1;
                }
            }
        }

        info!("Loaded {} embeddings", count);
        Ok(count)
    }

    /// Load similarity edges (node links)
    pub async fn load_similarity_edges(&mut self, edges_path: &Path) -> Result<usize> {
        let file = tokio::fs::File::open(edges_path).await?;
        let reader = tokio::io::BufReader::new(file);
        let mut lines = reader.lines();

        let mut count = 0;
        while let Some(line) = lines.next_line().await? {
            let data: serde_json::Value = serde_json::from_str(&line)?;
            if let (Some(source), Some(target), Some(sim)) =
                (data.get("source").and_then(|v| v.as_str()),
                 data.get("target").and_then(|v| v.as_str()),
                 data.get("similarity").and_then(|v| v.as_f64()))
            {
                self.similarity_links
                    .entry(source.to_string())
                    .or_default()
                    .push((target.to_string(), sim as f32));
                count += 1;
            }
        }

        info!("Loaded {} similarity edges", count);
        Ok(count)
    }

    /// Detect clusters using label propagation (same algorithm as viewer.html)
    pub fn detect_clusters(&mut self, iterations: usize) -> usize {
        let chunk_ids: Vec<String> = self.chunks.keys().cloned().collect();
        let mut labels: BTreeMap<String, usize> = chunk_ids
            .iter()
            .enumerate()
            .map(|(i, id)| (id.clone(), i))
            .collect();

        for _iter in 0..iterations {
            let mut new_labels = labels.clone();

            for chunk_id in &chunk_ids {
                if let Some(neighbors) = self.similarity_links.get(chunk_id) {
                    let mut counts: BTreeMap<usize, usize> = BTreeMap::new();

                    for (neighbor_id, _sim) in neighbors {
                        if let Some(&label) = labels.get(neighbor_id) {
                            *counts.entry(label).or_insert(0) += 1;
                        }
                    }

                    if !counts.is_empty() {
                        let max_label = counts
                            .iter()
                            .max_by_key(|&(_, count)| count)
                            .map(|(&label, _)| label)
                            .unwrap_or(labels[chunk_id]);

                        new_labels.insert(chunk_id.clone(), max_label);
                    }
                }
            }

            labels = new_labels;
        }

        // Renumber clusters contiguously
        let unique_labels: Vec<usize> = {
            let mut sorted: Vec<usize> = labels.values().copied().collect();
            sorted.sort();
            sorted.dedup();
            sorted
        };

        let remap: BTreeMap<usize, usize> = unique_labels
            .iter()
            .enumerate()
            .map(|(i, &label)| (label, i))
            .collect();

        for (chunk_id, label) in labels.iter_mut() {
            if let Some(&new_label) = remap.get(label) {
                self.clusters.insert(chunk_id.clone(), new_label);
            }
        }

        info!("Detected {} clusters", remap.len());
        remap.len()
    }

    /// Consolidate chunks within clusters
    /// Target: merge groups of ~4-5 chunks into ~10k token consolidated nodes
    pub fn consolidate(&self, target_tokens: usize) -> Result<Vec<ConsolidatedNode>> {
        let mut consolidated = Vec::new();
        let mut cluster_map: HashMap<usize, Vec<String>> = HashMap::new();

        // Group chunks by cluster
        for (chunk_id, cluster_id) in &self.clusters {
            cluster_map
                .entry(*cluster_id)
                .or_default()
                .push(chunk_id.clone());
        }

        // Within each cluster, create subgroups targeting ~target_tokens
        for (cluster_id, mut chunk_ids) in cluster_map {
            // Sort by similarity to first chunk for coherence
            if !chunk_ids.is_empty() {
                let first_id = chunk_ids[0].clone();
                let mut scored: Vec<(String, f32)> = chunk_ids
                    .into_iter()
                    .map(|id| {
                        let score = if id == first_id {
                            1.0
                        } else {
                            self.similarity_links
                                .get(&first_id)
                                .and_then(|links| {
                                    links
                                        .iter()
                                        .find(|(t, _)| t == &id)
                                        .map(|(_, s)| *s)
                                })
                                .unwrap_or(0.0)
                        };
                        (id, score)
                    })
                    .collect();

                scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                chunk_ids = scored.into_iter().map(|(id, _)| id).collect();
            }

            // Create subgroups within cluster
            let mut current_group = Vec::new();
            let mut current_tokens = 0;

            for chunk_id in chunk_ids {
                if let Some((chunk, _)) = self.chunks.get(&chunk_id) {
                    let tokens = chunk.token_count;

                    // If adding this chunk exceeds target, save current group and start new one
                    if !current_group.is_empty()
                        && current_tokens + tokens > target_tokens
                        && current_tokens > target_tokens / 3
                    {
                        consolidated.push(self.create_consolidated_node(
                            cluster_id,
                            current_group.clone(),
                        )?);
                        current_group.clear();
                        current_tokens = 0;
                    }

                    current_group.push(chunk_id);
                    current_tokens += tokens;
                }
            }

            // Don't lose the last group
            if !current_group.is_empty() {
                consolidated.push(self.create_consolidated_node(cluster_id, current_group)?);
            }
        }

        info!(
            "Consolidated {} chunks into {} nodes",
            self.chunks.len(),
            consolidated.len()
        );
        Ok(consolidated)
    }

    fn create_consolidated_node(
        &self,
        cluster_id: usize,
        chunk_ids: Vec<String>,
    ) -> Result<ConsolidatedNode> {
        let mut content_parts = Vec::new();
        let mut total_tokens = 0;
        let mut sources = std::collections::HashSet::new();
        let mut similarities = Vec::new();

        for chunk_id in &chunk_ids {
            if let Some((chunk, _)) = self.chunks.get(chunk_id) {
                content_parts.push(format!("### [{}]\n{}\n", chunk_id, chunk.content));
                total_tokens += chunk.token_count;
                
                // Extract source from document_id prefix if available
                let doc_prefix = chunk.document_id.split('-').next().unwrap_or("unknown");
                sources.insert(doc_prefix.to_string());

                // Calculate similarity to first chunk
                if let Some(links) = self.similarity_links.get(&chunk_ids[0]) {
                    if let Some((_, sim)) = links.iter().find(|(t, _)| t == chunk_id) {
                        similarities.push(*sim);
                    }
                }
            }
        }

        let avg_sim = if similarities.is_empty() {
            0.0
        } else {
            similarities.iter().sum::<f32>() / similarities.len() as f32
        };

        let node_id = format!("consolidated-{}-{}", cluster_id, chunk_ids[0].split('-').next_back().unwrap_or("0"));

        Ok(ConsolidatedNode {
            id: node_id,
            cluster_id,
            content: content_parts.join("\n---\n"),
            token_count: total_tokens,
            source_chunks: chunk_ids,
            sources: sources.into_iter().collect(),
            average_similarity: avg_sim,
        })
    }
}

/// Export consolidated nodes to JSONL format
pub async fn export_consolidated_nodes(
    nodes: &[ConsolidatedNode],
    output_path: &Path,
) -> Result<usize> {
    let mut writer = tokio::fs::File::create(output_path).await?;
    use tokio::io::AsyncWriteExt;

    for node in nodes {
        let json = serde_json::to_string(node)?;
        writer.write_all(json.as_bytes()).await?;
        writer.write_all(b"\n").await?;
    }

    info!("Exported {} consolidated nodes to {:?}", nodes.len(), output_path);
    Ok(nodes.len())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_consolidator_creation() {
        let consolidator = Consolidator::new();
        assert_eq!(consolidator.chunks.len(), 0);
    }
}
