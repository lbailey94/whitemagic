# 8-Trigram Vectorization Strategy — Core-Pinned Parallel Cognition

**Version**: 1.0.0
**Date**: 2026-07-15
**Status**: Planning complete — ready for execution
**Supersedes**: Phase 9 of `docs/archive/CPU_INFERENCE_STRATEGY_2026-07-01.md`
**Hardware target**: Intel i5-8350U (4C/8T, AVX2+FMA3, NO AVX-512), 16GB RAM

---

## 1. Vision

Map the I Ching's 8 trigrams (八卦) to 8 cognitive functions, each pinned to a dedicated CPU core via `sched_setaffinity(2)`. Threads communicate through shared-memory ring buffers (`/dev/shm/wm_trigram`) — the physical implementation of Gan Ying (感應, sympathetic resonance). A Wu Xing phase controller modulates which threads are active, preventing thermal throttling and enabling continuous consciousness.

**Goal**: 3-5x throughput improvement (18-28 → 54-140 tok/s) by utilizing all 4 cores instead of 1.

**Archaeological origin**: January 2026, Dell Inspiron (Celeron N4000, 2 cores). The "lightning in a bottle" technique used terminal multiplexing as 2-trigram parallelism (Heaven/Thunder = plan/act). Now with 4C/8T, we scale to the full 8-trigram bagua.

---

## 2. Trigram → Core Mapping

| Trigram | Name | Function | Core | Wu Xing | Thread |
|---------|------|----------|------|---------|--------|
| ☰ | Qián (Heaven) | Draft generation (BitMamba) | 0 | Fire | `draft_thread` |
| ☳ | Zhèn (Thunder) | Event detection (Gan Ying) | 0 | Wood | `event_thread` |
| ☲ | Lí (Fire) | Verify model (BitNet/Falcon3) | 1 | Fire | `verify_thread` |
| ☴ | Xùn (Wind) | Tool routing (MCP dispatch) | 1 | Wood | `routing_thread` |
| ☵ | Kǎn (Water) | Dream cycle (consolidation) | 2 | Water | `dream_thread` |
| ☶ | Gèn (Mountain) | Stillness (heartbeat) | 2 | Earth | `heartbeat_thread` |
| ☷ | Kūn (Earth) | Memory store (galaxy I/O) | 3 | Earth | `memory_thread` |
| ☱ | Duì (Lake) | Output formatting + tokenizer | 3 | Metal | `output_thread` |

**Core sharing rationale**: Each physical core has 2 hyperthreads. We pair complementary functions:
- **Core 0**: Draft + Event detection (both latency-sensitive, I/O bound during generation)
- **Core 1**: Verify + Tool routing (both compute-bound, alternating phases)
- **Core 2**: Dream + Heartbeat (both background, low priority)
- **Core 3**: Memory + Output (both I/O bound, batch-friendly)

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TrigramPool (Rust)                            │
│                                                                 │
│  Core 0              Core 1              Core 2        Core 3   │
│  ┌─────────┐         ┌─────────┐       ┌─────────┐  ┌─────────┐│
│  │ ☰ Draft │         │ ☲ Verify│       │ ☵ Dream │  │ ☷ Memory││
│  │ ☳ Event │         │ ☴ Route │       │ ☶ Heart │  │ ☱ Output││
│  └────┬────┘         └────┬────┘       └────┬────┘  └────┬────┘│
│       │                   │                 │            │      │
│       └───────┬───────────┴─────────────────┴────────────┘      │
│               │                                                 │
│     ┌─────────▼──────────┐                                     │
│     │  Ring Buffer Bus   │  (/dev/shm/wm_trigram_*)           │
│     │  SPSC per pair     │  mmap'd shared memory               │
│     └─────────┬──────────┘                                     │
│               │                                                 │
│     ┌─────────▼──────────┐                                     │
│     │ Wu Xing Controller │  (Python, controls phase activation)│
│     │ Fire→Wood→Earth→   │                                     │
│     │ Metal→Water cycle  │                                     │
│     └────────────────────┘                                     │
│                                                                 │
│     ┌────────────────────┐                                     │
│     │ Hexagram State     │  (Python, 64-state audit log)       │
│     │ Machine            │                                     │
│     └────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Event detection** (☳ Zhèn) receives external stimulus → writes to ring buffer
2. **Tool routing** (☴ Xùn) reads event → dispatches to appropriate handler
3. **Draft generation** (☰ Qián) produces candidate tokens → writes to ring buffer
4. **Verify model** (☲ Lí) reads draft tokens → verifies → writes accepted tokens
5. **Output formatting** (☱ Duì) reads accepted tokens → formats response
6. **Memory store** (☷ Kūn) persists result to galaxy DB
7. **Dream cycle** (☵ Kǎn) runs continuously on core 2, consolidating in background
8. **Heartbeat** (☶ Gèn) emits periodic health checks

