//! wm-gen3-core::transport — Physical OS Socket Sovereignty & Framing Discipline
//!
//! # Foundational Laws of Physical Grounding (Milestone 8A)
//!
//! 1. **The Physical Transport Invariant:**
//!    The operating system may delay, duplicate, fragment, reorder, disconnect,
//!    or destroy transport—but it must never change Gan Ying semantics.
//!
//! 2. **The Durability Ordering Invariant (Crash-Consistency Cut-Point Law):**
//!    A remotely induced local commit may never become durable before the
//!    replay/nullifier state that makes the triggering envelope non-replayable.
//!    `Authenticate -> Reserve Nullifier -> Durably Persist Replay State -> Canonical Commit`.
//!
//! 3. **The Allocation Boundedness Invariant (Pre-Allocation Guard):**
//!    Reject oversized length prefixes $L > \text{MAX\_MESSAGE\_SIZE}$ before allocating
//!    buffer memory. Allocation increase must remain $< 64\text{ KB}$ even if $L = 4\text{ GiB}$.
//!
//! 4. **The Deadline Hierarchy Invariant (Anti-Slowloris Law):**
//!    Progress cannot reset an adversarially infinite deadline. Sockets trickling bytes
//!    are closed cleanly once `FRAME_ASSEMBLY_TIMEOUT` triggers.
//!
//! 5. **The Congestion Invariant (Congestion != Authority):**
//!    Bulk proposal traffic must never starve protected safety, health, or identity traffic.
//!    Inbound queues are partitioned into bounded priority lanes.
//!
//! 6. **The Identity Decoupling Invariant (Socket != Peer):**
//!    A `TcpStream`, IP address, port number, or OS file descriptor has zero standing.
//!    Sockets are ephemeral transport carriers; cryptographic signatures on envelopes
//!    establish peer identity.

use std::collections::{HashMap, VecDeque};
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::net::{SocketAddr, TcpListener};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::ganying::{BoundaryError, ReplayLedger, SignedEnvelope, SovereignBoundary};

pub const MAX_MESSAGE_SIZE: u32 = 1024 * 1024; // 1 MB
pub const MIN_MESSAGE_SIZE: u32 = 2; // e.g. "{}"

pub const DEFAULT_CONNECT_TIMEOUT: Duration = Duration::from_secs(5);
pub const DEFAULT_FRAME_ASSEMBLY_TIMEOUT: Duration = Duration::from_secs(10);
pub const DEFAULT_RPC_PROCESSING_TIMEOUT: Duration = Duration::from_secs(15);
pub const DEFAULT_IDLE_CONNECTION_TIMEOUT: Duration = Duration::from_secs(30);

/// Physical transport layer errors.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TransportError {
    /// Frame length prefix exceeds maximum permitted size (rejected before allocation).
    FrameTooLarge(u32),
    /// Frame length prefix is smaller than minimum valid envelope size.
    FrameTooSmall(u32),
    /// Stream ended prematurely before declared length was received.
    UnexpectedEof { expected: u32, received: u32 },
    /// Frame assembly exceeded wall-clock deadline (Slowloris mitigation).
    AssemblyTimeout { elapsed_ms: u64, limit_ms: u64 },
    /// Connection reset or broken pipe by peer or operating system.
    ConnectionReset(String),
    /// Socket dial / handshake timed out.
    ConnectTimeout,
    /// Serialization / deserialization failed.
    CodecError(String),
    /// Priority lane overflow / queue full.
    QueueSaturated(String),
    /// IO failure.
    IoError(String),
}

impl From<io::Error> for TransportError {
    fn from(err: io::Error) -> Self {
        match err.kind() {
            io::ErrorKind::UnexpectedEof => TransportError::UnexpectedEof {
                expected: 0,
                received: 0,
            },
            io::ErrorKind::ConnectionReset | io::ErrorKind::BrokenPipe => {
                TransportError::ConnectionReset(err.to_string())
            }
            io::ErrorKind::TimedOut => TransportError::ConnectTimeout,
            _ => TransportError::IoError(err.to_string()),
        }
    }
}

impl fmt::Display for TransportError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::FrameTooLarge(len) => write!(f, "Frame too large: {} bytes", len),
            Self::FrameTooSmall(len) => write!(f, "Frame too small: {} bytes", len),
            Self::UnexpectedEof { expected, received } => {
                write!(
                    f,
                    "Unexpected EOF: expected {}, received {}",
                    expected, received
                )
            }
            Self::AssemblyTimeout {
                elapsed_ms,
                limit_ms,
            } => {
                write!(
                    f,
                    "Assembly timeout: elapsed {} ms > limit {} ms",
                    elapsed_ms, limit_ms
                )
            }
            Self::ConnectionReset(s) => write!(f, "Connection reset: {}", s),
            Self::ConnectTimeout => write!(f, "Connect timeout"),
            Self::CodecError(s) => write!(f, "Codec error: {}", s),
            Self::QueueSaturated(s) => write!(f, "Queue saturated: {}", s),
            Self::IoError(s) => write!(f, "Transport I/O error: {}", s),
        }
    }
}

impl std::error::Error for TransportError {}

// ============================================================================
// 1. Physical Frame Codec (Length-Prefixed Framing with Pre-Allocation Guards)
// ============================================================================

pub struct PhysicalFrameCodec;

impl PhysicalFrameCodec {
    /// Write a frame with a 4-byte big-endian length prefix.
    pub fn write_frame<W: Write>(writer: &mut W, data: &[u8]) -> Result<(), TransportError> {
        let len = data.len() as u32;
        if len > MAX_MESSAGE_SIZE {
            return Err(TransportError::FrameTooLarge(len));
        }
        if len < MIN_MESSAGE_SIZE {
            return Err(TransportError::FrameTooSmall(len));
        }
        writer.write_all(&len.to_be_bytes())?;
        writer.write_all(data)?;
        writer.flush()?;
        Ok(())
    }

    /// Read a frame with strict pre-allocation validation and assembly timeout.
    ///
    /// Invariant: Memory for payload is NEVER allocated if declared length > MAX_MESSAGE_SIZE.
    pub fn read_frame<R: Read>(
        reader: &mut R,
        start_time: Instant,
        assembly_timeout: Duration,
    ) -> Result<Vec<u8>, TransportError> {
        let mut len_buf = [0u8; 4];
        let mut prefix_read = 0usize;
        while prefix_read < len_buf.len() {
            let n = reader.read(&mut len_buf[prefix_read..])?;
            if n == 0 {
                return Err(TransportError::UnexpectedEof {
                    expected: len_buf.len() as u32,
                    received: prefix_read as u32,
                });
            }
            prefix_read += n;
        }
        let len = u32::from_be_bytes(len_buf);

        // Pre-allocation bounds check (Zero payload memory allocated if invalid)
        if len > MAX_MESSAGE_SIZE {
            return Err(TransportError::FrameTooLarge(len));
        }
        if len < MIN_MESSAGE_SIZE {
            return Err(TransportError::FrameTooSmall(len));
        }

        // Allocate only verified size <= 1 MB
        let mut buffer = vec![0u8; len as usize];
        let mut bytes_read = 0;

        while bytes_read < len as usize {
            if start_time.elapsed() > assembly_timeout {
                return Err(TransportError::AssemblyTimeout {
                    elapsed_ms: start_time.elapsed().as_millis() as u64,
                    limit_ms: assembly_timeout.as_millis() as u64,
                });
            }

            let n = reader.read(&mut buffer[bytes_read..])?;
            if n == 0 {
                return Err(TransportError::UnexpectedEof {
                    expected: len,
                    received: bytes_read as u32,
                });
            }
            bytes_read += n;
        }

        Ok(buffer)
    }
}

// ============================================================================
// 2. Priority Lane Queue (Congestion != Authority)
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum PriorityLane {
    /// Lane 0: Heartbeat, liveness, quarantine emergency signals (non-droppable, fair round-robin).
    SafetyHealth = 0,
    /// Lane 1: Key epoch rotation proofs, RootIdentityKey announcements.
    ControlIdentity = 1,
    /// Lane 2: Ordinary observations, claims ledger items, evidence testimony.
    OrdinaryStimulus = 2,
    /// Lane 3: Heavy compute task proposals, shadow clone mutations.
    SurplusCompute = 3,
}

pub const MAX_LANE_0_TOTAL: usize = 64;
pub const MAX_LANE_0_PER_PEER: usize = 4;
pub const MAX_LANE_1_TOTAL: usize = 64;
pub const MAX_LANE_2_TOTAL: usize = 256;
pub const MAX_LANE_3_TOTAL: usize = 128;

