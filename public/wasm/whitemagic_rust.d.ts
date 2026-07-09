/* tslint:disable */
/* eslint-disable */

export class Coordinate5D {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    id: string;
    v: number;
    w: number;
    x: number;
    y: number;
    z: number;
}

/**
 * Dharma rule engine for browser-local governance.
 */
export class DharmaEngine {
    free(): void;
    [Symbol.dispose](): void;
    add_rule(rule: DharmaRule): void;
    /**
     * Evaluate input text against all rules.
     */
    evaluate(text: string): DharmaResult;
    /**
     * List all rule IDs as JSON array.
     */
    list_rules(): string;
    constructor();
    remove_rule(id: string): boolean;
    rule_count(): number;
}

/**
 * Dharma evaluation result.
 */
export class DharmaResult {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    readonly allowed: boolean;
    readonly evaluated_rules: number;
    readonly matched_rule: string;
    readonly message: string;
}

/**
 * A Dharma rule for content governance.
 */
export class DharmaRule {
    free(): void;
    [Symbol.dispose](): void;
    constructor(id: string, pattern: string, action: string, message: string);
    readonly action: string;
    readonly id: string;
    readonly message: string;
    readonly pattern: string;
}

/**
 * Edge inference engine - WASM version
 */
export class EdgeEngine {
    free(): void;
    [Symbol.dispose](): void;
    /**
     * Add a rule to the engine
     */
    add_rule(rule: EdgeRule): void;
    /**
     * Get statistics
     */
    get_stats(): string;
    /**
     * Run inference on a query
     */
    infer(query: string): InferenceResult;
    /**
     * Get local resolution rate
     */
    local_rate(): number;
    constructor();
    /**
     * Reset statistics
     */
    reset_stats(): void;
    /**
     * Get total tokens saved
     */
    tokens_saved(): number;
}

/**
 * Edge inference rule
 */
export class EdgeRule {
    free(): void;
    [Symbol.dispose](): void;
    constructor(id: string, pattern: string, response: string, confidence: number);
    readonly confidence: number;
    readonly id: string;
    readonly response: string;
}

/**
 * Gnosis snapshot — system self-awareness summary.
 */
export class GnosisSnapshot {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    /**
     * Serialize to JSON.
     */
    to_json(): string;
    readonly dharma_rules: number;
    readonly edge_local: number;
    readonly edge_queries: number;
    readonly edge_tokens_saved: number;
    readonly karma_balance: number;
    readonly karma_entries: number;
    readonly memory_count: number;
}

export class HolographicCoordinate {
    free(): void;
    [Symbol.dispose](): void;
    constructor(x: number, y: number, z: number, w: number);
    to_vec(): Float64Array;
    w: number;
    x: number;
    y: number;
    z: number;
}

export class HolographicIndex {
    free(): void;
    [Symbol.dispose](): void;
    add(memory_id: string, x: number, y: number, z: number, w: number): void;
    constructor();
    query_nearest(x: number, y: number, z: number, w: number, n: number): string;
}

export class HolographicIndexBasic {
    free(): void;
    [Symbol.dispose](): void;
    add(id: string, x: number, y: number, z: number, w: number): void;
    constructor();
    query_nearest(x: number, y: number, z: number, w: number, k: number): string;
}

/**
 * Inference result
 */
export class InferenceResult {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    readonly answer: string;
    readonly confidence: number;
    readonly method: string;
    readonly needs_cloud: boolean;
    readonly tokens_saved: number;
}

/**
 * A karma ledger entry.
 */
export class KarmaEntry {
    private constructor();
    free(): void;
    [Symbol.dispose](): void;
    readonly action: string;
    readonly delta: number;
    readonly description: string;
    readonly id: string;
    readonly timestamp: string;
}

/**
 * Append-only karma ledger.
 */
