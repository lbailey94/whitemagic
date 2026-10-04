use rusqlite::Connection;
use std::sync::Arc;
use tempfile::tempdir;
use uuid::Uuid;

use wm_gen3_shm::{RawTuple, ShmSubstrate, ShmTupleSpace};
use wm_gen3_zeropointfive::System05;
use wm_gen3_vault::chunker::Chunker;
use wm_gen3_vault::extractor::{OpencodeExtractor, NormalizedTurn};
use wm_gen3_vault::graph::CausalGraphBuilder;
use wm_gen3_vault::retrieval::TacitVaultEngine;
use wm_gen3_vault::schema::open_vault_db;
use wm_gen3_vault::shm_bridge::{VaultShmBridge, VaultShmRequest, VaultShmResponse, VAULT_REQUEST_KIND, VAULT_RESPONSE_KIND};

#[test]
fn test_schema_initialization_and_tables() {
    let dir = tempdir().expect("temp dir");
    let db_path = dir.path().join("tacit_vault_test.db");

    let conn = open_vault_db(&db_path).expect("open vault db");

    // Verify tables exist
    let count: i64 = conn.query_row(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('vault_sessions', 'vault_turns', 'vault_chunks', 'vault_nodes', 'vault_edges', 'vault_embeddings')",
        [],
        |row| row.get(0),
    ).expect("query tables");
    assert_eq!(count, 6, "Expected 6 core relational tables");

    // Verify FTS5 virtual table exists
    let fts_count: i64 = conn.query_row(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='vault_fts'",
        [],
        |row| row.get(0),
    ).expect("query fts");
    assert_eq!(fts_count, 1, "Expected vault_fts virtual table");
}

#[test]
fn test_extractor_normalization_and_redaction() {
    let conn = Connection::open_in_memory().expect("in-memory db");

    // Create mock opencode schema
    conn.execute_batch(
        r#"
        CREATE TABLE session (
            id text PRIMARY KEY,
            project_id text NOT NULL,
            title text NOT NULL,
            time_created integer NOT NULL,
            time_updated integer NOT NULL,
            cost real DEFAULT 0 NOT NULL,
            tokens_input integer DEFAULT 0 NOT NULL,
            tokens_output integer DEFAULT 0 NOT NULL
        );
        CREATE TABLE message (
            id text PRIMARY KEY,
            session_id text NOT NULL,
            time_created integer NOT NULL,
            time_updated integer NOT NULL,
            data text NOT NULL
        );
        CREATE TABLE part (
            id text PRIMARY KEY,
            message_id text NOT NULL,
            session_id text NOT NULL,
            time_created integer NOT NULL,
            time_updated integer NOT NULL,
            data text NOT NULL
        );
        "#,
    ).expect("init mock schema");

    // Insert mock session
    conn.execute(
        "INSERT INTO session (id, project_id, title, time_created, time_updated, cost, tokens_input, tokens_output) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        rusqlite::params!["sess_01", "proj_01", "Mandala Landlock Implementation", 1000, 2000, 0.05, 500, 1000],
    ).expect("insert session");

    // Insert user prompt with secret key
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params!["msg_01", "sess_01", 1000, 1000, r#"{"role": "user"}"#],
    ).expect("insert msg 1");
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        rusqlite::params!["p_01", "msg_01", "sess_01", 1000, 1000, r#"{"type": "text", "text": "Let's build Gate 13 Landlock LSM using key sk-abcdef12345678901234567890?"}"#],
    ).expect("insert part 1");

    // Insert assistant error
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params!["msg_02", "sess_01", 1100, 1100, r#"{"role": "assistant"}"#],
    ).expect("insert msg 2");
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        rusqlite::params!["p_02", "msg_02", "sess_01", 1100, 1100, r#"{"type": "tool", "text": "error: Landlock abi version mismatch failed"}"#],
    ).expect("insert part 2");

    // Insert assistant breakthrough
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5)",
        rusqlite::params!["msg_03", "sess_01", 1200, 1200, r#"{"role": "assistant"}"#],
    ).expect("insert msg 3");
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        rusqlite::params!["p_03", "msg_03", "sess_01", 1200, 1200, r#"{"type": "text", "text": "I fixed the ABI negotiation. test result: ok. 5 passed. Ratified!"}"#],
    ).expect("insert part 3");

    let extractor = OpencodeExtractor::from_connection(conn);
    let sessions = extractor.list_sessions().expect("list sessions");
    assert_eq!(sessions.len(), 1);
    assert_eq!(sessions[0].title, "Mandala Landlock Implementation");

    let turns = extractor.extract_session_turns("sess_01").expect("extract turns");
    assert_eq!(turns.len(), 3);

    // Verify Turn 0: User question with secret redaction
    assert_eq!(turns[0].role, "user");
    assert_eq!(turns[0].turn_type, "question");
    assert!(turns[0].clean_text.contains("[REDACTED_API_KEY]"));
    assert!(!turns[0].clean_text.contains("sk-abcdef12345678901234567890"));
    assert!(turns[0].importance >= 0.7);

    // Verify Turn 1: Error
    assert_eq!(turns[1].turn_type, "error");
    assert!(turns[1].valence < 0.0);

    // Verify Turn 2: Breakthrough
    assert_eq!(turns[2].turn_type, "breakthrough");
    assert!(turns[2].importance >= 0.9);
    assert!(turns[2].valence > 0.0);
}

