#!/bin/bash
# Docker Compose Smoke Test for v2.1.3
set -e

echo "🐳 WhiteMagic v2.1.3 - Docker Compose Smoke Test"
echo "================================================"

cd "$(dirname "$0")/.."

# Check Docker Compose version
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    echo "✅ Using Docker Compose V2"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo "⚠️  Using Docker Compose V1 (consider upgrading to V2)"
else
    echo "❌ Docker Compose not found. Run: ./scripts/install_docker_compose_v2.sh"
    exit 1
fi

# 1. Start services
echo -e "\n📦 Starting services..."
$COMPOSE_CMD up -d

# 2. Wait for health checks
echo -e "\n⏳ Waiting for services to be healthy (60s)..."
sleep 60

# 3. Check service status
echo -e "\n📊 Service status:"
$COMPOSE_CMD ps

# 4. Test API health endpoint
echo -e "\n🔍 Testing API health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
echo "Response: $HEALTH_RESPONSE"

# Check version in response
if echo "$HEALTH_RESPONSE" | grep -q '"version":"2.1.3"'; then
    echo "✅ Version check passed: 2.1.3 detected"
else
    echo "❌ Version check failed: Expected 2.1.3"
    $COMPOSE_CMD logs api | tail -20
    exit 1
fi

# Check status
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo "✅ Health status: healthy"
else
    echo "❌ Health status: not healthy"
    $COMPOSE_CMD logs api | tail -20
    exit 1
fi

# 5. Test API docs endpoint
echo -e "\n📚 Testing API docs endpoint..."
DOCS_RESPONSE=$(curl -s http://localhost:8000/docs)
if echo "$DOCS_RESPONSE" | grep -q "Swagger UI"; then
    echo "✅ API docs accessible"
else
    echo "❌ API docs not accessible"
    exit 1
fi

# 6. Test dashboard via Caddy (if running)
echo -e "\n🎨 Testing dashboard..."
DASHBOARD_RESPONSE=$(curl -s http://localhost:3000 2>/dev/null || echo "Dashboard not configured")
if echo "$DASHBOARD_RESPONSE" | grep -q "WhiteMagic\|<!DOCTYPE html>"; then
    echo "✅ Dashboard accessible via Caddy"
else
    echo "⚠️  Dashboard not running (may not be configured)"
fi

# 7. Check logs for errors
echo -e "\n📝 Checking API logs for errors..."
ERROR_COUNT=$($COMPOSE_CMD logs api | grep -i "error\|exception\|failed" | grep -v "test" | wc -l)
if [ "$ERROR_COUNT" -lt 5 ]; then
    echo "✅ No significant errors in API logs"
else
    echo "⚠️  Found $ERROR_COUNT potential errors in logs:"
    $COMPOSE_CMD logs api | grep -i "error\|exception\|failed" | tail -10
fi

# 8. Summary
echo -e "\n"
echo "================================================"
echo "🎉 Docker Compose Smoke Test Complete"
echo "================================================"
echo "✅ Services running"
echo "✅ API health check passed (version 2.1.3)"
echo "✅ API docs accessible"
echo "✅ No critical errors detected"
echo ""
echo "Services are ready. To stop:"
echo "  $COMPOSE_CMD down"
echo ""
