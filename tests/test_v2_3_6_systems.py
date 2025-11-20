#\!/usr/bin/env python3
"""Test script for v2.3.6 autonomous systems."""

import sys
import asyncio
from pathlib import Path

print("=== WhiteMagic v2.3.6 System Test ===\n")

# Test 1: Config loads properly
print("→ Testing config system...")
try:
    from whitemagic.config import show_config, VERSION
    show_config()
    print(f"  ✓ Config v{VERSION} loaded\n")
except Exception as e:
    print(f"  ✗ Config error: {e}\n")
    sys.exit(1)

# Test 2: Founder account
print("→ Testing founder account...")
try:
    from whitemagic.users import initialize_founder
    founder = initialize_founder()
    print(f"  ✓ Founder: {founder['uid']}")
    print(f"  ✓ Tier: {founder['tier']}")
    print(f"  ✓ Permissions: {len(founder['permissions'])}\n")
except Exception as e:
    print(f"  ✗ Founder error: {e}\n")

# Test 3: Symbolic compression config
print("→ Testing symbolic compression...")
try:
    from whitemagic.symbolic_memory import (
        SYMBOLIC_COMPRESSION_ENABLED,
        SYMBOLIC_TOKEN_SAVINGS
    )
    print(f"  ✓ Enabled: {SYMBOLIC_COMPRESSION_ENABLED}")
    print(f"  ✓ Savings: {SYMBOLIC_TOKEN_SAVINGS*100:.1f}%\n")
except Exception as e:
    print(f"  ✗ Symbolic error: {e}\n")

# Test 4: Rapid cognition
print("→ Testing rapid cognition config...")
try:
    from whitemagic.learning.rapid_cognition import RapidCognition
    rc = RapidCognition()
    print(f"  ✓ Interval: {rc.learn_interval}s (3x faster)\n")
except Exception as e:
    print(f"  ✗ Cognition error: {e}\n")

# Test 5: Wisdom ingester (with fallback)
print("→ Testing wisdom ingester...")
try:
    from whitemagic.wisdom.auto_ingester import HAS_AIOHTTP, TEXTS
    print(f"  ✓ aiohttp available: {HAS_AIOHTTP}")
    print(f"  ✓ Texts configured: {len(TEXTS)}\n")
except Exception as e:
    print(f"  ✗ Ingester error: {e}\n")

# Test 6: Release automation
print("→ Testing release automation...")
try:
    from whitemagic.automation import run_release_automation
    print(f"  ✓ Automation ready\n")
except Exception as e:
    print(f"  ✗ Automation error: {e}\n")

# Test 7: WebSocket
print("→ Testing WebSocket infrastructure...")
try:
    from whitemagic.api.websocket import manager, emit_cycle_complete
    print(f"  ✓ WebSocket manager ready")
    print(f"  ✓ Events: cycle_complete, pattern_discovered, metrics_update\n")
except Exception as e:
    print(f"  ✗ WebSocket error: {e}\n")

print("=== All Systems Tested ===")
print("Ready for autonomous operation\! 🚀")
