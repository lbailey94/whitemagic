//! WhiteMagic Gen3 — Zero-Copy POSIX Shared Memory Sub-Symbolic Substrate.
//!
//! Sub-microsecond (< 250ns) inter-agent transport over `/dev/shm`.
//! Eliminates multi-thousand token LLM chat coordination overhead.

pub mod futex;
pub mod layout;
pub mod ring;
pub mod stigmergy_matrix;
pub mod tuple_table;

pub use futex::{futex_wait, futex_wake};
pub use layout::*;
pub use ring::{MpmcQueueHeader, ShmMpmcQueue};
pub use stigmergy_matrix::{RawPheromone, ShmConflict, ShmStigmergyMatrix};
pub use tuple_table::{RawTuple, ShmTupleTable};

#[cfg(unix)]
use std::ffi::CString;
#[cfg(unix)]
use std::fs::File;
#[cfg(unix)]
use std::os::fd::{FromRawFd, IntoRawFd, RawFd};
#[cfg(not(unix))]
type RawFd = i32;
use std::sync::atomic::Ordering;
use std::sync::Arc;
use std::time::SystemTime;
use uuid::Uuid;

/// Zero-Copy Shared Memory Substrate.
pub struct ShmSubstrate {
    mmap: memmap2::MmapMut,
    raw_fd: Option<RawFd>,
    is_owner: bool,
    #[cfg_attr(not(unix), allow(dead_code))]
    shm_name: Option<String>,
}

unsafe impl Send for ShmSubstrate {}
unsafe impl Sync for ShmSubstrate {}

