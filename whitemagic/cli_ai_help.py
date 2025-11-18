"""
CLI commands for AI assistance
"""

from whitemagic.ai.guidelines import AIGuidelinesManager, GuidelineCategory


def ai_guidelines_show(args):
    """Show AI guidelines."""
    manager = AIGuidelinesManager()
    
    # Filter if specified
    category = getattr(args, 'category', None)
    priority = getattr(args, 'priority', None)
    
    if category:
        try:
            category_enum = GuidelineCategory[category.upper()]
            guidelines = manager.get_guidelines(category=category_enum, priority=priority)
        except KeyError:
            print(f"❌ Unknown category: {category}")
            print(f"Available: {[c.value for c in GuidelineCategory]}")
            return
    elif priority:
        guidelines = manager.get_guidelines(priority=priority)
    else:
        guidelines = manager.guidelines
    
    output = manager.format_for_ai(guidelines)
    print(output)


def ai_guidelines_export(args):
    """Export guidelines to file."""
    manager = AIGuidelinesManager()
    
    output_file = args.output
    manager.export_to_file(output_file)
    
    print(f"✅ Exported AI guidelines to: {output_file}")


def ai_session_start(args):
    """Show session start protocol."""
    manager = AIGuidelinesManager()
    guidelines = manager.get_session_start_protocol()
    
    print("🚀 WhiteMagic Session Start Protocol")
    print("=" * 60)
    print()
    
    output = manager.format_for_ai(guidelines)
    print(output)


def register_ai_help_commands(subparsers):
    """Register AI help commands."""
    
    # Main ai-help command
    ai_parser = subparsers.add_parser(
        "ai-help",
        help="AI assistance and guidelines"
    )
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command")
    
    # Show guidelines
    show_parser = ai_subparsers.add_parser(
        "show",
        help="Show AI guidelines"
    )
    show_parser.add_argument(
        "--category",
        choices=[c.value for c in GuidelineCategory],
        help="Filter by category"
    )
    show_parser.add_argument(
        "--priority",
        choices=["critical", "high", "medium", "low"],
        help="Filter by priority"
    )
    show_parser.set_defaults(func=ai_guidelines_show)
    
    # Export guidelines
    export_parser = ai_subparsers.add_parser(
        "export",
        help="Export guidelines to file"
    )
    export_parser.add_argument(
        "--output",
        default="AI_GUIDELINES.md",
        help="Output file path"
    )
    export_parser.set_defaults(func=ai_guidelines_export)
    
    # Session start protocol
    session_parser = ai_subparsers.add_parser(
        "session-start",
        help="Show session start protocol"
    )
    session_parser.set_defaults(func=ai_session_start)
