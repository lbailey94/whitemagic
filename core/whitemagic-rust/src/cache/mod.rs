// WhiteMagic Unified Cache — mmap-backed LRU+TTL cache with PyO3 bindings.
//
// Provides sub-microsecond cache reads via in-memory HashMap with
// parking_lot RwLock. Optional mmap persistence for cross-session survival.
//
// All WhiteMagic cache layers (QueryCache, PrefetchCache, semantic cache,
// embedding cache) can route through this single Rust service.

pub mod unified_cache;

pub use unified_cache::UnifiedCache;
