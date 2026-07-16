// PyO3 module exposing inference acceleration functions to Python.
//
// Exposes:
//   - ternary_gemv: multiplication-free GEMV with packed ternary weights
//   - ternary_dot: ternary dot product (scalar fallback)
//   - pack_ternary_matrix: pack a flat ternary weight matrix per-row
//   - pack_ternary: pack a flat ternary vector
//   - unpack_ternary: unpack u32 words back to ternary values
//
// Usage from Python:
//   import whitemagic_rust.inference as inference
//   packed = inference.pack_ternary_matrix(weights, m, k)
//   result = inference.ternary_gemv(packed, activations, m, k)

use pyo3::prelude::*;
use pyo3::types::PyList;
use numpy::{PyReadonlyArray1, PyReadonlyArray2, PyArray1, PyArray2};

use crate::inference::ternary_kernel::{
    self, pack_ternary, pack_ternary_matrix, ternary_dot, ternary_gemv, ternary_gemv_batch,
    unpack_ternary, Ternary,
};
use crate::inference::ring_buffer::RingBuffer as RustRingBuffer;
use crate::inference::trigram_pool::{Trigram, TrigramPool as RustTrigramPool};
use crate::inference::simd_ops;

/// Convert a Python list of ints (-1, 0, 1) to Rust Ternary slice
fn py_to_ternary(values: &Bound<'_, PyList>) -> PyResult<Vec<Ternary>> {
    values
        .iter()
        .map(|v| {
            let val: i32 = v.extract()?;
            match val {
                0 => Ok(Ternary::Zero),
                1 => Ok(Ternary::PosOne),
                -1 => Ok(Ternary::NegOne),
                _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Ternary values must be -1, 0, or 1, got {}",
                    val
                ))),
            }
        })
        .collect()
}

/// Pack 16 ternary values into each 32-bit word.
///
/// Args:
///   values: List of ints (-1, 0, 1)
///
/// Returns:
///   List of u32 packed words
#[pyfunction]
fn py_pack_ternary(py: Python<'_>, values: &Bound<'_, PyList>) -> PyResult<PyObject> {
    let ternary_values = py_to_ternary(values)?;
    let packed = pack_ternary(&ternary_values);
    Ok(PyList::new_bound(py, packed.iter().copied()).to_object(py))
}

/// Pack a ternary weight matrix per-row.
///
/// Args:
///   weights: Flat list of ints (-1, 0, 1), length m * k
///   m: Number of rows
///   k: Number of columns
///
/// Returns:
///   List of u32 packed words, length m * ((k + 15) / 16)
#[pyfunction]
fn py_pack_ternary_matrix(
    py: Python<'_>,
    weights: &Bound<'_, PyList>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let ternary_values = py_to_ternary(weights)?;
    let packed = pack_ternary_matrix(&ternary_values, m, k);
    Ok(PyList::new_bound(py, packed.iter().copied()).to_object(py))
}

/// Unpack u32 words back to ternary values.
///
/// Args:
///   packed: List of u32 words
///   count: Number of ternary values to unpack
///
/// Returns:
///   List of ints (-1, 0, 1)
#[pyfunction]
fn py_unpack_ternary(
    py: Python<'_>,
    packed: &Bound<'_, PyList>,
    count: usize,
) -> PyResult<PyObject> {
    let words: Vec<u32> = packed.extract()?;
    let values = unpack_ternary(&words, count);
    let result: Vec<i32> = values.iter().map(|t| match t {
        Ternary::Zero => 0,
        Ternary::PosOne => 1,
        Ternary::NegOne => -1,
    }).collect();
    Ok(PyList::new_bound(py, result).to_object(py))
}

/// Ternary GEMV: Compute y = W * x where W is ternary and x is fp32.
///
/// Uses AVX2 masked add/sub for multiplication-free inference.
/// Falls back to scalar on non-x86_64 platforms.
///
/// Args:
///   weights_packed: Packed ternary weights (from pack_ternary_matrix)
///   activations: Input vector x, length k
///   m: Number of output rows
///   k: Number of input columns
///
/// Returns:
///   Output vector y, length m
#[pyfunction]
fn py_ternary_gemv(
    py: Python<'_>,
    weights_packed: &Bound<'_, PyList>,
    activations: Vec<f32>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let weights: Vec<u32> = weights_packed.extract()?;
    let result = ternary_gemv(&weights, &activations, m, k);
    Ok(PyList::new_bound(py, result).to_object(py))
}

