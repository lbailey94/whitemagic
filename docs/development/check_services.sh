#!/bin/bash
# Quick script to check if WhiteMagic services are running

echo "🔍 Checking WhiteMagic Services..."
echo ""

# Check Dashboard (port 3000)
echo "📊 Dashboard (port 3000):"
if lsof -i :3000 > /dev/null 2>&1; then
    echo "  ✅ Running"
    curl -s http://localhost:3000 | grep -q "WhiteMagic Dashboard" && echo "  ✅ HTML loads correctly"
else
    echo "  ❌ Not running"
    echo "  💡 Start with: cd dashboard && python3 -m http.server 3000 &"
fi
echo ""

# Check API (port 8000)
echo "🔌 API Backend (port 8000):"
if lsof -i :8000 > /dev/null 2>&1; then
    echo "  ✅ Running"
    HEALTH=$(curl -s http://localhost:8000/health)
    if [ -n "$HEALTH" ]; then
        echo "  ✅ Health check: OK"
        echo "  📊 $HEALTH"
    fi
else
    echo "  ❌ Not running"
    echo "  💡 Start with: ALLOWED_ORIGINS='http://localhost:3000' uvicorn whitemagic.api.app:app --reload --host 0.0.0.0 --port 8000 &"
fi
echo ""

echo "🔗 URLs:"
echo "  Dashboard: http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  API Health: http://localhost:8000/health"
