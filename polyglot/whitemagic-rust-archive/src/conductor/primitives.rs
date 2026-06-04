//! Orchestration primitives - circuit breaker, retry, timeout, backpressure

use std::collections::HashMap;
use std::sync::{
    atomic::{AtomicU32, AtomicU64, Ordering},
    Arc, RwLock,
};
use std::time::{Duration, Instant};

/// Circuit breaker states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CircuitState {
    Closed,   // Normal operation
    Open,     // Failing, rejecting requests
    HalfOpen, // Testing if service recovered
}

/// Circuit breaker configuration
#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    /// Failure threshold to open circuit
    pub failure_threshold: u32,
    /// Success threshold to close circuit from half-open
    pub success_threshold: u32,
    /// Timeout before attempting half-open
    pub timeout_duration: Duration,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 3,
            timeout_duration: Duration::from_secs(30),
        }
    }
}

/// Circuit breaker for fault tolerance
pub struct CircuitBreaker {
    name: String,
    state: RwLock<CircuitState>,
    config: CircuitBreakerConfig,

    // Statistics
    failure_count: AtomicU32,
    success_count: AtomicU32,
    last_failure_time: RwLock<Option<Instant>>,
    total_requests: AtomicU64,
    total_failures: AtomicU64,
    total_successes: AtomicU64,
}

impl CircuitBreaker {
    /// Create new circuit breaker
    pub fn new(name: String, config: CircuitBreakerConfig) -> Self {
        Self {
            name,
            state: RwLock::new(CircuitState::Closed),
            config,
            failure_count: AtomicU32::new(0),
            success_count: AtomicU32::new(0),
            last_failure_time: RwLock::new(None),
            total_requests: AtomicU64::new(0),
            total_failures: AtomicU64::new(0),
            total_successes: AtomicU64::new(0),
        }
    }

    /// Get current state
    pub fn get_state(&self) -> CircuitState {
        if let Ok(state) = self.state.read() {
            *state
        } else {
            CircuitState::Open // Fail safe
        }
    }

    /// Check if request can proceed
    pub fn can_execute(&self) -> bool {
        self.total_requests.fetch_add(1, Ordering::SeqCst);

        let state = self.get_state();

        match state {
            CircuitState::Closed => true,
            CircuitState::Open => {
                // Check if timeout elapsed, transition to half-open
                if let Ok(last_failure) = self.last_failure_time.read() {
                    if let Some(time) = *last_failure {
                        if time.elapsed() >= self.config.timeout_duration {
                            if let Ok(mut s) = self.state.write() {
                                *s = CircuitState::HalfOpen;
                            }
                            self.failure_count.store(0, Ordering::SeqCst);
                            self.success_count.store(0, Ordering::SeqCst);
                            return true;
                        }
                    }
                }
                false
            }
            CircuitState::HalfOpen => true,
        }
    }

    /// Record success
    pub fn record_success(&self) {
        self.total_successes.fetch_add(1, Ordering::SeqCst);

        let state = self.get_state();

        match state {
            CircuitState::HalfOpen => {
                let successes = self.success_count.fetch_add(1, Ordering::SeqCst) + 1;
                if successes >= self.config.success_threshold {
                    if let Ok(mut s) = self.state.write() {
                        *s = CircuitState::Closed;
                    }
                    self.failure_count.store(0, Ordering::SeqCst);
                    self.success_count.store(0, Ordering::SeqCst);
                }
            }
            CircuitState::Closed => {
                self.failure_count.store(0, Ordering::SeqCst);
            }
            _ => {}
        }
    }

    /// Record failure
    pub fn record_failure(&self) {
        self.total_failures.fetch_add(1, Ordering::SeqCst);

        if let Ok(mut last) = self.last_failure_time.write() {
            *last = Some(Instant::now());
        }

        let state = self.get_state();

        match state {
            CircuitState::HalfOpen | CircuitState::Closed => {
                let failures = self.failure_count.fetch_add(1, Ordering::SeqCst) + 1;
                if failures >= self.config.failure_threshold {
                    if let Ok(mut s) = self.state.write() {
                        *s = CircuitState::Open;
                    }
                }
            }
            _ => {}
        }
    }