impl ShmSubstrate {
    /// Create or attach to a named POSIX shared memory segment (e.g. "/wm_substrate_v1").
    #[cfg(unix)]
    pub fn open_or_create(shm_name: &str) -> std::io::Result<Self> {
        let normalized_name = if shm_name.starts_with('/') {
            shm_name.to_string()
        } else {
            format!("/{}", shm_name)
        };

        let c_name = CString::new(normalized_name.as_str())
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidInput, e))?;

        // Try exclusive create first
        let fd = unsafe {
            libc::shm_open(
                c_name.as_ptr(),
                libc::O_RDWR | libc::O_CREAT | libc::O_EXCL,
                0o660,
            )
        };

        if fd >= 0 {
            // We are the creator! Set segment size
            let trunc_res = unsafe { libc::ftruncate(fd, SHM_TOTAL_SIZE as libc::off_t) };
            if trunc_res != 0 {
                let err = std::io::Error::last_os_error();
                unsafe {
                    libc::close(fd);
                    libc::shm_unlink(c_name.as_ptr());
                }
                return Err(err);
            }

            let file = unsafe { File::from_raw_fd(fd) };
            let mut mmap = unsafe { memmap2::MmapMut::map_mut(&file)? };

            unsafe {
                Self::init_memory(mmap.as_mut_ptr());
            }

            Ok(Self {
                mmap,
                raw_fd: Some(file.into_raw_fd()),
                is_owner: true,
                shm_name: Some(normalized_name),
            })
        } else {
            // Already exists or permission denied
            let open_fd = unsafe { libc::shm_open(c_name.as_ptr(), libc::O_RDWR, 0o660) };
            if open_fd < 0 {
                return Err(std::io::Error::last_os_error());
            }

            let file = unsafe { File::from_raw_fd(open_fd) };
            let mmap = unsafe { memmap2::MmapMut::map_mut(&file)? };

            let substrate = Self {
                mmap,
                raw_fd: Some(file.into_raw_fd()),
                is_owner: false,
                shm_name: Some(normalized_name),
            };

            // Verify magic
            if substrate.superblock().magic != SHM_MAGIC {
                // Wait briefly for creator initialization (up to 100ms)
                for _ in 0..100 {
                    std::thread::sleep(std::time::Duration::from_millis(1));
                    if substrate.superblock().magic == SHM_MAGIC {
                        break;
                    }
                }
                if substrate.superblock().magic != SHM_MAGIC {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        "SHM segment header invalid or uninitialized",
                    ));
                }
            }

            Ok(substrate)
        }
    }

    /// Named POSIX shared memory is unavailable off-Unix; Windows builds use
    /// the in-process [`ShmSubstrate::anonymous`] substrate instead.
    #[cfg(not(unix))]
    pub fn open_or_create(_shm_name: &str) -> std::io::Result<Self> {
        Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "named POSIX shared memory is unavailable on this platform; use ShmSubstrate::anonymous()",
        ))
    }

    /// Allocate an anonymous, in-process shared memory substrate (ideal for unit testing).
    pub fn anonymous() -> std::io::Result<Self> {
        let mut mmap = memmap2::MmapMut::map_anon(SHM_TOTAL_SIZE)?;
        unsafe {
            Self::init_memory(mmap.as_mut_ptr());
        }
        Ok(Self {
            mmap,
            raw_fd: None,
            is_owner: true,
            shm_name: None,
        })
    }

    /// Attach directly from an inherited file descriptor (critical for Landlocked sandboxes).
    #[cfg(unix)]
    pub fn from_raw_fd(fd: RawFd, is_owner: bool) -> std::io::Result<Self> {
        let file = unsafe { File::from_raw_fd(fd) };
        let mmap = unsafe { memmap2::MmapMut::map_mut(&file)? };
        let retained_fd = file.into_raw_fd();

        let substrate = Self {
            mmap,
            raw_fd: Some(retained_fd),
            is_owner,
            shm_name: None,
        };

        if substrate.superblock().magic != SHM_MAGIC {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "SHM segment from FD has invalid magic",
            ));
        }

        Ok(substrate)
    }

    /// Inherited POSIX descriptors do not exist off-Unix.
    #[cfg(not(unix))]
    pub fn from_raw_fd(_fd: RawFd, _is_owner: bool) -> std::io::Result<Self> {
        Err(std::io::Error::new(
            std::io::ErrorKind::Unsupported,
            "inherited shared-memory descriptors are unavailable on this platform",
        ))
    }

    /// Returns the underlying raw file descriptor if backed by POSIX shm.
    pub fn raw_fd(&self) -> Option<RawFd> {
        self.raw_fd
    }

    /// Returns whether this instance created the segment.
    pub fn is_owner(&self) -> bool {
        self.is_owner
    }

    /// Access the superblock header.
    pub fn superblock(&self) -> &ShmSuperblock {
        unsafe { &*(self.mmap.as_ptr() as *const ShmSuperblock) }
    }

    /// Access the worker heartbeats array.
    pub fn heartbeats(&self) -> &[WorkerHeartbeatSlot] {
        unsafe {
            let ptr = self.mmap.as_ptr().add(HEARTBEAT_OFFSET) as *const WorkerHeartbeatSlot;
            std::slice::from_raw_parts(ptr, MAX_WORKERS)
        }
    }

    /// Access one of the 4 high-velocity MPMC ring queues (0..4).
    pub fn ring(&self, idx: usize) -> Option<ShmMpmcQueue<'_>> {
        if idx >= 4 {
            return None;
        }
        let ring_offsets = [RING_0_OFFSET, RING_1_OFFSET, RING_2_OFFSET, RING_3_OFFSET];
        let offset = ring_offsets[idx];

        let header_ptr = unsafe { self.mmap.as_ptr().add(offset) as *mut MpmcQueueHeader };
        let cells_ptr = unsafe {
            self.mmap
                .as_ptr()
                .add(offset + RING_HEADER_SIZE) as *mut RingCell
        };
        Some(ShmMpmcQueue::new(header_ptr, cells_ptr))
    }

    /// Access the Linda associative tuple table.
    pub fn tuple_table(&self) -> ShmTupleTable<'_> {
        let ptr = unsafe { self.mmap.as_ptr().add(TUPLE_TABLE_OFFSET) as *mut ShmTupleSlot };
        ShmTupleTable::new(ptr)
    }

    /// Access the digital stigmergic pheromone matrix.
    pub fn stigmergy(&self) -> ShmStigmergyMatrix<'_> {
        let ptr = unsafe { self.mmap.as_ptr().add(STIGMERGY_OFFSET) as *mut ShmPheromoneSlot };
        ShmStigmergyMatrix::new(ptr)
    }

    /// Futex primitive: wait on tuple state changes.
    pub fn futex_wait_tuple(&self, expected: u32, timeout_ms: Option<u64>) {
        futex_wait(&self.superblock().tuple_futex, expected, timeout_ms);
    }

    /// Futex primitive: wake threads waiting on tuple changes.
    pub fn futex_wake_tuple(&self, count: i32) -> i32 {
        self.superblock().tuple_futex.fetch_add(1, Ordering::Relaxed);
        futex_wake(&self.superblock().tuple_futex, count)
    }

    /// Futex primitive: wait on stigmergy state changes.
    pub fn futex_wait_stigmergy(&self, expected: u32, timeout_ms: Option<u64>) {
        futex_wait(&self.superblock().stigmergy_futex, expected, timeout_ms);
    }

    /// Futex primitive: wake threads waiting on stigmergy changes.
    pub fn futex_wake_stigmergy(&self, count: i32) -> i32 {
        self.superblock().stigmergy_futex.fetch_add(1, Ordering::Relaxed);
        futex_wake(&self.superblock().stigmergy_futex, count)
    }

    /// Explicitly unlink the shared memory segment from `/dev/shm`.
    #[cfg(unix)]
    pub fn unlink(&mut self) -> std::io::Result<()> {
        if let Some(name) = &self.shm_name {
            let c_name = CString::new(name.as_str())
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidInput, e))?;
            let res = unsafe { libc::shm_unlink(c_name.as_ptr()) };
            if res != 0 {
                return Err(std::io::Error::last_os_error());
            }
            self.shm_name = None;
        }
        Ok(())
    }

    /// Named segments never exist off-Unix, so there is nothing to unlink.
    #[cfg(not(unix))]
    pub fn unlink(&mut self) -> std::io::Result<()> {
        Ok(())
    }

    /// Internal formatting routine for raw shared memory.
    unsafe fn init_memory(ptr: *mut u8) {
        unsafe {
            std::ptr::write_bytes(ptr, 0, SHM_TOTAL_SIZE);

            let sb = ptr as *mut ShmSuperblock;
            (*sb).magic = SHM_MAGIC;
            (*sb).version = SHM_VERSION;
            (*sb).flags = 1; // ACTIVE
            (*sb).epoch = std::sync::atomic::AtomicU64::new(1);
            let now_ms = SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0);
            (*sb).created_at_ms = now_ms;
            (*sb).total_size = SHM_TOTAL_SIZE as u64;

            (*sb).heartbeat_offset = HEARTBEAT_OFFSET as u64;
            (*sb).ring_offsets = [
                RING_0_OFFSET as u64,
                RING_1_OFFSET as u64,
                RING_2_OFFSET as u64,
                RING_3_OFFSET as u64,
            ];
            (*sb).tuple_table_offset = TUPLE_TABLE_OFFSET as u64;
            (*sb).stigmergy_offset = STIGMERGY_OFFSET as u64;
            (*sb).arena_offset = ARENA_OFFSET as u64;

            // Initialize 4 MPMC rings
            let ring_offsets = [RING_0_OFFSET, RING_1_OFFSET, RING_2_OFFSET, RING_3_OFFSET];
            for &offset in &ring_offsets {
                let header_ptr = ptr.add(offset) as *mut MpmcQueueHeader;
                let cells_ptr = ptr.add(offset + RING_HEADER_SIZE) as *mut RingCell;
                ShmMpmcQueue::init(header_ptr, cells_ptr, RING_BUFFER_SIZE);
            }

            // Initialize Linda tuple slots
            let tuple_slots_ptr = ptr.add(TUPLE_TABLE_OFFSET) as *mut ShmTupleSlot;
            ShmTupleTable::init(tuple_slots_ptr, MAX_TUPLES);

            // Initialize Stigmergic pheromone slots
            let p_slots_ptr = ptr.add(STIGMERGY_OFFSET) as *mut ShmPheromoneSlot;
            ShmStigmergyMatrix::init(p_slots_ptr, MAX_PHEROMONES);
        }
    }
}

