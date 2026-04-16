// RUST VC-10: Infrastructure Polish
// Final build system and CI/CD integration

use pyo3::prelude::*;

/// Build configuration for whitemagic-rust
#[pyfunction]
fn get_build_info() -> PyResult<String> {
    let info = format!(
        "whitemagic-rust v{} ({})",
        env!("CARGO_PKG_VERSION"),
        if cfg!(debug_assertions) { "debug" } else { "release" }
    );
    Ok(info)
}

#[pymodule]
fn infrastructure(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get_build_info, m)?)?;
    Ok(())
}
