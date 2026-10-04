//! System 0.5 retrieval organ for WhiteMagic Gen3.
//!
//! Maps a state to a ranked shortlist of named candidates using a local static
//! embedding table (Model2Vec). Pure Rust, no network, no threads, caller-driven;
//! the substrate is never touched.

use std::collections::hash_map::DefaultHasher;
use std::fmt;
use std::hash::{Hash, Hasher};
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Instant;

use model2vec_rs::model::StaticModel;
use serde_json::{Value, json};

/// Environment variable overriding the checkpoint directory.
pub const ENV_MODEL: &str = "WM_GEN3_SYSTEM05_MODEL";

/// Environment variable overriding the default route catalog path.
pub const ENV_CATALOG: &str = "WM_GEN3_ROUTES_CATALOG";

/// Default enriched catalog file name.
pub const DEFAULT_CATALOG_NAME: &str = "routes_v9_enriched.json";

/// System 0.5 organ error.
#[derive(Debug)]
pub enum Error {
    /// No usable static-embedding checkpoint was found.
    ModelDirNotFound(String),
    /// The checkpoint failed to load.
    Load(String),
    /// The candidate set was malformed.
    BadRoutes(String),
    /// Embedding or ranking failed.
    Inference(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::ModelDirNotFound(paths) => {
                write!(
                    f,
                    "no static-embedding checkpoint found (looked in: {paths})"
                )
            }
            Error::Load(msg) => write!(f, "failed to load static embeddings: {msg}"),
            Error::BadRoutes(msg) => write!(f, "invalid candidate set: {msg}"),
            Error::Inference(msg) => write!(f, "embedding failed: {msg}"),
        }
    }
}

impl std::error::Error for Error {}

/// One ranked candidate.
#[derive(Debug, Clone)]
pub struct Candidate {
    pub name: String,
    pub score: f32,
}

/// Rank pre-normalized candidates by cosine similarity to a pre-normalized query.
#[must_use]
pub fn rank_candidates(
    query: &[f32],
    candidates: &[Vec<f32>],
    names: &[String],
    k: usize,
) -> Vec<Candidate> {
    let mut scored: Vec<(usize, f32)> = candidates
        .iter()
        .enumerate()
        .map(|(index, vector)| {
            let dot = query
                .iter()
                .zip(vector.iter())
                .map(|(a, b)| a * b)
                .sum::<f32>();
            (index, dot)
        })
        .collect();
    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored.truncate(k.min(scored.len()));
    scored
        .into_iter()
        .map(|(index, score)| Candidate {
            name: names[index].clone(),
            score,
        })
        .collect()
}

/// Rank routes by the maximum similarity across each route's utterances.
#[must_use]
pub fn rank_route_blocks(
    query: &[f32],
    vectors: &[Vec<f32>],
    ranges: &[(usize, usize)],
    names: &[String],
    k: usize,
) -> Vec<Candidate> {
    let mut scored: Vec<(usize, f32)> = ranges
        .iter()
        .enumerate()
        .map(|(route, &(start, end))| {
            let best = vectors[start..end]
                .iter()
                .map(|vector| {
                    query
                        .iter()
                        .zip(vector.iter())
                        .map(|(a, b)| a * b)
                        .sum::<f32>()
                })
                .fold(f32::NEG_INFINITY, f32::max);
            (route, best)
        })
        .collect();
    scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scored.truncate(k.min(scored.len()));
    scored
        .into_iter()
        .map(|(index, score)| Candidate {
            name: names[index].clone(),
            score,
        })
        .collect()
}

#[must_use]
pub fn l2_normalize(mut vector: Vec<f32>) -> Vec<f32> {
    let norm = vector.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for value in &mut vector {
            *value /= norm;
        }
    }
    vector
}

struct CatalogCache {
    digest: u64,
    names: Vec<String>,
    ranges: Vec<(usize, usize)>,
    vectors: Vec<Vec<f32>>,
}

/// Lazily loaded static-embedding retrieval organ.
pub struct System05 {
    model_dir: PathBuf,
    model: Mutex<Option<StaticModel>>,
    catalog: Mutex<Option<CatalogCache>>,
}

impl System05 {
    /// Create an organ bound to a checkpoint directory.
    #[must_use]
    pub fn new(model_dir: impl Into<PathBuf>) -> Self {
        Self {
            model_dir: model_dir.into(),
            model: Mutex::new(None),
            catalog: Mutex::new(None),
        }
    }

