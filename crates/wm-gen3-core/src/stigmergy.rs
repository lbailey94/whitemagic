//! Digital Stigmergy & AST Pheromones for non-verbal inter-agent coordination.
//!
//! Grounded in MIT SwarmWorld (2026) and PheroPath paradigms, agents leave
//! decaying environmental traces (pheromones) directly on the workspace/AST nodes
//! rather than generating high-overhead natural language chat messages.

use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use uuid::Uuid;

/// The functional intent of a digital pheromone trace.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PheromoneKind {
    /// An active mutation or write operation is occurring on this resource/AST scope.
    MutationActive,
    /// An agent is reading or inspecting this scope.
    Inspection,
    /// A multi-file structural refactoring or semantic migration is touching this node.
    Refactoring,
    /// A code review or testing verification is pending.
    ReviewPending,
    /// Custom domain-specific operational signal.
    Custom(String),
}

/// A digital pheromone emitted onto a resource or specific AST node.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Pheromone {
    /// Unique identifier for this pheromone trace.
    pub id: Uuid,
    /// Target file path relative to workspace root (e.g. "SharedWorkspace/bridge.py").
    pub target_path: String,
    /// Target AST scopes or symbol paths (e.g. ["class:WhiteboardHandler", "fn:do_GET"]).
    pub ast_scope: Vec<String>,
    /// Optional line span (start_line, end_line) 1-indexed inclusive.
    pub line_range: Option<(u32, u32)>,
    /// The functional kind/intent of the pheromone.
    pub kind: PheromoneKind,
    /// Initial intensity $I_0 \in (0.0, 1.0]$.
    pub initial_intensity: f64,
    /// Decay half-life $\tau$ in milliseconds (e.g. 60_000 for 1 minute).
    pub half_life_ms: u64,
    /// Emission timestamp in Unix milliseconds.
    pub emitted_at_ms: u64,
    /// Agent identifier that emitted this pheromone (e.g. "antigravity", "opencode").
    pub issuer: String,
    /// Optional structured metadata or tag payload.
    pub metadata: HashMap<String, String>,
}

impl Pheromone {
    /// Creates a new pheromone with a fresh UUID and current timestamp.
    pub fn new(
        target_path: impl Into<String>,
        ast_scope: Vec<String>,
        kind: PheromoneKind,
        initial_intensity: f64,
        half_life_ms: u64,
        issuer: impl Into<String>,
    ) -> Self {
        let now_ms = Utc::now().timestamp_millis().max(0) as u64;
        Self {
            id: Uuid::new_v4(),
            target_path: target_path.into(),
            ast_scope,
            line_range: None,
            kind,
            initial_intensity: initial_intensity.clamp(0.0, 1.0),
            half_life_ms: half_life_ms.max(100), // minimum 100ms half life
            emitted_at_ms: now_ms,
            issuer: issuer.into(),
            metadata: HashMap::new(),
        }
    }

    /// Builder method to attach a line range.
    pub fn with_line_range(mut self, start: u32, end: u32) -> Self {
        self.line_range = Some((start, end));
        self
    }

    /// Builder method to attach metadata.
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Computes the current decayed intensity $I(t) = I_0 \cdot 2^{-\frac{\Delta t}{\tau}}$.
    #[must_use]
    pub fn current_intensity(&self, now_ms: u64) -> f64 {
        if now_ms <= self.emitted_at_ms {
            return self.initial_intensity;
        }
        let delta_t = (now_ms - self.emitted_at_ms) as f64;
        let half_life = self.half_life_ms as f64;
        let exponent = -(delta_t / half_life);
        let decayed = self.initial_intensity * 2.0_f64.powf(exponent);
        if decayed.is_nan() || decayed < 0.001 {
            0.0
        } else {
            decayed
        }
    }

    /// Checks whether this pheromone has completely evaporated below a given threshold (default 0.01).
    #[must_use]
    pub fn is_evaporated(&self, now_ms: u64, threshold: f64) -> bool {
        self.current_intensity(now_ms) < threshold.max(0.001)
    }

    /// Convert to RawPheromone for zero-copy POSIX shared memory substrate.
    pub fn to_raw(&self) -> wm_gen3_shm::RawPheromone {
        let kind_code = match &self.kind {
            PheromoneKind::MutationActive => 0,
            PheromoneKind::Inspection => 1,
            PheromoneKind::Refactoring => 2,
            PheromoneKind::ReviewPending => 3,
            PheromoneKind::Custom(_) => 4,
        };
        let (line_start, line_end) = self.line_range.unwrap_or((1, 1));
        let ast_scope_str = self.ast_scope.join("::");

        wm_gen3_shm::RawPheromone {
            id: self.id,
            kind: kind_code,
            target_path: self.target_path.clone(),
            ast_scope: ast_scope_str,
            line_start,
            line_end,
            initial_intensity: self.initial_intensity as f32,
            half_life_ms: self.half_life_ms as u32,
            emitted_at_ms: self.emitted_at_ms,
            issuer: self.issuer.clone(),
        }
    }

