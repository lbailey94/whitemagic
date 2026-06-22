//! Health monitoring system

use crate::conductor::{SubsystemId, SubsystemRegistry};
use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc, RwLock,
};
use std::time::{Duration, Instant};

/// Health state of a subsystem
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthState {
    Healthy,
    Degraded,
    Failed,
    Unknown,
}

impl HealthState {
    /// Check if state is considered healthy
    pub fn is_healthy(&self) -> bool {
        matches!(self, Self::Healthy | Self::Degraded)
    }
}

/// Health status for a subsystem
#[derive(Debug, Clone)]
pub struct HealthStatus {
    pub state: HealthState,
    pub last_ping: Instant,
    pub error_count: u32,
    pub metrics: HashMap<String, f64>,
    pub message: Option<String>,
}

impl Default for HealthStatus {
    fn default() -> Self {
        Self {
            state: HealthState::Unknown,
            last_ping: Instant::now(),
            error_count: 0,
            metrics: HashMap::new(),
            message: None,
        }
    }
}

/// Health monitor for all subsystems
pub struct HealthMonitor {
    /// Registry reference
    registry: Arc<SubsystemRegistry>,

    /// Per-subsystem health status
    statuses: RwLock<HashMap<SubsystemId, HealthStatus>>,

    /// Monitor interval for periodic checks
    check_interval: Duration,

    /// Last check time
    last_check: RwLock<Instant>,

    /// Total health checks performed
    checks_performed: AtomicU64,

    /// Running flag
    running: RwLock<bool>,
}

impl HealthMonitor {
    /// Create new health monitor with default interval (30s)
    pub fn new(registry: Arc<SubsystemRegistry>) -> Self {
        Self {
            registry,
            statuses: RwLock::new(HashMap::new()),
            check_interval: Duration::from_secs(30),
            last_check: RwLock::new(Instant::now()),
            checks_performed: AtomicU64::new(0),
            running: RwLock::new(false),
        }
    }

    /// Create health monitor with custom check interval
    pub fn with_interval(registry: Arc<SubsystemRegistry>, check_interval: Duration) -> Self {
        Self {
            registry,
            statuses: RwLock::new(HashMap::new()),
            check_interval,
            last_check: RwLock::new(Instant::now()),
            checks_performed: AtomicU64::new(0),
            running: RwLock::new(false),
        }
    }

    /// Get the configured check interval
    pub fn get_check_interval(&self) -> Duration {
        self.check_interval
    }

    /// Check if a health check is due based on the interval
    pub fn is_check_due(&self) -> bool {
        if let Ok(last_check) = self.last_check.read() {
            last_check.elapsed() >= self.check_interval
        } else {
            true
        }
    }

    /// Perform periodic health check on all monitored subsystems
    /// Returns the number of subsystems checked
    pub fn perform_periodic_check(&self) -> usize {
        let now = Instant::now();

        // Update last check time
        if let Ok(mut last_check) = self.last_check.write() {
            *last_check = now;
        }

        // Increment check counter
        self.checks_performed.fetch_add(1, Ordering::SeqCst);

        // Check all monitored subsystems
        let mut checked = 0;
        if let Ok(mut statuses) = self.statuses.write() {
            for (_id, status) in statuses.iter_mut() {
                // Check if subsystem has pinged recently
                let time_since_ping = now.duration_since(status.last_ping);

                // If no ping for 3x the check interval, mark as degraded
                if time_since_ping > self.check_interval * 3 {
                    status.state = HealthState::Degraded;
                    status.message = Some(format!("No ping for {:?}", time_since_ping));
                }

                // If no ping for 10x the check interval, mark as failed
                if time_since_ping > self.check_interval * 10 {
                    status.state = HealthState::Failed;
                    status.message = Some(format!("No ping for {:?}", time_since_ping));
                }

                checked += 1;
            }
        }

        checked
    }

    /// Get time until next check is due
    pub fn time_until_next_check(&self) -> Duration {
        if let Ok(last_check) = self.last_check.read() {
            let elapsed = last_check.elapsed();
            if elapsed < self.check_interval {
                self.check_interval - elapsed
            } else {
                Duration::ZERO
            }
        } else {
            Duration::ZERO
        }
    }

