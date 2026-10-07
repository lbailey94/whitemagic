//! wm-gen3-harness::deliberation — Frontier 1 System 1.5 Local Deliberation Layer
//!
//! Provides:
//! 1. Conformal Risk Control Gating: Finite-sample distribution-free uncertainty thresholding.
//! 2. Grammar-Constrained SLM Deliberation: Dynamic GBNF logit masking over candidate shortlists (100% schema guarantee).
//! 3. Signed Continuity Receipts: Ed25519-attested `continuity-receipt/1.5#deliberation`.

use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Instant;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;
use wm_gen3_core::mandala::{Signature, Signer, SigningKey, Verifier, VerifyingKey};

use crate::receipt_verify::{OutcomeLineSkip, verified_outcome_sample};

/// Spec identifier for System 1.5 deliberation receipts.
pub const DELIBERATION_SPEC: &str = "continuity-receipt/1.5#deliberation.v2";

/// Previous spec identifier, still verifiable for receipts signed before v2.
pub const DELIBERATION_SPEC_V1: &str = "continuity-receipt/1.5#deliberation";

/// Prompt template revision recorded in every v2 receipt.
pub const DELIBERATION_PROMPT_VERSION: &str = "deliberation-prompt-v2";

/// Fail-closed mode: refuse to sign a degraded deliberation receipt.
pub const ENV_DELIBERATION_STRICT: &str = "WM_GEN3_DELIBERATION_STRICT";

/// Environment variable overriding the local SLM weights path.
pub const ENV_SLM_MODEL: &str = "WM_GEN3_SLM_MODEL";

/// Environment variable overriding the llama-cli binary path.
pub const ENV_LLAMA_CLI: &str = "WM_GEN3_LLAMA_CLI";

/// Default model path searched if ENV_SLM_MODEL is unset.
pub const DEFAULT_SLM_PATH: &str = "/home/lucas/models/qwen2.5-0.5b-instruct-q4_k_m.gguf";

/// Default llama executable path.
pub const DEFAULT_LLAMA_CLI_PATH: &str = "/home/lucas/llama.cpp/build/bin/llama-completion";

/// A candidate route presented to the deliberator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CandidateRoute {
    pub name: String,
    pub score: f64,
    pub description: Option<String>,
}

/// Outcome of one conformal calibration pass over the outcomes journal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationReport {
    /// Calibrated margin threshold (`default_tau` when data is insufficient).
    pub tau: f64,
    /// Confidence level used for the finite-sample quantile.
    pub confidence_level: f64,
    /// True when `<store>/receipts/outcomes.jsonl` exists.
    pub journal_present: bool,
    /// Non-empty journal lines seen.
    pub journal_lines: usize,
    /// Verified successful margins that produced the quantile.
    pub samples_used: usize,
    /// Lines skipped because they did not verify against the gate key.
    pub lines_skipped_unverified: usize,
    /// Verified lines skipped because they carry no signed margin.
    pub lines_skipped_no_margin: usize,
    /// True when `tau` fell back to `default_tau`.
    pub used_default_tau: bool,
}

/// Dynamic Conformal Risk Control Gate.
#[derive(Debug, Clone)]
pub struct ConformalGate {
    /// Desired statistical confidence level (e.g. 0.95 or 0.99).
    pub confidence_level: f64,
    /// Default fallback margin threshold if insufficient calibration data exists.
    pub default_tau: f64,
}

impl Default for ConformalGate {
    fn default() -> Self {
        Self {
            confidence_level: 0.95,
            default_tau: 0.05,
        }
    }
}

impl ConformalGate {
    pub fn new(confidence_level: f64, default_tau: f64) -> Self {
        Self {
            confidence_level,
            default_tau,
        }
    }

    /// Calibrate margin threshold tau from recorded outcomes.jsonl if present.
    ///
    /// Only cryptographically verified outcome receipts contribute; forged or
    /// tampered journal lines are skipped. Use [`Self::calibrate_tau_report`]
    /// to see how many lines were skipped.
    pub fn calibrate_tau(&self, store_path: &Path) -> f64 {
        self.calibrate_tau_report(store_path).tau
    }