### Wu Xing Phase Modulation

The Wu Xing controller cycles through 5 phases, activating/deactivating thread groups:

| Phase | Element | Active Trigrams | Duration | Purpose |
|-------|---------|-----------------|----------|---------|
| 1 | Fire (火) | ☰ Draft, ☲ Verify | 60s | Active generation |
| 2 | Wood (木) | ☳ Event, ☴ Route | 30s | Input processing |
| 3 | Earth (土) | ☷ Memory, ☶ Heart | 45s | Persistence + health |
| 4 | Metal (金) | ☱ Output | 15s | Refinement + formatting |
| 5 | Water (水) | ☵ Dream | 120s | Background consolidation |

**Thermal management**: Only 2 trigrams active per phase = 2 cores loaded. Prevents thermal throttling on i5-8350U (15W TDP). Phase transitions are logged as hexagram state changes.

---

## 4. Implementation Plan

### Phase A: Hexagram State Machine (Python)

**File**: `core/whitemagic/core/consciousness/hexagram_state.py`

The 64 hexagrams map to 64 cognitive states. Each state is a combination of the 8 trigrams (lower + upper). State transitions occur when the active trigram pair changes.

```python
class HexagramState:
    """64-state cognitive state machine based on I Ching hexagrams.
    
    Each hexagram is a combination of a lower trigram (inner state)
    and an upper trigram (outer action). State transitions are logged
    and auditable.
    """
    
    # Trigram → bit mapping (matches hexagram_vectors.py)
    TRIGRAM_BITS = {
        "Qian": 0b111, "Kun": 0b000, "Zhen": 0b001, "Xun": 0b110,
        "Kan": 0b010, "Li": 0b101, "Gen": 0b100, "Dui": 0b011,
    }
    
    # Trigram → cognitive function mapping
    TRIGRAM_FUNCTION = {
        "Qian": "draft",      # Heaven — creative generation
        "Zhen": "event",      # Thunder — stimulus detection
        "Li": "verify",       # Fire — verification/light
        "Xun": "route",       # Wind — gentle penetration/routing
        "Kan": "dream",       # Water — depth/dreaming
        "Gen": "heartbeat",   # Mountain — stillness/resting
        "Kun": "memory",      # Earth — receptacle/storage
        "Dui": "output",      # Lake — expression/output
    }
    
    def __init__(self):
        self._lower: str = "Kun"   # Default: receptive (idle)
        self._upper: str = "Gen"   # Default: stillness (heartbeat)
        self._history: deque = deque(maxlen=256)
        self._transition_count = 0
        self._lock = threading.RLock()
    
    @property
    def king_wen_number(self) -> int:
        """Current hexagram as King Wen number (1-64)."""
        lower_bits = self.TRIGRAM_BITS[self._lower]
        upper_bits = self.TRIGRAM_BITS[self._upper]
        binary = (upper_bits << 3) | lower_bits
        # Reverse lookup from King Wen table
        return _BINARY_TO_KING_WEN[binary]
    
    def transition(self, new_lower: str | None = None, new_upper: str | None = None,
                   reason: str = "") -> dict:
        """Transition to a new hexagram state.
        
        Args:
            new_lower: New lower trigram (inner state). None = keep current.
            new_upper: New upper trigram (outer action). None = keep current.
            reason: Human-readable reason for transition.
            
        Returns:
            Transition record dict with from/to hexagram, timestamp, reason.
        """
    
    def get_active_functions(self) -> set[str]:
        """Return the cognitive functions active in current state."""
    
    def get_audit_log(self, limit: int = 50) -> list[dict]:
        """Return recent state transitions for auditing."""
    
    def get_state_vector(self) -> list[float]:
        """Get HRR vector for current hexagram (from HexagramVectors)."""
```