    /// Construct Pheromone from RawPheromone.
    pub fn from_raw(raw: &wm_gen3_shm::RawPheromone) -> Self {
        let kind = match raw.kind {
            0 => PheromoneKind::MutationActive,
            1 => PheromoneKind::Inspection,
            2 => PheromoneKind::Refactoring,
            3 => PheromoneKind::ReviewPending,
            _ => PheromoneKind::Custom("shm_signal".into()),
        };
        let ast_scope = if raw.ast_scope.is_empty() {
            Vec::new()
        } else {
            raw.ast_scope.split("::").map(String::from).collect()
        };

        Pheromone {
            id: raw.id,
            target_path: raw.target_path.clone(),
            ast_scope,
            line_range: Some((raw.line_start, raw.line_end)),
            kind,
            initial_intensity: raw.initial_intensity as f64,
            half_life_ms: raw.half_life_ms as u64,
            emitted_at_ms: raw.emitted_at_ms,
            issuer: raw.issuer.clone(),
            metadata: HashMap::new(),
        }
    }

    /// Checks if this pheromone overlaps with a candidate target and AST scope.
    #[must_use]
    pub fn overlaps(
        &self,
        target_path: &str,
        candidate_ast_scope: &[String],
        candidate_lines: Option<(u32, u32)>,
    ) -> bool {
        if self.target_path != target_path {
            return false;
        }

        // If either has no AST scope specified, it applies to the whole file
        if self.ast_scope.is_empty() || candidate_ast_scope.is_empty() {
            return true;
        }

        // Check AST scope intersection
        let ast_match = self
            .ast_scope
            .iter()
            .any(|node| candidate_ast_scope.iter().any(|c| c == node));
        if ast_match {
            return true;
        }

        // Check line range overlap if present on both
        if let (Some((s1, e1)), Some((s2, e2))) = (self.line_range, candidate_lines) {
            return !(e1 < s2 || e2 < s1);
        }

        false
    }
}

/// An environmental field of active pheromones.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct StigmergicField {
    pheromones: Vec<Pheromone>,
}

impl StigmergicField {
    /// Creates an empty stigmergic field.
    pub fn new() -> Self {
        Self {
            pheromones: Vec::new(),
        }
    }

    /// Emits a new pheromone into the environment.
    pub fn emit(&mut self, pheromone: Pheromone) {
        self.pheromones.push(pheromone);
    }

    /// Evaporates stale pheromones whose intensity has fallen below `threshold`.
    ///
    /// Returns the number of evaporated pheromones purged from the field.
    pub fn evaporate(&mut self, now_ms: u64, threshold: f64) -> usize {
        let before = self.pheromones.len();
        self.pheromones
            .retain(|p| !p.is_evaporated(now_ms, threshold));
        before - self.pheromones.len()
    }

    /// Returns a slice of all active pheromones.
    pub fn all(&self) -> &[Pheromone] {
        &self.pheromones
    }

    /// Senses potential conflicts on a candidate target file and AST scope.
    ///
    /// Returns any pheromone emitted by another agent whose current intensity exceeds `threshold`.
    pub fn sense_conflicts(
        &self,
        target_path: &str,
        candidate_ast_scope: &[String],
        candidate_lines: Option<(u32, u32)>,
        threshold: f64,
        now_ms: u64,
        ignore_issuer: Option<&str>,
    ) -> Vec<(&Pheromone, f64)> {
        let mut conflicts = Vec::new();
        for p in &self.pheromones {
            if let Some(issuer) = ignore_issuer {
                if p.issuer == issuer {
                    continue;
                }
            }
            if p.overlaps(target_path, candidate_ast_scope, candidate_lines) {
                let intensity = p.current_intensity(now_ms);
                if intensity >= threshold {
                    conflicts.push((p, intensity));
                }
            }
        }
        conflicts
    }

    /// Computes aggregated heat score per target file for visualization and badge rendering.
    pub fn aggregate_file_heatmaps(&self, now_ms: u64) -> HashMap<String, f64> {
        let mut heatmap = HashMap::new();
        for p in &self.pheromones {
            let intensity = p.current_intensity(now_ms);
            if intensity > 0.001 {
                let entry = heatmap.entry(p.target_path.clone()).or_insert(0.0);
                *entry += intensity;
            }
        }
        heatmap
    }

