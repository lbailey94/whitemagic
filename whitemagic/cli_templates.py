"""CLI commands for template management."""

import sys
import json
import argparse
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Prompt

if TYPE_CHECKING:
    from whitemagic.core import MemoryManager


def command_template_list(manager: "MemoryManager", args: argparse.Namespace) -> int:
    """List available templates."""
    from whitemagic.templates import TemplateManager
    
    tmpl_mgr = TemplateManager()
    templates = tmpl_mgr.list_templates()
    
    if not templates:
        print("No templates available.")
        return 0
    
    if getattr(args, 'json', False):
        print(json.dumps({"templates": templates}))
    else:
        print("Available templates:")
        for name in templates:
            template = tmpl_mgr.get_template(name)
            print(f"  {name:<20} - {template.description if template else ''}")
    
    return 0


def command_template_show(manager: "MemoryManager", args: argparse.Namespace) -> int:
    """Show template details."""
    from whitemagic.templates import TemplateManager
    
    tmpl_mgr = TemplateManager()
    template = tmpl_mgr.get_template(args.name)
    
    if not template:
        print(f"Template not found: {args.name}", file=sys.stderr)
        return 1
    
    if getattr(args, 'json', False):
        print(json.dumps(template.model_dump(), indent=2))
    else:
        print(f"Template: {template.name}")
        print(f"Description: {template.description}")
        print(f"Memory Type: {template.memory_type}")
        print(f"\nRequired Tags: {', '.join(template.tags_required) if template.tags_required else 'None'}")
        print(f"Suggested Tags: {', '.join(template.tags_suggested) if template.tags_suggested else 'None'}")
        print(f"\nFields:")
        for field in template.fields:
            req_str = " (required)" if field.required else ""
            print(f"  - {field.name}: {field.type}{req_str}")
            if field.description:
                print(f"    {field.description}")
    
    return 0


def command_template_create(manager: "MemoryManager", args: argparse.Namespace) -> int:
    """Create memory from template."""
    from whitemagic.templates import TemplateManager
    
    tmpl_mgr = TemplateManager()
    template = tmpl_mgr.get_template(args.template)
    
    if not template:
        print(f"Template not found: {args.template}", file=sys.stderr)
        return 1
    
    console = Console()
    console.print(f"\n[bold cyan]Creating from template: {template.name}[/bold cyan]")
    console.print(f"{template.description}\n")
    
    # Collect fields
    fields = {}
    for field in template.fields:
        prompt_text = f"{field.name}"
        if field.required:
            prompt_text += " [required]"
        
        if field.type == "list":
            console.print(f"\n[yellow]{prompt_text}[/yellow] (one per line, empty to finish):")
            items = []
            while True:
                item = input("  - ")
                if not item:
                    break
                items.append(item)
            if items:
                fields[field.name] = items
        else:
            value = Prompt.ask(prompt_text, default=field.default or "")
            if value:
                fields[field.name] = value
    
    # Validate
    errors = template.validate_content(fields)
    if errors:
        console.print("\n[red]Errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        return 1
    
    # Generate
    content = template.generate_content(fields)
    title = args.title if hasattr(args, 'title') and args.title else Prompt.ask("\n[bold]Title[/bold]")
    
    tags = list(template.tags_required)
    if hasattr(args, 'tags') and args.tags:
        tags.extend(args.tags)
    
    # Create
    path = manager.create_memory(
        title=title,
        content=content,
        memory_type=template.memory_type,
        tags=tags
    )
    
    console.print(f"\n[green]✓[/green] Created: {path}")
    return 0
