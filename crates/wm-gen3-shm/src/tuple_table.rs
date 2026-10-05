//! Atomic associative Linda Tuple Table over shared memory slot array.

use crate::layout::{
    MAX_TUPLES, ShmTupleSlot, TUPLE_STATE_COMMITTED, TUPLE_STATE_EMPTY, TUPLE_STATE_EXPIRED,
    TUPLE_STATE_TAKEN, TUPLE_STATE_WRITING,
};
use std::marker::PhantomData;
use std::sync::atomic::Ordering;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct RawTuple {
    pub id: Uuid,
    pub kind_discriminator: u32,
    pub resource_hash: u64,
    pub holder_issuer_hash: u64,
    pub resource_path: String,
    pub tag: String,
    pub payload: Vec<u8>,
    pub created_at_ms: u64,
    pub expires_at_ms: u64,
    pub landlock_token: [u8; 32],
    pub capability_mask: u64,
}

pub struct ShmTupleTable<'a> {
    base_ptr: *mut ShmTupleSlot,
    _marker: PhantomData<&'a ()>,
}

unsafe impl<'a> Send for ShmTupleTable<'a> {}
unsafe impl<'a> Sync for ShmTupleTable<'a> {}

impl<'a> ShmTupleTable<'a> {
    /// Format and initialize the tuple table memory.
    pub unsafe fn init(slots: *mut ShmTupleSlot, count: usize) {
        unsafe {
            for i in 0..count {
                let slot = slots.add(i);
                (*slot)
                    .state_ver
                    .store(TUPLE_STATE_EMPTY, Ordering::Relaxed);
                (*slot).kind_discriminator = 0;
                (*slot).expires_at_ms = 0;
                (*slot).payload_len = 0;
            }
        }
    }

    pub fn new(base_ptr: *mut ShmTupleSlot) -> Self {
        Self {
            base_ptr,
            _marker: PhantomData,
        }
    }

    /// Deposit a tuple into the shared table (`out`).
    pub fn out(&self, tuple: &RawTuple) -> Result<Uuid, &'static str> {
        let hash = tuple.resource_hash;
        let start_idx = (hash as usize) % MAX_TUPLES;