    /// Calibrate tau and report how many journal lines were not trusted.
    pub fn calibrate_tau_report(&self, store_path: &Path) -> CalibrationReport {
        let outcomes_file = store_path.join("receipts").join("outcomes.jsonl");
        let mut report = CalibrationReport {
            tau: self.default_tau,
            confidence_level: self.confidence_level,
            journal_present: outcomes_file.exists(),
            journal_lines: 0,
            samples_used: 0,
            lines_skipped_unverified: 0,
            lines_skipped_no_margin: 0,
            used_default_tau: true,
        };
        if !report.journal_present {
            return report;
        }

        let content = match std::fs::read_to_string(&outcomes_file) {
            Ok(s) => s,
            Err(_) => return report,
        };

        // Extract margins for successful dispatches. A line only counts when
        // its outcome receipt (or referenced subject receipt) verifies against
        // the store gate key, so appended junk cannot move the threshold.
        let mut non_conformity_scores: Vec<f64> = Vec::new();
        for line in content.lines() {
            if line.trim().is_empty() {
                continue;
            }
            report.journal_lines += 1;
            match verified_outcome_sample(line, store_path) {
                Ok(sample) => {
                    if sample.success {
                        // High margin = low non-conformity score
                        non_conformity_scores.push((1.0 - sample.margin).max(0.0));
                    }
                }
                Err(OutcomeLineSkip::Unverified) => report.lines_skipped_unverified += 1,
                Err(OutcomeLineSkip::NoMargin) => report.lines_skipped_no_margin += 1,
            }
        }
        report.samples_used = non_conformity_scores.len();

        if non_conformity_scores.len() < 10 {
            return report;
        }

        non_conformity_scores.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let alpha = (1.0 - self.confidence_level).clamp(0.01, 0.50);
        let n = non_conformity_scores.len();
        let rank = ((n as f64 + 1.0) * (1.0 - alpha)).ceil() as usize;
        let idx = (rank.saturating_sub(1)).min(n - 1);
        let q = non_conformity_scores[idx];

        // Invert non-conformity score back to margin threshold
        report.tau = (1.0 - q).max(0.02);
        report.used_default_tau = false;
        report
    }

    /// Evaluate whether a top-1 candidate passes the conformal gate or requires deliberation.
    pub fn evaluate_margin(
        &self,
        top1_score: f64,
        top2_score: f64,
        store_path: &Path,
    ) -> (bool, f64) {
        let margin = (top1_score - top2_score).max(0.0);
        let tau = self.calibrate_tau(store_path);
        (margin >= tau, margin)
    }
}

/// Cryptographically signed deliberation receipt for System 1.5 decisions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeliberationReceipt {
    pub spec: String,
    pub receipt_id: String,
    pub timestamp_ms: u64,
    pub inquiry: String,
    pub inquiry_digest: String,
    pub candidates: Vec<String>,
    pub chosen_route: String,
    pub margin_prior: f64,
    pub conformal_tau: f64,
    pub confidence: f64,
    pub latency_ms: f64,
    #[serde(default)]
    pub degraded: bool,
    #[serde(default)]
    pub slm_model_sha256: String,
    #[serde(default)]
    pub prompt_version: String,
    pub layer: String,
    pub issuer_did: String,
    pub signature: String,
}

impl DeliberationReceipt {
    /// Compute canonical byte payload for Ed25519 signing.
    pub fn canonical_payload_v1(
        receipt_id: &str,
        inquiry_digest: &str,
        candidates: &[String],
        chosen_route: &str,
        margin_prior: f64,
        conformal_tau: f64,
        confidence: f64,
        timestamp_ms: u64,
    ) -> String {
        let cand_str = candidates.join(",");
        format!(
            "WHITEMAGIC:RECEIPT:1.5|id:{}|digest:{}|candidates:{}|chosen:{}|margin:{:.6}|tau:{:.6}|conf:{:.6}|time:{}",
            receipt_id,
            inquiry_digest,
            cand_str,
            chosen_route,
            margin_prior,
            conformal_tau,
            confidence,
            timestamp_ms
        )
    }

