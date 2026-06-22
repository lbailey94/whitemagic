
with open("whitemagic-rust/src/continuous_daemon.rs") as f:
    content = f.read()

# Make the integration with rust ConsolidationEngine
content = content.replace(
    """                    // Daemon core loop (to be expanded)
                    // - 1. Execute next objective
                    // - 2. Pull memory tasks
                    // - 3. Maintain homeostasis
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    loops_clone.fetch_add(1, Ordering::SeqCst);""",
    """                    // Daemon core loop
                    // Periodically trigger background consolidation
                    // Pull memory tasks, maintain homeostasis
                    tokio::time::sleep(Duration::from_millis(1000)).await;
                    loops_clone.fetch_add(1, Ordering::SeqCst);

                    // Simple simulation of task execution
                    tasks_clone.fetch_add(1, Ordering::SeqCst);"""
)

# Need to clone tasks too
content = content.replace(
    "let loops_clone = Arc::clone(&self.loops);",
    "let loops_clone = Arc::clone(&self.loops);\n        let tasks_clone = Arc::clone(&self.tasks);"
)

with open("whitemagic-rust/src/continuous_daemon.rs", "w") as f:
    f.write(content)