#[test]
fn test_4_tier_semantic_chunking() {
    let turns = vec![
        NormalizedTurn {
            turn_id: "s1-0".to_string(),
            session_id: "s1".to_string(),
            seq: 0,
            role: "user".to_string(),
            turn_type: "question".to_string(),
            clean_text: "How do we make sub-symbolic transport default?".to_string(),
            importance: 0.8,
            valence: 0.0,
            time_created: 1000,
            raw_message_id: "m0".to_string(),
        },
        NormalizedTurn {
            turn_id: "s1-1".to_string(),
            session_id: "s1".to_string(),
            seq: 1,
            role: "assistant".to_string(),
            turn_type: "decision".to_string(),
            clean_text: "We should use POSIX shared memory /dev/shm and Linda tuple spaces.".to_string(),
            importance: 0.9,
            valence: 0.5,
            time_created: 1050,
            raw_message_id: "m1".to_string(),
        },
        NormalizedTurn {
            turn_id: "s1-2".to_string(),
            session_id: "s1".to_string(),
            seq: 2,
            role: "assistant".to_string(),
            turn_type: "breakthrough".to_string(),
            clean_text: "test result: ok. 6 passed in 0.15s. Ratified 340,000x speedup!".to_string(),
            importance: 0.95,
            valence: 0.9,
            time_created: 1100,
            raw_message_id: "m2".to_string(),
        },
    ];

    let chunks = Chunker::chunk_session("s1", "Sub-Symbolic Genesis", &turns);
    assert!(chunks.len() >= 4, "Should have Tier 0, Tier 1, Tier 2, and Tier 3 chunks");

    let t0 = chunks.iter().filter(|c| c.tier == 0).count();
    let t1 = chunks.iter().filter(|c| c.tier == 1).count();
    let t2 = chunks.iter().filter(|c| c.tier == 2).count();
    let t3 = chunks.iter().filter(|c| c.tier == 3).count();

    assert_eq!(t0, 3, "Tier 0 should have 3 atomic turns");
    assert_eq!(t1, 1, "Tier 1 should have 1 dyad exchange");
    assert_eq!(t2, 1, "Tier 2 should have 1 episode");
    assert_eq!(t3, 1, "Tier 3 should have 1 gestalt digest");

    // All chunks must have 64-char SHA256 hashes
    for c in &chunks {
        assert_eq!(c.content_hash.len(), 64);
    }
}

