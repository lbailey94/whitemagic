#!/usr/bin/env python3
"""Quick SDK test (requires running WhiteMagic API)."""

import os
import sys

# Add parent to path for local testing
sys.path.insert(0, os.path.dirname(__file__))

from whitemagic_client import WhiteMagicClient, WhiteMagicError


def test():
    print("Testing WhiteMagic Python SDK...\n")

    api_key = os.getenv("WHITEMAGIC_API_KEY", "test-key")
    base_url = os.getenv("WHITEMAGIC_BASE_URL", "http://localhost:8000")

    with WhiteMagicClient(api_key=api_key, base_url=base_url) as client:
        # Test health check (no auth required)
        try:
            print("1. Testing health check...")
            health = client.health_check()
            print(f"✅ Health: {health.status} (v{health.version})")
        except Exception as e:
            print(f"⚠️  Health check failed (API not running?): {e}")
            return

        # If API key is set, test memory operations
        if os.getenv("WHITEMAGIC_API_KEY"):
            try:
                print("\n2. Testing create memory...")
                memory = client.create_memory(
                    {
                        "title": "SDK Test",
                        "content": "Testing Python SDK",
                        "type": "short_term",
                        "tags": ["test"],
                    }
                )
                print(f"✅ Created: {memory.id}")

                print("\n3. Testing list memories...")
                memories = client.list_memories({"limit": 5})
                print(f"✅ Listed: {len(memories)} memories")

                print("\n4. Testing get memory...")
                fetched = client.get_memory(memory.id)
                print(f"✅ Fetched: {fetched.title}")

                print("\n5. Testing update memory...")
                updated = client.update_memory(memory.id, {"content": "Updated content"})
                print(f"✅ Updated: {updated.id}")

                print("\n6. Testing delete memory...")
                client.delete_memory(memory.id)
                print("✅ Deleted")

                print("\n✅ All tests passed!")
            except WhiteMagicError as e:
                print(f"❌ Test failed: [{e.status}] {e.message}")
            except Exception as e:
                print(f"❌ Test failed: {e}")
        else:
            print("\n⚠️  Set WHITEMAGIC_API_KEY to test authenticated operations")


if __name__ == "__main__":
    test()
