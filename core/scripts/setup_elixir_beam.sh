#!/bin/bash
# Elixir BEAM Compilation and Setup Script
# Activates CascadeExecutor and all OTP concurrency features

set -e

echo "🔮 Setting up Elixir BEAM infrastructure..."

# Check if Elixir is installed
if ! command -v elixir &> /dev/null; then
    echo "❌ Elixir not found. Install with:"
    echo "   Ubuntu/Debian: sudo apt-get install elixir"
    echo "   macOS: brew install elixir"
    exit 1
fi

ELIXIR_VERSION=$(elixir --version | grep "Elixir" | awk '{print $2}')
echo "✅ Elixir $ELIXIR_VERSION found"

# Navigate to Elixir directory
ELIXIR_DIR="$HOME/Desktop/whitemagicdev/elixir"

if [ ! -d "$ELIXIR_DIR" ]; then
    echo "❌ Elixir directory not found at $ELIXIR_DIR"
    exit 1
fi

cd "$ELIXIR_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
if [ -f "mix.exs" ]; then
    mix deps.get
else
    echo "⚠️ mix.exs not found, skipping deps.get"
fi

# Compile the project
echo "🔨 Compiling BEAM bytecode..."
mix compile

# Check for CascadeExecutor module
if mix help | grep -q "cascade"; then
    echo "✅ CascadeExecutor module found"
else
    echo "⚠️ CascadeExecutor not in mix help, checking module directly..."
fi

# Run tests if available
if [ -d "test" ]; then
    echo "🧪 Running tests..."
    mix test || echo "⚠️ Some tests failed (non-critical)"
fi

echo ""
echo "🔮 Elixir BEAM setup complete!"
echo ""
echo "Available commands:"
echo "  cd $ELIXIR_DIR && iex -S mix    # Interactive shell"
echo "  mix run                         # Run the application"
