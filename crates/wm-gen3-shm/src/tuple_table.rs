//! Atomic associative Linda Tuple Table over shared memory slot array + Arena variable payloads.

use crate::layout::{
    ARENA_BLOCK_HEADER_SIZE, ARENA_DATA_START, ARENA_FREE_CLASSES, ARENA_SIZE, MAX_TUPLES,
    ShmArenaHeader, ShmTupleSlot, TUPLE_INLINE_MAX, TUPLE_STATE_COMMITTED, TUPLE_STATE_EMPTY,
    TUPLE_STATE_EXPIRED, TUPLE_STATE_LOCKED, TUPLE_STATE_TAKEN, TUPLE_STATE_WRITING,
};
use std::marker::PhantomData;
use std::sync::atomic::{AtomicU32, AtomicU64, Ordering};
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
    arena_ptr: *mut u8,
    arena_cursor: *const AtomicU64,
    _marker: PhantomData<&'a ()>,
}

unsafe impl<'a> Send for ShmTupleTable<'a> {}
unsafe impl<'a> Sync for ShmTupleTable<'a> {}

#[inline]
fn size_class_and_cap(len: usize) -> (usize, usize) {
    let mut cls = 0usize;
    let mut cap = 512usize;
    while cap < len && cls < ARENA_FREE_CLASSES {
        cap <<= 1;
        cls += 1;
    }
    if cls < ARENA_FREE_CLASSES {
        (cls, cap)
    } else {
        let aligned = (len + 63) & !63;
        (ARENA_FREE_CLASSES, aligned)
    }
}

