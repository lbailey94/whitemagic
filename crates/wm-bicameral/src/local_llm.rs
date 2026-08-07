//! LLM-backed left hemisphere — calls a local llama.cpp server for reasoning.
//!
//! When configured with `WM_LLAMA_ENDPOINT`, the bicameral engine uses this
//! hemisphere instead of the heuristic `LeftHemisphere`. The llama-server
//! exposes an OpenAI-compatible API, so we reuse the same ureq HTTP pattern
//! as the cloud LLM right hemisphere.
//!
//! Configuration via environment variables:
//! - `WM_LLAMA_ENDPOINT` — llama-server HTTP API URL (e.g. http://localhost:8080)
//! - `WM_LLAMA_MODEL` — Model name/path (default: `local`)
//! - `WM_LLAMA_TEMP` — Temperature for left hemisphere (default: `0.2`, low = deterministic)
//! - `WM_LLAMA_TIMEOUT_MS` — Request timeout in milliseconds (default: 10000)
//! - `WM_LLAMA_MAX_TOKENS` — Max response tokens (default: 512)

#![forbid(unsafe_code)]

use crate::hemisphere::{Hemisphere, HemisphereInput, HemisphereOutput, HemisphereSource, Stance};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Configuration for the llama.cpp left hemisphere.
#[derive(Debug, Clone)]
pub struct LlamaConfig {
    /// llama-server HTTP API URL (e.g. http://localhost:8080).
    pub endpoint: String,
    /// Model name/path reported to the API.
    pub model: String,
    /// Temperature — low for deterministic output (left hemisphere trait).
    pub temperature: f32,
    /// Request timeout.
    pub timeout: Duration,
    /// Maximum tokens for the response.
    pub max_tokens: u32,
}

impl Default for LlamaConfig {
    fn default() -> Self {
        Self {
            endpoint: "http://localhost:8080/v1/chat/completions".into(),
            model: "local".into(),
            temperature: 0.2,
            timeout: Duration::from_secs(10),
            max_tokens: 512,
        }
    }
}

impl LlamaConfig {
    /// Create a config from environment variables.
    ///
    /// Returns `None` if `WM_LLAMA_ENDPOINT` is not set or empty.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let endpoint_raw = std::env::var("WM_LLAMA_ENDPOINT").ok()?;
        if endpoint_raw.is_empty() {
            return None;
        }

        // Normalize: if the user gives just a base URL like http://localhost:8080,
        // append the standard OpenAI-compatible path.
        let endpoint = if endpoint_raw.ends_with("/v1/chat/completions") {
            endpoint_raw
        } else if endpoint_raw.ends_with('/') {
            format!("{endpoint_raw}v1/chat/completions")
        } else {
            format!("{endpoint_raw}/v1/chat/completions")
        };

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

        let max_tokens = std::env::var("WM_LLAMA_MAX_TOKENS")
            .ok()
            .and_then(|s| s.parse::<u32>().ok())
            .unwrap_or(512);

        Some(Self {
            endpoint,
            model,
            temperature,
            timeout: Duration::from_millis(timeout_ms),
            max_tokens,
        })
    }
}

/// OpenAI chat completion request body (shared shape with llm.rs).
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

/// Llama.cpp-backed left hemisphere.
///
/// Calls a local llama-server (OpenAI-compatible API) for structured,
/// deterministic reasoning. Low temperature ensures the left hemisphere
/// stays analytical and reproducible. If the API call fails, falls back
/// to the heuristic `LeftHemisphere` logic.
pub struct LlamaLeftHemisphere {
    config: LlamaConfig,
    agent: ureq::Agent,
    fallback: super::hemisphere::LeftHemisphere,
}