export class KarmaLedger {
    free(): void;
    [Symbol.dispose](): void;
    /**
     * Get current karma balance.
     */
    balance(): number;
    /**
     * Get total number of entries.
     */
    count(): number;
    /**
     * Export all entries as JSON (for backup).
     */
    export_json(): string;
    constructor();
    /**
     * Get recent entries as JSON (last N entries).
     */
    recent_json(n: number): string;
    /**
     * Record a karma action. Returns the entry ID.
     */
    record(action: string, delta: number, description: string): string;
}

/**
 * In-browser memory store (HashMap-backed cache + IndexedDB persistence).
 */
export class MemoryStore {
    free(): void;
    [Symbol.dispose](): void;
    /**
     * Get count of stored memories.
     */
    count(): number;
    /**
     * Create a new memory. Returns the assigned ID.
     */
    create(title: string, content: string, tags_json: string): string;
    /**
     * Delete a memory by ID.
     */
    delete(id: string): boolean;
    /**
     * Delete a single memory from IndexedDB.
     */
    delete_persisted(id: string): Promise<boolean>;
    /**
     * Export all memories as a JSON array (for backup/transfer).
     */
    export_json(): string;
    /**
     * Hydrate the in-memory cache from IndexedDB.
     */
    hydrate(): Promise<number>;
    /**
     * Import memories from a JSON array (merge into store).
     * Returns count of memories imported.
     */
    import_json(json_str: string): number;
    /**
     * List all memories, sorted by importance (descending).
     */
    list(): string;
    constructor();
    /**
     * Persist all memories to IndexedDB (full sync).
     */
    persist(): Promise<number>;
    /**
     * Persist a single memory to IndexedDB.
     */
    persist_one(id: string): Promise<boolean>;
    /**
     * Read a memory by ID. Returns JSON or empty string if not found.
     */
    read(id: string): string;
    /**
     * Full-text search across title and content. Returns JSON array of memory IDs.
     */
    search(query: string): string;
    /**
     * Search by tag. Returns JSON array of memory IDs.
     */
    search_by_tag(tag: string): string;
    /**
     * Update a memory's content and/or title.
     */
    update(id: string, title: string, content: string): boolean;
    /**
     * Create a MemoryStore with a custom IndexedDB database name
     * (useful for multi-user isolation).
     */
    static with_db_name(db_name: string): MemoryStore;
    /**
     * Get the IndexedDB database name.
     */
    readonly db_name: string;
}

/**
 * A memory record stored in the browser.
 */
export class WasmMemory {
    free(): void;
    [Symbol.dispose](): void;
    add_tag(tag: string): void;
    constructor(id: string, title: string, content: string);
    remove_tag(tag: string): void;
    tags_json(): string;
    to_json(): string;
    content: string;
    readonly created_at: string;
    readonly id: string;
    importance: number;
    readonly memory_type: string;
    title: string;
    readonly updated_at: string;
}

/**
 * Batch cosine similarity: compare one query vector against many candidates.
 * Returns JSON array of {index, score} sorted by score descending.
 */
export function batch_similarity(query_json: string, candidates_json: string, top_k: number): string;

/**
 * Cosine similarity between two vectors (passed as JSON arrays)
 */
export function cosine_similarity(a_json: string, b_json: string): number;

export function embedding_minhash_find_duplicates(embeddings_flat: Float32Array, embedding_dim: number, threshold: number, max_results: number): string;

/**
 * Generate a Gnosis snapshot from the current system state.
 */
export function gnosis_snapshot(store: MemoryStore, karma: KarmaLedger, dharma: DharmaEngine, engine: EdgeEngine): GnosisSnapshot;

export function holographic_encode_batch(memories_json: string): string;

export function holographic_encode_single(memory_json: string): string;

/**
 * Initialize the WASM module — call once on startup.
 * Installs the panic hook for better error messages.
 */
export function init_wasm(): void;

export function main_js(): void;

export function minhash_find_duplicates(keywords_json: string, threshold: number, max_results: number): string;

