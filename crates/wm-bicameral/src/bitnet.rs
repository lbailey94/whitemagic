//! BitNet right hemisphere — local 1.58-bit LLM for creative reasoning.
//!
//! BitNet (bitnet_b1_58) provides a local, CPU-friendly 1.58-bit model
//! that runs via `llama-cli` subprocess or `llama-server` HTTP API.
//! High temperature (0.7–1.0) is used for creative, divergent output —
//! complementing the left hemisphere's deterministic analysis.
//!
//! Configuration via environment variables:
//! - `WM_BITNET_ENABLED` — enable/disable (1/0, default 0)
//! - `WM_BITNET_ENDPOINT` — HTTP endpoint for llama-server serving BitNet
//! - `WM_BITNET_MODEL` — model name/path for HTTP mode
//! - `WM_BITNET_LLAMA_CLI` — path to llama-cli binary for subprocess mode
//! - `WM_BITNET_MODEL_PATH` — path to BitNet GGUF model file (subprocess mode)
//! - `WM_BITNET_TEMP` — temperature (default 0.8, high for creative output)
//! - `WM_BITNET_TIMEOUT_MS` — request/inference timeout (default 60000)
//! - `WM_BITNET_MAX_TOKENS` — max tokens for response (default 512)
//!
//! HTTP mode is preferred (persistent server, lower latency). Subprocess
//! mode spawns `llama-cli` per inference call (higher latency, no server needed).
//! If neither is configured, falls back to `RightHemisphereStub`.

#![forbid(unsafe_code)]

use crate::hemisphere::{
    HemisphereInput, HemisphereOutput, HemisphereSource, RightHemisphere, Stance,
};
use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Configuration for the BitNet right hemisphere.
#[derive(Debug, Clone)]
pub struct BitNetConfig {
    /// HTTP endpoint for llama-server (e.g. http://localhost:8081).
    /// If set, HTTP mode is used. If empty, subprocess mode is attempted.
    pub endpoint: String,
    /// Model name for HTTP mode (sent in chat completions request).
    pub model: String,
    /// Path to llama-cli binary for subprocess mode.
    pub llama_cli: String,
    /// Path to BitNet GGUF model file for subprocess mode.
    pub model_path: String,
    /// Temperature for generation (high = creative, default 0.8).
    pub temperature: f32,
    /// Request/inference timeout.
    pub timeout: Duration,
    /// Maximum tokens for the response.
    pub max_tokens: u32,
}

impl Default for BitNetConfig {
    fn default() -> Self {
        Self {
            endpoint: String::new(),
            model: "bitnet-b1.58".into(),
            llama_cli: String::new(),
            model_path: String::new(),
            temperature: 0.8,
            timeout: Duration::from_secs(60),
            max_tokens: 512,
        }
    }
}

impl BitNetConfig {
    /// Create a config from environment variables.
    ///
    /// Returns `None` if `WM_BITNET_ENABLED` is not "1" or if neither
    /// `WM_BITNET_ENDPOINT` nor `WM_BITNET_LLAMA_CLI` is set.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        let enabled = std::env::var("WM_BITNET_ENABLED")
            .is_ok_and(|v| v == "1" || v.eq_ignore_ascii_case("true"));

        if !enabled {
            return None;
        }

        let endpoint = std::env::var("WM_BITNET_ENDPOINT").unwrap_or_default();
        let llama_cli = std::env::var("WM_BITNET_LLAMA_CLI").unwrap_or_default();
        let model_path = std::env::var("WM_BITNET_MODEL_PATH").unwrap_or_default();

        // Validate endpoint if set
        if !endpoint.is_empty() && !is_endpoint_safe(&endpoint) {
            tracing::warn!(endpoint = %endpoint, "WM_BITNET_ENDPOINT rejected: must use http:// or https://");
            return None;
        }

        // Need at least one mode configured
        if endpoint.is_empty() && llama_cli.is_empty() {
            return None;
        }

        let model = std::env::var("WM_BITNET_MODEL").unwrap_or_else(|_| "bitnet-b1.58".into());
        let temperature = std::env::var("WM_BITNET_TEMP")
            .ok()
            .and_then(|s| s.parse::<f32>().ok())
            .unwrap_or(0.8);
        let timeout_ms = std::env::var("WM_BITNET_TIMEOUT_MS")
            .ok()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(60_000);
        let max_tokens = std::env::var("WM_BITNET_MAX_TOKENS")
            .ok()
            .and_then(|s| s.parse::<u32>().ok())
            .unwrap_or(512);