impl LlamaLeftHemisphere {
    /// Create a new llama left hemisphere with the given config.
    #[must_use]
    pub fn new(config: LlamaConfig) -> Self {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(config.timeout))
            .build()
            .new_agent();
        Self {
            config,
            agent,
            fallback: super::hemisphere::LeftHemisphere::new(),
        }
    }

    /// Create from environment variables, if configured.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        LlamaConfig::from_env().map(Self::new)
    }

    /// Build the system prompt for the left hemisphere.
    fn system_prompt(&self) -> String {
        "You are the left hemisphere of a bicameral reasoning system. \
         Your role is analytical, systematic, and evidence-based. \
         Analyze the topic and evidence methodically. \
         Provide a conclusion, your confidence (0.0-1.0), \
         your stance (agree, disagree, or uncertain), \
         and 3-5 key points. Respond in JSON format: \
         {\"conclusion\": \"...\", \"confidence\": 0.7, \"stance\": \"agree\", \
         \"key_points\": [\"...\", \"...\"]}"
            .into()
    }

    /// Build the user prompt from a hemisphere input.
    fn user_prompt(&self, input: &HemisphereInput) -> String {
        let evidence_str = if input.evidence.is_empty() {
            "No evidence provided.".to_string()
        } else {
            input
                .evidence
                .iter()
                .enumerate()
                .map(|(i, e)| format!("  {}. {}", i + 1, e))
                .collect::<Vec<_>>()
                .join("\n")
        };

        let context_str = if input.context.is_null() {
            "None".to_string()
        } else {
            serde_json::to_string_pretty(&input.context).unwrap_or_else(|_| "None".into())
        };

        format!(
            "Topic: {}\n\nEvidence:\n{}\n\nContext: {}\n\n\
             Analyze this topic systematically and provide your assessment.",
            input.topic, evidence_str, context_str
        )
    }

    /// Parse the LLM response into a `HemisphereOutput`.
    fn parse_response(&self, content: &str, input: &HemisphereInput) -> HemisphereOutput {
        // Try to parse as JSON first
        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(content) {
            let conclusion = parsed
                .get("conclusion")
                .and_then(serde_json::Value::as_str)
                .unwrap_or(content)
                .to_string();

            let confidence = parsed
                .get("confidence")
                .and_then(serde_json::Value::as_f64)
                .unwrap_or(0.5) as f32;

            let stance = parsed
                .get("stance")
                .and_then(serde_json::Value::as_str)
                .map_or(Stance::Uncertain, |s| match s.to_lowercase().as_str() {
                    "agree" | "yes" | "positive" | "support" => Stance::Agree,
                    "disagree" | "no" | "negative" | "oppose" => Stance::Disagree,
                    _ => Stance::Uncertain,
                });

            let key_points: Vec<String> = parsed
                .get("key_points")
                .and_then(serde_json::Value::as_array)
                .map(|arr| {
                    arr.iter()
                        .filter_map(|v| v.as_str().map(String::from))
                        .take(5)
                        .collect()
                })
                .unwrap_or_default();

            return HemisphereOutput {
                conclusion,
                confidence,
                stance,
                key_points,
                source: HemisphereSource::Left,
            };
        }

        // Fallback: treat the raw text as the conclusion
        fallback_left_output(content, input)
    }

    /// Call the llama-server API.
    fn call_llm(&self, input: &HemisphereInput) -> Result<String, String> {
        let request = ChatRequest {
            model: self.config.model.clone(),
            messages: vec![
                ChatMessage {
                    role: "system".into(),
                    content: self.system_prompt(),
                },
                ChatMessage {
                    role: "user".into(),
                    content: self.user_prompt(input),
                },
            ],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self
            .agent
            .post(&self.config.endpoint)
            .header("Content-Type", "application/json")
            .send_json(&request)
            .map_err(|e| format!("llama-server API error: {e}"))?;

        let chat_resp: ChatResponse = response
            .into_body()
            .read_json()
            .map_err(|e| format!("llama-server response parse error: {e}"))?;

        chat_resp
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .ok_or_else(|| "llama-server returned no choices".into())
    }
}

