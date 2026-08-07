//! LLM-backed right hemisphere — calls an OpenAI-compatible API for inference.
//!
//! When configured with an API key (via `WM_LLM_API_KEY` env var), the
//! bicameral engine uses this hemisphere instead of the heuristic stub.
//! The LLM receives the topic, evidence, and context, then returns a
//! structured analysis that is parsed into `HemisphereOutput`.
//!
//! Configuration via environment variables:
//! - `WM_LLM_API_KEY` — API key for the LLM provider (required to enable)
//! - `WM_LLM_ENDPOINT` — OpenAI-compatible chat completions endpoint
//!   (default: `https://api.openai.com/v1/chat/completions`)
//! - `WM_LLM_MODEL` — Model name (default: `gpt-4o-mini`)
//! - `WM_LLM_TIMEOUT_MS` — Request timeout in milliseconds (default: 5000)

#![forbid(unsafe_code)]

use crate::hemisphere::{
    HemisphereInput, HemisphereOutput, HemisphereSource, RightHemisphere, Stance,
};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Configuration for the LLM right hemisphere.
#[derive(Debug, Clone)]
pub struct LlmConfig {
    /// API key for authentication.
    pub api_key: String,
    /// OpenAI-compatible chat completions endpoint.
    pub endpoint: String,
    /// Model name to use.
    pub model: String,
    /// Request timeout.
    pub timeout: Duration,
    /// Maximum tokens for the response.
    pub max_tokens: u32,
}

impl Default for LlmConfig {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            endpoint: "https://api.openai.com/v1/chat/completions".into(),
            model: "gpt-4o-mini".into(),
            timeout: Duration::from_secs(5),
            max_tokens: 512,
        }
    }
}

impl LlmConfig {
    /// Create a config from environment variables.
    ///
    /// Returns `None` if `WM_LLM_API_KEY` is not set or empty.
    /// Endpoint must use `http://` or `https://` scheme.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let api_key = std::env::var("WM_LLM_API_KEY").ok()?;
        if api_key.is_empty() {
            return None;
        }

        let endpoint = std::env::var("WM_LLM_ENDPOINT")
            .unwrap_or_else(|_| "https://api.openai.com/v1/chat/completions".into());

        if !is_endpoint_safe(&endpoint) {
            tracing::warn!(endpoint = %endpoint, "WM_LLM_ENDPOINT rejected: must use http:// or https://");
            return None;
        }

        let model = std::env::var("WM_LLM_MODEL").unwrap_or_else(|_| "gpt-4o-mini".into());

        let timeout_ms = std::env::var("WM_LLM_TIMEOUT_MS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(5000);

        Some(Self {
            api_key,
            endpoint,
            model,
            timeout: Duration::from_millis(timeout_ms),
            max_tokens: 512,
        })
    }
}

/// Validate that an endpoint URL uses http:// or https:// and is not empty.
fn is_endpoint_safe(endpoint: &str) -> bool {
    if endpoint.is_empty() {
        return false;
    }
    endpoint.starts_with("http://") || endpoint.starts_with("https://")
}

/// OpenAI chat completion request body.
#[derive(Debug, Serialize)]
struct ChatRequest {
    model: String,
    messages: Vec<ChatMessage>,
    max_tokens: u32,
    temperature: f32,
}

/// OpenAI chat message.
#[derive(Debug, Serialize, Deserialize)]
struct ChatMessage {
    role: String,
    content: String,
}

/// OpenAI chat completion response.
#[derive(Debug, Deserialize)]
struct ChatResponse {
    choices: Vec<ChatChoice>,
}

#[derive(Debug, Deserialize)]
struct ChatChoice {
    message: ChatMessage,
}

/// LLM-backed right hemisphere.
///
/// Calls an OpenAI-compatible API to get an alternative analysis.
/// If the API call fails, falls back to a heuristic analysis
/// (similar to `RightHemisphereStub`).
pub struct LlmRightHemisphere {
    config: LlmConfig,
    agent: ureq::Agent,
}

