// Conditional compilation for Python vs WASM
#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

// Conductor module (ResonanceConductor - unified orchestration)
#[cfg(not(feature = "wasm"))]
pub mod conductor;

// Python modules (only compiled for Python target)
#[cfg(feature = "zig")]
pub mod zig_bridge;

// --- Directory modules (reorganized from flat structure) ---
#[cfg(feature = "python")]
pub mod embeddings;
#[cfg(feature = "python")]
pub mod ffi;
#[cfg(feature = "python")]
pub mod graph;
#[cfg(feature = "python")]
pub mod math;
#[cfg(feature = "python")]
pub mod cache;
#[cfg(feature = "python")]
pub mod memory;
#[cfg(feature = "python")]
pub mod pipeline;
#[cfg(feature = "python")]
pub mod safety;
#[cfg(feature = "python")]
pub mod search;

// --- Re-exports for backward compatibility (flat access from crate root) ---
#[cfg(feature = "python")]
pub use ffi::arrow_bridge;
#[cfg(feature = "python")]
pub use graph::association_miner;
#[cfg(feature = "python")]
pub use memory::consolidation;
#[cfg(feature = "python")]
pub use memory::constellations;
#[cfg(feature = "python")]
pub use graph::community_detector;
#[cfg(feature = "python")]
pub use pipeline::continuous_daemon;
#[cfg(feature = "python")]
pub use memory::emergence_detector;
#[cfg(feature = "python")]
pub use memory::galactic_accelerator;
#[cfg(feature = "python")]
pub use memory::galaxy_miner;
#[cfg(feature = "python")]
pub use graph::graph_engine;
#[cfg(feature = "python")]
pub use graph::graph_walker;
#[cfg(feature = "python")]
pub use graph::hnsw_index;
#[cfg(feature = "python")]
pub use math::holographic_encoder_5d;
#[cfg(feature = "python")]
pub use ffi::ipc_bridge;
#[cfg(feature = "python")]
pub use search::keyword_extract;
#[cfg(feature = "python")]
pub use pipeline::massive_deployer;
#[cfg(feature = "python")]
pub use memory::memory_consolidation;
#[cfg(feature = "python")]
pub use math::minhash;
#[cfg(feature = "python")]
pub use ffi::native_ffi;
#[cfg(feature = "python")]
pub use ffi::prat_router_v6;
#[cfg(feature = "python")]
pub use pipeline::reasoning_engine;
#[cfg(feature = "python")]
pub use pipeline::recursive_intelligence;
#[cfg(feature = "python")]
pub use embeddings::simhash_lsh;
#[cfg(feature = "python")]
pub use memory::sqlite_backend;
#[cfg(feature = "python")]
pub use pipeline::synthesis_engine;
#[cfg(feature = "python")]
pub use pipeline::tokio_clones;
#[cfg(feature = "python")]
pub use memory::unified;
#[cfg(feature = "python")]
pub use embeddings::vector_search;

// --- Remaining flat modules ---
#[cfg(feature = "python")]
pub mod hot_paths;
#[cfg(feature = "python")]
pub mod sutra_kernel;
#[cfg(feature = "python")]
pub mod geneseed_miner;

// Inference engine (ternary SIMD, streaming, quantization)
pub mod inference;
#[cfg(feature = "python")]
pub mod inference_pymodule;

// WASM-specific module
#[cfg(feature = "wasm")]
mod wasm;

