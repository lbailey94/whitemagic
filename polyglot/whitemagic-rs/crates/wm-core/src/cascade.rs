//! Gan Ying Cascade Accelerator (Rust)
//!
//! High-performance cascade trigger matching for the WhiteMagic resonance bus.
//! Given a table of cascade triggers (trigger_event → target_events) and an
//! incoming event, this module matches triggers in O(n) with early-exit
//! and returns the list of cascaded events that should be emitted.
//!
//! The Python GanYingBus._process_cascades() delegates to this module via
//! the JSON stdio bridge when available, falling back to pure Python otherwise.

use serde::{Deserialize, Serialize};

/// A cascade trigger: when `trigger_event` fires, emit all `target_events`
/// with confidence multiplied by `amplification` (capped at 1.0).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CascadeTriggerDef {
    pub trigger_event: String,
    pub target_events: Vec<String>,
    pub amplification: f64,
    pub max_cascade_depth: u8,
}

/// An incoming event to match against triggers.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CascadeEvent {
    pub event_type: String,
    pub confidence: f64,
    pub cascade_depth: u8,
}

/// A cascaded event to be emitted back into the bus.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CascadedEvent {
    pub event_type: String,
    pub confidence: f64,
    pub cascade_depth: u8,
    pub origin: String,
}

/// Match an event against a trigger table and return all cascaded events.
///
/// This is a flat scan — no recursion. The Python side handles recursive
/// emission by calling this function for each cascaded event until no
/// more triggers match (or depth limit is reached).
///
/// Returns an empty vec if no triggers match or depth limit is exceeded.
pub fn match_cascades(
    event: &CascadeEvent,
    triggers: &[CascadeTriggerDef],
) -> Vec<CascadedEvent> {
    let mut results = Vec::new();

    for trigger in triggers {
        // Fast path: skip if event type doesn't match
        if trigger.trigger_event != event.event_type {
            continue;
        }

        // Check depth limit
        if event.cascade_depth >= trigger.max_cascade_depth {
            continue;
        }

        let new_depth = event.cascade_depth + 1;
        let new_confidence = (event.confidence * trigger.amplification).min(1.0);

        for target in &trigger.target_events {
            results.push(CascadedEvent {
                event_type: target.clone(),
                confidence: new_confidence,
                cascade_depth: new_depth,
                origin: event.event_type.clone(),
            });
        }
    }

    results
}

/// Verify that a cascade trigger table has no cycles.
///
/// Builds a directed graph from trigger → target edges and runs
/// a DFS-based cycle detection. Returns a list of cycles found
/// (each cycle is a vec of event type names).
pub fn detect_cycles(triggers: &[CascadeTriggerDef]) -> Vec<Vec<String>> {
    use std::collections::{HashMap, HashSet};

    // Build adjacency list
    let mut graph: HashMap<String, Vec<String>> = HashMap::new();
    for trigger in triggers {
        graph
            .entry(trigger.trigger_event.clone())
            .or_default()
            .extend(trigger.target_events.iter().cloned());
    }

    let mut cycles: Vec<Vec<String>> = Vec::new();
    let mut visited: HashSet<String> = HashSet::new();
    let mut stack: Vec<String> = Vec::new();
    let mut on_stack: HashSet<String> = HashSet::new();

    fn dfs(
        node: &str,
        graph: &HashMap<String, Vec<String>>,
        visited: &mut HashSet<String>,
        stack: &mut Vec<String>,
        on_stack: &mut HashSet<String>,
        cycles: &mut Vec<Vec<String>>,
    ) {
        if on_stack.contains(node) {
            // Found a cycle — extract it from the stack
            if let Some(start) = stack.iter().position(|n| n == node) {
                let cycle: Vec<String> = stack[start..].to_vec();
                cycles.push(cycle);
            }
            return;
        }
        if visited.contains(node) {
            return;
        }

        visited.insert(node.to_string());
        on_stack.insert(node.to_string());
        stack.push(node.to_string());

        if let Some(neighbors) = graph.get(node) {
            for neighbor in neighbors {
                dfs(neighbor, graph, visited, stack, on_stack, cycles);
            }
        }

        on_stack.remove(node);
        stack.pop();
    }

    let nodes: Vec<String> = graph.keys().cloned().collect();
    for node in nodes {
        dfs(
            &node,
            &graph,
            &mut visited,
            &mut stack,
            &mut on_stack,
            &mut cycles,
        );
    }

    cycles
}

