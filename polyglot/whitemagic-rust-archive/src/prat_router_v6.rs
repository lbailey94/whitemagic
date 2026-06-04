use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::OnceLock;

static TOOL_TO_GANA: OnceLock<HashMap<&'static str, &'static str>> = OnceLock::new();
static GANA_ORDER: [&str; 28] = [
    "gana_horn",
    "gana_neck",
    "gana_root",
    "gana_room",
    "gana_heart",
    "gana_tail",
    "gana_winnowing_basket",
    "gana_ghost",
    "gana_willow",
    "gana_star",
    "gana_extended_net",
    "gana_wings",
    "gana_chariot",
    "gana_abundance",
    "gana_straddling_legs",
    "gana_mound",
    "gana_stomach",
    "gana_hairy_head",
    "gana_net",
    "gana_turtle_beak",
    "gana_three_stars",
    "gana_dipper",
    "gana_ox",
    "gana_girl",
    "gana_void",
    "gana_roof",
    "gana_encampment",
    "gana_wall",
];

fn get_tool_map() -> &'static HashMap<&'static str, &'static str> {
    TOOL_TO_GANA.get_or_init(|| {
        let mut m = HashMap::new();
        m.insert("search_memories", "gana_winnowing_basket");
        m.insert("gnosis", "gana_ghost");
        m.insert("health_report", "gana_horn");
        m.insert("create_memory", "gana_heart");
        m.insert("cluster_stats", "gana_dipper");
        m.insert("consolidate", "gana_abundance");
        m.insert("synthesize", "gana_three_stars");
        m
    })
}

#[pyfunction]
pub fn prat_route(tool: String) -> String {
    let map = get_tool_map();
    map.get(tool.as_str()).unwrap_or(&"gana_ghost").to_string()
}

#[pyfunction]
pub fn prat_route_batch(tools: Vec<String>) -> Vec<String> {
    tools.into_iter().map(prat_route).collect()
}

#[pyfunction]
pub fn resonance_predecessor(gana: String) -> String {
    let idx = GANA_ORDER
        .iter()
        .position(|&r| r == gana.as_str())
        .unwrap_or(0);
    let prev_idx = if idx == 0 { 27 } else { idx - 1 };
    GANA_ORDER[prev_idx].to_string()
}

#[pyfunction]
pub fn resonance_successor(gana: String) -> String {
    let idx = GANA_ORDER
        .iter()
        .position(|&r| r == gana.as_str())
        .unwrap_or(0);
    let next_idx = (idx + 1) % 28;
    GANA_ORDER[next_idx].to_string()
}

#[pyfunction]
pub fn circuit_check() -> String {
    // Basic circuit mock that is closed
    "closed".to_string()
}

#[pyfunction]
pub fn circuit_record_success() -> String {
    "ok".to_string()
}

#[pyfunction]
pub fn circuit_record_failure() -> String {
    "ok".to_string()
}

pub fn register_prat_router(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(prat_route, m)?)?;
    m.add_function(wrap_pyfunction!(prat_route_batch, m)?)?;
    m.add_function(wrap_pyfunction!(resonance_predecessor, m)?)?;
    m.add_function(wrap_pyfunction!(resonance_successor, m)?)?;
    m.add_function(wrap_pyfunction!(circuit_check, m)?)?;
    m.add_function(wrap_pyfunction!(circuit_record_success, m)?)?;
    m.add_function(wrap_pyfunction!(circuit_record_failure, m)?)?;
    Ok(())
}