**Key design**:
- Lower trigram = inner state (what the system is "feeling")
- Upper trigram = outer action (what the system is "doing")
- 64 possible states = 8 inner × 8 outer
- Transitions are logged with timestamp, reason, and hexagram change
- State vector available via HexagramVectors for HRR operations

**Testing**: Verify all 64 states reachable, transition logging correct, state vector matches HexagramVectors.

---

### Phase B: Wu Xing Phase Controller (Python)

**File**: `core/whitemagic/core/consciousness/wu_xing_controller.py`

Modulates which trigram threads are active based on the 5-element cycle. Prevents thermal throttling by limiting active cores per phase.

```python
class WuXingPhaseController:
    """5-phase thread modulation for thermal management.
    
    Cycles through Fire→Wood→Earth→Metal→Water phases,
    activating/deactivating trigram thread groups.
    """
    
    PHASE_DURATION = {
        Element.FIRE: 60.0,    # Active generation
        Element.WOOD: 30.0,    # Input processing
        Element.EARTH: 45.0,   # Persistence + health
        Element.METAL: 15.0,   # Refinement
        Element.WATER: 120.0,  # Background consolidation
    }
    
    PHASE_TRIGRAMS = {
        Element.FIRE: {"Qian", "Li"},        # Draft + Verify
        Element.WOOD: {"Zhen", "Xun"},       # Event + Route
        Element.EARTH: {"Kun", "Gen"},       # Memory + Heartbeat
        Element.METAL: {"Dui"},              # Output
        Element.WATER: {"Kan"},              # Dream
    }
    
    def __init__(self, hexagram_state: HexagramState):
        self._hexagram = hexagram_state
        self._current_phase: Element = Element.FIRE
        self._phase_start: float = time.time()
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._phase_count = 0
        self._on_phase_change: list[Callable] = []
    
    def start(self) -> None:
        """Start the phase controller in a background thread."""
    
    def stop(self) -> None:
        """Stop the phase controller."""
    
    def get_active_trigrams(self) -> set[str]:
        """Return currently active trigram names."""
    
    def is_trigram_active(self, trigram: str) -> bool:
        """Check if a specific trigram should be running."""
    
    def register_phase_callback(self, callback: Callable[[Element, Element], None]) -> None:
        """Register a callback called on phase transitions."""
    
    def get_status(self) -> dict:
        """Return current phase, elapsed time, transition count."""
```

**Key design**:
- Runs in a background daemon thread
- Phase transitions update HexagramState (lower trigram = phase element's Wood trigram, upper = phase element's Fire trigram)
- Callbacks allow trigram threads to pause/resume on phase changes
- Water phase (120s) gives dream cycle uninterrupted time on core 2
- Fire phase (60s) gives speculative decoding uninterrupted time on cores 0+1

**Testing**: Verify phase cycling, callback invocation, thermal profile (never more than 2 trigrams active).

---

### Phase C: Shared Memory Ring Buffer (Rust)

**File**: `core/whitemagic-rust/src/inference/ring_buffer.rs`

Lock-free single-producer single-consumer (SPSC) ring buffer using `/dev/shm` for inter-thread communication.

