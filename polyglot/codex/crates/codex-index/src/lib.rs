use codex_core::{Result, CodexError};
use std::collections::BinaryHeap;
use std::cmp::Ordering;
use rayon::prelude::*;

/// Embedding vector with its chunk ID.
pub struct Embedding {
    pub chunk_id: String,
    pub vector: Vec<f32>,
}

/// Similarity edge between two chunks.
#[derive(Debug, serde::Serialize)]
pub struct Edge {
    pub source: String,
    pub target: String,
    pub similarity: f32,
    pub rank: usize,
}

/// Load all embeddings from JSONL files in `embed_dir`.
pub fn load_embeddings(embed_dir: &std::path::Path) -> Result<Vec<Embedding>> {
    let mut embeddings = Vec::new();

    for entry in std::fs::read_dir(embed_dir).map_err(CodexError::Io)? {
        let entry = entry.map_err(CodexError::Io)?;
        let path = entry.path();
        if path.extension().and_then(|e| e.to_str()) != Some("jsonl") {
            continue;
        }

        let file = std::fs::File::open(&path).map_err(CodexError::Io)?;
        let reader = std::io::BufReader::new(file);
        for line in std::io::BufRead::lines(reader) {
            let line = line.map_err(CodexError::Io)?;
            if line.trim().is_empty() { continue; }
            let record: EmbeddingRecord = serde_json::from_str(&line)
                .map_err(|e| CodexError::Serialization(e.to_string()))?;
            embeddings.push(Embedding {
                chunk_id: record.chunk_id,
                vector: record.embedding,
            });
        }
    }

    Ok(embeddings)
}

/// Normalize all vectors to unit length (in-place).
pub fn normalize_vectors(embeddings: &mut [Embedding]) {
    embeddings.par_iter_mut().for_each(|emb| {
        let norm = emb.vector.iter().map(|v| v * v).sum::<f32>().sqrt();
        if norm > 0.0 {
            emb.vector.iter_mut().for_each(|v| *v /= norm);
        }
    });
}

/// Build top-K nearest neighbor edges using cosine similarity (dot product of normalized vectors).
pub fn build_knn_index(embeddings: &[Embedding], k: usize) -> Vec<Edge> {
    let n = embeddings.len();
    let dim = embeddings.first().map(|e| e.vector.len()).unwrap_or(0);
    assert!(dim > 0, "No embeddings loaded");

    // Flatten vectors into a single contiguous buffer for SIMD/cache efficiency
    let flat: Vec<f32> = embeddings.iter()
        .flat_map(|e| e.vector.clone())
        .collect();

    let chunk_ids: Vec<String> = embeddings.iter()
        .map(|e| e.chunk_id.clone())
        .collect();

    // For each source vector, compute dot product with all targets and keep top-K
    let results: Vec<Vec<Edge>> = (0..n)
        .into_par_iter()
        .map(|i| {
            let src_vec = &flat[i * dim..(i + 1) * dim];
            let src_id = &chunk_ids[i];

            // Min-heap of size k to track top-K highest similarities
            let mut heap: BinaryHeap<Neighbor> = BinaryHeap::with_capacity(k + 1);

            for j in 0..n {
                if i == j { continue; }
                let tgt_vec = &flat[j * dim..(j + 1) * dim];
                let sim = dot_product(src_vec, tgt_vec);

                heap.push(Neighbor { idx: j, similarity: sim });
                if heap.len() > k {
                    heap.pop(); // Remove lowest similarity
                }
            }

            // Extract edges, sorted by similarity descending
            let mut neighbors: Vec<Neighbor> = heap.into_vec();
            neighbors.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(Ordering::Equal));

            neighbors.into_iter().enumerate().map(|(rank, nb)| Edge {
                source: src_id.clone(),
                target: chunk_ids[nb.idx].clone(),
                similarity: nb.similarity,
                rank: rank + 1,
            }).collect()
        })
        .collect();

    results.into_iter().flatten().collect()
}

/// Write edges as JSONL.
pub fn write_edges(edges: &[Edge], path: &std::path::Path) -> Result<()> {
    use std::io::Write;
    let mut file = std::fs::File::create(path).map_err(CodexError::Io)?;
    for edge in edges {
        let line = serde_json::to_string(edge)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        writeln!(file, "{}", line).map_err(CodexError::Io)?;
    }
    Ok(())
}