/// Ternary dot product: sum(w[i] * x[i]) where w is ternary.
///
/// Args:
///   weights: List of ints (-1, 0, 1)
///   activations: List of floats, same length
///
/// Returns:
///   Float result
#[pyfunction]
fn py_ternary_dot(
    weights: &Bound<'_, PyList>,
    activations: Vec<f32>,
) -> PyResult<f32> {
    let ternary_values = py_to_ternary(weights)?;
    if ternary_values.len() != activations.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Length mismatch: weights={} activations={}",
            ternary_values.len(),
            activations.len()
        )));
    }
    Ok(ternary_dot(&ternary_values, &activations))
}

/// Batch ternary GEMV: Compute y[i] = W * x[i] for multiple input vectors.
///
/// Args:
///   weights_packed: Packed ternary weights (from pack_ternary_matrix)
///   activations_batch: List of input vectors, each length k
///   m: Number of output rows
///   k: Number of input columns
///
/// Returns:
///   List of output vectors, each length m
#[pyfunction]
fn py_ternary_gemv_batch(
    py: Python<'_>,
    weights_packed: &Bound<'_, PyList>,
    activations_batch: &Bound<'_, PyList>,
    m: usize,
    k: usize,
) -> PyResult<PyObject> {
    let weights: Vec<u32> = weights_packed.extract()?;
    let batch: Vec<Vec<f32>> = activations_batch.extract()?;
    let slices: Vec<&[f32]> = batch.iter().map(|v| v.as_slice()).collect();
    let results = ternary_gemv_batch(&weights, &slices, m, k);

    let py_results: Vec<PyObject> = results
        .into_iter()
        .map(|v| PyList::new_bound(py, v).to_object(py))
        .collect();
    Ok(PyList::new_bound(py, py_results).to_object(py))
}

/// Get the backend type (avx2, scalar)
#[pyfunction]
fn py_ternary_backend() -> String {
    #[cfg(target_arch = "x86_64")]
    {
        if std::is_x86_feature_detected!("avx2") {
            "avx2".to_string()
        } else {
            "scalar".to_string()
        }
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        "scalar".to_string()
    }
}

// ── Ring Buffer PyO3 bindings ──────────────────────────────────────────

/// Parse a trigram name string to Trigram enum.
fn parse_trigram(name: &str) -> PyResult<Trigram> {
    match name {
        "Qian" => Ok(Trigram::Qian),
        "Zhen" => Ok(Trigram::Zhen),
        "Li" => Ok(Trigram::Li),
        "Xun" => Ok(Trigram::Xun),
        "Kan" => Ok(Trigram::Kan),
        "Gen" => Ok(Trigram::Gen),
        "Kun" => Ok(Trigram::Kun),
        "Dui" => Ok(Trigram::Dui),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Invalid trigram '{}'. Must be one of: Qian, Zhen, Li, Xun, Kan, Gen, Kun, Dui",
            name
        ))),
    }
}

/// Shared-memory SPSC ring buffer for inter-trigram communication.
///
/// Created via `ring_buffer_create(name, capacity)` or `ring_buffer_open(name)`.
#[pyclass(name = "RingBuffer", module = "whitemagic_rust.inference")]
pub struct PyRingBuffer {
    inner: Option<RustRingBuffer>,
}

#[pymethods]
impl PyRingBuffer {
    /// Try to write raw bytes to the buffer.
    /// Returns True if written, False if buffer is full.
    fn try_write(&self, data: &[u8]) -> bool {
        if let Some(ref rb) = self.inner {
            rb.try_write(data)
        } else {
            false
        }
    }

    /// Try to read a message from the buffer.
    /// Returns bytes if available, None if empty.
    fn try_read(&self) -> Option<Vec<u8>> {
        if let Some(ref rb) = self.inner {
            rb.try_read()
        } else {
            None
        }
    }

    /// Try to write a fixed-size element (no length prefix).
    fn try_write_fixed(&self, data: &[u8]) -> bool {
        if let Some(ref rb) = self.inner {
            rb.try_write_fixed(data)
        } else {
            false
        }
    }

    /// Try to read a fixed-size element (no length prefix).
    fn try_read_fixed(&self) -> Option<Vec<u8>> {
        if let Some(ref rb) = self.inner {
            rb.try_read_fixed()
        } else {
            None
        }
    }

