
with open("whitemagic-rust/src/continuous_daemon.rs") as f:
    content = f.read()

# Make the struct more robust to store actual daemon stats
content = content.replace(
    """pub struct ContinuousDaemon {
    running: Arc<AtomicBool>,
    runtime: Option<Runtime>,
    _worker: Option<JoinHandle<()>>,
}""",
    """pub struct ContinuousDaemon {
    running: Arc<AtomicBool>,
    runtime: Option<Runtime>,
    _worker: Option<JoinHandle<()>>,
    loops: Arc<AtomicU64>,
    tasks: Arc<AtomicU64>,
    errors: Arc<AtomicU64>,
}"""
)

# Update initialization
content = content.replace(
    """        Ok(Self {
            running: Arc::new(AtomicBool::new(false)),
            runtime: Some(runtime),
            _worker: None,
        })""",
    """        Ok(Self {
            running: Arc::new(AtomicBool::new(false)),
            runtime: Some(runtime),
            _worker: None,
            loops: Arc::new(AtomicU64::new(0)),
            tasks: Arc::new(AtomicU64::new(0)),
            errors: Arc::new(AtomicU64::new(0)),
        })"""
)

# Update the loop to increment stats
content = content.replace(
    """        let running_clone = Arc::clone(&self.running);

        // Spawn the daemon loop in Tokio
        if let Some(rt) = &self.runtime {
            self._worker = Some(rt.spawn(async move {
                while running_clone.load(Ordering::SeqCst) {
                    // Daemon core loop (to be expanded)
                    // - 1. Execute next objective
                    // - 2. Pull memory tasks
                    // - 3. Maintain homeostasis
                    tokio::time::sleep(Duration::from_millis(100)).await;
                }
            }));
        }""",
    """        let running_clone = Arc::clone(&self.running);
        let loops_clone = Arc::clone(&self.loops);

        // Spawn the daemon loop in Tokio
        if let Some(rt) = &self.runtime {
            self._worker = Some(rt.spawn(async move {
                while running_clone.load(Ordering::SeqCst) {
                    // Daemon core loop (to be expanded)
                    // - 1. Execute next objective
                    // - 2. Pull memory tasks
                    // - 3. Maintain homeostasis
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    loops_clone.fetch_add(1, Ordering::SeqCst);
                }
            }));
        }"""
)

# Update get_stats to use actual stats
content = content.replace(
    """        stats.insert("loops".to_string(), 0);
        stats.insert("tasks".to_string(), 0);
        stats.insert("errors".to_string(), 0);""",
    """        stats.insert("loops".to_string(), self.loops.load(Ordering::SeqCst));
        stats.insert("tasks".to_string(), self.tasks.load(Ordering::SeqCst));
        stats.insert("errors".to_string(), self.errors.load(Ordering::SeqCst));"""
)

# Remove unused DaemonStats
content = content.replace(
    """#[derive(Default)]
pub struct DaemonStats {
    pub loops_completed: AtomicU64,
    pub tasks_executed: AtomicU64,
    pub errors: AtomicU64,
}

""", ""
)

with open("whitemagic-rust/src/continuous_daemon.rs", "w") as f:
    f.write(content)
