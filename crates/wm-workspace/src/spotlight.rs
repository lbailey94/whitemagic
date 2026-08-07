//! Spotlight mechanism — time-decayed attention arbitration.
//!
//! Ported from v2's `salience_arbiter.py`. The spotlight tracks which core
//! currently holds attention. The spotlight strength decays exponentially
//! over time: `strength = 0.5^(age / half_life)`.
//!
//! High-salience events (>0.8 composite) can preempt the current spotlight
//! immediately, bypassing the normal arbitration cycle.

use crate::event::{CoreId, WorkspaceEvent};
use std::time::{Duration, Instant};

/// Default half-life for spotlight decay (5 seconds).
pub const DEFAULT_HALF_LIFE: Duration = Duration::from_secs(5);

/// An entry in the spotlight — the current holder of attention.
#[derive(Debug, Clone)]
pub struct SpotlightEntry {
    /// The core currently holding the spotlight.
    pub core: CoreId,
    /// The event that won the spotlight.
    pub winning_event_type: crate::event::EventType,
    /// The salience score that won.
    pub salience: crate::salience::Salience,
    /// When this spotlight entry was created.
    pub timestamp: Instant,
    /// How many events were considered for this arbitration cycle.
    pub candidates: usize,
}

impl SpotlightEntry {
    /// Compute the current spotlight strength (0.0 to 1.0).
    ///
    /// Uses exponential decay: `strength = 0.5^(age / half_life)`.
    /// At `half_life` age, strength is 0.5. At 2× half_life, strength is 0.25.
    #[must_use]
    pub fn strength(&self, half_life: Duration) -> f32 {
        let age = self.timestamp.elapsed();
        let base = self.salience.composite();
        if age.is_zero() {
            return base;
        }
        let half_life_secs = half_life.as_secs_f64();
        if half_life_secs <= 0.0 {
            return 0.0;
        }
        let age_secs = age.as_secs_f64();
        let decay = 0.5_f64.powf(age_secs / half_life_secs) as f32;
        base * decay
    }

    /// Age of this spotlight entry.
    #[must_use]
    pub fn age(&self) -> Duration {
        self.timestamp.elapsed()
    }
}

/// The spotlight tracker — manages which core currently holds attention.
///
/// The spotlight decays over time. When a new event arrives with higher
/// salience than the current spotlight strength, the spotlight transfers
/// to the new event's core.
pub struct Spotlight {
    /// Current spotlight entry (if any).
    current: Option<SpotlightEntry>,
    /// Half-life for decay.
    half_life: Duration,
    /// Total number of spotlight transfers.
    transfer_count: u64,
    /// Total number of arbitration cycles.
    arbitration_count: u64,
    /// Per-core spotlight hold counts.
    core_holds: std::collections::HashMap<CoreId, u64>,
}

impl std::fmt::Debug for Spotlight {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Spotlight")
            .field("current", &self.current)
            .field("half_life", &self.half_life)
            .field("transfer_count", &self.transfer_count)
            .field("arbitration_count", &self.arbitration_count)
            .finish_non_exhaustive()
    }
}

impl Default for Spotlight {
    fn default() -> Self {
        Self::new(DEFAULT_HALF_LIFE)
    }
}

impl Spotlight {
    /// Create a new spotlight tracker with the given half-life.
    #[must_use]
    pub fn new(half_life: Duration) -> Self {
        Self {
            current: None,
            half_life,
            transfer_count: 0,
            arbitration_count: 0,
            core_holds: std::collections::HashMap::new(),
        }
    }

    /// Get the current spotlight entry (if any).
    #[must_use]
    pub const fn current(&self) -> Option<&SpotlightEntry> {
        self.current.as_ref()
    }

    /// Get the current spotlight strength (0.0 to 1.0).
    #[must_use]
    pub fn strength(&self) -> f32 {
        self.current
            .as_ref()
            .map_or(0.0, |e| e.strength(self.half_life))
    }

    /// Get the core currently holding the spotlight (if any).
    #[must_use]
    pub fn current_core(&self) -> Option<CoreId> {
        self.current.as_ref().map(|e| e.core)
    }

    /// Get the total number of spotlight transfers.
    #[must_use]
    pub const fn transfer_count(&self) -> u64 {
        self.transfer_count
    }

    /// Get the total number of arbitration cycles.
    #[must_use]
    pub const fn arbitration_count(&self) -> u64 {
        self.arbitration_count
    }

    /// Get the number of times a core has held the spotlight.
    #[must_use]
    pub fn core_hold_count(&self, core: CoreId) -> u64 {
        self.core_holds.get(&core).copied().unwrap_or(0)
    }