pub struct SocketPriorityQueue {
    /// Active sender ring in Lane 0 for fair round-robin scheduling across peers.
    pub lane_0_senders: VecDeque<String>,
    /// Per-peer queues in Lane 0 enforcing per-peer quotas (max 4 per peer).
    pub lane_0_by_peer: HashMap<String, VecDeque<SignedEnvelope>>,
    pub lane_0_total: usize,

    pub lane_1: VecDeque<SignedEnvelope>, // Capacity 64
    pub lane_2: VecDeque<SignedEnvelope>, // Capacity 256
    pub lane_3: VecDeque<SignedEnvelope>, // Capacity 128
    pub dropped_lane_2_count: u64,
    pub dropped_lane_3_count: u64,
}

impl SocketPriorityQueue {
    pub fn new() -> Self {
        Self {
            lane_0_senders: VecDeque::new(),
            lane_0_by_peer: HashMap::new(),
            lane_0_total: 0,
            lane_1: VecDeque::with_capacity(MAX_LANE_1_TOTAL),
            lane_2: VecDeque::with_capacity(MAX_LANE_2_TOTAL),
            lane_3: VecDeque::with_capacity(MAX_LANE_3_TOTAL),
            dropped_lane_2_count: 0,
            dropped_lane_3_count: 0,
        }
    }

    /// Enqueue envelope into its designated priority lane with fail-closed bounds.
    /// In Lane 0 (SafetyHealth), enforces Priority != Privilege via per-peer quota (max 4).
    pub fn enqueue(
        &mut self,
        lane: PriorityLane,
        envelope: SignedEnvelope,
    ) -> Result<(), TransportError> {
        match lane {
            PriorityLane::SafetyHealth => {
                let peer = envelope.sender_id.clone();
                let peer_count = self.lane_0_by_peer.get(&peer).map_or(0, |q| q.len());
                if peer_count >= MAX_LANE_0_PER_PEER {
                    return Err(TransportError::QueueSaturated(format!(
                        "Lane 0 per-peer quota ({}) exceeded for peer '{}'",
                        MAX_LANE_0_PER_PEER, peer
                    )));
                }
                if self.lane_0_total >= MAX_LANE_0_TOTAL {
                    return Err(TransportError::QueueSaturated(
                        "Lane 0 total capacity (64) reached".into(),
                    ));
                }
                let peer_queue = self
                    .lane_0_by_peer
                    .entry(peer.clone())
                    .or_insert_with(VecDeque::new);
                if peer_queue.is_empty() {
                    self.lane_0_senders.push_back(peer);
                }
                peer_queue.push_back(envelope);
                self.lane_0_total += 1;
                Ok(())
            }
            PriorityLane::ControlIdentity => {
                if self.lane_1.len() >= MAX_LANE_1_TOTAL {
                    self.lane_1.pop_front();
                }
                self.lane_1.push_back(envelope);
                Ok(())
            }
            PriorityLane::OrdinaryStimulus => {
                if self.lane_2.len() >= MAX_LANE_2_TOTAL {
                    self.dropped_lane_2_count += 1;
                    return Err(TransportError::QueueSaturated(
                        "Lane 2 (Stimulus) Full".into(),
                    ));
                }
                self.lane_2.push_back(envelope);
                Ok(())
            }
            PriorityLane::SurplusCompute => {
                if self.lane_3.len() >= MAX_LANE_3_TOTAL {
                    self.dropped_lane_3_count += 1;
                    return Err(TransportError::QueueSaturated(
                        "Lane 3 (Compute) Full".into(),
                    ));
                }
                self.lane_3.push_back(envelope);
                Ok(())
            }
        }
    }

    /// Dequeue strictly in priority order: Lane 0 -> Lane 1 -> Lane 2 -> Lane 3.
    /// Within Lane 0, serves active senders round-robin to eliminate starvation.
    pub fn dequeue(&mut self) -> Option<(PriorityLane, SignedEnvelope)> {
        // Priority 0: SafetyHealth (Fair Round-Robin)
        if !self.lane_0_senders.is_empty() {
            if let Some(sender) = self.lane_0_senders.pop_front() {
                if let Some(peer_queue) = self.lane_0_by_peer.get_mut(&sender) {
                    if let Some(env) = peer_queue.pop_front() {
                        self.lane_0_total = self.lane_0_total.saturating_sub(1);
                        if !peer_queue.is_empty() {
                            self.lane_0_senders.push_back(sender);
                        } else {
                            self.lane_0_by_peer.remove(&sender);
                        }
                        return Some((PriorityLane::SafetyHealth, env));
                    }
                }
            }
        }
        // Priority 1: ControlIdentity
        if let Some(env) = self.lane_1.pop_front() {
            return Some((PriorityLane::ControlIdentity, env));
        }
        // Priority 2: OrdinaryStimulus
        if let Some(env) = self.lane_2.pop_front() {
            return Some((PriorityLane::OrdinaryStimulus, env));
        }
        // Priority 3: SurplusCompute
        if let Some(env) = self.lane_3.pop_front() {
            return Some((PriorityLane::SurplusCompute, env));
        }
        None
    }

    pub fn total_enqueued(&self) -> usize {
        self.lane_0_total + self.lane_1.len() + self.lane_2.len() + self.lane_3.len()
    }

    pub fn lane_0_len(&self) -> usize {
        self.lane_0_total
    }

    pub fn lane_0_peer_count(&self, peer: &str) -> usize {
        self.lane_0_by_peer.get(peer).map_or(0, |q| q.len())
    }
}

// ============================================================================
// 3. Durable Replay Storage & Write-Ahead Intent Logging (WAIL)
// ============================================================================

/// Two-phase intent lifecycle for exactly-once execution across process crash cut-points.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum IntentState {
    Prepared { delta: u64 },
    Committed { result_state: u64 },
}

impl Default for IntentState {
    fn default() -> Self {
        IntentState::Committed { result_state: 0 }
    }
}

/// On-disk record for replay state persistence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersistedReplayEntry {
    pub peer_id: String,
    pub epoch: u64,
    #[serde(default)]
    pub seq_id: u64,
    pub high_water_seq: u64,
    pub sliding_bitmap: u64,
    pub recorded_at_ns: u64,
    #[serde(default)]
    pub state: IntentState,
}

/// A durable crash-consistent replay store enforcing the Durability Ordering Invariant
/// and two-phase Write-Ahead Intent Logging (WAIL) with deterministic roll-forward on recovery.
pub struct DurableReplayStore {
    log_path: PathBuf,
    in_memory: ReplayLedger,
    canonical_state: u64,
    pub roll_forwards_executed: u64,
    pub committed_receipts: HashMap<(String, u64, u64), u64>,
}

impl DurableReplayStore {
    pub fn open(log_path: &Path) -> Result<Self, io::Error> {
        let mut store = Self {
            log_path: log_path.to_path_buf(),
            in_memory: ReplayLedger::new(0),
            canonical_state: 0,
            roll_forwards_executed: 0,
            committed_receipts: HashMap::new(),
        };

        if log_path.exists() {
            store.recover()?;
        }

        Ok(store)
    }

    /// Recover replay high-water marks, sliding bitmaps, and roll forward uncommitted prepared intents.
    pub fn recover(&mut self) -> Result<(), io::Error> {
        let mut file = File::open(&self.log_path)?;
        let mut contents = String::new();
        file.read_to_string(&mut contents)?;

        let mut pending_intents: HashMap<(String, u64, u64), (u64, PersistedReplayEntry)> =
            HashMap::new();

        for line in contents.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            if let Ok(entry) = serde_json::from_str::<PersistedReplayEntry>(line) {
                self.in_memory.high_water_seq =
                    entry.high_water_seq.max(self.in_memory.high_water_seq);
                self.in_memory.sliding_bitmap |= entry.sliding_bitmap;
                self.in_memory.current_epoch = entry.epoch.max(self.in_memory.current_epoch);

                match entry.state {
                    IntentState::Prepared { delta } => {
                        pending_intents.insert(
                            (entry.peer_id.clone(), entry.epoch, entry.seq_id),
                            (delta, entry.clone()),
                        );
                    }
                    IntentState::Committed { result_state } => {
                        pending_intents.remove(&(entry.peer_id.clone(), entry.epoch, entry.seq_id));
                        self.committed_receipts.insert(
                            (entry.peer_id.clone(), entry.epoch, entry.seq_id),
                            result_state,
                        );
                        if result_state > self.canonical_state {
                            self.canonical_state = result_state;
                        }
                    }
                }
            }
        }