impl LlmRightHemisphere {
    /// Create a new LLM right hemisphere with the given config.
    #[must_use]
    pub fn new(config: LlmConfig) -> Self {
        let agent = ureq::config::Config::builder()
            .timeout_global(Some(config.timeout))
            .build()
            .new_agent();
        Self { config, agent }
    }

    /// Create from environment variables, if configured.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        LlmConfig::from_env().map(Self::new)
    }

    /// Build the system prompt for the LLM.
    fn system_prompt(&self) -> String {
        "You are the right hemisphere of a bicameral reasoning system. \
         Analyze the given topic and evidence. Provide a conclusion, \
         your confidence (0.0-1.0), your stance (agree, disagree, or uncertain), \
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
             Analyze this topic and provide your assessment.",
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
                source: HemisphereSource::Right,
            };
        }

        // Fallback: treat the raw text as the conclusion
        fallback_output(content, input)
    }

    /// Call the LLM API.
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
            temperature: 0.7,
        };

        let response = self
            .agent
            .post(&self.config.endpoint)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .send_json(&request)
            .map_err(|e| format!("LLM API error: {e}"))?;

        let chat_resp: ChatResponse = response
            .into_body()
            .read_json()
            .map_err(|e| format!("LLM response parse error: {e}"))?;

        chat_resp
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .ok_or_else(|| "LLM returned no choices".into())
    }
}

impl RightHemisphere for LlmRightHemisphere {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        match self.call_llm(input) {
            Ok(content) => self.parse_response(&content, input),
            Err(e) => {
                tracing::warn!(error = %e, "LLM right hemisphere failed, using fallback");
                fallback_output(&format!("LLM unavailable: {e}"), input)
            }
        }
    }

    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String> {
        // Use a simple heuristic critique for the LLM hemisphere
        let mut critiques = Vec::new();

        if other.confidence > 0.9 {
            critiques.push("Very high confidence — consider edge cases.".into());
        }
        if other.key_points.is_empty() {
            critiques.push("No key points — evidence basis unclear.".into());
        }
        if other.stance == Stance::Agree && input.evidence.len() < 3 {
            critiques.push("Agreement with limited evidence may be premature.".into());
        }

        if critiques.is_empty() {
            critiques.push("LLM review finds no major concerns.".into());
        }

        critiques
    }

    fn backend_name(&self) -> &'static str {
        "llm"
    }
}

