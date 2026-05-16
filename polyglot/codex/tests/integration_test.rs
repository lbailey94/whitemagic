use std::collections::HashMap;
use std::path::PathBuf;

use codex_core::{Chunk, Document, SourceType, ChunkLevel};

/// Integration test: Full pipeline from document to chunks
#[test]
fn test_document_to_chunk_pipeline() {
    // Create a test document
    let doc = Document {
        id: "integration-test-1".to_string(),
        source_path: PathBuf::from("test_document.md"),
        source_type: SourceType::Markdown,
        title: Some("Integration Test Doc".to_string()),
        author: Some("Test Author".to_string()),
        created: None,
        modified: None,
        content: "# Section 1\n\nThis is paragraph one with some content.\n\nThis is paragraph two with more content to process.\n\n# Section 2\n\nFinal paragraph here.".to_string(),
        raw_content: None,
        tags: vec!["test".to_string(), "integration".to_string()],
        metadata: {
            let mut m = HashMap::new();
            m.insert("test_key".to_string(), serde_json::json!("test_value"));
            m
        },
        word_count: 24,
        token_count: 30,
        language: Some("en".to_string()),
    };

    // Step 1: Verify document structure
    assert_eq!(doc.id, "integration-test-1");
    assert_eq!(doc.title.as_ref().unwrap(), "Integration Test Doc");
    assert_eq!(doc.word_count, 24);

    // Step 2: Chunk the document
    let chunks = codex_chunk::chunk_documents(&[doc.clone()]).unwrap();
    assert!(!chunks.is_empty(), "Should produce at least one chunk");

    // Step 3: Verify chunk properties
    for chunk in &chunks {
        assert_eq!(chunk.document_id, doc.id);
        assert_eq!(chunk.level, ChunkLevel::Paragraph);
        assert!(!chunk.content.is_empty());
        assert!(chunk.token_count > 0);
        assert!(chunk.char_count > 0);
    }

    // Step 4: Verify sequential positions
    for (i, chunk) in chunks.iter().enumerate() {
        assert_eq!(chunk.position, i);
    }
}

/// Integration test: Multiple documents with deduplication
#[test]
fn test_multi_document_deduplication() {
    let docs = vec![
        Document {
            id: "doc-1".to_string(),
            source_path: PathBuf::from("file1.md"),
            source_type: SourceType::Markdown,
            title: None,
            author: None,
            created: None,
            modified: None,
            content: "Common content here.\n\nUnique content one.".to_string(),
            raw_content: None,
            tags: vec![],
            metadata: HashMap::new(),
            word_count: 8,
            token_count: 10,
            language: None,
        },
        Document {
            id: "doc-2".to_string(),
            source_path: PathBuf::from("file2.md"),
            source_type: SourceType::Markdown,
            title: None,
            author: None,
            created: None,
            modified: None,
            content: "Common content here.\n\nUnique content two.".to_string(),
            raw_content: None,
            tags: vec![],
            metadata: HashMap::new(),
            word_count: 8,
            token_count: 10,
            language: None,
        },
    ];

    let chunks = codex_chunk::chunk_and_dedup_documents(&docs).unwrap();
    assert!(!chunks.is_empty());

    // Verify document IDs are preserved in cross-references
    let doc_ids: Vec<&str> = chunks.iter().map(|c| c.document_id.as_str()).collect();
    assert!(doc_ids.contains(&"doc-1") || doc_ids.contains(&"doc-2"));
}

/// Integration test: JSON serialization roundtrip
#[test]
fn test_json_roundtrip() {
    let original = Chunk {
        id: "test-chunk-123".to_string(),
        document_id: "doc-456".to_string(),
        content: "Test content for serialization".to_string(),
        token_count: 5,
        char_count: 30,
        parent_id: Some("parent-789".to_string()),
        children_ids: vec!["child-001".to_string()],
        level: ChunkLevel::Section,
        position: 2,
        tags: vec!["tag1".to_string(), "tag2".to_string()],
        embedding: Some(vec![0.1, 0.2, 0.3]),
        metadata: {
            let mut m = HashMap::new();
            m.insert("key".to_string(), serde_json::json!("value"));
            m
        },
    };

    // Serialize
    let json = serde_json::to_string(&original).unwrap();

    // Deserialize
    let restored: Chunk = serde_json::from_str(&json).unwrap();

    // Verify
    assert_eq!(restored.id, original.id);
    assert_eq!(restored.document_id, original.document_id);
    assert_eq!(restored.content, original.content);
    assert_eq!(restored.token_count, original.token_count);
    assert_eq!(restored.level, original.level);
    assert_eq!(restored.position, original.position);
    assert_eq!(restored.embedding, original.embedding);
}

/// Integration test: Error handling
#[test]
fn test_error_handling() {
    use codex_core::CodexError;

    let io_err = CodexError::Io(std::io::Error::new(std::io::ErrorKind::NotFound, "file missing"));
    assert!(io_err.to_string().contains("IO error"));

    let not_found = CodexError::NotFound("test.txt".to_string());
    assert!(not_found.to_string().contains("Not found: test.txt"));
}
