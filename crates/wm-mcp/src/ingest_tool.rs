//! `memory.ingest` — MCP surface for the knowledge ingest pipeline.
//!
//! Thin wrapper over [`crate::ingest::run_ingest`] with safe defaults
//! (`dry_run = true`, `redact = true`). It writes memories into the serving
//! store's LMDB + Tantivy index and reads arbitrary local paths (session
//! archives are the point), so it declares `Sandbox::Inherit` and a
//! non-destructive write effect row. Sources are never modified or deleted;
//! re-runs are idempotent via the store's ingest ledger.

use std::path::PathBuf;

use async_trait::async_trait;
use serde_json::{Value, json};
use wm_core::{Capability, Context, EffectRow, Gana, Resource, Sandbox, Tool, ToolStats};

/// Arguments accepted by `memory.ingest`, parsed without a runtime context so
/// the contract is unit-testable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct IngestParams {
    pub source: PathBuf,
    pub dry_run: bool,
    pub limit: usize,
    pub galaxy: Option<String>,
    pub redact: bool,
    pub wait_secs: u64,
    pub include_credential_files: bool,
}

pub(crate) fn parse_args(args: &Value) -> Result<IngestParams, String> {
    let source = args
        .get("source")
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| "source is required".to_string())?;
    let dry_run = args.get("dry_run").and_then(Value::as_bool).unwrap_or(true);
    let limit = args.get("limit").and_then(Value::as_u64).unwrap_or(0) as usize;
    let galaxy = args
        .get("galaxy")
        .and_then(Value::as_str)
        .map(str::to_string);
    let redact = args.get("redact").and_then(Value::as_bool).unwrap_or(true);
    let wait_secs = args.get("wait_secs").and_then(Value::as_u64).unwrap_or(0);
    let include_credential_files = args
        .get("include_credential_files")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    if include_credential_files && !redact {
        return Err("include_credential_files requires redact=true".to_string());
    }
    Ok(IngestParams {
        source: PathBuf::from(source),
        dry_run,
        limit,
        galaxy,
        redact,
        wait_secs,
        include_credential_files,
    })
}

pub struct MemoryIngestTool {
    store_path: PathBuf,
    stats: ToolStats,
    effects: EffectRow,
}

impl MemoryIngestTool {
    #[must_use]
    pub fn new(store_path: &std::path::Path) -> Self {
        Self {
            store_path: store_path.to_path_buf(),
            stats: ToolStats::default(),
            effects: EffectRow {
                reads: {
                    let mut reads = wm_tools::expansion::common::memory_galaxy_reads();
                    reads.push(Resource::Filesystem);
                    reads
                },
                writes: {
                    let mut writes = wm_tools::expansion::common::memory_galaxy_writes();
                    writes.push(Resource::SearchIndex);
                    writes
                },
                invokes: vec![Capability::MemoryWrite],
                destructive: false,
                // Harvesting session archives requires reading paths outside the
                // store root, so this tool is not StoreScoped.
                sandbox: Sandbox::Inherit,
                ..Default::default()
            },
        }
    }
}

#[async_trait]
impl Tool for MemoryIngestTool {
    fn name(&self) -> &str {
        "memory.ingest"
    }

    fn gana(&self) -> Gana {
        Gana::Encampment
    }

    fn effects(&self) -> &EffectRow {
        &self.effects
    }

    fn stats(&self) -> &ToolStats {
        &self.stats
    }