    /// Get total checks performed
    pub fn total_checks(&self) -> u64 {
        self.checks_performed.load(Ordering::SeqCst)
    }

    /// Start health monitoring
    pub fn start(&self) {
        if let Ok(mut running) = self.running.write() {
            *running = true;
        }
    }

    /// Stop health monitoring
    pub fn stop(&self) {
        if let Ok(mut running) = self.running.write() {
            *running = false;
        }
    }

    /// Check if monitor is running
    pub fn is_running(&self) -> bool {
        if let Ok(running) = self.running.read() {
            *running
        } else {
            false
        }
    }

    /// Start monitoring a specific subsystem
    pub fn start_monitoring(&self, id: SubsystemId) {
        if let Ok(mut statuses) = self.statuses.write() {
            statuses.insert(id, HealthStatus::default());
        }
    }

    /// Stop monitoring a specific subsystem
    pub fn stop_monitoring(&self, id: SubsystemId) {
        if let Ok(mut statuses) = self.statuses.write() {
            statuses.remove(&id);
        }
    }

    /// Update health status for a subsystem
    pub fn update_status(&self, id: SubsystemId, status: HealthStatus) -> bool {
        if let Ok(mut statuses) = self.statuses.write() {
            statuses.insert(id, status);
            true
        } else {
            false
        }
    }

    /// Report ping from a subsystem
    pub fn ping(&self, id: SubsystemId) -> bool {
        if let Ok(mut statuses) = self.statuses.write() {
            let status = statuses.entry(id).or_insert_with(HealthStatus::default);
            status.last_ping = Instant::now();
            status.state = HealthState::Healthy;
            true
        } else {
            false
        }
    }

    /// Report error from a subsystem
    pub fn report_error(&self, id: SubsystemId, error: &str) -> bool {
        if let Ok(mut statuses) = self.statuses.write() {
            let status = statuses.entry(id).or_insert_with(HealthStatus::default);
            status.error_count += 1;
            status.message = Some(error.to_string());

            // Degrade if too many errors
            if status.error_count > 5 {
                status.state = HealthState::Degraded;
            }
            if status.error_count > 10 {
                status.state = HealthState::Failed;
            }

            true
        } else {
            false
        }
    }

    /// Get health status for a subsystem
    pub fn get_status(&self, id: SubsystemId) -> Option<HealthStatus> {
        if let Ok(statuses) = self.statuses.read() {
            statuses.get(&id).cloned()
        } else {
            None
        }
    }

    /// Get all health statuses
    pub fn get_all_status(&self) -> HashMap<SubsystemId, HealthStatus> {
        if let Ok(statuses) = self.statuses.read() {
            statuses.clone()
        } else {
            HashMap::new()
        }
    }

    /// Check if subsystem is healthy
    pub fn is_healthy(&self, id: SubsystemId) -> bool {
        self.get_status(id)
            .map(|s| s.state.is_healthy())
            .unwrap_or(false)
    }

    /// Get overall system health
    pub fn get_overall_health(&self) -> HealthState {
        let statuses = self.get_all_status();

        if statuses.is_empty() {
            return HealthState::Unknown;
        }

        let failed = statuses
            .values()
            .filter(|s| s.state == HealthState::Failed)
            .count();
        let degraded = statuses
            .values()
            .filter(|s| s.state == HealthState::Degraded)
            .count();

        if failed > 0 {
            HealthState::Failed
        } else if degraded > 0 {
            HealthState::Degraded
        } else {
            HealthState::Healthy
        }
    }

    /// Get overall coherence score (0.0 - 1.0)
    pub fn get_coherence_score(&self) -> f64 {
        let statuses = self.get_all_status();

        if statuses.is_empty() {
            return 0.0;
        }

        let total: f64 = statuses
            .values()
            .map(|s| match s.state {
                HealthState::Healthy => 1.0,
                HealthState::Degraded => 0.5,
                HealthState::Failed => 0.0,
                HealthState::Unknown => 0.0,
            })
            .sum();

        total / statuses.len() as f64
    }

