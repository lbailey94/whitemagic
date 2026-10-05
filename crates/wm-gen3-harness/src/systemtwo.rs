//! wm-gen3-harness::systemtwo — System Two local generative consultancy.
//!
//! Opt-in [5/5]-style escalation above the local ladder: asks an
//! OpenAI-compatible local endpoint (ollama / llama-server) with explicit
//! context, signs a `continuity-receipt/2#consultation`, and fails closed on
//! remote endpoints unless `WM_SYSTEM2_ALLOW_REMOTE=1`.

use std::io::{Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;
use wm_gen3_core::mandala::{Signature, Signer, SigningKey, Verifier, VerifyingKey};

pub const SYSTEM2_SPEC: &str = "continuity-receipt/2#consultation";
pub const PROMPT_VERSION: &str = "system2-ask-v1";

pub const ENV_ENDPOINT: &str = "WM_SYSTEM2_ENDPOINT";
pub const ENV_MODEL: &str = "WM_SYSTEM2_MODEL";
pub const ENV_MAX_TOKENS: &str = "WM_SYSTEM2_MAX_TOKENS";
pub const ENV_TIMEOUT_MS: &str = "WM_SYSTEM2_TIMEOUT_MS";
pub const ENV_ALLOW_REMOTE: &str = "WM_SYSTEM2_ALLOW_REMOTE";

pub const V9_FG_ENDPOINT: &str = "WM_LLAMA_FG_ENDPOINT";
pub const V9_MODEL: &str = "WM_LLAMA_MODEL";
pub const V9_TIMEOUT_MS: &str = "WM_LLAMA_TIMEOUT_MS";

pub const DEFAULT_ENDPOINT: &str = "http://127.0.0.1:11434/v1";
pub const DEFAULT_MODEL: &str = "gemma4:e2b";
pub const DEFAULT_MAX_TOKENS: u32 = 1024;
pub const DEFAULT_TIMEOUT_MS: u64 = 30_000;

pub const SYSTEM_PROMPT: &str = "You are System Two, a grounded local assistant. Answer in one or two sentences using only the provided context. If the context does not contain the answer, say so.";

#[derive(Debug, Clone, PartialEq)]
pub struct SystemTwoConfig {
    pub endpoint: String,
    pub model: String,
    pub max_tokens: u32,
    pub timeout_ms: u64,
    pub allow_remote: bool,
}

fn parse_env_u32(name: &str) -> Result<Option<u32>, String> {
    match std::env::var(name) {
        Ok(v) if !v.trim().is_empty() => v
            .trim()
            .parse::<u32>()
            .map(Some)
            .map_err(|e| format!("system2: invalid {name}={v}: {e}")),
        _ => Ok(None),
    }
}

fn parse_env_u64(name: &str) -> Result<Option<u64>, String> {
    match std::env::var(name) {
        Ok(v) if !v.trim().is_empty() => v
            .trim()
            .parse::<u64>()
            .map(Some)
            .map_err(|e| format!("system2: invalid {name}={v}: {e}")),
        _ => Ok(None),
    }
}

fn env_flag(name: &str) -> bool {
    std::env::var(name)
        .map(|v| matches!(v.as_str(), "1" | "true" | "TRUE" | "True"))
        .unwrap_or(false)
}

fn env_nonempty(name: &str) -> Option<String> {
    std::env::var(name).ok().filter(|v| !v.trim().is_empty())
}

impl SystemTwoConfig {
    pub fn from_env() -> Result<Self, String> {
        let endpoint = env_nonempty(ENV_ENDPOINT)
            .or_else(|| env_nonempty(V9_FG_ENDPOINT))
            .unwrap_or_else(|| DEFAULT_ENDPOINT.to_string());
        let model = env_nonempty(ENV_MODEL)
            .or_else(|| env_nonempty(V9_MODEL))
            .unwrap_or_else(|| DEFAULT_MODEL.to_string());
        let max_tokens = parse_env_u32(ENV_MAX_TOKENS)?.unwrap_or(DEFAULT_MAX_TOKENS);
        let timeout_ms = parse_env_u64(ENV_TIMEOUT_MS)?
            .or(parse_env_u64(V9_TIMEOUT_MS)?)
            .unwrap_or(DEFAULT_TIMEOUT_MS);
        Ok(Self {
            endpoint,
            model,
            max_tokens,
            timeout_ms,
            allow_remote: env_flag(ENV_ALLOW_REMOTE),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HttpTarget {
    pub host: String,
    pub port: u16,
    pub path: String,
}

pub fn is_loopback_host(host: &str) -> bool {
    matches!(host, "127.0.0.1" | "localhost" | "::1" | "[::1]")
}

pub fn parse_http_target(endpoint: &str) -> Result<HttpTarget, String> {
    let rest = endpoint.strip_prefix("http://").ok_or_else(|| {
        if endpoint.starts_with("https://") {
            "system2: https endpoints are not supported (local http only)".to_string()
        } else {
            format!("system2: endpoint must start with http:// (got {endpoint})")
        }
    })?;
    let (authority, base_path) = match rest.split_once('/') {
        Some((a, p)) => (a, format!("/{}", p.trim_end_matches('/'))),
        None => (rest, String::new()),
    };
    if authority.is_empty() {
        return Err("system2: endpoint has no host".to_string());
    }
    let (host, port) = match authority.rsplit_once(':') {
        Some((h, p)) if !h.is_empty() => (
            h.to_string(),
            p.parse::<u16>()
                .map_err(|_| format!("system2: invalid port in endpoint: {endpoint}"))?,
        ),
        _ => (authority.to_string(), 80u16),
    };
    if host.is_empty() {
        return Err("system2: endpoint has no host".to_string());
    }
    let path = if base_path.is_empty() {
        "/chat/completions".to_string()
    } else {
        format!("{base_path}/chat/completions")
    };
    Ok(HttpTarget { host, port, path })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemTwoAnswer {
    pub content: String,
    pub model: String,
    pub endpoint: String,
    pub latency_ms: f64,
    pub max_tokens: u32,
    pub completion_tokens: Option<u64>,
}

pub fn build_request_body(
    config: &SystemTwoConfig,
    question: &str,
    context: Option<&str>,
) -> String {
    let user_content = match context {
        Some(ctx) if !ctx.trim().is_empty() => {
            format!("Context:\n{ctx}\n\nQuestion: {question}")
        }
        _ => question.to_string(),
    };
    serde_json::json!({
        "model": config.model,
        "messages": [
            { "role": "system", "content": SYSTEM_PROMPT },
            { "role": "user", "content": user_content }
        ],
        "max_tokens": config.max_tokens,
        "stream": false
    })
    .to_string()
}

pub fn extract_content(body: &str) -> Result<(String, Option<u64>), String> {
    let value: serde_json::Value =
        serde_json::from_str(body).map_err(|e| format!("system2: response is not JSON: {e}"))?;
    let message = value
        .pointer("/choices/0/message")
        .ok_or_else(|| "system2: response has no choices[0].message".to_string())?;
    let content = message
        .get("content")
        .and_then(|c| c.as_str())
        .unwrap_or_default()
        .to_string();
    if content.trim().is_empty() {
        let reasoning = message
            .get("reasoning")
            .and_then(|r| r.as_str())
            .unwrap_or_default();
        if !reasoning.trim().is_empty() {
            return Err(format!(
                "system2: model returned reasoning tokens only (max_tokens={}); raise WM_SYSTEM2_MAX_TOKENS",
                DEFAULT_MAX_TOKENS
            ));
        }
        return Err("system2: response content is empty".to_string());
    }
    let completion_tokens = value
        .pointer("/usage/completion_tokens")
        .and_then(|v| v.as_u64());
    Ok((content, completion_tokens))
}

fn decode_chunked(body: &[u8]) -> Result<Vec<u8>, String> {
    let mut pos = 0usize;
    let mut out = Vec::new();
    loop {
        let line_end = body[pos..]
            .windows(2)
            .position(|w| w == b"\r\n")
            .map(|p| pos + p)
            .ok_or_else(|| "system2: malformed chunked body (no size line)".to_string())?;
        let size_line = std::str::from_utf8(&body[pos..line_end])
            .map_err(|_| "system2: malformed chunk size".to_string())?;
        let size_hex = size_line.split(';').next().unwrap_or("").trim();
        let size = usize::from_str_radix(size_hex, 16)
            .map_err(|_| format!("system2: invalid chunk size {size_hex:?}"))?;
        pos = line_end + 2;
        if size == 0 {
            break;
        }
        if pos + size > body.len() {
            return Err("system2: truncated chunked body".to_string());
        }
        out.extend_from_slice(&body[pos..pos + size]);
        pos += size + 2;
    }
    Ok(out)
}

fn split_http_response(raw: &[u8]) -> Result<(u16, Vec<u8>), String> {
    let header_end = raw
        .windows(4)
        .position(|w| w == b"\r\n\r\n")
        .ok_or_else(|| "system2: malformed HTTP response (no header end)".to_string())?;
    let headers = std::str::from_utf8(&raw[..header_end])
        .map_err(|_| "system2: non-UTF8 HTTP headers".to_string())?;
    let status = headers
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse::<u16>().ok())
        .ok_or_else(|| "system2: malformed HTTP status line".to_string())?;
    let body = &raw[header_end + 4..];
    let chunked = headers.lines().any(|line| {
        let lower = line.to_ascii_lowercase();
        lower.starts_with("transfer-encoding:") && lower.contains("chunked")
    });
    let decoded = if chunked {
        decode_chunked(body)?
    } else {
        body.to_vec()
    };
    Ok((status, decoded))
}

fn http_post_json(target: &HttpTarget, body: &str, timeout: Duration) -> Result<String, String> {
    let addr = (target.host.as_str(), target.port)
        .to_socket_addrs()
        .map_err(|e| format!("system2: cannot resolve {}: {e}", target.host))?
        .next()
        .ok_or_else(|| format!("system2: no address for {}", target.host))?;
    let mut stream = TcpStream::connect_timeout(&addr, timeout).map_err(|e| {
        format!(
            "system2: connect {}:{} failed: {e}",
            target.host, target.port
        )
    })?;
    stream
        .set_read_timeout(Some(timeout))
        .map_err(|e| e.to_string())?;
    stream
        .set_write_timeout(Some(timeout))
        .map_err(|e| e.to_string())?;

    let request = format!(
        "POST {} HTTP/1.1\r\nHost: {}:{}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        target.path,
        target.host,
        target.port,
        body.len(),
        body
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|e| format!("system2: request write failed: {e}"))?;
    let mut raw = Vec::new();
    stream
        .read_to_end(&mut raw)
        .map_err(|e| format!("system2: response read failed: {e}"))?;

    let (status, decoded) = split_http_response(&raw)?;
    let text = String::from_utf8_lossy(&decoded).to_string();
    if !(200..300).contains(&status) {
        let excerpt: String = text.chars().take(400).collect();
        return Err(format!(
            "system2: endpoint returned HTTP {status}: {excerpt}"
        ));
    }
    Ok(text)
}

pub fn ask(
    config: &SystemTwoConfig,
    question: &str,
    context: Option<&str>,
) -> Result<SystemTwoAnswer, String> {
    if question.trim().is_empty() {
        return Err("system2: question is empty".to_string());
    }
    let target = parse_http_target(&config.endpoint)?;
    if !is_loopback_host(&target.host) && !config.allow_remote {
        return Err(format!(
            "system2: endpoint {} is not loopback; set {ENV_ALLOW_REMOTE}=1 to allow egress",
            config.endpoint
        ));
    }
    let body = build_request_body(config, question, context);
    let started = Instant::now();
    let response = http_post_json(&target, &body, Duration::from_millis(config.timeout_ms))?;
    let latency_ms = started.elapsed().as_secs_f64() * 1000.0;
    let (content, completion_tokens) = extract_content(&response)?;
    Ok(SystemTwoAnswer {
        content,
        model: config.model.clone(),
        endpoint: config.endpoint.clone(),
        latency_ms,
        max_tokens: config.max_tokens,
        completion_tokens,
    })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsultationReceipt {
    pub spec: String,
    pub receipt_id: String,
    pub timestamp_ms: u64,
    pub question_digest: String,
    pub response_digest: String,
    pub model: String,
    pub endpoint: String,
    pub prompt_version: String,
    pub max_tokens: u32,
    pub latency_ms: f64,
    pub issuer_did: String,
    pub signature: String,
}

impl ConsultationReceipt {
    #[allow(clippy::too_many_arguments)]
    pub fn canonical_payload(
        receipt_id: &str,
        question_digest: &str,
        response_digest: &str,
        model: &str,
        endpoint: &str,
        prompt_version: &str,
        max_tokens: u32,
        latency_ms: f64,
        timestamp_ms: u64,
    ) -> String {
        format!(
            "WHITEMAGIC:RECEIPT:2|id:{receipt_id}|q:{question_digest}|r:{response_digest}|model:{model}|endpoint:{endpoint}|prompt:{prompt_version}|max_tokens:{max_tokens}|latency:{latency_ms:.3}|time:{timestamp_ms}"
        )
    }

    pub fn sign(signing_key: &SigningKey, question: &str, answer: &SystemTwoAnswer) -> Self {
        let receipt_id = Uuid::new_v4().to_string();
        let timestamp_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;
        let question_digest = sha256_hex(question.as_bytes());
        let response_digest = sha256_hex(answer.content.as_bytes());
        let issuer_did = format!(
            "did:key:{}",
            hex_encode(&signing_key.verifying_key().to_bytes())
        );
        let payload = Self::canonical_payload(
            &receipt_id,
            &question_digest,
            &response_digest,
            &answer.model,
            &answer.endpoint,
            PROMPT_VERSION,
            answer.max_tokens,
            answer.latency_ms,
            timestamp_ms,
        );
        let signature = hex_encode(&signing_key.sign(payload.as_bytes()).to_bytes());
        Self {
            spec: SYSTEM2_SPEC.to_string(),
            receipt_id,
            timestamp_ms,
            question_digest,
            response_digest,
            model: answer.model.clone(),
            endpoint: answer.endpoint.clone(),
            prompt_version: PROMPT_VERSION.to_string(),
            max_tokens: answer.max_tokens,
            latency_ms: answer.latency_ms,
            issuer_did,
            signature,
        }
    }

    pub fn verify(&self) -> Result<(), String> {
        let pubkey_hex = self
            .issuer_did
            .strip_prefix("did:key:")
            .ok_or_else(|| "missing did:key: prefix".to_string())?;
        let mut pubkey_bytes = [0u8; 32];
        decode_hex(pubkey_hex, &mut pubkey_bytes)?;
        let verifying_key =
            VerifyingKey::from_bytes(&pubkey_bytes).map_err(|e| format!("invalid key: {e}"))?;
        let mut sig_bytes = [0u8; 64];
        decode_hex(&self.signature, &mut sig_bytes)?;
        let signature = Signature::from_bytes(&sig_bytes);
        let payload = Self::canonical_payload(
            &self.receipt_id,
            &self.question_digest,
            &self.response_digest,
            &self.model,
            &self.endpoint,
            &self.prompt_version,
            self.max_tokens,
            self.latency_ms,
            self.timestamp_ms,
        );
        verifying_key
            .verify(payload.as_bytes(), &signature)
            .map_err(|e| format!("consultation receipt signature invalid: {e}"))
    }

    pub fn persist(&self, store_path: &Path) -> std::io::Result<PathBuf> {
        let receipts_dir = store_path.join("receipts");
        std::fs::create_dir_all(&receipts_dir)?;
        let file_path = receipts_dir.join(format!("system2-{}.json", self.receipt_id));
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(&file_path, content)?;
        Ok(file_path)
    }
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn decode_hex<const N: usize>(hex_str: &str, out: &mut [u8; N]) -> Result<(), String> {
    if hex_str.len() != N * 2 {
        return Err(format!(
            "expected {} hex characters, got {}",
            N * 2,
            hex_str.len()
        ));
    }
    for i in 0..N {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16)
            .map_err(|e| format!("bad hex char at {}: {e}", i * 2))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_default_endpoint() {
        let target = parse_http_target(DEFAULT_ENDPOINT).expect("parse");
        assert_eq!(target.host, "127.0.0.1");
        assert_eq!(target.port, 11434);
        assert_eq!(target.path, "/v1/chat/completions");
    }

    #[test]
    fn parse_endpoint_without_path_or_port() {
        let target = parse_http_target("http://localhost").expect("parse");
        assert_eq!(target.host, "localhost");
        assert_eq!(target.port, 80);
        assert_eq!(target.path, "/chat/completions");
    }

    #[test]
    fn https_is_rejected() {
        assert!(parse_http_target("https://api.example.com/v1").is_err());
    }

    #[test]
    fn loopback_hosts_are_recognized() {
        assert!(is_loopback_host("127.0.0.1"));
        assert!(is_loopback_host("localhost"));
        assert!(is_loopback_host("::1"));
        assert!(!is_loopback_host("10.0.0.5"));
    }

    #[test]
    fn chunked_body_decodes() {
        let body = b"4\r\nWiki\r\n5\r\npedia\r\n0\r\n\r\n";
        assert_eq!(decode_chunked(body).unwrap(), b"Wikipedia");
    }

    #[test]
    fn response_split_handles_chunked_and_headers() {
        let raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n\r\n";
        let (status, body) = split_http_response(raw).expect("split");
        assert_eq!(status, 200);
        assert_eq!(body, b"{}");
    }

    #[test]
    fn extract_content_reads_choice_message() {
        let body = r#"{"choices":[{"message":{"content":"grounded answer"}}],"usage":{"completion_tokens":7}}"#;
        let (content, tokens) = extract_content(body).expect("content");
        assert_eq!(content, "grounded answer");
        assert_eq!(tokens, Some(7));
    }

    #[test]
    fn reasoning_only_response_is_a_clear_error() {
        let body = r#"{"choices":[{"message":{"content":"","reasoning":"thinking..."},"finish_reason":"length"}]}"#;
        let err = extract_content(body).unwrap_err();
        assert!(err.contains("reasoning tokens only"), "{err}");
    }

    #[test]
    fn consultation_receipt_signs_and_verifies() {
        let key = SigningKey::from_bytes(&[5u8; 32]);
        let answer = SystemTwoAnswer {
            content: "the answer".to_string(),
            model: "test-model".to_string(),
            endpoint: DEFAULT_ENDPOINT.to_string(),
            latency_ms: 12.5,
            max_tokens: 1024,
            completion_tokens: Some(3),
        };
        let receipt = ConsultationReceipt::sign(&key, "the question", &answer);
        assert_eq!(receipt.spec, SYSTEM2_SPEC);
        assert!(receipt.verify().is_ok());

        let mut tampered = receipt.clone();
        tampered.response_digest = sha256_hex(b"different");
        assert!(tampered.verify().is_err());
    }
}