    /// Compute canonical byte payload for Ed25519 signing (v2, provenance-signed).
    #[allow(clippy::too_many_arguments)]
    pub fn canonical_payload_v2(
        receipt_id: &str,
        inquiry_digest: &str,
        candidates: &[String],
        chosen_route: &str,
        margin_prior: f64,
        conformal_tau: f64,
        confidence: f64,
        degraded: bool,
        slm_model_sha256: &str,
        prompt_version: &str,
        timestamp_ms: u64,
    ) -> String {
        let cand_str = candidates.join(",");
        format!(
            "WHITEMAGIC:RECEIPT:1.5.v2|id:{}|digest:{}|candidates:{}|chosen:{}|margin:{:.6}|tau:{:.6}|conf:{:.6}|degraded:{}|model:{}|prompt:{}|time:{}",
            receipt_id,
            inquiry_digest,
            cand_str,
            chosen_route,
            margin_prior,
            conformal_tau,
            confidence,
            degraded,
            slm_model_sha256,
            prompt_version,
            timestamp_ms
        )
    }

    /// Sign and construct a new DeliberationReceipt.
    #[allow(clippy::too_many_arguments)]
    pub fn sign(
        signing_key: &SigningKey,
        inquiry: &str,
        candidates: &[String],
        chosen_route: &str,
        margin_prior: f64,
        conformal_tau: f64,
        confidence: f64,
        latency_ms: f64,
        degraded: bool,
        slm_model_sha256: &str,
        prompt_version: &str,
    ) -> Self {
        let receipt_id = Uuid::new_v4().to_string();
        let timestamp_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        let inquiry_digest = {
            let mut hasher = Sha256::new();
            hasher.update(inquiry.as_bytes());
            format!("{:x}", hasher.finalize())
        };

        let pubkey_bytes = signing_key.verifying_key().to_bytes();
        let issuer_did = format!("did:key:{}", hex_encode(&pubkey_bytes));

        let payload = Self::canonical_payload_v2(
            &receipt_id,
            &inquiry_digest,
            candidates,
            chosen_route,
            margin_prior,
            conformal_tau,
            confidence,
            degraded,
            slm_model_sha256,
            prompt_version,
            timestamp_ms,
        );

        let sig: Signature = signing_key.sign(payload.as_bytes());
        let signature = hex_encode(&sig.to_bytes());

        Self {
            spec: DELIBERATION_SPEC.to_string(),
            receipt_id,
            timestamp_ms,
            inquiry: inquiry.to_string(),
            inquiry_digest,
            candidates: candidates.to_vec(),
            chosen_route: chosen_route.to_string(),
            margin_prior,
            conformal_tau,
            confidence,
            latency_ms,
            degraded,
            slm_model_sha256: slm_model_sha256.to_string(),
            prompt_version: prompt_version.to_string(),
            layer: "system1.5".to_string(),
            issuer_did,
            signature,
        }
    }

    /// Verify cryptographic validity of this receipt.
    pub fn verify(&self) -> Result<(), String> {
        let pubkey_hex = self
            .issuer_did
            .strip_prefix("did:key:")
            .ok_or_else(|| "missing did:key: prefix".to_string())?;

        let mut pubkey_bytes = [0u8; 32];
        decode_hex_into_32(pubkey_hex, &mut pubkey_bytes)?;
        let verifying_key = VerifyingKey::from_bytes(&pubkey_bytes)
            .map_err(|e| format!("invalid verifying key: {e}"))?;

        let mut sig_bytes = [0u8; 64];
        decode_hex_into_64(&self.signature, &mut sig_bytes)?;
        let signature = Signature::from_bytes(&sig_bytes);

        let payload = if self.spec == DELIBERATION_SPEC {
            Self::canonical_payload_v2(
                &self.receipt_id,
                &self.inquiry_digest,
                &self.candidates,
                &self.chosen_route,
                self.margin_prior,
                self.conformal_tau,
                self.confidence,
                self.degraded,
                &self.slm_model_sha256,
                &self.prompt_version,
                self.timestamp_ms,
            )
        } else {
            Self::canonical_payload_v1(
                &self.receipt_id,
                &self.inquiry_digest,
                &self.candidates,
                &self.chosen_route,
                self.margin_prior,
                self.conformal_tau,
                self.confidence,
                self.timestamp_ms,
            )
        };

        verifying_key
            .verify(payload.as_bytes(), &signature)
            .map_err(|e| format!("deliberation receipt signature invalid: {e}"))?;

        Ok(())
    }