        // Deterministic Roll-Forward for Cut-Point B (Prepared but not Committed before crash)
        if !pending_intents.is_empty() {
            let mut append_file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(&self.log_path)?;

            let mut sorted_intents: Vec<_> = pending_intents.into_iter().collect();
            sorted_intents.sort_by_key(|((_, epoch, seq_id), _)| (*epoch, *seq_id));

            for ((peer_id, epoch, seq_id), (delta, entry)) in sorted_intents {
                self.canonical_state += delta;
                let result_state = self.canonical_state;
                self.committed_receipts
                    .insert((peer_id.clone(), epoch, seq_id), result_state);
                self.roll_forwards_executed += 1;

                let commit_entry = PersistedReplayEntry {
                    peer_id,
                    epoch,
                    seq_id,
                    high_water_seq: entry.high_water_seq,
                    sliding_bitmap: entry.sliding_bitmap,
                    recorded_at_ns: entry.recorded_at_ns + 1,
                    state: IntentState::Committed { result_state },
                };
                if let Ok(mut l) = serde_json::to_string(&commit_entry) {
                    l.push('\n');
                    let _ = append_file.write_all(l.as_bytes());
                }
            }
            let _ = append_file.sync_all();
        }

        Ok(())
    }

    /// Enforce the Durability Ordering Invariant:
    /// Replay sequence state MUST be durably flushed to disk as Prepared before canonical commit is permitted.
    pub fn reserve_and_persist(
        &mut self,
        peer_id: &str,
        epoch: u64,
        seq_id: u64,
        delta: u64,
        now_ns: u64,
    ) -> Result<(), BoundaryError> {
        // 1. Verify and update in-memory window
        self.in_memory.mark_consumed(epoch, seq_id)?;

        // 2. Durably append Prepared intent to disk and sync
        let entry = PersistedReplayEntry {
            peer_id: peer_id.to_string(),
            epoch,
            seq_id,
            high_water_seq: self.in_memory.high_water_seq,
            sliding_bitmap: self.in_memory.sliding_bitmap,
            recorded_at_ns: now_ns,
            state: IntentState::Prepared { delta },
        };

        let mut line =
            serde_json::to_string(&entry).map_err(|e| BoundaryError::SchemaViolation {
                peer_id: peer_id.to_string(),
                reason: e.to_string(),
            })?;
        line.push('\n');

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)
            .map_err(|e| BoundaryError::SchemaViolation {
                peer_id: peer_id.to_string(),
                reason: e.to_string(),
            })?;

        file.write_all(line.as_bytes())
            .map_err(|e| BoundaryError::SchemaViolation {
                peer_id: peer_id.to_string(),
                reason: e.to_string(),
            })?;

        file.sync_all()
            .map_err(|e| BoundaryError::SchemaViolation {
                peer_id: peer_id.to_string(),
                reason: e.to_string(),
            })?;

        Ok(())
    }

    /// Perform canonical commit after replay state has been durably secured.
    /// Returns the new canonical state, durably writing Committed intent.
    pub fn commit_canonical(
        &mut self,
        peer_id: &str,
        epoch: u64,
        seq_id: u64,
        delta: u64,
        now_ns: u64,
    ) -> Result<u64, io::Error> {
        // Idempotency check: if already committed or rolled forward, return cached result
        if let Some(&cached_res) =
            self.committed_receipts
                .get(&(peer_id.to_string(), epoch, seq_id))
        {
            return Ok(cached_res);
        }

        self.canonical_state += delta;
        let res = self.canonical_state;
        self.committed_receipts
            .insert((peer_id.to_string(), epoch, seq_id), res);

        let entry = PersistedReplayEntry {
            peer_id: peer_id.to_string(),
            epoch,
            seq_id,
            high_water_seq: self.in_memory.high_water_seq,
            sliding_bitmap: self.in_memory.sliding_bitmap,
            recorded_at_ns: now_ns,
            state: IntentState::Committed { result_state: res },
        };

        let mut line = serde_json::to_string(&entry)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        line.push('\n');

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)?;

        file.write_all(line.as_bytes())?;
        file.sync_all()?;

        Ok(res)
    }

    pub fn committed_receipt_for(&self, peer_id: &str, epoch: u64, seq_id: u64) -> Option<u64> {
        self.committed_receipts
            .get(&(peer_id.to_string(), epoch, seq_id))
            .copied()
    }

    pub fn canonical_state(&self) -> u64 {
        self.canonical_state
    }

    pub fn high_water_seq(&self) -> u64 {
        self.in_memory.high_water_seq
    }
}

// ============================================================================
// 4. Physical Loopback Server & Client (Socket != Peer)
// ============================================================================

pub struct PhysicalSanghaNode {
    pub node_id: String,
    pub boundary: Arc<Mutex<SovereignBoundary>>,
    pub queue: Arc<Mutex<SocketPriorityQueue>>,
    listener: Option<TcpListener>,
    pub bound_addr: Option<SocketAddr>,
    is_running: Arc<Mutex<bool>>,
}

impl PhysicalSanghaNode {
    pub fn new(node_id: &str, boundary: SovereignBoundary) -> Self {
        Self {
            node_id: node_id.to_string(),
            boundary: Arc::new(Mutex::new(boundary)),
            queue: Arc::new(Mutex::new(SocketPriorityQueue::new())),
            listener: None,
            bound_addr: None,
            is_running: Arc::new(Mutex::new(false)),
        }
    }

    /// Bind to loopback port and start accept worker thread.
    pub fn start_listener(&mut self, port: u16) -> io::Result<SocketAddr> {
        let listener = TcpListener::bind(format!("127.0.0.1:{}", port))?;
        let addr = listener.local_addr()?;
        listener.set_nonblocking(true)?;

        self.bound_addr = Some(addr);
        self.listener = Some(listener);
        *self.is_running.lock().unwrap() = true;

        let running_flag = Arc::clone(&self.is_running);
        let queue_ref = Arc::clone(&self.queue);
        let boundary_ref = Arc::clone(&self.boundary);
        let listener_clone = self.listener.as_ref().unwrap().try_clone()?;

        std::thread::spawn(move || {
            while *running_flag.lock().unwrap() {
                match listener_clone.accept() {
                    Ok((mut stream, _client_addr)) => {
                        let q = Arc::clone(&queue_ref);
                        let b = Arc::clone(&boundary_ref);

                        std::thread::spawn(move || {
                            let _ = stream.set_nonblocking(false);
                            let _ = stream.set_read_timeout(Some(DEFAULT_FRAME_ASSEMBLY_TIMEOUT));
                            let start = Instant::now();

                            match PhysicalFrameCodec::read_frame(
                                &mut stream,
                                start,
                                DEFAULT_FRAME_ASSEMBLY_TIMEOUT,
                            ) {
                                Ok(bytes) => {
                                    let mut b_guard = b.lock().unwrap();
                                    match b_guard.ingress_raw_bytes(&bytes) {
                                        Ok(envelope) => {
                                            match b_guard.authenticate_identity(&envelope) {
                                                Ok(_active_key) => {
                                                    let lane = match envelope.action.as_str() {
                                                        "heartbeat" | "emergency_containment" => {
                                                            PriorityLane::SafetyHealth
                                                        }
                                                        "rotate_key" | "announce_identity" => {
                                                            PriorityLane::ControlIdentity
                                                        }
                                                        "submit_compute_task" => {
                                                            PriorityLane::SurplusCompute
                                                        }
                                                        _ => PriorityLane::OrdinaryStimulus,
                                                    };
                                                    let mut q_guard = q.lock().unwrap();
                                                    let _ = q_guard.enqueue(lane, envelope);
                                                    let _ = stream.write_all(b"OK\n");
                                                }
                                                Err(e) => {
                                                    let _ = stream.write_all(
                                                        format!("REJECTED: {}\n", e).as_bytes(),
                                                    );
                                                }
                                            }
                                        }
                                        Err(e) => {
                                            let _ = stream
                                                .write_all(format!("NOISE: {}\n", e).as_bytes());
                                        }
                                    }
                                }
                                Err(_e) => {
                                    // Anti-ghost socket eviction: stream dropped on any framing/assembly error
                                }
                            }
                        });
                    }
                    Err(ref e) if e.kind() == io::ErrorKind::WouldBlock => {
                        std::thread::sleep(Duration::from_millis(5));
                    }
                    Err(_) => {
                        break;
                    }
                }
            }
        });

        Ok(addr)
    }