/// Check if the cascade table is safe (no cycles that could cause infinite loops).
pub fn is_safe(triggers: &[CascadeTriggerDef]) -> bool {
    detect_cycles(triggers).is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_match_simple_cascade() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "joy_triggered".to_string(),
            target_events: vec!["love_activated".to_string()],
            amplification: 1.2,
            max_cascade_depth: 3,
        }];
        let event = CascadeEvent {
            event_type: "joy_triggered".to_string(),
            confidence: 0.8,
            cascade_depth: 0,
        };
        let results = match_cascades(&event, &triggers);
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].event_type, "love_activated");
        assert!((results[0].confidence - 0.96).abs() < 0.01);
        assert_eq!(results[0].cascade_depth, 1);
    }

    #[test]
    fn test_no_match_different_event() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "joy_triggered".to_string(),
            target_events: vec!["love_activated".to_string()],
            amplification: 1.0,
            max_cascade_depth: 3,
        }];
        let event = CascadeEvent {
            event_type: "threat_detected".to_string(),
            confidence: 0.8,
            cascade_depth: 0,
        };
        let results = match_cascades(&event, &triggers);
        assert!(results.is_empty());
    }

    #[test]
    fn test_depth_limit() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "joy_triggered".to_string(),
            target_events: vec!["love_activated".to_string()],
            amplification: 1.0,
            max_cascade_depth: 2,
        }];
        let event = CascadeEvent {
            event_type: "joy_triggered".to_string(),
            confidence: 0.8,
            cascade_depth: 2, // Already at max
        };
        let results = match_cascades(&event, &triggers);
        assert!(results.is_empty());
    }

    #[test]
    fn test_confidence_capped_at_1() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "joy_triggered".to_string(),
            target_events: vec!["love_activated".to_string()],
            amplification: 1.5,
            max_cascade_depth: 3,
        }];
        let event = CascadeEvent {
            event_type: "joy_triggered".to_string(),
            confidence: 0.8,
            cascade_depth: 0,
        };
        let results = match_cascades(&event, &triggers);
        assert_eq!(results.len(), 1);
        assert!((results[0].confidence - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_detect_cycle() {
        let triggers = vec![
            CascadeTriggerDef {
                trigger_event: "a".to_string(),
                target_events: vec!["b".to_string()],
                amplification: 1.0,
                max_cascade_depth: 3,
            },
            CascadeTriggerDef {
                trigger_event: "b".to_string(),
                target_events: vec!["a".to_string()],
                amplification: 1.0,
                max_cascade_depth: 3,
            },
        ];
        let cycles = detect_cycles(&triggers);
        assert!(!cycles.is_empty());
        assert!(!is_safe(&triggers));
    }

    #[test]
    fn test_no_cycle_is_safe() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "a".to_string(),
            target_events: vec!["b".to_string(), "c".to_string()],
            amplification: 1.0,
            max_cascade_depth: 3,
        }];
        assert!(is_safe(&triggers));
    }

    #[test]
    fn test_multiple_targets() {
        let triggers = vec![CascadeTriggerDef {
            trigger_event: "love_activated".to_string(),
            target_events: vec!["connection_deepened".to_string(), "compassion_felt".to_string()],
            amplification: 1.3,
            max_cascade_depth: 3,
        }];
        let event = CascadeEvent {
            event_type: "love_activated".to_string(),
            confidence: 0.5,
            cascade_depth: 0,
        };
        let results = match_cascades(&event, &triggers);
        assert_eq!(results.len(), 2);
        assert!((results[0].confidence - 0.65).abs() < 0.01);
    }
}