    fn description(&self) -> &str {
        "Ingest documents and session transcripts from a local directory into this store \
         (idempotent via a SHA-256 ledger, credential-shaped content redacted; dry_run \
         defaults to true). Sources are never modified or deleted."
    }

    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Directory to harvest recursively."
                },
                "dry_run": {
                    "type": "boolean",
                    "default": true,
                    "description": "Report without writing or creating the store (default true)."
                },
                "limit": {
                    "type": "integer",
                    "default": 0,
                    "description": "Only consider the first N files in walk order (0 = all)."
                },
                "galaxy": {
                    "type": "string",
                    "description": "Optional galaxy override for transcripts/documents."
                },
                "redact": {
                    "type": "boolean",
                    "default": true,
                    "description": "Scrub credential-shaped content before storage (default true)."
                },
                "wait_secs": {
                    "type": "integer",
                    "default": 0,
                    "description": "Wait up to N seconds for a busy store before failing."
                },
                "include_credential_files": {
                    "type": "boolean",
                    "default": false,
                    "description": "Ingest credential-named files with redaction (requires redact=true)."
                }
            },
            "required": ["source"]
        })
    }

    async fn call(&self, _ctx: &mut Context, args: Value) -> wm_core::Result<Value> {
        let params = match parse_args(&args) {
            Ok(params) => params,
            Err(error) => return Ok(json!({ "status": "error", "error": error })),
        };
        if !params.source.is_dir() {
            return Ok(json!({
                "status": "error",
                "error": format!("source is not a directory: {}", params.source.display()),
            }));
        }
        let store_path = self.store_path.clone();
        let source_label = params.source.display().to_string();
        let IngestParams {
            source,
            dry_run,
            limit,
            galaxy,
            redact,
            wait_secs,
            include_credential_files,
        } = params;
        let outcome = tokio::task::spawn_blocking(move || {
            crate::ingest::run_ingest(
                &source,
                &store_path,
                dry_run,
                limit,
                galaxy.as_deref(),
                redact,
                wait_secs,
                include_credential_files,
            )
        })
        .await;
        match outcome {
            Ok(Ok(report)) => Ok(json!({
                "status": "success",
                "dry_run": dry_run,
                "summary": report.summary_line(),
                "files_found": report.files_found,
                "files_unchanged": report.files_unchanged,
                "files_ingested": report.files_ingested,
                "chunks_written": report.chunks_written,
                "redactions": report.redactions,
                "skipped": report
                    .skipped
                    .iter()
                    .take(20)
                    .map(|(path, reason)| json!({ "path": path, "reason": reason }))
                    .collect::<Vec<_>>(),
                "errors": report
                    .errors
                    .iter()
                    .take(20)
                    .map(|(path, reason)| json!({ "path": path, "reason": reason }))
                    .collect::<Vec<_>>(),
                "store": self.store_path.display().to_string(),
                "source": source_label,
            })),
            Ok(Err(error)) => Ok(json!({ "status": "error", "error": error.to_string() })),
            Err(join_error) => Ok(json!({
                "status": "error",
                "error": format!("ingest task failed: {join_error}"),
            })),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contract_requires_source_and_safe_defaults() {
        let tool = MemoryIngestTool::new(std::path::Path::new("/tmp/wm-ingest-tool-test"));
        assert_eq!(tool.name(), "memory.ingest");
        assert_eq!(tool.input_schema()["required"][0], "source");
        assert!(!tool.effects().destructive);

        let params = parse_args(&json!({ "source": "/tmp" })).unwrap();
        assert!(params.dry_run, "dry_run must default to true");
        assert!(params.redact, "redact must default to true");
        assert!(!params.include_credential_files);

        assert!(parse_args(&json!({})).is_err());
        assert!(parse_args(&json!({ "source": "  " })).is_err());
        assert!(
            parse_args(&json!({
                "source": "/tmp",
                "include_credential_files": true,
                "redact": false
            }))
            .is_err(),
            "credential-file override requires redaction"
        );
    }

    #[test]
    fn explicit_flags_are_honored() {
        let params = parse_args(&json!({
            "source": "/tmp/sessions",
            "dry_run": false,
            "limit": 25,
            "galaxy": "sessions",
            "redact": true,
            "wait_secs": 30
        }))
        .unwrap();
        assert!(!params.dry_run);
        assert_eq!(params.limit, 25);
        assert_eq!(params.galaxy.as_deref(), Some("sessions"));
        assert_eq!(params.wait_secs, 30);
    }
}