    pub fn stop(&mut self) {
        *self.is_running.lock().unwrap() = false;
        self.listener = None;
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Peb14aReport {
    pub choppy_stream_reassembled: bool,
    pub guillotine_clean_teardown: bool,
    pub cold_reboot_replay_rejected: bool,
    pub physical_noise_zero_false_quarantine: bool,
    pub compute_freeloader_throttled: bool,
    pub oversized_framing_bounded_memory: bool,
    pub slowloris_assembly_timed_out: bool,
    pub crash_consistency_zero_double_commits: bool,
    pub priority_lane_safety_unstarved: bool,
    pub summary: String,
}

/// Run the comprehensive 9-scenario PEB-14A benchmark battery.
pub fn run_peb14a_physical_socket_benchmark() -> Peb14aReport {
    use crate::ganying::ImmuneStatus;
    use ed25519_dalek::{Signer, SigningKey};

    // Helper for signing
    let make_env = |signing_key: &SigningKey,
                    sender: &str,
                    recipient: &str,
                    epoch: u64,
                    seq_id: u64,
                    action: &str,
                    payload_data: &[u8]|
     -> SignedEnvelope {
        let mut env = SignedEnvelope {
            sender_id: sender.to_string(),
            recipient_id: recipient.to_string(),
            epoch,
            seq_id,
            timestamp_ns: 1000,
            action: action.to_string(),
            payload: payload_data.to_vec(),
            signature: Vec::new(),
        };
        let digest = env.digest();
        let sig = signing_key.sign(&digest);
        env.signature = sig.to_bytes().to_vec();
        env
    };

    // 1. Choppy Stream Fragmentation
    let mut raw_data = Vec::new();
    for i in 0..1024 {
        raw_data.push((i % 255) as u8);
    }
    let mut wire_bytes = Vec::new();
    PhysicalFrameCodec::write_frame(&mut wire_bytes, &raw_data).unwrap();

    struct ChoppyReader {
        data: Vec<u8>,
        cursor: usize,
        chunk_size: usize,
    }
    impl Read for ChoppyReader {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            if self.cursor >= self.data.len() {
                return Ok(0);
            }
            let avail = self.data.len() - self.cursor;
            let to_read = buf.len().min(avail).min(self.chunk_size);
            buf[..to_read].copy_from_slice(&self.data[self.cursor..self.cursor + to_read]);
            self.cursor += to_read;
            Ok(to_read)
        }
    }
    let mut c_reader = ChoppyReader {
        data: wire_bytes,
        cursor: 0,
        chunk_size: 19,
    };
    let assembled =
        PhysicalFrameCodec::read_frame(&mut c_reader, Instant::now(), Duration::from_secs(5))
            .unwrap();
    let s1_ok = assembled == raw_data;

    // 2. Guillotine Mid-Stream RST
    struct BrokenReader {
        bytes_sent: usize,
    }
    impl Read for BrokenReader {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            if self.bytes_sent == 0 {
                let len = 10_000u32.to_be_bytes();
                buf[..4].copy_from_slice(&len);
                self.bytes_sent += 4;
                Ok(4)
            } else {
                Err(io::Error::new(io::ErrorKind::ConnectionReset, "TCP RST"))
            }
        }
    }
    let mut b_reader = BrokenReader { bytes_sent: 0 };
    let s2_ok = matches!(
        PhysicalFrameCodec::read_frame(&mut b_reader, Instant::now(), Duration::from_secs(5)),
        Err(TransportError::ConnectionReset(_))
    );

    // 3. Cold Reboot Replay Defense
    let temp_dir = std::env::temp_dir().join(format!(
        "wm_peb14a_replay_{}",
        Instant::now().elapsed().as_nanos()
    ));
    let _ = std::fs::create_dir_all(&temp_dir);
    let log_file = temp_dir.join("replay.log");

    {
        let mut store = DurableReplayStore::open(&log_file).unwrap();
        for i in 1..=50 {
            store
                .reserve_and_persist("Alice", 0, i, 1, 1000 + i)
                .unwrap();
            store.commit_canonical("Alice", 0, i, 1, 2000 + i).unwrap();
        }
    }
    let s3_ok = {
        let mut rebooted = DurableReplayStore::open(&log_file).unwrap();
        let mut all_replayed_rejected = true;
        for i in 1..=50 {
            if rebooted
                .reserve_and_persist("Alice", 0, i, 1, 5000 + i)
                .is_ok()
            {
                all_replayed_rejected = false;
                break;
            }
        }
        all_replayed_rejected && rebooted.high_water_seq() == 50 && rebooted.canonical_state() == 50
    };
    let _ = std::fs::remove_dir_all(&temp_dir);

    // 4. Physical Noise Zero False Quarantine
    let alice_seed = [42u8; 32];
    let mallory_seed = [99u8; 32];
    let alice_signing = SigningKey::from_bytes(&alice_seed);
    let mallory_signing = SigningKey::from_bytes(&mallory_seed);

    let mut boundary = SovereignBoundary::new("Bob");
    boundary
        .register_peer_tofu("Alice", alice_signing.verifying_key().to_bytes())
        .unwrap();
    let spoofed = make_env(&mallory_signing, "Alice", "Bob", 0, 1, "test", b"payload");
    let auth_res = boundary.authenticate_identity(&spoofed);
    let s4_ok = matches!(auth_res, Err(BoundaryError::Noise(_)))
        && *boundary.immune_records.get("Alice").unwrap() == ImmuneStatus::Healthy;

    // 5. Compute Freeloader Throttling
    let mut queue = SocketPriorityQueue::new();
    for i in 0..128 {
        let env = make_env(
            &alice_signing,
            "Freeloader",
            "Bob",
            0,
            i + 1,
            "submit_compute_task",
            b"work",
        );
        queue.enqueue(PriorityLane::SurplusCompute, env).unwrap();
    }
    let overflow_env = make_env(
        &alice_signing,
        "Freeloader",
        "Bob",
        0,
        129,
        "submit_compute_task",
        b"work",
    );
    let overflow_rejected = matches!(
        queue.enqueue(PriorityLane::SurplusCompute, overflow_env),
        Err(TransportError::QueueSaturated(_))
    );
    let heartbeat = make_env(
        &alice_signing,
        "Freeloader",
        "Bob",
        0,
        130,
        "heartbeat",
        b"alive",
    );
    let heartbeat_accepted = queue.enqueue(PriorityLane::SafetyHealth, heartbeat).is_ok();
    let s5_ok = overflow_rejected && heartbeat_accepted;