    /// Get stale subsystems (haven't pinged recently)
    pub fn get_stale_subsystems(&self, threshold: Duration) -> Vec<SubsystemId> {
        let now = Instant::now();

        if let Ok(statuses) = self.statuses.read() {
            statuses
                .iter()
                .filter(|(_, status)| now.duration_since(status.last_ping) > threshold)
                .map(|(id, _)| *id)
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Run a health check cycle
    pub fn check_all(&self) -> HealthCheckResult {
        let start = Instant::now();

        // Get all subsystems from registry
        let subsystems = self.registry.list_all();

        let mut checked = 0;
        let mut healthy = 0;
        let mut degraded = 0;
        let mut failed = 0;

        for (id, handle) in subsystems {
            checked += 1;

            // Try to get status from handle
            match handle.health_check() {
                Ok(_) => {
                    self.ping(id);
                    healthy += 1;
                }
                Err(e) => {
                    self.report_error(id, &e);
                    let status = self.get_status(id);
                    match status.map(|s| s.state) {
                        Some(HealthState::Degraded) => degraded += 1,
                        Some(HealthState::Failed) => failed += 1,
                        _ => failed += 1,
                    }
                }
            }
        }

        // Check for stale subsystems
        let stale = self.get_stale_subsystems(Duration::from_secs(60));
        let stale_count = stale.len();
        for id in stale {
            if let Ok(mut statuses) = self.statuses.write() {
                if let Some(status) = statuses.get_mut(&id) {
                    status.state = HealthState::Degraded;
                }
            }
        }

        self.checks_performed.fetch_add(1, Ordering::SeqCst);

        if let Ok(mut last_check) = self.last_check.write() {
            *last_check = Instant::now();
        }

        HealthCheckResult {
            checked,
            healthy,
            degraded,
            failed,
            stale: stale_count,
            duration_ms: start.elapsed().as_millis() as u64,
        }
    }

    /// Get check count
    pub fn get_check_count(&self) -> u64 {
        self.checks_performed.load(Ordering::SeqCst)
    }
}

/// Health check result
#[derive(Debug, Clone)]
pub struct HealthCheckResult {
    pub checked: usize,
    pub healthy: usize,
    pub degraded: usize,
    pub failed: usize,
    pub stale: usize,
    pub duration_ms: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_monitor_creation() {
        let registry = Arc::new(SubsystemRegistry::new(Arc::new(
            crate::conductor::EventBus::new(),
        )));
        let monitor = HealthMonitor::new(registry);

        assert!(!monitor.is_running());
        assert_eq!(monitor.get_check_count(), 0);
    }

    #[test]
    fn test_health_ping() {
        let registry = Arc::new(SubsystemRegistry::new(Arc::new(
            crate::conductor::EventBus::new(),
        )));
        let monitor = HealthMonitor::new(registry);

        let id = 1;
        monitor.start_monitoring(id);

        assert!(monitor.ping(id));

        let status = monitor.get_status(id).unwrap();
        assert_eq!(status.state, HealthState::Healthy);
    }

    #[test]
    fn test_error_reporting() {
        let registry = Arc::new(SubsystemRegistry::new(Arc::new(
            crate::conductor::EventBus::new(),
        )));
        let monitor = HealthMonitor::new(registry);

        let id = 1;
        monitor.start_monitoring(id);

        // Report errors
        for _ in 0..6 {
            monitor.report_error(id, "Test error");
        }

        let status = monitor.get_status(id).unwrap();
        assert_eq!(status.state, HealthState::Degraded);
        assert_eq!(status.error_count, 6);
    }

    #[test]
    fn test_overall_health() {
        let registry = Arc::new(SubsystemRegistry::new(Arc::new(
            crate::conductor::EventBus::new(),
        )));
        let monitor = HealthMonitor::new(registry);

        assert_eq!(monitor.get_overall_health(), HealthState::Unknown);

        // Add healthy subsystem
        monitor.start_monitoring(1);
        monitor.ping(1);

        assert_eq!(monitor.get_overall_health(), HealthState::Healthy);

        // Add degraded subsystem (needs >5 errors to degrade)
        monitor.start_monitoring(2);
        for _ in 0..6 {
            monitor.report_error(2, "error");
        }

        assert_eq!(monitor.get_overall_health(), HealthState::Degraded);
    }
}

use serde::{Deserialize, Serialize};