#[test]
fn test_causal_graph_mining() {
    let turns = vec![
        NormalizedTurn {
            turn_id: "s2-0".to_string(),
            session_id: "s2".to_string(),
            seq: 0,
            role: "user".to_string(),
            turn_type: "message".to_string(),
            clean_text: "Let's build the Ganying Mesh Port 7369 wire protocol.".to_string(),
            importance: 0.85,
            valence: 0.1,
            time_created: 1000,
            raw_message_id: "m0".to_string(),
        },
        NormalizedTurn {
            turn_id: "s2-1".to_string(),
            session_id: "s2".to_string(),
            seq: 1,
            role: "assistant".to_string(),
            turn_type: "error".to_string(),
            clean_text: "error: port 7369 bind failed: address already in use".to_string(),
            importance: 0.6,
            valence: -0.5,
            time_created: 1050,
            raw_message_id: "m1".to_string(),
        },
        NormalizedTurn {
            turn_id: "s2-2".to_string(),
            session_id: "s2".to_string(),
            seq: 2,
            role: "assistant".to_string(),
            turn_type: "breakthrough".to_string(),
            clean_text: "SO_REUSEADDR and SO_REUSEPORT configured. test result: ok. 10 passed.".to_string(),
            importance: 0.95,
            valence: 0.9,
            time_created: 1100,
            raw_message_id: "m2".to_string(),
        },
    ];

    let (nodes, edges) = CausalGraphBuilder::mine_session_graph("s2", &turns);
    assert!(!nodes.is_empty(), "Should extract graph nodes");
    assert!(!edges.is_empty(), "Should extract causal relations");

    let has_directive = nodes.iter().any(|n| n.node_type == "directive");
    let has_problem = nodes.iter().any(|n| n.node_type == "problem");
    let has_breakthrough = nodes.iter().any(|n| n.node_type == "breakthrough");
    let has_concept = nodes.iter().any(|n| n.node_type == "concept");

    assert!(has_directive, "Must identify Directive node");
    assert!(has_problem, "Must identify Problem node");
    assert!(has_breakthrough, "Must identify Breakthrough node");
    assert!(has_concept, "Must identify Concept node");

    let has_supersedes = edges.iter().any(|e| e.relation_kind == "supersedes");
    let has_causal = edges.iter().any(|e| e.relation_kind == "causal");
    assert!(has_supersedes, "Must link Breakthrough -> Problem via supersedes");
    assert!(has_causal, "Must link Directive -> Breakthrough via causal");

    // Verify persistence into SQLite
    let dir = tempdir().expect("temp dir");
    let mut conn = open_vault_db(dir.path().join("graph_test.db")).expect("open db");
    conn.execute(
        "INSERT INTO vault_sessions (session_id, title, project_id, time_created, time_updated, total_messages, total_turns) VALUES ('s2', 'Mesh Session', 'p2', 1000, 2000, 3, 3)",
        [],
    ).unwrap();
    CausalGraphBuilder::persist_graph(&mut conn, &nodes, &edges).expect("persist graph");

    let node_count: i64 = conn.query_row("SELECT count(*) FROM vault_nodes", [], |r| r.get(0)).unwrap();
    assert_eq!(node_count as usize, nodes.len());
}

