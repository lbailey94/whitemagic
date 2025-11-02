#!/usr/bin/env python3
"""
WhiteMagic CLI - Command-line interface for memory management.

This is a thin wrapper around the whitemagic package that provides
a user-friendly CLI for all memory operations.

Usage:
    python cli.py create --title "My Memory" --content "Content here"
    python cli.py list
    python cli.py search --query "keyword"
    python cli.py context --tier 1

For backward compatibility, memory_manager.py imports from this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

# Import from whitemagic package
from whitemagic import MemoryManager


# ---------------------------------------------------------------------- #
# CLI Command Handlers
# ---------------------------------------------------------------------- #

def command_create(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'create' command."""
    # Read content from various sources
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content_path = Path(args.content_file).expanduser()
        if not content_path.exists():
            print(f"File not found: {content_path}", file=sys.stderr)
            return 2
        content = content_path.read_text(encoding="utf-8")
    else:
        content = args.content

    # Parse extra metadata fields
    extra_fields = {}
    for kv in args.meta:
        if "=" in kv:
            key, value = kv.split("=", 1)
            extra_fields[key.strip()] = value.strip()

    # Create memory
    path = manager.create_memory(
        title=args.title,
        content=content,
        memory_type=args.type,
        tags=args.tags,
        extra_fields=extra_fields if extra_fields else None,
    )

    print(f"✓ Created: {path}")
    return 0


