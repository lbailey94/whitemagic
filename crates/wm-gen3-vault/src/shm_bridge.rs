use crate::retrieval::{RecallResult, TacitVaultEngine};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use uuid::Uuid;
use wm_gen3_shm::{RawTuple, ShmTupleSpace};

pub const VAULT_REQUEST_KIND: u32 = 107;
pub const VAULT_RESPONSE_KIND: u32 = 108;

#[derive(Debug, Serialize, Deserialize)]
pub struct VaultShmRequest {
    pub req_id: String,
    pub query: String,
    pub k: usize,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VaultShmResponse {
    pub req_id: String,
    pub results: Vec<RecallResult>,
}

pub struct VaultShmBridge {
    tuple_space: ShmTupleSpace,
    engine: Arc<TacitVaultEngine>,
}

impl VaultShmBridge {
    pub fn new(tuple_space: ShmTupleSpace, engine: Arc<TacitVaultEngine>) -> Self {
        Self {
            tuple_space,
            engine,
        }
    }

    /// Process a single incoming query tuple from /dev/shm if present
    pub fn process_one_request(&self) -> Result<bool, String> {
        let now_ms = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0);

        // Attempt to take a matching request tuple
        if let Some(req_tuple) =
            self.tuple_space
                .in_matching(Some(VAULT_REQUEST_KIND), None, now_ms)
        {
            let req: VaultShmRequest = serde_json::from_slice(&req_tuple.payload)
                .map_err(|e| format!("Failed to parse request payload: {e}"))?;

            let results = self.engine.recall_associative(&req.query, req.k)?;

            let response = VaultShmResponse {
                req_id: req.req_id.clone(),
                results,
            };

            let resp_bytes = serde_json::to_vec(&response)
                .map_err(|e| format!("Failed to serialize response: {e}"))?;

            let resp_tuple = RawTuple {
                id: Uuid::new_v4(),
                kind_discriminator: 108, // Vault recall response
                resource_hash: compute_fnv1a(req.req_id.as_bytes()),
                holder_issuer_hash: 0,
                resource_path: req.req_id,
                tag: "vault_response".to_string(),
                payload: resp_bytes,
                created_at_ms: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_millis() as u64)
                    .unwrap_or(0),
                expires_at_ms: 0,
                landlock_token: [0u8; 32],
                capability_mask: 0xFFFF,
            };

            self.tuple_space
                .out(&resp_tuple)
                .map_err(|e| format!("Failed to deposit response tuple: {e}"))?;

            Ok(true)
        } else {
            Ok(false)
        }
    }
}

fn compute_fnv1a(bytes: &[u8]) -> u64 {
    let mut hash: u64 = 0xcbf29ce484222325;
    for &b in bytes {
        hash ^= b as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}
