/// Core-pinned 8-trigram thread pool for parallel cognition.
///
/// Maps 8 I Ching trigrams to 8 cognitive functions, each pinned to a
/// specific CPU core via `sched_setaffinity(2)`. Threads communicate
/// through shared-memory ring buffers.
///
/// Trigram → Core mapping:
///   ☰ Qián  (Heaven)  → Core 0 (draft generation)
///   ☳ Zhèn  (Thunder) → Core 0 (event detection)
///   ☲ Lí    (Fire)    → Core 1 (verify model)
///   ☴ Xùn   (Wind)    → Core 1 (tool routing)
///   ☵ Kǎn   (Water)   → Core 2 (dream cycle)
///   ☶ Gèn   (Mountain)→ Core 2 (heartbeat)
///   ☷ Kūn   (Earth)   → Core 3 (memory store)
///   ☱ Duì   (Lake)    → Core 3 (output formatting)
///
/// The Wu Xing phase controller toggles `is_active` per trigram to
/// prevent thermal throttling (max 2 trigrams active per phase).

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};

use super::ring_buffer::RingBuffer;

/// The 8 trigrams of the I Ching bagua.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Trigram {
    /// ☰ Heaven — Draft generation
    Qian,
    /// ☳ Thunder — Event detection
    Zhen,
    /// ☲ Fire — Verify model
    Li,
    /// ☴ Wind — Tool routing
    Xun,
    /// ☵ Water — Dream cycle
    Kan,
    /// ☶ Mountain — Stillness/heartbeat
    Gen,
    /// ☷ Earth — Memory store
    Kun,
    /// ☱ Lake — Output formatting
    Dui,
}

impl Trigram {
    /// Get the CPU core ID for this trigram.
    pub fn core_id(&self) -> usize {
        match self {
            Trigram::Qian | Trigram::Zhen => 0,
            Trigram::Li | Trigram::Xun => 1,
            Trigram::Kan | Trigram::Gen => 2,
            Trigram::Kun | Trigram::Dui => 3,
        }
    }

    /// Get the trigram name as a string.
    pub fn name(&self) -> &'static str {
        match self {
            Trigram::Qian => "Qian",
            Trigram::Zhen => "Zhen",
            Trigram::Li => "Li",
            Trigram::Xun => "Xun",
            Trigram::Kan => "Kan",
            Trigram::Gen => "Gen",
            Trigram::Kun => "Kun",
            Trigram::Dui => "Dui",
        }
    }

    /// Get the cognitive function for this trigram.
    pub fn function(&self) -> &'static str {
        match self {
            Trigram::Qian => "draft",
            Trigram::Zhen => "event",
            Trigram::Li => "verify",
            Trigram::Xun => "route",
            Trigram::Kan => "dream",
            Trigram::Gen => "heartbeat",
            Trigram::Kun => "memory",
            Trigram::Dui => "output",
        }
    }

    /// All 8 trigrams in canonical order.
    pub fn all() -> [Trigram; 8] {
        [
            Trigram::Qian,
            Trigram::Zhen,
            Trigram::Li,
            Trigram::Xun,
            Trigram::Kan,
            Trigram::Gen,
            Trigram::Kun,
            Trigram::Dui,
        ]
    }
}

/// Errors that can occur in the trigram pool.
#[derive(Debug)]
pub enum TrigramPoolError {
    CorePinFailed(usize, String),
    RingBufferError(super::ring_buffer::RingBufferError),
    AlreadyRunning,
    NotRunning,
    HandlerMissing(Trigram),
}

impl std::fmt::Display for TrigramPoolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::CorePinFailed(core, msg) => {
                write!(f, "Failed to pin to core {}: {}", core, msg)
            }
            Self::RingBufferError(e) => write!(f, "Ring buffer error: {}", e),
            Self::AlreadyRunning => write!(f, "Trigram pool already running"),
            Self::NotRunning => write!(f, "Trigram pool not running"),
            Self::HandlerMissing(t) => write!(f, "No handler for trigram {}", t.name()),
        }
    }
}

impl std::error::Error for TrigramPoolError {}

impl From<super::ring_buffer::RingBufferError> for TrigramPoolError {
    fn from(e: super::ring_buffer::RingBufferError) -> Self {
        Self::RingBufferError(e)
    }
}

/// Status of a single trigram thread.
#[derive(Clone, Debug)]
pub struct TrigramStatus {
    pub trigram: Trigram,
    pub core_id: usize,
    pub is_active: bool,
    pub is_running: bool,
    pub messages_sent: u64,
    pub messages_received: u64,
}