def command_list(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'list' command."""
    listing = manager.list_all_memories(
        include_archived=args.include_archived,
        sort_by=args.sort_by
    )

    if args.json:
        print(json.dumps(listing, indent=2))
        return 0

    # Pretty print
    for memory_type in ["short_term", "long_term"]:
        memories = listing.get(memory_type, [])
        if memories:
            print(f"\n=== {memory_type.upper().replace('_', ' ')} ({len(memories)}) ===")
            for mem in memories:
                tags_str = ", ".join(mem.get("tags", [])) or "(no tags)"
                print(f"  {mem['filename']:40} | {mem.get('title', 'Untitled'):30} | {tags_str}")

    if args.include_archived and listing.get("archived"):
        memories = listing["archived"]
        print(f"\n=== ARCHIVED ({len(memories)}) ===")
        for mem in memories:
            tags_str = ", ".join(mem.get("tags", [])) or "(no tags)"
            print(f"  {mem['filename']:40} | {mem.get('title', 'Untitled'):30} | {tags_str}")

    return 0


def command_search(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'search' command."""
    results = manager.search_memories(
        query=args.query,
        memory_type=args.type,
        tags=args.tags if args.tags else None,
        include_archived=args.include_archived,
    )

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    if not results:
        print("No matching memories found.")
        return 0

    print(f"=== SEARCH RESULTS ({len(results)}) ===\n")
    for result in results:
        entry = result["entry"]
        preview = result.get("preview", "")
        print(f"  {entry['filename']}")
        print(f"    Title: {entry.get('title', 'Untitled')}")
        print(f"    Tags: {', '.join(entry.get('tags', [])) or '(none)'}")
        if not args.titles_only and preview:
            print(f"    Preview: {preview}")
        print()

    return 0


def command_context(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'context' command."""
    summary = manager.generate_context_summary(args.tier)
    print(summary)
    return 0


def command_consolidate(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'consolidate' command."""
    dry_run = not args.no_dry_run
    result = manager.consolidate_short_term(dry_run=dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if result["archived"] == 0:
        print("✓ No old memories to consolidate.")
        return 0

    if dry_run:
        print(f"=== DRY RUN: Would archive {result['archived']} memories ===\n")
    else:
        print(f"=== CONSOLIDATED: Archived {result['archived']} memories ===\n")

    print(f"  Auto-promoted: {result['auto_promoted']}")
    print(f"  Archived: {result['archived']}")

    if result.get("promoted_files"):
        print("\nPromoted to long-term:")
        for filename in result["promoted_files"]:
            print(f"  - {filename}")

    if result.get("archived_files"):
        print("\nArchived:")
        for filename in result["archived_files"]:
            print(f"  - {filename}")

    if dry_run:
        print("\nRun with --no-dry-run to apply changes.")

    return 0


def command_delete(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'delete' command."""
    result = manager.delete_memory(args.filename, permanent=args.permanent)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["success"] else 1

    if not result["success"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    action = result["action"]
    if action == "permanently_deleted":
        print(f"✓ Permanently deleted: {result['filename']}")
    elif action == "archived":
        print(f"✓ Archived: {result['filename']} → {result['path']}")
    elif action == "removed_from_index":
        print(f"✓ Removed from index (file was missing): {result['filename']}")

    return 0


def command_update(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'update' command."""
    # Handle content input
    content = None
    if args.stdin:
        content = sys.stdin.read()
    elif args.content_file:
        content_path = Path(args.content_file).expanduser()
        if not content_path.exists():
            print(f"File not found: {content_path}", file=sys.stderr)
            return 2
        content = content_path.read_text(encoding="utf-8")
    elif args.content:
        content = args.content

    # Prepare tag updates
    replace_tags = args.replace_tags if args.replace_tags else None

    result = manager.update_memory(
        args.filename,
        title=args.title,
        content=content,
        tags=replace_tags,
        add_tags=args.add_tags,
        remove_tags=args.remove_tags,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["success"] else 1

    if not result["success"]:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    print(f"✓ Updated: {result['filename']}")
    return 0


def command_list_tags(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'list-tags' command."""
    tags_info = manager.list_all_tags(include_archived=args.include_archived)

    if args.json:
        print(json.dumps(tags_info, indent=2))
        return 0

    if not tags_info["tags"]:
        print("No tags found.")
        return 0

    print(f"=== ALL TAGS ({tags_info['total_unique_tags']} unique) ===\n")
    for tag_info in tags_info["tags"]:
        used_in = ", ".join(tag_info["used_in"])
        print(f"  {tag_info['tag']:20} | {tag_info['count']:3} memories | {used_in}")

    print(f"\nTotal tagged memories: {tags_info['total_tag_usages']}")
    print(f"Memories with tags: {tags_info['total_memories_with_tags']}")
    return 0


def command_restore(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'restore' command."""
    result = manager.restore_memory(args.filename, memory_type=args.type)

    if not result["success"]:
        print(f"✗ Error: {result['error']}", file=sys.stderr)
        return 1

    print(f"✓ Restored '{result['filename']}' to {result['memory_type']}")
    print(f"  Path: {result['path']}")
    return 0


def command_normalize_tags(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'normalize-tags' command."""
    dry_run = not args.no_dry_run
    result = manager.normalize_legacy_tags(dry_run=dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    if result["affected_memories"] == 0:
        print("✓ All tags are already normalized.")
        return 0

    if dry_run:
        print(f"=== DRY RUN: {result['affected_memories']} memories would be updated ===\n")
    else:
        print(f"=== NORMALIZED: {result['affected_memories']} memories updated ===\n")

    for change in result["changes"]:
        print(f"  {change['filename']}")
        print(f"    Title: {change['title']}")
        print(f"    Before: {', '.join(change['before'])}")
        print(f"    After:  {', '.join(change['after'])}")
        print()

    if dry_run:
        print("Run with --no-dry-run to apply changes.")

    return 0


# Command dispatch table
COMMAND_HANDLERS = {
    "create": command_create,
    "list": command_list,
    "search": command_search,
    "context": command_context,
    "consolidate": command_consolidate,
    "delete": command_delete,
    "update": command_update,
    "list-tags": command_list_tags,
    "restore": command_restore,
    "normalize-tags": command_normalize_tags,
}


# ---------------------------------------------------------------------- #
# Argument Parser
# ---------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Memory management toolkit for the WhiteMagic prompt system."
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Project root containing the memory directory (default: current directory).",
    )

    subparsers = parser.add_subparsers(dest="command")

    # create
    create_parser = subparsers.add_parser(
        "create", help="Create a new memory entry."
    )
    create_parser.add_argument("--title", required=True, help="Memory title.")
    content_group = create_parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument(
        "--content",
        help="Literal content string. Useful for short notes.",
    )
    content_group.add_argument(
        "--content-file",
        help="Path to a file whose contents will be used for the memory body.",
    )
    content_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read memory content from STDIN.",
    )
    create_parser.add_argument(
        "--type",
        choices=["short_term", "long_term"],
        default="short_term",
        help="Memory type/duration.",
    )
    create_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="Tag to add (can be specified multiple times).",
    )
    create_parser.add_argument(
        "--meta",
        action="append",
        default=[],
        help="Additional frontmatter fields in key=value form (multiple allowed).",
    )

    # list
    list_parser = subparsers.add_parser("list", help="List memories.")
    list_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived entries in output.",
    )
    list_parser.add_argument(
        "--sort-by",
        choices=["created", "updated", "accessed"],
        default="created",
        help="Sort memories by this field (default: created).",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output list as JSON for downstream tooling.",
    )

    # search
    search_parser = subparsers.add_parser("search", help="Search memories.")
    search_parser.add_argument("--query", help="Search query.")
    search_parser.add_argument(
        "--type",
        choices=["short_term", "long_term"],
        help="Filter by memory type.",
    )
    search_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        default=[],
        help="Require memories to contain this tag (multiple allowed).",
    )
    search_parser.add_argument(
        "--titles-only",
        action="store_true",
        help="Skip full content scan (faster).",
    )
    search_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived memories in search results.",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output search results as JSON.",
    )

    # context
    context_parser = subparsers.add_parser(
        "context", help="Generate context summary for AI prompts."
    )
    context_parser.add_argument(
        "--tier",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Context tier: 0 (minimal), 1 (balanced), 2 (full).",
    )

    # consolidate
    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Archive old short-term memories, auto-promote special-tagged items.",
    )
    consolidate_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually perform consolidation (default is dry-run).",
    )
    consolidate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output consolidation results as JSON.",
    )

    # delete
    delete_parser = subparsers.add_parser(
        "delete", help="Delete or archive a memory."
    )
    delete_parser.add_argument("filename", help="Memory filename to delete.")
    delete_parser.add_argument(
        "--permanent",
        action="store_true",
        help="Permanently delete (skip archive step).",
    )
    delete_parser.add_argument(
        "--json",
        action="store_true",
        help="Output deletion result as JSON.",
    )

    # update
    update_parser = subparsers.add_parser(
        "update", help="Update an existing memory's content, title, or tags."
    )
    update_parser.add_argument("filename", help="Memory filename to update.")
    update_parser.add_argument("--title", help="New title.")
    content_group = update_parser.add_mutually_exclusive_group()
    content_group.add_argument("--content", help="New content (literal string).")
    content_group.add_argument(
        "--content-file",
        help="Path to file containing new content.",
    )
    content_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read new content from STDIN.",
    )
    update_parser.add_argument(
        "--add-tag",
        dest="add_tags",
        action="append",
        default=[],
        help="Add this tag (can be specified multiple times).",
    )
    update_parser.add_argument(
        "--remove-tag",
        dest="remove_tags",
        action="append",
        default=[],
        help="Remove this tag (can be specified multiple times).",
    )
    update_parser.add_argument(
        "--replace-tags",
        nargs="*",
        help="Replace all tags with this list.",
    )
    update_parser.add_argument(
        "--json",
        action="store_true",
        help="Output update result as JSON.",
    )

    # list-tags
    list_tags_parser = subparsers.add_parser(
        "list-tags", help="List all unique tags with usage counts."
    )
    list_tags_parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include tags from archived memories.",
    )
    list_tags_parser.add_argument(
        "--json",
        action="store_true",
        help="Output tags as JSON.",
    )

    # restore
    restore_parser = subparsers.add_parser(
        "restore", help="Restore an archived memory."
    )
    restore_parser.add_argument("filename", help="Archived memory filename to restore.")
    restore_parser.add_argument(
        "--type",
        choices=["short_term", "long_term"],
        default="short_term",
        help="Target memory type (default: short_term).",
    )

    # normalize-tags
    normalize_parser = subparsers.add_parser(
        "normalize-tags",
        help="Normalize legacy mixed-case tags to lowercase.",
    )
    normalize_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually apply normalization (default is dry-run).",
    )
    normalize_parser.add_argument(
        "--json",
        action="store_true",
        help="Output normalization results as JSON.",
    )

    return parser


# ---------------------------------------------------------------------- #
# Main Entry Point
# ---------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    manager = MemoryManager(base_dir=args.base_dir)
    handler = COMMAND_HANDLERS.get(args.command)
    if not handler:
        parser.error(f"Unknown command: {args.command}")
        return 2

    return handler(manager, args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