    /// Get fill level as a fraction (0.0 to 1.0).
    fn fill_level(&self) -> f32 {
        if let Some(ref rb) = self.inner {
            rb.fill_level()
        } else {
            0.0
        }
    }

    /// Get number of bytes available to read.
    fn available(&self) -> u64 {
        if let Some(ref rb) = self.inner {
            rb.available()
        } else {
            0
        }
    }

    /// Get the buffer name.
    #[getter]
    fn name(&self) -> String {
        if let Some(ref rb) = self.inner {
            rb.name().to_string()
        } else {
            String::new()
        }
    }

    /// Check if this instance is the owner (creator/producer).
    #[getter]
    fn is_owner(&self) -> bool {
        if let Some(ref rb) = self.inner {
            rb.is_owner()
        } else {
            false
        }
    }

    /// Get the buffer capacity in bytes.
    #[getter]
    fn capacity(&self) -> u64 {
        if let Some(ref rb) = self.inner {
            rb.capacity()
        } else {
            0
        }
    }

    /// Close the ring buffer and release resources.
    /// If owner, unlinks the SHM file.
    fn close(&mut self) -> PyResult<()> {
        if let Some(rb) = self.inner.take() {
            rb.close().map_err(|e| {
                pyo3::exceptions::PyRuntimeError::new_err(format!("Ring buffer close error: {}", e))
            })?;
        }
        Ok(())
    }

    fn __repr__(&self) -> String {
        if let Some(ref rb) = self.inner {
            format!(
                "RingBuffer(name='{}', capacity={}, fill={:.1}%)",
                rb.name(),
                rb.capacity(),
                rb.fill_level() * 100.0
            )
        } else {
            "RingBuffer(closed)".to_string()
        }
    }
}

impl Drop for PyRingBuffer {
    fn drop(&mut self) {
        // Drop the inner RingBuffer (munmaps but doesn't unlink unless owner called close)
        self.inner.take();
    }
}

/// Create a new ring buffer in shared memory.
///
/// Args:
///   name: Buffer name (creates /dev/shm/wm_trigram_{name})
///   capacity: Data capacity in bytes (excluding 64-byte header)
///
/// Returns:
///   RingBuffer instance
#[pyfunction]
fn ring_buffer_create(name: String, capacity: usize) -> PyResult<PyRingBuffer> {
    RustRingBuffer::create(&name, capacity)
        .map(|rb| PyRingBuffer { inner: Some(rb) })
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Ring buffer create error: {}", e))
        })
}

/// Open an existing ring buffer.
///
/// Args:
///   name: Buffer name (opens /dev/shm/wm_trigram_{name})
///
/// Returns:
///   RingBuffer instance
#[pyfunction]
fn ring_buffer_open(name: String) -> PyResult<PyRingBuffer> {
    RustRingBuffer::open(&name)
        .map(|rb| PyRingBuffer { inner: Some(rb) })
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Ring buffer open error: {}", e))
        })
}

// ── Trigram Pool PyO3 bindings ─────────────────────────────────────────

/// Core-pinned 8-trigram thread pool for parallel cognition.
///
/// Created via `trigram_pool_new()`. Manages 56 ring buffers (8×7 pairs)
/// and provides send/recv for inter-trigram communication.
#[pyclass(name = "TrigramPool", module = "whitemagic_rust.inference")]
pub struct PyTrigramPool {
    inner: Option<RustTrigramPool>,
}

#[pymethods]
impl PyTrigramPool {
    /// Send a message from one trigram to another.
    ///
    /// Args:
    ///   from_trigram: Sender trigram name (e.g., "Qian")
    ///   to_trigram: Receiver trigram name (e.g., "Li")
    ///   data: Bytes to send
    ///
    /// Returns:
    ///   True if sent, False if buffer is full
    fn send(&self, from_trigram: &str, to_trigram: &str, data: &[u8]) -> PyResult<bool> {
        let from = parse_trigram(from_trigram)?;
        let to = parse_trigram(to_trigram)?;
        if let Some(ref pool) = self.inner {
            Ok(pool.send(from, to, data))
        } else {
            Ok(false)
        }
    }

