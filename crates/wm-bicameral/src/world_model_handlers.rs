//! LLM-backed TierHandler adapters for the WorldModel.
//!
//! The `WorldModel` uses `TierHandler` (simple prompt → text + confidence),
//! while the bicameral hemispheres use the `Hemisphere`/`RightHemisphere` traits.
//! These adapters bridge the gap by calling OpenAI-compatible APIs directly.
//!
//! Configuration via environment variables:
//! - `WM_LLAMA_ENDPOINT` — llama-server URL for left hemisphere (deterministic)
//! - `WM_LLM_API_KEY` + `WM_LLM_ENDPOINT` — cloud LLM for right hemisphere (creative)
//!
//! Falls back to `StubWorldModelHandler` when env vars are not set.

#![forbid(unsafe_code)]

use std::sync::Arc;
use std::time::Duration;

use crate::router::TierHandler;
use crate::world_model::StubWorldModelHandler;

use serde::{Deserialize, Serialize};

// ── Shared HTTP types ─────────────────────────────────────────────────

#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    max_tokens: u32,
    temperature: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Debug, Deserialize)]
struct ChatResponse {
    choices: Vec<ChatChoice>,
}

#[derive(Debug, Deserialize)]
struct ChatChoice {
    message: ChatMessage,
}

// ── LLM TierHandler ───────────────────────────────────────────────────

/// LLM-backed tier handler — calls an OpenAI-compatible API.
///
/// Used as the left hemisphere of the WorldModel when `WM_LLAMA_ENDPOINT`
/// is set. Low temperature for deterministic predictions.
pub struct LlmTierHandler {
    endpoint: String,
    model: String,
    api_key: Option<String>,
    temperature: f32,
    agent: ureq::Agent,
    name: &'static str,
}

impl LlmTierHandler {
    /// Create a new LLM tier handler.
    #[must_use]
    pub fn new(
        endpoint: String,
        model: String,
        api_key: Option<String>,
        temperature: f32,
        timeout: Duration,
        name: &'static str,
    ) -> Self {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(timeout))
            .build()
            .new_agent();
        Self {
            endpoint,
            model,
            api_key,
            temperature,
            agent,
            name,
        }
    }

    /// Create a left-hemisphere handler (deterministic, low temp) from env.
    ///
    /// Uses `WM_LLAMA_ENDPOINT` and `WM_LLAMA_MODEL`.
    /// Returns `None` if `WM_LLAMA_ENDPOINT` is not set.
    #[must_use]
    pub fn left_from_env() -> Option<Self> {
        let endpoint_raw = std::env::var("WM_LLAMA_ENDPOINT").ok()?;
        if endpoint_raw.is_empty() {
            return None;
        }

        let endpoint = normalize_endpoint(&endpoint_raw);
        let model = std::env::var("WM_LLAMA_MODEL").unwrap_or_else(|_| "local".into());
        let temperature = std::env::var("WM_LLAMA_TEMP")
            .ok()
            .and_then(|s| s.parse::<f32>().ok())
            .unwrap_or(0.2)
            .clamp(0.0, 2.0);
        let timeout_ms = std::env::var("WM_LLAMA_TIMEOUT_MS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(10_000);

        Some(Self::new(
            endpoint,
            model,
            None,
            temperature,
            Duration::from_millis(timeout_ms),
            "llm-left",
        ))
    }

    /// Create a right-hemisphere handler (creative, higher temp) from env.
    ///
    /// Uses `WM_LLM_API_KEY`, `WM_LLM_ENDPOINT`, and `WM_LLM_MODEL`.
    /// Returns `None` if `WM_LLM_API_KEY` is not set.
    #[must_use]
    pub fn right_from_env() -> Option<Self> {
        let api_key = std::env::var("WM_LLM_API_KEY").ok()?;
        if api_key.is_empty() {
            return None;
        }

        let endpoint = std::env::var("WM_LLM_ENDPOINT")
            .unwrap_or_else(|_| "https://api.openai.com/v1/chat/completions".into());

        if !(endpoint.starts_with("http://") || endpoint.starts_with("https://")) {
            tracing::warn!(endpoint = %endpoint, "WM_LLM_ENDPOINT rejected: must use http:// or https://");
            return None;
        }

        let endpoint = normalize_endpoint(&endpoint);
        let model = std::env::var("WM_LLM_MODEL").unwrap_or_else(|_| "gpt-4o-mini".into());
        let timeout_ms = std::env::var("WM_LLM_TIMEOUT_MS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(15_000);

        Some(Self::new(
            endpoint,
            model,
            Some(api_key),
            0.7,
            Duration::from_millis(timeout_ms),
            "llm-right",
        ))
    }

    fn call_api(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String> {
        let system_prompt = "You are a world model for an imagination engine. \
            Given a state, action, and goal, predict the outcome. \
            Respond in this exact format:\n\
            DESCRIPTION: <one sentence description>\n\
            CHANGES: <comma-separated list of key changes>\n\
            RISKS: <comma-separated list of risk factors>\n\
            CONFIDENCE: <0.0-1.0>\n\
            GOAL_PROGRESS: <0.0-1.0>";

        let req = ChatRequest {
            model: self.model.clone(),
            messages: vec![
                ChatMessage {
                    role: "system".into(),
                    content: system_prompt.into(),
                },
                ChatMessage {
                    role: "user".into(),
                    content: prompt.into(),
                },
            ],
            max_tokens: max_tokens.min(512) as u32,
            temperature: self.temperature,
        };

        let mut request = self.agent.post(&self.endpoint);
        if let Some(ref key) = self.api_key {
            request = request.header("Authorization", &format!("Bearer {key}"));
        }

        let response: ChatResponse = request
            .send_json(req)
            .map_err(|e| format!("LLM API error: {e}"))?
            .body_mut()
            .read_json()
            .map_err(|e| format!("LLM response parse error: {e}"))?;

        let content = response
            .choices
            .first()
            .ok_or("no choices in LLM response")?
            .message
            .content
            .clone();

        // Parse confidence from the response
        let confidence = parse_confidence(&content);
        Ok((content, confidence))
    }
}

impl TierHandler for LlmTierHandler {
    fn handle(&self, prompt: &str, max_tokens: usize) -> Result<(String, f32), String> {
        self.call_api(prompt, max_tokens)
    }

    fn name(&self) -> &'static str {
        self.name
    }
}

// ── Helpers ───────────────────────────────────────────────────────────

/// Normalize an endpoint URL to include the chat completions path.
fn normalize_endpoint(raw: &str) -> String {
    if raw.ends_with("/v1/chat/completions") {
        raw.to_string()
    } else if raw.ends_with('/') {
        format!("{raw}v1/chat/completions")
    } else {
        format!("{raw}/v1/chat/completions")
    }
}

/// Parse confidence from LLM response text.
fn parse_confidence(content: &str) -> f32 {
    for line in content.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("CONFIDENCE:") {
            return rest.trim().parse::<f32>().unwrap_or(0.5).clamp(0.0, 1.0);
        }
    }
    0.5
}

