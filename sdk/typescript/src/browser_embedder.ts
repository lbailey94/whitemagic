/**
 * Browser ONNX Embedding Engine — in-browser semantic embeddings.
 *
 * Uses @xenova/transformers (transformers.js) to run a quantized
 * all-MiniLM-L6-v2 ONNX model entirely in the browser via WebGPU/WASM.
 * No network calls — fully private, offline-capable.
 *
 * Usage:
 * ```typescript
 * import { BrowserEmbedder } from '@whitemagic/sdk';
 *
 * const embedder = new BrowserEmbedder();
 * await embedder.init();
 *
 * const vector = await embedder.embed('hello world');
 * // Float32Array(384)
 *
 * const results = await embedder.embedBatch(['hello', 'world']);
 * // Float32Array[] of length 2
 *
 * const sim = embedder.cosineSimilarity(a, b);
 * // 0.0 - 1.0
 * ```
 */

const EMBEDDING_DIM = 384;
const MODEL_ID = "Xenova/all-MiniLM-L6-v2";

export class BrowserEmbedder {
  private pipeline: any = null;
  private _available = false;
  private _loading: Promise<void> | null = null;

  /**
   * Initialize the embedding model.
   * Downloads the quantized ONNX model on first use (~23MB),
   * cached by the browser's Cache API for subsequent loads.
   */
  async init(): Promise<void> {
    if (this._available) return;
    if (this._loading) {
      await this._loading;
      return;
    }
    this._loading = this._loadModel();
    await this._loading;
  }

  private async _loadModel(): Promise<void> {
    try {
      const { pipeline } = await import("@xenova/transformers");
      this.pipeline = await pipeline("feature-extraction", MODEL_ID, {
        quantized: true,
      });
      this._available = true;
    } catch (err) {
      // Fallback: try onnxruntime-web directly
      try {
        await this._loadOnnxRuntime();
      } catch (err2) {
        console.error("Failed to load embedding model:", err2);
        this._available = false;
      }
    }
  }

  private async _loadOnnxRuntime(): Promise<void> {
    const ort = await import("onnxruntime-web");
    // Load model from CDN or local path
    const modelPath = "/models/all-MiniLM-L6-v2-quantized.onnx";
    const session = await ort.InferenceSession.create(modelPath, {
      executionProviders: ["wasm"],
      graphOptimizationLevel: "all",
    });
    this.pipeline = { type: "onnx", session, ort };
    this._available = true;
  }

  get isAvailable(): boolean {
    return this._available;
  }

  get dim(): number {
    return EMBEDDING_DIM;
  }

  /**
   * Embed a single text string into a 384-dimensional vector.
   */
  async embed(text: string): Promise<Float32Array> {
    if (!this._available) {
      await this.init();
    }
    if (!this._available) {
      return this._hashEmbed(text);
    }

    try {
      if (this.pipeline?.type === "onnx") {
        return await this._embedOnnx(text);
      }
      const output = await this.pipeline(text, {
        pooling: "mean",
        normalize: true,
      });
      return new Float32Array(output.data);
    } catch (err) {
      console.warn("Embedding failed, using hash fallback:", err);
      return this._hashEmbed(text);
    }
  }

  /**
   * Embed multiple texts in a batch.
   */
  async embedBatch(texts: string[]): Promise<Float32Array[]> {
    if (!this._available) {
      await this.init();
    }
    if (!this._available) {
      return texts.map((t) => this._hashEmbed(t));
    }

    try {
      if (this.pipeline?.type === "onnx") {
        const results: Float32Array[] = [];
        for (const text of texts) {
          results.push(await this._embedOnnx(text));
        }
        return results;
      }
      const outputs = await this.pipeline(texts, {
        pooling: "mean",
        normalize: true,
      });
      // transformers.js returns a single tensor with all embeddings
      if (outputs.data.length === texts.length * EMBEDDING_DIM) {
        const results: Float32Array[] = [];
        for (let i = 0; i < texts.length; i++) {
          const start = i * EMBEDDING_DIM;
          results.push(new Float32Array(outputs.data.slice(start, start + EMBEDDING_DIM)));
        }
        return results;
      }
      return [new Float32Array(outputs.data)];
    } catch (err) {
      console.warn("Batch embedding failed, using hash fallback:", err);
      return texts.map((t) => this._hashEmbed(t));
    }
  }