    /// Execute function with circuit breaker
    pub fn execute<F, T>(&self, f: F) -> Result<T, CircuitBreakerError>
    where
        F: FnOnce() -> Result<T, String>,
    {
        if !self.can_execute() {
            return Err(CircuitBreakerError::CircuitOpen);
        }

        match f() {
            Ok(result) => {
                self.record_success();
                Ok(result)
            }
            Err(e) => {
                self.record_failure();
                Err(CircuitBreakerError::ExecutionFailed(e))
            }
        }
    }

    /// Get statistics
    pub fn get_stats(&self) -> CircuitBreakerStats {
        CircuitBreakerStats {
            name: self.name.clone(),
            state: self.get_state(),
            failure_count: self.failure_count.load(Ordering::SeqCst),
            success_count: self.success_count.load(Ordering::SeqCst),
            total_requests: self.total_requests.load(Ordering::SeqCst),
            total_failures: self.total_failures.load(Ordering::SeqCst),
            total_successes: self.total_successes.load(Ordering::SeqCst),
        }
    }
}

/// Circuit breaker error
#[derive(Debug, Clone, PartialEq)]
pub enum CircuitBreakerError {
    CircuitOpen,
    ExecutionFailed(String),
}

/// Circuit breaker statistics
#[derive(Debug, Clone)]
pub struct CircuitBreakerStats {
    pub name: String,
    pub state: CircuitState,
    pub failure_count: u32,
    pub success_count: u32,
    pub total_requests: u64,
    pub total_failures: u64,
    pub total_successes: u64,
}

/// Circuit breaker registry
pub struct CircuitBreakerRegistry {
    breakers: RwLock<HashMap<String, Arc<CircuitBreaker>>>,
}

impl CircuitBreakerRegistry {
    /// Create new registry
    pub fn new() -> Self {
        Self {
            breakers: RwLock::new(HashMap::new()),
        }
    }

    /// Get or create circuit breaker
    pub fn get_or_create(&self, name: &str, config: CircuitBreakerConfig) -> Arc<CircuitBreaker> {
        if let Ok(breakers) = self.breakers.read() {
            if let Some(breaker) = breakers.get(name) {
                return breaker.clone();
            }
        }

        if let Ok(mut breakers) = self.breakers.write() {
            let breaker = Arc::new(CircuitBreaker::new(name.to_string(), config));
            breakers.insert(name.to_string(), breaker.clone());
            breaker
        } else {
            Arc::new(CircuitBreaker::new(
                name.to_string(),
                CircuitBreakerConfig::default(),
            ))
        }
    }

    /// Get circuit breaker
    pub fn get(&self, name: &str) -> Option<Arc<CircuitBreaker>> {
        if let Ok(breakers) = self.breakers.read() {
            breakers.get(name).cloned()
        } else {
            None
        }
    }

    /// Get all circuit breakers
    pub fn get_all(&self) -> Vec<Arc<CircuitBreaker>> {
        if let Ok(breakers) = self.breakers.read() {
            breakers.values().cloned().collect()
        } else {
            Vec::new()
        }
    }
}

impl Default for CircuitBreakerRegistry {
    fn default() -> Self {
        Self::new()
    }
}

/// Retry configuration
#[derive(Debug, Clone)]
pub struct RetryConfig {
    /// Maximum retry attempts
    pub max_attempts: u32,
    /// Base delay between retries
    pub base_delay: Duration,
    /// Maximum delay between retries
    pub max_delay: Duration,
    /// Exponential backoff multiplier
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(30),
            backoff_multiplier: 2.0,
        }
    }
}

/// Retry executor
pub struct RetryExecutor;

impl RetryExecutor {
    /// Execute with retry
    pub fn execute<F, T>(config: &RetryConfig, f: F) -> Result<T, RetryError>
    where
        F: Fn() -> Result<T, String>,
    {
        let mut attempts = 0;
        let mut delay = config.base_delay;

        loop {
            attempts += 1;

            match f() {
                Ok(result) => return Ok(result),
                Err(e) => {
                    if attempts >= config.max_attempts {
                        return Err(RetryError::MaxAttemptsExceeded(attempts, e));
                    }

                    std::thread::sleep(delay);

                    // Calculate next delay with exponential backoff
                    let next_delay = Duration::from_millis(
                        (delay.as_millis() as f64 * config.backoff_multiplier) as u64,
                    );
                    delay = std::cmp::min(next_delay, config.max_delay);
                }
            }
        }
    }
}

