
with open("whitemagic-rust/src/continuous_daemon.rs") as f:
    content = f.read()

# Merge the pymethods blocks
content = content.replace(
    """    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }
}

pub fn register_daemon(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ContinuousDaemon>()?;
    Ok(())
}

use std::sync::atomic::AtomicU64;

#[derive(Default)]
pub struct DaemonStats {
    pub loops_completed: AtomicU64,
    pub tasks_executed: AtomicU64,
    pub errors: AtomicU64,
}

#[pymethods]
impl ContinuousDaemon {
    pub fn get_stats(&self) -> PyResult<std::collections::HashMap<String, u64>> {
        let mut stats = std::collections::HashMap::new();
        // Return dummy stats for now until wired
        stats.insert("loops".to_string(), 0);
        stats.insert("tasks".to_string(), 0);
        stats.insert("errors".to_string(), 0);
        Ok(stats)
    }
}""",
    """    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    pub fn get_stats(&self) -> PyResult<std::collections::HashMap<String, u64>> {
        let mut stats = std::collections::HashMap::new();
        // Return dummy stats for now until wired
        stats.insert("loops".to_string(), 0);
        stats.insert("tasks".to_string(), 0);
        stats.insert("errors".to_string(), 0);
        Ok(stats)
    }
}

use std::sync::atomic::AtomicU64;

#[derive(Default)]
pub struct DaemonStats {
    pub loops_completed: AtomicU64,
    pub tasks_executed: AtomicU64,
    pub errors: AtomicU64,
}

pub fn register_daemon(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ContinuousDaemon>()?;
    Ok(())
}"""
)

# Remove unused sync::mpsc
content = content.replace("use tokio::sync::mpsc;\n", "")

with open("whitemagic-rust/src/continuous_daemon.rs", "w") as f:
    f.write(content)