// ── WorldModel factory ────────────────────────────────────────────────

/// Build a `WorldModel` from environment-configured LLM handlers, falling
/// back to stub handlers when env vars are not set.
///
/// - Left: `LlmTierHandler::left_from_env()` or `StubWorldModelHandler::left()`
/// - Right: `LlmTierHandler::right_from_env()` or `StubWorldModelHandler::right()`
#[must_use]
pub fn world_model_from_env() -> crate::world_model::WorldModel {
    let left: Arc<dyn TierHandler> = match LlmTierHandler::left_from_env() {
        Some(h) => {
            tracing::info!("world model: using LLM left hemisphere");
            Arc::new(h)
        }
        None => {
            tracing::info!("world model: using stub left hemisphere (set WM_LLAMA_ENDPOINT for LLM)");
            Arc::new(StubWorldModelHandler::left())
        }
    };

    let right: Option<Arc<dyn TierHandler>> = match LlmTierHandler::right_from_env() {
        Some(h) => {
            tracing::info!("world model: using LLM right hemisphere");
            Some(Arc::new(h))
        }
        None => {
            tracing::info!("world model: using stub right hemisphere (set WM_LLM_API_KEY for LLM)");
            Some(Arc::new(StubWorldModelHandler::right()))
        }
    };

    crate::world_model::WorldModel::new(left, right)
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_endpoint_appends_path() {
        assert_eq!(
            normalize_endpoint("http://localhost:8080"),
            "http://localhost:8080/v1/chat/completions"
        );
        assert_eq!(
            normalize_endpoint("http://localhost:8080/"),
            "http://localhost:8080/v1/chat/completions"
        );
        assert_eq!(
            normalize_endpoint("http://localhost:8080/v1/chat/completions"),
            "http://localhost:8080/v1/chat/completions"
        );
    }

    #[test]
    fn parse_confidence_extracts_value() {
        assert!((parse_confidence("CONFIDENCE: 0.85") - 0.85).abs() < 0.001);
        assert!((parse_confidence("DESCRIPTION: foo\nCONFIDENCE: 0.7\n") - 0.7).abs() < 0.001);
        assert_eq!(parse_confidence("no confidence line"), 0.5);
    }

    #[test]
    fn parse_confidence_clamps() {
        assert_eq!(parse_confidence("CONFIDENCE: 1.5"), 1.0);
        assert_eq!(parse_confidence("CONFIDENCE: -0.3"), 0.0);
    }

    #[test]
    fn world_model_from_env_uses_stubs_without_env() {
        // Without WM_LLAMA_ENDPOINT or WM_LLM_API_KEY set,
        // world_model_from_env falls back to stub handlers.
        // (If env vars happen to be set, this still works — just with LLM handlers.)
        let wm = world_model_from_env();
        let pred = wm.predict("test state", "test action", "test goal");
        assert!(!pred.best().description.is_empty());
    }

    #[test]
    fn llm_tier_handler_name() {
        let h = LlmTierHandler::new(
            "http://localhost:8080/v1/chat/completions".into(),
            "test".into(),
            None,
            0.2,
            Duration::from_secs(5),
            "test-handler",
        );
        assert_eq!(h.name(), "test-handler");
    }
}
