//! Digital stigmergic pheromone field over shared memory.
//!
//! Sub-microsecond conflict detection with exponential half-life decay.

use crate::layout::{
    MAX_PHEROMONES, PHEROMONE_STATE_ACTIVE, PHEROMONE_STATE_EMPTY, PHEROMONE_STATE_EVAPORATED,
    ShmPheromoneSlot,
};
use std::marker::PhantomData;
use std::sync::atomic::Ordering;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct RawPheromone {
    pub id: Uuid,
    pub kind: u32,
    pub target_path: String,
    pub ast_scope: String,
    pub line_start: u32,
    pub line_end: u32,
    pub initial_intensity: f32,
    pub half_life_ms: u32,
    pub emitted_at_ms: u64,
    pub issuer: String,
}

#[derive(Debug, Clone)]
pub struct ShmConflict {
    pub conflict_id: Uuid,
    pub active_issuer: String,
    pub intensity: f32,
    pub line_start: u32,
    pub line_end: u32,
}

pub struct ShmStigmergyMatrix<'a> {
    base_ptr: *mut ShmPheromoneSlot,
    _marker: PhantomData<&'a ()>,
}

unsafe impl<'a> Send for ShmStigmergyMatrix<'a> {}
unsafe impl<'a> Sync for ShmStigmergyMatrix<'a> {}

impl<'a> ShmStigmergyMatrix<'a> {
    /// Format and initialize the pheromone matrix memory.
    pub unsafe fn init(slots: *mut ShmPheromoneSlot, count: usize) {
        unsafe {
            for i in 0..count {
                let slot = slots.add(i);
                (*slot)
                    .state_ver
                    .store(PHEROMONE_STATE_EMPTY, Ordering::Relaxed);
            }
        }
    }

    pub fn new(base_ptr: *mut ShmPheromoneSlot) -> Self {
        Self {
            base_ptr,
            _marker: PhantomData,
        }
    }

    /// Emit a pheromone deposit onto the shared field.
    pub fn emit(&self, p: &RawPheromone) -> Result<Uuid, &'static str> {
        let path_hash = Self::hash_str(&p.target_path);
        let ast_hash = Self::hash_str(&p.ast_scope);
        let start_idx = (path_hash as usize) % MAX_PHEROMONES;

        for step in 0..MAX_PHEROMONES {
            let idx = (start_idx + step) % MAX_PHEROMONES;
            let slot = unsafe { &*self.base_ptr.add(idx) };

            let curr = slot.state_ver.load(Ordering::Acquire);
            if curr == PHEROMONE_STATE_EMPTY || curr == PHEROMONE_STATE_EVAPORATED {
                if slot
                    .state_ver
                    .compare_exchange(
                        curr,
                        PHEROMONE_STATE_ACTIVE,
                        Ordering::AcqRel,
                        Ordering::Relaxed,
                    )
                    .is_ok()
                {
                    unsafe {
                        let slot_ref = &mut *self.base_ptr.add(idx);
                        slot_ref.kind = p.kind;
                        slot_ref.p_id.copy_from_slice(p.id.as_bytes());
                        slot_ref.target_path_hash = path_hash;
                        slot_ref.ast_scope_hash = ast_hash;
                        slot_ref.line_start = p.line_start;
                        slot_ref.line_end = p.line_end;
                        slot_ref.initial_intensity = p.initial_intensity;
                        slot_ref.half_life_ms = p.half_life_ms.max(100);
                        slot_ref.emitted_at_ms = p.emitted_at_ms;
                        slot_ref.issuer_hash = Self::hash_str(&p.issuer);

                        let p_bytes = p.target_path.as_bytes();
                        let p_len = p_bytes.len().min(159);
                        slot_ref.target_path_str[..p_len].copy_from_slice(&p_bytes[..p_len]);
                        slot_ref.target_path_str[p_len] = 0;

                        let a_bytes = p.ast_scope.as_bytes();
                        let a_len = a_bytes.len().min(95);
                        slot_ref.ast_scope_str[..a_len].copy_from_slice(&a_bytes[..a_len]);
                        slot_ref.ast_scope_str[a_len] = 0;

                        let i_bytes = p.issuer.as_bytes();
                        let i_len = i_bytes.len().min(47);
                        slot_ref.issuer_str[..i_len].copy_from_slice(&i_bytes[..i_len]);
                        slot_ref.issuer_str[i_len] = 0;
                    }
                    return Ok(p.id);
                }
            }
        }
        Err("Pheromone matrix full")
    }

    /// Sense active conflicting pheromones overlapping a target file and line range.
    pub fn sense_conflicts(
        &self,
        target_path: &str,
        line_start: u32,
        line_end: u32,
        threshold: f32,
        now_ms: u64,
        ignore_issuer: Option<&str>,
    ) -> Vec<ShmConflict> {
        let path_hash = Self::hash_str(target_path);
        let ignore_hash = ignore_issuer.map(Self::hash_str).unwrap_or(0);
        let mut conflicts = Vec::new();

        for idx in 0..MAX_PHEROMONES {
            let slot = unsafe { &*self.base_ptr.add(idx) };
            if slot.state_ver.load(Ordering::Acquire) != PHEROMONE_STATE_ACTIVE {
                continue;
            }

            if slot.target_path_hash != path_hash {
                continue;
            }

            if ignore_hash != 0 && slot.issuer_hash == ignore_hash {
                continue;
            }

            // Check line overlap
            let max_start = line_start.max(slot.line_start);
            let min_end = line_end.min(slot.line_end);
            if max_start <= min_end {
                // Compute mathematical decay: I(t) = I0 * 2^(-dt / tau)
                let dt = (now_ms.saturating_sub(slot.emitted_at_ms)) as f32;
                let tau = slot.half_life_ms as f32;
                let factor = (-dt / tau).exp2();
                let current_intensity = slot.initial_intensity * factor;

                if current_intensity >= threshold {
                    let nul = slot.issuer_str.iter().position(|&b| b == 0).unwrap_or(48);
                    let issuer = String::from_utf8_lossy(&slot.issuer_str[..nul]).into_owned();

                    conflicts.push(ShmConflict {
                        conflict_id: Uuid::from_bytes(slot.p_id),
                        active_issuer: issuer,
                        intensity: current_intensity,
                        line_start: slot.line_start,
                        line_end: slot.line_end,
                    });
                }
            }
        }

        conflicts
    }

    /// Evaporate dormant pheromones whose intensity has fallen below threshold.
    pub fn evaporate(&self, now_ms: u64, threshold: f32) -> usize {
        let mut purged = 0;
        for idx in 0..MAX_PHEROMONES {
            let slot = unsafe { &*self.base_ptr.add(idx) };
            if slot.state_ver.load(Ordering::Acquire) == PHEROMONE_STATE_ACTIVE {
                let dt = (now_ms.saturating_sub(slot.emitted_at_ms)) as f32;
                let tau = slot.half_life_ms as f32;
                let factor = (-dt / tau).exp2();
                let current_intensity = slot.initial_intensity * factor;

                if current_intensity < threshold {
                    slot.state_ver
                        .store(PHEROMONE_STATE_EVAPORATED, Ordering::Release);
                    purged += 1;
                }
            }
        }
        purged
    }

    fn hash_str(s: &str) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut h = DefaultHasher::new();
        s.hash(&mut h);
        h.finish()
    }
}
