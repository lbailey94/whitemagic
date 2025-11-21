"""
CLI Integration for Dharma Garden

Commands for ethical reasoning, harmony assessment, and boundary checking.
"""

from typing import Any, Dict
import json


def command_dharma_assess(args: Any) -> int:
    """Assess ethical harmony of an action"""
    from whitemagic.dharma import get_dharma
    
    dharma = get_dharma()
    
    # Build context
    context = {
        "user_requested": not args.no_user_request,
        "permission": args.has_permission
    }
    
    # Assess action
    result = dharma.check_action(args.action, context)
    
    # Display results
    print(f"\n🙏 Dharma Assessment")
    print(f"{'='*50}")
    print(f"Action: {args.action}")
    print(f"Harmony Score: {result['harmony_score']:.2f}")
    print(f"Level: {result['level']}")
    print(f"Allowed: {'✅ Yes' if result['allowed'] else '❌ No'}")
    
    if result.get('reasoning'):
        print(f"\nReasoning: {result['reasoning']}")
    
    if result.get('aligned_principles'):
        print(f"\n✅ Aligned: {', '.join(result['aligned_principles'])}")
    
    if result.get('violated_principles'):
        print(f"\n⚠️  Violated: {', '.join(result['violated_principles'])}")
    
    return 0


def command_dharma_history(args: Any) -> int:
    """Show Dharma assessment history"""
    from whitemagic.dharma import get_dharma
    
    dharma = get_dharma()
    history = dharma.get_history(limit=args.limit)
    
    if not history:
        print("No assessments yet.")
        return 0
    
    print(f"\n📜 Dharma History ({len(history)} assessments)")
    print(f"{'='*50}")
    
    for i, assessment in enumerate(history[-args.limit:], 1):
        print(f"\n{i}. [{assessment['timestamp']}]")
        print(f"   Action: {assessment['action'][:60]}")
        print(f"   Score: {assessment['harmony_score']:.2f} ({assessment['level']})")
        print(f"   Allowed: {'✅' if assessment['allowed'] else '❌'}")
    
    return 0


def command_dharma_principles(args: Any) -> int:
    """Show Dharma principles"""
    from pathlib import Path
    import yaml
    
    principles_path = Path(__file__).parent / "dharma" / "principles.yaml"
    
    if not principles_path.exists():
        print("Principles file not found.")
        return 1
    
    with open(principles_path) as f:
        principles = yaml.safe_load(f)
    
    print(f"\n☸️  Dharma Principles")
    print(f"{'='*50}")
    
    for category, items in principles.items():
        print(f"\n{category.upper()}:")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for key, value in item.items():
                        print(f"  • {key}: {value}")
                else:
                    print(f"  • {item}")
        else:
            print(f"  {items}")
    
    return 0


def command_dharma_check_boundary(args: Any) -> int:
    """Check if action crosses ethical boundaries"""
    from whitemagic.dharma import BoundaryDetector
    
    if not BoundaryDetector:
        print("Boundary detection not available.")
        return 1
    
    detector = BoundaryDetector()
    
    context = {"user_requested": not args.no_user_request}
    boundary = detector.detect(args.action, context)
    
    print(f"\n🛡️  Boundary Check")
    print(f"{'='*50}")
    print(f"Action: {args.action}")
    print(f"Boundary Type: {boundary.boundary_type}")
    print(f"Severity: {boundary.severity}")
    print(f"Reasoning: {boundary.reasoning}")
    
    return 0


def register_dharma_commands(subparsers: Any):
    """Register Dharma CLI commands"""
    
    # dharma assess
    assess = subparsers.add_parser(
        'dharma-assess',
        help='Assess ethical harmony of an action'
    )
    assess.add_argument('action', help='Action to assess')
    assess.add_argument('--no-user-request', action='store_true',
                       help='Action was not requested by user')
    assess.add_argument('--has-permission', action='store_true', default=True,
                       help='User gave permission (default: true)')
    
    # dharma history
    history = subparsers.add_parser(
        'dharma-history',
        help='Show assessment history'
    )
    history.add_argument('--limit', type=int, default=10,
                        help='Number of recent assessments to show')
    
    # dharma principles
    principles = subparsers.add_parser(
        'dharma-principles',
        help='Show Dharma ethical principles'
    )
    
    # dharma check-boundary
    boundary = subparsers.add_parser(
        'dharma-check-boundary',
        help='Check if action crosses ethical boundaries'
    )
    boundary.add_argument('action', help='Action to check')
    boundary.add_argument('--no-user-request', action='store_true',
                         help='Action was not requested by user')


# Command handler mapping
DHARMA_COMMAND_HANDLERS = {
    "dharma-assess": command_dharma_assess,
    "dharma-history": command_dharma_history,
    "dharma-principles": command_dharma_principles,
    "dharma-check-boundary": command_dharma_check_boundary,
}
