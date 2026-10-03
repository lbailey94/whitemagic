//! Optional System One typed-decision organ for WhiteMagic Gen3.
//!
//! Wraps the pure-Rust `laya` inference crate behind a small API: a state plus
//! typed questions in, calibrated probabilities out. Loading is lazy and
//! caller-driven; the organ never spawns threads and never touches the
//! substrate.

use std::fmt;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::Instant;

use laya::{Agent, Options, Question};
use serde_json::{Value, json};

/// Environment variable overriding the checkpoint directory.
pub const ENV_MODEL: &str = "WM_GEN3_SYSTEMONE_MODEL";

/// System One organ error.
#[derive(Debug)]
pub enum Error {
    /// No checkpoint directory with `model.safetensors` was found.
    ModelDirNotFound(String),
    /// The checkpoint failed to load.
    Load(String),
    /// The question payload was malformed.
    BadQuestions(String),
    /// Inference failed or the model is not loaded.
    Inference(String),
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::ModelDirNotFound(paths) => {
                write!(f, "no Laya checkpoint found (looked in: {paths})")
            }
            Error::Load(msg) => write!(f, "failed to load Laya checkpoint: {msg}"),
            Error::BadQuestions(msg) => write!(f, "invalid questions: {msg}"),
            Error::Inference(msg) => write!(f, "inference failed: {msg}"),
        }
    }
}

impl std::error::Error for Error {}

/// Lazily loaded Laya decision organ.
pub struct SystemOne {
    model_dir: PathBuf,
    agent: Mutex<Option<Agent>>,
}

impl SystemOne {
    /// Create an organ bound to a checkpoint directory. Nothing loads until
    /// [`SystemOne::ensure_loaded`] or [`SystemOne::decide`] is called.
    #[must_use]
    pub fn new(model_dir: impl Into<PathBuf>) -> Self {
        Self {
            model_dir: model_dir.into(),
            agent: Mutex::new(None),
        }
    }

    /// Resolve the checkpoint directory: explicit path, then
    /// `WM_GEN3_SYSTEMONE_MODEL`, then `~/tools/laya/models/laya-base`, then
    /// `~/.local/share/whitemagic/systemone/laya-base`.
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
                candidates.push(home.join("tools/laya/models/laya-base"));
                candidates.push(home.join(".local/share/whitemagic/systemone/laya-base"));
            }
        }
        for candidate in &candidates {
            if candidate.join("model.safetensors").is_file() {
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

    /// Checkpoint directory this organ is bound to.
    #[must_use]
    pub fn model_dir(&self) -> &std::path::Path {
        &self.model_dir
    }

    /// True once the checkpoint has been loaded.
    #[must_use]
    pub fn is_loaded(&self) -> bool {
        self.agent
            .lock()
            .map(|guard| guard.is_some())
            .unwrap_or(false)
    }

    /// Load the checkpoint if it is not already resident.
    pub fn ensure_loaded(&self) -> Result<(), Error> {
        let mut guard = self
            .agent
            .lock()
            .map_err(|_| Error::Load("systemone lock poisoned".to_string()))?;
        if guard.is_none() {
            if !self.model_dir.join("model.safetensors").is_file() {
                return Err(Error::ModelDirNotFound(
                    self.model_dir.display().to_string(),
                ));
            }
            let agent = Agent::from_dir(&self.model_dir, Options::default())
                .map_err(|e| Error::Load(e.to_string()))?;
            *guard = Some(agent);
        }
        Ok(())
    }

    /// Drop the resident checkpoint and release its memory.
    pub fn unload(&self) {
        if let Ok(mut guard) = self.agent.lock() {
            *guard = None;
        }
    }

    /// Run one typed decision. `questions` is either an object keyed by question
    /// id or an array of question objects carrying an `id`. The returned JSON
    /// mirrors the Laya response plus `latency_ms` and `model_dir`.
    pub fn decide(&self, state: &Value, questions: &Value) -> Result<Value, Error> {
        let parsed = parse_questions(questions)?;
        self.ensure_loaded()?;
        let guard = self
            .agent
            .lock()
            .map_err(|_| Error::Inference("systemone lock poisoned".to_string()))?;
        let agent = guard
            .as_ref()
            .ok_or_else(|| Error::Inference("model not loaded".to_string()))?;
        let started = Instant::now();
        let response = agent
            .system_one(state, &parsed)
            .map_err(|e| Error::Inference(e.to_string()))?;
        let mut out =
            serde_json::to_value(&response).map_err(|e| Error::Inference(e.to_string()))?;
        if let Value::Object(ref mut map) = out {
            map.insert(
                "latency_ms".to_string(),
                json!(started.elapsed().as_secs_f64() * 1000.0),
            );
            map.insert(
                "model_dir".to_string(),
                json!(self.model_dir.display().to_string()),
            );
        }
        Ok(out)
    }
}

fn parse_questions(questions: &Value) -> Result<Vec<(String, Question)>, Error> {
    match questions {
        Value::Object(map) => map
            .iter()
            .map(|(id, spec)| {
                let question: Question = serde_json::from_value(spec.clone())
                    .map_err(|e| Error::BadQuestions(format!("{id}: {e}")))?;
                Ok((id.clone(), question))
            })
            .collect(),
        Value::Array(items) => items
            .iter()
            .enumerate()
            .map(|(index, spec)| {
                let mut map = spec.as_object().cloned().ok_or_else(|| {
                    Error::BadQuestions(format!("question {index}: expected an object"))
                })?;
                let id = match map.remove("id") {
                    Some(Value::String(id)) => id,
                    Some(_) => {
                        return Err(Error::BadQuestions(format!(
                            "question {index}: `id` must be a string"
                        )));
                    }
                    None => format!("q{index}"),
                };
                let question: Question = serde_json::from_value(Value::Object(map))
                    .map_err(|e| Error::BadQuestions(format!("{id}: {e}")))?;
                Ok((id, question))
            })
            .collect(),
        _ => Err(Error::BadQuestions(
            "questions must be an object keyed by id or an array of question objects".to_string(),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_object_questions() {
        let questions =
            json!({"dept": {"type": "choice", "instructions": "which?", "criteria": ["a", "b"]}});
        let parsed = parse_questions(&questions).expect("object questions parse");
        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0].0, "dept");
    }

    #[test]
    fn parses_array_questions_with_ids() {
        let questions = json!([
            {"id": "dept", "type": "choice", "instructions": "which?", "criteria": ["a", "b"]},
            {"type": "noul", "instructions": "does this hold?"}
        ]);
        let parsed = parse_questions(&questions).expect("array questions parse");
        assert_eq!(parsed.len(), 2);
        assert_eq!(parsed[0].0, "dept");
        assert_eq!(parsed[1].0, "q1");
    }

    #[test]
    fn rejects_malformed_questions() {
        assert!(parse_questions(&json!({"dept": {"type": "wat"}})).is_err());
        assert!(parse_questions(&json!(42)).is_err());
    }

    #[test]
    fn resolve_model_dir_reports_missing() {
        let resolved = SystemOne::resolve_model_dir(Some(PathBuf::from(
            "/tmp/opencode/definitely-not-a-laya-checkpoint",
        )));
        assert!(matches!(resolved, Err(Error::ModelDirNotFound(_))));
    }
}
