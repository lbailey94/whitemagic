//! Sutra Canon 12-Glyph Model2Vec Calibration Fixture
//!
//! Calibrates the 12 canonical logoglyphs using Model2Vec System 0.5 (potion-base-32M).
//! Pre-computes normalized 512-dim vectors and exports:
//! - catalogs/sutra_vectors.bin (zero-copy mmap binary)
//! - catalogs/sutra_canon.json (structured metadata)

use serde::{Deserialize, Serialize};
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;
use wm_gen3_zeropointfive::System05;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KekkaiSpec {
    pub ro_paths: Vec<String>,
    pub rw_paths: Vec<String>,
    pub network_allowed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SutraGlyphMeta {
    pub index: usize,
    pub glyph: String,
    pub name: String,
    pub english: String,
    pub semantic_intent: String,
    pub skeleton_id: String,
    pub kekkai: KekkaiSpec,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub vector: Option<Vec<f32>>,
}

type CanonicalGlyph = (
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static [&'static str],
    &'static [&'static str],
    bool,
);

const CANONICAL_GLYPHS: &[CanonicalGlyph] = &[
    // 0: 證
    (
        "證",
        "Zhèng",
        "Verify / Proof",
        "Verify invariants, run tests, audit evidence, prove correctness",
        "skel-verify-commit",
        &["."],
        &["target/"],
        false,
    ),
    // 1: 行
    (
        "行",
        "Xíng",
        "Execute / Dispatch",
        "Execute mutations, commit changes, seal receipts, dispatch actions",
        "skel-verify-commit-vanguard",
        &["."],
        &[".git/", "receipts/"],
        false,
    ),
    // 2: 觀
    (
        "觀",
        "Guān",
        "Survey / Inspect",
        "Survey substrate, view telemetry, inspect state, fast lookup",
        "skel-fast-lookup",
        &["."],
        &[],
        false,
    ),
    // 3: 合
    (
        "合",
        "Hé",
        "Synthesize / Unify",
        "Synthesize disparate threads, combine concepts, unify systems into one",
        "skel-dream-dream-6cfcfda755",
        &["."],
        &["SharedWorkspace/"],
        true,
    ),
    // 4: 遠
    (
        "遠",
        "Yuǎn",
        "Horizon / Project",
        "Project downstream order effects, thirty year horizon, deliberate strategy",
        "skel-deliberate-horizon",
        &["."],
        &["scratch/"],
        true,
    ),
    // 5: 鏡
    (
        "鏡",
        "Jìng",
        "Mirror / Analogy",
        "Mirror across domains, draw biological and physical analogies, comparative analysis",
        "skel-dream-dream-bd11ebbb83",
        &["."],
        &["logs/"],
        false,
    ),
    // 6: 息
    (
        "息",
        "Xī",
        "Quiesce / Sleep",
        "Quiesce execution, enter deep sleep, incubate associative dreams",
        "skel-dream-dream-658170e0ff",
        &["."],
        &["dream.jsonl"],
        false,
    ),
    // 7: 清
    (
        "清",
        "Qīng",
        "Clean / Prune",
        "Clean working tree, prune dead branches, compact Pareto vault",
        "skel-edit-lint-check-opt",
        &["."],
        &["."],
        false,
    ),
    // 8: 應
    (
        "應",
        "Yìng",
        "Resonate / Wire",
        "Gan Ying resonance, wire protocol handshake, fleet synchronization, p2p mesh",
        "skel-ganying-handshake",
        &["."],
        &["/dev/shm"],
        true,
    ),
    // 9: 界
    (
        "界",
        "Jiè",
        "Kekkai / Sandbox",
        "Erect Landlock confinement, enforce spatial capability boundary, secure sandbox",
        "skel-landlock-jail",
        &["/"],
        &["sandbox/"],
        false,
    ),
    // 10: 根
    (
        "根",
        "Gēn",
        "Origin / Root",
        "Primordial invariants, trace Tacit lineage, ancestral roots, archaeology archive",
        "skel-archaeology-tacit",
        &["."],
        &[],
        false,
    ),
    // 11: 生
    (
        "生",
        "Shēng",
        "Evolve / Speciate",
        "Speciate new variants, genetic mutation, evolutionary promotion, germline action",
        "skel-edit-lint-check-vanguard",
        &["."],
        &["vault.jsonl"],
        false,
    ),
];

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

fn compound_vector(vectors: &[&[f32]]) -> Vec<f32> {
    assert!(!vectors.is_empty());
    let dim = vectors[0].len();
    let mut sum = vec![0.0f32; dim];
    for v in vectors {
        for (i, val) in v.iter().enumerate() {
            sum[i] += val;
        }
    }
    let norm = sum.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for val in &mut sum {
            *val /= norm;
        }
    }
    sum
}

