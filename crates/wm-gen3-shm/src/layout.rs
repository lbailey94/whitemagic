//! Memory topology and cache-line aligned POD structures for POSIX shared memory.
//!
//! Enforces exact byte sizing and 64-byte alignment to eliminate false sharing.

use std::sync::atomic::{AtomicU32, AtomicU64};

pub const SHM_MAGIC: u64 = 0x574D5F53484D3031; // "WM_SHM01"
pub const SHM_VERSION: u32 = 1;
pub const SHM_TOTAL_SIZE: usize = 64 * 1024 * 1024; // 64 MiB

pub const MAX_WORKERS: usize = 1024;
pub const MAX_TUPLES: usize = 32768;
pub const MAX_PHEROMONES: usize = 16384;
pub const RING_BUFFER_SIZE: usize = 16384; // per ring (must be power of two)

// Tuple States
pub const TUPLE_STATE_EMPTY: u32 = 0;
pub const TUPLE_STATE_WRITING: u32 = 1;
pub const TUPLE_STATE_COMMITTED: u32 = 2;
pub const TUPLE_STATE_LOCKED: u32 = 3;
pub const TUPLE_STATE_TAKEN: u32 = 4;
pub const TUPLE_STATE_EXPIRED: u32 = 5;

// Pheromone States
pub const PHEROMONE_STATE_EMPTY: u32 = 0;
pub const PHEROMONE_STATE_ACTIVE: u32 = 1;
pub const PHEROMONE_STATE_EVAPORATED: u32 = 2;

/// Superblock & System Synchronization Header (4 KiB, Page-Aligned).
#[repr(C, align(4096))]
pub struct ShmSuperblock {
    pub magic: u64,
    pub version: u32,
    pub flags: u32,
    pub epoch: AtomicU64,
    pub created_at_ms: u64,
    pub total_size: u64,

    // Partition Byte Offsets
    pub heartbeat_offset: u64,
    pub ring_offsets: [u64; 4],
    pub tuple_table_offset: u64,
    pub stigmergy_offset: u64,
    pub arena_offset: u64,

    // Linux Futex Sync Words (Zero-Spin Waiting)
    pub ring_futex: [AtomicU32; 4],
    pub tuple_futex: AtomicU32,
    pub stigmergy_futex: AtomicU32,

    pub _reserved: [u8; 3968],
}

/// Worker Registration & Heartbeat Slot (64 bytes = exact 1 L1D cache-line).
#[repr(C, align(64))]
pub struct WorkerHeartbeatSlot {
    pub pid: AtomicU32,
    pub state: AtomicU32, // 0=Idle, 1=Active, 2=InDream, 3=Dead
    pub agent_id_hash: u64,
    pub last_heartbeat_ms: AtomicU64,
    pub active_claims_count: AtomicU32,
    pub generation: AtomicU32,
    pub _pad: [u8; 32],
}

/// Associative Linda Tuple Slot (768 bytes = 12 cache lines).
#[repr(C, align(64))]
pub struct ShmTupleSlot {
    pub state_ver: AtomicU32,
    pub kind_discriminator: u32, // 1=Claim, 2=Task, 3=AuthorityGrant, 4=ResultNotice, 5=Generic
    pub tuple_id: [u8; 16],
    pub created_at_ms: u64,
    pub expires_at_ms: u64,
    pub resource_hash: u64,
    pub holder_issuer_hash: u64,
    pub task_id: [u8; 16],
    pub landlock_token: [u8; 32],
    pub capability_mask: u64,
    pub payload_len: u32,
    pub arena_offset: u32,
    pub resource_path_str: [u8; 128],
    pub tag_str: [u8; 64],
    pub inline_payload: [u8; 384],
    pub _pad: [u8; 72],
}

/// Digital Stigmergic Pheromone Slot (512 bytes = 8 cache lines).
#[repr(C, align(64))]
pub struct ShmPheromoneSlot {
    pub state_ver: AtomicU32, // 0=EMPTY, 1=ACTIVE, 2=EVAPORATED
    pub kind: u32,            // 0=MutationActive, 1=Inspection, 2=Refactoring, 3=Review
    pub p_id: [u8; 16],
    pub target_path_hash: u64,
    pub ast_scope_hash: u64,
    pub line_start: u32,
    pub line_end: u32,
    pub initial_intensity: f32,
    pub half_life_ms: u32,
    pub emitted_at_ms: u64,
    pub issuer_hash: u64,
    pub target_path_str: [u8; 160],
    pub ast_scope_str: [u8; 96],
    pub issuer_str: [u8; 48],
    pub _pad: [u8; 136],
}

/// MPMC Queue Ring Cell (256 bytes).
#[repr(C, align(64))]
pub struct RingCell {
    pub sequence: AtomicU64,
    pub payload_len: u32,
    pub flags: u32,
    pub payload: [u8; 240],
}

// Compile-Time Invariant Assertions
const _: () = assert!(std::mem::size_of::<ShmSuperblock>() == 4096);
const _: () = assert!(std::mem::size_of::<WorkerHeartbeatSlot>() == 64);
const _: () = assert!(std::mem::size_of::<ShmTupleSlot>() == 768);
const _: () = assert!(std::mem::size_of::<ShmPheromoneSlot>() == 512);
const _: () = assert!(std::mem::size_of::<RingCell>() == 256);

// Precise Partition Layout Offsets
pub const SUPERBLOCK_OFFSET: usize = 0;
pub const SUPERBLOCK_SIZE: usize = 4096;

pub const HEARTBEAT_OFFSET: usize = 4096;
pub const HEARTBEAT_SIZE: usize = MAX_WORKERS * std::mem::size_of::<WorkerHeartbeatSlot>(); // 65,536 bytes

pub const RING_HEADER_SIZE: usize = 4096;
pub const RING_CELLS_SIZE: usize = RING_BUFFER_SIZE * std::mem::size_of::<RingCell>(); // 4,194,304 bytes
pub const RING_TOTAL_SIZE: usize = RING_HEADER_SIZE + RING_CELLS_SIZE; // 4,198,400 bytes

pub const RING_0_OFFSET: usize = 69632;
pub const RING_1_OFFSET: usize = RING_0_OFFSET + RING_TOTAL_SIZE;
pub const RING_2_OFFSET: usize = RING_1_OFFSET + RING_TOTAL_SIZE;
pub const RING_3_OFFSET: usize = RING_2_OFFSET + RING_TOTAL_SIZE;

pub const TUPLE_TABLE_OFFSET: usize = RING_3_OFFSET + RING_TOTAL_SIZE; // 16,863,232
pub const TUPLE_TABLE_SIZE: usize = MAX_TUPLES * std::mem::size_of::<ShmTupleSlot>(); // 25,165,824 bytes

pub const STIGMERGY_OFFSET: usize = TUPLE_TABLE_OFFSET + TUPLE_TABLE_SIZE; // 42,029,056
pub const STIGMERGY_SIZE: usize = MAX_PHEROMONES * std::mem::size_of::<ShmPheromoneSlot>(); // 8,388,608 bytes

pub const ARENA_OFFSET: usize = STIGMERGY_OFFSET + STIGMERGY_SIZE; // 50,417,664
pub const ARENA_SIZE: usize = SHM_TOTAL_SIZE - ARENA_OFFSET; // 16,691,200 bytes (~15.91 MiB)

const _: () = assert!(ARENA_OFFSET + ARENA_SIZE == SHM_TOTAL_SIZE);
