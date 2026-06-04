// Phase 15 ML Inference: File 190
//! Optimized ML inference with ONNX Runtime

use pyo3::prelude::*;
use ndarray::{Array, ArrayView};
use ort::{Environment, Session, Value};

pub struct MLInferenceEngine {
    session: Session,
    input_shape: Vec<i64>,
}

impl MLInferenceEngine {
    pub fn new(model_path: &str) -> Result<Self, InferenceError> {
        let env = Environment::builder().build()?;
        let session = Session::builder(&env)?
            .with_model_from_file(model_path)?
            .build()?;
        
        Ok(Self {
            session,
            input_shape: vec![1, 3, 224, 224],
        })
    }

    pub fn infer(&self, input: Array<f32>) -> Result<Vec<f32>, InferenceError> {
        let input_tensor = Value::from_array(input)?;
        let outputs = self.session.run(vec![input_tensor])?;
        
        // Extract predictions
        let output = outputs[0].try_extract()?;
        Ok(output.view().to_owned().into_raw_vec())
    }
}
