#!/usr/bin/env python3
"""Interactive MCP Client for WhiteMagic testing."""

import json
import subprocess
import sys
import os

def mcp_call(tool_name, args=None, tool=None):
    """Call a tool via the MCP server."""
    # Build the tool call
    if tool:
        call_args = {"tool": tool, "args": args or {}}
    else:
        call_args = args or {}
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": call_args
        }
    }
    
    init = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "whitemagic.run_mcp_lean"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="<WHITEMAGIC_ROOT>",
        env={**os.environ, "PYTHONPATH": "core"}
    )
    
    # Send init + tool call
    proc.stdin.write(json.dumps(init) + "\n")
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    proc.stdin.close()
    
    # Read responses
    responses = []
    for line in proc.stdout:
        line = line.strip()
        if line:
            try:
                resp = json.loads(line)
                if resp.get("id") == 1:
                    responses.append(resp)
                    break
            except json.JSONDecodeError:
                continue
    
    proc.wait(timeout=5)
    
    if responses:
        result = responses[0].get("result", {})
        if result.get("content"):
            text = result["content"][0].get("text", "{}")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("WhiteMagic MCP Interactive Test Client")
    print("=" * 60)
    
    print("\n[1] Testing health_report...")
    health = mcp_call("gana_root", tool="health_report")
    if health:
        details = health.get("details", {})
        print(f"  Version: {details.get('version')}")
        print(f"  Health score: {details.get('health_score')}")
        print(f"  Rust bridge: {details.get('rust', {}).get('available')}")
        print(f"  Degraded: {details.get('degraded_mode')}")
    else:
        print("  FAILED")
    
    print("\n[2] Testing create_memory...")
    mem = mcp_call("gana_neck", tool="create_memory", args={
        "content": "Test memory created via MCP client",
        "title": "MCP Test Memory",
        "tags": "test,mcp,validation"
    })
    if mem and mem.get("status") == "success":
        mem_id = mem["details"].get("memory_id")
        print(f"  Created memory ID: {mem_id}")
    else:
        print(f"  Result: {mem}")
    
    print("\n[3] Testing search_memories...")
    search = mcp_call("gana_winnowing_basket", tool="search_memories", args={
        "query": "MCP test",
        "limit": 5
    })
    if search:
        print(f"  Status: {search.get('status')}")
        details = search.get("details", search)
        results = details.get("results", details.get("memories", []))
        print(f"  Results found: {len(results)}")
    else:
        print("  FAILED")
    
    print("\n[4] Testing gnosis...")
    gnosis = mcp_call("gana_ghost", tool="gnosis")
    if gnosis:
        details = gnosis.get("details", gnosis).get("gnosis", {})
        print(f"  Status: {details.get('status')}")
        print(f"  Tool count: {details.get('tool_count')}")
    else:
        print("  FAILED")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