    /// Arbitrate a new event against the current spotlight.
    ///
    /// Returns `true` if the spotlight was transferred to this event.
    /// The spotlight transfers if:
    /// 1. There is no current spotlight, OR
    /// 2. The event's salience is higher than the current spotlight strength, OR
    /// 3. The event's salience is high (>0.8) and preempts the spotlight
    ///
    /// Returns `false` if the current spotlight retains attention.
    pub fn arbitrate(&mut self, event: &WorkspaceEvent) -> bool {
        self.arbitration_count += 1;

        let should_transfer = match &self.current {
            None => true,
            Some(current) => {
                let current_strength = current.strength(self.half_life);
                let event_salience = event.composite_salience();

                // High-salience events preempt immediately
                if event.should_preempt() {
                    true
                } else {
                    // Normal arbitration: compare salience vs decayed strength
                    event_salience > current_strength
                }
            }
        };

        if should_transfer {
            let prev_core = self.current.as_ref().map(|e| e.core);
            self.current = Some(SpotlightEntry {
                core: event.core,
                winning_event_type: event.event_type,
                salience: event.salience,
                timestamp: Instant::now(),
                candidates: 1,
            });
            self.transfer_count += 1;
            *self.core_holds.entry(event.core).or_insert(0) += 1;

            if let Some(prev) = prev_core {
                if prev != event.core {
                    tracing::debug!(
                        from = %prev,
                        to = %event.core,
                        salience = event.composite_salience(),
                        "spotlight transferred"
                    );
                }
            }
            true
        } else {
            false
        }
    }

    /// Arbitrate multiple events at once. The highest-salience event wins.
    ///
    /// Returns the index of the winning event in the slice, or `None` if
    /// no event won the spotlight.
    pub fn arbitrate_batch(&mut self, events: &[WorkspaceEvent]) -> Option<usize> {
        if events.is_empty() {
            return None;
        }

        self.arbitration_count += 1;

        // Find the highest-salience event
        let mut best_idx = 0;
        let mut best_salience = events[0].composite_salience();
        for (i, event) in events.iter().enumerate().skip(1) {
            let s = event.composite_salience();
            if s > best_salience {
                best_salience = s;
                best_idx = i;
            }
        }

        // Check if the best event should win the spotlight
        let should_transfer = match &self.current {
            None => true,
            Some(current) => {
                let current_strength = current.strength(self.half_life);
                events[best_idx].should_preempt() || best_salience > current_strength
            }
        };

        if should_transfer {
            // Update the candidates count
            let mut entry = SpotlightEntry {
                core: events[best_idx].core,
                winning_event_type: events[best_idx].event_type,
                salience: events[best_idx].salience,
                timestamp: Instant::now(),
                candidates: events.len(),
            };
            // Already set candidates above
            entry.candidates = events.len();

            self.current = Some(entry);
            self.transfer_count += 1;
            *self.core_holds.entry(events[best_idx].core).or_insert(0) += 1;
            Some(best_idx)
        } else {
            None
        }
    }

    /// Clear the spotlight (no core holds attention).
    pub const fn clear(&mut self) {
        self.current = None;
    }

    /// Set the half-life for decay.
    pub const fn set_half_life(&mut self, half_life: Duration) {
        self.half_life = half_life;
    }