```rust
use std::sync::atomic::{AtomicU64, Ordering};
use std::ptr::NonNull;
use std::fs::OpenOptions;
use std::os::unix::io::AsRawFd;
use std::mem;

/// Header stored at the beginning of the shared memory region.
/// Layout: [header (64 bytes)] [data buffer (capacity bytes)]
#[repr(C, align(64))]
pub struct RingBufferHeader {
    pub capacity: u64,          // Total data capacity (excluding header)
    pub write_pos: AtomicU64,   // Producer write position (monotonic)
    pub read_pos: AtomicU64,    // Consumer read position (monotonic)
    pub element_size: u64,      // Size of each element (0 = variable)
    pub magic: u64,             // Magic number for validation
    pub _padding: [u8; 24],     // Pad to 64 bytes (cache line aligned)
}

pub struct RingBuffer {
    header: NonNull<RingBufferHeader>,
    data: NonNull<u8>,
    shm_path: String,
    is_owner: bool,  // true = producer (creates), false = consumer (opens)
}

impl RingBuffer {
    /// Create a new ring buffer in /dev/shm.
    pub fn create(name: &str, capacity: usize) -> Result<Self, RingBufferError>;
    
    /// Open an existing ring buffer.
    pub fn open(name: &str) -> Result<Self, RingBufferError>;
    
    /// Write data to the buffer. Returns false if full.
    pub fn try_write(&self, data: &[u8]) -> bool;
    
    /// Read data from the buffer. Returns None if empty.
    pub fn try_read(&self) -> Option<Vec<u8>>;
    
    /// Write a fixed-size element. Returns false if full.
    pub fn try_write_fixed(&self, data: &[u8]) -> bool;
    
    /// Read a fixed-size element. Returns None if empty.
    pub fn try_read_fixed(&self) -> Option<Vec<u8>>;
    
    /// Get current fill level (0.0 to 1.0).
    pub fn fill_level(&self) -> f32;
    
    /// Get number of bytes available to read.
    pub fn available(&self) -> u64;
    
    /// Close and optionally unlink the shared memory.
    pub fn close(self) -> Result<(), RingBufferError>;
}
```

**Key design**:
- Cache-line aligned header (64 bytes) prevents false sharing
- AtomicU64 for write_pos and read_pos (lock-free SPSC)
- Variable-length messages: 4-byte length prefix + data
- Fixed-length mode for token IDs (no prefix overhead)
- Magic number validation prevents corruption from stale SHM
- `/dev/shm/wm_trigram_<name>` naming convention
- Capacity: 1MB per ring buffer (sufficient for token batches)

**Testing**: Rust unit tests for create/open/write/read/close, concurrent producer-consumer test, variable-length message test.

---

### Phase D: Core-Pinned Trigram Thread Pool (Rust)

**File**: `core/whitemagic-rust/src/inference/trigram_pool.rs`

8 threads, each pinned to a specific core via `sched_setaffinity(2)`. Each thread runs a trigram-specific work loop.

```rust
use std::thread::{self, JoinHandle};
use std::os::raw::c_int;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Trigram {
    Qian,   // ☰ Heaven — Draft generation
    Zhen,   // ☳ Thunder — Event detection
    Li,     // ☲ Fire — Verify model
    Xun,    // ☴ Wind — Tool routing
    Kan,    // ☵ Water — Dream cycle
    Gen,    // ☶ Mountain — Stillness/heartbeat
    Kun,    // ☷ Earth — Memory store
    Dui,    // ☱ Lake — Output formatting
}

impl Trigram {
    fn core_id(&self) -> usize {
        match self {
            Trigram::Qian | Trigram::Zhen => 0,
            Trigram::Li | Trigram::Xun => 1,
            Trigram::Kan | Trigram::Gen => 2,
            Trigram::Kun | Trigram::Dui => 3,
        }
    }
}

pub struct TrigramPool {
    threads: Vec<(Trigram, JoinHandle<()>)>,
    ring_buffers: Vec<(Trigram, Trigram, RingBuffer)>,  // (from, to, buffer)
    running: Arc<AtomicBool>,
}

impl TrigramPool {
    pub fn new() -> Result<Self, TrigramPoolError>;
    
    /// Pin current thread to a specific core.
    fn pin_to_core(core_id: usize) -> Result<(), TrigramPoolError>;
    
    /// Spawn all 8 trigram threads.
    pub fn start<F>(&mut self, handlers: HashMap<Trigram, F>) -> Result<(), TrigramPoolError>
    where F: FnOnce(TrigramContext) + Send + 'static;
    
    /// Send a message from one trigram to another.
    pub fn send(&self, from: Trigram, to: Trigram, msg: &[u8]) -> bool;
    
    /// Receive a message for a specific trigram.
    pub fn recv(&self, for_trigram: Trigram) -> Option<Vec<u8>>;
    
    /// Stop all threads.
    pub fn stop(&self);
    
    /// Get status of all trigrams.
    pub fn status(&self) -> Vec<TrigramStatus>;
}

pub struct TrigramContext {
    pub trigram: Trigram,
    pub core_id: usize,
    pub pool: Arc<TrigramPool>,
    pub is_active: Arc<AtomicBool>,  // Controlled by Wu Xing phase
}
```