    /// Receive a message for a specific trigram.
    ///
    /// Args:
    ///   for_trigram: Receiver trigram name
    ///
    /// Returns:
    ///   Bytes if available, None if empty
    fn recv(&self, for_trigram: &str) -> PyResult<Option<Vec<u8>>> {
        let tri = parse_trigram(for_trigram)?;
        if let Some(ref pool) = self.inner {
            Ok(pool.recv(tri))
        } else {
            Ok(None)
        }
    }

    /// Set the active state of a trigram (called by Wu Xing controller).
    ///
    /// Args:
    ///   trigram: Trigram name
    ///   active: True to activate, False to deactivate
    fn set_active(&self, trigram: &str, active: bool) -> PyResult<()> {
        let tri = parse_trigram(trigram)?;
        if let Some(ref pool) = self.inner {
            pool.set_active(tri, active);
        }
        Ok(())
    }

    /// Check if a trigram is active.
    ///
    /// Args:
    ///   trigram: Trigram name
    ///
    /// Returns:
    ///   True if active
    fn is_active(&self, trigram: &str) -> PyResult<bool> {
        let tri = parse_trigram(trigram)?;
        if let Some(ref pool) = self.inner {
            Ok(pool.is_active(tri))
        } else {
            Ok(false)
        }
    }

    /// Check if the pool is running (threads started).
    #[getter]
    fn is_running(&self) -> bool {
        if let Some(ref pool) = self.inner {
            pool.is_running()
        } else {
            false
        }
    }

    /// Get status of all trigrams.
    ///
    /// Returns:
    ///   List of dicts with trigram, core_id, is_active, is_running, messages_sent, messages_received
    fn status(&self, py: Python<'_>) -> PyResult<PyObject> {
        if let Some(ref pool) = self.inner {
            let statuses = pool.status();
            let py_statuses: Vec<PyObject> = statuses
                .into_iter()
                .map(|s| {
                    let dict = pyo3::types::PyDict::new_bound(py);
                    dict.set_item("trigram", s.trigram.name()).unwrap();
                    dict.set_item("core_id", s.core_id).unwrap();
                    dict.set_item("is_active", s.is_active).unwrap();
                    dict.set_item("is_running", s.is_running).unwrap();
                    dict.set_item("messages_sent", s.messages_sent).unwrap();
                    dict.set_item("messages_received", s.messages_received).unwrap();
                    dict.to_object(py)
                })
                .collect();
            Ok(PyList::new_bound(py, py_statuses).to_object(py))
        } else {
            Ok(PyList::empty_bound(py).to_object(py))
        }
    }

    /// Get the list of all 8 trigram names.
    #[staticmethod]
    fn all_trigrams() -> Vec<String> {
        Trigram::all().iter().map(|t| t.name().to_string()).collect()
    }

    /// Get the core ID for a trigram.
    #[staticmethod]
    fn core_id(trigram: &str) -> PyResult<usize> {
        let tri = parse_trigram(trigram)?;
        Ok(tri.core_id())
    }

    /// Get the cognitive function for a trigram.
    #[staticmethod]
    fn trigram_function(trigram: &str) -> PyResult<String> {
        let tri = parse_trigram(trigram)?;
        Ok(tri.function().to_string())
    }

    fn __repr__(&self) -> String {
        if let Some(ref pool) = self.inner {
            format!(
                "TrigramPool(running={}, active_trigrams={})",
                pool.is_running(),
                Trigram::all()
                    .iter()
                    .filter(|t| pool.is_active(**t))
                    .map(|t| t.name())
                    .collect::<Vec<_>>()
                    .join(",")
            )
        } else {
            "TrigramPool(closed)".to_string()
        }
    }
}

impl Drop for PyTrigramPool {
    fn drop(&mut self) {
        // TrigramPool::drop stops threads and cleans up SHM files
        self.inner.take();
    }
}

/// Create a new trigram pool with 56 ring buffers.
///
/// Returns:
///   TrigramPool instance
#[pyfunction]
fn trigram_pool_new() -> PyResult<PyTrigramPool> {
    RustTrigramPool::new()
        .map(|pool| PyTrigramPool { inner: Some(pool) })
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!("Trigram pool create error: {}", e))
        })
}

// ── SIMD vector operations (AVX2+FMA, cache-tiled) ──