    /// Resolve the checkpoint directory: explicit path, then
    /// `WM_GEN3_SYSTEM05_MODEL`, then the canonical data dir, then `~/tools`.
    pub fn resolve_model_dir(explicit: Option<PathBuf>) -> Result<PathBuf, Error> {
        let mut candidates = Vec::new();
        if let Some(path) = explicit {
            candidates.push(path);
        } else {
            if let Ok(env) = std::env::var(ENV_MODEL) {
                if !env.is_empty() {
                    candidates.push(PathBuf::from(env));
                }
            }
            if let Some(home) = std::env::var_os("HOME") {
                let home = PathBuf::from(home);
                candidates.push(home.join(".local/share/whitemagic/system05/potion-base-32M"));
                candidates.push(home.join("tools/system05/potion-base-32M"));
                candidates.push(home.join(".local/share/whitemagic/system05/potion-base-8M"));
                candidates.push(home.join("tools/system05/potion-base-8M"));
            }
        }
        for candidate in &candidates {
            if candidate.join("model.safetensors").is_file()
                && candidate.join("tokenizer.json").is_file()
                && candidate.join("config.json").is_file()
            {
                return Ok(candidate.clone());
            }
        }
        let looked = candidates
            .iter()
            .map(|path| path.display().to_string())
            .collect::<Vec<_>>()
            .join(", ");
        Err(Error::ModelDirNotFound(looked))
    }

    /// Resolve a route-catalog JSON path: explicit path, then
    /// `WM_GEN3_ROUTES_CATALOG`, then the canonical data dir, then `~/tools`,
    /// then `./catalogs`.
    pub fn resolve_catalog_path(explicit: Option<PathBuf>) -> Result<PathBuf, Error> {
        let mut candidates = Vec::new();
        if let Some(path) = explicit {
            candidates.push(path);
        } else {
            if let Ok(env) = std::env::var(ENV_CATALOG) {
                if !env.is_empty() {
                    candidates.push(PathBuf::from(env));
                }
            }
            if let Some(home) = std::env::var_os("HOME") {
                let home = PathBuf::from(home);
                candidates.push(
                    home.join(".local/share/whitemagic/system05")
                        .join(DEFAULT_CATALOG_NAME),
                );
                candidates.push(home.join("tools/system05").join(DEFAULT_CATALOG_NAME));
            }
            candidates.push(PathBuf::from("catalogs").join(DEFAULT_CATALOG_NAME));
        }
        for candidate in &candidates {
            if candidate.is_file() {
                return Ok(candidate.clone());
            }
        }
        let looked = candidates
            .iter()
            .map(|path| path.display().to_string())
            .collect::<Vec<_>>()
            .join(", ");
        Err(Error::BadRoutes(format!(
            "no route catalog found (looked in: {looked})"
        )))
    }

    /// Checkpoint directory this organ is bound to.
    #[must_use]
    pub fn model_dir(&self) -> &std::path::Path {
        &self.model_dir
    }

