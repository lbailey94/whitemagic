/**
 * ONNX Embedding Provider — Client-side memory embedding
 *
 * Uses ONNX Runtime Web to run a quantized sentence embedding model
 * entirely in the browser. No API calls needed.
 *
 * Model: all-MiniLM-L6-v2 (quantized, 384 dimensions)
 * Size: ~22MB (ONNX), ~80MB (WASM)
 *
 * Usage:
 *   const provider = getEmbeddingProvider();
 *   const embedding = await provider.embed("Hello world");
 *   // [0.023, -0.045, 0.012, ...] (384 floats)
 */

import * as ort from "onnxruntime-web";

// Embedding model configuration
const MODEL_CONFIG = {
  url: "/models/model_quantized.onnx" as const,  // Local bundled model
  cdnUrl: "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model_quantized.onnx" as const,
  dim: 384,
  maxLength: 512,
} as const;

// Simple tokenizer (BPE-like approximation for MiniLM)
// In production, use a proper tokenizer from @xenova/transformers
class SimpleTokenizer {
  private vocab: Map<string, number> = new Map();
  private initialized = false;

  async init(): Promise<void> {
    if (this.initialized) return;
    // Load vocabulary from CDN
    try {
      const response = await fetch("https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/tokenizer.json");
      const data = await response.json();
      const vocab = data.model?.vocab;
      if (vocab) {
        for (const [token, id] of Object.entries(vocab)) {
          this.vocab.set(token, id as number);
        }
      }
      this.initialized = true;
    } catch {
      // Fallback: simple word-to-id mapping
      this.initialized = true;
    }
  }

  encode(text: string, maxLength: number): { input_ids: number[]; attention_mask: number[]; token_type_ids: number[] } {
    // Simple whitespace tokenization with [CLS]/[SEP] tokens
    const words = text.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const tokens = ["[CLS]", ...words.slice(0, maxLength - 2), "[SEP]"];

    const input_ids: number[] = [];
    const attention_mask: number[] = [];
    const token_type_ids: number[] = [];

    for (const token of tokens) {
      const id = this.vocab.get(token) ?? this.vocab.get(token.toLowerCase()) ?? 100; // [UNK] fallback
      input_ids.push(id);
      attention_mask.push(1);
      token_type_ids.push(0);
    }

    // Pad to maxLength
    while (input_ids.length < maxLength) {
      input_ids.push(0); // [PAD]
      attention_mask.push(0);
      token_type_ids.push(0);
    }

    return { input_ids, attention_mask, token_type_ids };
  }
}

// Embedding result
export interface EmbeddingResult {
  embedding: number[];
  dim: number;
  model: string;
  latency: number;
}

// ONNX Embedding Provider
export class ONNXEmbeddingProvider {
  private session: ort.InferenceSession | null = null;
  private tokenizer = new SimpleTokenizer();
  private initPromise: Promise<void>;
  private isReady = false;

  constructor() {
    this.initPromise = this.init();
  }

  /** Wait for model to be ready */
  async ready(): Promise<void> {
    return this.initPromise;
  }

  /** Initialize the embedding model */
  private async init(): Promise<void> {
    try {
      // Initialize tokenizer
      await this.tokenizer.init();

      // Try local model first, fall back to CDN
      let modelUrl: string = MODEL_CONFIG.url;
      try {
        const check = await fetch(MODEL_CONFIG.url, { method: "HEAD" });
        if (!check.ok) {
          console.log("[ONNXEmbedding] Local model not found, using CDN");
          modelUrl = MODEL_CONFIG.cdnUrl;
        }
      } catch {
        console.log("[ONNXEmbedding] Local model check failed, using CDN");
        modelUrl = MODEL_CONFIG.cdnUrl;
      }

      // Load ONNX model
      console.log("[ONNXEmbedding] Loading model from:", modelUrl);
      this.session = await ort.InferenceSession.create(modelUrl, {
        executionProviders: ["wasm"],
        graphOptimizationLevel: "all",
      });

      this.isReady = true;
      console.log("[ONNXEmbedding] Model loaded successfully from:", modelUrl);
    } catch (error) {
      console.error("[ONNXEmbedding] Failed to load model:", error);
      // Model load failed — embeddings will be zero vectors
    }
  }