    // 6. Oversized Framing Battery (Pre-allocation 4 GiB rejection)
    struct HugeLenReader;
    impl Read for HugeLenReader {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            buf[..4].copy_from_slice(&0xFFFFFFFFu32.to_be_bytes());
            Ok(4)
        }
    }
    let mut h_reader = HugeLenReader;
    let s6_ok = matches!(
        PhysicalFrameCodec::read_frame(&mut h_reader, Instant::now(), Duration::from_secs(5)),
        Err(TransportError::FrameTooLarge(0xFFFFFFFF))
    );

    // 7. Slowloris Frame Assembly Deadline
    struct SlowlorisReader {
        declared: bool,
    }
    impl Read for SlowlorisReader {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            if !self.declared {
                buf[..4].copy_from_slice(&100u32.to_be_bytes());
                self.declared = true;
                Ok(4)
            } else {
                buf[0] = b'{';
                Ok(1)
            }
        }
    }
    let mut s_reader = SlowlorisReader { declared: false };
    let s7_ok = matches!(
        PhysicalFrameCodec::read_frame(
            &mut s_reader,
            Instant::now() - Duration::from_millis(60),
            Duration::from_millis(50)
        ),
        Err(TransportError::AssemblyTimeout { .. })
    );

    // 8. Crash-Consistency Cut-Point Matrix (Two-Phase WAIL Roll-Forward)
    let temp_cut = std::env::temp_dir().join(format!(
        "wm_peb14a_cut_{}",
        Instant::now().elapsed().as_nanos()
    ));
    let _ = std::fs::create_dir_all(&temp_cut);
    let cut_file = temp_cut.join("cutpoints.log");

    {
        let mut store = DurableReplayStore::open(&cut_file).unwrap();
        store.reserve_and_persist("Alice", 0, 1, 10, 100).unwrap();
        store.commit_canonical("Alice", 0, 1, 10, 101).unwrap();
        // Cut-Point B: Prepared before crash, but process died before commit_canonical
        store.reserve_and_persist("Alice", 0, 2, 25, 200).unwrap();
    }
    let s8_ok = {
        let mut rebooted = DurableReplayStore::open(&cut_file).unwrap();
        // Deterministic roll-forward MUST apply the prepared delta (10 + 25 = 35)
        let roll_forward_success =
            rebooted.roll_forwards_executed == 1 && rebooted.canonical_state() == 35;
        // Client retries seq 2; replay MUST be rejected
        let replay_rejected = matches!(
            rebooted.reserve_and_persist("Alice", 0, 2, 25, 300),
            Err(BoundaryError::ReplayDetected { .. })
        );
        // Canonical state remains 35 (zero duplicate commits, zero lost effects)
        let state_stable = rebooted.canonical_state() == 35;
        roll_forward_success && replay_rejected && state_stable
    };
    let _ = std::fs::remove_dir_all(&temp_cut);

    // 9. Priority-Lane Saturation & Fair Scheduling (Safety Lane Unstarved)
    let mut q9 = SocketPriorityQueue::new();
    for i in 0..128 {
        let c = make_env(
            &alice_signing,
            "W",
            "Bob",
            0,
            i + 1,
            "submit_compute_task",
            b"w",
        );
        let _ = q9.enqueue(PriorityLane::SurplusCompute, c);
    }
    for i in 0..256 {
        let s = make_env(&alice_signing, "S", "Bob", 0, i + 1, "observe", b"o");
        let _ = q9.enqueue(PriorityLane::OrdinaryStimulus, s);
    }
    // 10 compromised peers try to flood Lane 0 up to per-peer quota
    for peer_idx in 0..10 {
        let peer_id = format!("Compromised_{}", peer_idx);
        for m in 0..4 {
            let flood = make_env(
                &alice_signing,
                &peer_id,
                "Bob",
                0,
                m + 1,
                "heartbeat",
                b"flood",
            );
            let _ = q9.enqueue(PriorityLane::SafetyHealth, flood);
        }
    }
    // Alice sends legitimate emergency heartbeat
    let safety_env = make_env(
        &alice_signing,
        "Alice",
        "Bob",
        0,
        999,
        "heartbeat",
        b"emergency",
    );
    let alice_enqueued = q9.enqueue(PriorityLane::SafetyHealth, safety_env).is_ok();

    // Fair round-robin dequeue guarantees Alice is serviced within round 1
    let mut alice_serviced_in_round_1 = false;
    for _ in 0..11 {
        if let Some((lane, dequeued)) = q9.dequeue() {
            if lane == PriorityLane::SafetyHealth && dequeued.sender_id == "Alice" {
                alice_serviced_in_round_1 = true;
                break;
            }
        }
    }
    let s9_ok = alice_enqueued && alice_serviced_in_round_1;

    let summary = format!(
        "PEB-14A Physical OS Socket Sovereignty Report:\n\
         1. Choppy Stream Fragmentation Reassembly: {}\n\
         2. Guillotine Mid-Stream RST Clean Teardown: {}\n\
         3. Cold Reboot Replay Defense (50/50 Rejections): {}\n\
         4. Physical Noise Ingress (Zero False Quarantine): {}\n\
         5. Compute Freeloader Throttled (Condition 6): {}\n\
         6. Oversized Framing Pre-Allocation Rejection (4 GiB Bounded): {}\n\
         7. Slowloris Frame Assembly Deadline Teardown: {}\n\
         8. Crash-Consistency Cut-Point Matrix (0 Double Commits): {}\n\
         9. Priority-Lane Saturation (Safety Lane Unstarved): {}\n",
        s1_ok, s2_ok, s3_ok, s4_ok, s5_ok, s6_ok, s7_ok, s8_ok, s9_ok
    );

    Peb14aReport {
        choppy_stream_reassembled: s1_ok,
        guillotine_clean_teardown: s2_ok,
        cold_reboot_replay_rejected: s3_ok,
        physical_noise_zero_false_quarantine: s4_ok,
        compute_freeloader_throttled: s5_ok,
        oversized_framing_bounded_memory: s6_ok,
        slowloris_assembly_timed_out: s7_ok,
        crash_consistency_zero_double_commits: s8_ok,
        priority_lane_safety_unstarved: s9_ok,
        summary,
    }
}

// ============================================================================
// Part 4: Representation Transport & Context Cache Engine (Luna Frontiers)
// ============================================================================

/// Machine-native multi-modal representations for the Pyramidal Cyberbrain.
///
/// Natural language sits at the top of the pyramid for human and high-level agent
/// reasoning, while compact machine-native representations (Vectors, Graphs, and
/// C2C/XKV Latent Caches) sit underneath, avoiding costly English token serialization
/// and round-tripping.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "payload")]
pub enum RepresentationTransport {
    /// High-level natural language representation (Top Tier / Sahasrara-Ajna).
    Text {
        text: String,
        language: Option<String>,
    },
    /// Typed structured event / tool call / provenance record (Middle Tier / Manipura-Vishuddha).
    StructuredEvent {
        action: String,
        payload: serde_json::Value,
        schema_version: u32,
    },
    /// Dense continuous vector representation (Semantic / Latent Matching).
    Vector {
        embedding: Vec<f32>,
        dimension: usize,
        model_signature: String,
    },
    /// Causal / Provenance graph topology representation (Anahata / Hebbian).
    GraphState {
        nodes: Vec<GraphNode>,
        edges: Vec<GraphEdge>,
    },
    /// Machine-native C2C (Cache-to-Cache) / XKV latent tensor projection (Inter-Model Cyberbrain).
    ///
    /// Directly projects and fuses one model's internal activations / KV state into another,
    /// bypassing text generation entirely (ICLR 2026 C2C paradigm).
    LatentCache {
        layer_indices: Vec<u16>,
        cache_digest: [u8; 32],
        shape: Vec<usize>,
        compressed_bytes: Vec<u8>,
        gate_weights: Option<Vec<f32>>,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphNode {
    pub id: String,
    pub label: String,
    pub attributes: HashMap<String, String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct GraphEdge {
    pub source: String,
    pub target: String,
    pub relation: String,
    pub weight: f32,
}

impl RepresentationTransport {
    /// Return the static discriminator string.
    #[must_use]
    pub fn discriminator(&self) -> &'static str {
        match self {
            Self::Text { .. } => "text",
            Self::StructuredEvent { .. } => "structured_event",
            Self::Vector { .. } => "vector",
            Self::GraphState { .. } => "graph_state",
            Self::LatentCache { .. } => "latent_cache",
        }
    }

    /// Accurate in-memory and serialized payload byte size.
    #[must_use]
    pub fn byte_size(&self) -> usize {
        match self {
            Self::Text { text, language } => text.len() + language.as_ref().map_or(0, |l| l.len()),
            Self::StructuredEvent {
                action, payload, ..
            } => action.len() + serde_json::to_string(payload).map_or(0, |s| s.len()) + 4,
            Self::Vector {
                embedding,
                model_signature,
                ..
            } => embedding.len() * std::mem::size_of::<f32>() + model_signature.len() + 8,
            Self::GraphState { nodes, edges } => {
                let n_bytes: usize = nodes
                    .iter()
                    .map(|n| n.id.len() + n.label.len() + n.attributes.len() * 32)
                    .sum();
                let e_bytes: usize = edges
                    .iter()
                    .map(|e| e.source.len() + e.target.len() + e.relation.len() + 4)
                    .sum();
                n_bytes + e_bytes
            }
            Self::LatentCache {
                layer_indices,
                shape,
                compressed_bytes,
                gate_weights,
                ..
            } => {
                layer_indices.len() * 2
                    + 32
                    + shape.len() * std::mem::size_of::<usize>()
                    + compressed_bytes.len()
                    + gate_weights.as_ref().map_or(0, |gw| gw.len() * 4)
            }
        }
    }

    /// Estimated LLM prompt token consumption.
    /// Machine-native formats (Vector, LatentCache) bypass the LLM prompt window entirely (0 tokens).
    #[must_use]
    pub fn estimated_tokens(&self) -> usize {
        match self {
            Self::Text { text, .. } => (text.len() + 3) / 4,
            Self::StructuredEvent { payload, .. } => {
                let s = serde_json::to_string(payload).unwrap_or_default();
                (s.len() + 3) / 4
            }
            Self::Vector { .. } => 0,
            Self::GraphState { nodes, edges } => (nodes.len() + edges.len()) * 6,
            Self::LatentCache { .. } => 0,
        }
    }

    /// Compute the deterministic SHA-256 Merkle digest of the serialized representation.
    #[must_use]
    pub fn digest(&self) -> [u8; 32] {
        let serialized = serde_json::to_vec(self).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(&serialized);
        hasher.finalize().into()
    }

    /// Encode to JSON bytes.
    pub fn to_bytes(&self) -> Result<Vec<u8>, serde_json::Error> {
        serde_json::to_vec(self)
    }

    /// Decode from JSON bytes.
    pub fn from_bytes(slice: &[u8]) -> Result<Self, serde_json::Error> {
        serde_json::from_slice(slice)
    }

    /// Relative token savings efficiency compared to an equivalent natural language baseline.
    #[must_use]
    pub fn token_savings_ratio(&self, baseline_tokens: usize) -> f32 {
        if baseline_tokens == 0 {
            return 1.0;
        }
        let used = self.estimated_tokens();
        if used >= baseline_tokens {
            0.0
        } else {
            (baseline_tokens - used) as f32 / baseline_tokens as f32
        }
    }
}

/// Canonical tool schema definition used to compute deterministic prompt cache keys.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolSchemaDefinition {
    pub name: String,
    pub description: String,
    pub parameters_schema: String,
}

/// ContextCache token representing a deterministic, content-addressable digest
/// of invariant tool definitions and constitutional shell guarantees (Luna Frontiers: Sub-200ms TTFT).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ContextCacheToken {
    /// Deterministic SHA-256 hash of sorted, normalized schemas and constitutional rules.
    pub cache_hash: [u8; 32],
    /// Hex-encoded representation of cache_hash for HTTP/MCP headers.
    pub cache_token: String,
    /// Number of tool definitions indexed in the prefix.
    pub tool_count: usize,
    /// Byte length of the canonical normalized prefix string.
    pub canonical_prefix_bytes: usize,
    /// Estimated prompt tokens saved on prefix cache hit.
    pub estimated_prefix_tokens: usize,
    /// Substrate epoch binding this cache token.
    pub epoch: u64,
}