        Some(Self {
            endpoint,
            model,
            llama_cli,
            model_path,
            temperature,
            timeout: Duration::from_millis(timeout_ms),
            max_tokens,
        })
    }

    /// Check if HTTP mode is configured.
    #[must_use]
    pub fn is_http_mode(&self) -> bool {
        !self.endpoint.is_empty()
    }

    /// Check if subprocess mode is configured.
    #[must_use]
    pub fn is_subprocess_mode(&self) -> bool {
        !self.llama_cli.is_empty() && !self.model_path.is_empty()
    }
}

/// Validate that an endpoint URL uses http:// or https:// and is not empty.
fn is_endpoint_safe(endpoint: &str) -> bool {
    if endpoint.is_empty() {
        return false;
    }
    endpoint.starts_with("http://") || endpoint.starts_with("https://")
}

/// OpenAI chat completion request body (reused for HTTP mode).
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

/// BitNet-backed right hemisphere.
///
/// Uses high temperature for creative, divergent output — complementing
/// the left hemisphere's deterministic analysis. Falls back to heuristic
/// `RightHemisphereStub` logic on failure.
pub struct BitNetRightHemisphere {
    config: BitNetConfig,
    agent: Option<ureq::Agent>,
}

impl BitNetRightHemisphere {
    /// Create a new BitNet right hemisphere with the given config.
    #[must_use]
    pub fn new(config: BitNetConfig) -> Self {
        let agent = if config.is_http_mode() {
            let agent = ureq::config::Config::builder()
                .timeout_global(Some(config.timeout))
                .build()
                .new_agent();
            Some(agent)
        } else {
            None
        };

        Self { config, agent }
    }

    /// Create from environment variables, if configured.
    #[must_use]
    pub fn from_env() -> Option<Self> {
        BitNetConfig::from_env().map(Self::new)
    }

    /// Build the system prompt for BitNet.
    fn system_prompt(&self) -> String {
        "You are the right hemisphere of a bicameral reasoning system. \
         Your role is to provide creative, divergent analysis. \
         Think laterally, challenge assumptions, and explore alternative perspectives. \
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
             Analyze this topic creatively and provide your assessment.",
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

    /// Call the BitNet model via HTTP (llama-server).
    fn call_http(&self, input: &HemisphereInput) -> Result<String, String> {
        let endpoint = if self.config.endpoint.ends_with("/v1/chat/completions") {
            self.config.endpoint.clone()
        } else if self.config.endpoint.ends_with('/') {
            format!("{}v1/chat/completions", self.config.endpoint)
        } else {
            format!("{}/v1/chat/completions", self.config.endpoint)
        };

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

        let agent = self
            .agent
            .as_ref()
            .ok_or_else(|| "HTTP agent not initialized".to_string())?;

        let response = agent
            .post(&endpoint)
            .header("Content-Type", "application/json")
            .send_json(&request)
            .map_err(|e| format!("BitNet HTTP error: {e}"))?;

        let chat_resp: ChatResponse = response
            .into_body()
            .read_json()
            .map_err(|e| format!("BitNet response parse error: {e}"))?;

        chat_resp
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .ok_or_else(|| "BitNet returned no choices".into())
    }

    /// Call the BitNet model via subprocess (llama-cli).
    fn call_subprocess(&self, input: &HemisphereInput) -> Result<String, String> {
        use std::process::Command;

        let prompt = format!("{}\n\n{}", self.system_prompt(), self.user_prompt(input));

        let output = Command::new(&self.config.llama_cli)
            .arg("-m")
            .arg(&self.config.model_path)
            .arg("-n")
            .arg(self.config.max_tokens.to_string())
            .arg("-p")
            .arg(&prompt)
            .arg("-ngl")
            .arg("0")
            .arg("-c")
            .arg("2048")
            .arg("--temp")
            .arg(self.config.temperature.to_string())
            .arg("-b")
            .arg("1")
            .arg("--log-disable")
            .output()
            .map_err(|e| format!("llama-cli spawn error: {e}"))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(format!(
                "llama-cli failed: {}",
                stderr.chars().take(200).collect::<String>()
            ));
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        Ok(stdout.into_owned())
    }

    /// Call the BitNet model (HTTP or subprocess depending on config).
    fn call_bitnet(&self, input: &HemisphereInput) -> Result<String, String> {
        if self.config.is_http_mode() {
            self.call_http(input)
        } else if self.config.is_subprocess_mode() {
            self.call_subprocess(input)
        } else {
            Err("no BitNet backend configured".into())
        }
    }
}

impl RightHemisphere for BitNetRightHemisphere {
    fn analyze(&self, input: &HemisphereInput) -> HemisphereOutput {
        match self.call_bitnet(input) {
            Ok(content) => self.parse_response(&content, input),
            Err(e) => {
                tracing::warn!(error = %e, "BitNet right hemisphere failed, using fallback");
                fallback_output(&format!("BitNet unavailable: {e}"), input)
            }
        }
    }

