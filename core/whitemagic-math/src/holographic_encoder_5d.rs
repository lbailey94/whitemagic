//! Holographic Encoder — 5D coordinate encoding for memories
//! Decoupled for WASM compatibility.

#![allow(dead_code)]

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;
use serde::{Deserialize, Serialize};

const LOGIC_KEYWORDS: &[&str] = &[
    "algorithm", "function", "class", "method", "variable", "parameter",
    "return", "import", "module", "interface", "struct", "enum", "type",
    "compile", "binary", "integer", "boolean", "array", "hash", "queue",
    "stack", "tree", "graph", "node", "edge", "index", "query", "schema",
    "database", "table", "column", "row", "key", "value", "config",
    "deploy", "build", "test", "debug", "error", "exception", "log",
];

const EMOTION_KEYWORDS: &[&str] = &[
    "feel", "believe", "hope", "fear", "love", "hate", "joy", "anger",
    "sadness", "surprise", "trust", "anticipation", "dream", "wish",
    "inspire", "motivate", "passion", "creative", "intuition", "vision",
    "soul", "spirit", "heart", "beauty", "harmony", "peace", "balance",
    "wisdom", "insight", "revelation", "epiphany", "grateful", "wonder",
    "meaning", "purpose", "destiny", "journey", "growth", "transform",
];

const MICRO_KEYWORDS: &[&str] = &[
    "byte", "bit", "char", "pixel", "cell", "atom", "detail", "specific",
    "particular", "individual", "single", "one", "local", "narrow",
    "small", "minor", "trivial", "line", "character", "token", "symbol", "field",
];

const MACRO_KEYWORDS: &[&str] = &[
    "system", "architecture", "framework", "platform", "ecosystem",
    "infrastructure", "enterprise", "global", "universal", "broad",
    "comprehensive", "holistic", "strategic", "vision", "roadmap",
    "philosophy", "paradigm", "worldview", "civilization", "cosmos",
];

fn garden_element(garden: &str) -> &'static str {
    match garden.to_lowercase().as_str() {
        "wood" | "east" => "wood",
        "fire" | "south" => "fire",
        "earth" | "center" => "earth",
        "metal" | "west" => "metal",
        "water" | "north" => "water",
        _ => "earth",
    }
}

fn element_bias(element: &str) -> [f64; 5] {
    match element {
        "wood" => [0.1, 0.15, 0.0, 1.0, 1.0],
        "fire" => [0.2, 0.1, 0.05, 1.1, 1.0],
        "earth" => [0.0, 0.0, 0.0, 1.0, 1.0],
        "metal" => [-0.15, -0.1, 0.0, 1.0, 1.05],
        "water" => [0.05, 0.05, -0.1, 0.95, 1.1],
        _ => [0.0, 0.0, 0.0, 1.0, 1.0],
    }
}

// Internal version of MemoryInput with all fields for Rust/Python use
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MemoryInput {
    pub id: String,
    pub content: String,
    pub importance: f64,
    pub access_count: u32,
    pub age_days: f64,
    pub galactic_distance: f64,
    pub garden: String,
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "wasm", wasm_bindgen(getter_with_clone))]
pub struct Coordinate5D {
    pub id: String,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub w: f64,
    pub v: f64,
}

#[inline]
fn count_keywords(text: &str, keywords: &[&str]) -> usize {
    let lower = text.to_lowercase();
    keywords.iter().filter(|kw| lower.contains(**kw)).count()
}

fn calculate_x(content: &str) -> f64 {
    let logic_count = count_keywords(content, LOGIC_KEYWORDS) as f64;
    let emotion_count = count_keywords(content, EMOTION_KEYWORDS) as f64;
    let total = logic_count + emotion_count;
    if total == 0.0 { return 0.0; }
    ((emotion_count - logic_count) / total).clamp(-1.0, 1.0)
}

