//! Pure Rust embedding binary - F001 Standalone
//! Processes memories directly from SQLite, no Python needed

use rusqlite::{Connection, params};
use serde_json;
use std::time::Instant;

#[cfg(all(not(target_arch = "wasm32"), feature = "arrow", feature = "ort"))]
fn main() {
    use whitemagic_rs::onnx_embedder::{ONNXEmbedder, ONNXEmbedderConfig};
    use arrow::array::StringBuilder;
    
    let db_path = dirs::home_dir()
        .map(|h| h.join(".whitemagic/memory/whitemagic.db"))
        .expect("Home dir not found");
    
    println!("F001 Standalone Rust Embedder");
    println!("DB: {:?}", db_path);
    
    // Connect to DB
    let conn = Connection::open(&db_path).expect("Failed to open DB");
    
    // Count work
    let already_embedded: i64 = conn
        .query_row("SELECT COUNT(*) FROM memory_embeddings", [], |r| r.get(0))
        .unwrap_or(0);
    
    let total_active: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM memories WHERE memory_type NOT IN ('archived_orphan', 'quarantined', 'scavenged')",
            [],
            |r| r.get(0)
        )
        .unwrap_or(0);
    
    let remaining = total_active - already_embedded;
    println!("Active: {} | Embedded: {} | Remaining: {}", total_active, already_embedded, remaining);
    
    if remaining == 0 {
        println!("All memories already embedded!");
        return;
    }
    
    // Create embedder
    let config = ONNXEmbedderConfig {
        model_path: "models/bge-small-en-v1.5.onnx".to_string(),
        use_gpu: false,
        intra_threads: 8,
        batch_size: 32,
    };
    
    let embedder = ONNXEmbedder::new(config).expect("Failed to create embedder");
    println!("ONNX Embedder ready (batch_size=32)");
    
    // Process in batches
    let batch_size = 32;
    let mut offset = 0;
    let mut total_embedded = 0;
    let start = Instant::now();
    
    loop {
        // Fetch batch
        let mut stmt = conn.prepare(
            "SELECT m.id, m.content FROM memories m
             LEFT JOIN memory_embeddings e ON m.id = e.memory_id
             WHERE m.memory_type NOT IN ('archived_orphan', 'quarantined', 'scavenged')
               AND e.memory_id IS NULL
             ORDER BY m.id LIMIT ? OFFSET ?"
        ).unwrap();
        
        let batch: Vec<(String, String)> = stmt
            .query_map(params![batch_size, offset], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
            })
            .unwrap()
            .filter_map(|r| r.ok())
            .collect();
        
        if batch.is_empty() {
            break;
        }
        
        let batch_start = Instant::now();
        let ids: Vec<String> = batch.iter().map(|(id, _)| id.clone()).collect();
        let texts: Vec<&str> = batch.iter().map(|(_, text)| text.as_str()).collect();
        
        // Build Arrow StringArray
        let mut builder = StringBuilder::new();
        for text in &texts {
            builder.append_value(*text);
        }
        let text_array = builder.finish();
        
        // Embed
        let result = embedder.encode_batch_arrow(&text_array).expect("Embedding failed");
        let embeddings: Vec<Vec<f32>> = result
            .column(0)
            .as_any()
            .downcast_ref::<arrow::array::ListArray>()
            .unwrap()
            .iter()
            .filter_map(|opt: Option<arrow::array::ArrayRef>| {
                opt.map(|list: arrow::array::ArrayRef| {
                    list.as_any()
                        .downcast_ref::<arrow::array::Float32Array>()
                        .unwrap()
                        .iter()
                        .filter_map(|v: Option<f32>| v)
                        .collect()
                })
            })
            .collect();
        
        // Write to DB
        let tx = conn.unchecked_transaction().expect("Transaction failed");
        for (id, emb) in ids.iter().zip(embeddings.iter()) {
            let emb_json = serde_json::to_string(emb).unwrap();
            tx.execute(
                "INSERT OR REPLACE INTO memory_embeddings (memory_id, embedding, model) VALUES (?1, ?2, ?3)",
                params![id, emb_json, "models/bge-small-en-v1.5.onnx"],
            ).unwrap();
        }
        tx.commit().unwrap();
        
        let batch_time = batch_start.elapsed().as_secs_f64();
        total_embedded += batch.len();
        let elapsed = start.elapsed().as_secs_f64();
        let rate = total_embedded as f64 / elapsed;
        
        println!(
            "  Batch: {}-{} | {}/{} ({:.2}%) | {:.1}/s | {:.2}s/batch",
            offset + 1,
            offset + batch.len(),
            total_embedded,
            remaining,
            total_embedded as f64 / remaining as f64 * 100.0,
            rate,
            batch_time
        );
        
        offset += batch.len();
        
        // Early exit for testing
        if offset >= 160 {
            println!("\n  Stopped after 160 for testing");
            break;
        }
    }
    
    let elapsed = start.elapsed().as_secs_f64();
    println!("\n  Embedded: {} texts in {:.1}s ({:.1}/s)", total_embedded, elapsed, total_embedded as f64 / elapsed);
}

#[cfg(not(all(feature = "arrow", feature = "ort")))]
fn main() {
    eprintln!("This binary requires 'arrow' and 'ort' features");
    eprintln!("Rebuild with: --features arrow,ort");
    std::process::exit(1);
}
