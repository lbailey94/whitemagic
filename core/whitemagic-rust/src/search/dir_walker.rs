use std::collections::HashMap;
use std::path::{Path, PathBuf};
use rayon::prelude::*;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Skip directories that match common vendor/build/archive names.
fn should_skip_dir(name: &str) -> bool {
    matches!(
        name,
        ".venv" | "venv" | "node_modules" | "target" | "dist" | "build" | "build-modern"
        | ".git" | "__pycache__" | ".pytest_cache" | ".mypy_cache" | ".tox" | "release"
        | "external" | "_deps" | "vendor" | "third_party" | "thirdparty" | "deps"
        | "lib" | "libs" | "site-packages" | "packages"
        | "out" | "cmake-build" | "oldFiles" | "archive" | "archives"
        | ".hypothesis" | ".strata-cache" | ".fragment"
    )
}

/// Recursively walk a directory in parallel, returning all non-skipped files
/// grouped by extension.
fn walk_directory_parallel(root: &Path) -> HashMap<String, Vec<PathBuf>> {
    use std::sync::Mutex;

    let entries: Mutex<Vec<PathBuf>> = Mutex::new(Vec::new());

    // First pass: collect all directories and files using walkdir with rayon
    let walker = walkdir::WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|e| {
            if e.file_type().is_dir() {
                let name = e.file_name().to_string_lossy();
                !should_skip_dir(&name)
            } else {
                true
            }
        });

    for entry in walker {
        if let Ok(entry) = entry {
            if entry.file_type().is_file() {
                entries.lock().unwrap().push(entry.path().to_path_buf());
            }
        }
    }

    // Group by extension in parallel
    let files = entries.into_inner().unwrap();
    let grouped: Mutex<HashMap<String, Vec<PathBuf>>> = Mutex::new(HashMap::new());

    files.par_iter().for_each(|path| {
        if let Some(ext) = path.extension() {
            let ext_str = format!(".{}", ext.to_string_lossy());
            grouped.lock().unwrap()
                .entry(ext_str)
                .or_insert_with(Vec::new)
                .push(path.clone());
        }
    });

    grouped.into_inner().unwrap()
}

/// Python-exposed function: walk a directory tree in parallel and return
/// a dict mapping file extensions to lists of file paths.
/// This replaces Python's sequential `rglob("*")` with a rayon-parallel walk.
#[pyfunction]
#[pyo3(signature = (root_path,))]
pub fn walk_directory(root_path: &str) -> PyResult<PyObject> {
    let root = Path::new(root_path);
    if !root.exists() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            format!("Path does not exist: {}", root_path),
        ));
    }

    let grouped = walk_directory_parallel(root);

    Python::with_gil(|py| {
        let result = PyDict::new_bound(py);
        for (ext, paths) in grouped {
            let path_strings: Vec<String> = paths
                .iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect();
            result.set_item(&ext, path_strings)?;
        }
        Ok(result.into())
    })
}
