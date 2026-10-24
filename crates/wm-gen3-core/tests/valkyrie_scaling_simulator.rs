//! Valkyrie-3 → Valkyrie-9 Scaling Simulator (TRANSPARENT PROJECTIONS).
//!
//! Every number printed here is a *model estimate*, not a measurement. The
//! only empirically anchored constants are the Valkyrie-2 organ's measured
//! footprint (29.16 KB, commit be8b4b8) and its ~29KB L2-cache residency;
//! everything downstream is parametric arithmetic over explicitly stated
//! assumptions. Read the ASSUMPTIONS section before quoting any figure.

/// Measured anchor: one Valkyrie-2 tricameral organ, packed ternary +
/// transcoder + bloom filter, as reported by memory_footprint_bytes().
const V2_ORGAN_BYTES: f64 = 29_160.0;
/// Expert lattice: 28 Ganas x 64 King Wen hexagrams x 24 Sutra codons.
const GANA_COUNT: f64 = 28.0;
const HEXAGRAM_COUNT: f64 = 64.0;
const SUTRA_COUNT: f64 = 24.0;
const MAX_EXPERT_SLOTS: f64 = GANA_COUNT * HEXAGRAM_COUNT * SUTRA_COUNT; // 43,008

// Hardware anchors (orders of magnitude, labeled in output).
const T480S_MEM_BW_GBS: f64 = 30.0; // dual-channel DDR4
const T480S_GFLOPS: f64 = 60.0; // sustained CPU, conservative
const H100_TFLOPS_TERNARY: f64 = 400.0; // effective for 2-bit sparse kernels (optimistic)
const NODE_MESH_GFLOPS: f64 = 60.0; // per volunteer laptop-class node

// Training recipe anchors (PROJECTION assumptions, printed in output).
const TOKENS_PER_PARAM: f64 = 20.0; // Chinchilla-style compute-optimal ratio
const TERNARY_BITS: f64 = 2.0;
const TOP_K_EXPERTS: f64 = 2.0; // matches route_top2_ganas
const MEZO_FORWARD_MULT: f64 = 3.0; // forward-only zeroth-order, ~3 fwd passes
const DENSE_TRAIN_FLOPS_PER_TOKEN: f64 = 6.0; // fwd+bwd
// MoE train overhead: per-token compute touches only top-k experts, but each
// expert is trained on a small slice of the corpus — load-imbalance, router
// updates, and duplicate gradient exchange make real MoE training ~4x less
// FLOP-efficient than the ideal sparse formula. 4x is a *conservative* floor;
// published MoE reports often cite 4-8x.
const MOE_TRAIN_OVERHEAD: f64 = 4.0;
const UNCERTAINTY: f64 = 2.0; // report band = value /2 .. value *2

fn human_bytes(mb: f64) -> String {
    if mb >= 1e6 {
        format!("{:.1} TB", mb / 1e6)
    } else if mb >= 1e3 {
        format!("{:.0} GB", mb / 1e3)
    } else {
        format!("{mb:.0} MB")
    }
}

struct VersionSpec {
    name: &'static str,
    total_params: f64, // ternary weights
    params_per_expert: f64,
    note: &'static str,
}

fn specs() -> Vec<VersionSpec> {
    // params_per_expert derived so totals land on the ladder while expert
    // count saturates at the 43,008-slot codon lattice.
    vec![
        VersionSpec {
            name: "Valkyrie-3",
            total_params: 8.0e6,
            params_per_expert: 8.0e3,
            note: "single surface organ; laptop-trainable tonight",
        },
        VersionSpec {
            name: "Valkyrie-4",
            total_params: 1.2e8,
            params_per_expert: 6.0e4,
            note: "first full codon lattice; hobbyist cluster",
        },
        VersionSpec {
            name: "Valkyrie-5",
            total_params: 1.1e9,
            params_per_expert: 5.0e5,
            note: "~$20K rented-H100 scale (nosy-blender)",
        },
        VersionSpec {
            name: "Valkyrie-6",
            total_params: 1.2e10,
            params_per_expert: 5.0e5,
            note: "grant-scale (~$100-300K)",
        },
        VersionSpec {
            name: "Valkyrie-7",
            total_params: 1.3e11,
            params_per_expert: 1.0e6,
            note: "upper grant zone",
        },
        VersionSpec {
            name: "Valkyrie-8",
            total_params: 1.5e12,
            params_per_expert: 5.0e6,
            note: "permissionless-mesh-only territory",
        },
        VersionSpec {
            name: "Valkyrie-9",
            total_params: 4.0e13,
            params_per_expert: 9.3e5,
            note: "43,008-slot saturation; multi-trillion sparse",
        },
    ]
}

