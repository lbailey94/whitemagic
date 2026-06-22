//! H003: Rust ONNX Embedder — Full Implementation
//! High-performance embedding via ONNX Runtime with Arrow IPC I/O
//! 
//! Expected speedup: 2-3x over Python V17 baseline (1,216/sec → 2,500-3,500/sec)
//! Target: 2,500-3,500 embeddings/sec on CPU
//!
//! Usage:
//!   cat input.arrow | h003-onnx-embedder > output.arrow 2>stats.log
//!
//! Input: Arrow IPC stream with StringArray column "text"
//! Output: Arrow IPC stream with List<Float32> column "embedding" (384-dim)

use std::io::{self, Read, Write};
use std::time::Instant;

// Import from the whitemagic crate
use whitemagic_rs::onnx_embedder::{ONNXEmbedder, ONNXEmbedderConfig};
use whitemagic_rs::arrow_bridge::{ipc_bytes_to_arrow, arrow_to_ipc_bytes};
use arrow::array::{Array, StringArray};

fn main() {
    let start = Instant::now();
    
    // Read Arrow IPC from stdin
    let mut input = Vec::new();
    if let Err(e) = io::stdin().read_to_end(&mut input) {
        eprintln!("H003 Error: Failed to read stdin: {}", e);
        std::process::exit(1);
    }
    
    let read_time = start.elapsed();
    
    // Parse Arrow IPC input
    let input_batch = match ipc_bytes_to_arrow(&input) {
        Ok(batch) => batch,
        Err(e) => {
            eprintln!("H003 Error: Failed to parse Arrow IPC: {}", e);
            std::process::exit(1);
        }
    };
    
    let parse_time = start.elapsed() - read_time;
    
    // Extract text column
    let texts = match input_batch.column(0).as_any().downcast_ref::<StringArray>() {
        Some(arr) => arr,
        None => {
            eprintln!("H003 Error: Expected StringArray as first column");
            std::process::exit(1);
        }
    };
    
    let batch_size = texts.len();
    
    // Initialize ONNX embedder
    let config = ONNXEmbedderConfig {
        model_path: std::env::var("H003_MODEL_PATH")
            .unwrap_or_else(|_| "models/bge-small-en-v1.5.onnx".to_string()),
        use_gpu: std::env::var("H003_USE_GPU")
            .map(|v| v == "1" || v == "true")
            .unwrap_or(false),
        intra_threads: std::env::var("H003_THREADS")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(8),
        batch_size: std::env::var("H003_BATCH_SIZE")
            .ok()
            .and_then(|v| v.parse().ok())
            .unwrap_or(256),
    };
    
    let embedder = match ONNXEmbedder::new(config) {
        Ok(e) => e,
        Err(e) => {
            eprintln!("H003 Error: Failed to load ONNX model: {}", e);
            std::process::exit(1);
        }
    };
    
    let init_time = start.elapsed() - read_time - parse_time;
    
    // Run ONNX inference
    let output_batch = match embedder.encode_batch_arrow(texts) {
        Ok(batch) => batch,
        Err(e) => {
            eprintln!("H003 Error: Inference failed: {}", e);
            std::process::exit(1);
        }
    };
    
    let inference_time = start.elapsed() - read_time - parse_time - init_time;
    
    // Serialize output as Arrow IPC
    let output_ipc = match arrow_to_ipc_bytes(&output_batch) {
        Ok(bytes) => bytes,
        Err(e) => {
            eprintln!("H003 Error: Failed to serialize output: {}", e);
            std::process::exit(1);
        }
    };
    
    let serialize_time = start.elapsed() - read_time - parse_time - init_time - inference_time;
    
    // Write output to stdout
    if let Err(e) = io::stdout().write_all(&output_ipc) {
        eprintln!("H003 Error: Failed to write stdout: {}", e);
        std::process::exit(1);
    }
    
    let total_time = start.elapsed();
    let throughput = if total_time.as_secs_f64() > 0.0 {
        batch_size as f64 / total_time.as_secs_f64()
    } else {
        0.0
    };
    
    // Stats to stderr
    eprintln!("H003 ONNX Embedder Complete:");
    eprintln!("  Batch size: {}", batch_size);
    eprintln!("  Read:       {:?}", read_time);
    eprintln!("  Parse:      {:?}", parse_time);
    eprintln!("  Init:       {:?}", init_time);
    eprintln!("  Inference:  {:?}", inference_time);
    eprintln!("  Serialize:  {:?}", serialize_time);
    eprintln!("  Total:      {:?}", total_time);
    eprintln!("  Throughput: {:.1} embeddings/sec", throughput);
    eprintln!("  Status:     SUCCESS");
}