    /// Serializes the active field to a JSON string.
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }

    /// Deserializes a field from JSON.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Loads the field from a file path if it exists, or returns an empty field.
    pub fn load_from_file(path: impl AsRef<Path>) -> std::io::Result<Self> {
        let path = path.as_ref();
        if !path.exists() {
            return Ok(Self::new());
        }
        let data = std::fs::read_to_string(path)?;
        Self::from_json(&data).map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Persists the field to disk atomically.
    pub fn save_to_file(&self, path: impl AsRef<Path>) -> std::io::Result<()> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let json = self
            .to_json()
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        let tmp_path = PathBuf::from(format!("{}.tmp.{}", path.display(), Uuid::new_v4()));
        std::fs::write(&tmp_path, json)?;
        std::fs::rename(tmp_path, path)?;
        Ok(())
    }

    /// Connect to a named zero-copy POSIX shared memory substrate.
    pub fn open_shm(name: &str) -> std::io::Result<wm_gen3_shm::ShmStigmergyField> {
        let substrate = wm_gen3_shm::ShmSubstrate::open_or_create(name)?;
        Ok(wm_gen3_shm::ShmStigmergyField::new(std::sync::Arc::new(
            substrate,
        )))
    }

    /// Attach to an inherited shared memory file descriptor (for Landlock sandboxes).
    #[cfg(unix)]
    pub fn attach_shm_fd(
        fd: std::os::unix::io::RawFd,
        is_owner: bool,
    ) -> std::io::Result<wm_gen3_shm::ShmStigmergyField> {
        let substrate = wm_gen3_shm::ShmSubstrate::from_raw_fd(fd, is_owner)?;
        Ok(wm_gen3_shm::ShmStigmergyField::new(std::sync::Arc::new(
            substrate,
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pheromone_decay_mathematics() {
        let now = 100_000;
        let mut p = Pheromone::new(
            "src/causal.rs",
            vec!["fn:evaluate_action_candidate".into()],
            PheromoneKind::MutationActive,
            1.0,
            60_000, // half-life 60 seconds
            "antigravity",
        );
        p.emitted_at_ms = now;

        // At t = 0, intensity is 1.0
        assert!((p.current_intensity(now) - 1.0).abs() < 1e-4);

        // At t = 60s (one half life), intensity is 0.5
        assert!((p.current_intensity(now + 60_000) - 0.5).abs() < 1e-4);

        // At t = 120s (two half lives), intensity is 0.25
        assert!((p.current_intensity(now + 120_000) - 0.25).abs() < 1e-4);

        // At t = 360s (six half lives), intensity is 0.0156
        assert!((p.current_intensity(now + 360_000) - 0.015625).abs() < 1e-4);

        // At t = 600s (ten half lives), intensity is < 0.001 (evaporated)
        assert_eq!(p.current_intensity(now + 600_000), 0.0);
        assert!(p.is_evaporated(now + 600_000, 0.01));
    }

    #[test]
    fn test_stigmergic_field_conflict_sensing() {
        let now = 1_000_000;
        let mut field = StigmergicField::new();

        let mut p1 = Pheromone::new(
            "SharedWorkspace/bridge.py",
            vec!["class:WhiteboardHandler".into(), "fn:do_GET".into()],
            PheromoneKind::MutationActive,
            0.9,
            30_000,
            "opencode",
        )
        .with_line_range(180, 260);
        p1.emitted_at_ms = now;
        field.emit(p1);

        // 1. Same target and overlapping AST node from different agent -> Conflict detected
        let conflicts = field.sense_conflicts(
            "SharedWorkspace/bridge.py",
            &["fn:do_GET".into()],
            Some((200, 220)),
            0.1,
            now + 10_000,
            Some("antigravity"),
        );
        assert_eq!(conflicts.len(), 1);
        assert_eq!(conflicts[0].0.issuer, "opencode");
        assert!(conflicts[0].1 > 0.7);

        // 2. Querying with same issuer ignored -> No conflict
        let self_conflicts = field.sense_conflicts(
            "SharedWorkspace/bridge.py",
            &["fn:do_GET".into()],
            Some((200, 220)),
            0.1,
            now + 10_000,
            Some("opencode"),
        );
        assert_eq!(self_conflicts.len(), 0);

        // 3. Different file -> No conflict
        let diff_file = field.sense_conflicts(
            "SharedWorkspace/sangha.py",
            &["fn:main".into()],
            None,
            0.1,
            now + 10_000,
            Some("antigravity"),
        );
        assert_eq!(diff_file.len(), 0);

        // 4. After 5 half-lives (150s), intensity has dropped below 0.1 threshold -> No conflict
        let post_decay = field.sense_conflicts(
            "SharedWorkspace/bridge.py",
            &["fn:do_GET".into()],
            Some((200, 220)),
            0.1,
            now + 150_000,
            Some("antigravity"),
        );
        assert_eq!(post_decay.len(), 0);

        // 5. Evaporation purges the trace
        let purged = field.evaporate(now + 150_000, 0.05);
        assert_eq!(purged, 1);
        assert_eq!(field.all().len(), 0);
    }
}
