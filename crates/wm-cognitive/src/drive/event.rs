//! Drive events — triggers that update drive state.

use serde::{Deserialize, Serialize};

/// Kind of drive event.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DriveEventKind {
    /// A tool executed successfully → satisfaction up, curiosity up.
    ToolSuccess,
    /// A tool execution failed → satisfaction down, caution up.
    ToolError,
    /// Novel input detected → curiosity up.
    NovelInput,
    /// Self-model confidence is low → caution up.
    LowConfidence,
    /// Self-model confidence is high → caution down.
    HighConfidence,
    /// System resources under pressure → energy down.
    ResourcePressure,
    /// System resources recovered → energy up.
    ResourceRelief,
    /// Social interaction occurred → social up.
    SocialInteraction,
    /// Time-based decay tick.
    Decay,
}

/// Source that triggered a drive event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DriveEventSource {
    /// Triggered by the dispatch pipeline.
    Dispatch,
    /// Triggered by the self-model.
    SelfModel,
    /// Triggered by the substrate monitor.
    Substrate,
    /// Triggered by the workspace bus.
    Workspace,
    /// Triggered by the autonomic layer (BitMamba salience).
    Autonomic,
    /// Triggered by a timer/periodic tick.
    Timer,
    /// Triggered manually (e.g., via MCP tool).
    Manual,
}

/// A drive event — a signal that updates one or more drives.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DriveEvent {
    /// What kind of event.
    pub kind: DriveEventKind,
    /// Where the event came from.
    pub source: DriveEventSource,
    /// Optional detail message.
    pub detail: Option<String>,
}

impl DriveEvent {
    /// Create a new drive event with the given kind and default source.
    #[must_use]
    pub const fn new(kind: DriveEventKind) -> Self {
        Self {
            kind,
            source: DriveEventSource::Manual,
            detail: None,
        }
    }

    /// Set the event source.
    #[must_use]
    #[allow(clippy::missing_const_for_fn)]
    pub fn with_source(mut self, source: DriveEventSource) -> Self {
        self.source = source;
        self
    }

    /// Set the detail message.
    #[must_use]
    pub fn with_detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = Some(detail.into());
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn drive_event_new() {
        let event = DriveEvent::new(DriveEventKind::ToolSuccess);
        assert_eq!(event.kind, DriveEventKind::ToolSuccess);
        assert!(matches!(event.source, DriveEventSource::Manual));
        assert!(event.detail.is_none());
    }

    #[test]
    fn drive_event_with_source() {
        let event =
            DriveEvent::new(DriveEventKind::NovelInput).with_source(DriveEventSource::Workspace);
        assert!(matches!(event.source, DriveEventSource::Workspace));
    }

    #[test]
    fn drive_event_with_detail() {
        let event = DriveEvent::new(DriveEventKind::ToolError)
            .with_detail("memory.create failed: invalid args");
        assert_eq!(
            event.detail.as_deref(),
            Some("memory.create failed: invalid args")
        );
    }

    #[test]
    fn drive_event_kind_variants() {
        let kinds = [
            DriveEventKind::ToolSuccess,
            DriveEventKind::ToolError,
            DriveEventKind::NovelInput,
            DriveEventKind::LowConfidence,
            DriveEventKind::HighConfidence,
            DriveEventKind::ResourcePressure,
            DriveEventKind::ResourceRelief,
            DriveEventKind::SocialInteraction,
            DriveEventKind::Decay,
        ];
        assert_eq!(kinds.len(), 9);
    }

    #[test]
    fn drive_event_source_variants() {
        let sources = [
            DriveEventSource::Dispatch,
            DriveEventSource::SelfModel,
            DriveEventSource::Substrate,
            DriveEventSource::Workspace,
            DriveEventSource::Autonomic,
            DriveEventSource::Timer,
            DriveEventSource::Manual,
        ];
        assert_eq!(sources.len(), 7);
    }
}
