use codex_core::{Document, SourceType, Result, CodexError};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;
use regex::Regex;

/// Extract all text documents from a directory path.
pub async fn extract_directory(
    path: &Path,
    base_path: &Path,
) -> Result<Vec<Document>> {
    let mut documents = Vec::new();

    for entry in WalkDir::new(path)
        .follow_links(true)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let file_path = entry.path();
        if !file_path.is_file() {
            continue;
        }

        let ext = file_path
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        let source_type = match ext.as_str() {
            "txt" | "text" => SourceType::Text,
            "md" | "markdown" => SourceType::Markdown,
            _ => continue, // Skip non-text files for now
        };

        let doc = extract_file(file_path, base_path, source_type).await?;
        documents.push(doc);
    }

    Ok(documents)
}

/// Extract a single file into a Document.
async fn extract_file(
    file_path: &Path,
    base_path: &Path,
    source_type: SourceType,
) -> Result<Document> {
    let bytes = tokio::fs::read(file_path).await
        .map_err(|e| CodexError::Extraction {
            path: file_path.to_path_buf(),
            reason: e.to_string(),
        })?;

    let (content, encoding_guess) = decode_with_encoding(&bytes)?;

    let rel_path = file_path.strip_prefix(base_path)
        .unwrap_or(file_path)
        .to_path_buf();

    let title = extract_title(&content, &rel_path, &source_type);

    let word_count = content.split_whitespace().count();

    let mut metadata = HashMap::new();
    metadata.insert("encoding".to_string(), serde_json::Value::String(encoding_guess));
    metadata.insert("file_size".to_string(), serde_json::Value::Number(bytes.len().into()));

    let id = format!("doc-{}", uuid::Uuid::new_v4().to_string().split('-').next().unwrap());

    Ok(Document {
        id,
        source_path: rel_path,
        source_type,
        title,
        author: None,
        created: None,
        modified: None,
        content: content.clone(),
        raw_content: Some(content),
        tags: Vec::new(),
        metadata,
        word_count,
        token_count: 0, // Will be computed during chunking
        language: None,
    })
}

/// Detect encoding and decode bytes to String.
fn decode_with_encoding(bytes: &[u8]) -> Result<(String, String)> {
    // Try UTF-8 first
    if let Ok(text) = String::from_utf8(bytes.to_vec()) {
        return Ok((text, "utf-8".to_string()));
    }

    // Fall back to chardetng
    let mut detector = chardetng::EncodingDetector::new();
    detector.feed(bytes, true);
    let (encoding, _confidence) = detector.guess_assess(None, true);

    let coder = encoding_rs::Encoding::for_label(encoding.name().as_bytes())
        .ok_or_else(|| CodexError::Extraction {
            path: PathBuf::from("<decode>"),
            reason: format!("Unknown encoding: {}", encoding.name()),
        })?;

    let (text, _encoding_used, had_errors) = coder.decode(bytes);
    if had_errors {
        // Best-effort: replace invalid characters
    }

    Ok((text.into_owned(), encoding.name().to_string()))
}

/// Extract title from content or filename.
fn extract_title(content: &str, path: &Path, source_type: &SourceType) -> Option<String> {
    // Try to find first markdown heading
    if matches!(source_type, SourceType::Markdown) {
        let heading_re = Regex::new(r"^#\s+(.+)$").ok()?;
        for line in content.lines().take(20) {
            let trimmed = line.trim();
            if let Some(caps) = heading_re.captures(trimmed) {
                return Some(caps.get(1)?.as_str().trim().to_string());
            }
        }
    }

    // Try first non-empty line as title
    for line in content.lines().take(5) {
        let trimmed = line.trim();
        if !trimmed.is_empty() && trimmed.len() < 200 {
            return Some(trimmed.to_string());
        }
    }

    // Fall back to filename
    path.file_stem()
        .and_then(|s| s.to_str())
        .map(|s| s.to_string())
}

/// Write documents as JSONL to a file.
pub async fn write_jsonl(docs: &[Document], output_path: &Path) -> Result<()> {
    use tokio::io::AsyncWriteExt;

    let mut file = tokio::fs::File::create(output_path).await
        .map_err(CodexError::Io)?;

    for doc in docs {
        let line = serde_json::to_string(doc)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        file.write_all(line.as_bytes()).await.map_err(CodexError::Io)?;
        file.write_all(b"\n").await.map_err(CodexError::Io)?;
    }

    Ok(())
}

/// Read documents from a JSONL file.
pub async fn read_jsonl(input_path: &Path) -> Result<Vec<Document>> {
    use tokio::io::AsyncBufReadExt;

    let file = tokio::fs::File::open(input_path).await
        .map_err(CodexError::Io)?;
    let reader = tokio::io::BufReader::new(file);
    let mut lines = reader.lines();

    let mut docs = Vec::new();
    while let Some(line) = lines.next_line().await.map_err(CodexError::Io)? {
        if line.trim().is_empty() {
            continue;
        }
        let doc: Document = serde_json::from_str(&line)
            .map_err(|e| CodexError::Serialization(e.to_string()))?;
        docs.push(doc);
    }

    Ok(docs)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_extract_title_from_markdown() {
        let content = "# My Title\n\nSome body text here.";
        let path = PathBuf::from("test.md");
        let title = extract_title(content, &path, &SourceType::Markdown);
        assert_eq!(title, Some("My Title".to_string()));
    }

    #[test]
    fn test_extract_title_from_text() {
        let content = "First line\nSecond line";
        let path = PathBuf::from("test.txt");
        let title = extract_title(content, &path, &SourceType::Text);
        assert_eq!(title, Some("First line".to_string()));
    }

    #[test]
    fn test_extract_title_fallback_to_filename() {
        let content = "\n\n\n"; // only empty lines
        let path = PathBuf::from("special-file.md");
        let title = extract_title(content, &path, &SourceType::Markdown);
        assert_eq!(title, Some("special-file".to_string()));
    }

    #[test]
    fn test_decode_utf8() {
        let bytes = b"Hello, UTF-8!";
        let (text, encoding) = decode_with_encoding(bytes).unwrap();
        assert_eq!(text, "Hello, UTF-8!");
        assert_eq!(encoding, "utf-8");
    }
}
