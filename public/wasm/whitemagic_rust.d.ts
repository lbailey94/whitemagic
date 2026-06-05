/* tslint:disable */
/* eslint-disable */

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
 * Batch cosine similarity: compare one query vector against many candidates.
 * Returns JSON array of {index, score} sorted by score descending.
 */
export function batch_similarity(query_json: string, candidates_json: string, top_k: number): string;

/**
 * Cosine similarity between two vectors (passed as JSON arrays)
 */
export function cosine_similarity(a_json: string, b_json: string): number;

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
    readonly __wbg_edgeengine_free: (a: number, b: number) => void;
    readonly __wbg_edgerule_free: (a: number, b: number) => void;
    readonly __wbg_inferenceresult_free: (a: number, b: number) => void;
    readonly batch_similarity: (a: number, b: number, c: number, d: number, e: number) => [number, number];
    readonly cosine_similarity: (a: number, b: number, c: number, d: number) => number;
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
    readonly inferenceresult_answer: (a: number) => [number, number];
    readonly inferenceresult_confidence: (a: number) => number;
    readonly inferenceresult_method: (a: number) => [number, number];
    readonly inferenceresult_needs_cloud: (a: number) => number;
    readonly inferenceresult_tokens_saved: (a: number) => number;
    readonly quick_infer: (a: number, b: number) => [number, number];
    readonly text_search: (a: number, b: number, c: number, d: number) => [number, number];
    readonly wasm_ready: () => number;
    readonly wasm_version: () => [number, number];
    readonly __wbindgen_externrefs: WebAssembly.Table;
    readonly __wbindgen_malloc: (a: number, b: number) => number;
    readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
    readonly __wbindgen_free: (a: number, b: number, c: number) => void;
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
