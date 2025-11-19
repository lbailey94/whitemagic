"""CLI commands for Autoimmune Defense System"""

from pathlib import Path
from whitemagic.defense import get_immune_system


def command_scan(manager, args):
    """Scan for anti-pattern violations"""
    system = get_immune_system()
    
    target = Path(args.target if args.target else ".")
    min_conf = args.confidence if hasattr(args, 'confidence') else 0.7
    
    print(f"🛡️  WhiteMagic Autoimmune Scan")
    print(f"   Target: {target}")
    print(f"   Min confidence: {min_conf:.0%}")
    print()
    
    if target.is_file():
        violations = system.scan_file(target, min_confidence=min_conf)
    else:
        print("📁 Scanning directory...")
        violations = system.scan_directory(target, min_confidence=min_conf)
    
    if not violations:
        print("✅ No violations detected - clean code!")
        return 0
    
    # Group by severity
    high_severity = [v for v in violations if v.pattern.confidence >= 0.8]
    medium_severity = [v for v in violations if 0.7 <= v.pattern.confidence < 0.8]
    
    print(f"⚠️  Found {len(violations)} potential violations:")
    if high_severity:
        print(f"   🔴 High severity: {len(high_severity)}")
    if medium_severity:
        print(f"   🟡 Medium severity: {len(medium_severity)}")
    print()
    
    # Show top violations
    print("Top violations:")
    for v in violations[:10]:
        severity = "🔴" if v.pattern.confidence >= 0.8 else "🟡"
        print(f"{severity} {v.file_path}:{v.line_number}")
        print(f"   {v.pattern.title[:70]}")
        print(f"   Confidence: {v.pattern.confidence:.0%}")
        if args.verbose:
            print(f"   Match: {v.matched_text}")
        print()
    
    if len(violations) > 10:
        print(f"... and {len(violations) - 10} more")
    
    return 1 if violations else 0


def command_scan_stats(manager, args):
    """Show autoimmune system statistics"""
    system = get_immune_system()
    
    print("🛡️  Autoimmune Defense Statistics\n")
    print(f"📊 Pattern Database:")
    print(f"   Total anti-patterns: {len(system.anti_patterns)}")
    
    by_confidence = {
        'High (>=0.8)': len([p for p in system.anti_patterns.values() if p.confidence >= 0.8]),
        'Medium (0.7-0.8)': len([p for p in system.anti_patterns.values() if 0.7 <= p.confidence < 0.8]),
        'Low (<0.7)': len([p for p in system.anti_patterns.values() if p.confidence < 0.7]),
    }
    
    for label, count in by_confidence.items():
        print(f"   {label}: {count}")
    
    auto_fixable = len([p for p in system.anti_patterns.values() if p.auto_fixable])
    print(f"\n⚡ Auto-fixable patterns: {auto_fixable}")
    
    print(f"\n💪 System Status: ACTIVE")
    print(f"   Ready to defend against known anti-patterns")
