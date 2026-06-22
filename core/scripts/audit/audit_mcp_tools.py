
import json
import logging
import sys
from pathlib import Path

# Ensure whitemagic is in path
sys.path.append(str(Path(__file__).resolve().parent))

from whitemagic.tools.unified_api import call_tool

# Setup basic logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_tool(name, **kwargs):
    print(f"\n--- Testing Tool: {name} ---")
    try:
        result = call_tool(name, **kwargs)
        status = result.get("status")
        print(f"Status: {status}")
        if status != "success":
            print(f"Error: {result.get('message')}")
            if "traceback" in result.get("details", {}):
                print(result["details"]["traceback"])
        else:
            # Print a snippet of the result
            output = {k: v for k, v in result.items() if k not in ["traceback", "details"]}
            print(json.dumps(output, indent=2)[:500] + "...")
        return result
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        return None

def main():
    print("🚀 Starting Deep MCP Tool Audit...")

    # 1. Gana Chariot (Archaeology)
    test_tool("archaeology", action="stats")

    # 2. Gana Willow (Grimoire/AutoCast)
    test_tool("grimoire_list")
    test_tool("grimoire_suggest", task="Optimize memory usage in Rust")

    # 3. Gana Dipper (Homeostasis)
    test_tool("homeostasis.status")
    test_tool("maturity.assess", path="whitemagic/core")

    # 4. Search & Memory (Rust-accelerated)
    test_tool("vector.status")
    test_tool("search_query", query="stability fixes", limit=5)
    test_tool("memory.consolidate")

    # 5. Gana Ghost (Introspection & Research)
    test_tool("manifest")
    test_tool("repo.summary")

    # 6. Gana Three Stars (Judgment & Synthesis)
    test_tool("art_of_war.chapter", chapter=1)

    # 7. Gana Ox (Endurance / Swarm)
    test_tool("swarm.status")

    # 8. Gana Tail (Performance)
    test_tool("token_report")

if __name__ == "__main__":
    main()
