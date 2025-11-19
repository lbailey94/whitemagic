"""
CLI commands for memory capture system (v2.3.1+).
"""

from pathlib import Path
from typing import Optional
import sys

from whitemagic.memory.auto_capture import get_capture
from whitemagic.config.memory import get_config, update_config


def command_memory_status(args):
    """Show memory capture status."""
    capture = get_capture()
    config = get_config()
    stats = capture.get_stats()
    
    print("\n📊 Memory Capture Status")
    print("=" * 60)
    print(f"\n📈 Statistics:")
    print(f"  Total actions: {stats['total_actions']}")
    print(f"  Short-term memories: {stats['short_term_memories']}/{config.short_term_max}")
    print(f"  Pending actions: {stats['pending_actions']}")
    print(f"  Next capture in: {stats['next_capture_in']} actions")
    
    print(f"\n⚙️  Configuration:")
    print(f"  Capture frequency: every {config.short_term_frequency} actions")
    print(f"  Max short-term: {config.short_term_max} memories")
    print(f"  Auto-capture: {'enabled' if config.auto_capture_enabled else 'disabled'}")
    print(f"  Consolidation: every {config.consolidate_frequency} actions")
    print(f"  Use Rust: {'yes' if config.use_rust_for_consolidation else 'no'}")
    
    print()


def command_memory_capture_now(args):
    """Force capture current actions."""
    capture = get_capture()
    
    print("\n💾 Forcing memory capture...")
    capture.capture_memory(force=True)
    print("✅ Memory captured")
    
    command_memory_status(args)


def command_memory_config(args):
    """Configure memory system."""
    config = get_config()
    
    if args.key and args.value:
        # Set configuration
        key = args.key.replace('-', '_')
        
        # Parse value
        if args.value.lower() in ('true', 'false'):
            value = args.value.lower() == 'true'
        elif args.value.isdigit():
            value = int(args.value)
        elif '.' in args.value:
            try:
                value = float(args.value)
            except:
                value = args.value
        else:
            value = args.value
        
        # Update
        try:
            update_config(**{key: value})
            print(f"\n✅ Updated {key} = {value}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return 1
    
    # Show current config
    print("\n⚙️  Memory System Configuration")
    print("=" * 60)
    
    config_dict = config.to_dict()
    for key, value in sorted(config_dict.items()):
        print(f"  {key}: {value}")
    
    print()


def command_memory_list(manager, args):
    """List short-term memories."""
    capture = get_capture()
    memories = sorted(capture.short_term_dir.glob("*.md"))
    
    print(f"\n📝 Short-Term Memories ({len(memories)} total)")
    print("=" * 60)
    
    limit = args.limit if hasattr(args, 'limit') else 20
    for mem in memories[-limit:]:
        print(f"\n  {mem.name}")
        
        # Show first few lines
        with open(mem) as f:
            lines = f.readlines()
            for line in lines[5:8]:  # Skip YAML frontmatter
                if line.strip() and line.startswith('#'):
                    print(f"    {line.strip()}")
    
    if len(memories) > limit:
        print(f"\n  ... and {len(memories) - limit} more")
    
    print()


def command_memory_view(args):
    """View a specific memory."""
    if not args.memory_id:
        print("❌ Error: memory ID required")
        print("Usage: whitemagic memory view <memory_id>")
        return 1
    
    capture = get_capture()
    
    # Find memory by ID (action count)
    try:
        action_id = int(args.memory_id)
        pattern = f"*_action_{action_id:04d}.md"
        matches = list(capture.short_term_dir.glob(pattern))
        
        if not matches:
            print(f"❌ Memory #{action_id} not found")
            return 1
        
        # Show content
        with open(matches[0]) as f:
            print(f.read())
    
    except ValueError:
        print(f"❌ Invalid memory ID: {args.memory_id}")
        return 1


def command_memory_auto_capture(manager, args):
    """Start auto-capture mode (for testing)."""
    capture = get_capture()
    config = get_config()
    
    print(f"\n🤖 Auto-Capture Mode")
    print("=" * 60)
    print(f"Frequency: every {config.short_term_frequency} actions")
    print(f"Recording simulated actions...")
    print()
    
    # Simulate some actions for testing
    test_actions = [
        ("file_read", "Read configuration file", "Need to understand settings", "Config loaded successfully"),
        ("analysis", "Analyze code structure", "Identify optimization opportunities", "Found 3 potential improvements"),
        ("edit", "Implement performance fix", "Based on analysis findings", "Code updated, 2x faster"),
        ("test", "Run unit tests", "Verify changes work correctly", "All tests passing"),
        ("commit", "Commit changes", "Save working implementation", "Committed successfully"),
    ]
    
    for i, (action_type, desc, reason, outcome) in enumerate(test_actions, 1):
        print(f"{i}. Recording: {action_type} - {desc}")
        capture.record_action(
            action_type=action_type,
            description=desc,
            reasoning=reason,
            outcome=outcome,
            tags=[action_type, 'test']
        )
    
    print(f"\n✅ Recorded {len(test_actions)} actions")
    command_memory_status(manager, args)