impl<'a> ShmTupleTable<'a> {
    /// Format and initialize the tuple table memory.
    ///
    /// # Safety
    ///
    /// `slots` must point to `count` writable [`ShmTupleSlot`] entries in shared
    /// memory valid for this process's lifetime.
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
                (*slot).arena_offset = 0;
            }
        }
    }

    pub fn new(base_ptr: *mut ShmTupleSlot) -> Self {
        Self {
            base_ptr,
            arena_ptr: std::ptr::null_mut(),
            arena_cursor: std::ptr::null(),
            _marker: PhantomData,
        }
    }

    /// Construct a tuple table backed by the variable-length shared-memory Arena & occupancy bitset.
    pub fn with_arena(
        base_ptr: *mut ShmTupleSlot,
        arena_ptr: *mut u8,
        arena_cursor: *const AtomicU64,
    ) -> Self {
        Self {
            base_ptr,
            arena_ptr,
            arena_cursor,
            _marker: PhantomData,
        }
    }

    #[inline]
    fn arena_hdr(&self) -> Option<&ShmArenaHeader> {
        if self.arena_ptr.is_null() {
            None
        } else {
            Some(unsafe { &*(self.arena_ptr as *const ShmArenaHeader) })
        }
    }

    #[inline]
    fn set_occupied_bit(&self, idx: usize) {
        if let Some(hdr) = self.arena_hdr() {
            let word_idx = idx >> 6;
            let bit = 1u64 << (idx & 63);
            hdr.occupancy_bitset[word_idx].fetch_or(bit, Ordering::Release);
        }
    }

    #[inline]
    fn clear_occupied_bit(&self, idx: usize) {
        if let Some(hdr) = self.arena_hdr() {
            let word_idx = idx >> 6;
            let bit = 1u64 << (idx & 63);
            hdr.occupancy_bitset[word_idx].fetch_and(!bit, Ordering::AcqRel);
        }
    }

    fn alloc_arena_payload(&self, data: &[u8]) -> Result<u32, &'static str> {
        let Some(hdr) = self.arena_hdr() else {
            return Err("Tuple arena unavailable");
        };
        if self.arena_cursor.is_null() {
            return Err("Tuple arena cursor unavailable");
        }
        let cursor_atomic = unsafe { &*self.arena_cursor };
        let (cls, cap) = size_class_and_cap(data.len());
        if cls < ARENA_FREE_CLASSES {
            loop {
                let head = hdr.free_heads[cls].load(Ordering::Acquire);
                let head_off = (head & 0xFFFF_FFFF) as u32;
                let head_tag = head >> 32;
                if head_off < ARENA_DATA_START as u32
                    || (head_off as usize) + ARENA_BLOCK_HEADER_SIZE > ARENA_SIZE
                {
                    break;
                }
                let next_off = unsafe {
                    let next_ptr = self.arena_ptr.add((head_off as usize) + 4) as *const AtomicU32;
                    (*next_ptr).load(Ordering::Acquire)
                };
                let new_head = (head_tag.wrapping_add(1) << 32) | u64::from(next_off);
                if hdr.free_heads[cls]
                    .compare_exchange_weak(head, new_head, Ordering::AcqRel, Ordering::Acquire)
                    .is_ok()
                {
                    unsafe {
                        let block_cap_ptr = self.arena_ptr.add(head_off as usize) as *mut u32;
                        let avail_cap = (*block_cap_ptr) as usize;
                        if avail_cap >= data.len()
                            && (head_off as usize) + ARENA_BLOCK_HEADER_SIZE + data.len()
                                <= ARENA_SIZE
                        {
                            let dst = std::slice::from_raw_parts_mut(
                                self.arena_ptr
                                    .add((head_off as usize) + ARENA_BLOCK_HEADER_SIZE),
                                data.len(),
                            );
                            dst.copy_from_slice(data);
                            return Ok(head_off);
                        }
                    }
                    break;
                }
            }
        }

        let total_bytes = (ARENA_BLOCK_HEADER_SIZE + cap) as u64;
        loop {
            let cur = cursor_atomic.load(Ordering::Acquire);
            let base = cur.max(ARENA_DATA_START as u64);
            let aligned_base = (base + 63) & !63;
            let next = aligned_base.saturating_add(total_bytes);
            if next > ARENA_SIZE as u64 || aligned_base > u32::MAX as u64 {
                return Err("Tuple arena exhausted");
            }
            if cursor_atomic
                .compare_exchange_weak(cur, next, Ordering::AcqRel, Ordering::Acquire)
                .is_ok()
            {
                let rel_off = aligned_base as usize;
                unsafe {
                    let cap_ptr = self.arena_ptr.add(rel_off) as *mut u32;
                    let next_ptr = self.arena_ptr.add(rel_off + 4) as *const AtomicU32;
                    *cap_ptr = cap as u32;
                    (*next_ptr).store(0, Ordering::Release);
                    let dst = std::slice::from_raw_parts_mut(
                        self.arena_ptr.add(rel_off + ARENA_BLOCK_HEADER_SIZE),
                        data.len(),
                    );
                    dst.copy_from_slice(data);
                }
                return Ok(rel_off as u32);
            }
        }
    }

    fn free_arena_payload(&self, arena_off: u32) {
        if arena_off < ARENA_DATA_START as u32 {
            return;
        }
        let off = arena_off as usize;
        if off + ARENA_BLOCK_HEADER_SIZE > ARENA_SIZE {
            return;
        }
        let Some(hdr) = self.arena_hdr() else {
            return;
        };
        let block_cap = unsafe { *(self.arena_ptr.add(off) as *const u32) } as usize;
        let (cls, _) = size_class_and_cap(block_cap);
        if cls >= ARENA_FREE_CLASSES {
            return;
        }
        loop {
            let head = hdr.free_heads[cls].load(Ordering::Acquire);
            let head_off = (head & 0xFFFF_FFFF) as u32;
            let tag = hdr.free_tags[cls].fetch_add(1, Ordering::Relaxed) + 1;
            unsafe {
                let next_ptr = self.arena_ptr.add(off + 4) as *const AtomicU32;
                (*next_ptr).store(head_off, Ordering::Release);
            }
            let new_head = (tag << 32) | u64::from(arena_off);
            if hdr.free_heads[cls]
                .compare_exchange_weak(head, new_head, Ordering::AcqRel, Ordering::Acquire)
                .is_ok()
            {
                break;
            }
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
            if (curr == TUPLE_STATE_EMPTY
                || curr == TUPLE_STATE_EXPIRED
                || curr == TUPLE_STATE_TAKEN)
                && slot
                    .state_ver
                    .compare_exchange(
                        curr,
                        TUPLE_STATE_WRITING,
                        Ordering::AcqRel,
                        Ordering::Relaxed,
                    )
                    .is_ok()
            {
                unsafe {
                    let slot_ref = &mut *self.base_ptr.add(idx);
                    let old_arena_off = slot_ref.arena_offset;
                    if old_arena_off >= ARENA_DATA_START as u32 {
                        slot_ref.arena_offset = 0;
                        self.free_arena_payload(old_arena_off);
                    }

                    let (arena_off, pl_len) = if tuple.payload.len() <= TUPLE_INLINE_MAX {
                        let len = tuple.payload.len();
                        slot_ref.inline_payload[..len].copy_from_slice(&tuple.payload);
                        (0u32, len as u32)
                    } else if self.arena_hdr().is_some() {
                        match self.alloc_arena_payload(&tuple.payload) {
                            Ok(off) => (off, tuple.payload.len() as u32),
                            Err(e) => {
                                slot_ref.payload_len = 0;
                                slot_ref.arena_offset = 0;
                                self.clear_occupied_bit(idx);
                                slot_ref
                                    .state_ver
                                    .store(TUPLE_STATE_EMPTY, Ordering::Release);
                                return Err(e);
                            }
                        }
                    } else {
                        let pl_len = tuple.payload.len().min(TUPLE_INLINE_MAX);
                        slot_ref.inline_payload[..pl_len].copy_from_slice(&tuple.payload[..pl_len]);
                        (0u32, pl_len as u32)
                    };

                    slot_ref.kind_discriminator = tuple.kind_discriminator;
                    slot_ref.tuple_id.copy_from_slice(tuple.id.as_bytes());
                    slot_ref.created_at_ms = tuple.created_at_ms;
                    slot_ref.expires_at_ms = tuple.expires_at_ms;
                    slot_ref.resource_hash = tuple.resource_hash;
                    slot_ref.holder_issuer_hash = tuple.holder_issuer_hash;
                    slot_ref.landlock_token = tuple.landlock_token;
                    slot_ref.capability_mask = tuple.capability_mask;

                    let path_bytes = tuple.resource_path.as_bytes();
                    let p_len = path_bytes.len().min(127);
                    slot_ref.resource_path_str[..p_len].copy_from_slice(&path_bytes[..p_len]);
                    slot_ref.resource_path_str[p_len] = 0;

                    let tag_bytes = tuple.tag.as_bytes();
                    let t_len = tag_bytes.len().min(63);
                    slot_ref.tag_str[..t_len].copy_from_slice(&tag_bytes[..t_len]);
                    slot_ref.tag_str[t_len] = 0;

                    slot_ref.arena_offset = arena_off;
                    slot_ref.payload_len = pl_len;

                    // Publish occupied bit BEFORE state transitions to COMMITTED.
                    self.set_occupied_bit(idx);
                    slot_ref
                        .state_ver
                        .store(TUPLE_STATE_COMMITTED, Ordering::Release);
                }
                return Ok(tuple.id);
            }
        }
        Err("Tuple table full")
    }

    fn visit_occupied_slots<F>(&self, mut f: F)
    where
        F: FnMut(usize) -> bool,
    {
        if let Some(hdr) = self.arena_hdr() {
            for (word_idx, atom) in hdr.occupancy_bitset.iter().enumerate() {
                let mut w = atom.load(Ordering::Acquire);
                while w != 0 {
                    let tz = w.trailing_zeros() as usize;
                    let idx = word_idx * 64 + tz;
                    w &= w - 1;
                    if !f(idx) {
                        return;
                    }
                }
            }
        } else {
            for idx in 0..MAX_TUPLES {
                if !f(idx) {
                    return;
                }
            }
        }
    }

    /// Read and remove a matching tuple from the table (`in`).
    pub fn in_matching(
        &self,
        kind: Option<u32>,
        resource_hash: Option<u64>,
        now_ms: u64,
    ) -> Option<RawTuple> {
        let mut matched: Option<RawTuple> = None;
        self.visit_occupied_slots(|idx| {
            let slot = unsafe { &*self.base_ptr.add(idx) };
            let state = slot.state_ver.load(Ordering::Acquire);
            if state != TUPLE_STATE_COMMITTED {
                return true;
            }

            if slot.expires_at_ms > 0 && slot.expires_at_ms < now_ms {
                if slot
                    .state_ver
                    .compare_exchange(
                        TUPLE_STATE_COMMITTED,
                        TUPLE_STATE_LOCKED,
                        Ordering::AcqRel,
                        Ordering::Relaxed,
                    )
                    .is_ok()
                {
                    unsafe {
                        let slot_mut = &mut *self.base_ptr.add(idx);
                        let off = slot_mut.arena_offset;
                        slot_mut.arena_offset = 0;
                        self.clear_occupied_bit(idx);
                        if off >= ARENA_DATA_START as u32 {
                            self.free_arena_payload(off);
                        }
                        slot_mut
                            .state_ver
                            .store(TUPLE_STATE_EXPIRED, Ordering::Release);
                    }
                }
                return true;
            }

            if let Some(k) = kind {
                if slot.kind_discriminator != k {
                    return true;
                }
            }
            if let Some(h) = resource_hash {
                if slot.resource_hash != h {
                    return true;
                }
            }

            // Lock exclusively so out() cannot overwrite slot/arena while reading & releasing.
            if slot
                .state_ver
                .compare_exchange(
                    TUPLE_STATE_COMMITTED,
                    TUPLE_STATE_LOCKED,
                    Ordering::AcqRel,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                let tuple = self.read_slot(slot);
                unsafe {
                    let slot_mut = &mut *self.base_ptr.add(idx);
                    let off = slot_mut.arena_offset;
                    slot_mut.arena_offset = 0;
                    self.clear_occupied_bit(idx);
                    if off >= ARENA_DATA_START as u32 {
                        self.free_arena_payload(off);
                    }
                    slot_mut
                        .state_ver
                        .store(TUPLE_STATE_TAKEN, Ordering::Release);
                }
                matched = tuple;
                return false;
            }
            true
        });
        matched
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
        if max_results == 0 {
            return results;
        }
        self.visit_occupied_slots(|idx| {
            if results.len() >= max_results {
                return false;
            }
            let slot = unsafe { &*self.base_ptr.add(idx) };
            let state = slot.state_ver.load(Ordering::Acquire);
            if state != TUPLE_STATE_COMMITTED {
                return true;
            }
            if slot.expires_at_ms > 0 && slot.expires_at_ms < now_ms {
                return true;
            }
            if let Some(k) = kind {
                if slot.kind_discriminator != k {
                    return true;
                }
            }
            if let Some(h) = resource_hash {
                if slot.resource_hash != h {
                    return true;
                }
            }
            if let Some(tuple) = self.read_slot_verified_committed(slot) {
                results.push(tuple);
            }
            results.len() < max_results
        });
        results
    }

    fn read_slot_verified_committed(&self, slot: &ShmTupleSlot) -> Option<RawTuple> {
        let tuple = self.read_slot(slot)?;
        if slot.state_ver.load(Ordering::Acquire) == TUPLE_STATE_COMMITTED {
            Some(tuple)
        } else {
            None
        }
    }

    fn read_slot(&self, slot: &ShmTupleSlot) -> Option<RawTuple> {
        let id = Uuid::from_bytes(slot.tuple_id);
        let total_len = slot.payload_len as usize;
        let off = slot.arena_offset as usize;
        let payload = if off >= ARENA_DATA_START && !self.arena_ptr.is_null() {
            let data_start = off + ARENA_BLOCK_HEADER_SIZE;
            let data_end = data_start.saturating_add(total_len);
            if data_end > ARENA_SIZE {
                return None;
            }
            let src =
                unsafe { std::slice::from_raw_parts(self.arena_ptr.add(data_start), total_len) };
            src.to_vec()
        } else {
            let p_len = total_len.min(TUPLE_INLINE_MAX);
            slot.inline_payload[..p_len].to_vec()
        };

        let path_nul = slot
            .resource_path_str
            .iter()
            .position(|&b| b == 0)
            .unwrap_or(128);
        let resource_path =
            String::from_utf8_lossy(&slot.resource_path_str[..path_nul]).into_owned();

        let tag_nul = slot.tag_str.iter().position(|&b| b == 0).unwrap_or(64);
        let tag = String::from_utf8_lossy(&slot.tag_str[..tag_nul]).into_owned();

        Some(RawTuple {
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
        })
    }
}