/// Batch cosine similarity between a query vector and a matrix of vectors.
/// Uses AVX2+FMA with L1 cache tiling. Vectors should be pre-normalized.
/// List-based interface (slower — use py_batch_cosine_numpy for numpy arrays).
#[pyfunction]
fn py_batch_cosine_similarity(
    query: Vec<f32>,
    matrix: Vec<f32>,
    dim: usize,
) -> Vec<f32> {
    let num_vectors = matrix.len() / dim;
    let mut results = vec![0.0f32; num_vectors];
    simd_ops::batch_cosine_similarity_simd(&query, &matrix, dim, &mut results);
    results
}

/// Batch cosine similarity using numpy arrays (zero-copy, GIL-released).
/// This is the fast path — use this when calling from numpy-based code.
#[pyfunction]
fn py_batch_cosine_numpy(
    py: Python<'_>,
    query: PyReadonlyArray1<'_, f32>,
    matrix: PyReadonlyArray2<'_, f32>,
) -> PyResult<Py<PyArray1<f32>>> {
    let q = query.as_slice().map_err(|_| {
        pyo3::exceptions::PyValueError::new_err("query must be contiguous")
    })?;
    let m = matrix.as_slice().map_err(|_| {
        pyo3::exceptions::PyValueError::new_err("matrix must be contiguous")
    })?;
    let dim = q.len();
    let num_vectors = m.len() / dim;

    let result = py.allow_threads(|| {
        let mut scores = vec![0.0f32; num_vectors];
        simd_ops::batch_cosine_similarity_simd(q, m, dim, &mut scores);
        scores
    });

    Ok(PyArray1::from_vec(py, result).into())
}

/// Batch dot product between a query vector and a matrix of vectors.
#[pyfunction]
fn py_batch_dot_product(
    query: Vec<f32>,
    matrix: Vec<f32>,
    dim: usize,
) -> Vec<f32> {
    let num_vectors = matrix.len() / dim;
    let mut results = vec![0.0f32; num_vectors];
    simd_ops::batch_dot_product_simd(&query, &matrix, dim, &mut results);
    results
}

/// Batch Euclidean distance between a query vector and a matrix of vectors.
#[pyfunction]
fn py_batch_euclidean_distance(
    query: Vec<f32>,
    matrix: Vec<f32>,
    dim: usize,
) -> Vec<f32> {
    let num_vectors = matrix.len() / dim;
    let mut results = vec![0.0f32; num_vectors];
    simd_ops::batch_euclidean_distance_simd(&query, &matrix, dim, &mut results);
    results
}

/// Batch circular convolution (HRR bind) using FFT for dim > 64.
/// O(n log n) per vector vs O(n²) for direct computation.
/// List-based interface.
#[pyfunction]
fn py_batch_circular_convolution(
    queries: Vec<f32>,
    relation: Vec<f32>,
    dim: usize,
    n_vectors: usize,
) -> Vec<f32> {
    let mut results = vec![0.0f32; n_vectors * dim];
    simd_ops::batch_circular_convolution_fft(&queries, &relation, dim, n_vectors, &mut results);
    results
}

/// Batch circular convolution using numpy arrays (zero-copy, GIL-released).
/// FFT-based HRR bind for dim > 64. This is the fast path.
#[pyfunction]
fn py_batch_circular_convolution_numpy(
    py: Python<'_>,
    queries: PyReadonlyArray2<'_, f32>,
    relation: PyReadonlyArray1<'_, f32>,
) -> PyResult<Py<PyArray2<f32>>> {
    let q = queries.as_slice().map_err(|_| {
        pyo3::exceptions::PyValueError::new_err("queries must be contiguous")
    })?;
    let r = relation.as_slice().map_err(|_| {
        pyo3::exceptions::PyValueError::new_err("relation must be contiguous")
    })?;
    let dim = r.len();
    let n_vectors = q.len() / dim;

    let result = py.allow_threads(|| {
        let mut out = vec![0.0f32; n_vectors * dim];
        simd_ops::batch_circular_convolution_fft(q, r, dim, n_vectors, &mut out);
        out
    });

    let result_2d: Vec<Vec<f32>> = result.chunks(dim).map(|c| c.to_vec()).collect();
    let py_array = PyArray2::from_vec2(py, &result_2d)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Array creation: {:?}", e)))?;
    Ok(py_array.into())
}

