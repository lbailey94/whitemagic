//! Code Writing Clone - Self-Modifying Clone Army
//! Clones that can write, edit, and transfer code
//! 
//! Target: 1M+ code operations/sec with parallel file I/O

use pyo3::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};
use rayon::prelude::*;
use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct CodeOperation {
    #[pyo3(get, set)]
    pub op_type: String,  // "write", "edit", "copy", "move", "delete"
    #[pyo3(get, set)]
    pub source_file: String,
    #[pyo3(get, set)]
    pub target_file: String,
    #[pyo3(get, set)]
    pub content: String,
    #[pyo3(get, set)]
    pub line_start: Option<usize>,
    #[pyo3(get, set)]
    pub line_end: Option<usize>,
}

#[pymethods]
impl CodeOperation {
    #[new]
    fn new(
        op_type: String,
        source_file: String,
        target_file: String,
        content: String,
        line_start: Option<usize>,
        line_end: Option<usize>,
    ) -> Self {
        Self {
            op_type,
            source_file,
            target_file,
            content,
            line_start,
            line_end,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[pyclass]
pub struct CodeWritingResult {
    #[pyo3(get)]
    pub operation_id: String,
    #[pyo3(get)]
    pub success: bool,
    #[pyo3(get)]
    pub files_modified: usize,
    #[pyo3(get)]
    pub lines_written: usize,
    #[pyo3(get)]
    pub duration_ms: f64,
    #[pyo3(get)]
    pub error_message: Option<String>,
}

#[pyclass]
pub struct CodeWritingClone {
    clone_id: String,
    operations: Arc<RwLock<Vec<CodeOperation>>>,
    results: Arc<RwLock<Vec<CodeWritingResult>>>,
    base_path: PathBuf,
}

#[pymethods]
impl CodeWritingClone {
    #[new]
    fn new(clone_id: String, base_path: String) -> Self {
        Self {
            clone_id,
            operations: Arc::new(RwLock::new(Vec::new())),
            results: Arc::new(RwLock::new(Vec::new())),
            base_path: PathBuf::from(base_path),
        }
    }

    fn add_operation(&mut self, operation: CodeOperation) -> PyResult<()> {
        let mut ops = self.operations.write().unwrap();
        ops.push(operation);
        Ok(())
    }

    fn execute_operation(&mut self, operation: CodeOperation) -> PyResult<CodeWritingResult> {
        let start = std::time::Instant::now();
        
        let result = match operation.op_type.as_str() {
            "write" => self.write_file(&operation),
            "edit" => self.edit_file(&operation),
            "copy" => self.copy_file(&operation),
            "move" => self.move_file(&operation),
            "delete" => self.delete_file(&operation),
            _ => Err(format!("Unknown operation type: {}", operation.op_type)),
        };

        let duration = start.elapsed().as_secs_f64() * 1000.0;

        let code_result = match result {
            Ok((files_modified, lines_written)) => CodeWritingResult {
                operation_id: format!("{}-{}", self.clone_id, uuid::Uuid::new_v4()),
                success: true,
                files_modified,
                lines_written,
                duration_ms: duration,
                error_message: None,
            },
            Err(e) => CodeWritingResult {
                operation_id: format!("{}-{}", self.clone_id, uuid::Uuid::new_v4()),
                success: false,
                files_modified: 0,
                lines_written: 0,
                duration_ms: duration,
                error_message: Some(e),
            },
        };

        let mut results = self.results.write().unwrap();
        results.push(code_result.clone());

        Ok(code_result)
    }

    fn execute_all(&mut self) -> PyResult<Vec<CodeWritingResult>> {
        let operations = {
            let ops = self.operations.read().unwrap();
            ops.clone()
        };

        let results: Vec<CodeWritingResult> = operations
            .into_par_iter()
            .map(|op| {
                let start = std::time::Instant::now();
                
                let result = match op.op_type.as_str() {
                    "write" => self.write_file_internal(&op),
                    "edit" => self.edit_file_internal(&op),
                    "copy" => self.copy_file_internal(&op),
                    _ => Err(format!("Operation not supported in parallel: {}", op.op_type)),
                };

                let duration = start.elapsed().as_secs_f64() * 1000.0;

                match result {
                    Ok((files_modified, lines_written)) => CodeWritingResult {
                        operation_id: format!("{}-{}", self.clone_id, uuid::Uuid::new_v4()),
                        success: true,
                        files_modified,
                        lines_written,
                        duration_ms: duration,
                        error_message: None,
                    },
                    Err(e) => CodeWritingResult {
                        operation_id: format!("{}-{}", self.clone_id, uuid::Uuid::new_v4()),
                        success: false,
                        files_modified: 0,
                        lines_written: 0,
                        duration_ms: duration,
                        error_message: Some(e),
                    },
                }
            })
            .collect();

        let mut stored_results = self.results.write().unwrap();
        stored_results.extend(results.clone());

        Ok(results)
    }

    fn get_results(&self) -> PyResult<Vec<CodeWritingResult>> {
        let results = self.results.read().unwrap();
        Ok(results.clone())
    }

    fn get_stats(&self) -> PyResult<HashMap<String, f64>> {
        let results = self.results.read().unwrap();
        
        let total_ops = results.len() as f64;
        let successful = results.iter().filter(|r| r.success).count() as f64;
        let total_files = results.iter().map(|r| r.files_modified).sum::<usize>() as f64;
        let total_lines = results.iter().map(|r| r.lines_written).sum::<usize>() as f64;
        let total_duration: f64 = results.iter().map(|r| r.duration_ms).sum();

        let mut stats = HashMap::new();
        stats.insert("total_operations".to_string(), total_ops);
        stats.insert("successful_operations".to_string(), successful);
        stats.insert("success_rate".to_string(), if total_ops > 0.0 { successful / total_ops } else { 0.0 });
        stats.insert("total_files_modified".to_string(), total_files);
        stats.insert("total_lines_written".to_string(), total_lines);
        stats.insert("total_duration_ms".to_string(), total_duration);
        stats.insert("avg_duration_ms".to_string(), if total_ops > 0.0 { total_duration / total_ops } else { 0.0 });

        Ok(stats)
    }
}

impl CodeWritingClone {
    fn write_file(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        self.write_file_internal(op)
    }

    fn write_file_internal(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        let target_path = self.base_path.join(&op.target_file);
        
        // Create parent directories
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directories: {}", e))?;
        }

        // Write content
        fs::write(&target_path, &op.content)
            .map_err(|e| format!("Failed to write file: {}", e))?;

        let lines = op.content.lines().count();
        Ok((1, lines))
    }

    fn edit_file(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        self.edit_file_internal(op)
    }

    fn edit_file_internal(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        let target_path = self.base_path.join(&op.target_file);
        
        // Read existing content
        let existing = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read file: {}", e))?;

        let mut lines: Vec<String> = existing.lines().map(|s| s.to_string()).collect();

        // Apply edit
        if let (Some(start), Some(end)) = (op.line_start, op.line_end) {
            let new_lines: Vec<String> = op.content.lines().map(|s| s.to_string()).collect();
            
            // Replace lines
            lines.splice(start..end, new_lines.clone());
            
            let new_content = lines.join("\n") + "\n";
            fs::write(&target_path, new_content)
                .map_err(|e| format!("Failed to write edited file: {}", e))?;

            Ok((1, new_lines.len()))
        } else {
            // Append content
            let new_content = existing + "\n" + &op.content;
            fs::write(&target_path, new_content)
                .map_err(|e| format!("Failed to append to file: {}", e))?;

            Ok((1, op.content.lines().count()))
        }
    }

    fn copy_file(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        self.copy_file_internal(op)
    }

    fn copy_file_internal(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        let source_path = self.base_path.join(&op.source_file);
        let target_path = self.base_path.join(&op.target_file);

        // Create parent directories
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directories: {}", e))?;
        }

        // Copy file
        fs::copy(&source_path, &target_path)
            .map_err(|e| format!("Failed to copy file: {}", e))?;

        // Count lines
        let content = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read copied file: {}", e))?;
        let lines = content.lines().count();

        Ok((1, lines))
    }

    fn move_file(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        let source_path = self.base_path.join(&op.source_file);
        let target_path = self.base_path.join(&op.target_file);

        // Create parent directories
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directories: {}", e))?;
        }

        // Move file
        fs::rename(&source_path, &target_path)
            .map_err(|e| format!("Failed to move file: {}", e))?;

        // Count lines
        let content = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read moved file: {}", e))?;
        let lines = content.lines().count();

        Ok((1, lines))
    }

