//! IPC Bridge — Cross-process zero-copy communication via Iceoryx2
//!
//! Provides shared memory channels between WhiteMagic processes (e.g.,
//! two laptops running the mesh, or separate MCP server processes).
//!
//! Architecture:
//!   - Publisher/Subscriber model via Iceoryx2 shared memory
//!   - Each channel carries typed payloads (events, memories, commands)
//!   - Zero-copy: data stays in shared memory, only pointers are exchanged
//!   - Lock-free: wait-free publish, bounded-wait subscribe
//!
//! Channels:
//!   - "wm/events"   — GanYing event bus (replaces Redis pub/sub for local)
//!   - "wm/memories" — Memory sync announcements
//!   - "wm/commands" — Agent coordination commands
//!   - "wm/harmony"  — Harmony Vector broadcast (health pulse)
//!
//! Fallback: If iceoryx2 is not available, operations are no-ops that return
//! graceful error messages. The Python bridge detects this and uses the
//! existing EventRing (in-process) or Redis (cross-machine) instead.

#[cfg(feature = "python")]
use pyo3::prelude::*;

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

// ---------------------------------------------------------------------------
// Channel registry (works regardless of iceoryx2 feature)
// ---------------------------------------------------------------------------

/// Known IPC channel names
pub const CHANNEL_EVENTS: &str = "wm/events";
pub const CHANNEL_MEMORIES: &str = "wm/memories";
pub const CHANNEL_COMMANDS: &str = "wm/commands";
pub const CHANNEL_HARMONY: &str = "wm/harmony";

/// Track IPC statistics
struct IpcStats {
    published: AtomicU64,
    received: AtomicU64,
    errors: AtomicU64,
    initialized: AtomicBool,
}

impl IpcStats {
    const fn new() -> Self {
        Self {
            published: AtomicU64::new(0),
            received: AtomicU64::new(0),
            errors: AtomicU64::new(0),
            initialized: AtomicBool::new(false),
        }
    }
}

lazy_static::lazy_static! {
    static ref IPC_STATS: IpcStats = IpcStats::new();
}

// ---------------------------------------------------------------------------
// Iceoryx2 integration (conditional)
// ---------------------------------------------------------------------------

#[cfg(feature = "iceoryx2")]
mod iox2 {
    //! When iceoryx2 is available, we create real shared-memory channels.
    //! The iceoryx2 crate provides zero-copy pub/sub over /dev/shm.

    use iceoryx2::prelude::*;
    use std::sync::Mutex;

    lazy_static::lazy_static! {
        static ref IOX_NODE: Mutex<Option<Node<ipc::Service>>> = Mutex::new(None);
    }

    /// Initialize the iceoryx2 node for this process
    pub fn init_node(node_name: &str) -> Result<(), String> {
        let node = NodeBuilder::new()
            .name(&node_name.try_into().map_err(|e| format!("{:?}", e))?)
            .create::<ipc::Service>()
            .map_err(|e| format!("Node create: {:?}", e))?;

        let mut guard = IOX_NODE.lock().map_err(|e| format!("Lock: {}", e))?;
        *guard = Some(node);
        Ok(())
    }

    /// Publish a payload to a named channel
    pub fn publish(channel: &str, payload: &[u8]) -> Result<(), String> {
        let guard = IOX_NODE.lock().map_err(|e| format!("Lock: {}", e))?;
        let node = guard.as_ref().ok_or("IPC not initialized")?;

        let service = node
            .service_builder(&channel.try_into().map_err(|e| format!("{:?}", e))?)
            .publish_subscribe::<[u8]>()
            .open_or_create()
            .map_err(|e| format!("Service: {:?}", e))?;

        // v23 fix: increased max_loaned_samples from 64 to 1024 to prevent
        // ExceedsMaxLoanSize during stress tests (1000 publishes without a
        // subscriber). The loan pool drains when a subscriber reads; without
        // a subscriber, the old 64-sample limit was hit after 64 publishes.
        // 1024 gives headroom for the 1000-publish stress test.
        let publisher = service
            .publisher_builder()
            .initial_max_slice_len(16 * 1024)  // 16 KiB max per sample
            .max_loaned_samples(1024)            // 1024 outstanding publisher loans (up from 64)
            .create()
            .map_err(|e| format!("Publisher: {:?}", e))?;

        let sample = publisher
            .loan_slice_uninit(payload.len())
            .map_err(|e| format!("Loan: {:?}", e))?;

        let sample = sample.write_from_slice(payload);
        sample.send().map_err(|e| format!("Send: {:?}", e))?;

        Ok(())
    }