#[test]
fn test_calibrate_and_export_sutra_canon() {
    let model_dir = System05::resolve_model_dir(None)
        .expect("potion-base-32M static model directory must resolve");
    println!("Loading System 0.5 model from: {}", model_dir.display());

    let organ = System05::new(model_dir);
    organ.ensure_loaded().expect("model must load");

    let mut glyphs_meta: Vec<SutraGlyphMeta> = Vec::new();
    let mut calibrated_vectors: Vec<Vec<f32>> = Vec::new();

    println!("\n=== Calibrating 12 Canonical Sutra Glyphs (512-dim) ===");
    for (i, &(glyph, name, english, semantic, skeleton, ro, rw, net)) in
        CANONICAL_GLYPHS.iter().enumerate()
    {
        // Embed the rich semantic intent into unit-norm 512-dim vector
        let vector = organ
            .encode_single(semantic)
            .expect("encoding must succeed");
        assert_eq!(vector.len(), 512, "embedding vector dimension must be 512");

        let norm: f32 = vector.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!(
            (norm - 1.0).abs() < 1e-4,
            "vector must be normalized to unit length"
        );

        println!(
            "[{:>2}] {} ({:<5}) | {:<18} -> 512-dim norm={:.4} | skeleton: {}",
            i, glyph, name, english, norm, skeleton
        );

        calibrated_vectors.push(vector.clone());
        glyphs_meta.push(SutraGlyphMeta {
            index: i,
            glyph: glyph.to_string(),
            name: name.to_string(),
            english: english.to_string(),
            semantic_intent: semantic.to_string(),
            skeleton_id: skeleton.to_string(),
            kekkai: KekkaiSpec {
                ro_paths: ro.iter().map(|s| s.to_string()).collect(),
                rw_paths: rw.iter().map(|s| s.to_string()).collect(),
                network_allowed: net,
            },
            vector: Some(vector),
        });
    }

    // Verify self-similarity and mutual distinction
    println!("\n=== Pairwise Cosine Similarity Matrix (Upper Triangle) ===");
    for i in 0..CANONICAL_GLYPHS.len() {
        for j in (i + 1)..CANONICAL_GLYPHS.len() {
            let sim = cosine_similarity(&calibrated_vectors[i], &calibrated_vectors[j]);
            if sim > 0.70 {
                println!(
                    "  NOTE: Higher similarity between [{}] {} and [{}] {}: {:.4}",
                    i, CANONICAL_GLYPHS[i].0, j, CANONICAL_GLYPHS[j].0, sim
                );
            }
        }
    }

    // Test Canonical Triplet Codons
    println!("\n=== Testing Compound Triplet Codons ===");
    // 1. ⟪ 證 · 行 · 鏡 ⟫ — The Shipwright’s Codon
    let v_shipwright = compound_vector(&[
        &calibrated_vectors[0],
        &calibrated_vectors[1],
        &calibrated_vectors[5],
    ]);
    let sim_zheng = cosine_similarity(&v_shipwright, &calibrated_vectors[0]);
    let sim_xing = cosine_similarity(&v_shipwright, &calibrated_vectors[1]);
    let sim_jing = cosine_similarity(&v_shipwright, &calibrated_vectors[5]);
    println!(
        "⟪ 證 · 行 · 鏡 ⟫ Shipwright Codon: sim(證)={:.4}, sim(行)={:.4}, sim(鏡)={:.4}",
        sim_zheng, sim_xing, sim_jing
    );
    assert!(sim_zheng > 0.4 && sim_xing > 0.4 && sim_jing > 0.4);

    // 2. ⟪ 觀 · 合 · 遠 ⟫ — The Architect’s Codon
    let v_architect = compound_vector(&[
        &calibrated_vectors[2],
        &calibrated_vectors[3],
        &calibrated_vectors[4],
    ]);
    let sim_guan = cosine_similarity(&v_architect, &calibrated_vectors[2]);
    let sim_he = cosine_similarity(&v_architect, &calibrated_vectors[3]);
    let sim_yuan = cosine_similarity(&v_architect, &calibrated_vectors[4]);
    println!(
        "⟪ 觀 · 合 · 遠 ⟫ Architect Codon:  sim(觀)={:.4}, sim(合)={:.4}, sim(遠)={:.4}",
        sim_guan, sim_he, sim_yuan
    );
    assert!(sim_guan > 0.4 && sim_he > 0.4 && sim_yuan > 0.4);

    // 3. ⟪ 息 · 清 · 生 ⟫ — The Dreamer’s Codon
    let v_dreamer = compound_vector(&[
        &calibrated_vectors[6],
        &calibrated_vectors[7],
        &calibrated_vectors[11],
    ]);
    let sim_xi = cosine_similarity(&v_dreamer, &calibrated_vectors[6]);
    let sim_qing = cosine_similarity(&v_dreamer, &calibrated_vectors[7]);
    let sim_sheng = cosine_similarity(&v_dreamer, &calibrated_vectors[11]);
    println!(
        "⟪ 息 · 清 · 生 ⟫ Dreamer Codon:    sim(息)={:.4}, sim(清)={:.4}, sim(生)={:.4}",
        sim_xi, sim_qing, sim_sheng
    );
    assert!(sim_xi > 0.4 && sim_qing > 0.4 && sim_sheng > 0.4);

    // 4. ⟪ 界 · 應 · 根 ⟫ — The Sovereign’s Codon
    let v_sovereign = compound_vector(&[
        &calibrated_vectors[9],
        &calibrated_vectors[8],
        &calibrated_vectors[10],
    ]);
    let sim_jie = cosine_similarity(&v_sovereign, &calibrated_vectors[9]);
    let sim_ying = cosine_similarity(&v_sovereign, &calibrated_vectors[8]);
    let sim_gen = cosine_similarity(&v_sovereign, &calibrated_vectors[10]);
    println!(
        "⟪ 界 · 應 · 根 ⟫ Sovereign Codon:  sim(界)={:.4}, sim(應)={:.4}, sim(根)={:.4}",
        sim_jie, sim_ying, sim_gen
    );
    assert!(sim_jie > 0.4 && sim_ying > 0.4 && sim_gen > 0.4);

    // Export catalogs
    let workspace_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .to_path_buf();
    let catalogs_dir = workspace_root.join("catalogs");
    std::fs::create_dir_all(&catalogs_dir).unwrap();

    // Export JSON
    let json_path = catalogs_dir.join("sutra_canon.json");
    let json_str = serde_json::to_string_pretty(&glyphs_meta).unwrap();
    std::fs::write(&json_path, json_str).unwrap();
    println!(
        "\nWrote sutra canon JSON: {} ({} bytes)",
        json_path.display(),
        std::fs::metadata(&json_path).unwrap().len()
    );

    // Export Binary: Magic (8 bytes) + Count (u32 LE) + Dim (u32 LE) + Vectors (12 * 512 * 4 bytes)
    let bin_path = catalogs_dir.join("sutra_vectors.bin");
    let mut file = File::create(&bin_path).unwrap();
    file.write_all(b"SUTR0001").unwrap();
    file.write_all(&(calibrated_vectors.len() as u32).to_le_bytes())
        .unwrap();
    file.write_all(&(512u32).to_le_bytes()).unwrap();
    for vec in &calibrated_vectors {
        for &val in vec {
            file.write_all(&val.to_le_bytes()).unwrap();
        }
    }
    file.flush().unwrap();
    println!(
        "Wrote sutra vectors BIN:  {} ({} bytes)",
        bin_path.display(),
        std::fs::metadata(&bin_path).unwrap().len()
    );
}
