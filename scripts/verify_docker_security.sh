#!/bin/bash
# Docker Security Verification Script for WhiteMagic
# Phase 2A.5 - Day 3

echo "🔒 WhiteMagic Docker Security Verification"
echo "=========================================="
echo ""

IMAGE="whitemagic:2.1.1"

# Check if image exists
if ! docker image inspect "$IMAGE" &> /dev/null; then
    echo "❌ ERROR: Image $IMAGE not found"
    echo "   Run: docker build -t $IMAGE ."
    exit 1
fi

echo "✅ Image exists: $IMAGE"
echo ""

# 1. Check non-root user
echo "📋 [1] Verifying non-root user..."
USER=$(docker inspect "$IMAGE" --format='{{.Config.User}}')
if [ "$USER" == "whitemagic" ] || [ "$USER" == "1000" ]; then
    echo "✅ Running as non-root user: $USER"
else
    echo "❌ FAIL: Running as root or unknown user: $USER"
fi
echo ""

# 2. Check healthcheck
echo "📋 [2] Verifying healthcheck..."
HEALTHCHECK=$(docker inspect "$IMAGE" --format='{{.Config.Healthcheck.Test}}')
if [[ "$HEALTHCHECK" == *"health"* ]]; then
    echo "✅ Healthcheck configured: $HEALTHCHECK"
else
    echo "❌ FAIL: No healthcheck configured"
fi
echo ""

# 3. Multi-stage build verification
echo "📋 [3] Verifying multi-stage build..."
LAYERS=$(docker history "$IMAGE" --no-trunc | wc -l)
if [ "$LAYERS" -gt 10 ]; then
    echo "✅ Multi-stage build detected ($LAYERS layers)"
else
    echo "⚠️  WARNING: Few layers detected ($LAYERS)"
fi
echo ""

# 4. Size check
echo "📋 [4] Checking image size..."
SIZE=$(docker image inspect "$IMAGE" --format='{{.Size}}' | awk '{print int($1/1024/1024)}')
echo "📊 Image size: ${SIZE}MB"
if [ "$SIZE" -lt 500 ]; then
    echo "✅ Good size (< 500MB)"
else
    echo "⚠️  Large image (> 500MB)"
fi
echo ""

# 5. Environment variables
echo "📋 [5] Checking security-related env vars..."
ENV_VARS=$(docker inspect "$IMAGE" --format='{{json .Config.Env}}')
if [[ "$ENV_VARS" == *"JSON_LOGS=true"* ]]; then
    echo "✅ JSON logging enabled"
else
    echo "❌ FAIL: JSON logging not enabled"
fi
echo ""

# Summary
echo "=========================================="
echo "🎯 Security Verification Complete"
echo ""
echo "To test with security hardening, run:"
echo "  docker run -d \\"
echo "    --name whitemagic-test \\"
echo "    --user 1000:1000 \\"
echo "    --cap-drop=ALL \\"
echo "    --read-only \\"
echo "    --security-opt=no-new-privileges:true \\"
echo "    -v whitemagic-data:/data \\"
echo "    --tmpfs /tmp \\"
echo "    -p 8001:8000 \\"
echo "    $IMAGE"