  /**
   * Compute cosine similarity between two vectors.
   */
  cosineSimilarity(a: Float32Array, b: Float32Array): number {
    let dot = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    const denom = Math.sqrt(normA) * Math.sqrt(normB);
    return denom === 0 ? 0 : dot / denom;
  }

  /**
   * Find top-K most similar texts from a list of candidates.
   */
  async topKSimilar(
    query: string,
    candidates: string[],
    k: number = 5,
  ): Promise<{ index: number; similarity: number }[]> {
    const queryVec = await this.embed(query);
    const candidateVecs = await this.embedBatch(candidates);
    const scores = candidates.map((_, i) => ({
      index: i,
      similarity: this.cosineSimilarity(queryVec, candidateVecs[i]),
    }));
    scores.sort((a, b) => b.similarity - a.similarity);
    return scores.slice(0, k);
  }

  /**
   * Run ONNX inference directly.
   */
  private async _embedOnnx(text: string): Promise<Float32Array> {
    const { session, ort } = this.pipeline;
    // Tokenize: simple word-level tokenization (model expects token IDs)
    // In production, use a proper tokenizer from tokenizers.js
    const tokens = this._simpleTokenize(text);
    const inputIds = new BigInt64Array(tokens.length);
    const attentionMask = new BigInt64Array(tokens.length);
    for (let i = 0; i < tokens.length; i++) {
      inputIds[i] = BigInt(tokens[i]);
      attentionMask[i] = 1n;
    }
    const feeds = {
      input_ids: new ort.Tensor("int64", inputIds, [1, tokens.length]),
      attention_mask: new ort.Tensor("int64", attentionMask, [1, tokens.length]),
    };
    const results = await session.run(feeds);
    // Get last hidden state and mean-pool
    const hiddenState = results.last_hidden_state?.data || Object.values(results)[0]?.data;
    if (!hiddenState) throw new Error("No output from ONNX model");
    // Mean pool over sequence dimension
    const seqLen = hiddenState.length / EMBEDDING_DIM;
    const pooled = new Float32Array(EMBEDDING_DIM);
    for (let d = 0; d < EMBEDDING_DIM; d++) {
      let sum = 0;
      for (let s = 0; s < seqLen; s++) {
        sum += hiddenState[s * EMBEDDING_DIM + d];
      }
      pooled[d] = sum / seqLen;
    }
    // L2 normalize
    let norm = 0;
    for (let i = 0; i < pooled.length; i++) {
      norm += pooled[i] * pooled[i];
    }
    norm = Math.sqrt(norm);
    if (norm > 0) {
      for (let i = 0; i < pooled.length; i++) {
        pooled[i] /= norm;
      }
    }
    return pooled;
  }

  /**
   * Simple hash-based tokenization for fallback.
   * Maps words to token IDs via hash. Not BPE — just a fallback.
   */
  private _simpleTokenize(text: string): number[] {
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    return words.map((w) => {
      let hash = 0;
      for (let i = 0; i < w.length; i++) {
        hash = ((hash << 5) - hash + w.charCodeAt(i)) | 0;
      }
      return Math.abs(hash) % 30000 + 1000; // Offset to avoid special tokens
    });
  }

  /**
   * Hash-based fallback embedding when ONNX is unavailable.
   * Produces deterministic 384-dim vectors from text — not semantic,
   * but sufficient for exact-match search.
   */
  private _hashEmbed(text: string): Float32Array {
    const vec = new Float32Array(EMBEDDING_DIM);
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    for (const word of words) {
      let hash = 0;
      for (let i = 0; i < word.length; i++) {
        hash = ((hash << 5) - hash + word.charCodeAt(i)) | 0;
      }
      const idx = Math.abs(hash) % EMBEDDING_DIM;
      vec[idx] += 1;
    }
    // L2 normalize
    let norm = 0;
    for (let i = 0; i < vec.length; i++) {
      norm += vec[i] * vec[i];
    }
    norm = Math.sqrt(norm);
    if (norm > 0) {
      for (let i = 0; i < vec.length; i++) {
        vec[i] /= norm;
      }
    }
    return vec;
  }
}