impl Drop for ShmSubstrate {
    fn drop(&mut self) {
        #[cfg(unix)]
        if let Some(fd) = self.raw_fd {
            unsafe {
                libc::close(fd);
            }
        }
    }
}

/// High-level Linda Tuple Space wrapper over shared memory.
#[derive(Clone)]
pub struct ShmTupleSpace {
    substrate: Arc<ShmSubstrate>,
}

impl ShmTupleSpace {
    pub fn new(substrate: Arc<ShmSubstrate>) -> Self {
        Self { substrate }
    }

    /// Deposit a tuple into the shared space and wake waiters.
    pub fn out(&self, tuple: &RawTuple) -> Result<Uuid, &'static str> {
        let id = self.substrate.tuple_table().out(tuple)?;
        self.substrate.futex_wake_tuple(1);
        Ok(id)
    }

    /// Read and take matching tuple.
    pub fn in_matching(&self, kind: Option<u32>, resource_hash: Option<u64>, now_ms: u64) -> Option<RawTuple> {
        let tuple = self.substrate.tuple_table().in_matching(kind, resource_hash, now_ms)?;
        self.substrate.futex_wake_tuple(1);
        Some(tuple)
    }

    /// Read matching tuples without taking.
    pub fn rd_matching(&self, kind: Option<u32>, resource_hash: Option<u64>, max_results: usize, now_ms: u64) -> Vec<RawTuple> {
        self.substrate.tuple_table().rd_matching(kind, resource_hash, max_results, now_ms)
    }
}

/// High-level Digital Stigmergic Field wrapper over shared memory.
#[derive(Clone)]
pub struct ShmStigmergyField {
    substrate: Arc<ShmSubstrate>,
}

impl ShmStigmergyField {
    pub fn new(substrate: Arc<ShmSubstrate>) -> Self {
        Self { substrate }
    }

    /// Emit a pheromone deposit and wake waiters.
    pub fn emit(&self, p: &RawPheromone) -> Result<Uuid, &'static str> {
        let id = self.substrate.stigmergy().emit(p)?;
        self.substrate.futex_wake_stigmergy(1);
        Ok(id)
    }

    /// Sense conflicting pheromones.
    pub fn sense_conflicts(
        &self,
        target_path: &str,
        line_start: u32,
        line_end: u32,
        threshold: f32,
        now_ms: u64,
        ignore_issuer: Option<&str>,
    ) -> Vec<ShmConflict> {
        self.substrate.stigmergy().sense_conflicts(
            target_path,
            line_start,
            line_end,
            threshold,
            now_ms,
            ignore_issuer,
        )
    }

    /// Evaporate pheromones.
    pub fn evaporate(&self, now_ms: u64, threshold: f32) -> usize {
        self.substrate.stigmergy().evaporate(now_ms, threshold)
    }
}