export function minhash_signatures(keywords_json: string): string;

/**
 * Quick inference function (convenience)
 */
export function quick_infer(query: string): string;

/**
 * Full-text search: find substring matches in a list of texts.
 * Returns JSON array of matching indices.
 */
export function text_search(query: string, texts_json: string): string;

/**
 * Check if WASM module is loaded
 */
export function wasm_ready(): boolean;

/**
 * Get WASM version
 */
export function wasm_version(): string;

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
    readonly memory: WebAssembly.Memory;
    readonly __wbg_dharmaengine_free: (a: number, b: number) => void;
    readonly __wbg_dharmaresult_free: (a: number, b: number) => void;
    readonly __wbg_dharmarule_free: (a: number, b: number) => void;
    readonly __wbg_edgeengine_free: (a: number, b: number) => void;
    readonly __wbg_edgerule_free: (a: number, b: number) => void;
    readonly __wbg_gnosissnapshot_free: (a: number, b: number) => void;
    readonly __wbg_inferenceresult_free: (a: number, b: number) => void;
    readonly __wbg_karmaentry_free: (a: number, b: number) => void;
    readonly __wbg_karmaledger_free: (a: number, b: number) => void;
    readonly __wbg_memorystore_free: (a: number, b: number) => void;
    readonly __wbg_wasmmemory_free: (a: number, b: number) => void;
    readonly batch_similarity: (a: number, b: number, c: number, d: number, e: number) => [number, number];
    readonly cosine_similarity: (a: number, b: number, c: number, d: number) => number;
    readonly dharmaengine_add_rule: (a: number, b: number) => void;
    readonly dharmaengine_evaluate: (a: number, b: number, c: number) => number;
    readonly dharmaengine_list_rules: (a: number) => [number, number];
    readonly dharmaengine_new: () => number;
    readonly dharmaengine_remove_rule: (a: number, b: number, c: number) => number;
    readonly dharmaengine_rule_count: (a: number) => number;
    readonly dharmaresult_allowed: (a: number) => number;
    readonly dharmaresult_evaluated_rules: (a: number) => number;
    readonly dharmaresult_matched_rule: (a: number) => [number, number];
    readonly dharmaresult_message: (a: number) => [number, number];
    readonly dharmarule_action: (a: number) => [number, number];
    readonly dharmarule_id: (a: number) => [number, number];
    readonly dharmarule_message: (a: number) => [number, number];
    readonly dharmarule_new: (a: number, b: number, c: number, d: number, e: number, f: number, g: number, h: number) => number;
    readonly dharmarule_pattern: (a: number) => [number, number];
    readonly edgeengine_add_rule: (a: number, b: number) => void;
    readonly edgeengine_get_stats: (a: number) => [number, number];
    readonly edgeengine_infer: (a: number, b: number, c: number) => number;
    readonly edgeengine_local_rate: (a: number) => number;
    readonly edgeengine_new: () => number;
    readonly edgeengine_reset_stats: (a: number) => void;
    readonly edgeengine_tokens_saved: (a: number) => number;
    readonly edgerule_confidence: (a: number) => number;
    readonly edgerule_id: (a: number) => [number, number];
    readonly edgerule_new: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => number;
    readonly edgerule_response: (a: number) => [number, number];
    readonly gnosis_snapshot: (a: number, b: number, c: number, d: number) => number;
    readonly gnosissnapshot_dharma_rules: (a: number) => number;
    readonly gnosissnapshot_edge_local: (a: number) => number;
    readonly gnosissnapshot_edge_queries: (a: number) => number;
    readonly gnosissnapshot_karma_balance: (a: number) => number;
    readonly gnosissnapshot_karma_entries: (a: number) => number;
    readonly gnosissnapshot_memory_count: (a: number) => number;
    readonly gnosissnapshot_to_json: (a: number) => [number, number];
    readonly inferenceresult_answer: (a: number) => [number, number];
    readonly inferenceresult_confidence: (a: number) => number;
    readonly inferenceresult_method: (a: number) => [number, number];
    readonly inferenceresult_needs_cloud: (a: number) => number;
    readonly inferenceresult_tokens_saved: (a: number) => number;
    readonly karmaentry_action: (a: number) => [number, number];
    readonly karmaentry_delta: (a: number) => number;
    readonly karmaentry_description: (a: number) => [number, number];
    readonly karmaentry_id: (a: number) => [number, number];
    readonly karmaentry_timestamp: (a: number) => [number, number];
    readonly karmaledger_count: (a: number) => number;
    readonly karmaledger_export_json: (a: number) => [number, number];
    readonly karmaledger_new: () => number;
    readonly karmaledger_recent_json: (a: number, b: number) => [number, number];
    readonly karmaledger_record: (a: number, b: number, c: number, d: number, e: number, f: number) => [number, number];
    readonly memorystore_create: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => [number, number];
    readonly memorystore_db_name: (a: number) => [number, number];
    readonly memorystore_delete: (a: number, b: number, c: number) => number;
    readonly memorystore_delete_persisted: (a: number, b: number, c: number) => any;
    readonly memorystore_export_json: (a: number) => [number, number];
    readonly memorystore_hydrate: (a: number) => any;
    readonly memorystore_import_json: (a: number, b: number, c: number) => number;
    readonly memorystore_list: (a: number) => [number, number];
    readonly memorystore_new: () => number;
    readonly memorystore_persist: (a: number) => any;
    readonly memorystore_persist_one: (a: number, b: number, c: number) => any;
    readonly memorystore_read: (a: number, b: number, c: number) => [number, number];
    readonly memorystore_search: (a: number, b: number, c: number) => [number, number];
    readonly memorystore_search_by_tag: (a: number, b: number, c: number) => [number, number];
    readonly memorystore_update: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => number;
    readonly memorystore_with_db_name: (a: number, b: number) => number;
    readonly quick_infer: (a: number, b: number) => [number, number];
    readonly text_search: (a: number, b: number, c: number, d: number) => [number, number];
    readonly wasm_ready: () => number;
    readonly wasm_version: () => [number, number];
    readonly wasmmemory_add_tag: (a: number, b: number, c: number) => void;
    readonly wasmmemory_content: (a: number) => [number, number];
    readonly wasmmemory_created_at: (a: number) => [number, number];
    readonly wasmmemory_id: (a: number) => [number, number];
    readonly wasmmemory_importance: (a: number) => number;
    readonly wasmmemory_memory_type: (a: number) => [number, number];
    readonly wasmmemory_new: (a: number, b: number, c: number, d: number, e: number, f: number) => number;
    readonly wasmmemory_remove_tag: (a: number, b: number, c: number) => void;
    readonly wasmmemory_set_content: (a: number, b: number, c: number) => void;
    readonly wasmmemory_set_importance: (a: number, b: number) => void;
    readonly wasmmemory_set_title: (a: number, b: number, c: number) => void;
    readonly wasmmemory_tags_json: (a: number) => [number, number];
    readonly wasmmemory_title: (a: number) => [number, number];
    readonly wasmmemory_to_json: (a: number) => [number, number];
    readonly wasmmemory_updated_at: (a: number) => [number, number];
    readonly init_wasm: () => void;
    readonly gnosissnapshot_edge_tokens_saved: (a: number) => number;
    readonly karmaledger_balance: (a: number) => number;
    readonly memorystore_count: (a: number) => number;
    readonly __wbg_coordinate5d_free: (a: number, b: number) => void;
    readonly __wbg_get_coordinate5d_id: (a: number) => [number, number];
    readonly __wbg_get_coordinate5d_v: (a: number) => number;
    readonly __wbg_get_coordinate5d_w: (a: number) => number;
    readonly __wbg_get_coordinate5d_x: (a: number) => number;
    readonly __wbg_get_coordinate5d_y: (a: number) => number;
    readonly __wbg_get_coordinate5d_z: (a: number) => number;
    readonly __wbg_set_coordinate5d_id: (a: number, b: number, c: number) => void;
    readonly __wbg_set_coordinate5d_v: (a: number, b: number) => void;
    readonly __wbg_set_coordinate5d_w: (a: number, b: number) => void;
    readonly __wbg_set_coordinate5d_x: (a: number, b: number) => void;
    readonly __wbg_set_coordinate5d_y: (a: number, b: number) => void;
    readonly __wbg_set_coordinate5d_z: (a: number, b: number) => void;
    readonly holographic_encode_batch: (a: number, b: number) => [number, number, number, number];
    readonly holographic_encode_single: (a: number, b: number) => [number, number, number, number];
    readonly __wbg_holographicindexbasic_free: (a: number, b: number) => void;
    readonly holographicindexbasic_add: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => void;
    readonly holographicindexbasic_new: () => number;
    readonly holographicindexbasic_query_nearest: (a: number, b: number, c: number, d: number, e: number, f: number) => [number, number, number, number];
    readonly main_js: () => void;
    readonly minhash_find_duplicates: (a: number, b: number, c: number, d: number) => [number, number, number, number];
    readonly minhash_signatures: (a: number, b: number) => [number, number, number, number];
    readonly embedding_minhash_find_duplicates: (a: number, b: number, c: number, d: number, e: number) => [number, number, number, number];
    readonly __wbg_get_holographiccoordinate_w: (a: number) => number;
    readonly __wbg_get_holographiccoordinate_x: (a: number) => number;
    readonly __wbg_get_holographiccoordinate_y: (a: number) => number;
    readonly __wbg_get_holographiccoordinate_z: (a: number) => number;
    readonly __wbg_holographiccoordinate_free: (a: number, b: number) => void;
    readonly __wbg_holographicindex_free: (a: number, b: number) => void;
    readonly __wbg_set_holographiccoordinate_w: (a: number, b: number) => void;
    readonly __wbg_set_holographiccoordinate_x: (a: number, b: number) => void;
    readonly __wbg_set_holographiccoordinate_y: (a: number, b: number) => void;
    readonly __wbg_set_holographiccoordinate_z: (a: number, b: number) => void;
    readonly holographiccoordinate_new: (a: number, b: number, c: number, d: number) => number;
    readonly holographiccoordinate_to_vec: (a: number) => [number, number];
    readonly holographicindex_add: (a: number, b: number, c: number, d: number, e: number, f: number, g: number) => void;
    readonly holographicindex_new: () => number;
    readonly holographicindex_query_nearest: (a: number, b: number, c: number, d: number, e: number, f: number) => [number, number, number, number];
    readonly wasm_bindgen__convert__closures_____invoke__hb240e798b97a84fa: (a: number, b: number, c: any) => [number, number];
    readonly wasm_bindgen__convert__closures_____invoke__h0ca18a6293b4ae72: (a: number, b: number, c: any, d: any) => void;
    readonly wasm_bindgen__convert__closures_____invoke__h85ded4be30241e32: (a: number, b: number, c: any) => void;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __wbindgen_exn_store: (a: number) => void;
    readonly __externref_table_alloc: () => number;
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
    readonly __wbindgen_destroy_closure: (a: number, b: number) => void;
    readonly __externref_table_dealloc: (a: number) => void;
    readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;

/**
 * Instantiates the given `module`, which can either be bytes or
 * a precompiled `WebAssembly.Module`.
 *
 * @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
 *
 * @returns {InitOutput}
 */
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
 * If `module_or_path` is {RequestInfo} or {URL}, makes a request and
 * for everything else, calls `WebAssembly.instantiate` directly.
 *
 * @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
 *
 * @returns {Promise<InitOutput>}
 */
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
