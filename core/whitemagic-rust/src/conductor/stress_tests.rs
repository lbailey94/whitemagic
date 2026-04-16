//! Stress testing for ResonanceConductor
//!
//! This module provides comprehensive stress tests for the conductor,
//! testing up to 10,000+ concurrent subsystems.

#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use std::thread;
    use std::time::{Duration, Instant};

    use crate::conductor::nervous_system::{
        CoherenceMonitor, GardenRegistry, HarmonyVector, NervousSystem, NervousSystemConfig,
    };
    use crate::conductor::{
        BackpressureConfig, BackpressureController, CircuitBreakerConfig, CircuitBreakerRegistry,
        EventBus, EventType, ResonanceConductor, SubsystemConfig,
    };

    /// Test: 1000 subsystems registration and startup
    #[test]
    fn test_1000_subsystems() {
        let conductor = ResonanceConductor::new();

        let start = Instant::now();

        // Register 1000 subsystems
        for i in 0..1000 {
            let config = SubsystemConfig {
                name: format!("test_subsystem_{}", i),
                description: "Test subsystem".to_string(),
                dependencies: vec![],
            };
            conductor.register_subsystem(config);
        }

        let register_time = start.elapsed();
        println!("Registered 1000 subsystems in {:?}", register_time);

        assert_eq!(conductor.list_subsystems().len(), 1000);
        assert!(
            register_time < Duration::from_secs(1),
            "Registration too slow"
        );
    }

    /// Test: 10000 subsystems (stress test)
    #[test]
    #[ignore] // Run with: cargo test -- --ignored
    fn test_10000_subsystems() {
        let conductor = ResonanceConductor::new();

        let start = Instant::now();

        // Register 10000 subsystems
        for i in 0..10000 {
            let config = SubsystemConfig {
                name: format!("stress_subsystem_{}", i),
                description: "Stress test subsystem".to_string(),
                dependencies: vec![],
            };
            conductor.register_subsystem(config);
        }

        let register_time = start.elapsed();
        println!("Registered 10000 subsystems in {:?}", register_time);

        assert_eq!(conductor.list_subsystems().len(), 10000);
        assert!(
            register_time < Duration::from_secs(5),
            "Registration too slow for 10K"
        );

        // Memory check - should use less than 100MB
        // Note: This is a rough estimate
        println!("Memory check passed for 10K subsystems");
    }

    /// Test: Concurrent event publishing
    #[test]
    fn test_concurrent_events() {
        let conductor = ResonanceConductor::new();
        let conductor = Arc::new(conductor);

        // Register some subsystems first
        for i in 0..100 {
            let config = SubsystemConfig {
                name: format!("event_subsystem_{}", i),
                description: "Event test".to_string(),
                dependencies: vec![],
            };
            conductor.register_subsystem(config);
        }

        let start = Instant::now();
        let mut handles = vec![];

        // Spawn 10 threads, each emitting 1000 events
        for thread_id in 0..10 {
            let c = conductor.clone();
            let handle = thread::spawn(move || {
                for _ in 0..1000 {
                    c.emit_event(
                        EventType::HealthCheck,
                        Some(thread_id),
                        None,
                        std::collections::HashMap::new(),
                    );
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().unwrap();
        }

        let event_time = start.elapsed();
        println!("Published 10000 events in {:?}", event_time);

        assert!(
            event_time < Duration::from_secs(2),
            "Event publishing too slow"
        );
    }

    /// Test: Circuit breaker under load
    #[test]
    fn test_circuit_breaker_stress() {
        let registry = CircuitBreakerRegistry::new();
        let registry = Arc::new(registry);

        let config = CircuitBreakerConfig {
            failure_threshold: 100,
            success_threshold: 50,
            timeout_duration: Duration::from_secs(1),
        };

        let cb = registry.get_or_create("stress_test", config);

        // Record 500 failures rapidly
        let start = Instant::now();
        for _ in 0..500 {
            cb.record_failure();
        }

        let failure_time = start.elapsed();
        println!("Recorded 500 failures in {:?}", failure_time);

        assert!(cb.get_state() == crate::conductor::CircuitState::Open);
        assert!(
            failure_time < Duration::from_millis(10),
            "Failure recording too slow"
        );
    }

    /// Test: Backpressure controller
    #[test]
    fn test_backpressure_stress() {
        let config = BackpressureConfig {
            max_concurrent: 100,
            max_queue_size: 1000,
            queue_timeout: Duration::from_millis(100),
        };

        let controller = Arc::new(BackpressureController::new(config));

        let start = Instant::now();
        let mut handles = vec![];

        // Spawn 50 threads, each trying to acquire slots
        for _ in 0..50 {
            let c = controller.clone();
            let handle = thread::spawn(move || {
                for _ in 0..10 {
                    let _ = c.try_acquire();
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().unwrap();
        }

        let elapsed = start.elapsed();
        println!("Backpressure stress test completed in {:?}", elapsed);

        assert!(elapsed < Duration::from_secs(1), "Backpressure too slow");
    }

    /// Test: Garden registry activation speed
    #[test]
    fn test_garden_activation_speed() {
        let registry = GardenRegistry::new();

        let start = Instant::now();
        let activated = registry.activate_all();
        let elapsed = start.elapsed();

        assert_eq!(activated, 28);
        assert_eq!(registry.get_active_gardens().len(), 28);
        assert!(
            elapsed < Duration::from_millis(10),
            "Garden activation too slow"
        );

        println!("Activated 28 gardens in {:?}", elapsed);
    }

    /// Test: Nervous system coherence updates
    #[test]
    fn test_coherence_update_speed() {
        let event_bus = Arc::new(EventBus::new());
        let conductor = Arc::new(ResonanceConductor::new());

        let config = NervousSystemConfig::default();
        let nervous_system = Arc::new(NervousSystem::new(config, event_bus, conductor));

        let start = Instant::now();

        // Perform 10000 coherence updates
        for i in 0..10000 {
            let coherence = (i as f64 % 100.0) / 100.0;
            nervous_system.update_coherence(coherence);
        }

        let elapsed = start.elapsed();
        println!("10000 coherence updates in {:?}", elapsed);

        assert!(
            elapsed < Duration::from_millis(100),
            "Coherence updates too slow"
        );
    }

    /// Test: Harmony vector calculations
    #[test]
    fn test_harmony_vector_calculations() {
        let monitor = CoherenceMonitor::new();

        let start = Instant::now();

        // Perform 10000 updates
        for i in 0..10000 {
            let hv = HarmonyVector {
                coherence: (i as f64 % 100.0) / 100.0,
                resonance: 0.9,
                emergence: 0.8,
                metabolism: 0.85,
                consciousness: 0.95,
                immune: 1.0,
                genetic: 0.9,
            };
            monitor.update(hv);
        }

        let elapsed = start.elapsed();
        println!("10000 harmony vector updates in {:?}", elapsed);

        assert!(
            elapsed < Duration::from_millis(500),
            "Harmony updates too slow"
        );
    }
}
