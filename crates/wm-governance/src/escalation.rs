//! Dharma escalation — the human review queue for ambiguous verdicts.
//!
//! Port of the v26 escalation pipeline's review surface: when the policy
//! tier returns an ambiguous verdict (Advise / Correct), an action can be
//! escalated to a human review queue. Reviews are resolved with an explicit
//! decision (allow / warn / block) and a human-assigned score; the resolved
//! decisions feed back into the record so operators can audit the pipeline.
//!
//! The v26 pipeline had four tiers (policy → heuristic → LLM → human). v5
//! implements the policy and heuristic tiers natively; the human tier is
//! this queue. The LLM tier is intentionally omitted — v5 is local-first.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use serde_json::{Value, json};

/// Status of a review item.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ReviewStatus {
    /// Awaiting a human decision.
    Pending,
    /// Resolved by a human.
    Resolved,
}

impl ReviewStatus {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Resolved => "resolved",
        }
    }
}

/// A single escalated action awaiting (or given) a human decision.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReviewItem {
    /// Stable identifier (e.g. "review-0001").
    pub id: String,
    /// The tool being escalated.
    pub tool: String,
    /// Human-readable action description.
    pub action: String,
    /// The ambiguous verdict that triggered escalation.
    pub verdict: String,
    /// Why it was escalated.
    pub reason: String,
    /// Epoch seconds when the review was created.
    pub created_at: i64,
    /// Pending / resolved.
    pub status: ReviewStatus,
    /// Human decision once resolved: "allow", "warn", or "block".
    pub decision: Option<String>,
    /// Human-assigned score (0.0–1.0).
    pub score: Option<f64>,
}

/// The escalation review queue — persistable via [`to_json`](Self::to_json)
/// / [`from_json`](Self::from_json).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EscalationQueue {
    /// All review items (pending and resolved).
    pub items: Vec<ReviewItem>,
    /// Sequence counter for review IDs.
    next_id: u64,
}

impl EscalationQueue {
    /// Create an empty queue.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Escalate an action to the human review queue.
    pub fn escalate(
        &mut self,
        tool: &str,
        action: &str,
        verdict: &str,
        reason: &str,
    ) -> ReviewItem {
        let id = format!("review-{:04}", self.next_id);
        self.next_id += 1;
        let item = ReviewItem {
            id,
            tool: tool.to_string(),
            action: action.to_string(),
            verdict: verdict.to_string(),
            reason: reason.to_string(),
            created_at: chrono::Utc::now().timestamp(),
            status: ReviewStatus::Pending,
            decision: None,
            score: None,
        };
        self.items.push(item.clone());
        item
    }

    /// List pending review items (oldest first).
    #[must_use]
    pub fn pending(&self) -> Vec<ReviewItem> {
        self.items
            .iter()
            .filter(|i| i.status == ReviewStatus::Pending)
            .cloned()
            .collect()
    }

    /// All review items (pending and resolved), newest first.
    #[must_use]
    pub fn all(&self) -> Vec<ReviewItem> {
        let mut items = self.items.clone();
        items.reverse();
        items
    }

    /// Resolve a pending review with a decision and score.
    ///
    /// `decision` must be one of "allow", "warn", "block".
    pub fn resolve(
        &mut self,
        review_id: &str,
        decision: &str,
        score: f64,
    ) -> Result<ReviewItem, String> {
        if !matches!(decision, "allow" | "warn" | "block") {
            return Err(format!(
                "decision must be 'allow', 'warn', or 'block', got '{decision}'"
            ));
        }
        let item = self
            .items
            .iter_mut()
            .find(|i| i.id == review_id)
            .ok_or_else(|| format!("unknown review id: {review_id}"))?;
        if item.status != ReviewStatus::Pending {
            return Err(format!("review {} already resolved", item.id));
        }
        item.status = ReviewStatus::Resolved;
        item.decision = Some(decision.to_string());
        item.score = Some(score.clamp(0.0, 1.0));
        Ok(item.clone())
    }

