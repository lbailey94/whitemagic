#!/bin/bash
# Verify Railway deployment after release

set -e

RAILWAY_URL=${1:-"https://imaginative-courage.railway.app"}
API_KEY=$2

if [ -z "$API_KEY" ]; then
    echo "Usage: ./scripts/verify_railway.sh https://your-app.railway.app YOUR_API_KEY"
    exit 1
fi

echo "🔍 Verifying Railway deployment: $RAILWAY_URL"
echo ""

# 1. Health check
echo "1️⃣  Health check..."
HEALTH=$(curl -s "$RAILWAY_URL/health")
if [ -z "$HEALTH" ]; then
    echo "   ❌ Health endpoint returned empty response"
    exit 1
fi
echo "   Response: $HEALTH"

VERSION=$(echo "$HEALTH" | grep -oP '(?<="version":")[^"]*' || echo "unknown")
echo "   Version: $VERSION"
echo ""

# 2. Create memory test
echo "2️⃣  Testing memory creation..."
CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RAILWAY_URL/api/v1/memories" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Deployment Test","content":"Verifying v'$VERSION'"}')

HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$CREATE_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo "   ✅ Status: $HTTP_CODE"
    echo "   Response: $RESPONSE_BODY"
else
    echo "   ❌ Status: $HTTP_CODE"
    echo "   Response: $RESPONSE_BODY"
fi
echo ""

# 3. Search test
echo "3️⃣  Testing search..."
SEARCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RAILWAY_URL/api/v1/search" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}')

HTTP_CODE=$(echo "$SEARCH_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$SEARCH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ]; then
    TOTAL=$(echo "$RESPONSE_BODY" | grep -oP '(?<="total":)\d+' || echo "0")
    echo "   ✅ Status: $HTTP_CODE"
    echo "   Found: $TOTAL results"
else
    echo "   ❌ Status: $HTTP_CODE"
    echo "   Response: $RESPONSE_BODY"
fi
echo ""

# 4. Parallel search test (v2.2.7+)
echo "4️⃣  Testing parallel search (v2.2.7+)..."
PARALLEL_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$RAILWAY_URL/api/v1/parallel/search" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"queries":["test","deployment"]}')

HTTP_CODE=$(echo "$PARALLEL_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$PARALLEL_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "   ✅ Status: $HTTP_CODE"
    echo "   Response: $RESPONSE_BODY"
else
    echo "   ⚠️  Status: $HTTP_CODE (may not be available in this version)"
    echo "   Response: $RESPONSE_BODY"
fi
echo ""

echo "✅ Verification complete!"
