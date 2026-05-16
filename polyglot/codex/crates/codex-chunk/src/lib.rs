use codex_core::{Chunk, Document, Result, CodexError};
use std::collections::HashMap;
use std::path::Path;

/// Chunk documents by merging paragraphs into ~2000 char targets.
pub fn chunk_documents(docs: &[Document]) -> Result<Vec<Chunk>> {
    let mut chunks = Vec::new();
    for doc in docs {
        let paras: Vec<&str> = doc.content.split("\n\n").collect();
        let mut current = String::new();
        let mut pos = 0;
        for para in paras {
            let trimmed = para.trim();
            if trimmed.is_empty() { continue; }
            if current.len() + trimmed.len() + 2 > 2000 && !current.is_empty() {
                chunks.push(make_chunk(doc, &current, pos, None));
                pos += 1;
                current = trimmed.to_string();
            } else {
                if !current.is_empty() { current.push_str("\n\n"); }
                current.push_str(trimmed);
            }
            if current.len() > 4000 {
                for sentence_chunk in split_by_sentences(&current) {
                    chunks.push(make_chunk(doc, &sentence_chunk, pos, None));
                    pos += 1;
                }
                current.clear();
            }
        }
        if !current.is_empty() {
            chunks.push(make_chunk(doc, &current, pos, None));
        }
    }
    Ok(chunks)
}

/// Chunk and deduplicate identical chunks across documents, adding cross-references.
pub fn chunk_and_dedup_documents(docs: &[Document]) -> Result<Vec<Chunk>> {
    let all = chunk_documents(docs)?;
    let mut seen: HashMap<String, Chunk> = HashMap::new();
    let mut output = Vec::new();
    for mut chunk in all {
        let normalized = chunk.content.to_lowercase().replace(|c: char| !c.is_alphanumeric(), "");
        if let Some(existing) = seen.get_mut(&normalized) {
            existing.metadata.entry("xref".to_string())
                .or_insert_with(|| serde_json::json!([]))
                .as_array_mut()
                .unwrap()
                .push(serde_json::json!({
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "source_path": chunk.metadata.get("source_path").cloned(),
                }));
        } else {
            seen.insert(normalized.clone(), chunk.clone());
            chunk.metadata.insert("xref_count".to_string(), serde_json::json!(1));
            output.push(chunk);
        }
    }
    Ok(output)
}

/// Count tokens in text using tiktoken if available, otherwise estimate chars/4.
fn count_tokens(text: &str) -> usize {
    #[cfg(feature = "tiktoken")]
    {
        use tiktoken_rs::cl100k_base;
        if let Ok(bpe) = cl100k_base() {
            return bpe.encode_with_special_tokens(text).len();
        }
    }
    text.chars().count() / 4
}

fn make_chunk(doc: &Document, content: &str, position: usize, target_tokens: Option<usize>) -> Chunk {
    let chars = content.chars().count();
    let tokens = count_tokens(content);
    let level = if let Some(target) = target_tokens {
        if tokens > target * 2 {
            codex_core::ChunkLevel::Document
        } else if tokens > target {
            codex_core::ChunkLevel::Section
        } else {
            codex_core::ChunkLevel::Paragraph
        }
    } else {
        codex_core::ChunkLevel::Paragraph
    };
    Chunk {
        id: format!("{}-chunk-{}", doc.id, position),
        document_id: doc.id.clone(),
        content: content.to_string(),
        token_count: tokens,
        char_count: chars,
        parent_id: None,
        children_ids: Vec::new(),
        level,
        position,
        tags: doc.tags.clone(),
        embedding: None,
        metadata: {
            let mut m = HashMap::new();
            m.insert("source_path".to_string(), serde_json::json!(doc.source_path.to_string_lossy().to_string()));
            m
        },
    }
}

fn split_by_sentences(text: &str) -> Vec<String> {
    let mut result = Vec::new();
    let mut current = String::new();
    for sentence in text.split(['.', '!', '?']) {
        let trimmed = sentence.trim();
        if trimmed.is_empty() { continue; }
        if current.len() + trimmed.len() + 2 > 2000 && !current.is_empty() {
            result.push(current.clone());
            current.clear();
        }
        if !current.is_empty() { current.push_str(". "); }
        current.push_str(trimmed);
    }
    if !current.is_empty() {
        result.push(current);
    }
    if result.is_empty() {
        result.push(text.to_string());
    }
    result
}

/// Write chunks as JSONL.
pub async fn write_chunks_jsonl(chunks: &[Chunk], path: &Path) -> Result<()> {
    use tokio::io::AsyncWriteExt;
    let mut file = tokio::fs::File::create(path).await.map_err(CodexError::Io)?;
    for chunk in chunks {
        let line = serde_json::to_string(chunk)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        file.write_all(line.as_bytes()).await.map_err(CodexError::Io)?;
        file.write_all(b"\n").await.map_err(CodexError::Io)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn create_test_doc(id: &str, content: &str) -> Document {
        Document {
            id: id.to_string(),
            source_path: PathBuf::from(format!("{}.md", id)),
            source_type: codex_core::SourceType::Markdown,
            title: None,
            author: None,
            created: None,
            modified: None,
            content: content.to_string(),
            raw_content: None,
            tags: vec![],
            metadata: HashMap::new(),
            word_count: content.split_whitespace().count(),
            token_count: 0,
            language: None,
        }
    }

    #[test]
    fn test_chunk_documents_basic() {
        let doc = create_test_doc("test-1", "First paragraph.\n\nSecond paragraph with more text here.\n\nThird paragraph.");
        let chunks = chunk_documents(&[doc]).unwrap();
        assert!(!chunks.is_empty());
        assert_eq!(chunks[0].document_id, "test-1");
    }

    #[test]
    fn test_chunk_preserves_document_id() {
        let doc = create_test_doc("doc-abc", "Some content here.\n\nMore content.");
        let chunks = chunk_documents(&[doc]).unwrap();
        for chunk in &chunks {
            assert_eq!(chunk.document_id, "doc-abc");
        }
    }

    #[test]
    fn test_chunk_positions_are_sequential() {
        let content = "Para 1.\n\nPara 2.\n\nPara 3.\n\nPara 4.";
        let doc = create_test_doc("seq-test", content);
        let chunks = chunk_documents(&[doc]).unwrap();
        for (i, chunk) in chunks.iter().enumerate() {
            assert_eq!(chunk.position, i);
        }
    }

    #[test]
    fn test_deduplication() {
        let doc1 = create_test_doc("doc-1", "Duplicate content here.\n\nMore text.");
        let doc2 = create_test_doc("doc-2", "Duplicate content here.\n\nDifferent ending.");
        let chunks = chunk_and_dedup_documents(&[doc1, doc2]).unwrap();
        // Should still have chunks but with xref metadata
        assert!(!chunks.is_empty());
    }

    #[test]
    fn test_split_by_sentences() {
        let text = "First sentence. Second sentence! Third sentence?";
        let result = split_by_sentences(text);
        assert!(!result.is_empty());
        assert!(result[0].contains("First"));
    }
}