/// Write flat binary vectors for fast loading: [n_chunks: u64][dim: u64][chunk_id_len: u32][chunk_id_bytes][vector...]
pub fn write_vectors_binary(embeddings: &[Embedding], path: &std::path::Path) -> Result<()> {
    use std::io::Write;
    let mut file = std::fs::File::create(path).map_err(CodexError::Io)?;

    let n = embeddings.len() as u64;
    let dim = embeddings.first().map(|e| e.vector.len()).unwrap_or(0) as u64;
    file.write_all(&n.to_le_bytes()).map_err(CodexError::Io)?;
    file.write_all(&dim.to_le_bytes()).map_err(CodexError::Io)?;

    for emb in embeddings {
        let id_bytes = emb.chunk_id.as_bytes();
        let len = id_bytes.len() as u32;
        file.write_all(&len.to_le_bytes()).map_err(CodexError::Io)?;
        file.write_all(id_bytes).map_err(CodexError::Io)?;
        for v in &emb.vector {
            file.write_all(&v.to_le_bytes()).map_err(CodexError::Io)?;
        }
    }

    Ok(())
}

#[derive(Debug, serde::Deserialize)]
struct EmbeddingRecord {
    chunk_id: String,
    embedding: Vec<f32>,
}

#[derive(Debug, Clone)]
struct Neighbor {
    idx: usize,
    similarity: f32,
}

impl Eq for Neighbor {}
impl PartialEq for Neighbor {
    fn eq(&self, other: &Self) -> bool {
        self.similarity == other.similarity
    }
}
impl Ord for Neighbor {
    fn cmp(&self, other: &Self) -> Ordering {
        self.similarity.partial_cmp(&other.similarity)
            .unwrap_or(Ordering::Equal)
            .reverse() // Min-heap: smallest similarity at top
    }
}
impl PartialOrd for Neighbor {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

fn dot_product(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

/// Read vectors from flat binary format: [n: u64][dim: u64][id_len: u32][id_bytes][vec...]
pub fn read_vectors_binary(path: &std::path::Path) -> Result<Vec<Embedding>> {
    use std::io::Read;
    let mut file = std::fs::File::open(path).map_err(CodexError::Io)?;
    let mut buf8 = [0u8; 8];

    file.read_exact(&mut buf8).map_err(CodexError::Io)?;
    let n = u64::from_le_bytes(buf8) as usize;
    file.read_exact(&mut buf8).map_err(CodexError::Io)?;
    let dim = u64::from_le_bytes(buf8) as usize;

    let mut embeddings = Vec::with_capacity(n);
    let mut buf4 = [0u8; 4];

    for _ in 0..n {
        file.read_exact(&mut buf4).map_err(CodexError::Io)?;
        let id_len = u32::from_le_bytes(buf4) as usize;
        let mut id_bytes = vec![0u8; id_len];
        file.read_exact(&mut id_bytes).map_err(CodexError::Io)?;
        let chunk_id = String::from_utf8(id_bytes)
            .map_err(|e| CodexError::Serialization(format!("Invalid UTF-8 in binary: {}", e)))?;

        let mut vec_bytes = vec![0u8; dim * 4];
        file.read_exact(&mut vec_bytes).map_err(CodexError::Io)?;
        let vector: Vec<f32> = vec_bytes
            .chunks_exact(4)
            .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
            .collect();

        embeddings.push(Embedding { chunk_id, vector });
    }

    Ok(embeddings)
}

/// Find top-K most similar embeddings to a query vector using dot product.
pub fn query_semantic(
    embeddings: &[Embedding],
    query_vec: &[f32],
    k: usize,
) -> Vec<(String, f32)> {
    let mut heap: BinaryHeap<SemanticNeighbor> = BinaryHeap::with_capacity(k + 1);

    for emb in embeddings {
        let sim = dot_product(&emb.vector, query_vec);
        heap.push(SemanticNeighbor {
            chunk_id: emb.chunk_id.clone(),
            similarity: sim,
        });
        if heap.len() > k {
            heap.pop();
        }
    }

    let mut results: Vec<SemanticNeighbor> = heap.into_vec();
    results.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(Ordering::Equal));

    results.into_iter().map(|n| (n.chunk_id, n.similarity)).collect()
}

#[derive(Debug, Clone)]
struct SemanticNeighbor {
    chunk_id: String,
    similarity: f32,
}

impl Eq for SemanticNeighbor {}
impl PartialEq for SemanticNeighbor {
    fn eq(&self, other: &Self) -> bool {
        self.similarity == other.similarity
    }
}
impl Ord for SemanticNeighbor {
    fn cmp(&self, other: &Self) -> Ordering {
        self.similarity.partial_cmp(&other.similarity)
            .unwrap_or(Ordering::Equal)
            .reverse()
    }
}
impl PartialOrd for SemanticNeighbor {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}