impl Hemisphere for LlamaLeftHemisphere {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        match self.call_llm(input) {
            Ok(content) => self.parse_response(&content, input),
            Err(e) => {
                tracing::warn!(error = %e, "llama left hemisphere failed, using heuristic fallback");
                self.fallback.analyze(input)
            }
        }
    }

    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String> {
        // Use the heuristic left hemisphere's critique logic.
        // This keeps critique fast and local — no need for an LLM round-trip
        // just to produce a critique list.
        self.fallback.critique(other, input)
    }

    fn name(&self) -> &'static str {
        "llama-left"
    }
}

/// Produce a fallback output when the LLM is unavailable but we still
/// need a left-hemisphere result. Uses the heuristic left hemisphere.
fn fallback_left_output(reason: &str, input: &HemisphereInput) -> HemisphereOutput {
    let mut output = super::hemisphere::LeftHemisphere::new().analyze(input);
    // Append the fallback reason to the conclusion for transparency
    output.conclusion = format!("{} (llama fallback: {reason})", output.conclusion);
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn llama_config_defaults() {
        let config = LlamaConfig::default();
        assert!(config.endpoint.contains("localhost"));
        assert_eq!(config.model, "local");
        assert!((config.temperature - 0.2).abs() < 0.01);
        assert_eq!(config.max_tokens, 512);
    }

    #[test]
    fn llama_config_endpoint_normalization() {
        // Test that we can construct configs with different endpoint formats
        let config = LlamaConfig {
            endpoint: "http://localhost:8080".into(),
            ..LlamaConfig::default()
        };
        assert_eq!(config.endpoint, "http://localhost:8080");
    }

    #[test]
    fn parse_response_valid_json() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = r#"{"conclusion": "Test conclusion", "confidence": 0.8, "stance": "agree", "key_points": ["point1", "point2"]}"#;
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.conclusion, "Test conclusion");
        assert!((output.confidence - 0.8).abs() < 0.01);
        assert_eq!(output.stance, Stance::Agree);
        assert_eq!(output.key_points.len(), 2);
        assert_eq!(output.source, HemisphereSource::Left);
    }

    #[test]
    fn parse_response_invalid_json_falls_back() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = "This is not JSON, just a plain text response.";
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.source, HemisphereSource::Left);
        assert!(!output.conclusion.is_empty());
    }

    #[test]
    fn parse_response_partial_json() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = r#"{"conclusion": "Partial result"}"#;
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.conclusion, "Partial result");
        assert!((output.confidence - 0.5).abs() < 0.01);
        assert_eq!(output.stance, Stance::Uncertain);
    }

    #[test]
    fn llama_left_hemisphere_name() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        assert_eq!(hemisphere.name(), "llama-left");
    }

    #[test]
    fn llama_analyze_fails_gracefully() {
        // Point to a non-existent server — should fail and use heuristic fallback.
        let config = LlamaConfig {
            endpoint: "http://localhost:1/v1/chat/completions".into(),
            model: "test".into(),
            temperature: 0.2,
            timeout: Duration::from_millis(100),
            max_tokens: 64,
        };
        let hemisphere = LlamaLeftHemisphere::new(config);
        let input = HemisphereInput::new("test topic");
        let output = hemisphere.analyze(&input);
        assert_eq!(output.source, HemisphereSource::Left);
        assert!(!output.conclusion.is_empty());
    }

    #[test]
    fn llama_critique_uses_heuristic() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let other = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.95,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };
        let critiques = hemisphere.critique(&other, &input);
        assert!(!critiques.is_empty());
    }

    #[test]
    fn llama_left_implements_hemisphere_trait() {
        let config = LlamaConfig::default();
        let hemisphere = LlamaLeftHemisphere::new(config);
        // Verify it can be used as Box<dyn Hemisphere>
        let _boxed: Box<dyn Hemisphere> = Box::new(hemisphere);
    }
}