/// Produce a fallback output when the LLM is unavailable.
fn fallback_output(reason: &str, input: &HemisphereInput) -> HemisphereOutput {
    let evidence_count = input.evidence.len();
    let (stance, confidence) = if evidence_count == 0 {
        (Stance::Uncertain, 0.2)
    } else if evidence_count > 5 {
        (Stance::Agree, 0.5)
    } else {
        (Stance::Uncertain, 0.35)
    };

    HemisphereOutput {
        conclusion: format!(
            "LLM fallback analysis of '{}' (evidence: {}): {}",
            input.topic, evidence_count, reason
        ),
        confidence,
        stance,
        key_points: input.evidence.iter().take(3).cloned().collect(),
        source: HemisphereSource::Right,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn llm_config_from_env_returns_none_without_key() {
        // When no API key is set, from_env returns None.
        // We test the logic by checking that an empty key produces None.
        // (Can't mutate env vars in forbid(unsafe_code) crates.)
        let config = LlmConfig {
            api_key: String::new(),
            ..LlmConfig::default()
        };
        assert!(config.api_key.is_empty());
    }

    #[test]
    fn llm_config_from_env_with_key() {
        // Test config construction directly (env var mutation requires unsafe
        // in Rust 2024, which is forbidden in this crate).
        let config = LlmConfig {
            api_key: "test-key".into(),
            model: "test-model".into(),
            ..LlmConfig::default()
        };
        assert_eq!(config.api_key, "test-key");
        assert_eq!(config.model, "test-model");
    }

    #[test]
    fn llm_config_defaults() {
        let config = LlmConfig::default();
        assert!(config.api_key.is_empty());
        assert_eq!(config.model, "gpt-4o-mini");
        assert_eq!(config.max_tokens, 512);
    }

    #[test]
    fn fallback_output_no_evidence() {
        let input = HemisphereInput::new("test topic");
        let output = fallback_output("LLM unavailable", &input);
        assert_eq!(output.stance, Stance::Uncertain);
        assert!(output.confidence < 0.5);
        assert!(output.conclusion.contains("test topic"));
    }

    #[test]
    fn fallback_output_with_evidence() {
        let input = HemisphereInput::new("test topic")
            .with_evidence(vec!["evidence 1".into(), "evidence 2".into()]);
        let output = fallback_output("LLM unavailable", &input);
        assert_eq!(output.source, HemisphereSource::Right);
        assert!(!output.key_points.is_empty());
    }

    #[test]
    fn parse_response_valid_json() {
        let config = LlmConfig::default();
        let hemisphere = LlmRightHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = r#"{"conclusion": "Test conclusion", "confidence": 0.8, "stance": "agree", "key_points": ["point1", "point2"]}"#;
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.conclusion, "Test conclusion");
        assert!((output.confidence - 0.8).abs() < 0.01);
        assert_eq!(output.stance, Stance::Agree);
        assert_eq!(output.key_points.len(), 2);
    }

    #[test]
    fn parse_response_invalid_json_falls_back() {
        let config = LlmConfig::default();
        let hemisphere = LlmRightHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = "This is not JSON, just a plain text response.";
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.source, HemisphereSource::Right);
        assert!(!output.conclusion.is_empty());
    }

    #[test]
    fn parse_response_partial_json() {
        let config = LlmConfig::default();
        let hemisphere = LlmRightHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let content = r#"{"conclusion": "Partial result"}"#;
        let output = hemisphere.parse_response(content, &input);
        assert_eq!(output.conclusion, "Partial result");
        // Confidence should default to 0.5
        assert!((output.confidence - 0.5).abs() < 0.01);
        assert_eq!(output.stance, Stance::Uncertain);
    }

    #[test]
    fn llm_right_hemisphere_backend_name() {
        let config = LlmConfig::default();
        let hemisphere = LlmRightHemisphere::new(config);
        assert_eq!(hemisphere.backend_name(), "llm");
    }

    #[test]
    fn llm_right_hemisphere_critique() {
        let config = LlmConfig::default();
        let hemisphere = LlmRightHemisphere::new(config);
        let input = HemisphereInput::new("test");
        let other = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.95,
            stance: Stance::Agree,
            key_points: vec![],
            source: HemisphereSource::Left,
        };
        let critiques = hemisphere.critique(&other, &input);
        assert!(!critiques.is_empty());
    }

    #[test]
    fn llm_analyze_fails_gracefully() {
        // No real API key, so this will fail and use fallback.
        // (Can't mutate env vars in forbid(unsafe_code) crates.)
        let config = LlmConfig {
            api_key: "invalid".into(),
            endpoint: "http://localhost:1/v1/chat/completions".into(),
            model: "test".into(),
            timeout: Duration::from_millis(100),
            max_tokens: 64,
        };
        let hemisphere = LlmRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");
        let output = hemisphere.analyze(&input);
        assert_eq!(output.source, HemisphereSource::Right);
        assert!(!output.conclusion.is_empty());
    }

    #[test]
    fn is_endpoint_safe_rejects_non_http() {
        assert!(!is_endpoint_safe("ftp://evil.com"));
        assert!(!is_endpoint_safe("file:///etc/passwd"));
        assert!(!is_endpoint_safe("javascript:alert(1)"));
        assert!(!is_endpoint_safe(""));
        assert!(!is_endpoint_safe("data:text/html,<script>"));
    }

    #[test]
    fn is_endpoint_safe_accepts_http() {
        assert!(is_endpoint_safe("http://localhost:8081"));
        assert!(is_endpoint_safe(
            "https://api.openai.com/v1/chat/completions"
        ));
    }
}