    /// Persist receipt atomically to `<store>/receipts/deliberation-<id>.json`.
    pub fn persist(&self, store_path: &Path) -> std::io::Result<PathBuf> {
        let receipts_dir = store_path.join("receipts");
        std::fs::create_dir_all(&receipts_dir)?;
        let file_path = receipts_dir.join(format!("deliberation-{}.json", self.receipt_id));
        let content = serde_json::to_string_pretty(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(&file_path, content)?;
        Ok(file_path)
    }
}

/// Result of a System 1.5 deliberation, including provenance for the receipt.
#[derive(Debug, Clone)]
pub struct DeliberationOutcome {
    pub chosen_route: String,
    pub confidence: f64,
    pub latency_ms: f64,
    pub degraded: bool,
    pub slm_model_sha256: String,
    pub prompt_version: String,
}

/// Frontier 1 System 1.5 Deliberator Engine.
pub struct Deliberator {
    slm_model_path: PathBuf,
    llama_cli_path: PathBuf,
}

impl Default for Deliberator {
    fn default() -> Self {
        let slm_model_path = std::env::var(ENV_SLM_MODEL)
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from(DEFAULT_SLM_PATH));
        let llama_cli_path = std::env::var(ENV_LLAMA_CLI)
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                let comp = PathBuf::from("/home/lucas/llama.cpp/build/bin/llama-completion");
                if comp.exists() {
                    comp
                } else {
                    PathBuf::from(DEFAULT_LLAMA_CLI_PATH)
                }
            });
        Self {
            slm_model_path,
            llama_cli_path,
        }
    }
}

impl Deliberator {
    pub fn new(slm_model_path: PathBuf, llama_cli_path: PathBuf) -> Self {
        Self {
            slm_model_path,
            llama_cli_path,
        }
    }

    /// Check if local SLM execution environment is available.
    pub fn is_available(&self) -> bool {
        self.slm_model_path.exists() && self.llama_cli_path.exists()
    }

