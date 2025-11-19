"""CLI for Autoimmune Defense"""
from pathlib import Path
from whitemagic.defense import get_immune_system

def command_scan(manager, args):
    system = get_immune_system()
    target = Path(args.target if hasattr(args, 'target') and args.target else ".")
    violations = system.scan_file(target) if target.is_file() else system.scan_directory(target)
    
    print(f"🛡️ Scanned: {len(violations)} violations")
    if hasattr(args, 'heal') and args.heal and violations:
        fixed = system.auto_heal(violations)
        print(f"✅ Auto-healed: {fixed}")
    
    for v in violations[:5]:
        print(f"  {v.file_path}:{v.line_number} - {v.pattern.title[:50]}")
    return 0