    fn critique(&self, other: &HemisphereOutput, input: &HemisphereInput) -> Vec<String> {
        // Use heuristic critique — no need for another LLM call
        let mut critiques = Vec::new();

        if other.confidence > 0.9 {
            critiques.push(
                "Very high confidence — creative analysis should embrace uncertainty.".into(),
            );
        }
        if other.key_points.is_empty() {
            critiques.push("No key points — divergent thinking needs concrete outputs.".into());
        }
        if other.stance == Stance::Agree && input.evidence.len() < 3 {
            critiques
                .push("Quick agreement with limited evidence — explore more alternatives.".into());
        }
        if other.conclusion.len() < 20 {
            critiques.push("Brief conclusion — elaborate on creative insights.".into());
        }

        if critiques.is_empty() {
            critiques.push("BitNet review finds the analysis sufficiently creative.".into());
        }

        critiques
    }

    fn backend_name(&self) -> &'static str {
        "bitnet"
    }
}

/// Produce a fallback output when BitNet is unavailable.
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
            "BitNet fallback analysis of '{}' (evidence: {}): {}",
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
    fn bitnet_config_defaults() {
        let config = BitNetConfig::default();
        assert!((config.temperature - 0.8).abs() < 0.01);
        assert_eq!(config.max_tokens, 512);
        assert!(config.endpoint.is_empty());
        assert!(config.llama_cli.is_empty());
    }

    #[test]
    fn bitnet_config_http_mode() {
        let config = BitNetConfig {
            endpoint: "http://localhost:8081".into(),
            ..BitNetConfig::default()
        };
        assert!(config.is_http_mode());
        assert!(!config.is_subprocess_mode());
    }

    #[test]
    fn bitnet_config_subprocess_mode() {
        let config = BitNetConfig {
            llama_cli: "/usr/bin/llama-cli".into(),
            model_path: "/models/bitnet.gguf".into(),
            ..BitNetConfig::default()
        };
        assert!(!config.is_http_mode());
        assert!(config.is_subprocess_mode());
    }

    #[test]
    fn bitnet_config_no_mode() {
        let config = BitNetConfig::default();
        assert!(!config.is_http_mode());
        assert!(!config.is_subprocess_mode());
    }

    #[test]
    fn bitnet_right_hemisphere_backend_name() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        assert_eq!(hemisphere.backend_name(), "bitnet");
    }

    #[test]
    fn bitnet_right_hemisphere_implements_trait() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        // Verify it implements RightHemisphere
        fn assert_trait<T: RightHemisphere + ?Sized>(_: &T) {}
        assert_trait(&hemisphere);
    }

    #[test]
    fn bitnet_parse_response_valid_json() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic").with_evidence(vec!["evidence 1".into()]);

        let json = r#"{"conclusion": "Creative analysis", "confidence": 0.7, "stance": "agree", "key_points": ["point 1", "point 2"]}"#;
        let output = hemisphere.parse_response(json, &input);

        assert_eq!(output.conclusion, "Creative analysis");
        assert!((output.confidence - 0.7).abs() < 0.01);
        assert_eq!(output.stance, Stance::Agree);
        assert_eq!(output.key_points.len(), 2);
        assert_eq!(output.source, HemisphereSource::Right);
    }

    #[test]
    fn bitnet_parse_response_invalid_json_falls_back() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");

        let output = hemisphere.parse_response("not valid json", &input);
        assert!(output.conclusion.contains("not valid json"));
        assert_eq!(output.source, HemisphereSource::Right);
    }

    #[test]
    fn bitnet_parse_response_partial_json() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");

        // JSON with missing fields — should use defaults
        let json = r#"{"conclusion": "Partial analysis"}"#;
        let output = hemisphere.parse_response(json, &input);

        assert_eq!(output.conclusion, "Partial analysis");
        assert!((output.confidence - 0.5).abs() < 0.01);
        assert_eq!(output.stance, Stance::Uncertain);
    }

    #[test]
    fn bitnet_fallback_output_no_evidence() {
        let input = HemisphereInput::new("test topic");
        let output = fallback_output("test reason", &input);

        assert!(output.conclusion.contains("test reason"));
        assert_eq!(output.stance, Stance::Uncertain);
        assert!((output.confidence - 0.2).abs() < 0.01);
        assert_eq!(output.source, HemisphereSource::Right);
    }

    #[test]
    fn bitnet_fallback_output_with_evidence() {
        let input = HemisphereInput::new("test topic").with_evidence(vec![
            "e1".into(),
            "e2".into(),
            "e3".into(),
        ]);
        let output = fallback_output("test reason", &input);

        assert_eq!(output.stance, Stance::Uncertain);
        assert!((output.confidence - 0.35).abs() < 0.01);
        assert_eq!(output.key_points.len(), 3);
    }

    #[test]
    fn bitnet_fallback_output_much_evidence() {
        let input = HemisphereInput::new("test topic").with_evidence(vec![
            "e1".into(),
            "e2".into(),
            "e3".into(),
            "e4".into(),
            "e5".into(),
            "e6".into(),
        ]);
        let output = fallback_output("test reason", &input);

        assert_eq!(output.stance, Stance::Agree);
        assert!((output.confidence - 0.5).abs() < 0.01);
    }

    #[test]
    fn bitnet_critique_high_confidence() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");
        let output = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.95,
            stance: Stance::Agree,
            key_points: vec!["point".into()],
            source: HemisphereSource::Right,
        };

        let critiques = hemisphere.critique(&output, &input);
        assert!(critiques.iter().any(|c| c.contains("high confidence")));
    }

    #[test]
    fn bitnet_critique_no_key_points() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");
        let output = HemisphereOutput {
            conclusion: "test".into(),
            confidence: 0.5,
            stance: Stance::Uncertain,
            key_points: vec![],
            source: HemisphereSource::Right,
        };

        let critiques = hemisphere.critique(&output, &input);
        assert!(critiques.iter().any(|c| c.contains("No key points")));
    }

    #[test]
    fn bitnet_critique_no_concerns() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic").with_evidence(vec![
            "e1".into(),
            "e2".into(),
            "e3".into(),
        ]);
        let output = HemisphereOutput {
            conclusion: "A sufficiently detailed conclusion here".into(),
            confidence: 0.6,
            stance: Stance::Uncertain,
            key_points: vec!["point 1".into(), "point 2".into()],
            source: HemisphereSource::Right,
        };

        let critiques = hemisphere.critique(&output, &input);
        assert!(
            critiques
                .iter()
                .any(|c| c.contains("no major concerns") || c.contains("sufficiently creative"))
        );
    }

    #[test]
    fn bitnet_analyze_fails_gracefully() {
        let config = BitNetConfig::default();
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test topic");

        // No backend configured → should fall back gracefully
        let output = hemisphere.analyze(&input);
        assert!(output.conclusion.contains("BitNet unavailable"));
        assert_eq!(output.source, HemisphereSource::Right);
    }

    #[test]
    fn bitnet_http_endpoint_normalization() {
        let config = BitNetConfig {
            endpoint: "http://localhost:65535".into(),
            ..BitNetConfig::default()
        };
        let hemisphere = BitNetRightHemisphere::new(config);
        let input = HemisphereInput::new("test");

        // This will fail (no server) but should produce fallback
        let output = hemisphere.analyze(&input);
        assert!(output.conclusion.contains("BitNet unavailable"));
    }
}