    fn delete_file(&self, op: &CodeOperation) -> Result<(usize, usize), String> {
        let target_path = self.base_path.join(&op.target_file);

        fs::remove_file(&target_path)
            .map_err(|e| format!("Failed to delete file: {}", e))?;

        Ok((1, 0))
    }
}

#[pyclass]
pub struct CodeWritingArmy {
    army_id: String,
    clones: Arc<RwLock<Vec<CodeWritingClone>>>,
    base_path: PathBuf,
}

#[pymethods]
impl CodeWritingArmy {
    #[new]
    fn new(army_id: String, base_path: String, clone_count: usize) -> Self {
        let mut clones = Vec::with_capacity(clone_count);
        let base = PathBuf::from(&base_path);

        for i in 0..clone_count {
            clones.push(CodeWritingClone::new(
                format!("{}-clone-{}", army_id, i),
                base_path.clone(),
            ));
        }

        Self {
            army_id,
            clones: Arc::new(RwLock::new(clones)),
            base_path: base,
        }
    }

    fn deploy_operations(&mut self, operations: Vec<CodeOperation>) -> PyResult<Vec<CodeWritingResult>> {
        let start = std::time::Instant::now();

        // Distribute operations across clones
        let results: Vec<CodeWritingResult> = operations
            .into_par_iter()
            .map(|op| {
                let op_start = std::time::Instant::now();
                
                // Execute operation directly (stateless)
                let result = match op.op_type.as_str() {
                    "write" => Self::write_file_static(&self.base_path, &op),
                    "copy" => Self::copy_file_static(&self.base_path, &op),
                    _ => Err(format!("Operation not supported: {}", op.op_type)),
                };

                let duration = op_start.elapsed().as_secs_f64() * 1000.0;

                match result {
                    Ok((files_modified, lines_written)) => CodeWritingResult {
                        operation_id: format!("{}-{}", self.army_id, uuid::Uuid::new_v4()),
                        success: true,
                        files_modified,
                        lines_written,
                        duration_ms: duration,
                        error_message: None,
                    },
                    Err(e) => CodeWritingResult {
                        operation_id: format!("{}-{}", self.army_id, uuid::Uuid::new_v4()),
                        success: false,
                        files_modified: 0,
                        lines_written: 0,
                        duration_ms: duration,
                        error_message: Some(e),
                    },
                }
            })
            .collect();

        let total_duration = start.elapsed().as_secs_f64();
        let throughput = results.len() as f64 / total_duration;

        println!("\n🚀 Code Writing Army Deployment:");
        println!("  Operations: {}", results.len());
        println!("  Duration: {:.3}s", total_duration);
        println!("  Throughput: {:.0} ops/sec", throughput);
        println!("  Success rate: {:.1}%", 
            results.iter().filter(|r| r.success).count() as f64 / results.len() as f64 * 100.0
        );

        Ok(results)
    }