    /// Deliberate over an ambiguous shortlist of candidates using grammar-constrained SLM generation.
    pub fn deliberate(
        &self,
        inquiry: &str,
        candidates: &[CandidateRoute],
    ) -> Result<DeliberationOutcome, String> {
        if candidates.is_empty() {
            return Err("cannot deliberate over empty candidates".to_string());
        }
        if candidates.len() == 1 {
            return Ok(DeliberationOutcome {
                chosen_route: candidates[0].name.clone(),
                confidence: candidates[0].score,
                latency_ms: 0.1,
                degraded: false,
                slm_model_sha256: String::new(),
                prompt_version: DELIBERATION_PROMPT_VERSION.to_string(),
            });
        }

        let start = Instant::now();

        // If local SLM runner is available, execute grammar-constrained generation
        if self.is_available() {
            let names: Vec<String> = candidates.iter().map(|c| c.name.clone()).collect();
            let grammar = build_gbnf_grammar(&names);

            let mut formatted_options = String::new();
            let show_scores = candidates.iter().any(|c| c.score > 0.0);
            for c in candidates {
                let desc = c.description.as_deref().unwrap_or("Action route");
                if show_scores {
                    formatted_options.push_str(&format!(
                        "- {} (shortlist score {:.3}): {}\n",
                        c.name, c.score, desc
                    ));
                } else {
                    formatted_options.push_str(&format!("- {}: {}\n", c.name, desc));
                }
            }

            let prompt = format!(
                "You are an action router. Choose exactly one option that best handles the request. Answer with only the option name.\nUser Request: \"{}\"\nAllowed Options:\n{}Answer: ",
                inquiry, formatted_options
            );

            let invoke = |flag: &str| {
                Command::new(&self.llama_cli_path)
                    .arg("-m")
                    .arg(&self.slm_model_path)
                    .arg("-p")
                    .arg(&prompt)
                    .arg("--grammar")
                    .arg(&grammar)
                    .arg("-n")
                    .arg("4")
                    .arg("-t")
                    .arg("4")
                    .arg("--temp")
                    .arg("0.0")
                    .arg("-c")
                    .arg("512")
                    .arg(flag)
                    .stdin(std::process::Stdio::null())
                    .output()
            };
            let mut output = invoke("-st");
            if let Ok(res) = &output {
                if !res.status.success() {
                    output = invoke("-no-cnv");
                }
            }

            if let Ok(res) = output {
                if res.status.success() {
                    let raw_stdout = String::from_utf8_lossy(&res.stdout);
                    let mut best: Option<(&String, usize)> = None;
                    for name in &names {
                        if let Some(pos) = raw_stdout.rfind(name.as_str()) {
                            if best.is_none_or(|(_, best_pos)| pos > best_pos) {
                                best = Some((name, pos));
                            }
                        }
                    }
                    if let Some((name, _)) = best {
                        let latency = start.elapsed().as_secs_f64() * 1000.0;
                        let prior_score = candidates
                            .iter()
                            .find(|c| &c.name == name)
                            .map(|c| c.score)
                            .unwrap_or(0.90);
                        return Ok(DeliberationOutcome {
                            chosen_route: name.clone(),
                            confidence: prior_score.max(0.85),
                            latency_ms: latency,
                            degraded: false,
                            slm_model_sha256: self.model_fingerprint().unwrap_or_default(),
                            prompt_version: DELIBERATION_PROMPT_VERSION.to_string(),
                        });
                    }
                }
            }
        }

        // Fallback: Pick highest candidate score with calibrated tie-breaking
        let best = candidates
            .iter()
            .max_by(|a, b| {
                a.score
                    .partial_cmp(&b.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap();
        let latency = start.elapsed().as_secs_f64() * 1000.0;
        Ok(DeliberationOutcome {
            chosen_route: best.name.clone(),
            confidence: 0.0,
            latency_ms: latency,
            degraded: true,
            slm_model_sha256: self.model_fingerprint().unwrap_or_default(),
            prompt_version: DELIBERATION_PROMPT_VERSION.to_string(),
        })
    }

    fn model_fingerprint(&self) -> Option<String> {
        model_sha256(&self.slm_model_path)
    }
}

fn model_sha256(path: &Path) -> Option<String> {
    let sidecar = PathBuf::from(format!("{}.sha256", path.display()));
    if let Ok(existing) = std::fs::read_to_string(&sidecar) {
        if let Some(token) = existing.split_whitespace().next() {
            if token.len() == 64 && token.chars().all(|c| c.is_ascii_hexdigit()) {
                return Some(token.to_ascii_lowercase());
            }
        }
    }

    let mut file = File::open(path).ok()?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 65536];
    loop {
        let n = file.read(&mut buf).ok()?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let digest = format!("{:x}", hasher.finalize());
    let _ = std::fs::write(&sidecar, format!("{digest}  {}", path.display()));
    Some(digest)
}

/// Construct a strictly constrained GBNF grammar matching only candidate names.
pub fn build_gbnf_grammar(candidates: &[String]) -> String {
    let mut parts: Vec<String> = Vec::new();
    for c in candidates {
        parts.push(format!("\"{}\"", c));
    }
    format!("root ::= ({})\n", parts.join(" | "))
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn decode_hex_into_32(hex_str: &str, out: &mut [u8; 32]) -> Result<(), String> {
    if hex_str.len() != 64 {
        return Err(format!(
            "expected 64 hex characters for 32-byte key, got {}",
            hex_str.len()
        ));
    }
    for i in 0..32 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16)
            .map_err(|e| format!("bad hex char at {}: {e}", i * 2))?;
    }
    Ok(())
}

fn decode_hex_into_64(hex_str: &str, out: &mut [u8; 64]) -> Result<(), String> {
    if hex_str.len() != 128 {
        return Err(format!(
            "expected 128 hex characters for 64-byte signature, got {}",
            hex_str.len()
        ));
    }
    for i in 0..64 {
        out[i] = u8::from_str_radix(&hex_str[i * 2..i * 2 + 2], 16)
            .map_err(|e| format!("bad hex char at {}: {e}", i * 2))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gbnf_grammar_builder() {
        let candidates = vec![
            "memory.create".to_string(),
            "session.checkpoint".to_string(),
        ];
        let gbnf = build_gbnf_grammar(&candidates);
        assert_eq!(
            gbnf,
            "root ::= (\"memory.create\" | \"session.checkpoint\")\n"
        );
    }

    #[test]
    fn test_conformal_gate_eval() {
        let gate = ConformalGate::new(0.95, 0.05);
        let temp_dir = std::env::temp_dir().join("wm_gate_test");
        let _ = std::fs::create_dir_all(&temp_dir);

        let (pass_clear, margin_clear) = gate.evaluate_margin(0.85, 0.70, &temp_dir);
        assert!(pass_clear);
        assert!((margin_clear - 0.15).abs() < 1e-4);

        let (pass_ambiguous, margin_amb) = gate.evaluate_margin(0.72, 0.70, &temp_dir);
        assert!(!pass_ambiguous);
        assert!((margin_amb - 0.02).abs() < 1e-4);
    }

    #[test]
    fn test_deliberation_receipt_signing_and_tamper() {
        let seed = [9u8; 32];
        let signing_key = SigningKey::from_bytes(&seed);

        let candidates = vec![
            "memory.create".to_string(),
            "session.checkpoint".to_string(),
        ];
        let receipt = DeliberationReceipt::sign(
            &signing_key,
            "save this fact to memory",
            &candidates,
            "memory.create",
            0.02,
            0.05,
            0.92,
            12.5,
            false,
            "abc123",
            DELIBERATION_PROMPT_VERSION,
        );

        assert_eq!(receipt.chosen_route, "memory.create");
        assert_eq!(receipt.spec, DELIBERATION_SPEC);
        assert!(!receipt.degraded);
        assert!(receipt.verify().is_ok());

        // Tamper with chosen route
        let mut tampered = receipt.clone();
        tampered.chosen_route = "session.checkpoint".to_string();
        assert!(tampered.verify().is_err());
    }

    #[test]
    fn test_deliberation_receipt_v2_provenance_is_signed() {
        let signing_key = SigningKey::from_bytes(&[7u8; 32]);
        let candidates = vec![
            "memory.create".to_string(),
            "session.checkpoint".to_string(),
        ];
        let receipt = DeliberationReceipt::sign(
            &signing_key,
            "route this",
            &candidates,
            "session.checkpoint",
            0.01,
            0.05,
            0.0,
            3.0,
            true,
            "a5c1f3",
            DELIBERATION_PROMPT_VERSION,
        );

        assert!(receipt.degraded);
        assert!(receipt.verify().is_ok());

        let mut tampered = receipt.clone();
        tampered.degraded = false;
        assert!(tampered.verify().is_err());

        let mut tampered_model = receipt.clone();
        tampered_model.slm_model_sha256 = "0".repeat(64);
        assert!(tampered_model.verify().is_err());
    }

    #[test]
    fn test_deliberation_fallback_is_degraded_and_fail_closed() {
        let deliberator = Deliberator::new(
            PathBuf::from("/nonexistent/slm.gguf"),
            PathBuf::from("/nonexistent/llama-cli"),
        );
        let candidates = vec![
            CandidateRoute {
                name: "memory.create".to_string(),
                score: 0.91,
                description: None,
            },
            CandidateRoute {
                name: "session.checkpoint".to_string(),
                score: 0.90,
                description: None,
            },
        ];

        let outcome = deliberator.deliberate("save this", &candidates).unwrap();
        assert!(outcome.degraded);
        assert_eq!(outcome.confidence, 0.0);
        assert_eq!(outcome.chosen_route, "memory.create");
    }

    fn calibration_fixture_store(key: &SigningKey) -> PathBuf {
        let store = std::env::temp_dir().join(format!("wm-calibration-{}", Uuid::new_v4()));
        std::fs::create_dir_all(store.join("receipts")).expect("create calibration store");
        std::fs::write(store.join("mandala_gate_key.bin"), key.to_bytes()).expect("write gate key");
        store
    }

    #[test]
    fn test_calibrate_tau_ignores_forged_unverified_journal_lines() {
        let key = SigningKey::from_bytes(&[31u8; 32]);
        let store = calibration_fixture_store(&key);
        let mut journal = String::new();
        for _ in 0..10 {
            journal.push_str("{\"margin\":0.0,\"success\":true}\n");
        }
        // A structurally valid but tampered signature must not count either.
        let mut forged = crate::receipt_verify::OutcomeRecord::new(
            "subject".into(),
            "continuity-receipt/0.5#deliberation.v2".into(),
            true,
            Some(0.0),
            &serde_json::json!({"outcome": "success"}),
            format!("did:key:{}", hex_encode(&key.verifying_key().to_bytes())),
        )
        .expect("forged record builds");
        forged.sign(&key);
        forged.signature = Some("0".repeat(128));
        journal.push_str(&serde_json::to_string(&forged).expect("serialize forged"));
        journal.push('\n');
        std::fs::write(store.join("receipts").join("outcomes.jsonl"), journal)
            .expect("write forged journal");

        let gate = ConformalGate::new(0.95, 0.05);
        let report = gate.calibrate_tau_report(&store);
        assert_eq!(report.tau, 0.05, "forged lines must not move tau");
        assert_eq!(report.lines_skipped_unverified, 11);
        assert_eq!(report.samples_used, 0);
        assert!(report.used_default_tau);
        assert_eq!(gate.calibrate_tau(&store), 0.05);
        std::fs::remove_dir_all(store).expect("cleanup calibration store");
    }

    #[test]
    fn test_calibrate_tau_follows_verified_subject_references() {
        let key = SigningKey::from_bytes(&[32u8; 32]);
        let store = calibration_fixture_store(&key);
        let receipt = DeliberationReceipt::sign(
            &key,
            "reference calibration fixture",
            &["memory.search".into(), "memory.create".into()],
            "memory.search",
            0.5,
            0.05,
            0.9,
            1.0,
            false,
            "model-sha256",
            DELIBERATION_PROMPT_VERSION,
        );
        let subject_path = store
            .join("receipts")
            .join(format!("deliberation-{}.json", receipt.receipt_id));
        std::fs::write(
            &subject_path,
            serde_json::to_vec(&receipt).expect("serialize subject"),
        )
        .expect("write subject receipt");

        let mut journal = String::new();
        for _ in 0..10 {
            journal.push_str(&format!(
                "{{\"subject_receipt\":\"{}\",\"success\":true}}\n",
                receipt.receipt_id
            ));
        }
        journal.push_str("{\"subject_receipt\":\"missing-subject\",\"success\":true}\n");
        std::fs::write(store.join("receipts").join("outcomes.jsonl"), journal)
            .expect("write reference journal");

        let gate = ConformalGate::new(0.95, 0.05);
        let report = gate.calibrate_tau_report(&store);
        assert_eq!(report.samples_used, 10);
        assert_eq!(report.lines_skipped_unverified, 1);
        assert_eq!(report.lines_skipped_no_margin, 0);
        assert!(
            (report.tau - 0.5).abs() < 1e-9,
            "verified subject references must calibrate, got {}",
            report.tau
        );
        std::fs::remove_dir_all(store).expect("cleanup calibration store");
    }
}
