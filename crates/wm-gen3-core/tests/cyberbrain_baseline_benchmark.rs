//! Cyberbrain Baseline Benchmark Suite (Pre-Cyberbrain Micro-Model Upgrades)
//!
//! Evaluates Baseline WhiteMagic Gen3 v10.0-alpha:
//! 1. Memory Ingestion Throughput & Storage Footprint
//! 2. Lexical & Exact Symbol Recall Latency (p50 / p95) and MRR@5
//! 3. Temporal Fact Invalidation & Conflict Resolution
//! 4. Cognitive JEV Routing & Homeostatic Gating Latency

use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use wm_gen3_core::bicameral::JevDecisionTensor;
use wm_gen3_core::constitution::default_view;
use wm_gen3_core::evidence::RatifiedChannel;
use wm_gen3_core::ops::{ImportKind, RecallQuery, RememberItem, Substrate};

struct TempDir(PathBuf);

impl TempDir {
    fn new(label: &str) -> Self {
        let mut nonce = [0u8; 8];
        getrandom::fill(&mut nonce).unwrap();
        let path = std::env::temp_dir().join(format!(
            "wm-gen3-cyberbrain-bench-{label}-{:x}",
            u64::from_be_bytes(nonce)
        ));
        let _ = fs::remove_dir_all(&path);
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn dir_size(path: &Path) -> u64 {
    let mut total = 0;
    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let p = entry.path();
            if p.is_file() {
                if let Ok(meta) = entry.metadata() {
                    total += meta.len();
                }
            } else if p.is_dir() {
                total += dir_size(&p);
            }
        }
    }
    total
}