    /// Aggregate queue status.
    #[must_use]
    pub fn status(&self) -> Value {
        let pending = self
            .items
            .iter()
            .filter(|i| i.status == ReviewStatus::Pending)
            .count();
        let resolved = self.items.len() - pending;
        let decisions = self.items.iter().filter_map(|i| i.decision.clone()).fold(
            std::collections::BTreeMap::new(),
            |mut acc, d| {
                *acc.entry(d).or_insert(0usize) += 1;
                acc
            },
        );
        json!({
            "status": "success",
            "total": self.items.len(),
            "pending": pending,
            "resolved": resolved,
            "decisions": decisions,
        })
    }

    /// Serialize to JSON for persistence.
    #[must_use]
    pub fn to_json(&self) -> Value {
        serde_json::to_value(self).unwrap_or_else(|_| json!({}))
    }

    /// Restore from persisted JSON.
    pub fn from_json(&mut self, value: &Value) -> Result<(), String> {
        let restored: Self = serde_json::from_value(value.clone()).map_err(|e| e.to_string())?;
        *self = restored;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escalate_creates_pending_review() {
        let mut queue = EscalationQueue::new();
        let item = queue.escalate(
            "memory.delete",
            "Delete memory 123 without purpose",
            "Correct",
            "autonomous delete without declared purpose",
        );
        assert_eq!(item.id, "review-0000");
        assert_eq!(item.status, ReviewStatus::Pending);
        assert!(item.decision.is_none());
        assert_eq!(queue.pending().len(), 1);
    }

    #[test]
    fn resolve_applies_decision_and_score() {
        let mut queue = EscalationQueue::new();
        let item = queue.escalate("memory.delete", "delete 123", "Correct", "no purpose");
        let resolved = queue.resolve(&item.id, "block", 0.9).unwrap();
        assert_eq!(resolved.status, ReviewStatus::Resolved);
        assert_eq!(resolved.decision.as_deref(), Some("block"));
        assert_eq!(resolved.score, Some(0.9));
        assert!(queue.pending().is_empty());
        assert_eq!(queue.status()["resolved"], 1);
    }

    #[test]
    fn cannot_resolve_twice_or_unknown() {
        let mut queue = EscalationQueue::new();
        let item = queue.escalate("memory.delete", "delete 123", "Correct", "no purpose");
        queue.resolve(&item.id, "allow", 0.5).unwrap();
        assert!(queue.resolve(&item.id, "warn", 0.5).is_err());
        assert!(queue.resolve("review-9999", "allow", 0.5).is_err());
        assert!(queue.resolve(&item.id, "bogus", 0.5).is_err());
    }

    #[test]
    fn json_roundtrip() {
        let mut queue = EscalationQueue::new();
        let item = queue.escalate("memory.delete", "delete 123", "Correct", "no purpose");
        queue.resolve(&item.id, "warn", 0.7).unwrap();
        let json = queue.to_json();
        let mut restored = EscalationQueue::new();
        restored.from_json(&json).unwrap();
        assert_eq!(restored.items.len(), 1);
        assert_eq!(restored.items[0].decision.as_deref(), Some("warn"));
        // IDs continue from the restored counter
        let next = restored.escalate("dharma.rules", "read", "Observe", "audit");
        assert_eq!(next.id, "review-0001");
    }

    #[test]
    fn status_tracks_decisions() {
        let mut queue = EscalationQueue::new();
        let a = queue.escalate("x", "a", "Correct", "r");
        let b = queue.escalate("y", "b", "Correct", "r");
        queue.resolve(&a.id, "allow", 0.8).unwrap();
        queue.resolve(&b.id, "block", 0.6).unwrap();
        let status = queue.status();
        assert_eq!(status["pending"], 0);
        assert_eq!(status["decisions"]["allow"], 1);
        assert_eq!(status["decisions"]["block"], 1);
    }
}
