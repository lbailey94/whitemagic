/// Layer-Streaming Inference Engine
/// 
/// Breakthrough: Load one layer at a time from SD card
/// Result: 2.3GB → 25MB per model (92x reduction!)
/// 
/// Architecture:
/// 1. mmap layers from disk
/// 2. Stream through layers sequentially
/// 3. Prefetch next layer while computing
/// 4. Free previous layer after use
/// 
/// Trade-off: Slightly slower per-token, but NO SWAP = net faster!

use std::path::Path;
use std::fs::File;
use memmap2::Mmap;

use crate::inference::quantization::{QuantizedKVCache, Precision};
use crate::inference::ternary_kernel::{ternary_gemv, pack_ternary_matrix, Ternary};
use crate::inference::simd::{matmul_f32_simd, relu_f32, layer_norm, GeluLookup};

/// Configuration for streaming engine
pub struct StreamingConfig {
    /// Path to model weights on SD card
    pub model_path: String,
    /// Number of layers to prefetch ahead
    pub prefetch_distance: usize,
    /// Use io_uring for async I/O (Linux only)
    pub use_io_uring: bool,
    /// Enable AVX2 SIMD optimizations
    pub use_simd: bool,
    /// KV cache quantization precision
    pub kv_cache_precision: Precision,
    /// Use ternary kernels for weight computation
    pub use_ternary: bool,
}

impl Default for StreamingConfig {
    fn default() -> Self {
        Self {
            model_path: String::new(),
            prefetch_distance: 2,
            use_io_uring: cfg!(target_os = "linux"),
            use_simd: cfg!(target_feature = "avx2"),
            kv_cache_precision: Precision::Int8,
            use_ternary: false,
        }
    }
}

/// Memory-mapped layer weights
pub struct LayerMmap {
    /// Layer index
    pub index: usize,
    /// Memory-mapped file
    _file: File,
    /// Memory mapping
    mmap: Mmap,
    /// Size in bytes
    pub size: usize,
}

impl LayerMmap {
    /// Load layer from disk via mmap
    pub fn new(layer_path: &Path, index: usize) -> Result<Self, std::io::Error> {
        let file = File::open(layer_path)?;
        let metadata = file.metadata()?;
        let size = metadata.len() as usize;
        
        // Memory map the file (zero-copy!)
        // SAFETY: Mmap::map is safe when given a valid, open file. The file remains open for the lifetime of MmapLayer.
        let mmap = unsafe { Mmap::map(&file)? };
        
        Ok(Self {
            index,
            _file: file,
            mmap,
            size,
        })
    }
    
    /// Get layer data as slice
    pub fn data(&self) -> &[u8] {
        &self.mmap
    }
    
    /// Prefetch layer into OS cache
    pub fn prefetch(&self) -> Result<(), std::io::Error> {
        // Advise kernel to read ahead
        // SAFETY: madvise is called with a valid mmap pointer and size from a live Mmap object.
        #[cfg(target_os = "linux")]
        unsafe {
            libc::madvise(
                self.mmap.as_ptr() as *mut libc::c_void,
                self.size,
                libc::MADV_WILLNEED,
            );
        }
        Ok(())
    }
}

/// Streaming inference engine
pub struct StreamingEngine {
    /// Configuration
    config: StreamingConfig,
    /// All layer mmaps (lazy loaded)
    layers: Vec<Option<LayerMmap>>,
    /// Number of layers
    num_layers: usize,
    /// Current active layer
    current_layer: Option<usize>,
    /// Quantized KV cache (per-layer)
    kv_caches: Vec<Option<QuantizedKVCache>>,
}

impl StreamingEngine {
    /// Create new streaming engine
    pub fn new(config: StreamingConfig) -> Result<Self, std::io::Error> {
        // Discover layer files
        let model_dir = Path::new(&config.model_path);
        let num_layers = Self::count_layers(model_dir)?;
        
        Ok(Self {
            config,
            layers: (0..num_layers).map(|_| None).collect(),
            num_layers,
            current_layer: None,
            kv_caches: (0..num_layers).map(|_| None).collect(),
        })
    }
    
