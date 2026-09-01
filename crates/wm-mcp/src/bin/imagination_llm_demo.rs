//! Imagination Engine LLM demo — exercises all systems with real LLM hemispheres.
//!
//! Run with: WM_LLAMA_ENDPOINT=http://localhost:8080 cargo run --bin imagination_llm_demo

use serde_json::json;
use std::sync::Arc;
use wm_bicameral::{
    ScenarioEngine, ScenarioEvaluator,
    simulation_bridge::{SimulationBridge, SimulationBridgeConfig},
    world_model_from_env,
};
use wm_cognitive::PatternBridge;
use wm_core::{Context, Tool};
use wm_memory::MemoryStore;
use wm_tools::expansion::imagination::{
    ImaginePredictTool, ImagineReflectTool, ImagineScenarioTool,
};

fn separator(title: &str) {
    println!("\n{}", "=".repeat(60));
    println!("  {title}");
    println!("{}", "=".repeat(60));
}

#[tokio::main]
async fn main() {
    separator("IMAGINATION ENGINE — LIVE LLM DEMO");

    let wm_llama = std::env::var("WM_LLAMA_ENDPOINT").ok();
    let wm_llm_key = std::env::var("WM_LLM_API_KEY").ok();
    println!("\nLLM Configuration:");
    println!(
        "  WM_LLAMA_ENDPOINT: {}",
        wm_llama.as_deref().unwrap_or("(not set — using stubs)")
    );
    println!(
        "  WM_LLM_API_KEY: {}",
        if wm_llm_key.is_some() {
            "set (cloud LLM for right hemisphere)"
        } else {
            "(not set — using stub right)"
        }
    );

    // Estimate LLM calls: step1(19) + step2(2) + step3(4) + step4(3*3*2=18) + step6(19+2+4=25) = ~68 calls
    let est_calls = 19 + 2 + 4 + 3 * 3 * 2 + 25;
    println!("\n  Estimated LLM calls: ~{est_calls} (each taking ~15-30s with a local 3B model)");
    println!(
        "  Expected runtime: ~{}-{} minutes",
        est_calls * 15 / 60,
        est_calls * 30 / 60
    );

    // ── 1. Scenario Engine with LLM ─────────────────────────────────
    separator("1. Scenario Engine — LLM-generated scenarios");

    let world_model = world_model_from_env();
    let engine = ScenarioEngine::with_defaults(world_model, ScenarioEvaluator::with_defaults());

    println!("\nState: \"production API server experiencing high latency under concurrent load\"");
    println!("Goal: \"reduce p99 latency below 200ms without sacrificing throughput\"");

    let scenarios = engine.imagine(
        "production API server experiencing high latency under concurrent load",
        "reduce p99 latency below 200ms without sacrificing throughput",
        "previous attempts: added caching, tuned connection pool, indexed database queries",
    );

    println!("\nGenerated {} scenarios:", scenarios.len());
    for (i, s) in scenarios.iter().enumerate() {
        println!(
            "\n  {}. action=\"{}\"",
            i + 1,
            s.action.chars().take(120).collect::<String>()
        );
        println!(
            "     score={:.2} risk={:.2} novelty={:.2}",
            s.score, s.risk, s.novelty
        );
        if !s.rationale.is_empty() {
            println!(
                "     rationale: {}",
                s.rationale.chars().take(200).collect::<String>()
            );
        }
        if let Some(ref breakdown) = s.breakdown {
            println!(
                "     breakdown: overall={:.2} goal={:.2} risk={:.2} novelty={:.2} confidence={:.2}",
                breakdown.overall,
                breakdown.goal_progress,
                breakdown.risk_avoidance,
                breakdown.novelty,
                breakdown.confidence
            );
        }
    }

    if let Some(best) = engine.select_balanced(&scenarios, 0.05) {
        println!(
            "\n  ★ Best (balanced): \"{}\"",
            best.action.chars().take(120).collect::<String>()
        );
        println!("    score={:.2} risk={:.2}", best.score, best.risk);
    }

    // ── 2. Prediction with LLM ──────────────────────────────────────
    separator("2. World Model — LLM prediction of specific action");

    let world_model = world_model_from_env();
    let prediction = world_model.predict(
        "API server with 500ms p99 latency, 1000 concurrent users, PostgreSQL backend",
        "implement request coalescing with 50ms deduplication window",
        "reduce p99 latency below 200ms",
    );

    let best = prediction.best();
    println!("\nBest prediction:");
    println!("  description: {}", best.description);
    println!("  confidence:  {:.2}", best.confidence);
    println!("  goal_progress: {:.2}", best.goal_progress);
    println!("  changes: {:?}", best.changes);
    println!("  risks: {:?}", best.risks);
    println!("  has_consensus: {}", prediction.has_consensus());

    if let Some(ref right) = prediction.right {
        println!("\n  Right hemisphere alternative:");
        println!("    description: {}", right.description);
        println!("    confidence:  {:.2}", right.confidence);
    }

    // ── 3. Counterfactual Reflection with LLM ───────────────────────
    separator("3. Counterfactual Reflection — LLM-powered what-if analysis");

    let world_model = world_model_from_env();
    let engine = ScenarioEngine::with_defaults(world_model, ScenarioEvaluator::with_defaults());

    println!("\nPast state: \"API server was hitting 800ms p99 under load spikes\"");
    println!("Actual action: \"added Redis caching layer\"");
    println!("Alternative: \"implemented request queue with backpressure and circuit breaker\"");
    println!("Goal: \"maintain p99 below 300ms during load spikes\"");

    let reflection = engine.reflect(
        "API server was hitting 800ms p99 under load spikes",
        "added Redis caching layer",
        "implemented request queue with backpressure and circuit breaker",
        "maintain p99 below 300ms during load spikes",
    );

    println!("\nActual outcome (predicted):");
    println!("  {}", reflection.actual_prediction.description);
    println!(
        "  confidence: {:.2}",
        reflection.actual_prediction.confidence
    );
    println!(
        "  goal_progress: {:.2}",
        reflection.actual_prediction.goal_progress
    );

    println!("\nCounterfactual outcome (predicted):");
    println!("  {}", reflection.counterfactual_prediction.description);
    println!(
        "  confidence: {:.2}",
        reflection.counterfactual_prediction.confidence
    );
    println!(
        "  goal_progress: {:.2}",
        reflection.counterfactual_prediction.goal_progress
    );

    println!(
        "\n  would_have_been_better: {}",
        reflection.would_have_been_better
    );
    println!("  lesson: {}", reflection.lesson);

    // ── 4. Simulation Bridge ────────────────────────────────────────
    separator("4. Simulation Bridge — MC rollout + forecasting + sensitivity");

    let world_model = world_model_from_env();
    // Use a small MC sample count for the demo — each sample calls the LLM,
    // so 1_000 (default) would take hours with a real LLM.
    let mc_samples = 3;
    let bridge_config = SimulationBridgeConfig {
        mc_samples,
        sensitivity_samples: 50,
        cf_bootstrap: 50,
        ..Default::default()
    };
    let mut bridge = SimulationBridge::new(bridge_config);

    let scenario = &scenarios[0];
    let history: Vec<f64> = vec![0.45, 0.50, 0.55, 0.52, 0.58, 0.60];
    let n_steps = scenario.trajectory.len().max(3);
    println!(
        "\n  Running MC rollout: {mc_samples} samples × {n_steps} steps × 2 hemispheres = {} LLM calls...",
        mc_samples * n_steps * 2
    );
    let enriched = bridge.enrich_scenario(&world_model, scenario, &history);

    println!(
        "\nEnriched scenario: \"{}\"",
        enriched
            .scenario
            .action
            .chars()
            .take(100)
            .collect::<String>()
    );
    println!("  original score: {:.2}", enriched.scenario.score);
    println!(
        "  adjusted confidence: {:.2}",
        enriched.adjusted_confidence()
    );
    println!(
        "  MC rollout: mean={:.3} std_dev={:.3} samples={} positive_frac={:.2}",
        enriched.rollout.mean,
        enriched.rollout.std_dev,
        enriched.rollout.n_samples,
        enriched.rollout.positive_fraction
    );
    println!(
        "  Forecast: {} points, method={}, mae={:.4}",
        enriched.prior.n_points, enriched.prior.method, enriched.prior.mae
    );
    if let Some(top) = enriched.sensitivity.most_influential() {
        println!(
            "  Most influential factor: \"{}\" (total_order={:.3})",
            top.label, top.total_order
        );
    }

    // ── 5. Pattern Bridge ───────────────────────────────────────────
    separator("5. Pattern Bridge — novelty + strategy + surprise assessment");

    let pattern_bridge = PatternBridge::default();
    let enriched_scenarios = pattern_bridge.enrich_scenarios(&scenarios);

    println!(
        "\nPattern enrichment for {} scenarios:",
        enriched_scenarios.len()
    );
    for (i, es) in enriched_scenarios.iter().enumerate() {
        println!(
            "\n  {}. \"{}\"",
            i + 1,
            es.scenario.action.chars().take(80).collect::<String>()
        );
        println!(
            "     novelty: familiar={} score={:.2} constellations={}",
            es.novelty.is_familiar, es.novelty.novelty_score, es.novelty.constellation_count
        );
        println!(
            "     surprise: decision={:?} novelty={:.2} deep_analysis={}",
            es.surprise.decision, es.surprise.novelty_score, es.surprise.needs_deep_analysis
        );
        println!(
            "     score adjustment: {:.2} → {:.2}",
            es.scenario.score, es.adjusted_score
        );
    }

    // ── 6. MCP Tools ────────────────────────────────────────────────
    separator("6. MCP Tools — imagine.scenario / predict / reflect");

    let dir = std::env::temp_dir().join("wm_imagination_llm_demo");
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let store = Arc::new(MemoryStore::open(&dir, 1024 * 1024).unwrap());

    // imagine.scenario
    let scenario_tool = ImagineScenarioTool::new(store);
    let mut ctx = Context::default();
    println!("\nimagine.scenario:");
    let result = scenario_tool.call(
        &mut ctx,
        json!({
            "state": "microservice architecture with 12 services, inter-service latency is 150ms average",
            "goal": "reduce inter-service communication overhead",
            "enrich_simulation": false,
        }),
    ).await;
    if let Ok(val) = result {
        println!("  status: {}", val["status"].as_str().unwrap_or("?"));
        if let Some(count) = val["scenario_count"].as_u64() {
            println!("  scenarios: {count}");
        }
        if let Some(action) = val["best_action"].as_str() {
            println!(
                "  best: \"{}\"",
                action.chars().take(120).collect::<String>()
            );
        }
    }

    // imagine.predict
    let predict_tool = ImaginePredictTool::new();
    println!("\nimagine.predict:");
    let result = predict_tool
        .call(
            &mut ctx,
            json!({
                "state": "12 microservices with REST APIs, 150ms avg inter-service latency",
                "action": "replace REST calls with gRPC + Protocol Buffers",
                "goal": "reduce inter-service latency to under 50ms",
            }),
        )
        .await;
    if let Ok(val) = result {
        println!("  status: {}", val["status"].as_str().unwrap_or("?"));
        if let Some(desc) = val["best_prediction"]["description"].as_str() {
            println!(
                "  prediction: {}",
                desc.chars().take(200).collect::<String>()
            );
        }
        if let Some(conf) = val["best_prediction"]["confidence"].as_f64() {
            println!("  confidence: {conf:.2}");
        }
        println!("  has_consensus: {}", val["has_consensus"]);
    }

    // imagine.reflect
    let reflect_tool = ImagineReflectTool::new();
    println!("\nimagine.reflect:");
    let result = reflect_tool.call(
        &mut ctx,
        json!({
            "past_state": "12 microservices with 150ms REST latency causing cascading timeouts",
            "actual_action": "added retry logic with exponential backoff",
            "alternative_action": "switched to gRPC with connection pooling and circuit breakers",
            "goal": "eliminate cascading timeouts",
        }),
    ).await;
    if let Ok(val) = result {
        println!("  status: {}", val["status"].as_str().unwrap_or("?"));
        if let Some(desc) = val["actual_outcome"]["description"].as_str() {
            println!("  actual: {}", desc.chars().take(150).collect::<String>());
        }
        if let Some(desc) = val["counterfactual_outcome"]["description"].as_str() {
            println!(
                "  counterfactual: {}",
                desc.chars().take(150).collect::<String>()
            );
        }
        println!(
            "  would_have_been_better: {}",
            val["would_have_been_better"]
        );
        if let Some(lesson) = val["lesson"].as_str() {
            println!("  lesson: {}", lesson.chars().take(200).collect::<String>());
        }
    }

    // ── 7. NLU Routing ──────────────────────────────────────────────
    separator("7. NLU Routing — natural language → imagination tools");

    let queries = [
        "imagine scenarios for migrating from REST to gRPC",
        "brainstorm contingency plans for database failover",
        "envision what-if we switched to event sourcing",
        "counterfactual analysis of choosing Redis over Memcached",
        "predict the outcome of adding a CDN layer",
    ];

    for q in &queries {
        let (tool, conf) = wm_tools::nlu::classify(q);
        println!("  \"{q}\"");
        println!("    → {tool} (confidence: {conf:.3})");
    }

    separator("LIVE LLM DEMO COMPLETE");
    println!("\nAll imagination engine systems exercised with real LLM hemispheres. ✦");
}