    fn get_army_stats(&self) -> PyResult<HashMap<String, f64>> {
        let clones = self.clones.read().unwrap();
        
        let mut total_stats = HashMap::new();
        total_stats.insert("clone_count".to_string(), clones.len() as f64);

        Ok(total_stats)
    }
}

impl CodeWritingArmy {
    fn write_file_static(base_path: &Path, op: &CodeOperation) -> Result<(usize, usize), String> {
        let target_path = base_path.join(&op.target_file);
        
        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directories: {}", e))?;
        }

        fs::write(&target_path, &op.content)
            .map_err(|e| format!("Failed to write file: {}", e))?;

        let lines = op.content.lines().count();
        Ok((1, lines))
    }

    fn copy_file_static(base_path: &Path, op: &CodeOperation) -> Result<(usize, usize), String> {
        let source_path = base_path.join(&op.source_file);
        let target_path = base_path.join(&op.target_file);

        if let Some(parent) = target_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directories: {}", e))?;
        }

        fs::copy(&source_path, &target_path)
            .map_err(|e| format!("Failed to copy file: {}", e))?;

        let content = fs::read_to_string(&target_path)
            .map_err(|e| format!("Failed to read copied file: {}", e))?;
        let lines = content.lines().count();

        Ok((1, lines))
    }
}

#[pyfunction]
pub fn benchmark_code_writing(operation_count: usize, base_path: String) -> PyResult<HashMap<String, f64>> {
    let start = std::time::Instant::now();
    let base = PathBuf::from(&base_path);

    // Create test operations
    let operations: Vec<_> = (0..operation_count)
        .map(|i| CodeOperation {
            op_type: "write".to_string(),
            source_file: String::new(),
            target_file: format!("test_output/test_{}.txt", i),
            content: format!("Test content {}", i),
            line_start: None,
            line_end: None,
        })
        .collect();

    // Execute in parallel
    let results: Vec<_> = operations
        .into_par_iter()
        .map(|op| {
            CodeWritingArmy::write_file_static(&base, &op)
        })
        .collect();

    let duration = start.elapsed().as_secs_f64();
    let successful = results.iter().filter(|r| r.is_ok()).count();
    let throughput = operation_count as f64 / duration;

    let mut stats = HashMap::new();
    stats.insert("operation_count".to_string(), operation_count as f64);
    stats.insert("successful".to_string(), successful as f64);
    stats.insert("duration_sec".to_string(), duration);
    stats.insert("throughput_ops_sec".to_string(), throughput);

    Ok(stats)
}