fn calculate_y(content: &str) -> f64 {
    let micro_count = count_keywords(content, MICRO_KEYWORDS) as f64;
    let macro_count = count_keywords(content, MACRO_KEYWORDS) as f64;
    let total = micro_count + macro_count;
    if total == 0.0 { return 0.0; }
    ((macro_count - micro_count) / total).clamp(-1.0, 1.0)
}

fn calculate_z(age_days: f64) -> f64 {
    if age_days <= 0.0 { return 1.0; }
    let normalized = 1.0 - (2.0 / (1.0 + (-age_days / 180.0).exp()));
    normalized.clamp(-1.0, 1.0)
}

fn calculate_w(importance: f64, access_count: u32, content_len: usize) -> f64 {
    let base = importance.max(0.5);
    let access_boost = (access_count as f64 / 10.0).min(0.5);
    let richness_boost = if content_len > 500 { 0.2 } else if content_len > 200 { 0.1 } else { 0.0 };
    (base + access_boost + richness_boost).min(2.5)
}

fn calculate_v(galactic_distance: f64, access_count: u32, importance: f64) -> f64 {
    let distance_vitality = 1.0 - galactic_distance.clamp(0.0, 1.0);
    let access_vitality = (access_count as f64 / 20.0).min(0.3);
    let importance_vitality = (importance - 0.5).max(0.0) * 0.2;
    (distance_vitality + access_vitality + importance_vitality).clamp(0.0, 1.0)
}

pub fn encode_memory(mem: &MemoryInput) -> Coordinate5D {
    let mut x = calculate_x(&mem.content);
    let mut y = calculate_y(&mem.content);
    let mut z = calculate_z(mem.age_days);
    let mut w = calculate_w(mem.importance, mem.access_count, mem.content.len());
    let mut v = calculate_v(mem.galactic_distance, mem.access_count, mem.importance);

    if !mem.garden.is_empty() {
        let element = garden_element(&mem.garden);
        let bias = element_bias(element);
        x = (x + bias[0]).clamp(-1.0, 1.0);
        y = (y + bias[1]).clamp(-1.0, 1.0);
        z = (z + bias[2]).clamp(-1.0, 1.0);
        w *= bias[3];
        v *= bias[4];
    }

    Coordinate5D {
        id: mem.id.clone(),
        x, y, z,
        w: w.min(2.5),
        v: v.clamp(0.0, 1.0),
    }
}

pub fn encode_batch(memories: &[MemoryInput]) -> Vec<Coordinate5D> {
    memories.iter().map(encode_memory).collect()
}

#[inline]
pub fn distance_5d(a: &Coordinate5D, b: &Coordinate5D, weights: &[f64; 5]) -> f64 {
    let dx = (a.x - b.x) * weights[0];
    let dy = (a.y - b.y) * weights[1];
    let dz = (a.z - b.z) * weights[2];
    let dw = (a.w - b.w) * weights[3];
    let dv = (a.v - b.v) * weights[4];
    (dx * dx + dy * dy + dz * dz + dw * dw + dv * dv).sqrt()
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn holographic_encode_batch(memories_json: &str) -> Result<String, JsValue> {
    let memories: Vec<MemoryInput> = serde_json::from_str(memories_json).map_err(|e| {
        JsValue::from_str(&format!("JSON parse: {}", e))
    })?;
    let coords = encode_batch(&memories);
    serde_json::to_string(&coords).map_err(|e| {
        JsValue::from_str(&format!("JSON serialize: {}", e))
    })
}

#[cfg(feature = "wasm")]
#[wasm_bindgen]
pub fn holographic_encode_single(memory_json: &str) -> Result<String, JsValue> {
    let mem: MemoryInput = serde_json::from_str(memory_json).map_err(|e| {
        JsValue::from_str(&format!("JSON parse: {}", e))
    })?;
    let coord = encode_memory(&mem);
    serde_json::to_string(&coord).map_err(|e| {
        JsValue::from_str(&format!("JSON serialize: {}", e))
    })
}