    /// True once the checkpoint has been loaded.
    #[must_use]
    pub fn is_loaded(&self) -> bool {
        self.model
            .lock()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Load the checkpoint if it is not already resident.
    pub fn ensure_loaded(&self) -> Result<(), Error> {
        let mut guard = self
            .model
            .lock()
            .map_err(|_| Error::Load("system05 lock poisoned".to_string()))?;
        if guard.is_none() {
            let loaded = StaticModel::from_pretrained(&self.model_dir, None, Some(true), None)
                .map_err(|e| Error::Load(e.to_string()))?;
            *guard = Some(loaded);
        }
        Ok(())
    }

    /// Drop the resident checkpoint and catalog cache.
    pub fn unload(&self) {
        if let Ok(mut guard) = self.model.lock() {
            *guard = None;
        }
        if let Ok(mut catalog) = self.catalog.lock() {
            *catalog = None;
        }
    }

    /// Encode a single text into a normalized embedding vector.
    pub fn encode_single(&self, text: &str) -> Result<Vec<f32>, Error> {
        self.ensure_loaded()?;
        let model = self
            .model
            .lock()
            .map_err(|_| Error::Inference("system05 lock poisoned".to_string()))?;
        let model = model
            .as_ref()
            .ok_or_else(|| Error::Inference("model not loaded".to_string()))?;
        Ok(l2_normalize(model.encode_single(text)))
    }

    /// Encode a batch of texts into normalized embedding vectors.
    pub fn encode_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>, Error> {
        self.ensure_loaded()?;
        let model = self
            .model
            .lock()
            .map_err(|_| Error::Inference("system05 lock poisoned".to_string()))?;
        let model = model
            .as_ref()
            .ok_or_else(|| Error::Inference("model not loaded".to_string()))?;
        let encoded = model.encode(texts);
        Ok(encoded.into_iter().map(l2_normalize).collect())
    }

    /// Rank candidate routes for a state and return a shortlist report.
    /// Rank candidate routes for a state and return a shortlist report.
    ///
    /// `routes` is an object `{name: description}`, an object
    /// `{name: [utterances...]}`, or an array of route names. Routes with
    /// multiple utterances are scored by their best-matching utterance
    /// (max-over-utterances).
    pub fn shortlist(&self, state: &str, routes: &Value, k: usize) -> Result<Value, Error> {
        let parsed = parse_routes(routes)?;
        let names: Vec<String> = parsed.iter().map(|(name, _)| name.clone()).collect();
        let mut texts: Vec<String> = Vec::new();
        let mut ranges: Vec<(usize, usize)> = Vec::with_capacity(names.len());
        for (name, utterances) in &parsed {
            let start = texts.len();
            if utterances.is_empty() {
                texts.push(name.clone());
            } else {
                for utterance in utterances {
                    if utterance.is_empty() {
                        texts.push(name.clone());
                    } else {
                        texts.push(format!("{name} — {utterance}"));
                    }
                }
            }
            ranges.push((start, texts.len()));
        }

        let mut hasher = DefaultHasher::new();
        names.hash(&mut hasher);
        texts.hash(&mut hasher);
        let digest = hasher.finish();

        self.ensure_loaded()?;
        let started = Instant::now();
        let model = self
            .model
            .lock()
            .map_err(|_| Error::Inference("system05 lock poisoned".to_string()))?;
        let model = model
            .as_ref()
            .ok_or_else(|| Error::Inference("model not loaded".to_string()))?;

        let query = l2_normalize(model.encode_single(state));

        let vectors = {
            let mut catalog = self
                .catalog
                .lock()
                .map_err(|_| Error::Inference("catalog lock poisoned".to_string()))?;
            let hit = catalog.as_ref().filter(|cache| {
                cache.digest == digest && cache.names == names && cache.ranges == ranges
            });
            match hit {
                Some(cache) => cache.vectors.clone(),
                None => {
                    let encoded = model.encode(&texts);
                    let vectors: Vec<Vec<f32>> = encoded.into_iter().map(l2_normalize).collect();
                    *catalog = Some(CatalogCache {
                        digest,
                        names: names.clone(),
                        ranges: ranges.clone(),
                        vectors: vectors.clone(),
                    });
                    vectors
                }
            }
        };

        let ranked = rank_route_blocks(&query, &vectors, &ranges, &names, k.max(1));
        let margin = if ranked.len() > 1 {
            ranked[0].score - ranked[1].score
        } else {
            ranked.first().map_or(0.0, |c| c.score)
        };
        let latency_ms = started.elapsed().as_secs_f64() * 1000.0;

        Ok(json!({
            "status": "success",
            "organ": "system0.5/shortlist",
            "model": self
                .model_dir
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or("static-embeddings"),
            "candidate_count": names.len(),
            "utterance_count": texts.len(),
            "ranked": ranked
                .iter()
                .map(|candidate| json!({"route": candidate.name, "score": candidate.score}))
                .collect::<Vec<Value>>(),
            "top1": ranked.first().map(|c| c.name.clone()),
            "confidence": ranked.first().map_or(0.0, |c| c.score),
            "margin": margin,
            "latency_ms": latency_ms,
        }))
    }
}

fn parse_routes(routes: &Value) -> Result<Vec<(String, Vec<String>)>, Error> {
    match routes {
        Value::Object(map) => {
            let mut parsed = Vec::with_capacity(map.len());
            for (name, value) in map {
                let utterances = match value {
                    Value::String(text) => vec![text.clone()],
                    Value::Null => vec![String::new()],
                    Value::Array(items) => {
                        let mut list = Vec::with_capacity(items.len());
                        for item in items {
                            match item {
                                Value::String(text) => list.push(text.clone()),
                                other => {
                                    return Err(Error::BadRoutes(format!(
                                        "route '{name}' utterances must be strings, got {other}"
                                    )));
                                }
                            }
                        }
                        if list.is_empty() {
                            return Err(Error::BadRoutes(format!(
                                "route '{name}' has an empty utterance list"
                            )));
                        }
                        list
                    }
                    other => {
                        return Err(Error::BadRoutes(format!(
                            "route '{name}' must be a description or an array of utterances, got {other}"
                        )));
                    }
                };
                parsed.push((name.clone(), utterances));
            }
            if parsed.is_empty() {
                return Err(Error::BadRoutes("candidate set is empty".to_string()));
            }
            Ok(parsed)
        }
        Value::Array(items) => {
            let mut parsed = Vec::with_capacity(items.len());
            for item in items {
                match item {
                    Value::String(name) => parsed.push((name.clone(), vec![String::new()])),
                    other => {
                        return Err(Error::BadRoutes(format!(
                            "array entries must be strings, got {other}"
                        )));
                    }
                }
            }
            if parsed.is_empty() {
                return Err(Error::BadRoutes("candidate set is empty".to_string()));
            }
            Ok(parsed)
        }
        _ => Err(Error::BadRoutes(
            "expected an object of name->description or an array of names".to_string(),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ranking_is_sorted_and_truncated() {
        let query = l2_normalize(vec![1.0, 0.0]);
        let candidates = vec![
            vec![0.0, 1.0],
            l2_normalize(vec![1.0, 0.0]),
            l2_normalize(vec![0.7, 0.7]),
        ];
        let names = vec![
            "orthogonal".to_string(),
            "aligned".to_string(),
            "diagonal".to_string(),
        ];
        let ranked = rank_candidates(&query, &candidates, &names, 2);
        assert_eq!(ranked.len(), 2);
        assert_eq!(ranked[0].name, "aligned");
        assert_eq!(ranked[1].name, "diagonal");
        assert!(ranked[0].score > ranked[1].score);
    }

    #[test]
    fn normalize_produces_unit_length() {
        let normalized = l2_normalize(vec![3.0, 4.0]);
        assert!((normalized[0] - 0.6).abs() < 1e-6);
        assert!((normalized[1] - 0.8).abs() < 1e-6);
    }

    #[test]
    fn parses_object_and_array_routes() {
        let object = json!({"a": "first", "b": "", "c": ["one", "two"]});
        let parsed = parse_routes(&object).expect("object parses");
        assert_eq!(parsed.len(), 3);
        assert_eq!(parsed[2].1.len(), 2);

        let array = json!(["a", "b"]);
        let parsed = parse_routes(&array).expect("array parses");
        assert_eq!(parsed[1].1, vec![String::new()]);
    }

    #[test]
    fn rejects_empty_utterance_lists() {
        assert!(parse_routes(&json!({"a": []})).is_err());
    }

    #[test]
    fn max_pooling_prefers_best_utterance() {
        let query = l2_normalize(vec![1.0, 0.0]);
        let vectors = vec![
            l2_normalize(vec![0.0, 1.0]),
            l2_normalize(vec![0.9, 0.1]),
            l2_normalize(vec![1.0, 0.0]),
        ];
        let ranges = vec![(0, 2), (2, 3)];
        let names = vec!["grab-bag".to_string(), "exact".to_string()];
        let ranked = rank_route_blocks(&query, &vectors, &ranges, &names, 2);
        assert_eq!(ranked[0].name, "exact");
        assert_eq!(ranked[1].name, "grab-bag");
    }

    #[test]
    fn rejects_malformed_routes() {
        assert!(parse_routes(&json!({})).is_err());
        assert!(parse_routes(&json!(42)).is_err());
        assert!(parse_routes(&json!([1, 2])).is_err());
    }

    #[test]
    fn resolve_model_dir_reports_missing() {
        let resolved = System05::resolve_model_dir(Some(PathBuf::from(
            "/tmp/opencode/definitely-not-a-system05-checkpoint",
        )));
        assert!(matches!(resolved, Err(Error::ModelDirNotFound(_))));
    }

    #[test]
    fn resolve_catalog_reports_missing() {
        let resolved = System05::resolve_catalog_path(Some(PathBuf::from(
            "/tmp/opencode/definitely-not-a-catalog.json",
        )));
        assert!(matches!(resolved, Err(Error::BadRoutes(_))));
    }
}
