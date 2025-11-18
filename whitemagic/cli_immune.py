"""
CLI commands for the immune system
"""

from pathlib import Path

from whitemagic.immune import (
    AntibodyLibrary,
    ImmuneMemory,
    ImmuneResponse,
    ThreatDetector,
    ThreatLevel,
)


def immune_scan_command(args):
    """Run immune system scan."""
    project_root = Path.cwd()
    
    print("🔬 WhiteMagic Immune System - Health Scan")
    print("=" * 60)
    print()
    
    # Initialize detector
    detector = ThreatDetector(project_root)
    
    print("🔍 Scanning system for threats...")
    threats = detector.scan_system()
    
    if not threats:
        print("✅ System is HEALTHY - No threats detected!")
        return
    
    # Generate health report
    report = detector.generate_health_report()
    
    print(f"\n📊 Health Status: {report['health_status']}")
    print(f"   Health Score: {report['health_score']}/100")
    print(f"   Total Threats: {report['total_threats']}\n")
    
    # Show threats by level
    print("Threats by Level:")
    for level in ["critical", "high", "medium", "low"]:
        count = report["threats_by_level"][level]
        if count > 0:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[level]
            print(f"  {emoji} {level.upper()}: {count}")
    
    print()
    
    # Show individual threats
    print("Detected Threats:")
    print("-" * 60)
    
    for i, threat in enumerate(threats, 1):
        level_emoji = {
            ThreatLevel.CRITICAL: "🔴",
            ThreatLevel.HIGH: "🟠",
            ThreatLevel.MEDIUM: "🟡",
            ThreatLevel.LOW: "🟢"
        }[threat.level]
        
        print(f"\n{i}. {level_emoji} [{threat.threat_type.value.upper()}]")
        print(f"   {threat.description}")
        print(f"   Location: {threat.location}")
        print(f"   Antigen: {threat.antigen}")
        if threat.suggested_antibody:
            print(f"   💉 Suggested Fix: {threat.suggested_antibody}")
    
    print()
    print("=" * 60)
    print("💡 Run 'whitemagic immune heal' to automatically fix these issues")


def immune_heal_command(args):
    """Run immune system auto-healing."""
    project_root = Path.cwd()
    
    print("💉 WhiteMagic Immune System - Auto-Healing")
    print("=" * 60)
    print()
    
    # Initialize components
    detector = ThreatDetector(project_root)
    antibody_library = AntibodyLibrary(project_root)
    immune_memory = ImmuneMemory()
    immune_response = ImmuneResponse(antibody_library, immune_memory)
    
    # Detect threats
    print("🔍 Scanning for threats...")
    threats = detector.scan_system()
    
    if not threats:
        print("✅ No threats detected - system is healthy!")
        return
    
    critical_threats = detector.get_critical_threats()
    
    if critical_threats:
        print(f"⚠️  Found {len(critical_threats)} CRITICAL/HIGH threats")
    
    print(f"📊 Total threats: {len(threats)}\n")
    
    # Respond to threats
    dry_run = args.dry_run if hasattr(args, 'dry_run') else True
    
    if dry_run:
        print("🔍 DRY RUN - No actual fixes will be applied")
        print("   (use --no-dry-run to apply fixes)\n")
    else:
        print("🔧 Applying fixes...\n")
    
    outcomes = immune_response.respond_to_threats(threats, auto_heal=not dry_run)
    
    # Show results
    successful = sum(1 for o in outcomes if o.success)
    
    print("=" * 60)
    print(f"📊 Healing Results: {successful}/{len(outcomes)} successful")
    print()
    
    for i, outcome in enumerate(outcomes, 1):
        status_emoji = "✅" if outcome.success else "❌"
        print(f"{i}. {status_emoji} {outcome.threat.description}")
        if outcome.antibody_used:
            print(f"   💉 Antibody: {outcome.antibody_used}")
        print(f"   Action: {outcome.action_taken}")
        if outcome.error:
            print(f"   ⚠️  Error: {outcome.error}")
        print()
    
    if dry_run and successful > 0:
        print("💡 Run with --no-dry-run to apply these fixes")


def immune_status_command(args):
    """Show immune system status and statistics."""
    project_root = Path.cwd()
    
    print("🧬 WhiteMagic Immune System - Status")
    print("=" * 60)
    print()
    
    # Antibody library stats
    antibody_library = AntibodyLibrary(project_root)
    library_stats = antibody_library.get_statistics()
    
    print("💉 Antibody Library:")
    print(f"   Total Antibodies: {library_stats['total_antibodies']}")
    print()
    
    for ab in library_stats['antibodies']:
        print(f"   • {ab['name']}")
        print(f"     {ab['description']}")
        print(f"     Success Rate: {ab['success_rate']} | Applications: {ab['applications']}")
        print()
    
    # Immune memory stats
    immune_memory = ImmuneMemory()
    memory_stats = immune_memory.export_statistics()
    
    print("🧠 Immune Memory:")
    print(f"   Total Memories: {memory_stats['total_memories']}")
    print(f"   Total Encounters: {memory_stats['total_encounters']}")
    print(f"   Overall Success Rate: {memory_stats['overall_success_rate']}")
    print()
    
    if memory_stats['most_common_threats']:
        print("   Most Common Threats:")
        for threat in memory_stats['most_common_threats']:
            print(f"   • {threat['antigen']}: {threat['encounters']} encounters ({threat['success_rate']} success)")
        print()
    
    if memory_stats['problematic_threats']:
        print("   ⚠️  Problematic Threats (low success rate):")
        for threat in memory_stats['problematic_threats']:
            print(f"   • {threat['antigen']}: {threat['encounters']} encounters ({threat['success_rate']} success)")
        print()


def register_immune_commands(subparsers):
    """Register immune system commands."""
    
    # Main immune command
    immune_parser = subparsers.add_parser(
        "immune",
        help="Biological immune system commands"
    )
    immune_subparsers = immune_parser.add_subparsers(dest="immune_command")
    
    # Scan command
    scan_parser = immune_subparsers.add_parser(
        "scan",
        help="Scan system for threats"
    )
    scan_parser.set_defaults(func=immune_scan_command)
    
    # Heal command
    heal_parser = immune_subparsers.add_parser(
        "heal",
        help="Auto-heal detected threats"
    )
    heal_parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Actually apply fixes (default is dry-run)"
    )
    heal_parser.set_defaults(func=immune_heal_command)
    
    # Status command
    status_parser = immune_subparsers.add_parser(
        "status",
        help="Show immune system status"
    )
    status_parser.set_defaults(func=immune_status_command)