    /// Get the current half-life.
    #[must_use]
    pub const fn half_life(&self) -> Duration {
        self.half_life
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::salience::Salience;

    fn make_event(core: CoreId, salience: f32) -> WorkspaceEvent {
        WorkspaceEvent::new(
            core,
            crate::event::EventType::AttentionRequest,
            Salience::new(salience, salience, salience),
            serde_json::json!({}),
        )
    }

    #[test]
    fn spotlight_starts_empty() {
        let sp = Spotlight::default();
        assert!(sp.current().is_none());
        assert_eq!(sp.strength(), 0.0);
    }

    #[test]
    fn arbitrate_first_event_wins() {
        let mut sp = Spotlight::default();
        let event = make_event(CoreId::Citta, 0.5);
        assert!(sp.arbitrate(&event));
        assert_eq!(sp.current_core(), Some(CoreId::Citta));
    }

    #[test]
    fn arbitrate_higher_salience_wins() {
        let mut sp = Spotlight::default();
        let low = make_event(CoreId::Citta, 0.3);
        assert!(sp.arbitrate(&low));

        let high = make_event(CoreId::Dream, 0.9);
        assert!(sp.arbitrate(&high));
        assert_eq!(sp.current_core(), Some(CoreId::Dream));
    }

    #[test]
    fn arbitrate_lower_salience_loses() {
        let mut sp = Spotlight::default();
        let high = make_event(CoreId::Citta, 0.9);
        assert!(sp.arbitrate(&high));

        let low = make_event(CoreId::Dream, 0.1);
        assert!(!sp.arbitrate(&low));
        assert_eq!(sp.current_core(), Some(CoreId::Citta));
    }

    #[test]
    fn preempt_high_salience() {
        let mut sp = Spotlight::default();
        // Set up a strong current spotlight
        let strong = make_event(CoreId::Citta, 0.9);
        assert!(sp.arbitrate(&strong));

        // Even though current is strong, a high-salience event preempts
        let preempt = make_event(CoreId::Reflex, 0.95);
        assert!(preempt.should_preempt());
        assert!(sp.arbitrate(&preempt));
        assert_eq!(sp.current_core(), Some(CoreId::Reflex));
    }

    #[test]
    fn spotlight_decay() {
        let mut sp = Spotlight::new(Duration::from_millis(50));
        let event = make_event(CoreId::Citta, 0.8);
        assert!(sp.arbitrate(&event));

        // Immediately, strength should be ~composite (0.8^3 = 0.512)
        let s1 = sp.strength();
        assert!(s1 > 0.48 && s1 < 0.53, "initial strength: {s1}");

        // After half-life, strength should be ~half of composite
        std::thread::sleep(Duration::from_millis(50));
        let s2 = sp.strength();
        assert!(s2 < s1, "strength should decay: {s2} vs {s1}");
        assert!(s2 > 0.15 && s2 < 0.30, "strength after half-life: {s2}");
    }

    #[test]
    fn decayed_spotlight_can_be_overtaken() {
        let mut sp = Spotlight::new(Duration::from_millis(20));
        let high = make_event(CoreId::Citta, 0.8);
        assert!(sp.arbitrate(&high));

        // Wait for decay
        std::thread::sleep(Duration::from_millis(60));

        // A moderate-salience event should now be able to win
        // After 3 half-lives, high's strength = 0.512 * 0.125 = 0.064
        // 0.5^3 = 0.125 > 0.064, so this should overtake
        let low = make_event(CoreId::Dream, 0.5);
        assert!(sp.arbitrate(&low));
        assert_eq!(sp.current_core(), Some(CoreId::Dream));
    }

    #[test]
    fn arbitrate_batch() {
        let mut sp = Spotlight::default();
        let events = vec![
            make_event(CoreId::Citta, 0.3),
            make_event(CoreId::Dream, 0.7),
            make_event(CoreId::Reflex, 0.5),
        ];

        let winner = sp.arbitrate_batch(&events);
        assert_eq!(winner, Some(1)); // Dream has highest salience
        assert_eq!(sp.current_core(), Some(CoreId::Dream));
    }

    #[test]
    fn arbitrate_batch_empty() {
        let mut sp = Spotlight::default();
        assert!(sp.arbitrate_batch(&[]).is_none());
    }

    #[test]
    fn transfer_count() {
        let mut sp = Spotlight::default();
        let e1 = make_event(CoreId::Citta, 0.5);
        let e2 = make_event(CoreId::Dream, 0.7);
        let e3 = make_event(CoreId::Reflex, 0.9);

        assert!(sp.arbitrate(&e1));
        assert!(sp.arbitrate(&e2));
        assert!(sp.arbitrate(&e3));
        assert_eq!(sp.transfer_count(), 3);
    }

    #[test]
    fn core_hold_count() {
        let mut sp = Spotlight::default();
        let e1 = make_event(CoreId::Citta, 0.5);
        let e2 = make_event(CoreId::Dream, 0.7);
        let e3 = make_event(CoreId::Citta, 0.8);

        assert!(sp.arbitrate(&e1));
        assert!(sp.arbitrate(&e2));
        assert!(sp.arbitrate(&e3));
        assert_eq!(sp.core_hold_count(CoreId::Citta), 2);
        assert_eq!(sp.core_hold_count(CoreId::Dream), 1);
    }

    #[test]
    fn clear_spotlight() {
        let mut sp = Spotlight::default();
        let event = make_event(CoreId::Citta, 0.5);
        assert!(sp.arbitrate(&event));
        assert!(sp.current().is_some());

        sp.clear();
        assert!(sp.current().is_none());
    }

    #[test]
    fn spotlight_entry_strength() {
        let entry = SpotlightEntry {
            core: CoreId::Citta,
            winning_event_type: crate::event::EventType::AttentionRequest,
            salience: Salience::new(0.8, 0.8, 0.8),
            timestamp: Instant::now(),
            candidates: 3,
        };
        // Fresh entry should have strength = composite salience
        let s = entry.strength(Duration::from_secs(5));
        assert!(s > 0.49 && s < 0.52, "expected ~0.512, got {s}");
    }

    #[test]
    fn set_half_life() {
        let mut sp = Spotlight::default();
        assert_eq!(sp.half_life(), DEFAULT_HALF_LIFE);
        sp.set_half_life(Duration::from_secs(10));
        assert_eq!(sp.half_life(), Duration::from_secs(10));
    }
}
