use std::path::PathBuf;

fn main() {
    let dir: PathBuf = std::env::var("WM_GEN3_EMBED_CACHE")
        .ok()
        .filter(|value| !value.trim().is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            let mut fallback = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            fallback.pop();
            fallback.pop();
            fallback.push(".fastembed_cache");
            fallback
        });
    std::fs::create_dir_all(&dir).expect("create fastembed cache dir");
    let options = fastembed::TextInitOptions::new(fastembed::EmbeddingModel::BGESmallENV15Q)
        .with_cache_dir(dir.clone())
        .with_show_download_progress(true);
    fastembed::TextEmbedding::try_new(options).expect("download fastembed model into cache");
    println!("fastembed cache ready: {}", dir.display());
}