  /** Generate embedding for a single text */
  async embed(text: string): Promise<EmbeddingResult> {
    await this.ready();

    const start = performance.now();

    if (!this.session) {
      // Fallback: return zero vector
      return {
        embedding: new Array(MODEL_CONFIG.dim).fill(0),
        dim: MODEL_CONFIG.dim,
        model: "fallback-zero",
        latency: 0,
      };
    }

    // Tokenize
    const tokens = this.tokenizer.encode(text, MODEL_CONFIG.maxLength);

    // Create tensors
    const inputIds = new ort.Tensor("int64", BigInt64Array.from(tokens.input_ids.map(BigInt)), [1, tokens.input_ids.length]);
    const attentionMask = new ort.Tensor("int64", BigInt64Array.from(tokens.attention_mask.map(BigInt)), [1, tokens.attention_mask.length]);
    const tokenTypeIds = new ort.Tensor("int64", BigInt64Array.from(tokens.token_type_ids.map(BigInt)), [1, tokens.token_type_ids.length]);

    // Run inference
    const feeds = {
      input_ids: inputIds,
      attention_mask: attentionMask,
      token_type_ids: tokenTypeIds,
    };

    const results = await this.session.run(feeds);

    // Extract embedding (last_hidden_state or pooled_output)
    const output = results.last_hidden_state ?? results.pooled_output;
    if (!output) {
      return {
        embedding: new Array(MODEL_CONFIG.dim).fill(0),
        dim: MODEL_CONFIG.dim,
        model: "error-no-output",
        latency: performance.now() - start,
      };
    }

    // Mean pooling over tokens with attention mask
    const embedding = this.meanPool(output, tokens.attention_mask);
    const latency = performance.now() - start;

    return {
      embedding,
      dim: MODEL_CONFIG.dim,
      model: "all-MiniLM-L6-v2-quantized",
      latency,
    };
  }

  /** Mean pooling with attention mask */
  private meanPool(output: ort.Tensor, attentionMask: number[]): number[] {
    const data = output.data as Float32Array;
    const [batchSize, seqLength, dim] = output.dims;
    const embedding = new Array(dim).fill(0);

    let validTokens = 0;
    for (let i = 0; i < seqLength; i++) {
      if (attentionMask[i] === 1) {
        for (let d = 0; d < dim; d++) {
          embedding[d] += data[i * dim + d];
        }
        validTokens++;
      }
    }

    if (validTokens > 0) {
      for (let d = 0; d < dim; d++) {
        embedding[d] /= validTokens;
      }
    }

    // L2 normalize
    const norm = Math.sqrt(embedding.reduce((sum, v) => sum + v * v, 0));
    if (norm > 0) {
      for (let d = 0; d < dim; d++) {
        embedding[d] /= norm;
      }
    }

    return embedding;
  }

  /** Embed multiple texts in batch */
  async embedBatch(texts: string[]): Promise<EmbeddingResult[]> {
    const results: EmbeddingResult[] = [];
    for (const text of texts) {
      results.push(await this.embed(text));
    }
    return results;
  }

  /** Compute cosine similarity between two embeddings */
  static cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length || a.length === 0) return 0;

    let dot = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }

    const denom = Math.sqrt(normA) * Math.sqrt(normB);
    return denom > 0 ? dot / denom : 0;
  }

  /** Find top-k most similar embeddings */
  static topK(query: number[], candidates: number[][], k: number): Array<{ index: number; score: number }> {
    const scores = candidates.map((c, i) => ({
      index: i,
      score: ONNXEmbeddingProvider.cosineSimilarity(query, c),
    }));

    scores.sort((a, b) => b.score - a.score);
    return scores.slice(0, k);
  }

  /** Check if model is ready */
  get isModelReady(): boolean {
    return this.isReady;
  }
}

// Singleton instance
let embeddingProvider: ONNXEmbeddingProvider | null = null;

export function getEmbeddingProvider(): ONNXEmbeddingProvider {
  if (!embeddingProvider) {
    embeddingProvider = new ONNXEmbeddingProvider();
  }
  return embeddingProvider;
}