#[test]
fn test_cyberbrain_baseline_benchmark_suite() {
    let is_debug = cfg!(debug_assertions);
    println!("\n================================================================================");
    println!("  WHITE MAGIC GEN3: CYBERBRAIN BASELINE BENCHMARK SUITE");
    println!("  Evaluating: Ingestion, Lexical/BM25 Recall, Conflict Resolution & JEV Routing");
    println!(
        "  Mode:       {}",
        if is_debug {
            "Debug (Unoptimized)"
        } else {
            "Release (Optimized)"
        }
    );
    println!("================================================================================\n");

    let temp_store = TempDir::new("baseline");
    let mut substrate = Substrate::open(temp_store.path(), None, default_view())
        .expect("Substrate open must succeed");
    substrate.set_budget(1_000_000);
    substrate.set_intake_authority(RatifiedChannel::mint("cyberbrain-bench"));

    // -------------------------------------------------------------------------
    // Phase 1: Ingestion Throughput & Storage Footprint
    // -------------------------------------------------------------------------
    let num_records = if is_debug { 200 } else { 1_000 };
    println!("--- [1] Memory Ingestion & Storage Footprint ---");
    println!("  Ingesting {num_records} heterogeneous episodic records...");

    let start_ingest = Instant::now();
    for i in 0..num_records {
        let content = match i % 5 {
            0 => format!(
                "Error compile failure in crate wm-core: error[E{:04}]: unresolved import symbol `prctl` on darwin host key {}",
                i % 500,
                i
            ),
            1 => format!(
                "Architectural decision #{}: Folded Landlock V5 into Mandala Kekkai barrier. Workspace claim signature: ed25519:{:016x}",
                i,
                i * 314159
            ),
            2 => format!(
                "Routine tool log: cargo check completed with 0 warnings, 310 tests pass, target x86_64-unknown-linux-gnu step {}",
                i
            ),
            3 => format!(
                "System One Laya dispatch #{i}: warm predict 3.59s for decision triage with act_probability 1.0 on seat {}",
                i % 4
            ),
            _ => format!(
                "Session note: Lucas reviewed Agora dispatch #{} regarding three generations comparison and multi-arch targets.",
                i
            ),
        };

        let item = RememberItem {
            content,
            source: format!("session_{:03}", i % 10),
            kind: ImportKind::Reported,
        };
        let res = substrate.remember_batch(&[item]);
        assert!(
            !res.is_empty() && res[0].is_ok(),
            "Ingest must succeed: {:?}",
            res.first()
        );
    }
    let ingest_elapsed = start_ingest.elapsed();
    let ingest_ms_per_item = (ingest_elapsed.as_micros() as f64 / num_records as f64) / 1000.0;
    let ingest_items_per_sec = (num_records as f64 / ingest_elapsed.as_secs_f64()) as u64;
    let total_bytes = dir_size(temp_store.path());

    println!(
        "  Total Ingestion Time: {:.2} ms",
        ingest_elapsed.as_secs_f64() * 1000.0
    );
    println!("  Latency per Record:   {:.3} ms", ingest_ms_per_item);
    println!(
        "  Ingestion Throughput: {} records/sec",
        ingest_items_per_sec
    );
    println!(
        "  LMDB Store Size:      {} bytes ({:.2} KB)",
        total_bytes,
        total_bytes as f64 / 1024.0
    );
    println!(
        "  Bytes per Record:     {:.1} bytes",
        total_bytes as f64 / num_records as f64
    );

    // -------------------------------------------------------------------------
    // Phase 2: Exact Symbol & Lexical Recall Latency & Precision
    // -------------------------------------------------------------------------
    println!("\n--- [2] Memory Recall: Exact Symbol & Lexical BM25 ---");
    let test_queries = [
        ("unresolved import symbol `prctl`", "E0000"),
        ("Landlock V5 Mandala Kekkai", "Architectural"),
        ("System One Laya dispatch warm predict", "Laya"),
        ("Agora dispatch three generations comparison", "generations"),
        ("error[E0123]", "E0123"),
    ];

    let mut latencies_us = Vec::new();
    let mut hits_at_1 = 0;
    let mut hits_at_5 = 0;
    let mut reciprocal_ranks = Vec::new();

    let recall_rounds = if is_debug { 50 } else { 200 };
    for round in 0..recall_rounds {
        let (query_text, target_substr) = &test_queries[round % test_queries.len()];
        let q = RecallQuery {
            query: query_text.to_string(),
            limit: 5,
            ..Default::default()
        };

        let t_query = Instant::now();
        let results = substrate.recall(&q).expect("Recall query must succeed");
        let elapsed_us = t_query.elapsed().as_micros();
        latencies_us.push(elapsed_us);

        let mut hit_rank = None;
        for (rank, res) in results.iter().enumerate() {
            if res.content.contains(target_substr) {
                hit_rank = Some(rank + 1);
                break;
            }
        }

        match hit_rank {
            Some(1) => {
                hits_at_1 += 1;
                hits_at_5 += 1;
                reciprocal_ranks.push(1.0);
            }
            Some(r) => {
                hits_at_5 += 1;
                reciprocal_ranks.push(1.0 / (r as f64));
            }
            None => {
                reciprocal_ranks.push(0.0);
            }
        }
    }

    latencies_us.sort_unstable();
    let p50_us = latencies_us[latencies_us.len() / 2];
    let p95_us = latencies_us[(latencies_us.len() as f64 * 0.95) as usize];
    let mrr_5: f64 = reciprocal_ranks.iter().sum::<f64>() / (recall_rounds as f64);
    let p_at_1 = (hits_at_1 as f64 / recall_rounds as f64) * 100.0;
    let r_at_5 = (hits_at_5 as f64 / recall_rounds as f64) * 100.0;

    println!("  Total Queries Tested: {}", recall_rounds);
    println!(
        "  Recall Latency p50:   {} µs ({:.3} ms)",
        p50_us,
        p50_us as f64 / 1000.0
    );
    println!(
        "  Recall Latency p95:   {} µs ({:.3} ms)",
        p95_us,
        p95_us as f64 / 1000.0
    );
    println!("  Precision@1:          {:.1}%", p_at_1);
    println!("  Recall@5:             {:.1}%", r_at_5);
    println!("  Mean Reciprocal Rank: {:.4}", mrr_5);

    // -------------------------------------------------------------------------
    // Phase 3: Temporal Fact Invalidation & Conflict Resolution
    // -------------------------------------------------------------------------
    println!("\n--- [3] Temporal Fact Invalidation & Conflict Resolution ---");
    // T1: Insert older superseded fact
    let old_fact = RememberItem {
        content: "Configuration fact: Target production gateway IP is 192.168.1.100:8080"
            .to_string(),
        source: "session_infra_old".to_string(),
        kind: ImportKind::Reported,
    };
    let res1 = substrate.remember_batch(&[old_fact]);
    assert!(
        !res1.is_empty() && res1[0].is_ok(),
        "Ingest must succeed: {:?}",
        res1.first()
    );

    // T2: Insert newer corrective fact
    let new_fact = RememberItem {
        content: "SUPERSEDED NOTICE: Target production gateway IP relocated to 10.0.0.250:9090 as verified by Lucas.".to_string(),
        source: "session_infra_new".to_string(),
        kind: ImportKind::Reported,
    };
    let res2 = substrate.remember_batch(&[new_fact]);
    assert!(
        !res2.is_empty() && res2[0].is_ok(),
        "Ingest must succeed: {:?}",
        res2.first()
    );

    let conflict_query = RecallQuery {
        query: "Target production gateway IP".to_string(),
        limit: 2,
        ..Default::default()
    };
    let conflict_results = substrate
        .recall(&conflict_query)
        .expect("Conflict recall must succeed");
    let resolved_first =
        !conflict_results.is_empty() && conflict_results[0].content.contains("10.0.0.250:9090");

    println!(
        "  Temporal Invalidation Result: {}",
        if resolved_first {
            "PASS (Newest ratified fact ranked first)"
        } else {
            "HEURISTIC TIE / INVERSION (Baseline unranked by temporal recency)"
        }
    );

    // -------------------------------------------------------------------------
    // Phase 4: Cognitive JEV Routing & Homeostatic Gating
    // -------------------------------------------------------------------------
    println!("\n--- [4] Cognitive JEV Decision Tensor Latency ---");
    let tensor = JevDecisionTensor::default();
    let jev_rounds = if is_debug { 5_000 } else { 50_000 };
    let start_jev = Instant::now();
    let mut sum = 0.0f64;
    for _i in 0..jev_rounds {
        let u = 0.70;
        let r = 0.15;
        let v = 0.85;
        let c = 0.10;
        sum += tensor.compute_jev(u, r, v, c);
    }
    let jev_elapsed = start_jev.elapsed();
    let jev_ns_per_op = jev_elapsed.as_nanos() as f64 / jev_rounds as f64;
    let jev_ops_per_sec = (jev_rounds as f64 / jev_elapsed.as_secs_f64()) as u64;

    println!("  Iterations:       {}", jev_rounds);
    println!("  Latency per eval: {:.1} ns", jev_ns_per_op);
    println!("  Throughput:       {} evals/sec", jev_ops_per_sec);
    assert!(sum.is_finite());

    println!("\n================================================================================");
    println!("  CYBERBRAIN BASELINE BENCHMARK COMPLETE");
    println!("================================================================================\n");
}
