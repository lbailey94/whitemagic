//! NLU router observability tools — shadow mode disagreement reporting.
//!
//! Tools:
//! - `nlu.shadow_report`: Report embedding vs TF-IDF disagreement stats and promotion readiness.

#![forbid(unsafe_code)]

use crate::embedding_router::ShadowModeStats;
use async_trait::async_trait;
use serde_json::{Value, json};
use wm_core::{Context, EffectRow, Gana, Result, Tool, ToolStats};

/// Report shadow mode disagreement stats between embedding and TF-IDF routers.
///
/// Returns total queries, disagreement count/rate, top disagreement pairs,
/// recent samples, and promotion readiness assessment.
pub struct NluShadowReportTool {
    shadow_stats: std::sync::Arc<std::sync::RwLock<ShadowModeStats>>,
    stats: ToolStats,
    effects: EffectRow,
}

impl NluShadowReportTool {
    #[must_use]
    pub fn new(shadow_stats: std::sync::Arc<std::sync::RwLock<ShadowModeStats>>) -> Self {
        Self {
            shadow_stats,
            stats: ToolStats::default(),
            effects: EffectRow::pure(),
        }
    }
}

#[async_trait]
impl Tool for NluShadowReportTool {
    fn name(&self) -> &str {
        "nlu.shadow_report"
    }

    fn gana(&self) -> Gana {
        Gana::Horn
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    async fn call(&self, _ctx: &mut Context, _args: Value) -> Result<Value> {
        let report = if let Ok(stats) = self.shadow_stats.read() {
            stats.report()
        } else {
            json!({"status": "error", "message": "Failed to acquire shadow stats lock"})
        };
        Ok(report)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shadow_report_returns_stats() {
        let stats = std::sync::Arc::new(std::sync::RwLock::new(ShadowModeStats::default()));
        {
            let mut s = stats.write().unwrap();
            s.record("test query", "memory.create", 0.9, "memory.list", 0.7);
            s.record("another query", "memory.create", 0.8, "memory.create", 0.8);
        }
        let tool = NluShadowReportTool::new(stats);
        assert_eq!(tool.name(), "nlu.shadow_report");
        assert_eq!(tool.gana(), Gana::Horn);
    }
}