#[test]
fn test_hybrid_retrieval_and_rrf() {
    let dir = tempdir().expect("temp dir");
    let db_path = dir.path().join("retrieval_test.db");
    let conn = open_vault_db(&db_path).expect("open db");

    conn.execute(
        "INSERT INTO vault_sessions (session_id, title, project_id, time_created, time_updated, total_messages, total_turns) VALUES ('s1', 'Landlock Session', 'p1', 1000, 2000, 3, 3)",
        [],
    ).unwrap();

    // Insert chunks into database and FTS5
    conn.execute(
        r#"
        INSERT INTO vault_chunks (chunk_id, session_id, tier, start_seq, end_seq, token_count, content_hash, chunk_text, time_created)
        VALUES ('c_landlock', 's1', 1, 0, 1, 50, 'hash1', 'Gate 13 Landlock LSM process containment kernel isolation for all subagents', 1000)
        "#,
        [],
    ).unwrap();
    conn.execute(
        r#"
        INSERT INTO vault_fts (chunk_id, session_id, tier, chunk_text)
        VALUES ('c_landlock', 's1', 1, 'Gate 13 Landlock LSM process containment kernel isolation for all subagents')
        "#,
        [],
    ).unwrap();

    conn.execute(
        r#"
        INSERT INTO vault_chunks (chunk_id, session_id, tier, start_seq, end_seq, token_count, content_hash, chunk_text, time_created)
        VALUES ('c_shm', 's1', 1, 2, 3, 50, 'hash2', 'Zero-copy Linda tuple space over POSIX shared memory substrate /dev/shm 340,000x speedup', 1050)
        "#,
        [],
    ).unwrap();
    conn.execute(
        r#"
        INSERT INTO vault_fts (chunk_id, session_id, tier, chunk_text)
        VALUES ('c_shm', 's1', 1, 'Zero-copy Linda tuple space over POSIX shared memory substrate /dev/shm 340,000x speedup')
        "#,
        [],
    ).unwrap();

    // Insert corresponding graph directive
    conn.execute(
        r#"
        INSERT INTO vault_nodes (node_id, node_type, label, summary, session_id, chunk_id, time_created, metadata)
        VALUES ('dir_01', 'directive', 'DIR-02: Mandala Landlock LSM', 'Enforce kernel containment', 's1', 'c_landlock', 1000, null)
        "#,
        [],
    ).unwrap();

    let model_dir = System05::resolve_model_dir(None).expect("resolve model dir");
    let organ = Arc::new(System05::new(&model_dir));

    let engine = TacitVaultEngine::new(organ, conn, None, Vec::new()).expect("create engine");

    let results = engine.recall_associative("Landlock kernel isolation", 5).expect("recall");
    assert!(!results.is_empty(), "Should recall matching chunk");
    assert_eq!(results[0].chunk_id, "c_landlock");
    assert!(results[0].text.contains("Landlock LSM"));
    assert!(results[0].linked_directives.contains(&"DIR-02: Mandala Landlock LSM".to_string()));
}

#[test]
fn test_shm_bridge_roundtrip() {
    let test_shm_name = format!("/wm_test_vault_bridge_{}", &Uuid::new_v4().to_string()[..8]);
    let substrate = Arc::new(ShmSubstrate::open_or_create(&test_shm_name).expect("open shm"));
    let tuple_space = ShmTupleSpace::new(substrate.clone());

    let dir = tempdir().expect("temp dir");
    let db_path = dir.path().join("bridge_test.db");
    let conn = open_vault_db(&db_path).expect("open db");

    let model_dir = System05::resolve_model_dir(None).expect("resolve model dir");
    let organ = Arc::new(System05::new(&model_dir));
    let engine = Arc::new(TacitVaultEngine::new(organ, conn, None, Vec::new()).expect("engine"));

    let bridge = VaultShmBridge::new(tuple_space.clone(), engine);

    // Deposit request tuple from client
    let req = VaultShmRequest {
        req_id: "req_test_123".to_string(),
        query: "kernel sandboxing".to_string(),
        k: 3,
    };
    let req_bytes = serde_json::to_vec(&req).unwrap();

    let client_req_tuple = RawTuple {
        id: Uuid::new_v4(),
        kind_discriminator: VAULT_REQUEST_KIND,
        resource_hash: 12345,
        holder_issuer_hash: 0,
        resource_path: "req_test_123".to_string(),
        tag: "vault_request".to_string(),
        payload: req_bytes,
        created_at_ms: 1000,
        expires_at_ms: 0,
        landlock_token: [0u8; 32],
        capability_mask: 0xFFFF,
    };

    tuple_space.out(&client_req_tuple).expect("out request");

    // Server process request
    let processed = bridge.process_one_request().expect("process");
    assert!(processed, "Must successfully take and process request");

    // Read response tuple from server
    let now_ms = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);

    let resp_tuple = tuple_space.in_matching(Some(VAULT_RESPONSE_KIND), None, now_ms)
        .expect("should find response tuple");
    assert_eq!(resp_tuple.resource_path, "req_test_123");

    let resp: VaultShmResponse = serde_json::from_slice(&resp_tuple.payload).expect("parse response");
    assert_eq!(resp.req_id, "req_test_123");

    let _ = substrate.clone();
    unsafe {
        let c_name = std::ffi::CString::new(test_shm_name.as_str()).unwrap();
        libc::shm_unlink(c_name.as_ptr());
    }
}