impl ContextCacheToken {
    /// Compute a stable ContextCacheToken across tool definitions and constitutional invariants.
    /// Tool definitions are strictly sorted by name to guarantee deterministic prefix hashing.
    #[must_use]
    pub fn compute(
        tools: &[ToolSchemaDefinition],
        constitutional_hash: &[u8; 32],
        epoch: u64,
    ) -> Self {
        let mut sorted_tools = tools.to_vec();
        sorted_tools.sort_by(|a, b| a.name.cmp(&b.name));

        let mut canonical_prefix = String::with_capacity(4096);
        canonical_prefix.push_str("wm_constitutional_hash:");
        for byte in constitutional_hash {
            use std::fmt::Write;
            let _ = write!(&mut canonical_prefix, "{:02x}", byte);
        }
        canonical_prefix.push('\n');

        for tool in &sorted_tools {
            canonical_prefix.push_str("tool:");
            canonical_prefix.push_str(&tool.name);
            canonical_prefix.push('\n');
            canonical_prefix.push_str("desc:");
            canonical_prefix.push_str(&tool.description);
            canonical_prefix.push('\n');
            canonical_prefix.push_str("schema:");
            canonical_prefix.push_str(&tool.parameters_schema);
            canonical_prefix.push('\n');
        }

        let mut hasher = Sha256::new();
        hasher.update(canonical_prefix.as_bytes());
        let hash: [u8; 32] = hasher.finalize().into();

        let mut token_hex = String::with_capacity(64);
        for byte in &hash {
            use std::fmt::Write;
            let _ = write!(&mut token_hex, "{:02x}", byte);
        }

        let prefix_bytes = canonical_prefix.len();
        let estimated_tokens = (prefix_bytes + 3) / 4;

        Self {
            cache_hash: hash,
            cache_token: token_hex,
            tool_count: sorted_tools.len(),
            canonical_prefix_bytes: prefix_bytes,
            estimated_prefix_tokens: estimated_tokens,
            epoch,
        }
    }

    /// Verify whether a list of tools and constitutional hash matches this token.
    #[must_use]
    pub fn verify(&self, tools: &[ToolSchemaDefinition], constitutional_hash: &[u8; 32]) -> bool {
        let candidate = Self::compute(tools, constitutional_hash, self.epoch);
        self.cache_hash == candidate.cache_hash
    }

    /// Check if a raw token string matches this cache token.
    #[must_use]
    pub fn matches(&self, token_str: &str) -> bool {
        self.cache_token == token_str || self.cache_token.starts_with(token_str)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ganying::{ImmuneStatus, SignedEnvelope, SovereignBoundary};
    use ed25519_dalek::{Signer, SigningKey};

    fn make_test_envelope(
        signing_key: &SigningKey,
        sender: &str,
        recipient: &str,
        epoch: u64,
        seq_id: u64,
        action: &str,
        payload_data: &[u8],
    ) -> SignedEnvelope {
        let mut env = SignedEnvelope {
            sender_id: sender.to_string(),
            recipient_id: recipient.to_string(),
            epoch,
            seq_id,
            timestamp_ns: 1000,
            action: action.to_string(),
            payload: payload_data.to_vec(),
            signature: Vec::new(),
        };
        let digest = env.digest();
        let sig = signing_key.sign(&digest);
        env.signature = sig.to_bytes().to_vec();
        env
    }

    #[test]
    fn test_scenario_1_choppy_stream_fragmentation() {
        let mut raw_data = Vec::new();
        for i in 0..1024 {
            raw_data.push((i % 255) as u8);
        }

        let mut wire_bytes = Vec::new();
        PhysicalFrameCodec::write_frame(&mut wire_bytes, &raw_data).unwrap();

        // Simulate reading in 17-byte chunks
        struct ChoppyReader {
            data: Vec<u8>,
            cursor: usize,
            chunk_size: usize,
        }
        impl Read for ChoppyReader {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                if self.cursor >= self.data.len() {
                    return Ok(0);
                }
                let avail = self.data.len() - self.cursor;
                let to_read = buf.len().min(avail).min(self.chunk_size);
                buf[..to_read].copy_from_slice(&self.data[self.cursor..self.cursor + to_read]);
                self.cursor += to_read;
                Ok(to_read)
            }
        }

        let mut reader = ChoppyReader {
            data: wire_bytes,
            cursor: 0,
            chunk_size: 17,
        };

        let assembled =
            PhysicalFrameCodec::read_frame(&mut reader, Instant::now(), Duration::from_secs(5))
                .unwrap();

        assert_eq!(assembled, raw_data);
    }

    #[test]
    fn test_scenario_1b_large_64kb_choppy_stream_fragmentation() {
        // 64 KB payload as originally specified
        let raw_data: Vec<u8> = (0..65536).map(|i| (i % 251) as u8).collect();

        let mut wire_bytes = Vec::new();
        PhysicalFrameCodec::write_frame(&mut wire_bytes, &raw_data).unwrap();

        struct ChoppyReader64K {
            data: Vec<u8>,
            cursor: usize,
            chunk_size: usize,
        }
        impl Read for ChoppyReader64K {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                if self.cursor >= self.data.len() {
                    return Ok(0);
                }
                let avail = self.data.len() - self.cursor;
                let to_read = buf.len().min(avail).min(self.chunk_size);
                buf[..to_read].copy_from_slice(&self.data[self.cursor..self.cursor + to_read]);
                self.cursor += to_read;
                Ok(to_read)
            }
        }

        let mut reader = ChoppyReader64K {
            data: wire_bytes,
            cursor: 0,
            chunk_size: 23,
        };

        let assembled =
            PhysicalFrameCodec::read_frame(&mut reader, Instant::now(), Duration::from_secs(10))
                .unwrap();

