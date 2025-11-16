"""
Meta-Optimization Example - v2.2.5 Features

Demonstrates the new meta-optimization features that reduce initial
session token burn by 60-70%.

Features demonstrated:
1. Hierarchical workspace loading
2. Smart START HERE templates
3. Delta-based session summaries
4. Automatic session type detection
"""

from pathlib import Path
from datetime import datetime
from whitemagic import (
    # Meta-optimization imports
    load_workspace_for_task,
    create_start_here_memory,
    track_session_changes,
    configure_session,
    print_session_config,
    SessionType,
)


def example_1_workspace_loading():
    """Example 1: Hierarchical workspace loading."""
    print("=" * 60)
    print("Example 1: Hierarchical Workspace Loading")
    print("=" * 60)
    
    # Load workspace at different tiers
    workspace_root = Path.cwd()
    
    # Tier 0: Minimal (only relevant to task)
    context_tier0 = load_workspace_for_task(
        str(workspace_root),
        "Implement symbolic reasoning module",
        tier=0
    )
    print(f"\nTier 0 (Minimal):")
    print(f"  Token estimate: ~{context_tier0['token_estimate']} tokens")
    print(f"  Task type: {context_tier0['task_type']}")
    print(f"  Directories loaded: {len(context_tier0['structure']['directories'])}")
    
    # Tier 1: Balanced
    context_tier1 = load_workspace_for_task(
        str(workspace_root),
        "Implement symbolic reasoning module",
        tier=1
    )
    print(f"\nTier 1 (Balanced):")
    print(f"  Token estimate: ~{context_tier1['token_estimate']} tokens")
    print(f"  Directories loaded: {len(context_tier1['structure']['directories'])}")
    
    # Compare savings
    if context_tier0['token_estimate'] > 0:
        savings = (1 - context_tier0['token_estimate'] / context_tier1['token_estimate']) * 100
        print(f"\n💡 Tier 0 saves ~{savings:.0f}% tokens vs Tier 1")
    
    print()


def example_2_smart_start_here():
    """Example 2: Smart START HERE templates."""
    print("=" * 60)
    print("Example 2: Smart START HERE Templates")
    print("=" * 60)
    
    # Create a START HERE memory at different tiers
    memory_dir = Path("memory")
    
    # Quick tier (30-second resume)
    path_quick = create_start_here_memory(
        version="2.2.5",
        phase="Phase 1: Meta-Optimization",
        current_focus="Session type detection",
        next_action="Implement symbolic reasoning module",
        memory_dir=memory_dir,
        tier="quick",
        files_modified=["whitemagic/session_types.py"],
        decisions_made=["Use enum for session types", "Auto-detect from keywords"],
        token_used=67000,
        token_remaining=133000,
    )
    
    print(f"\n✅ Created quick START HERE template: {path_quick.name}")
    print(f"   Estimated: <1K tokens for next session resume")
    
    # Balanced tier (2-minute deep dive)
    path_balanced = create_start_here_memory(
        version="2.2.5",
        phase="Phase 1: Meta-Optimization",
        current_focus="Session type detection",
        next_action="Implement symbolic reasoning module",
        memory_dir=memory_dir,
        tier="balanced",
        files_modified=[
            "whitemagic/workspace_loader.py",
            "whitemagic/session_templates.py",
            "whitemagic/delta_tracking.py",
            "whitemagic/session_types.py",
        ],
        decisions_made=[
            "Use tiered loading (0, 1, 2)",
            "Auto-detect session type from keywords",
            "Track deltas instead of absolute state",
        ],
        open_questions=["Should we add more session types?"],
        token_used=67000,
        token_remaining=133000,
    )
    
    print(f"\n✅ Created balanced START HERE template: {path_balanced.name}")
    print(f"   Estimated: ~3K tokens for next session resume")
    
    print(f"\n💡 Choose tier based on session complexity")
    print()


def example_3_delta_tracking():
    """Example 3: Delta-based session tracking."""
    print("=" * 60)
    print("Example 3: Delta-Based Session Tracking")
    print("=" * 60)
    
    # Start tracking session changes
    tracker = track_session_changes()
    
    # Track various changes during session
    tracker.add_feature("Hierarchical workspace loader")
    tracker.add_feature("Smart START HERE templates")
    tracker.add_feature("Delta-based session summaries")
    tracker.add_feature("Session type detection")
    
    tracker.track_file_change(
        "whitemagic/workspace_loader.py",
        change_type="created",
        lines_added=450,
        description="Tiered workspace loading system"
    )
    
    tracker.track_file_change(
        "whitemagic/session_templates.py",
        change_type="created",
        lines_added=380,
        description="START HERE template generator"
    )
    
    tracker.make_decision(
        decision="Use enums for session types",
        reasoning="Type safety and better IDE support",
        alternatives=["String constants", "Integer flags"]
    )
    
    tracker.add_insight("Token burn solved, new bottleneck is context loading")
    tracker.discover_pattern("Tiered loading reduces initial tokens by 60%+")
    
    tracker.complete_phase("Phase 1: Meta-Optimization Foundation")
    
    tracker.solve_problem()
    tracker.solve_problem()
    tracker.update_token_usage(67000)
    
    # Generate summary
    print("\n📊 Session Delta Summary:\n")
    summary = tracker.generate_summary(format="markdown")
    print(summary[:500] + "...\n")
    
    # Get delta object
    delta = tracker.get_delta()
    print(f"Duration: {delta.duration_minutes} minutes")
    print(f"Features added: {len(delta.features_added)}")
    print(f"Files changed: {len(delta.files_changed)}")
    print(f"Decisions made: {len(delta.decisions_made)}")
    print(f"Problems solved: {delta.problems_solved}")
    
    print(f"\n💡 Delta summaries focus on changes, not redundant context")
    print()