/// Context passed to each trigram thread handler.
pub struct TrigramContext {
    pub trigram: Trigram,
    pub core_id: usize,
    pub is_active: Arc<AtomicBool>,
    pub pool: Arc<TrigramPoolInner>,
}

impl TrigramContext {
    /// Check if this trigram is currently active (Wu Xing phase controller).
    pub fn is_active(&self) -> bool {
        self.is_active.load(Ordering::Relaxed)
    }

    /// Send a message to another trigram.
    pub fn send(&self, to: Trigram, msg: &[u8]) -> bool {
        self.pool.send(self.trigram, to, msg)
    }

    /// Receive a message addressed to this trigram.
    pub fn recv(&self) -> Option<Vec<u8>> {
        self.pool.recv_for(self.trigram)
    }

    /// Get the trigram name.
    pub fn name(&self) -> &'static str {
        self.trigram.name()
    }
}

/// Inner state of the trigram pool (shared via Arc).
pub struct TrigramPoolInner {
    /// Ring buffers for inter-trigram communication.
    /// Key: (from_trigram, to_trigram)
    ring_buffers: std::sync::Mutex<HashMap<(Trigram, Trigram), RingBuffer>>,
    /// Active flags per trigram (controlled by Wu Xing phase controller).
    active_flags: HashMap<Trigram, Arc<AtomicBool>>,
    /// Running flag for the entire pool.
    running: AtomicBool,
    /// Message counters.
    sent_counters: HashMap<Trigram, std::sync::atomic::AtomicU64>,
    recv_counters: HashMap<Trigram, std::sync::atomic::AtomicU64>,
}

impl TrigramPoolInner {
    fn send(&self, from: Trigram, to: Trigram, msg: &[u8]) -> bool {
        let key = (from, to);
        let buffers = self.ring_buffers.lock().unwrap();
        if let Some(rb) = buffers.get(&key) {
            let success = rb.try_write(msg);
            if success {
                if let Some(counter) = self.sent_counters.get(&from) {
                    counter.fetch_add(1, Ordering::Relaxed);
                }
            }
            success
        } else {
            false
        }
    }

    fn recv_for(&self, trigram: Trigram) -> Option<Vec<u8>> {
        let buffers = self.ring_buffers.lock().unwrap();
        // Check all ring buffers where this trigram is the receiver
        for ((_from, to), rb) in buffers.iter() {
            if *to == trigram {
                if let Some(data) = rb.try_read() {
                    if let Some(counter) = self.recv_counters.get(&trigram) {
                        counter.fetch_add(1, Ordering::Relaxed);
                    }
                    return Some(data);
                }
            }
        }
        None
    }
}

/// The 8-trigram thread pool.
pub struct TrigramPool {
    inner: Arc<TrigramPoolInner>,
    threads: Vec<(Trigram, JoinHandle<()>)>,
    started: bool,
}

impl TrigramPool {
    /// Create a new trigram pool with ring buffers.
    /// Does not start threads yet — call `start()` to begin.
    pub fn new() -> Result<Self, TrigramPoolError> {
        let mut ring_buffers = HashMap::new();
        let mut active_flags = HashMap::new();
        let mut sent_counters = HashMap::new();
        let mut recv_counters = HashMap::new();

        // Create ring buffers for all directional pairs
        for from in Trigram::all().iter() {
            for to in Trigram::all().iter() {
                if from == to {
                    continue;
                }
                let name = format!("{}_to_{}", from.name(), to.name());
                // Clean up any stale SHM file from a previous crashed run
                let shm_path = std::path::Path::new("/dev/shm").join(format!("wm_trigram_{}", name));
                if shm_path.exists() {
                    let _ = std::fs::remove_file(&shm_path);
                }
                let rb = RingBuffer::create(&name, 1024 * 1024)?;
                ring_buffers.insert((*from, *to), rb);
            }
        }

        // Initialize active flags and counters
        for t in Trigram::all().iter() {
            active_flags.insert(*t, Arc::new(AtomicBool::new(true)));
            sent_counters.insert(*t, std::sync::atomic::AtomicU64::new(0));
            recv_counters.insert(*t, std::sync::atomic::AtomicU64::new(0));
        }

        let inner = Arc::new(TrigramPoolInner {
            ring_buffers: std::sync::Mutex::new(ring_buffers),
            active_flags,
            running: AtomicBool::new(false),
            sent_counters,
            recv_counters,
        });

        Ok(Self {
            inner,
            threads: Vec::new(),
            started: false,
        })
    }