/// Batch top-k cosine similarity: find k most similar vectors.
/// Returns list of (index, score) tuples.
#[pyfunction]
fn py_batch_topk(
    query: Vec<f32>,
    matrix: Vec<f32>,
    dim: usize,
    num_vectors: usize,
    k: usize,
) -> Vec<(usize, f32)> {
    let mut indices = vec![0usize; k];
    let mut scores = vec![0.0f32; k];
    let count = simd_ops::batch_topk_simd(&query, &matrix, dim, num_vectors, k, &mut indices, &mut scores);
    indices[..count].iter().zip(scores[..count].iter()).map(|(&i, &s)| (i, s)).collect()
}

/// Check which SIMD backend is available.
#[pyfunction]
fn py_simd_backend() -> String {
    if is_x86_feature_detected!("avx2") && is_x86_feature_detected!("fma") {
        "avx2+fma".to_string()
    } else if is_x86_feature_detected!("avx2") {
        "avx2".to_string()
    } else {
        "scalar".to_string()
    }
}

/// Batch pack embeddings: numpy (N, dim) f32 array → Vec<Vec<u8>> blobs for SQLite.
/// Each blob is dim * 4 bytes (little-endian f32).
/// Replaces Python struct.pack loop.
#[pyfunction]
fn py_batch_pack_embeddings(
    py: Python<'_>,
    embeddings: PyReadonlyArray2<'_, f32>,
) -> Vec<Vec<u8>> {
    let emb = embeddings.as_slice().unwrap_or(&[]);
    if emb.is_empty() {
        return Vec::new();
    }
    let n = embeddings.len().unwrap_or(0);
    if n == 0 {
        return Vec::new();
    }
    let dim = emb.len() / n;
    emb.chunks(dim)
        .map(|row| {
            let mut blob = Vec::with_capacity(dim * 4);
            for &v in row {
                blob.extend_from_slice(&v.to_le_bytes());
            }
            blob
        })
        .collect()
}

/// Batch unpack embeddings: Vec<(id, blob_bytes)> → numpy (N, dim) f32 array + Vec<String> ids.
/// Returns (ids_list, embeddings_array) — replaces Python struct.unpack loop.
#[pyfunction]
fn py_batch_unpack_embeddings(
    py: Python<'_>,
    ids: Vec<String>,
    blobs: Vec<Vec<u8>>,
) -> (Vec<String>, Py<PyArray2<f32>>) {
    let mut max_dim = 0;
    for blob in &blobs {
        let dim = blob.len() / 4;
        if dim > max_dim {
            max_dim = dim;
        }
    }

    let n = ids.len();
    let mut flat = vec![0.0f32; n * max_dim];
    for (i, blob) in blobs.iter().enumerate() {
        let dim = blob.len() / 4;
        for j in 0..dim {
            let bytes = [blob[j * 4], blob[j * 4 + 1], blob[j * 4 + 2], blob[j * 4 + 3]];
            flat[i * max_dim + j] = f32::from_le_bytes(bytes);
        }
    }

    let rows: Vec<Vec<f32>> = flat.chunks(max_dim).map(|c| c.to_vec()).collect();
    let arr = PyArray2::from_vec2(py, &rows)
        .unwrap_or_else(|_| PyArray2::zeros(py, [n, max_dim], false));
    (ids, arr.into())
}

#[pymodule]
pub fn inference(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_pack_ternary, m)?)?;
    m.add_function(wrap_pyfunction!(py_pack_ternary_matrix, m)?)?;
    m.add_function(wrap_pyfunction!(py_unpack_ternary, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_gemv, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_dot, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_gemv_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_ternary_backend, m)?)?;

    // Ring buffer bindings
    m.add_function(wrap_pyfunction!(ring_buffer_create, m)?)?;
    m.add_function(wrap_pyfunction!(ring_buffer_open, m)?)?;
    m.add_class::<PyRingBuffer>()?;

    // Trigram pool bindings
    m.add_function(wrap_pyfunction!(trigram_pool_new, m)?)?;
    m.add_class::<PyTrigramPool>()?;

    // SIMD vector operations
    m.add_function(wrap_pyfunction!(py_batch_cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_cosine_numpy, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_euclidean_distance, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_circular_convolution, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_circular_convolution_numpy, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_topk, m)?)?;
    m.add_function(wrap_pyfunction!(py_simd_backend, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_pack_embeddings, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_unpack_embeddings, m)?)?;

    m.add("__doc__", "WhiteMagic inference acceleration — ternary SIMD, ring buffers, trigram pool, FMA vector ops")?;
    Ok(())
}
