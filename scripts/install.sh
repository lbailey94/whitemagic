#!/usr/bin/env bash
# WhiteMagic one-command install script
# Usage: curl -fsSL https://raw.githubusercontent.com/lbailey94/whitemagic/main/scripts/install.sh | bash
set -euo pipefail

echo "🌐 WhiteMagic Installer"
echo "========================"
echo

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3.11+ required"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VERSION"

# Create venv
INSTALL_DIR="${WM_INSTALL_DIR:-$HOME/.whitemagic}"
echo "→ Installing to $INSTALL_DIR"

mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/.venv"
source "$INSTALL_DIR/.venv/bin/activate"

# Install WhiteMagic
pip install --upgrade pip -q
pip install whitemagic -q

# Install optional dependencies
echo "→ Installing optional dependencies..."
pip install grpcio grpcio-tools websockets textual -q 2>/dev/null || true

# Check for llama-server
if command -v llama-server &>/dev/null; then
    echo "✓ llama-server found"
else
    echo "⚠ llama-server not found (optional — for local LLM inference)"
    echo "  Install from: https://github.com/ggerganov/llama.cpp"
fi

# Check for Ollama
if command -v ollama &>/dev/null; then
    echo "✓ Ollama found"
else
    echo "⚠ Ollama not found (optional — for local LLM inference)"
fi

# Create default config
echo "→ Creating default config..."
python3 -c "
from whitemagic.config.daemon_config import save_default_config
save_default_config()
print('✓ Config created at ~/.whitemagic/config.yaml')
"

# Create shell alias
echo
echo "✅ Installation complete!"
echo
echo "Quick start:"
echo "  wm daemon start       # Start consciousness daemon"
echo "  wm daemon status      # Check daemon status"
echo "  wm tui                # Open cognitive TUI"
echo "  wm mesh enable        # Enable P2P mesh (opt-in)"
echo
echo "  wm --help             # See all commands"