/// Retry error
#[derive(Debug, Clone, PartialEq)]
pub enum RetryError {
    MaxAttemptsExceeded(u32, String),
}

/// Timeout configuration
#[derive(Debug, Clone)]
pub struct TimeoutConfig {
    pub duration: Duration,
}

impl Default for TimeoutConfig {
    fn default() -> Self {
        Self {
            duration: Duration::from_secs(30),
        }
    }
}

/// Backpressure configuration
#[derive(Debug, Clone)]
pub struct BackpressureConfig {
    /// Maximum concurrent requests
    pub max_concurrent: usize,
    /// Maximum queue size
    pub max_queue_size: usize,
    /// Queue timeout
    pub queue_timeout: Duration,
}

impl Default for BackpressureConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 100,
            max_queue_size: 1000,
            queue_timeout: Duration::from_secs(60),
        }
    }
}

/// Backpressure controller
pub struct BackpressureController {
    config: BackpressureConfig,
    concurrent: AtomicU32,
    queued: AtomicU32,
}

impl BackpressureController {
    /// Create new controller
    pub fn new(config: BackpressureConfig) -> Self {
        Self {
            config,
            concurrent: AtomicU32::new(0),
            queued: AtomicU32::new(0),
        }
    }

    /// Try to acquire slot
    pub fn try_acquire(&self) -> Result<BackpressureGuard<'_>, BackpressureError> {
        let concurrent = self.concurrent.load(Ordering::SeqCst);
        let queued = self.queued.load(Ordering::SeqCst);

        if concurrent as usize >= self.config.max_concurrent {
            if queued as usize >= self.config.max_queue_size {
                return Err(BackpressureError::QueueFull);
            }

            self.queued.fetch_add(1, Ordering::SeqCst);

            // Wait for slot (with timeout)
            let start = Instant::now();
            while self.concurrent.load(Ordering::SeqCst) as usize >= self.config.max_concurrent {
                if start.elapsed() >= self.config.queue_timeout {
                    self.queued.fetch_sub(1, Ordering::SeqCst);
                    return Err(BackpressureError::QueueTimeout);
                }
                std::thread::sleep(Duration::from_millis(10));
            }

            self.queued.fetch_sub(1, Ordering::SeqCst);
        }

        self.concurrent.fetch_add(1, Ordering::SeqCst);

        Ok(BackpressureGuard { controller: self })
    }

    /// Release slot
    fn release(&self) {
        self.concurrent.fetch_sub(1, Ordering::SeqCst);
    }

    /// Get current load
    pub fn get_load(&self) -> LoadMetrics {
        LoadMetrics {
            concurrent: self.concurrent.load(Ordering::SeqCst),
            queued: self.queued.load(Ordering::SeqCst),
            max_concurrent: self.config.max_concurrent as u32,
            max_queue: self.config.max_queue_size as u32,
        }
    }
}

/// Backpressure guard (auto-release on drop)
pub struct BackpressureGuard<'a> {
    controller: &'a BackpressureController,
}

impl<'a> Drop for BackpressureGuard<'a> {
    fn drop(&mut self) {
        self.controller.release();
    }
}

impl<'a> std::ops::Deref for BackpressureGuard<'a> {
    type Target = BackpressureController;

    fn deref(&self) -> &Self::Target {
        self.controller
    }
}

/// Backpressure error
#[derive(Debug, Clone, PartialEq)]
pub enum BackpressureError {
    QueueFull,
    QueueTimeout,
}

/// Load metrics
#[derive(Debug, Clone)]
pub struct LoadMetrics {
    pub concurrent: u32,
    pub queued: u32,
    pub max_concurrent: u32,
    pub max_queue: u32,
}

