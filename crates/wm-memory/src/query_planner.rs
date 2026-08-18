//! Deterministic query-class planner for v6 episodic retrieval.

use crate::episodic_keys::{KeyCategory, extract_episodic_keys};

/// Retrieval class used to select bounded scoring signals.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QueryClass {
    ExactFact,
    Temporal,
    KnowledgeUpdate,
    MultiHop,
    Preference,
    Procedure,
    Summary,
}

/// Planner output: class plus bounded retrieval knobs.
#[derive(Debug, Clone, PartialEq)]
pub struct QueryPlan {
    pub class: QueryClass,
    pub candidate_limit: usize,
    pub key_weight: f32,
}

impl QueryPlan {
    /// Classify a query and return retrieval knobs.
    #[must_use]
    pub fn plan(query: &str, requested_limit: usize) -> Self {
        let class = classify_query(query);
        let requested = requested_limit.max(1);
        match class {
            QueryClass::ExactFact => Self {
                class,
                candidate_limit: requested.saturating_mul(2).max(20),
                key_weight: 0.18,
            },
            QueryClass::Temporal | QueryClass::KnowledgeUpdate => Self {
                class,
                candidate_limit: requested.saturating_mul(3).max(30),
                key_weight: 0.15,
            },
            QueryClass::MultiHop => Self {
                class,
                candidate_limit: requested.saturating_mul(4).max(40),
                key_weight: 0.12,
            },
            QueryClass::Preference => Self {
                class,
                candidate_limit: requested.saturating_mul(3).max(30),
                key_weight: 0.25,
            },
            QueryClass::Procedure => Self {
                class,
                candidate_limit: requested.saturating_mul(3).max(24),
                key_weight: 0.1,
            },
            QueryClass::Summary => Self {
                class,
                candidate_limit: requested.saturating_mul(5).max(50),
                key_weight: 0.05,
            },
        }
    }
}

fn classify_query(query: &str) -> QueryClass {
    let lower = query.to_ascii_lowercase();
    let keys = extract_episodic_keys(query);
    if contains_any(
        &lower,
        &[
            "how do i",
            "how to",
            "procedure",
            "failed",
            "error",
            "workaround",
        ],
    ) {
        return QueryClass::Procedure;
    }
    if contains_any(
        &lower,
        &[
            "now",
            "currently",
            "updated",
            "changed",
            "instead of",
            "anymore",
            "latest",
        ],
    ) {
        return QueryClass::KnowledgeUpdate;
    }
    if keys
        .iter()
        .any(|key| key.category == KeyCategory::Preference)
        || contains_any(&lower, &["favorite", "prefer", "like", "enjoy"])
    {
        return QueryClass::Preference;
    }
    if keys.iter().any(|key| key.category == KeyCategory::Date)
        || contains_any(
            &lower,
            &[
                "when",
                "how long",
                "before",
                "after",
                "last year",
                "yesterday",
            ],
        )
    {
        return QueryClass::Temporal;
    }
    if contains_any(
        &lower,
        &[
            "how many", "both", "and also", "across", "each of", "together",
        ],
    ) {
        return QueryClass::MultiHop;
    }
    if contains_any(&lower, &["summarize", "overview", "all of", "everything"]) {
        return QueryClass::Summary;
    }
    QueryClass::ExactFact
}

fn contains_any(haystack: &str, needles: &[&str]) -> bool {
    needles.iter().any(|needle| haystack.contains(needle))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classifies_temporal_and_preference_queries() {
        assert_eq!(
            QueryPlan::plan("When did I volunteer at the animal shelter?", 10).class,
            QueryClass::Temporal
        );
        assert_eq!(
            QueryPlan::plan("What is my favorite streaming service?", 10).class,
            QueryClass::Preference
        );
    }

    #[test]
    fn classifies_count_as_multihop_and_fact_as_exact() {
        assert_eq!(
            QueryPlan::plan("How many bikes do I own?", 10).class,
            QueryClass::MultiHop
        );
        let plan = QueryPlan::plan("What degree did I graduate with?", 10);
        assert_eq!(plan.class, QueryClass::ExactFact);
        assert!(plan.candidate_limit >= 20);
    }

    #[test]
    fn update_and_procedure_have_distinct_classes() {
        assert_eq!(
            QueryPlan::plan("What is my current internet plan now?", 10).class,
            QueryClass::KnowledgeUpdate
        );
        assert_eq!(
            QueryPlan::plan("How do I recover from a failed bike repair?", 10).class,
            QueryClass::Procedure
        );
    }
}
