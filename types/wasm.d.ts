declare module "/wasm/whitemagic_rust.js" {
  const init: (initPath: string | URL) => Promise<void>;
  export { init as default };
  export class EdgeEngine {
    constructor();
    infer(query: string): {
      answer(): string;
      confidence(): number;
      method(): string;
      needs_cloud(): boolean;
      tokens_saved(): number;
    };
    get_stats(): string;
  }
  export function cosine_similarity(a: string, b: string): number;
  export function batch_similarity(query: string, candidates: string, top_k: number): string;
  export function text_search(query: string, texts: string): string;
  export function wasm_version(): string;
  export function wasm_ready(): boolean;
}
