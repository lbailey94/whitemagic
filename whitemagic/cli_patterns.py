"""CLI for Solution Patterns"""
from whitemagic.utils.patterns import get_library

def command_suggest_fix(manager, args):
    lib = get_library()
    problem = args.problem if hasattr(args, 'problem') else ""
    solution = lib.suggest_fix(problem)
    if solution:
        print(f"💡 {solution.title}")
        print(f"   Confidence: {solution.confidence:.0%}, Used: {solution.frequency}x")
    else:
        print("❌ No solution found")
    return 0

def command_search_patterns(manager, args):
    lib = get_library()
    query = args.query if hasattr(args, 'query') else ""
    matches = lib.search(query)
    print(f"🔍 Found {len(matches)} matches")
    for s in matches[:10]:
        print(f"  • {s.title[:60]}")
    return 0
