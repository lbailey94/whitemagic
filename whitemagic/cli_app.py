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
import asyncio
import json
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

# Import from whitemagic package
from whitemagic import MemoryManager
from whitemagic.backup import BackupManager
from whitemagic.cli_audit import audit_project, print_audit_report
from whitemagic.cli_docs import docs_check_and_fix
from whitemagic.cli_immune import register_immune_commands
from whitemagic.cli_orchestra import register_orchestra_commands
from whitemagic.cli_version import bump_version

# ---------------------------------------------------------------------- #
# Utility Functions & Decorators
# ---------------------------------------------------------------------- #


def async_command(func: Callable) -> Callable:
    """
    Decorator to make CLI commands async-aware.

    Wraps async functions with asyncio.run() so they can be called
    from synchronous CLI dispatch.

    Example:
        @async_command
        async def command_search_semantic(manager, args):
            results = await manager.search_semantic(...)
            return 0
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> int:
        if asyncio.iscoroutinefunction(func):
            return asyncio.run(func(*args, **kwargs))
        return func(*args, **kwargs)

    return wrapper


def get_console():
    """Get a rich Console instance for formatted output."""
    from rich.console import Console

    return Console()


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

    # Auto-suggest tags if not disabled
    tags = list(args.tags) if args.tags else []
    if not getattr(args, "no_auto_tag", False) and not tags:
        from rich.prompt import Confirm

        from whitemagic.auto_tagger import AutoTagger

        console = get_console()

        tagger = AutoTagger(memory_manager=manager)
        suggested = tagger.suggest_tags(args.title, content, tags)

        if suggested:
            console.print(f"\n[yellow]Suggested tags:[/yellow] {', '.join(suggested)}")
            if Confirm.ask("Accept these tags?", default=True):
                tags = suggested

    # Create memory
    path = manager.create_memory(
        title=args.title,
        content=content,
        memory_type=args.type,
        tags=tags,
        extra_fields=extra_fields if extra_fields else None,
    )

    print(f"✓ Created: {path}")
    return 0


def command_list(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'list' command."""
    listing = manager.list_all_memories(
        include_archived=args.include_archived, sort_by=args.sort_by
    )

    if args.json:
        print(json.dumps(listing, indent=2))
        return 0

    from rich.table import Table

    console = get_console()

    # Display each memory type with rich tables
    for memory_type in ["short_term", "long_term"]:
        memories = listing.get(memory_type, [])
        if memories:
            console.print(
                f"\n[bold cyan]{memory_type.upper().replace('_', ' ')}[/bold cyan] [dim]({len(memories)} memories)[/dim]\n"
            )

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Filename", style="cyan", no_wrap=True)
            table.add_column("Title", style="green")
            table.add_column("Tags", style="yellow")

            for mem in memories:
                tags_str = ", ".join(mem.get("tags", [])) or "[dim](no tags)[/dim]"
                table.add_row(mem["filename"], mem.get("title", "[dim]Untitled[/dim]"), tags_str)

            console.print(table)

    if args.include_archived and listing.get("archived"):
        memories = listing["archived"]
        console.print(f"\n[bold red]ARCHIVED[/bold red] [dim]({len(memories)} memories)[/dim]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Filename", style="cyan", no_wrap=True)
        table.add_column("Title", style="green")
        table.add_column("Tags", style="yellow")

        for mem in memories:
            tags_str = ", ".join(mem.get("tags", [])) or "[dim](no tags)[/dim]"
            table.add_row(mem["filename"], mem.get("title", "[dim]Untitled[/dim]"), tags_str)

        console.print(table)

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
    role = getattr(args, "role", None)
    summary = manager.generate_context_summary(args.tier, role=role)
    print(summary)
    return 0