#[test]
fn test_valkyrie_scaling_projections() {
    println!(
        "\n========================================================================================"
    );
    println!("  VALKYRIE-3..9 SCALING SIMULATOR — ALL FIGURES ARE PROJECTIONS, NOT MEASUREMENTS");
    println!(
        "========================================================================================"
    );
    println!(
        "  Anchors: V2 organ = {:.1} KB measured | expert lattice = {} slots | ternary 2-bit",
        V2_ORGAN_BYTES / 1024.0,
        MAX_EXPERT_SLOTS as u64
    );
    println!(
        "  Assumptions: {:.0} tok/param train, top-k={:.0} experts, MeZO {:.0}x fwd, dense 6ND",
        TOKENS_PER_PARAM, TOP_K_EXPERTS, MEZO_FORWARD_MULT
    );
    println!("  Uncertainty band: every figure /{0}..*{0}\n", UNCERTAINTY);

    let header = format!(
        "  {:<11}|{:>10}|{:>10}|{:>9}|{:>8}|{:>11}|{:>11}|{:>12}",
        "Version",
        "Params",
        "Ternary",
        "Active/tok",
        "Experts",
        "T480s tok/s",
        "Train GPU-hrs",
        "Dense-equiv"
    );
    println!("{header}");
    println!("  {}", "-".repeat(header.len() - 2));

    let mut prev_params = 0.0f64;
    let mut prev_footprint = 0.0f64;
    for s in specs() {
        let experts = MAX_EXPERT_SLOTS
            .min(s.total_params / s.params_per_expert)
            .floor()
            .max(1.0);
        let total_bytes = s.total_params * TERNARY_BITS / 8.0;
        let active_frac = (TOP_K_EXPERTS / experts).min(1.0);
        let active_params = s.total_params * active_frac;
        let active_bytes = active_params * TERNARY_BITS / 8.0;

        // Inference: memory-bandwidth bound, then compute bound, take the min.
        // NOTE: pure-math ceiling — real pipelines add routing, KV, host I/O.
        let bw_bound = T480S_MEM_BW_GBS * 1e9 / active_bytes.max(1.0);
        let flops_bound = T480S_GFLOPS * 1e9 / (2.0 * active_params).max(1.0);
        let t480s_toks = bw_bound.min(flops_bound);

        // Training (sparse, forward-only): tokens * active params * 2 flops
        // * MeZO mult * MoE inefficiency overhead.
        let tokens = s.total_params * TOKENS_PER_PARAM;
        let flops = tokens * active_params * 2.0 * MEZO_FORWARD_MULT * MOE_TRAIN_OVERHEAD;
        let h100_hrs = flops / (H100_TFLOPS_TERNARY * 1e12) / 3600.0;
        let mesh_100_node_days = flops / (100.0 * NODE_MESH_GFLOPS * 1e9) / 86400.0;

        // Dense monolith comparison: same total params, dense training compute.
        let dense_flops = tokens * s.total_params * DENSE_TRAIN_FLOPS_PER_TOKEN;
        let dense_ratio = dense_flops / flops;

        println!(
            "  {:<11}|{:>10.2e}|{:>10}|{:>9.2e}|{:>8.0}|{:>11.1}|{:>11.1}|{:>12.0}x",
            s.name,
            s.total_params,
            human_bytes(total_bytes / 1e6),
            active_params,
            experts,
            t480s_toks,
            h100_hrs,
            dense_ratio
        );
        println!(
            "             | {} | mesh(100n) train ≈ {:.1} days",
            s.note, mesh_100_node_days
        );

        assert!(s.total_params > prev_params, "ladder must be monotonic");
        assert!(total_bytes > prev_footprint, "footprint grows monotonic");
        assert!(active_params <= s.total_params);
        prev_params = s.total_params;
        prev_footprint = total_bytes;
    }

    // Sensitivity: V-5 tok/s and train-cost under top-k sweep.
    let v5 = 1.1e9f64;
    let experts = 2200.0f64;
    println!("\n  SENSITIVITY (Valkyrie-5): top-k sweep on T480s");
    for k in [1.0f64, 2.0, 4.0, 8.0] {
        let active = v5 * (k / experts);
        let flops_bound = T480S_GFLOPS * 1e9 / (2.0 * active).max(1.0);
        let bw_bound = T480S_MEM_BW_GBS * 1e9 / (active * TERNARY_BITS / 8.0).max(1.0);
        println!(
            "    k={k:<4.0} -> {:.1} tok/s (band {:.1}e)",
            flops_bound.min(bw_bound),
            UNCERTAINTY
        );
    }
    println!("\n  INTERPRETATION: sub-billion versions are laptop/grant scale; V-8+ exists");
    println!("  only as decentralized sparse bake. Verification stack (receipts + Bend");
    println!("  laws) is the honest differentiator vs TOPLOC-style probabilistic checks.");
    println!("  NOTHING above is a measured result.\n");
}