    /// Pin the current thread to a specific CPU core.
    fn pin_to_core(core_id: usize) -> Result<(), TrigramPoolError> {
        #[cfg(target_os = "linux")]
        {
            unsafe {
                let mut cpu_set: libc::cpu_set_t = std::mem::zeroed();
                libc::CPU_ZERO(&mut cpu_set);
                libc::CPU_SET(core_id, &mut cpu_set);
                let result = libc::sched_setaffinity(0, std::mem::size_of::<libc::cpu_set_t>(), &cpu_set);
                if result != 0 {
                    let err = std::io::Error::last_os_error();
                    return Err(TrigramPoolError::CorePinFailed(core_id, err.to_string()));
                }
            }
        }
        // On non-Linux, silently skip pinning
        Ok(())
    }

    /// Start all 8 trigram threads with the given handlers.
    ///
    /// Each handler runs in its own thread, pinned to the appropriate core.
    /// The handler receives a TrigramContext for sending/receiving messages
    /// and checking if it's active.
    pub fn start<F>(&mut self, handlers: HashMap<Trigram, F>) -> Result<(), TrigramPoolError>
    where
        F: FnOnce(TrigramContext) + Send + 'static,
    {
        if self.started {
            return Err(TrigramPoolError::AlreadyRunning);
        }

        self.inner.running.store(true, Ordering::Release);

        let mut handlers = handlers;
        let all_trigrams = Trigram::all();
        for trigram in all_trigrams.iter() {
            if let Some(handler) = handlers.remove(trigram) {
                let core_id = trigram.core_id();
                let is_active = self.inner.active_flags.get(trigram).unwrap().clone();
                let inner = self.inner.clone();
                let trigram_val = *trigram;

                let handle = thread::Builder::new()
                    .name(format!("trigram-{}", trigram_val.name()))
                    .spawn(move || {
                        // Pin to core
                        let _ = Self::pin_to_core(core_id);

                        let ctx = TrigramContext {
                            trigram: trigram_val,
                            core_id,
                            is_active,
                            pool: inner,
                        };

                        handler(ctx);
                    })
                    .map_err(|e| {
                        TrigramPoolError::CorePinFailed(core_id, e.to_string())
                    })?;

                self.threads.push((trigram_val, handle));
            }
        }

        self.started = true;
        Ok(())
    }

    /// Send a message from one trigram to another.
    pub fn send(&self, from: Trigram, to: Trigram, msg: &[u8]) -> bool {
        self.inner.send(from, to, msg)
    }

    /// Receive a message for a specific trigram.
    pub fn recv(&self, for_trigram: Trigram) -> Option<Vec<u8>> {
        self.inner.recv_for(for_trigram)
    }

    /// Set the active state of a trigram (called by Wu Xing controller).
    pub fn set_active(&self, trigram: Trigram, active: bool) {
        if let Some(flag) = self.inner.active_flags.get(&trigram) {
            flag.store(active, Ordering::Relaxed);
        }
    }

    /// Check if a trigram is active.
    pub fn is_active(&self, trigram: Trigram) -> bool {
        self.inner
            .active_flags
            .get(&trigram)
            .map(|f| f.load(Ordering::Relaxed))
            .unwrap_or(false)
    }

    /// Stop all trigram threads.
    pub fn stop(&mut self) {
        self.inner.running.store(false, Ordering::Release);

        // Deactivate all trigrams so threads can exit their work loops
        for trigram in Trigram::all().iter() {
            self.set_active(*trigram, false);
        }

        // Wait for threads to finish
        for (trigram, handle) in self.threads.drain(..) {
            if let Err(e) = handle.join() {
                eprintln!("Trigram {} thread panicked: {:?}", trigram.name(), e);
            }
        }

        self.started = false;
    }

    /// Get status of all trigrams.
    pub fn status(&self) -> Vec<TrigramStatus> {
        Trigram::all()
            .iter()
            .map(|t| TrigramStatus {
                trigram: *t,
                core_id: t.core_id(),
                is_active: self.is_active(*t),
                is_running: self.started,
                messages_sent: self
                    .inner
                    .sent_counters
                    .get(t)
                    .map(|c| c.load(Ordering::Relaxed))
                    .unwrap_or(0),
                messages_received: self
                    .inner
                    .recv_counters
                    .get(t)
                    .map(|c| c.load(Ordering::Relaxed))
                    .unwrap_or(0),
            })
            .collect()
    }

