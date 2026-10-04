use std::fs::File;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use memmap2::Mmap;
use wm_gen3_zeropointfive::System05;

pub const VECTOR_FILE_MAGIC: u32 = 0x5641554C; // "VAUL"

pub struct VaultEmbedder {
    organ: Arc<System05>,
    dimension: usize,
    model_name: String,
}

impl VaultEmbedder {
    pub fn new(model_dir: Option<PathBuf>) -> Result<Self, String> {
        let dir = System05::resolve_model_dir(model_dir)
            .map_err(|e| format!("Failed to resolve System05 model dir: {e}"))?;
        let organ = Arc::new(System05::new(&dir));
        organ.ensure_loaded().map_err(|e| format!("Failed to load model: {e}"))?;

        let model_name = dir.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("potion-base-8M")
            .to_string();

        // Detect dimension with a test probe
        let probe = organ.encode_single("probe")
            .map_err(|e| format!("Probe encoding failed: {e}"))?;
        let dimension = probe.len();

        Ok(Self {
            organ,
            dimension,
            model_name,
        })
    }

    pub fn dimension(&self) -> usize {
        self.dimension
    }

    pub fn model_name(&self) -> &str {
        &self.model_name
    }

    pub fn encode_single(&self, text: &str) -> Result<Vec<f32>, String> {
        self.organ.encode_single(text).map_err(|e| format!("{e}"))
    }

    pub fn encode_batch(&self, texts: &[String]) -> Result<Vec<Vec<f32>>, String> {
        self.organ.encode_batch(texts).map_err(|e| format!("{e}"))
    }

    /// Write contiguous normalized vectors to binary format:
    /// [magic: 4B, version: 4B, count: 4B, dim: 4B] + raw float bytes
    pub fn write_vector_file<P: AsRef<Path>>(
        path: P,
        vectors: &[Vec<f32>],
        dimension: usize,
    ) -> std::io::Result<()> {
        let mut file = File::create(path)?;
        file.write_all(&VECTOR_FILE_MAGIC.to_le_bytes())?;
        file.write_all(&1u32.to_le_bytes())?; // Version 1
        file.write_all(&(vectors.len() as u32).to_le_bytes())?;
        file.write_all(&(dimension as u32).to_le_bytes())?;

        for vec in vectors {
            for &val in vec {
                file.write_all(&val.to_le_bytes())?;
            }
        }
        file.flush()?;
        Ok(())
    }

    /// Memory map vector file for zero-copy ultra-fast querying
    pub fn open_vector_mmap<P: AsRef<Path>>(path: P) -> std::io::Result<(Mmap, usize, usize)> {
        let file = File::open(path)?;
        let mmap = unsafe { Mmap::map(&file)? };

        if mmap.len() < 16 {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Vector file too short for header",
            ));
        }

        let magic = u32::from_le_bytes([mmap[0], mmap[1], mmap[2], mmap[3]]);
        if magic != VECTOR_FILE_MAGIC {
            return Err(std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "Invalid vector file magic",
            ));
        }

        let count = u32::from_le_bytes([mmap[8], mmap[9], mmap[10], mmap[11]]) as usize;
        let dim = u32::from_le_bytes([mmap[12], mmap[13], mmap[14], mmap[15]]) as usize;

        let expected_bytes = 16 + count * dim * 4;
        if mmap.len() < expected_bytes {
            return Err(std::io::Error::new(
                std::io::ErrorKind::UnexpectedEof,
                "Truncated vector file payload",
            ));
        }

        Ok((mmap, count, dim))
    }

    /// SIMD dot product scan across mmapped vectors
    pub fn scan_top_k(
        query: &[f32],
        mmap: &Mmap,
        count: usize,
        dim: usize,
        k: usize,
    ) -> Vec<(usize, f32)> {
        let data = &mmap[16..];
        let mut scores: Vec<(usize, f32)> = Vec::with_capacity(count);

        for i in 0..count {
            let offset = i * dim * 4;
            let vec_slice = &data[offset..offset + dim * 4];
            let dot = fast_dot_product(query, vec_slice, dim);
            scores.push((i, dot));
        }

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(k.min(scores.len()));
        scores
    }
}

/// Unrolled 8-wide float dot product on raw byte slice for vectorization
#[inline(always)]
fn fast_dot_product(query: &[f32], raw_bytes: &[u8], dim: usize) -> f32 {
    let mut sum0 = 0.0f32;
    let mut sum1 = 0.0f32;
    let mut sum2 = 0.0f32;
    let mut sum3 = 0.0f32;

    let chunks = dim / 4;
    let remainder = dim % 4;

    for i in 0..chunks {
        let idx = i * 16;
        let v0 = f32::from_le_bytes([raw_bytes[idx], raw_bytes[idx+1], raw_bytes[idx+2], raw_bytes[idx+3]]);
        let v1 = f32::from_le_bytes([raw_bytes[idx+4], raw_bytes[idx+5], raw_bytes[idx+6], raw_bytes[idx+7]]);
        let v2 = f32::from_le_bytes([raw_bytes[idx+8], raw_bytes[idx+9], raw_bytes[idx+10], raw_bytes[idx+11]]);
        let v3 = f32::from_le_bytes([raw_bytes[idx+12], raw_bytes[idx+13], raw_bytes[idx+14], raw_bytes[idx+15]]);

        sum0 += query[i * 4] * v0;
        sum1 += query[i * 4 + 1] * v1;
        sum2 += query[i * 4 + 2] * v2;
        sum3 += query[i * 4 + 3] * v3;
    }

    let mut total = sum0 + sum1 + sum2 + sum3;
    let base_idx = chunks * 4;
    for r in 0..remainder {
        let idx = (base_idx + r) * 4;
        let v = f32::from_le_bytes([raw_bytes[idx], raw_bytes[idx+1], raw_bytes[idx+2], raw_bytes[idx+3]]);
        total += query[base_idx + r] * v;
    }

    total
}