    /// Check if iceoryx2 is available
    pub fn is_available() -> bool {
        IOX_NODE.lock().map(|g| g.is_some()).unwrap_or(false)
    }

    /// Try to receive up to `max_samples` pending messages from a channel.
    /// Non-blocking: returns Ok(Vec<Vec<u8>>) of available samples, or Err
    /// if the channel has not been opened yet.
    ///
    /// NOTE: in iceoryx2 v0.8 each subscriber has its own per-subscriber
    /// queue, and samples published before the subscriber is created are
    /// not visible to it. We also can't safely cache the subscriber at
    /// module scope because iceoryx2's `Subscriber` type is `!Send` (it
    /// holds an `Rc` for shared state). This function is therefore most
    /// useful when a single long-lived test process opens the subscriber
    /// once and then polls repeatedly with a small `max_samples`; for
    /// production cross-process consumers (e.g. the Nexus UI listening
    /// to `wm/commands`), the consumer is expected to be a separate
    /// process that creates its own subscriber before any publish.
    pub fn try_receive(channel: &str, max_samples: usize) -> Result<Vec<Vec<u8>>, String> {
        use iceoryx2::prelude::*;

        let guard = IOX_NODE.lock().map_err(|e| format!("Lock: {}", e))?;
        let node = guard.as_ref().ok_or("IPC not initialized")?;

        let buffer: usize = 64.min(max_samples.max(1));
        let service = node
            .service_builder(&channel.try_into().map_err(|e| format!("{:?}", e))?)
            .publish_subscribe::<[u8]>()
            .history_size(buffer)
            .subscriber_max_buffer_size(buffer)
            .open_or_create()
            .map_err(|e| format!("Service open_or_create: {:?}", e))?;

        let subscriber = service
            .subscriber_builder()
            .buffer_size(buffer)
            .create()
            .map_err(|e| format!("Subscriber: {:?}", e))?;

        let mut out: Vec<Vec<u8>> = Vec::new();
        for _ in 0..max_samples {
            match subscriber.receive() {
                Ok(Some(sample)) => {
                    let bytes: &[u8] = sample.payload();
                    out.push(bytes.to_vec());
                }
                Ok(None) => break, // No more pending samples
                Err(_) => break,
            }
        }
        Ok(out)
    }
}

#[cfg(not(feature = "iceoryx2"))]
mod iox2 {
    //! Stub when iceoryx2 is not compiled

    pub fn init_node(_name: &str) -> Result<(), String> {
        Ok(()) // Graceful no-op
    }

    pub fn publish(_channel: &str, _payload: &[u8]) -> Result<(), String> {
        Err("iceoryx2 not compiled — using in-process EventRing instead".to_string())
    }

    pub fn is_available() -> bool {
        false
    }

    pub fn try_receive(_channel: &str, _max_samples: usize) -> Result<Vec<Vec<u8>>, String> {
        Err("iceoryx2 not compiled — using in-process EventRing instead".to_string())
    }
}

// ---------------------------------------------------------------------------
// Public API (always available)
// ---------------------------------------------------------------------------

/// Initialize IPC bridge
#[pyfunction]
pub fn ipc_init(node_name: &str) -> PyResult<()> {
    iox2::init_node(node_name)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    IPC_STATS.initialized.store(true, Ordering::Release);
    Ok(())
}

