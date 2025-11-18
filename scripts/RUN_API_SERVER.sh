#!/bin/bash
# WhiteMagic API Server - Quick Start Script

set -e

echo "======================================================================"
echo "WhiteMagic API Server - Starting"
echo "======================================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "whitemagic/api/app.py" ]; then
    echo "❌ Error: Please run this script from the whitemagic project root"
    exit 1
fi

# Set environment variables (development defaults)
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./whitemagic_dev.db}"
export REDIS_URL="${REDIS_URL:-}"  # Optional for development
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-CHANGE-IN-PRODUCTION-$(openssl rand -hex 16)}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export WM_BASE_PATH="${WM_BASE_PATH:-./users}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-https://example.com}"

echo "Configuration:"
echo "  Database: $DATABASE_URL"
echo "  Redis: ${REDIS_URL:-Not configured (optional)}"
echo "  Environment: $ENVIRONMENT"
echo "  Base Path: $WM_BASE_PATH"
echo ""

# Create users directory
mkdir -p "$WM_BASE_PATH"

# Check if database needs initialization
if [ ! -f "whitemagic_dev.db" ]; then
    echo "📦 Initializing database..."
    echo ""

    # Run migrations
    if command -v alembic &> /dev/null; then
        alembic upgrade head || echo "⚠️  Warning: Alembic migrations not found (this is OK for first run)"
    fi
fi

echo ""
echo "======================================================================"
echo "Starting API server..."
echo "======================================================================"
echo ""
echo "📍 API will be available at:"
echo "   - Swagger docs: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo "   - Health check: http://localhost:8000/health"
echo "   - Dashboard: http://localhost:8000/dashboard/"
echo ""
echo "Press Ctrl+C to stop"
echo "======================================================================"
echo ""

# Start server with hot reload
uvicorn whitemagic.api.app:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