def example_4_session_type_detection():
    """Example 4: Automatic session type detection."""
    print("=" * 60)
    print("Example 4: Session Type Detection")
    print("=" * 60)
    
    # Detect session type from different task descriptions
    tasks = [
        "Continue implementing symbolic reasoning module",
        "I'm new to this project, can you explain how it works?",
        "Fix the import error in workspace_loader.py",
        "Explore ideas for Wu Xing cycle detection",
        "Optimize token usage in memory loading",
    ]
    
    for task in tasks:
        config = configure_session(task_description=task)
        
        print(f"\nTask: '{task}'")
        print(f"  Detected type: {config.session_type.value}")
        print(f"  Confidence: {config.detection_confidence*100:.0f}%")
        print(f"  Memory tier: {config.strategy.tier}")
        print(f"  Estimated tokens: ~{config.estimated_initial_tokens:,}")
    
    print(f"\n💡 Auto-detection optimizes context loading for each session")
    print()


def example_5_full_workflow():
    """Example 5: Complete workflow using all features."""
    print("=" * 60)
    print("Example 5: Complete Meta-Optimization Workflow")
    print("=" * 60)
    
    # Step 1: Detect session type
    print("\n🔍 Step 1: Detect Session Type")
    config = configure_session(
        task_description="Continue implementing v2.2.5 features",
        memory_dir=Path("memory")
    )
    print(f"  Type: {config.session_type.value}")
    print(f"  Initial tokens: ~{config.estimated_initial_tokens:,}")
    
    # Step 2: Load workspace (tier based on session type)
    print("\n📂 Step 2: Load Workspace Context")
    workspace = load_workspace_for_task(
        str(Path.cwd()),
        "Continue implementing v2.2.5 features",
        tier=config.strategy.workspace_tier
    )
    print(f"  Workspace tokens: ~{workspace['token_estimate']}")
    print(f"  Total so far: ~{config.estimated_initial_tokens + workspace['token_estimate']}")
    
    # Step 3: Track changes during session
    print("\n📝 Step 3: Track Changes During Session")
    tracker = track_session_changes()
    tracker.add_feature("Complete meta-optimization example")
    tracker.complete_phase("Phase 1: Meta-Optimization")
    print(f"  Tracking: features, decisions, insights, metrics")
    
    # Step 4: Create START HERE for next session
    print("\n💾 Step 4: Create START HERE for Next Session")
    start_here_path = create_start_here_memory(
        version="2.2.5",
        phase="Phase 1: Complete",
        current_focus="Meta-optimization foundation",
        next_action="Begin Phase 2: Symbolic reasoning module",
        memory_dir=Path("memory"),
        tier="quick",  # Use quick tier since it's a continuation
        files_modified=["examples/meta_optimization_example.py"],
        token_used=70000,
        token_remaining=130000,
    )
    print(f"  Created: {start_here_path.name}")
    print(f"  Next session will load in <1K tokens")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Session Summary")
    print("=" * 60)
    total_initial = config.estimated_initial_tokens + workspace['token_estimate']
    print(f"  Initial context load: ~{total_initial:,} tokens")
    print(f"  Traditional approach: ~20,000 tokens")
    savings = (1 - total_initial / 20000) * 100
    print(f"  Savings: ~{savings:.0f}% reduction")
    print(f"\n✨ Meta-optimization: Complete!")
    print()


if __name__ == "__main__":
    print("\n🎯 WhiteMagic v2.2.5: Meta-Optimization Features\n")
    
    # Run examples
    example_1_workspace_loading()
    example_2_smart_start_here()
    example_3_delta_tracking()
    example_4_session_type_detection()
    example_5_full_workflow()
    
    print("=" * 60)
    print("All examples complete! 🌸")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Try these features in your own workflows")
    print("  2. Measure token savings in real sessions")
    print("  3. Customize session types for your use case")
    print("\nDocumentation: docs/guides/META_OPTIMIZATION.md")
    print()
