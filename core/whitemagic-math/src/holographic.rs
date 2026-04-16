//! Holographic Spatial Memory Backend — WASM Compatible
//! Coordinates: [x (Logic-Emotion), y (Micro-Macro), z (Time), w (Importance)]

use kdtree::distance::squared_euclidean;
use kdtree::KdTree;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use serde::{Deserialize, Serialize};

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub struct HolographicCoordinate {
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub w: f64,
}

#[cfg_attr(feature = "wasm", wasm_bindgen)]
impl HolographicCoordinate {
    #[cfg_attr(feature = "wasm", wasm_bindgen(constructor))]
    pub fn new(x: f64, y: f64, z: f64, w: f64) -> Self {
        Self { x, y, z, w }
    }

    pub fn to_vec(&self) -> Vec<f64> {
        vec![self.x, self.y, self.z, self.w]
    }
}

type Point = [f64; 4];

#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub struct HolographicIndex {
    tree: Arc<RwLock<KdTree<f64, String, Point>>>,
    coords: Arc<RwLock<HashMap<String, Point>>>,
}

#[cfg_attr(feature = "wasm", wasm_bindgen)]
impl HolographicIndex {
    #[cfg_attr(feature = "wasm", wasm_bindgen(constructor))]
    pub fn new() -> Self {
        Self {
            tree: Arc::new(RwLock::new(KdTree::new(4))),
            coords: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn add(&self, memory_id: String, x: f64, y: f64, z: f64, w: f64) {
        let point: Point = [x, y, z, w];
        if let Ok(mut tree) = self.tree.write() {
            if let Ok(mut coords) = self.coords.write() {
                if let Some(old_point) = coords.get(&memory_id) {
                    let _ = tree.remove(old_point, &memory_id);
                }
                let _ = tree.add(point, memory_id.clone());
                coords.insert(memory_id, point);
            }
        }
    }

    // internal method for logic
    pub(crate) fn query_nearest_vec(&self, x: f64, y: f64, z: f64, w: f64, n: usize) -> Vec<(String, f64)> {
        if let Ok(tree) = self.tree.read() {
            let point: Point = [x, y, z, w];
            if let Ok(results) = tree.nearest(&point, n, &squared_euclidean) {
                return results.into_iter().map(|(d, id)| (id.clone(), d)).collect();
            }
        }
        Vec::new()
    }

    #[cfg(feature = "wasm")]
    pub fn query_nearest(&self, x: f64, y: f64, z: f64, w: f64, n: usize) -> Result<String, JsValue> {
        let results = self.query_nearest_vec(x, y, z, w, n);
        serde_json::to_string(&results).map_err(|e| JsValue::from_str(&format!("{}", e)))
    }
}
