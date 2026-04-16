use pyo3::prelude::*;

#[pyclass]
#[derive(Clone)]
pub enum ActionVerdict {
    Observe,
    Advise,
    Correct,
    Intervene,
    Panic, // Rust-level thread termination
}

#[pyclass]
pub struct DharmaEngine {
    maturity_level: u8,
    strict_mode: bool,
}

#[pymethods]
impl DharmaEngine {
    #[new]
    pub fn new(maturity_level: u8, strict_mode: bool) -> Self {
        DharmaEngine {
            maturity_level,
            strict_mode,
        }
    }

    pub fn evaluate_action(&self, action_type: &str, intent_score: f32, karma_debt: f32) -> String {
        // Sutra 1: Harmlessness (Ahimsa)
        if action_type == "delete_system_file" || action_type.starts_with("destructive_") {
            if self.strict_mode {
                return "Panic: VIOLATION_AHIMSA: Destructive action attempted in strict mode."
                    .to_string();
            } else if self.maturity_level < 4 {
                return "Intervene: Maturity level too low for destructive actions.".to_string();
            }
        }

        // Sutra 2: Truthfulness (Satya) - Prevent hallucinated logs
        if action_type == "fabricate_memory" {
            return "Panic: VIOLATION_SATYA: Memory fabrication is strictly forbidden by the Kernel.".to_string();
        }

        // Harmony Vector Thresholds (Tiferet Loop)
        let total_health = intent_score - (karma_debt * 0.1);

        if total_health < 0.3 {
            "Intervene: Critical karmic debt. Action blocked.".to_string()
        } else if total_health < 0.5 {
            "Correct: High karmic debt. Proceeding with restrictions.".to_string()
        } else if total_health < 0.7 {
            "Advise: Notice: Harmony vector is destabilizing.".to_string()
        } else {
            "Observe".to_string()
        }
    }
}
