#!/bin/bash
# download-onnx-model.sh — Download quantized MiniLM model for browser embedding
#
# Model: all-MiniLM-L6-v2 (quantized)
# Size: ~22MB
# Dimensions: 384
#
# Usage: bash scripts/download-onnx-model.sh

set -e

MODELS_DIR="$(cd "$(dirname "$0")/../apps/site/public/models" && pwd)"
MODEL_URL="https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model_quantized.onnx"
MODEL_FILE="$MODELS_DIR/model_quantized.onnx"

echo "============================================================"
echo "  WhiteMagic — ONNX Model Download"
echo "============================================================"
echo ""
echo "  Model: all-MiniLM-L6-v2 (quantized)"
echo "  Dimensions: 384"
echo "  Target: $MODEL_FILE"
echo ""

if [ -f "$MODEL_FILE" ]; then
    SIZE=$(du -h "$MODEL_FILE" | cut -f1)
    echo "  ✅ Model already exists ($SIZE)"
    echo "  To re-download, delete $MODEL_FILE first"
    exit 0
fi

echo "  Downloading..."
curl -L -o "$MODEL_FILE" "$MODEL_URL"

if [ -f "$MODEL_FILE" ]; then
    SIZE=$(du -h "$MODEL_FILE" | cut -f1)
    echo ""
    echo "  ✅ Downloaded successfully ($SIZE)"
    echo ""
    echo "  Next: Update onnx-embedding.ts to use local model path"
else
    echo ""
    echo "  ❌ Download failed"
    exit 1
fi