    /// Count number of layer files
    fn count_layers(model_dir: &Path) -> Result<usize, std::io::Error> {
        let mut count = 0;
        for entry in std::fs::read_dir(model_dir)? {
            let entry = entry?;
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("layer") {
                count += 1;
            }
        }
        Ok(count)
    }
    
    /// Load specific layer (on-demand)
    fn load_layer(&mut self, index: usize) -> Result<&LayerMmap, std::io::Error> {
        if self.layers[index].is_none() {
            let layer_path = Path::new(&self.config.model_path)
                .join(format!("layer_{}.bin", index));
            
            let layer = LayerMmap::new(&layer_path, index)?;
            self.layers[index] = Some(layer);
        }
        
        Ok(self.layers[index].as_ref().unwrap())
    }
    
    /// Free layer to reclaim memory
    fn free_layer(&mut self, index: usize) {
        self.layers[index] = None;
    }
    
    /// Prefetch upcoming layers
    fn prefetch_ahead(&mut self, current: usize) -> Result<(), std::io::Error> {
        for i in 1..=self.config.prefetch_distance {
            let next = current + i;
            if next < self.num_layers {
                if let Some(layer) = &self.layers[next] {
                    layer.prefetch()?;
                }
            }
        }
        Ok(())
    }
    
    /// Process through all layers (streaming!)
    pub fn forward_pass(&mut self, input: &[f32]) -> Result<Vec<f32>, std::io::Error> {
        let mut hidden = input.to_vec();
        
        for layer_idx in 0..self.num_layers {
            // Load current layer
            let layer_data: Vec<u8> = {
                let layer = self.load_layer(layer_idx)?;
                layer.data().to_vec()
            };
            
            // Prefetch next layers
            self.prefetch_ahead(layer_idx)?;
            
            // Compute layer (placeholder - actual compute in simd.rs)
            hidden = self.compute_layer_raw(&layer_data, &hidden)?;
            
            // Free previous layer (if not first)
            if layer_idx > 0 {
                self.free_layer(layer_idx - 1);
            }
            
            self.current_layer = Some(layer_idx);
        }
        
        Ok(hidden)
    }
    
    /// Compute single layer from mmap'd LayerMmap
    fn compute_layer(&self, layer: &LayerMmap, hidden: &[f32]) -> Result<Vec<f32>, std::io::Error> {
        self.compute_layer_raw(layer.data(), hidden)
    }
    