        for step in 0..MAX_TUPLES {
            let idx = (start_idx + step) % MAX_TUPLES;
            let slot = unsafe { &*self.base_ptr.add(idx) };

            let curr = slot.state_ver.load(Ordering::Acquire);
            if curr == TUPLE_STATE_EMPTY || curr == TUPLE_STATE_EXPIRED || curr == TUPLE_STATE_TAKEN
            {
                // Attempt to claim slot for writing
                if slot
                    .state_ver
                    .compare_exchange(
                        curr,
                        TUPLE_STATE_WRITING,
                        Ordering::AcqRel,
                        Ordering::Relaxed,
                    )
                    .is_ok()
                {
                    // Claimed! Write slot fields using raw pointer
                    unsafe {
                        let slot_ref = &mut *self.base_ptr.add(idx);
                        slot_ref.kind_discriminator = tuple.kind_discriminator;
                        slot_ref.tuple_id.copy_from_slice(tuple.id.as_bytes());
                        slot_ref.created_at_ms = tuple.created_at_ms;
                        slot_ref.expires_at_ms = tuple.expires_at_ms;
                        slot_ref.resource_hash = tuple.resource_hash;
                        slot_ref.holder_issuer_hash = tuple.holder_issuer_hash;
                        slot_ref.landlock_token = tuple.landlock_token;
                        slot_ref.capability_mask = tuple.capability_mask;

                        // String copies
                        let path_bytes = tuple.resource_path.as_bytes();
                        let p_len = path_bytes.len().min(127);
                        slot_ref.resource_path_str[..p_len].copy_from_slice(&path_bytes[..p_len]);
                        slot_ref.resource_path_str[p_len] = 0;

                        let tag_bytes = tuple.tag.as_bytes();
                        let t_len = tag_bytes.len().min(63);
                        slot_ref.tag_str[..t_len].copy_from_slice(&tag_bytes[..t_len]);
                        slot_ref.tag_str[t_len] = 0;

                        // Payload copy
                        let pl_len = tuple.payload.len().min(384);
                        slot_ref.payload_len = pl_len as u32;
                        slot_ref.inline_payload[..pl_len].copy_from_slice(&tuple.payload[..pl_len]);

                        // Publish committed state
                        slot_ref
                            .state_ver
                            .store(TUPLE_STATE_COMMITTED, Ordering::Release);
                    }
                    return Ok(tuple.id);
                }
            }
        }
        Err("Tuple table full")
    }

    /// Read and remove a matching tuple from the table (`in`).
    pub fn in_matching(
        &self,
        kind: Option<u32>,
        resource_hash: Option<u64>,
        now_ms: u64,
    ) -> Option<RawTuple> {
        for idx in 0..MAX_TUPLES {
            let slot = unsafe { &*self.base_ptr.add(idx) };
            let state = slot.state_ver.load(Ordering::Acquire);

            if state == TUPLE_STATE_COMMITTED {
                // Check expiry
                if slot.expires_at_ms > 0 && slot.expires_at_ms < now_ms {
                    let _ = slot.state_ver.compare_exchange(
                        TUPLE_STATE_COMMITTED,
                        TUPLE_STATE_EXPIRED,
                        Ordering::Relaxed,
                        Ordering::Relaxed,
                    );
                    continue;
                }

                // Check filter
                if let Some(k) = kind {
                    if slot.kind_discriminator != k {
                        continue;
                    }
                }
                if let Some(h) = resource_hash {
                    if slot.resource_hash != h {
                        continue;
                    }
                }

                // Try to take
                if slot
                    .state_ver
                    .compare_exchange(
                        TUPLE_STATE_COMMITTED,
                        TUPLE_STATE_TAKEN,
                        Ordering::AcqRel,
                        Ordering::Relaxed,
                    )
                    .is_ok()
                {
                    return Some(self.read_slot(slot));
                }
            }
        }
        None
    }

    /// Read matching tuples without removing (`rd`).
    pub fn rd_matching(
        &self,
        kind: Option<u32>,
        resource_hash: Option<u64>,
        max_results: usize,
        now_ms: u64,
    ) -> Vec<RawTuple> {
        let mut results = Vec::new();
        for idx in 0..MAX_TUPLES {
            if results.len() >= max_results {
                break;
            }
            let slot = unsafe { &*self.base_ptr.add(idx) };
            let state = slot.state_ver.load(Ordering::Acquire);

            if state == TUPLE_STATE_COMMITTED {
                if slot.expires_at_ms > 0 && slot.expires_at_ms < now_ms {
                    continue;
                }
                if let Some(k) = kind {
                    if slot.kind_discriminator != k {
                        continue;
                    }
                }
                if let Some(h) = resource_hash {
                    if slot.resource_hash != h {
                        continue;
                    }
                }
                results.push(self.read_slot(slot));
            }
        }
        results
    }

    fn read_slot(&self, slot: &ShmTupleSlot) -> RawTuple {
        let id = Uuid::from_bytes(slot.tuple_id);
        let p_len = (slot.payload_len as usize).min(384);
        let payload = slot.inline_payload[..p_len].to_vec();

        let path_nul = slot
            .resource_path_str
            .iter()
            .position(|&b| b == 0)
            .unwrap_or(128);
        let resource_path =
            String::from_utf8_lossy(&slot.resource_path_str[..path_nul]).into_owned();

        let tag_nul = slot.tag_str.iter().position(|&b| b == 0).unwrap_or(64);
        let tag = String::from_utf8_lossy(&slot.tag_str[..tag_nul]).into_owned();

        RawTuple {
            id,
            kind_discriminator: slot.kind_discriminator,
            resource_hash: slot.resource_hash,
            holder_issuer_hash: slot.holder_issuer_hash,
            resource_path,
            tag,
            payload,
            created_at_ms: slot.created_at_ms,
            expires_at_ms: slot.expires_at_ms,
            landlock_token: slot.landlock_token,
            capability_mask: slot.capability_mask,
        }
    }
}
