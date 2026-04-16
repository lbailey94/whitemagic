#!/bin/bash
# Safe Build Wrapper - Prevents Concurrent Builds
# Usage: ./safe_build.sh <build_command>
#
# This script creates a lock file to prevent multiple build processes
# from running simultaneously, which can cause crashes and corruption.

set -e

LOCK_DIR="/tmp/whitemagic_build_lock"
LOCK_FILE="$LOCK_DIR/build.lock"
BUILD_START_TIME=$(date +%s)
SCRIPT_PID=$$

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to cleanup lock on exit
cleanup_lock() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
        if [ "$lock_pid" = "$SCRIPT_PID" ]; then
            rm -f "$LOCK_FILE"
            rmdir "$LOCK_DIR" 2>/dev/null || true
            echo -e "${GREEN}✓ Build lock released${NC}"
        fi
    fi
}

# Set trap to cleanup on exit
trap cleanup_lock EXIT INT TERM

# Create lock directory
mkdir -p "$LOCK_DIR"

# Try to acquire lock
if [ -f "$LOCK_FILE" ]; then
    local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Another build is already running (PID: $lock_pid)${NC}"
        echo -e "${YELLOW}   Waiting for it to complete...${NC}"
        
        # Wait for lock with timeout (5 minutes)
        local wait_count=0
        local max_wait=300  # 5 minutes
        
        while [ -f "$LOCK_FILE" ] && [ $wait_count -lt $max_wait ]; do
            sleep 1
            wait_count=$((wait_count + 1))
            
            # Show progress every 10 seconds
            if [ $((wait_count % 10)) -eq 0 ]; then
                echo -e "${YELLOW}   Still waiting... (${wait_count}s)${NC}"
            fi
        done
        
        if [ $wait_count -ge $max_wait ]; then
            echo -e "${RED}✗ Timeout waiting for build lock${NC}"
            echo -e "${YELLOW}   Force removing stale lock...${NC}"
            rm -f "$LOCK_FILE"
        fi
    else
        # Stale lock file
        echo -e "${YELLOW}⚠️  Removing stale lock file${NC}"
        rm -f "$LOCK_FILE"
    fi
fi

# Acquire lock
echo "$SCRIPT_PID" > "$LOCK_FILE"
echo -e "${GREEN}✓ Build lock acquired (PID: $SCRIPT_PID)${NC}"

# If no command provided, just show status
if [ $# -eq 0 ]; then
    echo -e "${GREEN}Build system ready. Run with a command:${NC}"
    echo "  ./safe_build.sh 'cargo build --release'"
    echo "  ./safe_build.sh 'zig build'"
    echo "  ./safe_build.sh 'mojo build'"
    exit 0
fi

# Run the build command
echo -e "${GREEN}▶ Starting build: $*${NC}"
echo ""

BUILD_SUCCESS=false
if eval "$@"; then
    BUILD_SUCCESS=true
    echo ""
    echo -e "${GREEN}✓ Build completed successfully${NC}"
else
    BUILD_EXIT_CODE=$?
    echo ""
    echo -e "${RED}✗ Build failed with exit code: $BUILD_EXIT_CODE${NC}"
fi

# Calculate build time
BUILD_END_TIME=$(date +%s)
BUILD_DURATION=$((BUILD_END_TIME - BUILD_START_TIME))
echo -e "${GREEN}  Duration: ${BUILD_DURATION}s${NC}"

# Return appropriate exit code
if [ "$BUILD_SUCCESS" = true ]; then
    exit 0
else
    exit $BUILD_EXIT_CODE
fi
