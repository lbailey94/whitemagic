use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Debug, Clone)]
#[pyclass]
pub struct LedgerEntry {
    pub id: String,
    pub timestamp: u64,
    pub action_type: String,
    pub parent_hash: String,
    pub payload_hash: String,
    pub signature: String,
    pub guna_classification: String, // sattvic, rajasic, tamasic
    pub karma_score: f32,
}

#[pyclass]
pub struct ZodiacLedger {
    pub entries: Vec<LedgerEntry>,
    pub current_hash: String,
}

#[pymethods]
impl ZodiacLedger {
    #[new]
    pub fn new() -> Self {
        ZodiacLedger {
            entries: Vec::new(),
            current_hash: String::from("GENESIS_BINDU"),
        }
    }

    pub fn record_action(
        &mut self,
        action_type: &str,
        payload: &str,
        guna: &str,
        karma: f32,
    ) -> String {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let mut hasher = Sha256::new();
        hasher.update(payload.as_bytes());
        let payload_hash = format!("{:x}", hasher.finalize());

        let mut sig_hasher = Sha256::new();
        sig_hasher.update(
            format!(
                "{}{}{}{}",
                self.current_hash, action_type, payload_hash, timestamp
            )
            .as_bytes(),
        );
        let signature = format!("{:x}", sig_hasher.finalize());

        let entry = LedgerEntry {
            id: format!("ZODIAC_{}", timestamp),
            timestamp,
            action_type: action_type.to_string(),
            parent_hash: self.current_hash.clone(),
            payload_hash,
            signature: signature.clone(),
            guna_classification: guna.to_string(),
            karma_score: karma,
        };

        self.current_hash = signature.clone();
        self.entries.push(entry);

        signature
    }
}