def command_resume(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'resume' command - show recent context for session continuity."""
    from pathlib import Path

    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()

    # Get current version
    version_file = Path(__file__).parent.parent / "VERSION"
    current_version = version_file.read_text().strip() if version_file.exists() else "unknown"

    console.print(f"\n[bold cyan]🔄 WhiteMagic Session Resume - v{current_version}[/bold cyan]\n")

    # 1. Search for in-progress sessions
    console.print("[bold]📍 Recent Session Snapshots:[/bold]")
    in_progress = manager.search_memories(tags=["in-progress", "project-state", "session"])[
        :3
    ]  # Limit to 3 most recent
    if in_progress:
        for entry in in_progress:
            entry_data = entry.get("entry", {})
            created = entry_data.get("created", "unknown")
            title = entry_data.get("title", "Untitled")
            filename = entry_data.get("filename", "unknown")
            console.print(f"  • {title} ([dim]{created}[/dim])")
            console.print(f"    [dim]→ {filename}[/dim]")
    else:
        console.print("  [dim]No active session snapshots found[/dim]")

    # 2. Search for version-specific context
    console.print(f"\n[bold]🏷️  v{current_version} Context:[/bold]")
    version_memories = manager.search_memories(query=f"v{current_version}")[:5]  # Limit to 5
    if version_memories:
        for entry in version_memories[:3]:
            entry_data = entry.get("entry", {})
            title = entry_data.get("title", "Untitled")
            console.print(f"  • {title}")
    else:
        console.print(f"  [dim]No v{current_version}-specific memories found[/dim]")

    # 3. Always do tier 0 quick scan for efficiency
    console.print("\n[bold]📚 Memory Overview (Tier 0 - Titles & Tags):[/bold]")
    tier0_summary = manager.generate_context_summary(0)
    tier0_lines = tier0_summary.split("\n")
    if len(tier0_lines) > 20:
        tier0_truncated = "\n".join(tier0_lines[:20]) + f"\n\n... ({len(tier0_lines) - 20} more)"
    else:
        tier0_truncated = tier0_summary
    console.print(Panel(Markdown(tier0_truncated), border_style="cyan"))

    # 4. Get additional tiered context if requested
    if args.tier is not None and args.tier > 0:
        console.print(f"\n[bold]🧠 Detailed Context (Tier {args.tier}):[/bold]")
        summary = manager.generate_context_summary(args.tier)

        # Show truncated version in panel
        lines = summary.split("\n")
        if len(lines) > 30:
            truncated = "\n".join(lines[:30]) + f"\n\n... ({len(lines) - 30} more lines)"
        else:
            truncated = summary

        console.print(Panel(Markdown(truncated), border_style="blue"))

    # 5. Helpful next steps
    console.print("\n[bold green]✅ Session Context Ready![/bold green]")
    console.print("\n[bold]Recommended next steps:[/bold]")
    console.print("  1. Share relevant findings with your AI assistant")
    console.print('  2. Use [cyan]whitemagic search "[query]"[/cyan] for targeted context')
    console.print(
        "  3. Use [cyan]whitemagic resume --tier 1[/cyan] for balanced context (automatic tier 0 + tier 1)"
    )
    console.print(
        "\n[dim]💡 Tip: Tier 0 always shown automatically for token efficiency (~500 tokens)[/dim]"
    )

    if args.detailed and in_progress:
        console.print("\n[bold]📄 Full Session Details:[/bold]")
        for entry in in_progress[:1]:  # Show first in-progress memory in full
            entry_data = entry.get("entry", {})
            filename = entry_data.get("filename")
            title = entry_data.get("title", "Untitled")
            if filename:
                content = manager.read_memory(filename)
                console.print(
                    Panel(
                        Markdown(content.get("content", "")),
                        title=f"[bold]{title}[/bold]",
                        border_style="green",
                    )
                )

    return 0


def command_consolidate(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'consolidate' command - now with automated intelligence!"""
    # Use new automated consolidation engine
    from whitemagic.automation.consolidation import consolidate_cli
    consolidate_cli(args)
    return 0
    
    # Old manual consolidation (kept as fallback)
    # dry_run = not args.no_dry_run
    # result = manager.consolidate_short_term(dry_run=dry_run)

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


def command_backup(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'backup' command - create system backup."""
    backup_mgr = BackupManager(Path(args.base_dir))

    output_path = Path(args.output) if args.output else None
    last_backup = (
        Path(args.last_backup) if hasattr(args, "last_backup") and args.last_backup else None
    )

    try:
        # v2.2.2: Incremental backups re-enabled (implementation complete)
        result = backup_mgr.create_backup(
            output_path=output_path,
            incremental=args.incremental if hasattr(args, "incremental") else False,
            last_backup=last_backup,
            compress=not args.no_compress,
        )

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0

        if result["success"]:
            manifest = result["manifest"]
            print("✓ Backup created successfully!")
            print(f"  Path: {result['backup_path']}")
            print(f"  Files: {manifest['stats']['total_files']}")
            print(f"  Size: {manifest['stats']['total_size_mb']:.2f} MB")
            print(f"  Manifest: {result['manifest_path']}")
            return 0
        else:
            print(f"✗ Backup failed: {result.get('error')}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"✗ Backup error: {str(e)}", file=sys.stderr)
        return 1


def command_restore_backup(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'restore-backup' command - restore from system backup."""
    backup_mgr = BackupManager(Path(args.base_dir))
    backup_path = Path(args.backup_path)

    if not backup_path.exists():
        print(f"✗ Backup file not found: {backup_path}", file=sys.stderr)
        return 1

    try:
        result = backup_mgr.restore_backup(
            backup_path=backup_path,
            target_dir=Path(args.target_dir) if args.target_dir else None,
            verify=not args.no_verify,
            dry_run=args.dry_run,
        )

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0

        if result["success"]:
            if result.get("dry_run"):
                print(f"=== DRY RUN: Would restore {result['total_files']} files ===\n")
                for file_path in result["files_to_restore"][:10]:
                    print(f"  {file_path}")
                if len(result["files_to_restore"]) > 10:
                    print(f"  ... and {len(result['files_to_restore']) - 10} more")
            else:
                print("✓ Backup restored successfully!")
                print(f"  Restored files: {result['total_files']}")
                print(f"  Target: {result['target_dir']}")
                print(f"  Pre-restore backup: {result['pre_restore_backup']}")
            return 0
        else:
            print(f"✗ Restore failed: {result.get('error')}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"✗ Restore error: {str(e)}", file=sys.stderr)
        return 1


def command_list_backups(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'list-backups' command - list available backups."""
    backup_mgr = BackupManager(Path(args.base_dir))

    try:
        backups = backup_mgr.list_backups()

        if args.json:
            print(json.dumps(backups, indent=2, default=str))
            return 0

        if not backups:
            print("No backups found.")
            return 0

        print(f"=== AVAILABLE BACKUPS ({len(backups)}) ===\n")
        for backup in backups:
            print(f"  {backup['name']}")
            print(f"    Created: {backup['created']}")
            print(f"    Size: {backup['size_mb']:.2f} MB")
            if backup["has_manifest"] and backup["manifest"]:
                print(f"    Files: {backup['manifest']['stats']['total_files']}")
            print()

        return 0

    except Exception as e:
        print(f"✗ Error listing backups: {str(e)}", file=sys.stderr)
        return 1


def command_verify_backup(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'verify-backup' command - verify backup integrity."""
    backup_mgr = BackupManager(Path(args.base_dir))
    backup_path = Path(args.backup_path)

    try:
        result = backup_mgr.verify_backup(backup_path)

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return 0

        if result["valid"]:
            print("✓ Backup verification passed!")
            print(f"  Path: {result['backup_path']}")
            print(f"  Files: {result['file_count']}")
            print(f"  Has manifest: {result['has_manifest']}")
            if result["has_manifest"]:
                print(f"  Manifest valid: {result['manifest_valid']}")
            return 0
        else:
            print(f"✗ Backup verification failed: {result.get('error')}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"✗ Verification error: {str(e)}", file=sys.stderr)
        return 1


def command_exec(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'exec' command - execute terminal commands."""
    try:
        from whitemagic.terminal import ExecutionMode, Profile, TerminalMCPTools
    except ImportError:
        print(
            "✗ Terminal tools not available. Install with: pip install whitemagic[terminal]",
            file=sys.stderr,
        )
        return 1

    # Determine profile and mode
    profile = Profile.AGENT if args.write else Profile.PROD
    mode = ExecutionMode.WRITE if args.write else ExecutionMode.READ

    # Create tools (approver configured later)
    approver = None

    # Get approval for write operations
    if args.write:
        print("\n⚠️  Write Operation Requested", file=sys.stderr)
        print(f"Command: {args.cmd_name} {' '.join(args.cmd_args)}", file=sys.stderr)
        print(f"Working Directory: {args.cwd or 'current'}", file=sys.stderr)
        if args.env:
            print(f"Environment: {args.env}", file=sys.stderr)
        print("\n⚠️  This command will modify the filesystem!", file=sys.stderr)

        response = input("\nApprove this operation? [y/N]: ")
        if response.lower() != "y":
            print("✗ Operation cancelled by user", file=sys.stderr)
            return 1
        from whitemagic.terminal.approver import Approver

        approver = Approver(auto_approve=True)

    tools = TerminalMCPTools(profile=profile, approver=approver)

    # Execute
    try:
        import asyncio

        result = asyncio.run(
            tools.execute_command(
                cmd=args.cmd_name,
                args=args.cmd_args,
                mode=mode,
                cwd=args.cwd,
                timeout_ms=args.timeout * 1000,
            )
        )

        # Output result
        if args.json:
            print(json.dumps(result, indent=2))
            return 0 if result.get("success") else 1

        if result.get("success"):
            print(result.get("stdout", ""), end="")
            if result.get("stderr"):
                print(result["stderr"], file=sys.stderr, end="")
            return 0
        else:
            print(f"✗ Command failed: {result.get('error', 'Unknown error')}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"✗ Execution error: {str(e)}", file=sys.stderr)
        return 1


@async_command
async def command_search_semantic(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'search-semantic' command - semantic search with local/OpenAI embeddings."""
    try:
        from whitemagic.search import SearchMode, SemanticSearcher
    except ImportError:
        console = get_console()
        console.print(
            "✗ Semantic search not available. Install with: pip install whitemagic[search]",
            style="bold red",
        )
        return 1

    try:
        from rich.panel import Panel
        from rich.progress import Progress, SpinnerColumn, TextColumn
        from rich.table import Table

        console = get_console()

        # Create searcher with memory manager
        searcher = SemanticSearcher(memory_manager=manager)

        # Convert mode string to enum
        mode_map = {
            "keyword": SearchMode.KEYWORD,
            "semantic": SearchMode.SEMANTIC,
            "hybrid": SearchMode.HYBRID,
        }
        search_mode = mode_map.get(args.mode, SearchMode.HYBRID)

        # Search with spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Searching with {args.mode} mode...", total=None)

            results = await searcher.search(
                query=args.query,
                mode=search_mode,
                k=args.limit,
                memory_type=args.type,
                tags=args.tags,
            )

        # Output
        if args.json:
            print(json.dumps([r.__dict__ for r in results], indent=2, default=str))
            return 0

        if not results:
            console.print("\n[yellow]No results found.[/yellow]")
            return 0

        # Display results with rich formatting
        console.print(f"\n[bold green]Found {len(results)} results[/bold green]\n")

        for i, result in enumerate(results, 1):
            # Create a table for each result
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Field", style="cyan")
            table.add_column("Value")

            table.add_row("Title", f"[bold]{result.title}[/bold]")
            table.add_row("Score", f"[green]{result.score:.3f}[/green]")
            table.add_row("Type", result.type)
            if result.tags:
                table.add_row("Tags", f"[blue]{', '.join(result.tags)}[/blue]")

            # Show preview
            preview = result.content[:150] + "..." if len(result.content) > 150 else result.content
            table.add_row("Preview", preview)

            # Wrap in panel
            panel = Panel(
                table, title=f"[bold]Result {i}[/bold]", border_style="blue", expand=False
            )
            console.print(panel)

        return 0

    except Exception as e:
        console = get_console()
        console.print(f"\n[bold red]✗ Search error:[/bold red] {str(e)}")
        return 1


def command_embeddings_install(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'embeddings-install' command - install embedding model with progress."""
    from rich.console import Console
    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

    console = Console()

    # Get model name
    model = args.model

    # Load model name from config if not specified
    if not model:
        try:
            from whitemagic.config import get_config_manager

            config_mgr = get_config_manager()
            config = config_mgr.load()
            model = config.embeddings.model
        except Exception:
            model = "all-MiniLM-L6-v2"

    console.print(f"\n📦 Installing embedding model: [bold]{model}[/bold]")

    # Estimate size based on model
    estimated_mb = 90 if "MiniLM" in model else 420 if "mpnet" in model else 340
    console.print(f"   Estimated size: ~{estimated_mb}MB (one-time download)\n")

    try:
        from pathlib import Path

        from sentence_transformers import SentenceTransformer

        # Check if already cached
        cache_dir = Path.home() / ".cache" / "torch" / "sentence_transformers"
        model_cache = cache_dir / model.replace("/", "_")

        if model_cache.exists():
            console.print(f"✓ Model already installed at: {model_cache}\n")
            return 0

        # Download with progress simulation
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"Downloading {model}...", total=100)

            # The actual download happens inside SentenceTransformer
            # We simulate progress since sentence-transformers doesn't provide callbacks
            import threading

            download_complete = False
            model_obj = None
            error = None

            def download_model():
                nonlocal model_obj, error, download_complete
                try:
                    model_obj = SentenceTransformer(model)
                    download_complete = True
                except Exception as e:
                    error = e
                    download_complete = True

            # Start download in background
            thread = threading.Thread(target=download_model)
            thread.start()

            # Simulate progress while waiting
            import time

            while not download_complete:
                for i in range(0, 101, 5):
                    if download_complete:
                        progress.update(task, completed=100)
                        break
                    progress.update(task, completed=i)
                    time.sleep(0.2)

            thread.join()

            if error:
                raise error

            progress.update(task, completed=100)

        console.print("\n✓ Model installed successfully!")
        console.print(f"✓ Cached at: {model_cache}")
        console.print("\nYou can now use semantic search:")
        console.print("  [bold]whitemagic search-semantic 'your query'[/bold]\n")

        return 0

    except Exception as e:
        console.print(f"\n✗ Installation failed: {e}", style="bold red")
        return 1


def command_setup(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'setup' command - tier-aware interactive setup wizard."""
    from whitemagic.setup import SetupWizard

    wizard = SetupWizard()
    try:
        config = wizard.run()
        return 0
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        return 130
    except Exception as e:
        print(f"\n✗ Setup failed: {e}", file=sys.stderr)
        return 1


def command_setup_embeddings(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'setup-embeddings' command - interactive setup wizard."""

    print("🔧 Embeddings Configuration Wizard\n")

    # Provider selection
    print("Choose embedding provider:")
    print("  1. local (recommended) - Privacy-first, no API key needed")
    print("  2. openai - Higher quality, requires API key")

    choice = input("\nSelect [1/2] (default: 1): ").strip() or "1"

    if choice == "1":
        # Local provider
        print("\nLocal embeddings selected!")
        print("\nChoose model:")
        print("  1. all-MiniLM-L6-v2 (recommended) - Fast, 90MB, good quality")
        print("  2. all-mpnet-base-v2 - Better quality, 420MB, slower")

        model_choice = input("\nSelect [1/2] (default: 1): ").strip() or "1"
        model = "all-MiniLM-L6-v2" if model_choice == "1" else "all-mpnet-base-v2"

        # Download model
        print(f"\nDownloading model: {model}...")
        try:
            from sentence_transformers import SentenceTransformer

            SentenceTransformer(model)  # Downloads if needed
            print("✓ Model downloaded successfully!")
        except Exception as e:
            print(f"✗ Error downloading model: {e}", file=sys.stderr)
            return 1

        print("\n✓ Local embeddings configured!")
        print("\nTo use these settings, set environment variables:")
        print("  export WM_EMBEDDING_PROVIDER=local")
        print(f"  export WM_EMBEDDING_MODEL={model}")
        print("\nOr add to your .env file:")
        print("  WM_EMBEDDING_PROVIDER=local")
        print(f"  WM_EMBEDDING_MODEL={model}")

    elif choice == "2":
        # OpenAI provider
        print("\nOpenAI embeddings selected!")
        import getpass

        api_key = getpass.getpass("\nEnter OpenAI API key: ")

        if not api_key:
            print("✗ API key required", file=sys.stderr)
            return 1

        # Test key
        print("\nTesting API key...")
        try:
            from whitemagic.embeddings import OpenAIEmbeddings

            provider = OpenAIEmbeddings(api_key)
            # Test with a simple embedding
            import asyncio

            asyncio.run(provider.embed("test"))
            print("✓ API key validated!")
        except Exception as e:
            print(f"✗ API key validation failed: {e}", file=sys.stderr)
            return 1

        print("\n✓ OpenAI embeddings configured!")
        print("\nTo use these settings, set environment variables:")
        print("  export WM_EMBEDDING_PROVIDER=openai")
        print(f"  export OPENAI_API_KEY={api_key[:8]}...")
        print("\nOr add to your .env file:")
        print("  WM_EMBEDDING_PROVIDER=openai")
        print(f"  OPENAI_API_KEY={api_key}")

    else:
        print("✗ Invalid choice", file=sys.stderr)
        return 1

    print("\n✓ Setup complete! You can now use semantic search.")
    return 0


def command_config_get(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'config get' command - get config value."""
    from whitemagic.config import ConfigManager

    config_mgr = ConfigManager()
    value = config_mgr.get(args.key)

    if value is None:
        print(f"✗ Config key not found: {args.key}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"key": args.key, "value": value}))
    else:
        print(value)

    return 0


def command_config_set(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'config set' command - set config value."""
    from whitemagic.config import ConfigManager

    config_mgr = ConfigManager()

    # Smart type conversion for common types
    value = args.value
    # Try to convert to appropriate type
    if value.lower() in ("true", "yes", "on", "1"):
        value = True
    elif value.lower() in ("false", "no", "off", "0"):
        value = False
    elif value.isdigit():
        value = int(value)
    elif value.replace(".", "", 1).isdigit() and value.count(".") == 1:
        value = float(value)

    try:
        config_mgr.set(args.key, value)
        print(f"✓ Set {args.key} = {value}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_config_show(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'config show' command - display all config."""
    import yaml

    from whitemagic.config import ConfigManager

    config_mgr = ConfigManager()
    config = config_mgr.load()

    if args.json:
        print(json.dumps(config.model_dump(), indent=2))
    else:
        print(yaml.dump(config.model_dump(), default_flow_style=False, sort_keys=False))

    return 0


def command_config_path(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'config path' command - show config file path."""
    from whitemagic.config import ConfigManager

    config_mgr = ConfigManager()
    path = config_mgr.get_path()

    if args.json:
        print(json.dumps({"config_path": str(path)}))
    else:
        print(path)

    return 0


def command_ai_init(manager: MemoryManager, args: argparse.Namespace) -> int:
    """
    Handle 'ai-init' command.

    Display comprehensive initialization guide for AI assistants.
    Shows essential documentation, project structure, and workflow recommendations.
    """
    from pathlib import Path

    from rich.console import Console
    from rich.text import Text

    console = Console()

    # Header
    console.print("\n[bold cyan]🪄 WhiteMagic AI Initialization Guide[/bold cyan]\n")

    # 1. Project Overview
    console.print("[bold]📖 Essential Documentation[/bold]")
    console.print("  • Overview: [cyan]docs/OVERVIEW.md[/cyan]")
    console.print("  • Quick Start: [cyan]docs/guides/QUICKSTART.md[/cyan]")
    console.print("  • Architecture: [cyan]docs/ARCHITECTURE.md[/cyan]")
    console.print("  • Latest Release: [cyan]docs/releases/RELEASE_NOTES_v2.2.6.md[/cyan]\n")

    # 2. Key Concepts
    console.print("[bold]🧠 Core Concepts to Understand[/bold]")
    console.print("  1. [yellow]Meta-Optimization[/yellow]: 94% token reduction via tiered loading")
    console.print("     → [cyan]docs/guides/META_OPTIMIZATION.md[/cyan]")
    console.print(
        "  2. [yellow]Memory System[/yellow]: Short-term, long-term, and archived memories"
    )
    console.print("     → [cyan]docs/guides/MEMORY_SYSTEM_README.md[/cyan]")
    console.print("  3. [yellow]CLI Metrics[/yellow]: Track token efficiency and workflow")
    console.print("     → [cyan]docs/guides/CLI_METRICS.md[/cyan]\n")

    # 3. Project Structure
    console.print("[bold]📁 Project Structure[/bold]")
    structure = """
whitemagic/
├── whitemagic/        # Python package
│   ├── cli/           # CLI commands
│   ├── api/           # FastAPI server
│   ├── embeddings/    # Semantic search
│   └── ...
├── whitemagic-mcp/    # MCP server (TypeScript)
├── tests/             # Test suite
├── docs/              # Documentation
│   ├── guides/        # How-to guides
│   ├── production/    # Deployment
│   └── sdk/           # Client libraries
├── memory/            # Memory storage (gitignored)
└── users/             # Multi-user storage (gitignored)
    """
    console.print(Text(structure, style="dim"))

    # 4. Quick Commands
    console.print("[bold]⚡ Quick Commands[/bold]")
    console.print("  [yellow]whitemagic stats[/yellow]              # Show memory statistics")
    console.print("  [yellow]whitemagic list[/yellow]               # List all memories")
    console.print("  [yellow]whitemagic context --tier 1[/yellow]   # Generate context")
    console.print("  [yellow]pytest -q[/yellow]                   # Run tests\n")

    # 5. Current Version
    version_file = Path("VERSION")
    if version_file.exists():
        version = version_file.read_text().strip()
        console.print(f"[bold]📌 Current Version:[/bold] v{version}\n")

    # 6. Important Notes
    console.print("[bold yellow]⚠️  Important Notes[/bold yellow]")
    console.print(
        "  • Use [cyan]Tier 0/1[/cyan] context loading to save tokens (see META_OPTIMIZATION.md)"
    )
    console.print("  • Memory files are [yellow]personal[/yellow] - excluded from git")
    console.print("  • Read [cyan]CONTRIBUTING.md[/cyan] before making changes")
    console.print("  • Check [cyan]ROADMAP.md[/cyan] for future plans\n")

    # 7. Workflow Recommendations
    console.print("[bold]🎯 Recommended AI Workflow[/bold]")
    console.print("  1. Start with [cyan]Tier 0[/cyan] context scan")
    console.print("  2. Load specific files as needed")
    console.print("  3. Track metrics: [yellow]whitemagic metrics-track ...[/yellow]")
    console.print("  4. Create memories for important decisions")
    console.print("  5. Consolidate when you have 5-10 short-term memories\n")

    # 8. Stats (if available)
    try:
        from whitemagic.stats import generate_stats

        stats = generate_stats(manager)
        total = stats.get("total_memories", 0)
        console.print(f"[bold]📊 Current Memory Count:[/bold] {total} memories")
        console.print(f"  • Short-term: {stats.get('by_type', {}).get('short_term', 0)}")
        console.print(f"  • Long-term: {stats.get('by_type', {}).get('long_term', 0)}\n")
    except Exception:
        # Gracefully handle if stats aren't available
        console.print("[bold]📊 Memory System:[/bold] Ready\n")

    console.print("[bold green]✅ Ready to go! Use commands above to explore.[/bold green]\n")

    return 0


def command_stats(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'stats' command - show memory statistics dashboard."""
    from whitemagic.stats import generate_stats, print_stats_dashboard

    stats = generate_stats(manager)

    if args.json:
        stats["by_type"] = dict(stats["by_type"])
        stats["by_status"] = dict(stats["by_status"])
        print(json.dumps(stats, indent=2, default=str))
    else:
        print_stats_dashboard(stats)

    return 0


def command_metrics_track(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'metrics-track' command."""
    from whitemagic.metrics import track_metric

    try:
        track_metric(
            category=args.category,
            metric=args.metric,
            value=float(args.value),
            context=args.context,
        )
        print(f"✓ Tracked {args.category}/{args.metric} = {args.value}")
        if args.context:
            print(f"  Context: {args.context}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_metrics_summary(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'metrics-summary' command."""
    from whitemagic.metrics import get_tracker

    tracker = get_tracker()
    categories = args.categories if hasattr(args, "categories") and args.categories else None

    try:
        summary = tracker.get_summary(categories)

        if args.json:
            print(json.dumps(summary, indent=2, default=str))
            return 0

        from rich.table import Table

        console = get_console()

        console.print("\n[bold cyan]📊 Metrics Summary[/bold cyan]\n")

        for category, data in summary.items():
            # Skip empty categories and token_tracking (shown separately)
            if category == "token_tracking":
                continue
            if isinstance(data, dict) and data.get("count", 0) == 0:
                continue

            console.print(f"[yellow]{category.upper()}[/yellow]")
            table = Table(show_header=True, header_style="bold magenta", box=None)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            # Special handling for task metrics
            if category == "tasks":
                table.add_row("Total Tasks", str(data["count"]))
                if data.get("total_tokens", 0) > 0:
                    table.add_row("Total Tokens", f"{data['total_tokens']:,}")
                    table.add_row("Avg Tokens/Task", f"{data['avg_tokens']:.0f}")
                table.add_row("Total Duration", f"{data['total_duration_s']:.1f}s")
                table.add_row("Avg Duration", f"{data['avg_duration_s']:.2f}s")
                table.add_row("Success Rate", f"{data['success_rate']:.1%}")

                if data.get("latest"):
                    latest = data["latest"]
                    table.add_row("Latest Task", latest.get("task_name", "N/A"))
                    if latest.get("tokens_used", 0) > 0:
                        table.add_row("Latest Tokens", f"{latest['tokens_used']:,}")
            else:
                # Custom metric display
                if data.get("latest"):
                    latest = data["latest"]
                    table.add_row("Latest Value", str(latest.get("value", "N/A")))
                    table.add_row("Latest Metric", latest.get("metric", "N/A"))
                    if latest.get("context"):
                        table.add_row("Context", latest.get("context", "N/A")[:50])

                if "average" in data:
                    table.add_row("Average", f"{data['average']:.2f}")
                table.add_row("Total Entries", str(data["count"]))

            console.print(table)
            console.print()

        # Show token tracking status
        if "token_tracking" in summary:
            tk = summary["token_tracking"]
            status_emoji = "✅" if tk["available"] else "⚠️"
            console.print(f"{status_emoji} [dim]Token Tracking: {tk['method']}[/dim]\n")

        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_metrics_export(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'metrics-export' command."""
    from pathlib import Path

    from whitemagic.metrics import get_tracker

    tracker = get_tracker()
    output_path = Path(args.output)

    try:
        categories = args.categories if hasattr(args, "categories") and args.categories else None
        summary = tracker.get_summary(categories)

        if args.format == "json":
            output_path.write_text(json.dumps(summary, indent=2, default=str))
        elif args.format == "csv":
            import csv

            with output_path.open("w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Category", "Metric", "Value", "Context", "Timestamp"])

                for category, data in summary.items():
                    if data.get("latest"):
                        latest = data["latest"]
                        writer.writerow(
                            [
                                category,
                                latest.get("metric", ""),
                                latest.get("value", ""),
                                latest.get("context", ""),
                                latest.get("timestamp", ""),
                            ]
                        )

        print(f"✓ Exported to: {output_path}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


from whitemagic.automation.precommit import PreCommitAutoFix
from whitemagic.cli_graph import command_graph, command_graph_stats
from whitemagic.cli_relationships import command_relate, command_related

# Import template commands
from whitemagic.cli_templates import (
    command_template_create,
    command_template_list,
    command_template_show,
)


# New automation command handlers
def command_audit(manager, args):
    results = audit_project(full=args.full)
    print_audit_report(results)
    return 0


def command_docs_check(manager, args):
    issues = docs_check_and_fix(fix=args.fix, dry_run=args.dry_run)
    if not issues:
        print("✅ No drift detected!")
    else:
        print(f"Found {len(issues)} files with drift")
    return 0


def command_version_bump(manager, args):
    bump_version(args.new_version, commit=not args.no_commit)
    return 0


def command_precommit_autofix(manager, args):
    """Run pre-commit with auto-fix."""
    fixer = PreCommitAutoFix(max_attempts=args.max_attempts, timeout=args.timeout)
    success, message = fixer.run_with_autofix(args.files)
    print(message)
    return 0 if success else 1


def command_test_watch(manager, args):
    """Watch files and auto-run tests."""
    watcher = TestWatcher(watch_path=args.path, pattern=args.pattern)
    watcher.watch(test_command=args.command)
    return 0


def command_pad_new(manager, args):
    """Create a new scratchpad channel."""
    from whitemagic.agentic.terminal_multiplex import create_pad
    try:
        pad = create_pad(args.name, args.description or "")
        print(f"✓ Created scratchpad channel: {args.name}")
        print(f"  Use 'whitemagic pad switch {args.name}' to activate")
        return 0
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_pad_switch(manager, args):
    """Switch to a scratchpad channel."""
    from whitemagic.agentic.terminal_multiplex import switch_pad
    try:
        pad = switch_pad(args.name)
        print(f"✓ Switched to scratchpad: {args.name}")
        return 0
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_pad_list(manager, args):
    """List all scratchpad channels."""
    from whitemagic.agentic.terminal_multiplex import list_pads
    from rich.table import Table
    from rich.console import Console
    
    pads = list_pads()
    
    if not pads:
        print("No active scratchpad channels.")
        print("Create one with: whitemagic pad new <name>")
        return 0
    
    console = Console()
    table = Table(title="Scratchpad Channels", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Task", style="white")
    table.add_column("Created", style="dim")
    table.add_column("Status", style="green")
    
    for pad in pads:
        status = "🟢 ACTIVE" if pad["is_current"] else "⚪"
        created = pad["created"][:10] if pad["created"] else "N/A"
        table.add_row(
            pad["name"],
            pad["task_description"][:40] if pad["task_description"] else "(no description)",
            created,
            status
        )
    
    console.print(table)
    return 0


def command_pad_show(manager, args):
    """Show content of a scratchpad channel."""
    from whitemagic.agentic.terminal_multiplex import get_multiplex
    try:
        multiplex = get_multiplex()
        content = multiplex.show_pad(args.name)
        print(content)
        return 0
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_pad_close(manager, args):
    """Close a scratchpad channel."""
    from whitemagic.agentic.terminal_multiplex import get_multiplex
    try:
        multiplex = get_multiplex()
        memory_path = multiplex.close_pad(args.name, finalize_to_memory=not args.no_finalize)
        
        if memory_path:
            print(f"✓ Closed pad '{args.name}' and finalized to memory: {memory_path}")
        else:
            print(f"✓ Closed pad '{args.name}' (not finalized)")
        return 0
    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_confidence_record(manager, args):
    """Record a confidence prediction outcome."""
    from whitemagic.agentic.confidence_learning import record_outcome
    import json
    
    try:
        # Parse factors JSON
        factors = json.loads(args.factors) if args.factors else {}
        
        record_outcome(
            task_id=args.task_id,
            task_name=args.task_name,
            predicted_confidence=args.predicted,
            actual_success=args.success,
            factors=factors,
            category=args.category or "general",
            notes=args.notes or "",
        )
        
        print(f"✓ Recorded outcome for task: {args.task_name}")
        print(f"  Predicted: {args.predicted:.2f}, Actual: {'SUCCESS' if args.success else 'FAILURE'}")
        return 0
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def command_confidence_stats(manager, args):
    """Show confidence calibration statistics."""
    from whitemagic.agentic.confidence_learning import get_learner
    from rich.table import Table
    from rich.console import Console
    
    learner = get_learner()
    stats = learner.get_calibration_stats()
    
    console = Console()
    
    console.print("\n[bold cyan]🎯 Confidence Calibration Statistics[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Predictions", str(stats["total_predictions"]))
    table.add_row("Accuracy", f"{stats['accuracy']:.1%}")
    table.add_row("Over-Confidence Rate", f"{stats['over_confidence_rate']:.1%}")
    table.add_row("Under-Confidence Rate", f"{stats['under_confidence_rate']:.1%}")
    table.add_row("Mean Prediction Error", f"{stats['mean_error']:.3f}")
    
    console.print(table)
    
    # Show category breakdown if requested
    if args.category:
        cat_stats = learner.get_category_stats(args.category)
        console.print(f"\n[bold yellow]Category: {args.category}[/bold yellow]\n")
        cat_table = Table(show_header=True)
        cat_table.add_column("Metric", style="cyan")
        cat_table.add_column("Value", style="green")
        cat_table.add_row("Predictions", str(cat_stats["total_predictions"]))
        cat_table.add_row("Accuracy", f"{cat_stats['accuracy']:.1%}")
        cat_table.add_row("Mean Confidence", f"{cat_stats['mean_confidence']:.2f}")
        cat_table.add_row("Success Rate", f"{cat_stats['success_rate']:.1%}")
        console.print(cat_table)
    
    return 0


def command_confidence_calibrate(manager, args):
    """Auto-calibrate confidence weights based on outcomes."""
    from whitemagic.agentic.confidence_learning import auto_calibrate, get_learner
    from rich.table import Table
    from rich.console import Console
    
    console = Console()
    learner = get_learner()
    
    old_weights = learner.weights.copy()
    new_weights = auto_calibrate(min_samples=args.min_samples)
    
    console.print("\n[bold cyan]⚙️ Auto-Calibration Results[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Factor", style="cyan")
    table.add_column("Old Weight", style="yellow")
    table.add_column("New Weight", style="green")
    table.add_column("Change", style="white")
    
    for factor in sorted(new_weights.keys()):
        old = old_weights.get(factor, 0.0)
        new = new_weights[factor]
        change = new - old
        change_str = f"{change:+.3f}"
        table.add_row(factor, f"{old:.3f}", f"{new:.3f}", change_str)
    
    console.print(table)
    console.print(f"\n[dim]Based on {len(learner.outcomes)} outcomes[/dim]")
    
    return 0


def command_immune(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'immune' command with subcommands."""
    if hasattr(args, 'func'):
        # Call the subcommand function directly (it doesn't need manager)
        args.func(args)
        return 0
    else:
        print("Error: No immune subcommand specified")
        print("Available subcommands: scan, heal, status")
        return 1


def command_orchestra(manager: MemoryManager, args: argparse.Namespace) -> int:
    """Handle 'orchestra' command with subcommands."""
    if hasattr(args, 'func'):
        # Call the subcommand function directly
        args.func(args)
        return 0
    else:
        print("Error: No orchestra subcommand specified")
        print("Available subcommands: health, maintain, emergency")
        return 1


# Command dispatch table
COMMAND_HANDLERS = {
    "ai-init": command_ai_init,
    "audit": command_audit,
    "docs-check": command_docs_check,
    "version": command_version_bump,
    "precommit-fix": command_precommit_autofix,
    "test-watch": command_test_watch,
    "create": command_create,
    "list": command_list,
    "search": command_search,
    "context": command_context,
    "resume": command_resume,
    "consolidate": command_consolidate,
    "delete": command_delete,
    "update": command_update,
    "list-tags": command_list_tags,
    "restore": command_restore,
    "normalize-tags": command_normalize_tags,
    "backup": command_backup,
    "restore-backup": command_restore_backup,
    "list-backups": command_list_backups,
    "verify-backup": command_verify_backup,
    "exec": command_exec,
    "search-semantic": command_search_semantic,
    "embeddings-install": command_embeddings_install,
    "setup": command_setup,
    "setup-embeddings": command_setup_embeddings,
    "config-get": command_config_get,
    "config-set": command_config_set,
    "config-show": command_config_show,
    "config-path": command_config_path,
    "template-list": command_template_list,
    "template-show": command_template_show,
    "template-create": command_template_create,
    "relate": command_relate,
    "related": command_related,
    "graph": command_graph,
    "graph-stats": command_graph_stats,
    "stats": command_stats,
    "metrics-track": command_metrics_track,
    "metrics-summary": command_metrics_summary,
    "metrics-export": command_metrics_export,
    "pad-new": command_pad_new,
    "pad-switch": command_pad_switch,
    "pad-list": command_pad_list,
    "pad-show": command_pad_show,
    "pad-close": command_pad_close,
    "confidence-record": command_confidence_record,
    "confidence-stats": command_confidence_stats,
    "confidence-calibrate": command_confidence_calibrate,
    "immune": command_immune,
    "orchestra": command_orchestra,
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
    create_parser = subparsers.add_parser("create", help="Create a new memory entry.")
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
    create_parser.add_argument(
        "--no-auto-tag",
        action="store_true",
        help="Disable automatic tag suggestions.",
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
    context_parser.add_argument(
        "--role",
        type=str,
        help="Task role for smart preloading (e.g., bug-fix, feature, audit, refactor, documentation).",
    )

    # resume
    resume_parser = subparsers.add_parser(
        "resume",
        help="Show recent context for session continuity (always shows tier 0 quick scan + optional deeper tiers).",
    )
    resume_parser.add_argument(
        "--tier",
        type=int,
        choices=[0, 1, 2],
        default=None,
        help="Include additional context at specified tier (tier 0 always shown, use 1 or 2 for more detail).",
    )
    resume_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show full content of most recent in-progress memory.",
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
    delete_parser = subparsers.add_parser("delete", help="Delete or archive a memory.")
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
    restore_parser = subparsers.add_parser("restore", help="Restore an archived memory.")
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

    # backup
    backup_parser = subparsers.add_parser(
        "backup",
        help="Create a system backup of all WhiteMagic memories.",
    )
    backup_parser.add_argument(
        "-o",
        "--output",
        help="Output path for backup file (default: backups/backup_TIMESTAMP.tar.gz).",
    )
    # TODO v2.1.7: Implement incremental backups
    # Incremental flag removed until manifest diffing is implemented
    # See: docs/development/SECURITY_REVIEW_NOV14_2025.md #3
    backup_parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Skip compression (faster but larger).",
    )
    backup_parser.add_argument(
        "--json",
        action="store_true",
        help="Output backup result as JSON.",
    )

    # restore-backup
    restore_backup_parser = subparsers.add_parser(
        "restore-backup",
        help="Restore WhiteMagic system from a backup.",
    )
    restore_backup_parser.add_argument(
        "backup_path",
        help="Path to backup file to restore.",
    )
    restore_backup_parser.add_argument(
        "--target-dir",
        help="Target directory for restore (default: current base directory).",
    )
    restore_backup_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip backup verification before restoring.",
    )
    restore_backup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored without actually restoring.",
    )
    restore_backup_parser.add_argument(
        "--json",
        action="store_true",
        help="Output restore result as JSON.",
    )

    # list-backups
    list_backups_parser = subparsers.add_parser(
        "list-backups",
        help="List all available backup files.",
    )
    list_backups_parser.add_argument(
        "--json",
        action="store_true",
        help="Output backups list as JSON.",
    )

    # verify-backup
    verify_backup_parser = subparsers.add_parser(
        "verify-backup",
        help="Verify backup file integrity.",
    )
    verify_backup_parser.add_argument(
        "backup_path",
        help="Path to backup file to verify.",
    )
    verify_backup_parser.add_argument(
        "--json",
        action="store_true",
        help="Output verification result as JSON.",
    )

    # exec
    exec_parser = subparsers.add_parser(
        "exec",
        help="Execute terminal commands safely.",
    )
    exec_parser.add_argument(
        "cmd_name",
        help="Command to execute (e.g., 'ls', 'git', 'rg').",
    )
    exec_parser.add_argument(
        "cmd_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Arguments to pass to the command (place CLI options before the command, e.g., '--json exec ls -la').",
    )
    exec_parser.add_argument(
        "--write",
        action="store_true",
        help="Enable write operations (requires approval).",
    )
    exec_parser.add_argument(
        "--cwd",
        help="Working directory for command execution.",
    )
    exec_parser.add_argument(
        "--env",
        help="Environment variables as JSON string.",
    )
    exec_parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds (default: 30).",
    )
    exec_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON.",
    )

    # search-semantic
    search_semantic_parser = subparsers.add_parser(
        "search-semantic",
        help="Semantic search with local or OpenAI embeddings.",
    )
    search_semantic_parser.add_argument(
        "query",
        help="Search query.",
    )
    search_semantic_parser.add_argument(
        "--mode",
        choices=["keyword", "semantic", "hybrid"],
        default="hybrid",
        help="Search mode (default: hybrid).",
    )
    search_semantic_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10).",
    )
    search_semantic_parser.add_argument(
        "--type",
        choices=["short_term", "long_term"],
        help="Filter by memory type.",
    )
    search_semantic_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        help="Filter by tags (can be specified multiple times).",
    )
    search_semantic_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    # embeddings-install
    embeddings_install_parser = subparsers.add_parser(
        "embeddings-install",
        help="Install embedding model with progress bar.",
    )
    embeddings_install_parser.add_argument(
        "--model",
        help="Model name to install (default: from config or all-MiniLM-L6-v2).",
    )

    # setup
    setup_parser = subparsers.add_parser(
        "setup",
        help="Interactive setup wizard for first-run configuration.",
    )

    # setup-embeddings
    setup_embeddings_parser = subparsers.add_parser(
        "setup-embeddings",
        help="Interactive wizard to configure embedding providers.",
    )

    # config-get
    config_get_parser = subparsers.add_parser(
        "config-get",
        help="Get a configuration value by key (e.g., 'embeddings.provider').",
    )
    config_get_parser.add_argument(
        "key",
        help="Config key in dot notation (e.g., 'embeddings.provider', 'search.max_results').",
    )
    config_get_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # config-set
    config_set_parser = subparsers.add_parser(
        "config-set",
        help="Set a configuration value.",
    )
    config_set_parser.add_argument(
        "key",
        help="Config key in dot notation.",
    )
    config_set_parser.add_argument(
        "value",
        help="New value for the key.",
    )

    # config-show
    config_show_parser = subparsers.add_parser(
        "config-show",
        help="Display all configuration settings.",
    )
    config_show_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # config-path
    config_path_parser = subparsers.add_parser(
        "config-path",
        help="Show path to config file.",
    )
    config_path_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # template-list
    template_list_parser = subparsers.add_parser(
        "template-list",
        help="List available memory templates.",
    )
    template_list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # template-show
    template_show_parser = subparsers.add_parser(
        "template-show",
        help="Show template details.",
    )
    template_show_parser.add_argument(
        "name",
        help="Template name to show.",
    )
    template_show_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # template-create
    template_create_parser = subparsers.add_parser(
        "template-create",
        help="Create a memory from a template interactively.",
    )
    template_create_parser.add_argument(
        "template",
        help="Template name to use.",
    )
    template_create_parser.add_argument(
        "--title",
        help="Memory title (prompted if not provided).",
    )
    template_create_parser.add_argument(
        "--tags",
        nargs="+",
        help="Additional tags (template tags included automatically).",
    )

    # relate
    relate_parser = subparsers.add_parser(
        "relate",
        help="Link two memories with a relationship.",
    )
    relate_parser.add_argument("source", help="Source memory filename.")
    relate_parser.add_argument("target", help="Target memory filename.")
    relate_parser.add_argument(
        "--type",
        choices=[
            "depends_on",
            "implements",
            "supersedes",
            "informed_by",
            "relates_to",
            "contradicts",
        ],
        default="relates_to",
        help="Relationship type.",
    )
    relate_parser.add_argument("--description", help="Optional description.")

    # related
    related_parser = subparsers.add_parser(
        "related",
        help="Show relationships for a memory.",
    )
    related_parser.add_argument("filename", help="Memory filename.")
    related_parser.add_argument(
        "--type",
        choices=[
            "depends_on",
            "implements",
            "supersedes",
            "informed_by",
            "relates_to",
            "contradicts",
        ],
        help="Filter by relationship type.",
    )

    # graph
    graph_parser = subparsers.add_parser(
        "graph",
        help="Show relationship graph for a memory.",
    )
    graph_parser.add_argument("filename", help="Memory filename.")
    graph_parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Maximum depth for graph traversal (default: 2).",
    )
    graph_parser.add_argument(
        "--type",
        choices=[
            "depends_on",
            "implements",
            "supersedes",
            "informed_by",
            "relates_to",
            "contradicts",
        ],
        help="Filter relationships by type.",
    )

    # graph-stats
    graph_stats_parser = subparsers.add_parser(
        "graph-stats",
        help="Show graph statistics for all memories.",
    )
    graph_stats_parser.add_argument(
        "--show-orphaned",
        action="store_true",
        help="Show memories with no relationships.",
    )

    # ai-init
    ai_init_parser = subparsers.add_parser(
        "ai-init",
        help="Initialize AI assistant with WhiteMagic project context.",
    )

    # audit
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run project health check.",
    )
    audit_parser.add_argument("--full", action="store_true", help="Full audit (slower)")

    # docs-check
    docs_parser = subparsers.add_parser(
        "docs-check",
        help="Check/fix documentation version drift.",
    )
    docs_parser.add_argument("--fix", action="store_true", help="Auto-fix drift")
    docs_parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed")

    # version
    version_parser = subparsers.add_parser(
        "version",
        help="Bump version across all files.",
    )
    version_parser.add_argument("new_version", help="New version (e.g., 2.2.9)")
    version_parser.add_argument("--no-commit", action="store_true", help="Don't auto-commit")

    # precommit-fix
    precommit_parser = subparsers.add_parser(
        "precommit-fix",
        help="Run pre-commit with auto-fix loop.",
    )
    precommit_parser.add_argument("--files", nargs="+", help="Specific files to check")
    precommit_parser.add_argument("--max-attempts", type=int, default=3, help="Max fix attempts")
    precommit_parser.add_argument(
        "--timeout", type=int, default=300, help="Timeout in seconds (default: 300)"
    )

    # test-watch
    test_watch_parser = subparsers.add_parser(
        "test-watch",
        help="Watch files and auto-run tests on changes.",
    )
    test_watch_parser.add_argument("--path", default=".", help="Path to watch")
    test_watch_parser.add_argument("--pattern", default="**/*.py", help="File pattern")
    test_watch_parser.add_argument("--command", default="pytest -v", help="Test command")

    # pad-new
    pad_new_parser = subparsers.add_parser(
        "pad-new",
        help="Create a new scratchpad channel for parallel thought streams.",
    )
    pad_new_parser.add_argument("name", help="Channel name (e.g., 'bug-fix', 'feature-auth')")
    pad_new_parser.add_argument("--description", help="Task description")

    # pad-switch
    pad_switch_parser = subparsers.add_parser(
        "pad-switch",
        help="Switch to an existing scratchpad channel.",
    )
    pad_switch_parser.add_argument("name", help="Channel name to switch to")

    # pad-list
    pad_list_parser = subparsers.add_parser(
        "pad-list",
        help="List all active scratchpad channels.",
    )

    # pad-show
    pad_show_parser = subparsers.add_parser(
        "pad-show",
        help="Show content of a scratchpad channel.",
    )
    pad_show_parser.add_argument("name", help="Channel name to show")

    # pad-close
    pad_close_parser = subparsers.add_parser(
        "pad-close",
        help="Close a scratchpad channel (optionally finalize to memory).",
    )
    pad_close_parser.add_argument("name", help="Channel name to close")
    pad_close_parser.add_argument("--no-finalize", action="store_true", help="Don't save to memory")

    # confidence-record
    confidence_record_parser = subparsers.add_parser(
        "confidence-record",
        help="Record a confidence prediction outcome for learning.",
    )
    confidence_record_parser.add_argument("task_id", help="Unique task identifier")
    confidence_record_parser.add_argument("task_name", help="Human-readable task name")
    confidence_record_parser.add_argument("predicted", type=float, help="Predicted confidence (0.0-1.0)")
    confidence_record_parser.add_argument("--success", action="store_true", help="Task succeeded")
    confidence_record_parser.add_argument("--factors", help='Factor scores as JSON (e.g., \'{"has_tests": 0.8}\')')
    confidence_record_parser.add_argument("--category", help="Task category (e.g., bug-fix, feature)")
    confidence_record_parser.add_argument("--notes", help="Optional notes about the outcome")

    # confidence-stats
    confidence_stats_parser = subparsers.add_parser(
        "confidence-stats",
        help="Show confidence calibration statistics.",
    )
    confidence_stats_parser.add_argument("--category", help="Show stats for specific category")

    # confidence-calibrate
    confidence_calibrate_parser = subparsers.add_parser(
        "confidence-calibrate",
        help="Auto-calibrate confidence weights based on outcomes.",
    )
    confidence_calibrate_parser.add_argument(
        "--min-samples", type=int, default=10, help="Minimum outcomes before calibrating (default: 10)"
    )

    # stats
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show memory statistics dashboard.",
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON.",
    )

    # metrics-track
    metrics_track_parser = subparsers.add_parser(
        "metrics-track",
        help="Track a metric value.",
    )
    metrics_track_parser.add_argument(
        "--category", required=True, help="Metric category (e.g., token_efficiency)"
    )
    metrics_track_parser.add_argument(
        "--metric", required=True, help="Metric name (e.g., usage_percent)"
    )
    metrics_track_parser.add_argument("--value", required=True, help="Metric value (numeric)")
    metrics_track_parser.add_argument("--context", help="Optional context string")

    # metrics-summary
    metrics_summary_parser = subparsers.add_parser(
        "metrics-summary",
        help="Display metrics summary dashboard.",
    )
    metrics_summary_parser.add_argument("--categories", nargs="+", help="Filter by categories")
    metrics_summary_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # metrics-export
    metrics_export_parser = subparsers.add_parser(
        "metrics-export",
        help="Export metrics to file.",
    )
    metrics_export_parser.add_argument("--output", required=True, help="Output file path")
    metrics_export_parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Export format"
    )
    metrics_export_parser.add_argument("--categories", nargs="+", help="Filter by categories")

    # Register immune system commands
    register_immune_commands(subparsers)
    
    # Register automation orchestra commands
    register_orchestra_commands(subparsers)

    return parser


# ---------------------------------------------------------------------- #
# Main Entry Point
# ---------------------------------------------------------------------- #


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main CLI entry point."""
    import os

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    # Support environment variable for base_dir (parallel contexts)
    # Priority: CLI arg > WHITEMAGIC_BASE_DIR env > default
    base_dir = args.base_dir
    if base_dir == "." and "WHITEMAGIC_BASE_DIR" in os.environ:
        base_dir = os.environ["WHITEMAGIC_BASE_DIR"]

    manager = MemoryManager(base_dir=base_dir)
    handler = COMMAND_HANDLERS.get(args.command)
    if not handler:
        parser.error(f"Unknown command: {args.command}")
        return 2

    return handler(manager, args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