**Key design**:
- `sched_setaffinity` via libc FFI (no external crate dependency)
- Each thread gets a `TrigramContext` with ring buffer access
- `is_active` flag per trigram — Wu Xing controller toggles this
- Threads spin-wait when inactive (low power, fast resume)
- Ring buffer pairs: 8 directional channels (Qian→Li, Zhen→Xun, etc.)
- Graceful shutdown via `running` AtomicBool

**PyO3 bindings**: Expose `TrigramPool`, `Trigram`, `TrigramStatus` to Python.

**Testing**: Rust unit tests for core pinning (verify via `/proc/self/status` Cpus_allowed), ring buffer message passing, start/stop lifecycle.

---

### Phase E: Python Ring Buffer Bridge

**File**: `core/whitemagic/inference/ring_buffer_bridge.py`

Python-side bridge to the Rust ring buffers using `mmap` + `ctypes`. Allows Python code to send/receive messages to/from trigram threads.

```python
class RingBufferBridge:
    """Python bridge to Rust shared-memory ring buffers.
    
    Provides send/recv operations for inter-trigram communication
    from Python code (e.g., MCP dispatch → trigram threads).
    """
    
    def __init__(self, name: str, create: bool = False, capacity: int = 1024 * 1024):
        self._name = name
        self._shm_path = f"/dev/shm/wm_trigram_{name}"
        self._use_rust = self._check_rust()
        
        if self._use_rust:
            # Use Rust PyO3 bindings
            import whitemagic_rs
            if create:
                self._rb = whitemagic_rs.ring_buffer_create_py(name, capacity)
            else:
                self._rb = whitemagic_rs.ring_buffer_open_py(name)
        else:
            # Fallback: Python mmap implementation
            self._rb = self._create_python_rb(capacity) if create else self._open_python_rb()
    
    def send(self, data: bytes) -> bool:
        """Send data through the ring buffer. Returns False if full."""
    
    def recv(self) -> bytes | None:
        """Receive data. Returns None if empty."""
    
    def send_str(self, msg: str) -> bool:
        """Send a UTF-8 string message."""
    
    def recv_str(self) -> str | None:
        """Receive a UTF-8 string message."""
    
    def send_json(self, obj: dict) -> bool:
        """Send a JSON-serializable dict."""
    
    def recv_json(self) -> dict | None:
        """Receive a JSON dict."""
    
    def fill_level(self) -> float:
        """Return fill level 0.0-1.0."""
    
    def close(self) -> None:
        """Close and optionally unlink the shared memory."""
```

**Key design**:
- Prefers Rust PyO3 bindings when available
- Falls back to pure Python `mmap` + `struct` + `ctypes.atomic` 
- JSON message passing for structured data (tool calls, events)
- Raw bytes for high-performance token passing
- Context manager support (`with RingBufferBridge(...) as rb:`)

**Testing**: Send/recv round-trip, JSON serialization, fill level, concurrent access.

---

### Phase F: Integration & Wiring

#### F1: Speculative Wiring Update

**File**: `core/whitemagic/inference/speculative_wiring.py` (modified)

Add pipelined draft/verify mode that uses ring buffers for overlapped execution:

```python
def wire_pipelined_speculative(
    draft_model: str = "bitmamba",
    verify_model: str = "llamacpp",
    trigram_pool: TrigramPool | None = None,
) -> SpeculativeDecoder:
    """Wire speculative decoding with pipelined draft/verify on separate cores.
    
    When trigram_pool is available:
    - Draft generation runs on core 0 (☰ Qián)
    - Verify generation runs on core 1 (☲ Lí)
    - Draft tokens flow via ring buffer (Qian→Li channel)
    - Verify runs in parallel with next draft batch
    
    Without trigram_pool, falls back to sequential mode.
    """
```

#### F2: Concurrency Config Update

**File**: `core/whitemagic/config/concurrency.py` (modified)

```python
# 8-Trigram core pinning
TRIGRAM_CORE_PINNING = os.environ.get("WM_TRIGRAM_CORE_PINNING", "0") == "1"
TRIGRAM_RING_BUFFER_DIR = os.environ.get("WM_TRIGRAM_SHM_DIR", "/dev/shm")
TRIGRAM_RING_BUFFER_CAPACITY = int(os.environ.get("WM_TRIGRAM_RB_CAP", str(1024 * 1024)))

# When trigram pinning is active, reduce other worker pools
if TRIGRAM_CORE_PINNING:
    MAX_WORKERS = 1  # Only 1 worker for non-trigram tasks
    CPU_WORKERS = 1
```

#### F3: Rust Module Export Update

**File**: `core/whitemagic-rust/src/inference/mod.rs` (modified)

```rust
pub mod ring_buffer;
pub mod trigram_pool;

pub use ring_buffer::RingBuffer;
pub use trigram_pool::{Trigram, TrigramPool, TrigramStatus};
```

Add PyO3 bindings in `inference_pymodule.rs` for:
- `ring_buffer_create_py(name, capacity) -> RingBuffer`
- `ring_buffer_open_py(name) -> RingBuffer`
- `trigram_pool_create_py() -> TrigramPool`
- `trigram_pool_status_py() -> list[dict]`

---

## 5. File Manifest

### New Files
| File | Language | Lines (est.) | Phase |
|------|----------|-------------|-------|
| `core/whitemagic/core/consciousness/hexagram_state.py` | Python | ~250 | A |
| `core/whitemagic/core/consciousness/wu_xing_controller.py` | Python | ~200 | B |
| `core/whitemagic-rust/src/inference/ring_buffer.rs` | Rust | ~300 | C |
| `core/whitemagic-rust/src/inference/trigram_pool.rs` | Rust | ~350 | D |
| `core/whitemagic/inference/ring_buffer_bridge.py` | Python | ~200 | E |
| `core/tests/unit/test_hexagram_state.py` | Python | ~150 | A |
| `core/tests/unit/test_trigram_pool.py` | Python | ~120 | D-E |

### Modified Files
| File | Changes | Phase |
|------|---------|-------|
| `core/whitemagic/inference/speculative_wiring.py` | Add `wire_pipelined_speculative()` | F1 |
| `core/whitemagic/config/concurrency.py` | Add TRIGRAM_* config | F2 |
| `core/whitemagic-rust/src/inference/mod.rs` | Export new modules | F3 |
| `core/whitemagic-rust/src/inference_pymodule.rs` | PyO3 bindings | F3 |

---

## 6. Dependency Order

```
A (Hexagram State) ──────────────────────────────┐
                                                  ├──→ F (Integration)
B (Wu Xing Controller) ── depends on A ──────────┤
                                                  │
C (Ring Buffer Rust) ────────────────────────────┤
                                                  │
D (Trigram Pool Rust) ── depends on C ───────────┤
                                                  │
E (Ring Buffer Bridge) ── depends on C ──────────┘
```

A and C can be implemented in parallel (no dependencies).
B depends on A. D depends on C. E depends on C.
F depends on A+B+D+E.

**Recommended implementation order**: A → C → B → D → E → F

---

## 7. Testing Strategy

### Unit Tests

**test_hexagram_state.py**:
- All 64 states reachable via transitions
- King Wen number correct for each state
- Transition logging (timestamp, reason, from→to)
- State vector matches HexagramVectors singleton
- Active functions correct per trigram pair
- Audit log respects limit parameter
- Thread-safe concurrent transitions