// Python module
#[cfg(feature = "python")]
#[pymodule]
fn whitemagic_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<embeddings::EmbeddingEngine>()?;
    m.add_class::<memory::consolidation::ConsolidationEngine>()?;
    m.add_class::<graph::association_miner::AssociationMiner>()?;
    m.add_class::<memory::unified::UnifiedMemory>()?;
    m.add_class::<graph::graph_walker::GraphWalker>()?;

    // Additional PSR classes
    m.add_class::<embeddings::vector_search::PyVectorIndex>()?;
    m.add_class::<math::spatial_index_5d::SpatialIndex5D>()?;
    m.add_class::<pipeline::reasoning_engine::PyReasoningEngine>()?;
    m.add_class::<pipeline::reasoning_engine::Fact>()?;
    m.add_class::<pipeline::reasoning_engine::Rule>()?;
    m.add_class::<memory::emergence_detector::PyEmergenceDetector>()?;
    m.add_class::<graph::community_detector::PyCommunityDetector>()?;
    m.add_class::<graph::constellation_detector::Constellation>()?;
    m.add_class::<graph::constellation_detector::PyConstellationDetector>()?;
    m.add_class::<graph::constellation_boost::ConstellationMember>()?;
    m.add_class::<graph::constellation_boost::PyConstellationBoost>()?;

    // Memory consolidation pyfunctions
    m.add_function(wrap_pyfunction!(memory::memory_consolidation::consolidate_memories, m)?)?;
    m.add_function(wrap_pyfunction!(memory::memory_consolidation::consolidate_memories_from_content_py, m)?)?;

    // Add arrow_bridge sub-module
    let arrow_bridge_module = PyModule::new_bound(_py, "arrow_bridge")?;
    ffi::arrow_bridge::arrow_bridge(_py, &arrow_bridge_module)?;
    m.add_submodule(&arrow_bridge_module)?;

    // Add sutra_kernel sub-module
    let sutra_kernel_module = PyModule::new_bound(_py, "sutra_kernel")?;
    sutra_kernel::sutra_kernel(_py, &sutra_kernel_module)?;
    m.add_submodule(&sutra_kernel_module)?;

    // Add constellations sub-module
    let constellations_module = PyModule::new_bound(_py, "constellations")?;
    memory::constellations::constellations(_py, &constellations_module)?;
    m.add_submodule(&constellations_module)?;

    // Add galactic_accelerator functions directly to main module for backward compatibility
    m.add_function(wrap_pyfunction!(
        memory::galactic_accelerator::galactic_batch_score,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        memory::galactic_accelerator::galactic_batch_score_quick,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        memory::galactic_accelerator::galactic_decay_drift,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        memory::galactic_accelerator::galactic_zone_counts,
        m
    )?)?;

    // Register native FFI functions
    ffi::native_ffi::register_native_ffi(m)?;

    // Add massive_deployer classes
    m.add_class::<pipeline::massive_deployer::MassiveDeployer>()?;
    m.add_class::<pipeline::massive_deployer::CampaignTask>()?;
    m.add_function(wrap_pyfunction!(
        pipeline::massive_deployer::create_massive_deployer,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        pipeline::massive_deployer::benchmark_rust_vs_python,
        m
    )?)?;

    // Add inference sub-module (ternary SIMD kernels)
    let inference_module = PyModule::new_bound(_py, "inference")?;
    inference_pymodule::inference(_py, &inference_module)?;
    m.add_submodule(&inference_module)?;

    // --- START RECONCILLATION ---
    // Manually register missing top-level functions from submodules for flat whitemagic_rust access
    m.add_function(wrap_pyfunction!(search::keyword_extract::keyword_extract, m)?)?;
    m.add_function(wrap_pyfunction!(search::keyword_extract::keyword_extract_batch, m)?)?;
    m.add_function(wrap_pyfunction!(math::minhash::minhash_find_duplicates, m)?)?;
    m.add_function(wrap_pyfunction!(math::minhash::minhash_signatures, m)?)?;
    m.add_function(wrap_pyfunction!(pipeline::tokio_clones::tokio_deploy_clones, m)?)?;
    m.add_function(wrap_pyfunction!(pipeline::tokio_clones::tokio_clone_bench, m)?)?;
    m.add_function(wrap_pyfunction!(pipeline::tokio_clones::tokio_clone_stats, m)?)?;
    m.add_function(wrap_pyfunction!(math::spatial_index_5d::batch_nearest_5d, m)?)?;
    m.add_function(wrap_pyfunction!(math::spatial_index_5d::density_map_5d, m)?)?;
    // --- END RECONCILLATION ---

    // Register prat router functions
    ffi::prat_router_v6::register_prat_router(m)?;

    // Register continuous daemon
    pipeline::continuous_daemon::register_daemon(m)?;

    // Add graph_engine sub-module
    let graph_engine_module = PyModule::new_bound(_py, "graph_engine")?;
    graph::graph_engine::graph_engine(_py, &graph_engine_module)?;
    m.add_submodule(&graph_engine_module)?;

    // Add hnsw_index sub-module
    let hnsw_index_module = PyModule::new_bound(_py, "hnsw_index")?;
    graph::hnsw_index::hnsw_index(_py, &hnsw_index_module)?;
    m.add_submodule(&hnsw_index_module)?;

    // Add simhash_lsh sub-module
    let simhash_module = PyModule::new_bound(_py, "simhash_lsh")?;
    embeddings::simhash_lsh::simhash_lsh(_py, &simhash_module)?;
    m.add_submodule(&simhash_module)?;

    // Add galaxy_miner sub-module
    let galaxy_miner_module = PyModule::new_bound(_py, "galaxy_miner")?;
    memory::galaxy_miner::galaxy_miner(_py, &galaxy_miner_module)?;
    m.add_submodule(&galaxy_miner_module)?;

    // Add recursive_intelligence sub-module
    let recursive_intelligence_module = PyModule::new_bound(_py, "recursive_intelligence")?;
    pipeline::recursive_intelligence::recursive_intelligence(_py, &recursive_intelligence_module)?;
    m.add_submodule(&recursive_intelligence_module)?;

    // Add holographic_encoder_5d sub-module
    let holographic_module = PyModule::new_bound(_py, "holographic_encoder_5d")?;
    math::holographic_encoder_5d::register_holographic_encoder(_py, &holographic_module)?;
    m.add_submodule(&holographic_module)?;

    // Add ipc_bridge sub-module
    let ipc_bridge_module = PyModule::new_bound(_py, "ipc_bridge")?;
    ffi::ipc_bridge::ipc_bridge(_py, &ipc_bridge_module)?;
    m.add_submodule(&ipc_bridge_module)?;

    // Add conductor sub-module
    let conductor_module = PyModule::new_bound(_py, "conductor")?;
    conductor::ffi::conductor(_py, &conductor_module)?;
    m.add_submodule(&conductor_module)?;

    // Add search functions directly to main module
    m.add_function(wrap_pyfunction!(search::search_build_index, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_query, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_fuzzy, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_and_query, m)?)?;
    m.add_function(wrap_pyfunction!(search::search_stats, m)?)?;

    // Add hot_paths functions directly to main module
    hot_paths::hot_paths(_py, m)?;

    // Add synthesis_engine sub-module
    let synthesis_module = PyModule::new_bound(_py, "synthesis_engine")?;
    pipeline::synthesis_engine::synthesis_engine(_py, &synthesis_module)?;
    m.add_submodule(&synthesis_module)?;

    // Add sqlite_backend sub-module
    let sqlite_module = PyModule::new_bound(_py, "sqlite_backend")?;
    memory::sqlite_backend::register_sqlite_backend(&sqlite_module)?;
    m.add_submodule(&sqlite_module)?;

    // Add zig_ffi functions directly to main module for Zig bridge support
    zig_ffi::register_zig_ffi(m)?;

    // Geneseed Vault — git history pattern mining
    m.add_class::<geneseed_miner::OptimizationPattern>()?;
    m.add_class::<geneseed_miner::GeneseedStats>()?;
    m.add_function(wrap_pyfunction!(geneseed_miner::mine_geneseed_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(geneseed_miner::get_geneseed_stats, m)?)?;

    // Code Writing Clone Army — parallel file operations via Rayon
    m.add_class::<pipeline::code_writing_clone::CodeOperation>()?;
    m.add_class::<pipeline::code_writing_clone::CodeWritingResult>()?;
    m.add_class::<pipeline::code_writing_clone::CodeWritingClone>()?;
    m.add_class::<pipeline::code_writing_clone::CodeWritingArmy>()?;
    m.add_function(wrap_pyfunction!(
        pipeline::code_writing_clone::benchmark_code_writing,
        m
    )?)?;

    // Add convergence Detector — functions wired via convergence_bridge.py
    m.add_function(wrap_pyfunction!(search::convergence_detector::detect_convergence, m)?)?;
    m.add_function(wrap_pyfunction!(search::convergence_detector::convergence_score, m)?)?;

    // Directory walker — parallel file tree walk for STRATA acceleration
    m.add_function(wrap_pyfunction!(search::dir_walker::walk_directory, m)?)?;

    // STRATA accelerators — batch regex scan + fast content hashing
    m.add_function(wrap_pyfunction!(search::strata_accel::batch_regex_scan, m)?)?;
    m.add_function(wrap_pyfunction!(search::strata_accel::fast_sha256, m)?)?;
    m.add_function(wrap_pyfunction!(search::strata_accel::batch_sha256, m)?)?;

    // StateBoard — mmap-backed shared-memory blackboard for system vital signs
    pipeline::state_board::register_state_board(m)?;

    // Unified Cache — sub-microsecond LRU+TTL cache for all cache layers
    cache::unified_cache::register_cache(m)?;

    // Monte Carlo forecasting calibration (Sprint F)
    m.add_class::<monte_carlo::PercentileSummary>()?;
    m.add_class::<monte_carlo::MonteCarloResult>()?;
    m.add_class::<monte_carlo::MonteCarloForecast>()?;
    m.add_function(wrap_pyfunction!(monte_carlo::run_mc_forecast_calibration, m)?)?;

    // I Ching engine (Phase 2a)
    m.add_function(wrap_pyfunction!(iching::iching_cast, m)?)?;
    m.add_function(wrap_pyfunction!(iching::iching_cast_stochastic, m)?)?;

    // Hexagram SIMD engine (Phase 6b)
    m.add_function(wrap_pyfunction!(hexagram_simd_py_execute, m)?)?;
    m.add_function(wrap_pyfunction!(hexagram_dispatch_info, m)?)?;
    m.add_function(wrap_pyfunction!(hexagram_boltzmann_select, m)?)?;

    Ok(())
}

