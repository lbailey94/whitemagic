use std::path::PathBuf;
use std::time::Instant;
use wm_gen3_vault::daemon::VaultDaemon;
use wm_gen3_vault::embedder::VaultEmbedder;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("═══════════════════════════════════════════════════════════════");
    println!("  WhiteMagic Gen3 — Tacit Continuity Vault Miner (DIR-08)");
    println!("═══════════════════════════════════════════════════════════════");

    let opencode_path = PathBuf::from("/home/lucas/.local/share/opencode/opencode.db");
    let vault_dir = PathBuf::from("/home/lucas/.local/share/whitemagic/vault");

    if !opencode_path.exists() {
        eprintln!(
            "Error: opencode.db not found at {}",
            opencode_path.display()
        );
        std::process::exit(1);
    }

    std::fs::create_dir_all(&vault_dir)?;

    // Try loading Model2Vec embedder (optional for basic indexing)
    let embedder = match VaultEmbedder::new(None) {
        Ok(emb) => {
            println!(
                "✓ Loaded System 0.5 Model2Vec static embedder ({}, dim={})",
                emb.model_name(),
                emb.dimension()
            );
            Some(emb)
        }
        Err(e) => {
            println!(
                "! Model2Vec embedder not resident ({e}); continuing with FTS5 lexical & graph indexing"
            );
            None
        }
    };

    let daemon = VaultDaemon::new(&opencode_path, &vault_dir, embedder);
    let state_before = daemon.load_state();
    println!(
        "Previous sync state: {} chunks, {} nodes, {} edges indexed",
        state_before.total_chunks_indexed,
        state_before.total_nodes_indexed,
        state_before.total_edges_indexed
    );

    // Parse CLI arguments: e.g. wm_vault_index 100 or --all or --batch 50
    let args: Vec<String> = std::env::args().collect();
    let mut limit = std::env::var("WM_SYNC_LIMIT")
        .ok()
        .and_then(|s| s.parse::<usize>().ok());

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--all" | "-a" => {
                limit = None;
            }
            "--batch" | "-b" | "--limit" | "-n" => {
                if i + 1 < args.len() {
                    limit = args[i + 1].parse::<usize>().ok();
                    i += 1;
                }
            }
            arg if !arg.starts_with('-') => {
                if let Ok(n) = arg.parse::<usize>() {
                    limit = Some(n);
                }
            }
            _ => {}
        }
        i += 1;
    }
    if limit.is_none() && !args.iter().any(|a| a == "--all" || a == "-a") {
        limit = Some(100);
    }

    println!(
        "Starting non-blocking WAL streaming extraction (session batch: {:?})...",
        limit
    );
    let t0 = Instant::now();

    let new_state = daemon
        .run_sync_pass(limit)
        .map_err(|e| format!("Sync pass failed: {e}"))?;

    let elapsed = t0.elapsed();
    println!(
        "\n✓ Indexing pass complete in {:.2}s!",
        elapsed.as_secs_f64()
    );
    println!(
        "  Total chunks in vault: {}",
        new_state.total_chunks_indexed
    );
    println!("  Total graph nodes:     {}", new_state.total_nodes_indexed);
    println!("  Total causal edges:    {}", new_state.total_edges_indexed);
    println!(
        "  Vault DB location:     {}",
        vault_dir.join("tacit_vault.db").display()
    );
    println!("═══════════════════════════════════════════════════════════════\n");

    Ok(())
}