impl LoadMetrics {
    /// Calculate load percentage
    pub fn load_percentage(&self) -> f64 {
        let total_capacity = self.max_concurrent + self.max_queue;
        let current_load = self.concurrent + self.queued;

        if total_capacity == 0 {
            0.0
        } else {
            (current_load as f64 / total_capacity as f64) * 100.0
        }
    }

    /// Check if under pressure
    pub fn is_under_pressure(&self) -> bool {
        self.concurrent >= self.max_concurrent || self.queued > 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circuit_breaker_closed() {
        let cb = CircuitBreaker::new("test".to_string(), CircuitBreakerConfig::default());

        assert_eq!(cb.get_state(), CircuitState::Closed);
        assert!(cb.can_execute());

        // Record successes
        for _ in 0..10 {
            cb.record_success();
        }

        assert_eq!(cb.get_state(), CircuitState::Closed);
    }

    #[test]
    fn test_circuit_breaker_opens() {
        let config = CircuitBreakerConfig {
            failure_threshold: 3,
            success_threshold: 2,
            timeout_duration: Duration::from_secs(30),
        };

        let cb = CircuitBreaker::new("test".to_string(), config);

        // Record failures to open circuit
        for _ in 0..3 {
            cb.record_failure();
        }

        assert_eq!(cb.get_state(), CircuitState::Open);
        assert!(!cb.can_execute());
    }

    #[test]
    fn test_circuit_breaker_half_open() {
        let config = CircuitBreakerConfig {
            failure_threshold: 2,
            success_threshold: 2,
            timeout_duration: Duration::from_millis(1),
        };

        let cb = CircuitBreaker::new("test".to_string(), config);

        // Open circuit
        cb.record_failure();
        cb.record_failure();
        assert_eq!(cb.get_state(), CircuitState::Open);

        // Wait for timeout
        std::thread::sleep(Duration::from_millis(10));

        // Should transition to half-open
        assert!(cb.can_execute());
        assert_eq!(cb.get_state(), CircuitState::HalfOpen);
    }

    #[test]
    fn test_circuit_breaker_registry() {
        let registry = CircuitBreakerRegistry::new();

        let cb1 = registry.get_or_create("test1", CircuitBreakerConfig::default());
        let cb2 = registry.get_or_create("test1", CircuitBreakerConfig::default());

        // Should return same instance
        assert!(Arc::ptr_eq(&cb1, &cb2));

        let cb3 = registry.get_or_create("test2", CircuitBreakerConfig::default());
        assert!(!Arc::ptr_eq(&cb1, &cb3));
    }

    #[test]
    fn test_retry_executor() {
        let config = RetryConfig {
            max_attempts: 3,
            base_delay: Duration::from_millis(1),
            max_delay: Duration::from_millis(10),
            backoff_multiplier: 2.0,
        };

        // Test success
        let result = RetryExecutor::execute(&config, || Ok::<_, String>(42));
        assert_eq!(result, Ok(42));

        // Test failure after max attempts
        let attempts = std::cell::Cell::new(0);
        let result = RetryExecutor::execute(&config, || -> Result<i32, String> {
            attempts.set(attempts.get() + 1);
            Err("always fails".to_string())
        });

        assert!(result.is_err());
        assert_eq!(attempts.get(), 3);
    }

    #[test]
    fn test_backpressure() {
        let config = BackpressureConfig {
            max_concurrent: 1,
            max_queue_size: 1,
            queue_timeout: Duration::from_millis(10),
        };

        let controller = BackpressureController::new(config);

        // Acquire first slot
        let guard1 = controller.try_acquire();
        assert!(guard1.is_ok());

        // Second acquire should queue then timeout
        let guard2 = controller.try_acquire();
        assert!(guard2.is_err());

        // Release first guard
        drop(guard1);

        // Now should be able to acquire
        std::thread::sleep(Duration::from_millis(20));
        let guard3 = controller.try_acquire();
        assert!(guard3.is_ok());
    }

    #[test]
    fn test_load_metrics() {
        let metrics = LoadMetrics {
            concurrent: 50,
            queued: 25,
            max_concurrent: 100,
            max_queue: 100,
        };

        assert_eq!(metrics.load_percentage(), 37.5);
        assert!(metrics.is_under_pressure());
    }
}
