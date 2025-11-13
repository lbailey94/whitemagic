#!/bin/bash
# Generate TypeScript client from OpenAPI schema

set -e

echo "🔧 Generating TypeScript SDK from OpenAPI schema"
echo "================================================"

cd "$(dirname "$0")/.."

# Ensure schema exists
if [ ! -f "openapi_schema.json" ]; then
    echo "📥 Extracting OpenAPI schema from FastAPI..."
    python3 -c "
from whitemagic.api.app import app
import json
schema = app.openapi()
print(json.dumps(schema, indent=2))
" > openapi_schema.json
    echo "✅ Schema extracted"
fi

# Install generator if needed
if ! command -v npx &> /dev/null; then
    echo "❌ npm/npx not found. Please install Node.js first."
    exit 1
fi

echo "📦 Installing openapi-typescript-codegen..."
npm install --save-dev @hey-api/openapi-ts

echo "🏗️  Generating TypeScript client..."
npx @hey-api/openapi-ts \
  --input openapi_schema.json \
  --output clients/typescript/src \
  --client fetch \
  --name WhiteMagicClient

echo "✅ TypeScript client generated!"
echo ""
echo "📂 Output: clients/typescript/src"
echo ""
echo "Next steps:"
echo "  1. Review generated code"
echo "  2. Add custom wrapper (auth, retry logic)"
echo "  3. Build package: cd clients/typescript && npm run build"
echo "  4. Publish: npm publish"