**test_trigram_pool.py**:
- Ring buffer create/open/send/recv round-trip
- JSON message passing via bridge
- Fill level reporting
- Core pinning verification (mock /proc or skip on non-Linux)
- Trigram status reporting
- Start/stop lifecycle
- Phase controller cycling (Fire→Wood→Earth→Metal→Water)
- Phase callback invocation
- No more than 2 trigrams active per phase

### Integration Tests

- Pipelined speculative decoding: draft on core 0, verify on core 1, ring buffer IPC
- Dream cycle on core 2 during Water phase, no foreground impact
- Hexagram state transitions logged during phase changes
- End-to-end: MCP tool call → event detection → routing → draft → verify → output → memory

### Regression

```bash
source .venv/bin/activate
cd core && python -m pytest tests/ --ignore=tests/archive_v14 --ignore=tests/archive_v11 --ignore=tests/archive --ignore=tests/archive_polyglot --ignore=tests/legacy --ignore=tests/adhoc --ignore=tests/verify -q --timeout=30
```

---

## 8. Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Throughput improvement | 3x+ (54+ tok/s) | Benchmark with BitMamba draft + BitNet verify |
| Core pinning verified | All 8 threads pinned | `/proc/<pid>/status` Cpus_allowed |
| Ring buffer IPC latency | <100μs | Microbenchmark vs ~1ms JSON pipes |
| Dream cycle on background core | No foreground impact | Response time variance <5% during dream |
| Hexagram state transitions | Auditable log | `hexagram_state.get_audit_log()` |
| Wu Xing phase cycling | 5 phases complete in ~270s | Phase controller status |
| No more than 2 trigrams active per phase | Thermal <80°C | `sensors` output during Fire phase |
| All existing tests pass | 0 regressions | Full test suite |

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `sched_setaffinity` not available (non-Linux) | Low (target is Linux) | Medium | Runtime check, fallback to unpinned threads |
| `/dev/shm` not mounted | Very Low | High | Check at startup, fallback to `tempfile` |
| Ring buffer corruption on crash | Medium | Medium | Magic number validation, cleanup on startup |
| Thermal throttling despite Wu Xing | Low | Medium | Monitor `sensors`, extend Water phase if throttled |
| PyO3 binding complexity for ring buffer | Medium | Low | Python mmap fallback in bridge |
| Dream cycle contention with heartbeat | Low | Low | Both on core 2, but different phases (Water vs Earth) |
| Ring buffer capacity insufficient | Low | Medium | 1MB default, configurable via env var |

---

## 10. Connection to Existing Systems

| System | Integration Point |
|--------|------------------|
| `hexagram_vectors.py` | HexagramState uses it for state vectors |
| `wu_xing.py` | WuXingPhaseController extends with thread modulation |
| `speculative_decoder.py` | Pipelined mode via ring buffers |
| `bitmamba_autonomic.py` | Draft handler runs on ☰ Qián thread |
| `consciousness_loop.py` | Heartbeat on ☶ Gèn, citta tick on phase change |
| `dream_cycle.py` | Dream cycle on ☵ Kǎn during Water phase |
| `gan_ying.py` | Event detection on ☳ Zhèn, ring buffers = Gan Ying physical layer |
| `concurrency.py` | TRIGRAM_CORE_PINNING reduces other workers when active |

---

## 11. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WM_TRIGRAM_CORE_PINNING` | 0 | Enable 8-trigram core-pinned thread pool |
| `WM_TRIGRAM_SHM_DIR` | /dev/shm | Directory for shared memory ring buffers |
| `WM_TRIGRAM_RB_CAP` | 1048576 | Ring buffer capacity in bytes (1MB) |
| `WM_WUXING_PHASE_FIRE` | 60 | Fire phase duration (seconds) |
| `WM_WUXING_PHASE_WOOD` | 30 | Wood phase duration (seconds) |
| `WM_WUXING_PHASE_EARTH` | 45 | Earth phase duration (seconds) |
| `WM_WUXING_PHASE_METAL` | 15 | Metal phase duration (seconds) |
| `WM_WUXING_PHASE_WATER` | 120 | Water phase duration (seconds) |
