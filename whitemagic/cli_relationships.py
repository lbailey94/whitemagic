"""CLI commands for memory relationships (minimal)."""
import sys
import argparse
from whitemagic.relationships import RelationType, add_relationship
from whitemagic.frontmatter import split_frontmatter, build_frontmatter

def command_relate(manager, args):
    """Link two memories."""
    # Find source
    source = next((e for e in manager._entries(None, True) if e["filename"] == args.source), None)
    if not source:
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1
    
    # Update file
    path = manager.base_dir / source["path"]
    raw = path.read_text()
    front, body = split_frontmatter(raw)
    front = add_relationship(front, args.target, RelationType(args.type), args.description)
    path.write_text(build_frontmatter(front, body))
    
    print(f"✓ Linked: {args.source} → {args.target}")
    return 0

def command_related(manager, args):
    """Show relationships."""
    entry = next((e for e in manager._entries(None, True) if e["filename"] == args.filename), None)
    if not entry:
        print(f"Not found: {args.filename}", file=sys.stderr)
        return 1
    
    path = manager.base_dir / entry["path"]
    front, _ = split_frontmatter(path.read_text())
    rels = front.get("related_to", [])
    
    if not rels:
        print("No relationships")
        return 0
    
    print(f"\n{entry['title']}:")
    for r in rels:
        print(f"  → {r['filename']} ({r['type']})")
    return 0