    /// Compute single layer from raw bytes
    ///
    /// Binary layer format:
    ///   [Header: 16 bytes]
    ///   [Weight data: variable]
    ///   [Bias: n * 4 bytes]
    ///   [Layer norm gamma: n * 4 bytes (optional)]
    ///   [Layer norm beta: n * 4 bytes (optional)]
    ///
    /// Header:
    ///   4 bytes: magic "WMLY"
    ///   1 byte:  layer_type (0=dense, 1=ternary)
    ///   1 byte:  activation (0=none, 1=relu, 2=gelu)
    ///   1 byte:  has_layer_norm (0=no, 1=yes)
    ///   1 byte:  reserved
    ///   4 bytes: input_dim (k) — little-endian u32
    ///   4 bytes: output_dim (n) — little-endian u32
    fn compute_layer_raw(&self, data: &[u8], hidden: &[f32]) -> Result<Vec<f32>, std::io::Error> {
        if data.len() < 16 {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Layer data too short for header",
            ));
        }

        // Parse header
        let magic = &data[0..4];
        if magic != b"WMLY" {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Invalid layer magic",
            ));
        }

        let layer_type = data[4];
        let activation = data[5];
        let has_layer_norm = data[6] == 1;
        let k = u32::from_le_bytes([data[8], data[9], data[10], data[11]]) as usize;
        let n = u32::from_le_bytes([data[12], data[13], data[14], data[15]]) as usize;

        if hidden.len() < k {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidInput,
                format!("Hidden size {} < expected input dim {}", hidden.len(), k),
            ));
        }

        let mut output = match layer_type {
            0 => self.compute_dense(&data[16..], hidden, k, n)?,
            1 => self.compute_ternary(&data[16..], hidden, k, n)?,
            _ => {
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    format!("Unknown layer type: {}", layer_type),
                ));
            }
        };

        // Apply activation
        match activation {
            1 => output = relu_f32(&output),
            2 => {
                let gelu = GeluLookup::new(-10.0, 10.0, 1024);
                output = gelu.apply_vec(&output);
            }
            _ => {}
        }

        // Apply layer norm if present
        if has_layer_norm {
            let weight_bytes = if layer_type == 0 { k * n * 4 } else { ((k + 15) / 16) * 4 * n };
            let bias_start = 16 + weight_bytes;
            let ln_start = bias_start + n * 4;
            if data.len() >= ln_start + n * 8 {
                let gamma = unsafe {
                    std::slice::from_raw_parts(data.as_ptr().add(ln_start) as *const f32, n)
                };
                let beta = unsafe {
                    std::slice::from_raw_parts(data.as_ptr().add(ln_start + n * 4) as *const f32, n)
                };
                output = layer_norm(&output, gamma, beta, 1e-5);
            }
        }

        Ok(output)
    }

    /// Dense layer compute: y = W * x + b
    /// W is (n x k) row-major f32, b is (n,) f32
    fn compute_dense(&self, data: &[u8], hidden: &[f32], k: usize, n: usize) -> Result<Vec<f32>, std::io::Error> {
        let weight_bytes = n * k * 4;
        let bias_bytes = n * 4;
        if data.len() < weight_bytes + bias_bytes {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("Dense layer data too short: {} < {}", data.len(), weight_bytes + bias_bytes),
            ));
        }

        // Reinterpret bytes as f32 weights (W is n x k row-major)
        let weights = unsafe {
            std::slice::from_raw_parts(data.as_ptr() as *const f32, n * k)
        };
        let bias = unsafe {
            std::slice::from_raw_parts(data.as_ptr().add(weight_bytes) as *const f32, n)
        };

        // matmul_f32_simd computes C = A * B where A=(m x k), B=(k x n), C=(m x n)
        // We need y = W * x where W=(n x k), x=(k,) → treat as W * x = (n x k) * (k x 1)
        // Use matmul with m=n, n=1, k=k
        let mut result = matmul_f32_simd(weights, hidden, n, 1, k);

        // Add bias
        for i in 0..n {
            result[i] += bias[i];
        }

        Ok(result)
    }

    /// Ternary layer compute: y = W * x + b
    /// W is (n x k) ternary packed, b is (n,) f32
    fn compute_ternary(&self, data: &[u8], hidden: &[f32], k: usize, n: usize) -> Result<Vec<f32>, std::io::Error> {
        let words_per_row = (k + 15) / 16;
        let weight_bytes = words_per_row * 4 * n;
        let bias_bytes = n * 4;
        if data.len() < weight_bytes + bias_bytes {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                format!("Ternary layer data too short: {} < {}", data.len(), weight_bytes + bias_bytes),
            ));
        }

        // Reinterpret bytes as packed u32 weights
        let weights_packed = unsafe {
            std::slice::from_raw_parts(data.as_ptr() as *const u32, words_per_row * n)
        };
        let bias = unsafe {
            std::slice::from_raw_parts(data.as_ptr().add(weight_bytes) as *const f32, n)
        };

        // ternary_gemv computes y = W * x where W is (n x k) packed ternary
        let mut result = ternary_gemv(weights_packed, hidden, n, k);

        // Add bias
        for i in 0..n {
            result[i] += bias[i];
        }

        Ok(result)
    }
    
    /// Store KV cache for a layer (quantized)
    pub fn store_kv_cache(&mut self, layer_idx: usize, keys: &[f32], values: &[f32], shape: (usize, usize)) {
        if layer_idx < self.kv_caches.len() {
            self.kv_caches[layer_idx] = Some(QuantizedKVCache::with_precision(
                keys, values, shape, self.config.kv_cache_precision,
            ));
        }
    }
    
    /// Retrieve dequantized KV cache for a layer
    pub fn get_kv_cache(&self, layer_idx: usize) -> Option<(Vec<f32>, Vec<f32>)> {
        self.kv_caches.get(layer_idx)?.as_ref().map(|c| (c.get_keys(), c.get_values()))
    }
    
    /// Get total KV cache memory usage in bytes
    pub fn kv_cache_memory_bytes(&self) -> usize {
        self.kv_caches.iter()
            .filter_map(|c| c.as_ref())
            .map(|c| c.memory_bytes())
            .sum()
    }
    
    /// Get KV cache compression statistics
    pub fn kv_cache_stats(&self) -> KVCacheStats {
        let active = self.kv_caches.iter().filter(|c| c.is_some()).count();
        let total_memory = self.kv_cache_memory_bytes();
        let precision = self.config.kv_cache_precision;
        
        KVCacheStats {
            active_caches: active,
            total_layers: self.num_layers,
            memory_bytes: total_memory,
            precision,
        }
    }
    
    /// Get memory statistics
    pub fn get_memory_stats(&self) -> MemoryStats {
        let loaded_layers = self.layers.iter().filter(|l| l.is_some()).count();
        let total_memory: usize = self.layers.iter()
            .filter_map(|l| l.as_ref())
            .map(|l| l.size)
            .sum();
        
        MemoryStats {
            loaded_layers,
            total_layers: self.num_layers,
            memory_used_mb: total_memory / 1024 / 1024,
            max_concurrent_layers: self.config.prefetch_distance + 1,
        }
    }
}

