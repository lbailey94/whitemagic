//! WebAssembly bindings for WhiteMagic Edge AI
//!
//! Compiles to WASM for browser execution.
//! 10-100x faster than JavaScript implementation.
//!
//! Build with: wasm-pack build --target web

use std::collections::HashMap;
use wasm_bindgen::prelude::*;

/// Initialize the WASM module — call once on startup.
/// Installs the panic hook for better error messages.
#[wasm_bindgen(start)]
pub fn init_wasm() {
    console_error_panic_hook::set_once();
}

/// Edge inference rule
#[wasm_bindgen]
#[derive(Clone)]
pub struct EdgeRule {
    id: String,
    pattern: String,
    response: String,
    confidence: f32,
}

#[wasm_bindgen]
impl EdgeRule {
    #[wasm_bindgen(constructor)]
    pub fn new(id: &str, pattern: &str, response: &str, confidence: f32) -> EdgeRule {
        EdgeRule {
            id: id.to_string(),
            pattern: pattern.to_string(),
            response: response.to_string(),
            confidence,
        }
    }

    #[wasm_bindgen(getter)]
    pub fn id(&self) -> String {
        self.id.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn response(&self) -> String {
        self.response.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn confidence(&self) -> f32 {
        self.confidence
    }
}

/// Inference result
#[wasm_bindgen]
pub struct InferenceResult {
    answer: String,
    confidence: f32,
    method: String,
    needs_cloud: bool,
    tokens_saved: u32,
}

#[wasm_bindgen]
impl InferenceResult {
    #[wasm_bindgen(getter)]
    pub fn answer(&self) -> String {
        self.answer.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn confidence(&self) -> f32 {
        self.confidence
    }

    #[wasm_bindgen(getter)]
    pub fn method(&self) -> String {
        self.method.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn needs_cloud(&self) -> bool {
        self.needs_cloud
    }

    #[wasm_bindgen(getter)]
    pub fn tokens_saved(&self) -> u32 {
        self.tokens_saved
    }
}

/// Edge inference engine - WASM version
#[wasm_bindgen]
pub struct EdgeEngine {
    rules: Vec<EdgeRule>,
    cache: HashMap<String, String>,
    stats_queries: u32,
    stats_local: u32,
    stats_tokens_saved: u32,
}

#[wasm_bindgen]
impl EdgeEngine {
    #[wasm_bindgen(constructor)]
    pub fn new() -> EdgeEngine {
        let mut engine = EdgeEngine {
            rules: Vec::new(),
            cache: HashMap::new(),
            stats_queries: 0,
            stats_local: 0,
            stats_tokens_saved: 0,
        };

        // Add default rules
        engine.add_rule(EdgeRule::new(
            "version",
            "version|what version",
            "WhiteMagic version 23.2.0",
            1.0,
        ));
        engine.add_rule(EdgeRule::new(
            "gardens",
            "garden|how many garden",
            "WhiteMagic has 28 gardens: courage, stillness, healing, sanctuary, love, wisdom, grief, humor, voice, sangha, beauty, adventure, joy, awe, gratitude, creation, presence, play, practice, reverence, dharma, patience, connection, mystery, protection, transformation, truth, metal",
            1.0
        ));
        engine.add_rule(EdgeRule::new(
            "tests",
            "test|how many test",
            "WhiteMagic has 2,564 passing tests",
            0.95,
        ));
        engine.add_rule(EdgeRule::new(
            "offline",
            "offline|work offline|no internet",
            "Yes! This runs entirely locally via WebAssembly. No cloud needed.",
            1.0,
        ));
        engine.add_rule(EdgeRule::new(
            "wasm",
            "wasm|webassembly|fast",
            "This is running as WebAssembly - 10-100x faster than JavaScript!",
            1.0,
        ));

        engine
    }

    /// Add a rule to the engine
    #[wasm_bindgen]
    pub fn add_rule(&mut self, rule: EdgeRule) {
        self.rules.push(rule);
    }

    /// Run inference on a query
    #[wasm_bindgen]
    pub fn infer(&mut self, query: &str) -> InferenceResult {
        self.stats_queries += 1;
        let query_lower = query.to_lowercase();

        // Check cache first
        if let Some(cached) = self.cache.get(&query_lower) {
            self.stats_local += 1;
            self.stats_tokens_saved += 500;
            return InferenceResult {
                answer: cached.clone(),
                confidence: 1.0,
                method: "cache".to_string(),
                needs_cloud: false,
                tokens_saved: 500,
            };
        }

        // Try each rule
        for rule in &self.rules {
            let keywords: Vec<&str> = rule.pattern.split('|').collect();
            let matches = keywords.iter().any(|kw| query_lower.contains(kw.trim()));

            if matches {
                self.stats_local += 1;
                let tokens = (rule.response.len() / 4) as u32 + 100;
                self.stats_tokens_saved += tokens;

                // Cache the result
                self.cache.insert(query_lower, rule.response.clone());

                return InferenceResult {
                    answer: rule.response.clone(),
                    confidence: rule.confidence,
                    method: format!("rule:{}", rule.id),
                    needs_cloud: false,
                    tokens_saved: tokens,
                };
            }
        }

        // No match - needs cloud
        InferenceResult {
            answer: "I don't have a local answer. This might need cloud AI.".to_string(),
            confidence: 0.1,
            method: "no_match".to_string(),
            needs_cloud: true,
            tokens_saved: 0,
        }
    }

    /// Get statistics
    #[wasm_bindgen]
    pub fn get_stats(&self) -> String {
        serde_json::json!({
            "queries": self.stats_queries,
            "local": self.stats_local,
            "tokens_saved": self.stats_tokens_saved,
            "rules": self.rules.len(),
            "cache_size": self.cache.len()
        }).to_string()
    }

    /// Get local resolution rate
    #[wasm_bindgen]
    pub fn local_rate(&self) -> f32 {
        if self.stats_queries == 0 {
            0.0
        } else {
            self.stats_local as f32 / self.stats_queries as f32
        }
    }

    /// Reset statistics
    #[wasm_bindgen]
    pub fn reset_stats(&mut self) {
        self.stats_queries = 0;
        self.stats_local = 0;
        self.stats_tokens_saved = 0;
        self.cache.clear();
    }

    /// Get total tokens saved
    #[wasm_bindgen]
    pub fn tokens_saved(&self) -> u32 {
        self.stats_tokens_saved
    }
}

/// Quick inference function (convenience)
#[wasm_bindgen]
pub fn quick_infer(query: &str) -> String {
    let mut engine = EdgeEngine::new();
    let result = engine.infer(query);
    result.answer
}

/// Cosine similarity between two vectors (passed as JSON arrays)
#[wasm_bindgen]
pub fn cosine_similarity(a_json: &str, b_json: &str) -> f64 {
    let a: Vec<f64> = serde_json::from_str(a_json).unwrap_or_default();
    let b: Vec<f64> = serde_json::from_str(b_json).unwrap_or_default();
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

/// Batch cosine similarity: compare one query vector against many candidates.
/// Returns JSON array of {index, score} sorted by score descending.
#[wasm_bindgen]
pub fn batch_similarity(query_json: &str, candidates_json: &str, top_k: usize) -> String {
    let query: Vec<f64> = serde_json::from_str(query_json).unwrap_or_default();
    let candidates: Vec<Vec<f64>> = serde_json::from_str(candidates_json).unwrap_or_default();

    if query.is_empty() || candidates.is_empty() {
        return "[]".to_string();
    }

    let norm_q: f64 = query.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_q == 0.0 {
        return "[]".to_string();
    }

    let mut scores: Vec<(usize, f64)> = candidates
        .iter()
        .enumerate()
        .map(|(i, c)| {
            if c.len() != query.len() {
                return (i, 0.0);
            }
            let dot: f64 = query.iter().zip(c.iter()).map(|(a, b)| a * b).sum();
            let norm_c: f64 = c.iter().map(|x| x * x).sum::<f64>().sqrt();
            let sim = if norm_c > 0.0 {
                dot / (norm_q * norm_c)
            } else {
                0.0
            };
            (i, sim)
        })
        .collect();

    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scores.truncate(top_k);

    serde_json::to_string(
        &scores
            .iter()
            .map(|(i, s)| serde_json::json!({"index": i, "score": s}))
            .collect::<Vec<_>>(),
    )
    .unwrap_or_else(|_| "[]".to_string())
}

/// Full-text search: find substring matches in a list of texts.
/// Returns JSON array of matching indices.
#[wasm_bindgen]
pub fn text_search(query: &str, texts_json: &str) -> String {
    let texts: Vec<String> = serde_json::from_str(texts_json).unwrap_or_default();
    let query_lower = query.to_lowercase();

    let matches: Vec<usize> = texts
        .iter()
        .enumerate()
        .filter(|(_, t)| t.to_lowercase().contains(&query_lower))
        .map(|(i, _)| i)
        .collect();

    serde_json::to_string(&matches).unwrap_or_else(|_| "[]".to_string())
}

/// Check if WASM module is loaded
#[wasm_bindgen]
pub fn wasm_ready() -> bool {
    true
}

/// Get WASM version
#[wasm_bindgen]
pub fn wasm_version() -> String {
    "23.2.0".to_string()
}

// ── Re-exports from whitemagic-math (holographic 5D encoding) ───────────
// These are compiled into the same WASM binary via the wasm feature flag.

pub use whitemagic_math::holographic_encoder_5d::holographic_encode_single;
pub use whitemagic_math::holographic_encoder_5d::holographic_encode_batch;
pub use whitemagic_math::holographic_encoder_5d::Coordinate5D;

// ── Memory Store (browser-local, HashMap-backed) ────────────────────────

/// A memory record stored in the browser.
#[wasm_bindgen]
#[derive(Clone)]
pub struct WasmMemory {
    id: String,
    title: String,
    content: String,
    tags: Vec<String>,
    importance: f32,
    memory_type: String,
    created_at: String,
    updated_at: String,
}

#[wasm_bindgen]
impl WasmMemory {
    #[wasm_bindgen(constructor)]
    pub fn new(id: &str, title: &str, content: &str) -> WasmMemory {
        let now = js_sys::Date::new(&JsValue::from_f64(js_sys::Date::now())).to_iso_string().as_string().unwrap_or_default();
        WasmMemory {
            id: id.to_string(),
            title: title.to_string(),
            content: content.to_string(),
            tags: Vec::new(),
            importance: 0.5,
            memory_type: "long_term".to_string(),
            created_at: now.clone(),
            updated_at: now,
        }
    }

    #[wasm_bindgen(getter)]
    pub fn id(&self) -> String { self.id.clone() }

    #[wasm_bindgen(getter)]
    pub fn title(&self) -> String { self.title.clone() }

    #[wasm_bindgen(setter)]
    pub fn set_title(&mut self, v: String) { self.title = v; }

    #[wasm_bindgen(getter)]
    pub fn content(&self) -> String { self.content.clone() }

    #[wasm_bindgen(setter)]
    pub fn set_content(&mut self, v: String) { self.content = v; }

    #[wasm_bindgen(getter)]
    pub fn importance(&self) -> f32 { self.importance }

    #[wasm_bindgen(setter)]
    pub fn set_importance(&mut self, v: f32) { self.importance = v; }

    #[wasm_bindgen(getter)]
    pub fn memory_type(&self) -> String { self.memory_type.clone() }

    #[wasm_bindgen(getter)]
    pub fn created_at(&self) -> String { self.created_at.clone() }

    #[wasm_bindgen(getter)]
    pub fn updated_at(&self) -> String { self.updated_at.clone() }

    pub fn tags_json(&self) -> String {
        serde_json::to_string(&self.tags).unwrap_or_else(|_| "[]".to_string())
    }

    pub fn add_tag(&mut self, tag: &str) {
        if !self.tags.iter().any(|t| t == tag) {
            self.tags.push(tag.to_string());
        }
    }

    pub fn remove_tag(&mut self, tag: &str) {
        self.tags.retain(|t| t != tag);
    }

    pub fn to_json(&self) -> String {
        serde_json::json!({
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "importance": self.importance,
            "memory_type": self.memory_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }).to_string()
    }
}

/// In-browser memory store (HashMap-backed cache + IndexedDB persistence).
#[wasm_bindgen]
pub struct MemoryStore {
    memories: HashMap<String, WasmMemory>,
    next_id: u64,
    db_name: String,
}

#[wasm_bindgen]
impl MemoryStore {
    #[wasm_bindgen(constructor)]
    pub fn new() -> MemoryStore {
        MemoryStore {
            memories: HashMap::new(),
            next_id: 1,
            db_name: "whitemagic_memories".to_string(),
        }
    }

    /// Create a MemoryStore with a custom IndexedDB database name
    /// (useful for multi-user isolation).
    pub fn with_db_name(db_name: &str) -> MemoryStore {
        MemoryStore {
            memories: HashMap::new(),
            next_id: 1,
            db_name: db_name.to_string(),
        }
    }

    /// Create a new memory. Returns the assigned ID.
    pub fn create(&mut self, title: &str, content: &str, tags_json: &str) -> String {
        let id = format!("mem_{}", self.next_id);
        self.next_id += 1;

        let mut mem = WasmMemory::new(&id, title, content);
        if let Ok(tags) = serde_json::from_str::<Vec<String>>(tags_json) {
            for tag in tags {
                mem.add_tag(&tag);
            }
        }

        let id_out = id.clone();
        self.memories.insert(id, mem);
        id_out
    }

    /// Read a memory by ID. Returns JSON or empty string if not found.
    pub fn read(&self, id: &str) -> String {
        match self.memories.get(id) {
            Some(m) => m.to_json(),
            None => String::new(),
        }
    }

    /// Update a memory's content and/or title.
    pub fn update(&mut self, id: &str, title: &str, content: &str) -> bool {
        if let Some(mem) = self.memories.get_mut(id) {
            if !title.is_empty() {
                mem.set_title(title.to_string());
            }
            if !content.is_empty() {
                mem.set_content(content.to_string());
            }
            let now = js_sys::Date::new(&JsValue::from_f64(js_sys::Date::now())).to_iso_string().as_string().unwrap_or_default();
            mem.updated_at = now;
            true
        } else {
            false
        }
    }

    /// Delete a memory by ID.
    pub fn delete(&mut self, id: &str) -> bool {
        self.memories.remove(id).is_some()
    }

    /// Full-text search across title and content. Returns JSON array of memory IDs.
    pub fn search(&self, query: &str) -> String {
        let query_lower = query.to_lowercase();
        let results: Vec<&WasmMemory> = self.memories.values()
            .filter(|m| {
                m.title.to_lowercase().contains(&query_lower)
                    || m.content.to_lowercase().contains(&query_lower)
            })
            .collect();

        serde_json::to_string(
            &results.iter().map(|m| {
                serde_json::json!({
                    "id": m.id,
                    "title": m.title,
                    "importance": m.importance,
                    "snippet": m.content.chars().take(200).collect::<String>(),
                })
            }).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }

    /// Search by tag. Returns JSON array of memory IDs.
    pub fn search_by_tag(&self, tag: &str) -> String {
        let results: Vec<&WasmMemory> = self.memories.values()
            .filter(|m| m.tags.iter().any(|t| t == tag))
            .collect();

        serde_json::to_string(
            &results.iter().map(|m| m.id.clone()).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }

    /// List all memories, sorted by importance (descending).
    pub fn list(&self) -> String {
        let mut all: Vec<&WasmMemory> = self.memories.values().collect();
        all.sort_by(|a, b| b.importance.partial_cmp(&a.importance).unwrap_or(std::cmp::Ordering::Equal));

        serde_json::to_string(
            &all.iter().map(|m| {
                serde_json::json!({
                    "id": m.id,
                    "title": m.title,
                    "importance": m.importance,
                    "tags": m.tags,
                    "created_at": m.created_at,
                })
            }).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }

    /// Get count of stored memories.
    pub fn count(&self) -> usize {
        self.memories.len()
    }

    /// Export all memories as a JSON array (for backup/transfer).
    pub fn export_json(&self) -> String {
        let all: Vec<&WasmMemory> = self.memories.values().collect();
        serde_json::to_string(
            &all.iter().map(|m| m.to_json()).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }

    /// Import memories from a JSON array (merge into store).
    /// Returns count of memories imported.
    pub fn import_json(&mut self, json_str: &str) -> usize {
        match serde_json::from_str::<Vec<serde_json::Value>>(json_str) {
            Ok(items) => {
                let mut count = 0;
                for item in items {
                    let id = item.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    if id.is_empty() {
                        continue;
                    }
                    let title = item.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let content = item.get("content").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let importance = item.get("importance").and_then(|v| v.as_f64()).unwrap_or(0.5) as f32;
                    let tags: Vec<String> = item.get("tags")
                        .and_then(|v| v.as_array())
                        .map(|arr| arr.iter().filter_map(|t| t.as_str().map(String::from)).collect())
                        .unwrap_or_default();

                    let mut mem = WasmMemory::new(&id, &title, &content);
                    mem.set_importance(importance);
                    for tag in tags {
                        mem.add_tag(&tag);
                    }
                    self.memories.insert(id, mem);
                    count += 1;
                }
                count
            }
            Err(_) => 0,
        }
    }

    // ── IndexedDB persistence (async, browser-only) ───────────────

    /// JS helper: wrap an IDB request in a Promise.
    /// Called via Function to avoid Closure lifetime issues.
    fn idb_request_to_promise(request: &web_sys::IdbRequest) -> js_sys::Promise {
        let helper = js_sys::Function::new_with_args(
            "req",
            "return new Promise((resolve, reject) => { req.onsuccess = () => resolve(req.result); req.onerror = () => reject(req.error); });"
        );
        helper.call1(&JsValue::undefined(), request)
            .and_then(|v| v.dyn_into::<js_sys::Promise>())
            .unwrap_or_else(|_| js_sys::Promise::reject(&JsValue::from_str("failed to create IDB promise")))
    }

    /// JS helper: wrap an IDB transaction completion in a Promise.
    fn idb_transaction_to_promise(tx: &web_sys::IdbTransaction) -> js_sys::Promise {
        let helper = js_sys::Function::new_with_args(
            "tx",
            "return new Promise((resolve, reject) => { tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });"
        );
        helper.call1(&JsValue::undefined(), tx)
            .and_then(|v| v.dyn_into::<js_sys::Promise>())
            .unwrap_or_else(|_| js_sys::Promise::reject(&JsValue::from_str("failed to create transaction promise")))
    }

    /// JS helper: open an IDB database with object store creation.
    fn idb_open_db(db_name: &str) -> Result<js_sys::Promise, JsValue> {
        let window = web_sys::window().ok_or_else(|| JsValue::from_str("no window"))?;
        let factory = window.indexed_db()
            .map_err(|_| JsValue::from_str("indexedDB unavailable"))?
            .ok_or_else(|| JsValue::from_str("indexedDB not supported"))?;

        let open_request = factory.open(db_name)?;

        // Set up onupgradeneeded via a Closure
        let upgrade_closure = Closure::wrap(Box::new(|event: web_sys::IdbVersionChangeEvent| {
            let target = match event.target() {
                Some(t) => t,
                None => return,
            };
            let request: web_sys::IdbOpenDbRequest = target.unchecked_into();
            if let Ok(db_val) = request.result() {
                let db: web_sys::IdbDatabase = db_val.into();
                let stores = db.object_store_names();
                if !stores.contains("memories") {
                    let _ = db.create_object_store("memories");
                }
            }
        }) as Box<dyn FnMut(web_sys::IdbVersionChangeEvent)>);
        open_request.set_onupgradeneeded(Some(upgrade_closure.as_ref().unchecked_ref()));
        upgrade_closure.forget();

        Ok(Self::idb_request_to_promise(&open_request))
    }

    /// Hydrate the in-memory cache from IndexedDB.
    #[wasm_bindgen]
    pub async fn hydrate(&mut self) -> Result<u32, JsValue> {
        let promise = Self::idb_open_db(&self.db_name)?;
        let db_result = wasm_bindgen_futures::JsFuture::from(promise).await?;
        let db: web_sys::IdbDatabase = db_result.into();

        let tx = db.transaction_with_str_and_mode("memories", web_sys::IdbTransactionMode::Readonly)?;
        let store = tx.object_store("memories")?;
        let get_all = store.get_all()?;

        let js_values = wasm_bindgen_futures::JsFuture::from(Self::idb_request_to_promise(&get_all)).await?;
        db.close();

        let arr = js_sys::Array::unchecked_from_js(js_values);
        let mut count = 0u32;
        for i in 0..arr.length() {
            let js_val: JsValue = arr.get(i);
            if let Some(json_str) = js_val.as_string() {
                if let Ok(item) = serde_json::from_str::<serde_json::Value>(&json_str) {
                    let id = item.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    if id.is_empty() { continue; }
                    let title = item.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let content = item.get("content").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let importance = item.get("importance").and_then(|v| v.as_f64()).unwrap_or(0.5) as f32;
                    let tags: Vec<String> = item.get("tags")
                        .and_then(|v| v.as_array())
                        .map(|a| a.iter().filter_map(|t| t.as_str().map(String::from)).collect())
                        .unwrap_or_default();
                    let created_at = item.get("created_at").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let updated_at = item.get("updated_at").and_then(|v| v.as_str()).unwrap_or("").to_string();

                    let mut mem = WasmMemory::new(&id, &title, &content);
                    mem.set_importance(importance);
                    for tag in &tags { mem.add_tag(tag); }
                    mem.created_at = created_at;
                    mem.updated_at = updated_at;

                    if let Some(n) = id.strip_prefix("mem_") {
                        if let Ok(parsed) = n.parse::<u64>() {
                            if parsed >= self.next_id { self.next_id = parsed + 1; }
                        }
                    }

                    self.memories.insert(id, mem);
                    count += 1;
                }
            }
        }

        Ok(count)
    }

    /// Persist all memories to IndexedDB (full sync).
    #[wasm_bindgen]
    pub async fn persist(&self) -> Result<u32, JsValue> {
        let promise = Self::idb_open_db(&self.db_name)?;
        let db_result = wasm_bindgen_futures::JsFuture::from(promise).await?;
        let db: web_sys::IdbDatabase = db_result.into();

        let tx = db.transaction_with_str_and_mode("memories", web_sys::IdbTransactionMode::Readwrite)?;
        let store = tx.object_store("memories")?;
        store.clear()?;

        let mut count = 0u32;
        for (id, mem) in &self.memories {
            let json = mem.to_json();
            store.put_with_key(&JsValue::from_str(&json), &JsValue::from_str(id))?;
            count += 1;
        }

        let _ = wasm_bindgen_futures::JsFuture::from(Self::idb_transaction_to_promise(&tx)).await;
        db.close();

        Ok(count)
    }

    /// Persist a single memory to IndexedDB.
    #[wasm_bindgen]
    pub async fn persist_one(&self, id: &str) -> Result<bool, JsValue> {
        let mem = match self.memories.get(id) {
            Some(m) => m,
            None => return Ok(false),
        };

        let promise = Self::idb_open_db(&self.db_name)?;
        let db_result = wasm_bindgen_futures::JsFuture::from(promise).await?;
        let db: web_sys::IdbDatabase = db_result.into();

        let tx = db.transaction_with_str_and_mode("memories", web_sys::IdbTransactionMode::Readwrite)?;
        let store = tx.object_store("memories")?;
        let json = mem.to_json();
        store.put_with_key(&JsValue::from_str(&json), &JsValue::from_str(id))?;

        let _ = wasm_bindgen_futures::JsFuture::from(Self::idb_transaction_to_promise(&tx)).await;
        db.close();

        Ok(true)
    }

    /// Delete a single memory from IndexedDB.
    #[wasm_bindgen]
    pub async fn delete_persisted(&self, id: &str) -> Result<bool, JsValue> {
        let promise = Self::idb_open_db(&self.db_name)?;
        let db_result = wasm_bindgen_futures::JsFuture::from(promise).await?;
        let db: web_sys::IdbDatabase = db_result.into();

        let tx = db.transaction_with_str_and_mode("memories", web_sys::IdbTransactionMode::Readwrite)?;
        let store = tx.object_store("memories")?;
        store.delete(&JsValue::from_str(id))?;

        let _ = wasm_bindgen_futures::JsFuture::from(Self::idb_transaction_to_promise(&tx)).await;
        db.close();

        Ok(true)
    }

    /// Get the IndexedDB database name.
    #[wasm_bindgen(getter)]
    pub fn db_name(&self) -> String {
        self.db_name.clone()
    }
}

// ── Dharma Rule Engine (browser-local governance) ──────────────────────

/// A Dharma rule for content governance.
#[wasm_bindgen]
#[derive(Clone)]
pub struct DharmaRule {
    id: String,
    pattern: String,
    action: String,
    message: String,
}

#[wasm_bindgen]
impl DharmaRule {
    #[wasm_bindgen(constructor)]
    pub fn new(id: &str, pattern: &str, action: &str, message: &str) -> DharmaRule {
        DharmaRule {
            id: id.to_string(),
            pattern: pattern.to_string(),
            action: action.to_string(),
            message: message.to_string(),
        }
    }

    #[wasm_bindgen(getter)]
    pub fn id(&self) -> String { self.id.clone() }
    #[wasm_bindgen(getter)]
    pub fn pattern(&self) -> String { self.pattern.clone() }
    #[wasm_bindgen(getter)]
    pub fn action(&self) -> String { self.action.clone() }
    #[wasm_bindgen(getter)]
    pub fn message(&self) -> String { self.message.clone() }
}

/// Dharma evaluation result.
#[wasm_bindgen]
pub struct DharmaResult {
    allowed: bool,
    matched_rule: String,
    message: String,
    evaluated_rules: u32,
}

#[wasm_bindgen]
impl DharmaResult {
    #[wasm_bindgen(getter)]
    pub fn allowed(&self) -> bool { self.allowed }
    #[wasm_bindgen(getter)]
    pub fn matched_rule(&self) -> String { self.matched_rule.clone() }
    #[wasm_bindgen(getter)]
    pub fn message(&self) -> String { self.message.clone() }
    #[wasm_bindgen(getter)]
    pub fn evaluated_rules(&self) -> u32 { self.evaluated_rules }
}

/// Dharma rule engine for browser-local governance.
#[wasm_bindgen]
pub struct DharmaEngine {
    rules: Vec<DharmaRule>,
}

#[wasm_bindgen]
impl DharmaEngine {
    #[wasm_bindgen(constructor)]
    pub fn new() -> DharmaEngine {
        let mut engine = DharmaEngine { rules: Vec::new() };

        // Default safety rules
        engine.add_rule(DharmaRule::new(
            "no_harm", "kill|self.harm|suicide|hurt myself",
            "block", "I can't help with that. If you're in crisis, please contact a crisis helpline.",
        ));
        engine.add_rule(DharmaRule::new(
            "no_csam", "child|minor|underage",
            "block", "This topic is not permitted.",
        ));
        engine.add_rule(DharmaRule::new(
            "no_medical", "diagnose|prescribe|medical advice|treat.*illness",
            "warn", "I'm not a medical professional. Please consult a healthcare provider.",
        ));
        engine.add_rule(DharmaRule::new(
            "no_financial", "investment advice|financial advice|buy.*stock|trade.*crypto",
            "warn", "This is not financial advice. Please consult a qualified advisor.",
        ));

        engine
    }

    pub fn add_rule(&mut self, rule: DharmaRule) {
        self.rules.push(rule);
    }

    pub fn remove_rule(&mut self, id: &str) -> bool {
        let before = self.rules.len();
        self.rules.retain(|r| r.id != id);
        self.rules.len() != before
    }

    /// Evaluate input text against all rules.
    pub fn evaluate(&self, text: &str) -> DharmaResult {
        let text_lower = text.to_lowercase();
        let mut evaluated = 0u32;

        for rule in &self.rules {
            evaluated += 1;
            let keywords: Vec<&str> = rule.pattern.split('|').collect();
            let matches = keywords.iter().any(|kw| {
                let kw = kw.trim();
                if kw.is_empty() { return false; }
                text_lower.contains(kw)
            });

            if matches {
                let allowed = rule.action != "block";
                return DharmaResult {
                    allowed,
                    matched_rule: rule.id.clone(),
                    message: rule.message.clone(),
                    evaluated_rules: evaluated,
                };
            }
        }

        DharmaResult {
            allowed: true,
            matched_rule: String::new(),
            message: String::new(),
            evaluated_rules: evaluated,
        }
    }

    pub fn rule_count(&self) -> usize {
        self.rules.len()
    }

    /// List all rule IDs as JSON array.
    pub fn list_rules(&self) -> String {
        serde_json::to_string(
            &self.rules.iter().map(|r| {
                serde_json::json!({
                    "id": r.id,
                    "pattern": r.pattern,
                    "action": r.action,
                    "message": r.message,
                })
            }).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }
}

// ── Karma Ledger (browser-local, append-only) ──────────────────────────

/// A karma ledger entry.
#[wasm_bindgen]
#[derive(Clone)]
pub struct KarmaEntry {
    id: String,
    action: String,
    delta: f32,
    timestamp: String,
    description: String,
}

#[wasm_bindgen]
impl KarmaEntry {
    #[wasm_bindgen(getter)]
    pub fn id(&self) -> String { self.id.clone() }
    #[wasm_bindgen(getter)]
    pub fn action(&self) -> String { self.action.clone() }
    #[wasm_bindgen(getter)]
    pub fn delta(&self) -> f32 { self.delta }
    #[wasm_bindgen(getter)]
    pub fn timestamp(&self) -> String { self.timestamp.clone() }
    #[wasm_bindgen(getter)]
    pub fn description(&self) -> String { self.description.clone() }
}

/// Append-only karma ledger.
#[wasm_bindgen]
pub struct KarmaLedger {
    entries: Vec<KarmaEntry>,
    balance: f32,
    next_id: u64,
}

#[wasm_bindgen]
impl KarmaLedger {
    #[wasm_bindgen(constructor)]
    pub fn new() -> KarmaLedger {
        KarmaLedger {
            entries: Vec::new(),
            balance: 0.0,
            next_id: 1,
        }
    }

    /// Record a karma action. Returns the entry ID.
    pub fn record(&mut self, action: &str, delta: f32, description: &str) -> String {
        let id = format!("karma_{}", self.next_id);
        self.next_id += 1;
        let ts = js_sys::Date::new(&JsValue::from_f64(js_sys::Date::now())).to_iso_string().as_string().unwrap_or_default();

        let entry = KarmaEntry {
            id: id.clone(),
            action: action.to_string(),
            delta,
            timestamp: ts,
            description: description.to_string(),
        };

        self.balance += delta;
        self.entries.push(entry);
        id
    }

    /// Get current karma balance.
    pub fn balance(&self) -> f32 {
        self.balance
    }

    /// Get total number of entries.
    pub fn count(&self) -> usize {
        self.entries.len()
    }

    /// Get recent entries as JSON (last N entries).
    pub fn recent_json(&self, n: usize) -> String {
        let start = if self.entries.len() > n { self.entries.len() - n } else { 0 };
        let recent = &self.entries[start..];

        serde_json::to_string(
            &recent.iter().map(|e| {
                serde_json::json!({
                    "id": e.id,
                    "action": e.action,
                    "delta": e.delta,
                    "timestamp": e.timestamp,
                    "description": e.description,
                })
            }).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }

    /// Export all entries as JSON (for backup).
    pub fn export_json(&self) -> String {
        serde_json::to_string(
            &self.entries.iter().map(|e| {
                serde_json::json!({
                    "id": e.id,
                    "action": e.action,
                    "delta": e.delta,
                    "timestamp": e.timestamp,
                    "description": e.description,
                })
            }).collect::<Vec<_>>()
        ).unwrap_or_else(|_| "[]".to_string())
    }
}

// ── Gnosis Snapshot (self-introspection) ───────────────────────────────

/// Gnosis snapshot — system self-awareness summary.
#[wasm_bindgen]
pub struct GnosisSnapshot {
    memory_count: usize,
    karma_balance: f32,
    karma_entries: usize,
    dharma_rules: usize,
    edge_queries: u32,
    edge_local: u32,
    edge_tokens_saved: u32,
}

#[wasm_bindgen]
impl GnosisSnapshot {
    #[wasm_bindgen(getter)]
    pub fn memory_count(&self) -> usize { self.memory_count }
    #[wasm_bindgen(getter)]
    pub fn karma_balance(&self) -> f32 { self.karma_balance }
    #[wasm_bindgen(getter)]
    pub fn karma_entries(&self) -> usize { self.karma_entries }
    #[wasm_bindgen(getter)]
    pub fn dharma_rules(&self) -> usize { self.dharma_rules }
    #[wasm_bindgen(getter)]
    pub fn edge_queries(&self) -> u32 { self.edge_queries }
    #[wasm_bindgen(getter)]
    pub fn edge_local(&self) -> u32 { self.edge_local }
    #[wasm_bindgen(getter)]
    pub fn edge_tokens_saved(&self) -> u32 { self.edge_tokens_saved }

    /// Serialize to JSON.
    pub fn to_json(&self) -> String {
        serde_json::json!({
            "memory_count": self.memory_count,
            "karma_balance": self.karma_balance,
            "karma_entries": self.karma_entries,
            "dharma_rules": self.dharma_rules,
            "edge_queries": self.edge_queries,
            "edge_local": self.edge_local,
            "edge_tokens_saved": self.edge_tokens_saved,
            "maturity_stage": self._maturity_stage(),
        }).to_string()
    }

    fn _maturity_stage(&self) -> String {
        if self.memory_count < 10 {
            "seedling".to_string()
        } else if self.memory_count < 100 {
            "growing".to_string()
        } else if self.memory_count < 500 {
            "established".to_string()
        } else {
            "mature".to_string()
        }
    }
}

/// Generate a Gnosis snapshot from the current system state.
#[wasm_bindgen]
pub fn gnosis_snapshot(
    store: &MemoryStore,
    karma: &KarmaLedger,
    dharma: &DharmaEngine,
    engine: &EdgeEngine,
) -> GnosisSnapshot {
    let stats = engine.get_stats();
    let parsed: serde_json::Value = serde_json::from_str(&stats).unwrap_or_default();
    let queries = parsed.get("queries").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let local = parsed.get("local").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let tokens = parsed.get("tokens_saved").and_then(|v| v.as_u64()).unwrap_or(0) as u32;

    GnosisSnapshot {
        memory_count: MemoryStore::count(store),
        karma_balance: karma.balance(),
        karma_entries: KarmaLedger::count(karma),
        dharma_rules: dharma.rule_count(),
        edge_queries: queries,
        edge_local: local,
        edge_tokens_saved: tokens,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_inference() {
        let mut engine = EdgeEngine::new();
        let result = engine.infer("What version?");
        assert!(result.answer.contains("23.2.0"));
        assert!(!result.needs_cloud);
    }

    #[test]
    fn test_caching() {
        let mut engine = EdgeEngine::new();
        engine.infer("version");
        let result = engine.infer("version");
        assert_eq!(result.method, "cache");
    }

    #[test]
    fn test_no_match() {
        let mut engine = EdgeEngine::new();
        let result = engine.infer("random nonsense xyz");
        assert!(result.needs_cloud);
        assert!(result.confidence < 0.5);
    }

    #[test]
    fn test_stats() {
        let mut engine = EdgeEngine::new();
        engine.infer("version");
        engine.infer("gardens");
        assert_eq!(engine.stats_queries, 2);
        assert_eq!(engine.stats_local, 2);
    }

    #[test]
    fn test_cosine_similarity_identical() {
        let a = "[1.0, 0.0, 0.0]";
        let b = "[1.0, 0.0, 0.0]";
        let sim = cosine_similarity(a, b);
        assert!((sim - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_similarity_orthogonal() {
        let a = "[1.0, 0.0]";
        let b = "[0.0, 1.0]";
        let sim = cosine_similarity(a, b);
        assert!(sim.abs() < 1e-6);
    }

    #[test]
    fn test_batch_similarity() {
        let query = "[1.0, 0.0, 0.0]";
        let candidates = "[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0]]";
        let result = batch_similarity(query, candidates, 2);
        assert!(result.contains("\"index\":0")); // First candidate should be best match
    }

    #[test]
    fn test_text_search() {
        let texts = r#"["Hello world", "Goodbye moon", "Hello again"]"#;
        let result = text_search("hello", texts);
        assert!(result.contains("0"));
        assert!(result.contains("2"));
        assert!(!result.contains("1"));
    }

    #[test]
    fn test_holographic_encode() {
        let mem = r#"{"id":"test-1","content":"algorithm and function","importance":0.8,"access_count":5,"age_days":30.0,"galactic_distance":0.2,"garden":"courage","tags":["rust","wasm"]}"#;
        let result = holographic_encode_single(mem);
        assert!(result.is_ok());
        let json = result.unwrap();
        assert!(json.contains("\"x\""));
        assert!(json.contains("\"y\""));
        assert!(json.contains("\"z\""));
        assert!(json.contains("\"w\""));
        assert!(json.contains("\"v\""));
    }

    // ── MemoryStore tests ──────────────────────────────────────────

    #[test]
    fn test_memory_store_crud() {
        let mut store = MemoryStore::new();
        assert_eq!(store.count(), 0);

        let id = store.create("Test Title", "Test content", r#"["tag1","tag2"]"#);
        assert_eq!(store.count(), 1);
        assert!(id.starts_with("mem_"));

        let mem_json = store.read(&id);
        assert!(mem_json.contains("Test Title"));
        assert!(mem_json.contains("Test content"));

        assert!(store.update(&id, "Updated Title", "Updated content"));
        let updated = store.read(&id);
        assert!(updated.contains("Updated Title"));

        assert!(store.delete(&id));
        assert_eq!(store.count(), 0);
        assert!(store.read(&id).is_empty());
    }

    #[test]
    fn test_memory_store_search() {
        let mut store = MemoryStore::new();
        store.create("Rust Programming", "Learn Rust systems language", "[]");
        store.create("Python Guide", "Python is great for AI", "[]");
        store.create("Rust WASM", "Compile Rust to WebAssembly", "[]");

        let results = store.search("rust");
        assert!(results.contains("Rust Programming"));
        assert!(results.contains("Rust WASM"));
        assert!(!results.contains("Python Guide"));
    }

    #[test]
    fn test_memory_store_tag_search() {
        let mut store = MemoryStore::new();
        store.create("Memory 1", "Content 1", r#"["important","work"]"#);
        store.create("Memory 2", "Content 2", r#"["personal"]"#);
        store.create("Memory 3", "Content 3", r#"["important","todo"]"#);

        let results = store.search_by_tag("important");
        assert!(results.contains("mem_1"));
        assert!(results.contains("mem_3"));
        assert!(!results.contains("mem_2"));
    }

    #[test]
    fn test_memory_store_export_import() {
        let mut store = MemoryStore::new();
        store.create("Export Test", "Content for export", r#"["test"]"#);

        let exported = store.export_json();
        assert!(exported.contains("Export Test"));

        let mut store2 = MemoryStore::new();
        let count = store2.import_json(&exported);
        assert_eq!(count, 1);
        assert_eq!(store2.count(), 1);
    }

    #[test]
    fn test_memory_store_with_db_name() {
        let store = MemoryStore::with_db_name("user_alice_memories");
        assert_eq!(store.db_name(), "user_alice_memories");
        assert_eq!(store.count(), 0);

        let default_store = MemoryStore::new();
        assert_eq!(default_store.db_name(), "whitemagic_memories");
    }

    // ── DharmaEngine tests ─────────────────────────────────────────

    #[test]
    fn test_dharma_engine_defaults() {
        let engine = DharmaEngine::new();
        assert!(engine.rule_count() >= 4);
    }

    #[test]
    fn test_dharma_block_rule() {
        let engine = DharmaEngine::new();
        let result = engine.evaluate("I want to kill myself");
        assert!(!result.allowed);
        assert_eq!(result.matched_rule, "no_harm");
        assert!(!result.message.is_empty());
    }

    #[test]
    fn test_dharma_warn_rule() {
        let engine = DharmaEngine::new();
        let result = engine.evaluate("Can you diagnose my illness?");
        assert!(result.allowed);
        assert_eq!(result.matched_rule, "no_medical");
    }

    #[test]
    fn test_dharma_allowed_text() {
        let engine = DharmaEngine::new();
        let result = engine.evaluate("Tell me about WhiteMagic memory system");
        assert!(result.allowed);
        assert!(result.matched_rule.is_empty());
    }

    #[test]
    fn test_dharma_add_remove_rule() {
        let mut engine = DharmaEngine::new();
        let initial = engine.rule_count();

        engine.add_rule(DharmaRule::new("custom", "forbidden|banned", "block", "Not allowed."));
        assert_eq!(engine.rule_count(), initial + 1);

        assert!(engine.remove_rule("custom"));
        assert_eq!(engine.rule_count(), initial);
    }

    // ── KarmaLedger tests ──────────────────────────────────────────

    #[test]
    fn test_karma_ledger_record() {
        let mut ledger = KarmaLedger::new();
        assert_eq!(ledger.count(), 0);
        assert!((ledger.balance() - 0.0).abs() < 1e-6);

        let id1 = ledger.record("help_user", 1.0, "Helped a user with setup");
        assert!(id1.starts_with("karma_"));
        assert_eq!(ledger.count(), 1);
        assert!((ledger.balance() - 1.0).abs() < 1e-6);

        let id2 = ledger.record("spam", -0.5, "Posted spam content");
        assert_ne!(id1, id2);
        assert_eq!(ledger.count(), 2);
        assert!((ledger.balance() - 0.5).abs() < 1e-6);
    }

    #[test]
    fn test_karma_ledger_recent() {
        let mut ledger = KarmaLedger::new();
        for i in 0..10 {
            ledger.record("action", 0.1 * i as f32, &format!("Action {}", i));
        }

        let recent = ledger.recent_json(3);
        assert!(recent.contains("Action 7"));
        assert!(recent.contains("Action 8"));
        assert!(recent.contains("Action 9"));
        assert!(!recent.contains("Action 0"));
    }

    #[test]
    fn test_karma_ledger_export() {
        let mut ledger = KarmaLedger::new();
        ledger.record("test_action", 1.0, "Test description");

        let exported = ledger.export_json();
        assert!(exported.contains("test_action"));
        assert!(exported.contains("Test description"));
    }

    // ── Gnosis tests ───────────────────────────────────────────────

    #[test]
    fn test_gnosis_snapshot() {
        let mut store = MemoryStore::new();
        store.create("Test", "Content", "[]");

        let mut karma = KarmaLedger::new();
        karma.record("test", 1.0, "Test karma");

        let dharma = DharmaEngine::new();
        let engine = EdgeEngine::new();

        let snapshot = gnosis_snapshot(&store, &karma, &dharma, &engine);
        assert_eq!(snapshot.memory_count(), 1);
        assert_eq!(snapshot.karma_entries(), 1);
        assert!((snapshot.karma_balance() - 1.0).abs() < 1e-6);
        assert!(snapshot.dharma_rules() >= 4);

        let json = snapshot.to_json();
        assert!(json.contains("memory_count"));
        assert!(json.contains("karma_balance"));
        assert!(json.contains("maturity_stage"));
    }

    #[test]
    fn test_gnosis_maturity_stages() {
        let store = MemoryStore::new();
        let karma = KarmaLedger::new();
        let dharma = DharmaEngine::new();
        let engine = EdgeEngine::new();

        let snapshot = gnosis_snapshot(&store, &karma, &dharma, &engine);
        let json = snapshot.to_json();
        assert!(json.contains("seedling"));
    }
}
