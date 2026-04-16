use kdtree::distance::squared_euclidean;
use kdtree::KdTree;
use std::sync::Mutex;
use lazy_static::lazy_static;

#[cfg(feature = "wasm")]
use wasm_bindgen::prelude::*;

#[cfg_attr(feature = "wasm", wasm_bindgen)]
pub struct HolographicIndexBasic {
    tree: KdTree<f64, String, [f64; 4]>,
    count: usize,
}

#[cfg_attr(feature = "wasm", wasm_bindgen)]
impl HolographicIndexBasic {
    #[cfg_attr(feature = "wasm", wasm_bindgen(constructor))]
    pub fn new() -> Self {
        HolographicIndexBasic {
            tree: KdTree::new(4),
            count: 0,
        }
    }

    pub fn add(&mut self, id: String, x: f64, y: f64, z: f64, w: f64) {
        let _ = self.tree.add([x, y, z, w], id);
        self.count += 1;
    }

    pub(crate) fn query_nearest_vec(&self, x: f64, y: f64, z: f64, w: f64, k: usize) -> Vec<(String, f64)> {
        if let Ok(results) = self.tree.nearest(&[x, y, z, w], k, &squared_euclidean) {
            return results.into_iter().map(|(d, id)| (id.clone(), d)).collect();
        }
        Vec::new()
    }

    #[cfg(feature = "wasm")]
    pub fn query_nearest(&self, x: f64, y: f64, z: f64, w: f64, k: usize) -> Result<String, JsValue> {
        let results = self.query_nearest_vec(x, y, z, w, k);
        serde_json::to_string(&results).map_err(|e| JsValue::from_str(&format!("{}", e)))
    }
}