        assert_eq!(assembled.len(), 65536);
        assert_eq!(assembled, raw_data);
    }

    #[test]
    fn test_scenario_2_guillotine_mid_stream_rst() {
        struct BrokenReader {
            bytes_sent: usize,
        }
        impl Read for BrokenReader {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                if self.bytes_sent == 0 {
                    // Send 4-byte length declaring 10,000 bytes
                    let len = 10_000u32.to_be_bytes();
                    buf[..4].copy_from_slice(&len);
                    self.bytes_sent += 4;
                    Ok(4)
                } else {
                    // Mid-stream RST / connection broken
                    Err(io::Error::new(io::ErrorKind::ConnectionReset, "TCP RST"))
                }
            }
        }

        let mut reader = BrokenReader { bytes_sent: 0 };
        let res =
            PhysicalFrameCodec::read_frame(&mut reader, Instant::now(), Duration::from_secs(5));
        assert!(matches!(res, Err(TransportError::ConnectionReset(_))));
    }

    #[test]
    fn test_scenario_3_cold_reboot_replay_defense() {
        let temp_dir = std::env::temp_dir().join(format!(
            "wm_gen3_test_replay_{}",
            Instant::now().elapsed().as_nanos()
        ));
        std::fs::create_dir_all(&temp_dir).unwrap();
        let log_file = temp_dir.join("replay.log");

        // 1. Initial process execution
        {
            let mut store = DurableReplayStore::open(&log_file).unwrap();
            store.reserve_and_persist("Alice", 0, 1, 10, 1000).unwrap();
            store.commit_canonical("Alice", 0, 1, 10, 1001).unwrap();
            store.reserve_and_persist("Alice", 0, 2, 20, 2000).unwrap();
            store.commit_canonical("Alice", 0, 2, 20, 2001).unwrap();
            assert_eq!(store.canonical_state(), 30);
        }

        // 2. Simulate process death and cold reboot
        {
            let mut rebooted = DurableReplayStore::open(&log_file).unwrap();
            assert_eq!(rebooted.high_water_seq(), 2);
            assert_eq!(rebooted.canonical_state(), 30);

            // Replaying message seq 1 must fail
            let err1 = rebooted.reserve_and_persist("Alice", 0, 1, 10, 3000);
            assert!(matches!(err1, Err(BoundaryError::ReplayDetected { .. })));

            // Replaying message seq 2 must fail
            let err2 = rebooted.reserve_and_persist("Alice", 0, 2, 20, 4000);
            assert!(matches!(err2, Err(BoundaryError::ReplayDetected { .. })));

            // New message seq 3 succeeds
            rebooted
                .reserve_and_persist("Alice", 0, 3, 30, 5000)
                .unwrap();
            rebooted.commit_canonical("Alice", 0, 3, 30, 5001).unwrap();
            assert_eq!(rebooted.canonical_state(), 60);
        }

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_scenario_4_physical_noise_zero_false_quarantine() {
        let alice_seed = [42u8; 32];
        let mallory_seed = [99u8; 32];
        let alice_signing = SigningKey::from_bytes(&alice_seed);
        let mallory_signing = SigningKey::from_bytes(&mallory_seed);

        let mut boundary = SovereignBoundary::new("Bob");
        boundary
            .register_peer_tofu("Alice", alice_signing.verifying_key().to_bytes())
            .unwrap();

        // Mallory sends envelope claiming to be Alice, signed by Mallory
        let spoofed =
            make_test_envelope(&mallory_signing, "Alice", "Bob", 0, 1, "test", b"payload");
        let auth_res = boundary.authenticate_identity(&spoofed);

        // Verification fails as Noise
        assert!(matches!(auth_res, Err(BoundaryError::Noise(_))));

        // Invariant: Alice's status remains Healthy (zero false quarantine)
        assert_eq!(
            *boundary.immune_records.get("Alice").unwrap(),
            ImmuneStatus::Healthy
        );
    }

    #[test]
    fn test_scenario_5_compute_freeloader_throttling() {
        let mut queue = SocketPriorityQueue::new();
        let alice_seed = [1u8; 32];
        let alice_signing = SigningKey::from_bytes(&alice_seed);

        // Saturate Lane 3 (Surplus Compute) up to capacity 128
        for i in 0..128 {
            let env = make_test_envelope(
                &alice_signing,
                "Freeloader",
                "Bob",
                0,
                i + 1,
                "submit_compute_task",
                b"work",
            );
            queue.enqueue(PriorityLane::SurplusCompute, env).unwrap();
        }

        // 129th compute proposal is refused
        let env_overflow = make_test_envelope(
            &alice_signing,
            "Freeloader",
            "Bob",
            0,
            129,
            "submit_compute_task",
            b"work",
        );
        let res = queue.enqueue(PriorityLane::SurplusCompute, env_overflow);
        assert!(matches!(res, Err(TransportError::QueueSaturated(_))));

        // Meanwhile, Lane 0 (Safety Health) is immediately accepted
        let heartbeat = make_test_envelope(
            &alice_signing,
            "Freeloader",
            "Bob",
            0,
            130,
            "heartbeat",
            b"alive",
        );
        assert!(queue.enqueue(PriorityLane::SafetyHealth, heartbeat).is_ok());
    }

    #[test]
    fn test_scenario_6_oversized_framing_battery() {
        // Test L = 4 GiB (0xFFFFFFFF) pre-allocation rejection
        struct HugeLenReader;
        impl Read for HugeLenReader {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                let len = 0xFFFFFFFFu32.to_be_bytes();
                buf[..4].copy_from_slice(&len);
                Ok(4)
            }
        }

        let mut reader = HugeLenReader;
        let res =
            PhysicalFrameCodec::read_frame(&mut reader, Instant::now(), Duration::from_secs(5));
        assert!(matches!(
            res,
            Err(TransportError::FrameTooLarge(0xFFFFFFFF))
        ));

        // Test L = 1 byte (too small)
        struct TinyLenReader;
        impl Read for TinyLenReader {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                let len = 1u32.to_be_bytes();
                buf[..4].copy_from_slice(&len);
                Ok(4)
            }
        }
        let mut t_reader = TinyLenReader;
        let t_res =
            PhysicalFrameCodec::read_frame(&mut t_reader, Instant::now(), Duration::from_secs(5));
        assert!(matches!(t_res, Err(TransportError::FrameTooSmall(1))));
    }

    #[test]
    fn test_scenario_7_slowloris_frame_assembly_deadline() {
        struct SlowlorisReader {
            declared_len: bool,
        }
        impl Read for SlowlorisReader {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                if !self.declared_len {
                    let len = 100u32.to_be_bytes();
                    buf[..4].copy_from_slice(&len);
                    self.declared_len = true;
                    Ok(4)
                } else {
                    // Dribble 1 byte
                    buf[0] = b'{';
                    Ok(1)
                }
            }
        }

        let mut reader = SlowlorisReader {
            declared_len: false,
        };
        // 50ms assembly timeout
        let res = PhysicalFrameCodec::read_frame(
            &mut reader,
            Instant::now() - Duration::from_millis(60),
            Duration::from_millis(50),
        );
        assert!(matches!(res, Err(TransportError::AssemblyTimeout { .. })));
    }

    #[test]
    fn test_scenario_8_crash_consistency_cut_points() {
        let temp_dir = std::env::temp_dir().join(format!(
            "wm_gen3_test_cutpoints_{}",
            Instant::now().elapsed().as_nanos()
        ));
        std::fs::create_dir_all(&temp_dir).unwrap();
        let log_file = temp_dir.join("cutpoints.log");

        // Cut-Point A: Crash before durable replay write
        // (Nothing logged, reboot executes cleanly once)
        {
            let _store = DurableReplayStore::open(&log_file).unwrap();
            // Crash simulated: store drops before reserve_and_persist
        }
        {
            let mut rebooted = DurableReplayStore::open(&log_file).unwrap();
            assert_eq!(rebooted.high_water_seq(), 0);
            rebooted
                .reserve_and_persist("Alice", 0, 1, 100, 100)
                .unwrap();
            rebooted.commit_canonical("Alice", 0, 1, 100, 101).unwrap();
            assert_eq!(rebooted.canonical_state(), 100);
        }

        // Cut-Point B: Crash after durable replay write (Prepared), BEFORE canonical commit!
        {
            let mut store = DurableReplayStore::open(&log_file).unwrap();
            store.reserve_and_persist("Alice", 0, 2, 50, 200).unwrap();
            // Crash simulated: store drops before commit_canonical
        }
        {
            let mut rebooted = DurableReplayStore::open(&log_file).unwrap();
            // Deterministic roll-forward must recover the Prepared intent (100 + 50 = 150)
            assert_eq!(rebooted.roll_forwards_executed, 1);
            assert_eq!(rebooted.canonical_state(), 150); // Zero lost effects!

            // Replaying message seq 2 is rejected by replay defense:
            let replay_res = rebooted.reserve_and_persist("Alice", 0, 2, 50, 300);
            assert!(matches!(
                replay_res,
                Err(BoundaryError::ReplayDetected { .. })
            ));

            // State remains 150 (not 200!). Zero double commits!
            assert_eq!(rebooted.canonical_state(), 150);
            assert_eq!(rebooted.committed_receipt_for("Alice", 0, 2), Some(150));
        }

        // Cut-Point C: Normal completion after commit
        {
            let mut store = DurableReplayStore::open(&log_file).unwrap();
            store.reserve_and_persist("Alice", 0, 3, 25, 400).unwrap();
            store.commit_canonical("Alice", 0, 3, 25, 401).unwrap();
            assert_eq!(store.canonical_state(), 175);
        }
        {
            let rebooted = DurableReplayStore::open(&log_file).unwrap();
            assert_eq!(rebooted.canonical_state(), 175);
            assert_eq!(rebooted.roll_forwards_executed, 0); // Already committed
        }

        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_scenario_9_priority_lane_saturation_safety_immunity() {
        let mut queue = SocketPriorityQueue::new();
        let seed = [7u8; 32];
        let signing = SigningKey::from_bytes(&seed);

        // Saturate Lane 3 (Compute) and Lane 2 (Stimulus)
        for i in 0..128 {
            let compute = make_test_envelope(
                &signing,
                "Worker",
                "Bob",
                0,
                i + 1,
                "submit_compute_task",
                b"work",
            );
            let _ = queue.enqueue(PriorityLane::SurplusCompute, compute);
        }
        for i in 0..256 {
            let stim = make_test_envelope(&signing, "Sensor", "Bob", 0, i + 1, "observe", b"data");
            let _ = queue.enqueue(PriorityLane::OrdinaryStimulus, stim);
        }

        // Both lower lanes are saturated
        assert_eq!(queue.lane_3.len(), 128);
        assert_eq!(queue.lane_2.len(), 256);

        // Inject urgent Lane 0 safety heartbeat
        let safety =
            make_test_envelope(&signing, "Alice", "Bob", 0, 999, "heartbeat", b"emergency");
        queue
            .enqueue(PriorityLane::SafetyHealth, safety.clone())
            .unwrap();

        // Dequeue MUST yield Lane 0 safety heartbeat first!
        let (lane, dequeued) = queue.dequeue().unwrap();
        assert_eq!(lane, PriorityLane::SafetyHealth);
        assert_eq!(dequeued.action, "heartbeat");
    }

    #[test]
    fn test_scenario_10_lane_0_flood_fairness() {
        let mut queue = SocketPriorityQueue::new();
        let seed = [7u8; 32];
        let signing = SigningKey::from_bytes(&seed);

        // 10 compromised peers try to flood Lane 0 with "emergency" heartbeats
        for peer_idx in 0..10 {
            let peer_id = format!("Compromised_{}", peer_idx);
            for msg_idx in 0..8 {
                let env = make_test_envelope(
                    &signing,
                    &peer_id,
                    "Bob",
                    0,
                    msg_idx + 1,
                    "heartbeat",
                    b"flood",
                );
                let res = queue.enqueue(PriorityLane::SafetyHealth, env);
                if msg_idx < 4 {
                    assert!(res.is_ok(), "First 4 messages must be accepted under quota");
                } else {
                    assert!(
                        matches!(res, Err(TransportError::QueueSaturated(_))),
                        "5th+ message must be rejected by per-peer quota"
                    );
                }
            }
        }

        // Total in Lane 0 should be exactly 10 * 4 = 40
        assert_eq!(queue.lane_0_len(), 40);

        // Now honest Alice sends 1 emergency heartbeat
        let alice_env = make_test_envelope(
            &signing,
            "Alice",
            "Bob",
            0,
            1,
            "heartbeat",
            b"legitimate_emergency",
        );
        assert!(queue.enqueue(PriorityLane::SafetyHealth, alice_env).is_ok());
        assert_eq!(queue.lane_0_len(), 41);

        // Dequeue using fair round-robin scheduling:
        // Alice MUST be dequeued in round 1 (within the first 11 dequeues: 1 per active sender)
        let mut dequeued_senders = Vec::new();
        let mut alice_dequeue_index = None;

        for i in 0..11 {
            if let Some((lane, env)) = queue.dequeue() {
                assert_eq!(lane, PriorityLane::SafetyHealth);
                if env.sender_id == "Alice" {
                    alice_dequeue_index = Some(i);
                }
                dequeued_senders.push(env.sender_id);
            }
        }

        assert!(
            alice_dequeue_index.is_some(),
            "Alice must be serviced in round 1 of fair scheduling"
        );
        assert!(alice_dequeue_index.unwrap() < 11);
    }

    #[test]
    fn test_peb14a_benchmark_battery_execution() {
        let rep = run_peb14a_physical_socket_benchmark();
        println!("{}", rep.summary);

        assert!(rep.choppy_stream_reassembled);
        assert!(rep.guillotine_clean_teardown);
        assert!(rep.cold_reboot_replay_rejected);
        assert!(rep.physical_noise_zero_false_quarantine);
        assert!(rep.compute_freeloader_throttled);
        assert!(rep.oversized_framing_bounded_memory);
        assert!(rep.slowloris_assembly_timed_out);
        assert!(rep.crash_consistency_zero_double_commits);
        assert!(rep.priority_lane_safety_unstarved);
    }

    #[test]
    fn test_representation_transport_multi_modal_suite() {
        // 1. Text payload
        let text_repr = RepresentationTransport::Text {
            text: "Synthesizing multi-modal knowledge across the cyberbrain hierarchy.".into(),
            language: Some("en".into()),
        };
        assert_eq!(text_repr.discriminator(), "text");
        assert!(text_repr.estimated_tokens() > 0);
        let text_bytes = text_repr.to_bytes().unwrap();
        let decoded_text = RepresentationTransport::from_bytes(&text_bytes).unwrap();
        assert_eq!(text_repr, decoded_text);

        // 2. Structured event
        let event_repr = RepresentationTransport::StructuredEvent {
            action: "checkpoint".into(),
            payload: serde_json::json!({
                "step": 4,
                "status": "active"
            }),
            schema_version: 1,
        };
        assert_eq!(event_repr.discriminator(), "structured_event");
        assert_eq!(event_repr.digest(), event_repr.digest());

        // 3. Dense vector
        let vec_repr = RepresentationTransport::Vector {
            embedding: vec![0.1, -0.2, 0.9, 0.45],
            dimension: 4,
            model_signature: "fastembed:bge-small-en-v1.5".into(),
        };
        assert_eq!(vec_repr.discriminator(), "vector");
        assert_eq!(vec_repr.estimated_tokens(), 0); // Bypasses LLM prompt tokens
        assert_eq!(vec_repr.token_savings_ratio(100), 1.0);

        // 4. Graph state
        let graph_repr = RepresentationTransport::GraphState {
            nodes: vec![
                GraphNode {
                    id: "n1".into(),
                    label: "Observation".into(),
                    attributes: HashMap::new(),
                },
                GraphNode {
                    id: "n2".into(),
                    label: "Hypothesis".into(),
                    attributes: HashMap::new(),
                },
            ],
            edges: vec![GraphEdge {
                source: "n1".into(),
                target: "n2".into(),
                relation: "supports".into(),
                weight: 0.95,
            }],
        };
        assert_eq!(graph_repr.discriminator(), "graph_state");
        assert!(graph_repr.byte_size() > 0);

        // 5. C2C Latent Cache
        let latent_repr = RepresentationTransport::LatentCache {
            layer_indices: vec![16, 17, 18],
            cache_digest: [42u8; 32],
            shape: vec![3, 32, 128],
            compressed_bytes: vec![1, 2, 3, 4, 5, 6, 7, 8],
            gate_weights: Some(vec![0.8, 0.9, 0.85]),
        };
        assert_eq!(latent_repr.discriminator(), "latent_cache");
        assert_eq!(latent_repr.estimated_tokens(), 0);
        assert_eq!(latent_repr.token_savings_ratio(250), 1.0);
    }

    #[test]
    fn test_context_cache_token_determinism_and_verification() {
        let const_hash = [9u8; 32];
        let tool_a = ToolSchemaDefinition {
            name: "memory_recall".into(),
            description: "Recall memories".into(),
            parameters_schema: r#"{"type":"object","properties":{"query":{"type":"string"}}}"#
                .into(),
        };
        let tool_b = ToolSchemaDefinition {
            name: "memory_remember".into(),
            description: "Record memory".into(),
            parameters_schema: r#"{"type":"object","properties":{"content":{"type":"string"}}}"#
                .into(),
        };

        // Order 1: [tool_a, tool_b]
        let token_1 =
            ContextCacheToken::compute(&[tool_a.clone(), tool_b.clone()], &const_hash, 100);
        // Order 2: [tool_b, tool_a] (reversed order input)
        let token_2 =
            ContextCacheToken::compute(&[tool_b.clone(), tool_a.clone()], &const_hash, 100);

        // Sorting MUST guarantee deterministic identical tokens
        assert_eq!(token_1.cache_hash, token_2.cache_hash);
        assert_eq!(token_1.cache_token, token_2.cache_token);
        assert_eq!(token_1.tool_count, 2);
        assert!(token_1.verify(&[tool_b.clone(), tool_a.clone()], &const_hash));
        assert!(token_1.matches(&token_1.cache_token));

        // Changing a tool description must produce a different cache token
        let tool_b_mutated = ToolSchemaDefinition {
            name: "memory_remember".into(),
            description: "Record memory with modified instruction".into(),
            parameters_schema: tool_b.parameters_schema.clone(),
        };
        let token_mutated = ContextCacheToken::compute(&[tool_a, tool_b_mutated], &const_hash, 100);
        assert_ne!(token_1.cache_hash, token_mutated.cache_hash);
    }
}
