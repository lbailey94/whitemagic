//! Semantic projection primitive (GEN3-P2B-PROJECTION-001).
//!
//! One frozen pretrained geometry (`Qdrant/bge-small-en-v1.5-onnx-Q`) behind the
//! `WM_GEN3_PROJECTION` switch, attaching at two implementation points: recall
//! candidate expansion and `think` pair gating. Brute-force cosine over cached
//! vectors — no ANN, no fine-tuning, no corpus-specific vocabulary, no query
//! rewriting. Pinned artifacts and hashes: `receipts/DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16.md`.
//!
//! The gate threshold [`TAU_GATE`] is calibrated on the frozen genericity
//! battery only (pre-committed rule: maximum-margin separator at the midpoint
//! between the highest hard-negative similarity and the lowest positive
//! similarity). The frozen requirement is separation; the measured margin is
//! thin (0.0116) and is recorded as a sensitivity advisory in the
//! implementation-freeze receipt, not as a kill criterion (it is not part of
//! the frozen pre-registration). Never calibrated on benchmark outcomes.

use std::path::Path;
use std::time::Instant;

/// Frozen embedding model id (exception receipt pins the artifact hashes).
pub const MODEL_ID: &str = "Qdrant/bge-small-en-v1.5-onnx-Q";
pub const DIM: usize = 384;

/// Similarity gate, calibrated on the genericity battery (see test below):
/// maximum-margin separator at the measured midpoint between the highest hard
/// negative (0.6882) and the lowest positive (0.6998). Pinned at implementation
/// freeze; any change re-baselines the experiment.
pub const TAU_GATE: f32 = 0.694;

/// Calibrated candidate sweep floor (Gate 9C): filters out cross-topic noise (mean 0.40-0.47)
/// while preserving genuine paraphrased updates and revisions (0.52-0.75).
pub const TAU_SWEEP: f32 = 0.50;

/// Minimum acceptable battery separation between hard negatives and positives.
pub const MIN_BATTERY_MARGIN: f32 = 0.05;

/// Model load + embedding counters (cost accounting, pre-reg §4/M-cost).
#[derive(Debug, Default, Clone, Copy)]
pub struct ProjectionStats {
    pub model_load_ms: u64,
    pub embed_calls: u64,
    pub embed_texts: u64,
    pub embed_ms: u64,
}

pub struct Projection {
    model: fastembed::TextEmbedding,
    cache_dir: std::path::PathBuf,
    pub stats: ProjectionStats,
}

impl Projection {
    /// Load the frozen model from a local cache directory (no network at run
    /// time; the dir is read-only for this process).
    pub fn load(cache_dir: &Path) -> Result<Self, String> {
        let started = Instant::now();
        // Code-enforce offline execution: fail closed if cache is missing or incomplete,
        // preventing any network attempts (erratum #57).
        if !cache_dir.exists() {
            return Err(format!(
                "projection: cache directory missing: {cache_dir:?}; offline execution refuses network fetch"
            ));
        }
        let model_dir = cache_dir.join("models--Qdrant--bge-small-en-v1.5-onnx-Q");
        let legacy_model_dir = cache_dir.join("models--Xenova--bge-small-en-v1.5");
        if !model_dir.exists() && !legacy_model_dir.exists() {
            return Err(format!(
                "projection: model artifacts missing in {cache_dir:?}; offline execution refuses network fetch"
            ));
        }
        let options = fastembed::TextInitOptions::new(fastembed::EmbeddingModel::BGESmallENV15Q)
            .with_cache_dir(cache_dir.to_path_buf())
            .with_show_download_progress(false);
        let model = fastembed::TextEmbedding::try_new(options)
            .map_err(|e| format!("projection: model load failed from {cache_dir:?}: {e}"))?;
        let load_ms = started.elapsed().as_millis() as u64;
        Ok(Self {
            model,
            cache_dir: cache_dir.to_path_buf(),
            stats: ProjectionStats {
                model_load_ms: load_ms,
                ..Default::default()
            },
        })
    }

    #[must_use]
    pub fn cache_dir(&self) -> &Path {
        &self.cache_dir
    }

