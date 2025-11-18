#!/bin/bash
# Install Docker Compose V2 Plugin
# Fixes urllib3 2.5.0 incompatibility with old docker-compose v1.29.2

set -e

echo "🐳 Installing Docker Compose V2"
echo "================================"

# Check Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "✅ Docker found: $(docker --version)"

# Check current compose version
if docker compose version &> /dev/null; then
    CURRENT_VERSION=$(docker compose version --short 2>/dev/null || echo "unknown")
    if [[ $CURRENT_VERSION == v2* ]]; then
        echo "✅ Docker Compose V2 already installed: $CURRENT_VERSION"
        exit 0
    fi
fi

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        PLATFORM="linux-x86_64"
        ;;
    aarch64|arm64)
        PLATFORM="linux-aarch64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Get latest version
echo "📥 Fetching latest Docker Compose V2 version..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | sed -E 's/.*"v([^"]+)".*/\1/')

if [ -z "$COMPOSE_VERSION" ]; then
    echo "⚠️  Could not fetch latest version, using v2.23.0"
    COMPOSE_VERSION="2.23.0"
fi

echo "📦 Installing Docker Compose v${COMPOSE_VERSION}..."

# Create plugin directory
DOCKER_CLI_PLUGINS_DIR="$HOME/.docker/cli-plugins"
mkdir -p "$DOCKER_CLI_PLUGINS_DIR"

# Download Compose V2
COMPOSE_URL="https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-${PLATFORM}"

echo "⬇️  Downloading from: $COMPOSE_URL"
curl -SL "$COMPOSE_URL" -o "$DOCKER_CLI_PLUGINS_DIR/docker-compose"

# Make executable
chmod +x "$DOCKER_CLI_PLUGINS_DIR/docker-compose"

# Verify installation
echo ""
echo "✅ Docker Compose V2 installed successfully!"
echo ""
docker compose version

echo ""
echo "================================================"
echo "🎉 Installation Complete"
echo "================================================"
echo ""
echo "You can now use: docker compose (V2)"
echo "Old command:     docker-compose (V1) - deprecated"
echo ""
echo "Update your scripts to use 'docker compose' instead of 'docker-compose'"
echo ""
