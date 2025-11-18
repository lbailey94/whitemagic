"""
CLI commands for homeostasis system.
"""

from pathlib import Path
import json

from whitemagic.homeostasis.metrics import collect_metrics, save_metrics
from whitemagic.homeostasis.equilibrium import equilibrium_report
from whitemagic.homeostasis.feedback import apply_action


def homeostasis_check(args):
    """Check system equilibrium and show report"""
    memory_dir = Path(args.memory_dir) if hasattr(args, 'memory_dir') else Path.cwd() / "memory"
    
    print("🔍 Collecting system metrics...")
    metrics = collect_metrics(memory_dir)
    
    print("📊 Analyzing equilibrium...")
    report = equilibrium_report(metrics, gain=args.gain if hasattr(args, 'gain') else 1.0)
    
    print(report)
    
    # Save metrics if requested
    if hasattr(args, 'save') and args.save:
        output_file = Path(args.save)
        save_metrics(metrics, output_file)
        print(f"💾 Metrics saved to {output_file}")


def homeostasis_balance(args):
    """Apply corrective actions to restore balance"""
    memory_dir = Path(args.memory_dir) if hasattr(args, 'memory_dir') else Path.cwd() / "memory"
    
    print("🔍 Collecting system metrics...")
    metrics = collect_metrics(memory_dir)
    
    print("📊 Analyzing equilibrium...")
    report = equilibrium_report(metrics)
    
    if not report.actions:
        print("✅ System is already in equilibrium!")
        return
    
    print(f"\n🎯 Found {len(report.actions)} recommended actions")
    
    # Apply actions if not dry run
    if hasattr(args, 'dry_run') and args.dry_run:
        print("\n🔍 DRY RUN - Would apply:")
        for action in report.actions[:5]:
            print(f"  • [{action.priority}/10] {action.action_type.value}")
            print(f"    {action.reason}")
    else:
        print("\n⚡ Applying corrective actions...")
        
        actions_to_apply = report.actions[:args.max_actions if hasattr(args, 'max_actions') else 3]
        
        for i, action in enumerate(actions_to_apply, 1):
            print(f"\n[{i}/{len(actions_to_apply)}] Applying: {action.action_type.value}")
            print(f"  Reason: {action.reason}")
            
            success = apply_action(action, str(memory_dir))
            
            if not success:
                print(f"  ⚠️ Failed or not yet implemented")
        
        print("\n✅ Balance restoration complete!")


def homeostasis_monitor(args):
    """Monitor equilibrium over time"""
    memory_dir = Path(args.memory_dir) if hasattr(args, 'memory_dir') else Path.cwd() / "memory"
    
    # TODO: Implement continuous monitoring with periodic checks
    print("⚠️ Continuous monitoring not yet implemented")
    print("Suggestion: Use cron to run 'whitemagic homeostasis check' periodically")


def register_homeostasis_commands(subparsers):
    """Register homeostasis CLI commands"""
    
    homeostasis_parser = subparsers.add_parser(
        "homeostasis",
        help="System equilibrium and self-balancing"
    )
    homeostasis_subparsers = homeostasis_parser.add_subparsers(dest="homeostasis_command")
    
    # Check equilibrium
    check_parser = homeostasis_subparsers.add_parser(
        "check",
        help="Check system equilibrium and show report"
    )
    check_parser.add_argument(
        "--memory-dir",
        default=None,
        help="Memory directory (default: ./memory)"
    )
    check_parser.add_argument(
        "--gain",
        type=float,
        default=1.0,
        help="Feedback controller gain (default: 1.0)"
    )
    check_parser.add_argument(
        "--save",
        help="Save metrics to JSON file"
    )
    check_parser.set_defaults(func=homeostasis_check)
    
    # Balance system
    balance_parser = homeostasis_subparsers.add_parser(
        "balance",
        help="Apply corrective actions to restore equilibrium"
    )
    balance_parser.add_argument(
        "--memory-dir",
        default=None,
        help="Memory directory (default: ./memory)"
    )
    balance_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    balance_parser.add_argument(
        "--max-actions",
        type=int,
        default=3,
        help="Maximum actions to apply (default: 3)"
    )
    balance_parser.set_defaults(func=homeostasis_balance)
    
    # Monitor
    monitor_parser = homeostasis_subparsers.add_parser(
        "monitor",
        help="Monitor equilibrium over time"
    )
    monitor_parser.add_argument(
        "--memory-dir",
        default=None,
        help="Memory directory (default: ./memory)"
    )
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Check interval in seconds (default: 3600)"
    )
    monitor_parser.set_defaults(func=homeostasis_monitor)