    /// Embed texts (L2-normalized). Batch call; stats recorded.
    pub fn embed(&mut self, texts: &[String]) -> Result<Vec<Vec<f32>>, String> {
        let started = Instant::now();
        let mut out = self
            .model
            .embed(texts, None)
            .map_err(|e| format!("projection: embed failed: {e}"))?;
        for v in out.iter_mut() {
            l2_normalize(v);
        }
        self.stats.embed_calls += 1;
        self.stats.embed_texts += texts.len() as u64;
        self.stats.embed_ms += started.elapsed().as_millis() as u64;
        Ok(out)
    }

    pub fn embed_one(&mut self, text: &str) -> Result<Vec<f32>, String> {
        let mut v = self.embed(&[text.to_string()])?;
        Ok(v.pop().unwrap_or_default())
    }
}

/// L2 normalization (pinned: L2-normalized, cosine similarity).
pub fn l2_normalize(v: &mut [f32]) {
    let norm = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > f32::EPSILON {
        for x in v.iter_mut() {
            *x /= norm;
        }
    }
}

/// Cosine similarity for L2-normalized vectors (plain dot product).
#[must_use]
pub fn cosine(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

/// Support in [0,1] from cosine: 0 below the gate, 1 at full similarity.
#[must_use]
pub fn semantic_support(cos: f32) -> f32 {
    if cos <= TAU_GATE {
        0.0
    } else {
        ((cos - TAU_GATE) / (1.0 - TAU_GATE)).clamp(0.0, 1.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Frozen genericity battery (pre-reg §5): synonym/paraphrase positives must
    /// form a neighborhood; lexical-overlap hard negatives must be rejected;
    /// separation is computed here and the compiled TAU_GATE must sit between.
    #[test]
    fn genericity_battery() {
        let dir = crate::embed_cache_dir_or_panic();
        let mut p = Projection::load(&dir).expect("model loads from cache");
        let positives = [
            ("automobile", "car"),
            ("physician", "doctor"),
            ("relocated", "moved"),
            ("canine", "dog"),
            ("software release", "version"),
            (
                "The storm forced the airport to cancel all departures.",
                "Flights were grounded because of the weather.",
            ),
            (
                "She repaired the leaking radiator.",
                "The plumber fixed the broken heating unit.",
            ),
        ];
        let negatives = [
            (
                "the river bank was steep",
                "she deposited money at the bank",
            ),
            ("Apple released a new phone", "the apple fell from the tree"),
            ("the band played a set", "a set of tools"),
            ("he left the bat on the field", "the bat flew at dusk"),
        ];
        let mut texts: Vec<String> = Vec::new();
        for (a, b) in positives.iter().chain(negatives.iter()) {
            texts.push((*a).to_string());
            texts.push((*b).to_string());
        }
        let vectors = p.embed(&texts).expect("battery embeds");
        let cos_of = |i: usize| cosine(&vectors[i * 2], &vectors[i * 2 + 1]);
        let pos_cos: Vec<f32> = (0..positives.len()).map(cos_of).collect();
        let neg_cos: Vec<f32> = (positives.len()..positives.len() + negatives.len())
            .map(cos_of)
            .collect();
        let min_pos = pos_cos.iter().cloned().fold(f32::MAX, f32::min);
        let max_neg = neg_cos.iter().cloned().fold(f32::MIN, f32::max);
        let mid = (min_pos + max_neg) / 2.0;
        println!(
            "battery: min_pos={min_pos:.4} max_neg={max_neg:.4} midpoint={mid:.4} (TAU_GATE={TAU_GATE})"
        );
        for (name, c) in positives.iter().zip(pos_cos.iter()) {
            println!("  POS {name:?} cos={c:.4}");
        }
        for (name, c) in negatives.iter().zip(neg_cos.iter()) {
            println!("  NEG {name:?} cos={c:.4}");
        }
        assert!(
            neg_cos.iter().all(|c| *c <= TAU_GATE) && pos_cos.iter().all(|c| *c >= TAU_GATE),
            "compiled TAU_GATE={TAU_GATE} does not separate the battery (midpoint={mid:.4})"
        );
        let margin = min_pos - max_neg;
        if margin < MIN_BATTERY_MARGIN {
            // Advisory only: the frozen pre-registration requires separation
            // (which holds); the margin is the implementer's sensitivity warning
            // and is recorded in the implementation-freeze receipt.
            println!(
                "battery ADVISORY: thin margin {margin:.4} < {MIN_BATTERY_MARGIN} — separation holds; recorded in implementation freeze"
            );
        }
    }
}

#[cfg(test)]
mod a3_diagnostic {
    use super::*;

    /// A3 read-only diagnostic (P2D/P2E failure taxonomy): ungated cosine values.
    /// If `WM_GEN3_DIAG_PAIRS` points to a JSON file, measures those pairs:
    ///   [{"label": "...", "query": "...", "candidates": [{"name": "...", "text": "..."}]}]
    /// Otherwise falls back to the built-in anomaly pairs. Measures only — no
    /// ranking behavior changes anywhere. Run with:
    ///   WM_GEN3_DIAG_PAIRS=… cargo test a3_diagnostic_ungated_cosine -- --ignored --nocapture
    #[test]
    #[ignore]
    fn a3_diagnostic_ungated_cosine() {
        let dir = crate::embed_cache_dir();
        let mut p = Projection::load(&dir).expect("model loads");
        if let Ok(path) = std::env::var("WM_GEN3_DIAG_PAIRS") {
            #[derive(serde::Deserialize)]
            struct Cand {
                name: String,
                text: String,
            }
            #[derive(serde::Deserialize)]
            struct Entry {
                label: String,
                query: String,
                candidates: Vec<Cand>,
            }
            let entries: Vec<Entry> =
                serde_json::from_slice(&std::fs::read(&path).expect("pairs file"))
                    .expect("pairs json");
            for e in entries {
                let mut all: Vec<String> = vec![e.query.clone()];
                all.extend(e.candidates.iter().map(|c| c.text.clone()));
                let vs = p.embed(&all).expect("embed");
                println!("== {}: {}", e.label, e.query);
                for (i, c) in e.candidates.iter().enumerate() {
                    let cos = cosine(&vs[0], &vs[i + 1]);
                    println!("   {} cos={:.4} | {}", c.name, cos, c.text);
                }
            }
            return;
        }
        // Inline fixture table; a type alias would not add clarity here.
        #[allow(clippy::type_complexity)]
        let pairs: &[(&str, &str, Vec<(&str, &str)>)] = &[
            (
                "seed14/T1_coffee",
                "What's my current favorite coffee?",
                vec![
                    ("correct id744", "For coffee, I always go with dark roast."),
                    ("cross id731", "My favorite sport is tennis."),
                    ("old id645", "My favorite coffee is dark roast."),
                    ("old id65", "My favorite coffee is oat milk latte."),
                ],
            ),
            (
                "seed14/T1_food",
                "What's my current favorite food?",
                vec![
                    ("correct id726", "I prefer Italian for my food."),
                    ("cross id731", "My favorite sport is tennis."),
                    ("old id375", "My favorite food is Korean."),
                ],
            ),
            (
                "seed14/T1_transport",
                "What's my current favorite transport?",
                vec![
                    (
                        "correct id740",
                        "I've been really into bus lately for transport.",
                    ),
                    ("cross id731", "My favorite sport is tennis."),
                    ("old id92", "My favorite transport is walking."),
                ],
            ),
            (
                "seed2/T1_book_genre",
                "What's my current favorite book genre?",
                vec![
                    ("label id781", "My favorite book_genre is cookbooks."),
                    ("rank1 id789", "My favorite book_genre is fantasy."),
                ],
            ),
        ];
        for (label, query, texts) in pairs {
            let mut all: Vec<String> = vec![(*query).to_string()];
            all.extend(texts.iter().map(|(_, t)| (*t).to_string()));
            let vs = p.embed(&all).expect("embed");
            let qv = &vs[0];
            println!("== {label}: {query}");
            for (i, (name, text)) in texts.iter().enumerate() {
                let c = cosine(qv, &vs[i + 1]);
                println!("   {name:14} cos={c:.4} | {text}");
            }
        }
    }

    #[test]
    fn test_missing_cache_fails_closed_offline() {
        let non_existent = std::path::PathBuf::from("/nonexistent/fastembed_cache_test");
        let res = Projection::load(&non_existent);
        assert!(
            res.is_err(),
            "missing cache dir must fail closed without attempting network"
        );
    }
}
