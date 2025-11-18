"""
CLI commands for the Automation Orchestra
"""

from pathlib import Path

from whitemagic.automation.orchestra import AutomationOrchestra


def orchestra_health_command(args):
    """Run full system health check."""
    project_root = Path.cwd()
    orchestra = AutomationOrchestra(project_root)
    
    auto_heal = not args.dry_run if hasattr(args, 'dry_run') else False
    health_report = orchestra.perform_health_check(auto_heal=auto_heal)
    
    print("\n" + "=" * 60)
    print(f"📊 Overall Health: {health_report['overall_health'].upper()}")
    print(f"   Health Score: {health_report['overall_score']:.1f}/100")
    print()
    
    print("System Status:")
    for system_name, system_data in health_report["systems"].items():
        score = system_data.get("health_score", "N/A")
        print(f"  • {system_name}: {score}/100")
    print()
    
    if health_report["coordinated_actions"]:
        print("Coordinated Actions Taken:")
        for action in health_report["coordinated_actions"]:
            print(f"  • [{action['system']}] {action['action']}")
    print()
    
    if health_report["recommendations"]:
        print("Recommendations:")
        for rec in health_report["recommendations"]:
            print(f"  {rec}")


def orchestra_maintain_command(args):
    """Run full maintenance cycle."""
    project_root = Path.cwd()
    orchestra = AutomationOrchestra(project_root)
    
    dry_run = args.dry_run if hasattr(args, 'dry_run') else True
    
    if dry_run:
        print("🔍 DRY RUN - Preview of maintenance actions\n")
    
    results = orchestra.trigger_maintenance_cycle(dry_run=dry_run)
    
    print("\n" + "=" * 60)
    print("📊 Maintenance Cycle Summary:")
    for step in results["steps"]:
        step_name = step["step"]
        if step.get("skipped"):
            print(f"  • {step_name}: Skipped")
        elif step_name == "immune_scan":
            print(f"  • {step_name}: {step['threats_found']} threats found ({step['critical']} critical)")
        elif step_name == "heal_critical":
            print(f"  • {step_name}: {step['successful']}/{step['addressed']} healed")
        elif step_name == "consolidation":
            print(f"  • {step_name}: {step['archived']} archived, {step['promoted']} promoted")
    
    final_score = results["final_health"]["health_score"]
    print(f"\n✅ Final Health Score: {final_score}/100")


def orchestra_emergency_command(args):
    """Emergency response for critical issues."""
    project_root = Path.cwd()
    orchestra = AutomationOrchestra(project_root)
    
    print("🚨 Activating Emergency Response Protocol...\n")
    
    health_report = orchestra.emergency_response()
    
    print("\n" + "=" * 60)
    print(f"📊 Post-Emergency Health: {health_report['overall_health'].upper()}")
    print(f"   Health Score: {health_report['overall_score']:.1f}/100")
    
    if health_report.get("overall_score", 0) < 60:
        print("\n⚠️  System still in degraded state")
        print("   Manual intervention may be required")
    else:
        print("\n✅ System stabilized")


def register_orchestra_commands(subparsers):
    """Register automation orchestra commands."""
    
    # Main orchestra command
    orchestra_parser = subparsers.add_parser(
        "orchestra",
        help="Automation orchestra - integrated system management"
    )
    orchestra_subparsers = orchestra_parser.add_subparsers(dest="orchestra_command")
    
    # Health command
    health_parser = orchestra_subparsers.add_parser(
        "health",
        help="Full system health check with coordination"
    )
    health_parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Actually apply fixes (default is dry-run)"
    )
    health_parser.set_defaults(func=orchestra_health_command)
    
    # Maintain command
    maintain_parser = orchestra_subparsers.add_parser(
        "maintain",
        help="Run full automated maintenance cycle"
    )
    maintain_parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Actually apply fixes (default is dry-run)"
    )
    maintain_parser.set_defaults(func=orchestra_maintain_command)
    
    # Emergency command
    emergency_parser = orchestra_subparsers.add_parser(
        "emergency",
        help="Emergency response protocol (auto-heal enabled)"
    )
    emergency_parser.set_defaults(func=orchestra_emergency_command)
