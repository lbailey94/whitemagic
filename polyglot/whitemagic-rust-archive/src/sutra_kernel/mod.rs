pub mod dharma_engine;
pub mod zodiac_ledger;

use pyo3::prelude::*;

pub use dharma_engine::DharmaEngine;
pub use zodiac_ledger::ZodiacLedger;

pub fn sutra_kernel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ZodiacLedger>()?;
    m.add_class::<DharmaEngine>()?;
    Ok(())
}
