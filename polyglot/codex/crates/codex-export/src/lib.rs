use codex_core::{Result, CodexError};
use std::collections::HashMap;
use std::path::Path;

#[derive(Debug, serde::Serialize)]
pub struct SphereNode {
    pub id: String,
    pub label: String,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub color: String,
    pub size: f64,
    pub source: String,
    pub token_count: usize,
    pub links: Vec<NodeLink>,
    pub content_preview: String,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct NodeLink {
    pub target: String,
    pub similarity: f32,
    pub rank: usize,
}

#[derive(Debug, serde::Serialize)]
pub struct VayaVidaSphere {
    pub version: String,
    pub total_nodes: usize,
    pub total_links: usize,
    pub nodes: Vec<SphereNode>,
}

/// Export chunks and their similarity edges as a Vaya Vida sphere.
pub fn export_vaya_vida(
    chunks_dir: &Path,
    edges_path: &Path,
    output_path: &Path,
) -> Result<()> {
    let chunks = load_chunks(chunks_dir)?;
    let edges = load_edges(edges_path)?;

    // Build edge lookup: source chunk -> top links
    let mut edge_map: HashMap<String, Vec<NodeLink>> = HashMap::new();
    for e in edges {
        edge_map.entry(e.source.clone()).or_default().push(NodeLink {
            target: e.target,
            similarity: e.similarity,
            rank: e.rank,
        });
    }

    // Sort links by similarity descending and truncate to top 5 per node
    for links in edge_map.values_mut() {
        links.sort_by(|a, b| b.similarity.partial_cmp(&a.similarity).unwrap_or(std::cmp::Ordering::Equal));
        links.truncate(5);
    }

    // Assign positions on Fibonacci sphere
    let n = chunks.len();
    let golden_ratio = (1.0 + 5f64.sqrt()) / 2.0;

    let nodes: Vec<SphereNode> = chunks.into_iter().enumerate().map(|(i, chunk)| {
        let theta = 2.0 * std::f64::consts::PI * (i as f64) / golden_ratio;
        let phi = (1.0 - 2.0 * (i as f64 + 0.5) / (n as f64)).acos();

        let x = phi.sin() * theta.cos();
        let y = phi.sin() * theta.sin();
        let z = phi.cos();

        let source = infer_source(&chunk.document_id);
        let color = match source.as_str() {
            "conversations" => "#4ade80", // green
            "research" => "#fb923c",     // orange
            _ => "#60a5fa",              // blue (library default)
        };

        let size = (chunk.token_count as f64 / 1000.0).clamp(0.5, 3.0);
        let preview = chunk.content.chars().take(120).collect::<String>() + "...";

        SphereNode {
            id: chunk.id.clone(),
            label: chunk.id.clone(),
            x,
            y,
            z,
            color: color.to_string(),
            size,
            source,
            token_count: chunk.token_count,
            links: edge_map.get(&chunk.id).cloned().unwrap_or_default(),
            content_preview: preview,
        }
    }).collect();

    let total_links = nodes.iter().map(|n| n.links.len()).sum();

    let sphere = VayaVidaSphere {
        version: "v2.0".to_string(),
        total_nodes: nodes.len(),
        total_links,
        nodes,
    };

    let json = serde_json::to_string_pretty(&sphere)
        .map_err(|e| CodexError::Serialization(e.to_string()))?;
    std::fs::write(output_path, json).map_err(CodexError::Io)?;

    println!("Exported {} nodes, {} links to {:?}", sphere.total_nodes, total_links, output_path);
    Ok(())
}

fn infer_source(document_id: &str) -> String {
    if document_id.starts_with("conv-") || document_id.starts_with("doc-conv-") {
        "conversations".to_string()
    } else if document_id.starts_with("research-") || document_id.starts_with("doc-research-") {
        "research".to_string()
    } else {
        "library".to_string()
    }
}

fn load_chunks(chunks_dir: &Path) -> Result<Vec<codex_core::Chunk>> {
    let mut chunks = Vec::new();
    for entry in std::fs::read_dir(chunks_dir).map_err(CodexError::Io)? {
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
            let chunk: codex_core::Chunk = serde_json::from_str(&line)
                .map_err(|e| CodexError::Serialization(e.to_string()))?;
            chunks.push(chunk);
        }
    }
    Ok(chunks)
}

#[derive(Debug, serde::Deserialize)]
struct EdgeRecord {
    source: String,
    target: String,
    similarity: f32,
    rank: usize,
}

fn load_edges(edges_path: &Path) -> Result<Vec<EdgeRecord>> {
    if !edges_path.exists() {
        return Ok(Vec::new());
    }
    let file = std::fs::File::open(edges_path).map_err(CodexError::Io)?;
    let reader = std::io::BufReader::new(file);
    let mut edges = Vec::new();
    for line in std::io::BufRead::lines(reader) {
        let line = line.map_err(CodexError::Io)?;
        if line.trim().is_empty() { continue; }
        let edge: EdgeRecord = serde_json::from_str(&line)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        edges.push(edge);
    }
    Ok(edges)
}