    /// Check if the pool is running.
    pub fn is_running(&self) -> bool {
        self.started
    }
}

impl Drop for TrigramPool {
    fn drop(&mut self) {
        if self.started {
            self.stop();
        }
        // Clean up SHM files for all ring buffers
        let buffers = self.inner.ring_buffers.lock().unwrap();
        for ((from, to), _rb) in buffers.iter() {
            let name = format!("{}_to_{}", from.name(), to.name());
            let shm_path = std::path::Path::new("/dev/shm").join(format!("wm_trigram_{}", name));
            let _ = std::fs::remove_file(&shm_path);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // Serialize tests that create TrigramPool (they share SHM file names)
    static TEST_LOCK: Mutex<()> = Mutex::new(());

    #[test]
    fn test_trigram_core_mapping() {
        assert_eq!(Trigram::Qian.core_id(), 0);
        assert_eq!(Trigram::Zhen.core_id(), 0);
        assert_eq!(Trigram::Li.core_id(), 1);
        assert_eq!(Trigram::Xun.core_id(), 1);
        assert_eq!(Trigram::Kan.core_id(), 2);
        assert_eq!(Trigram::Gen.core_id(), 2);
        assert_eq!(Trigram::Kun.core_id(), 3);
        assert_eq!(Trigram::Dui.core_id(), 3);
    }

    #[test]
    fn test_trigram_names_and_functions() {
        assert_eq!(Trigram::Qian.name(), "Qian");
        assert_eq!(Trigram::Qian.function(), "draft");
        assert_eq!(Trigram::Li.function(), "verify");
        assert_eq!(Trigram::Kan.function(), "dream");
    }

    #[test]
    fn test_ring_buffer_communication() {
        let _guard = TEST_LOCK.lock().unwrap();
        let pool = TrigramPool::new().unwrap();

        // Send a message from Qian to Li
        assert!(pool.send(Trigram::Qian, Trigram::Li, b"test message"));

        // Receive it
        let msg = pool.recv(Trigram::Li).unwrap();
        assert_eq!(msg, b"test message");

        // Buffer should be empty now
        assert!(pool.recv(Trigram::Li).is_none());
    }

    #[test]
    fn test_active_flags() {
        let _guard = TEST_LOCK.lock().unwrap();
        let pool = TrigramPool::new().unwrap();

        // All trigrams should start active
        assert!(pool.is_active(Trigram::Qian));
        assert!(pool.is_active(Trigram::Li));

        // Deactivate Qian
        pool.set_active(Trigram::Qian, false);
        assert!(!pool.is_active(Trigram::Qian));
        assert!(pool.is_active(Trigram::Li));

        // Reactivate
        pool.set_active(Trigram::Qian, true);
        assert!(pool.is_active(Trigram::Qian));
    }

    #[test]
    fn test_status() {
        let _guard = TEST_LOCK.lock().unwrap();
        let pool = TrigramPool::new().unwrap();
        let statuses = pool.status();
        assert_eq!(statuses.len(), 8);

        // All should be active initially
        for s in &statuses {
            assert!(s.is_active);
        }

        // Check core assignments
        let qian_status = statuses.iter().find(|s| s.trigram == Trigram::Qian).unwrap();
        assert_eq!(qian_status.core_id, 0);
    }

    #[test]
    fn test_thread_start_stop() {
        let _guard = TEST_LOCK.lock().unwrap();
        let pool = Arc::new(Mutex::new(TrigramPool::new().unwrap()));
        let pool_clone = pool.clone();

        let mut handlers: HashMap<Trigram, Box<dyn FnOnce(TrigramContext) + Send>> =
            HashMap::new();

        // Simple handler that counts messages until stopped
        for trigram in Trigram::all().iter() {
            handlers.insert(*trigram, Box::new(move |ctx: TrigramContext| {
                while ctx.pool.running.load(Ordering::Relaxed) {
                    if let Some(_msg) = ctx.recv() {
                        // Process message
                    }
                    if !ctx.is_active() {
                        std::thread::yield_now();
                        continue;
                    }
                    std::thread::yield_now();
                }
            }));
        }

        {
            let mut p = pool_clone.lock().unwrap();
            p.start(handlers).unwrap();
            assert!(p.is_running());
        }

        // Let threads run briefly
        std::thread::sleep(std::time::Duration::from_millis(50));

        {
            let mut p = pool_clone.lock().unwrap();
            p.stop();
            assert!(!p.is_running());
        }
    }
}