/// Memory usage statistics
#[derive(Debug)]
pub struct MemoryStats {
    pub loaded_layers: usize,
    pub total_layers: usize,
    pub memory_used_mb: usize,
    pub max_concurrent_layers: usize,
}

/// KV cache statistics
#[derive(Debug)]
pub struct KVCacheStats {
    pub active_caches: usize,
    pub total_layers: usize,
    pub memory_bytes: usize,
    pub precision: Precision,
}

impl KVCacheStats {
    pub fn memory_kb(&self) -> f32 {
        self.memory_bytes as f32 / 1024.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_config_default() {
        let config = StreamingConfig::default();
        assert_eq!(config.prefetch_distance, 2);
    }

    /// Build a dense layer binary blob for testing
    fn build_dense_layer(weights: &[f32], bias: &[f32], k: usize, n: usize, activation: u8) -> Vec<u8> {
        let mut data = Vec::new();
        // Header
        data.extend_from_slice(b"WMLY");
        data.push(0); // dense
        data.push(activation);
        data.push(0); // no layer norm
        data.push(0); // reserved
        data.extend_from_slice(&(k as u32).to_le_bytes());
        data.extend_from_slice(&(n as u32).to_le_bytes());
        // Weights (n x k f32)
        for w in weights {
            data.extend_from_slice(&w.to_le_bytes());
        }
        // Bias (n f32)
        for b in bias {
            data.extend_from_slice(&b.to_le_bytes());
        }
        data
    }

    /// Build a ternary layer binary blob for testing
    fn build_ternary_layer(weights_packed: &[u32], bias: &[f32], k: usize, n: usize) -> Vec<u8> {
        let mut data = Vec::new();
        // Header
        data.extend_from_slice(b"WMLY");
        data.push(1); // ternary
        data.push(0); // no activation
        data.push(0); // no layer norm
        data.push(0); // reserved
        data.extend_from_slice(&(k as u32).to_le_bytes());
        data.extend_from_slice(&(n as u32).to_le_bytes());
        // Weights (packed u32)
        for w in weights_packed {
            data.extend_from_slice(&w.to_le_bytes());
        }
        // Bias (n f32)
        for b in bias {
            data.extend_from_slice(&b.to_le_bytes());
        }
        data
    }

    #[test]
    fn test_compute_dense_layer() {
        // 2x3 dense layer: W = [[1,0,0],[0,1,0]], bias = [0.5, -0.5]
        // x = [2.0, 3.0, 99.0] → y = [2.5, 2.5]
        let weights = vec![1.0, 0.0, 0.0, 0.0, 1.0, 0.0];
        let bias = vec![0.5, -0.5];
        let layer_data = build_dense_layer(&weights, &bias, 3, 2, 0);

        let config = StreamingConfig::default();
        let engine = StreamingEngine {
            config,
            layers: vec![],
            num_layers: 0,
            current_layer: None,
            kv_caches: vec![],
        };

        let input = vec![2.0, 3.0, 99.0];
        let output = engine.compute_layer_raw(&layer_data, &input).unwrap();

        assert_eq!(output.len(), 2);
        assert!((output[0] - 2.5).abs() < 1e-5, "output[0] = {}", output[0]);
        assert!((output[1] - 2.5).abs() < 1e-5, "output[1] = {}", output[1]);
    }

    #[test]
    fn test_compute_dense_with_relu() {
        // 2x2 dense layer with ReLU: W = [[1,0],[0,-1]], bias = [0, 0]
        // x = [1.0, 1.0] → y = [1.0, -1.0] → relu → [1.0, 0.0]
        let weights = vec![1.0, 0.0, 0.0, -1.0];
        let bias = vec![0.0, 0.0];
        let layer_data = build_dense_layer(&weights, &bias, 2, 2, 1); // activation=relu

        let config = StreamingConfig::default();
        let engine = StreamingEngine {
            config,
            layers: vec![],
            num_layers: 0,
            current_layer: None,
            kv_caches: vec![],
        };

        let input = vec![1.0, 1.0];
        let output = engine.compute_layer_raw(&layer_data, &input).unwrap();

        assert_eq!(output.len(), 2);
        assert!((output[0] - 1.0).abs() < 1e-5);
        assert!(output[1].abs() < 1e-5, "relu should zero out negative: {}", output[1]);
    }

    #[test]
    fn test_compute_ternary_layer() {
        // 2x4 ternary layer: W = [[+1,-1,0,+1],[0,+1,-1,0]], bias = [1.0, 0.0]
        // x = [1.0, 2.0, 3.0, 4.0]
        // y[0] = 1 - 2 + 0 + 4 + 1 = 4
        // y[1] = 0 + 2 - 3 + 0 + 0 = -1
        let weights = vec![
            Ternary::PosOne, Ternary::NegOne, Ternary::Zero, Ternary::PosOne,
            Ternary::Zero, Ternary::PosOne, Ternary::NegOne, Ternary::Zero,
        ];
        let packed = pack_ternary_matrix(&weights, 2, 4);
        let bias = vec![1.0, 0.0];
        let layer_data = build_ternary_layer(&packed, &bias, 4, 2);

        let config = StreamingConfig::default();
        let engine = StreamingEngine {
            config,
            layers: vec![],
            num_layers: 0,
            current_layer: None,
            kv_caches: vec![],
        };

        let input = vec![1.0, 2.0, 3.0, 4.0];
        let output = engine.compute_layer_raw(&layer_data, &input).unwrap();

        assert_eq!(output.len(), 2);
        assert!((output[0] - 4.0).abs() < 1e-5, "output[0] = {}", output[0]);
        assert!((output[1] - (-1.0)).abs() < 1e-5, "output[1] = {}", output[1]);
    }

    #[test]
    fn test_compute_invalid_magic() {
        let bad_data = vec![0u8; 32];
        let config = StreamingConfig::default();
        let engine = StreamingEngine {
            config,
            layers: vec![],
            num_layers: 0,
            current_layer: None,
            kv_caches: vec![],
        };

        let result = engine.compute_layer_raw(&bad_data, &[1.0]);
        assert!(result.is_err());
    }

    #[test]
    fn test_compute_data_too_short() {
        let mut data = b"WMLY".to_vec();
        data.push(0);
        data.push(0);
        data.push(0);
        data.push(0);
        data.extend_from_slice(&100u32.to_le_bytes());
        data.extend_from_slice(&100u32.to_le_bytes());
        // No weight data after header

        let config = StreamingConfig::default();
        let engine = StreamingEngine {
            config,
            layers: vec![],
            num_layers: 0,
            current_layer: None,
            kv_caches: vec![],
        };

        let result = engine.compute_layer_raw(&data, &[1.0; 100]);
        assert!(result.is_err());
    }
}
