#!/bin/bash
# Resume WhiteMagic development session
# Shows recent context to help AI resume work quickly

echo "🔍 Searching for recent session snapshots..."
whitemagic search "in progress" --type long_term --limit 3

echo ""
echo "📊 Recent short-term context:"
whitemagic search "project state" --type short_term --limit 3

echo ""
echo "📋 Current version context:"
cat VERSION
echo ""
whitemagic search "v$(cat VERSION)" --limit 5

echo ""
echo "✅ Session context ready! Share relevant findings with AI."