// WASM exports - re-export from wasm module
#[cfg(feature = "wasm")]
pub use wasm::*;

#[cfg(feature = "python")]
pub mod monte_carlo;

#[cfg(feature = "python")]
pub mod iching;

#[cfg(feature = "python")]
pub mod iching_dispatch;

#[cfg(feature = "python")]
pub mod iching_resonance;

#[cfg(feature = "python")]
pub mod kuramoto;

#[cfg(feature = "python")]
pub mod hexagram_hrr;

#[cfg(feature = "python")]
pub mod hexagram_simd;

// Zig FFI module for polyglot bridge support (Python only)
#[cfg(feature = "python")]
mod zig_ffi;

// ---------------------------------------------------------------------------
// Phase 6b: PyO3 wrappers for hexagram SIMD engine
// ---------------------------------------------------------------------------

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pyfunction]
fn hexagram_simd_py_execute(loads: std::collections::HashMap<u32, Vec<f64>>) -> Vec<(u32, Vec<f64>)> {
    let mut engine = hexagram_simd::HexagramSimdEngine::new();
    for (&num, data) in &loads {
        engine.load(num, data.clone());
    }
    engine.execute();
    engine.collect()
}

#[cfg(feature = "python")]
#[pyfunction]
fn hexagram_dispatch_info(hexagram_num: u32) -> Option<(String, String, u32, u32, bool)> {
    use iching_dispatch::dispatch_for_hexagram;
    dispatch_for_hexagram(hexagram_num).map(|d| {
        (
            format!("{:?}", d.effective_compute),
            format!("{:?}", d.effective_io),
            d.lane_width,
            d.priority,
            d.fully_simd,
        )
    })
}

#[cfg(feature = "python")]
#[pyfunction]
fn hexagram_boltzmann_select(temperature: f64) -> u32 {
    use rand::SeedableRng;
    use rand::rngs::SmallRng;
    let mut rng = SmallRng::from_entropy();
    iching_dispatch::boltzmann_select(&mut rng, temperature)
}