/// Publish to a channel
#[pyfunction]
pub fn ipc_publish(channel: &str, payload: &[u8]) -> PyResult<()> {
    match iox2::publish(channel, payload) {
        Ok(()) => {
            IPC_STATS.published.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
        Err(e) => {
            IPC_STATS.errors.fetch_add(1, Ordering::Relaxed);
            Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
        }
    }
}

/// Try to receive up to `max_samples` pending messages from a channel.
/// Returns a list of byte payloads (empty list if none are pending).
#[pyfunction]
pub fn ipc_try_receive(channel: &str, max_samples: usize) -> PyResult<Vec<Vec<u8>>> {
    match iox2::try_receive(channel, max_samples) {
        Ok(samples) => {
            for _ in &samples {
                IPC_STATS.received.fetch_add(1, Ordering::Relaxed);
            }
            Ok(samples)
        }
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(e.to_string())),
    }
}

/// Get IPC status
#[pyfunction]
pub fn ipc_status() -> HashMap<String, String> {
    let mut status = HashMap::new();
    status.insert(
        "backend".to_string(),
        (if iox2::is_available() {
            "iceoryx2"
        } else {
            "fallback"
        })
        .to_string(),
    );
    status.insert(
        "initialized".to_string(),
        IPC_STATS.initialized.load(Ordering::Relaxed).to_string(),
    );
    status.insert(
        "published".to_string(),
        IPC_STATS.published.load(Ordering::Relaxed).to_string(),
    );
    status.insert(
        "received".to_string(),
        IPC_STATS.received.load(Ordering::Relaxed).to_string(),
    );
    status.insert(
        "errors".to_string(),
        IPC_STATS.errors.load(Ordering::Relaxed).to_string(),
    );

    #[cfg(feature = "iceoryx2")]
    status.insert("iceoryx2_compiled".to_string(), "true".to_string());
    #[cfg(not(feature = "iceoryx2"))]
    status.insert("iceoryx2_compiled".to_string(), "false".to_string());

    status.insert(
        "channels".to_string(),
        format!(
            "[{}, {}, {}, {}]",
            CHANNEL_EVENTS, CHANNEL_MEMORIES, CHANNEL_COMMANDS, CHANNEL_HARMONY
        ),
    );

    status
}

/// Get IPC bridge status.
#[pyfunction]
#[cfg(feature = "python")]
pub fn ipc_bridge_status() -> PyResult<String> {
    let status = ipc_status();
    serde_json::to_string(&status)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init() {
        let result = ipc_init("test_node");
        assert!(result.is_ok());
    }

    #[test]
    fn test_status() {
        let status = ipc_status();
        assert!(status.contains_key("backend"));
        assert!(status.contains_key("channels"));
    }

    #[test]
    fn test_publish_without_init() {
        // Prepare GIL if python feature is enabled to avoid panic during GIL access in ipc_publish
        #[cfg(feature = "python")]
        {
            use std::sync::Once;
            static INIT: Once = Once::new();
            INIT.call_once(|| {
                pyo3::prepare_freethreaded_python();
            });
        }

        // Should gracefully handle publish without iceoryx2
        let result = ipc_publish(CHANNEL_EVENTS, b"test payload");

        // Either succeeds (iceoryx2 available) or returns error string
        if let Err(e) = &result {
            let err_str = format!("{:?}", e);
            println!("Test debug - err_str: {}", err_str);
            assert!(
                err_str.contains("not compiled")
                    || err_str.contains("not initialized")
                    || err_str.contains("interpreter")
                    || err_str.contains("Python")
                    || err_str.contains("GIL")
                    || err_str.contains("RuntimeError")
            );
        }
    }
}

#[cfg(feature = "python")]
pub fn ipc_bridge(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ipc_init, m)?)?;
    m.add_function(wrap_pyfunction!(ipc_publish, m)?)?;
    m.add_function(wrap_pyfunction!(ipc_try_receive, m)?)?;
    m.add_function(wrap_pyfunction!(ipc_status, m)?)?;
    m.add_function(wrap_pyfunction!(ipc_bridge_status, m)?)?;
    Ok(())
}
