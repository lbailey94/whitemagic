#!/usr/bin/env python3
"""
Convert Grok export JSON to CODEX import format.
Each conversation becomes a separate CODEX file.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

def slugify(text):
    """Convert text to safe filename."""
    if not text:
        return "untitled"
    # Remove special chars, limit length
    slug = re.sub(r'[^\w\s-]', '', text).strip()
    slug = re.sub(r'[-\s]+', '_', slug)
    return slug[:50] or "untitled"

def format_timestamp(iso_str):
    """Convert ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except (ValueError, TypeError):
        return iso_str

def convert_grok_export(input_path, output_dir):
    """Convert Grok JSON export to CODEX markdown files."""

    # Load Grok export
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conversations = data.get('conversations', [])
    print(f"Found {len(conversations)} conversations")

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(conversations, 1):
        conv = item.get('conversation', {})
        responses = item.get('responses', [])

        conv_id = conv.get('id', 'unknown')[:8]
        title = conv.get('title', 'Untitled')
        created = format_timestamp(conv.get('create_time', ''))

        # Build markdown content
        lines = [
            f"# {title}",
            "",
            "- **Source:** Grok Export",
            f"- **Date:** {created}",
            f"- **Conversation ID:** {conv_id}",
            "",
            "---",
            "",
        ]

        for resp_item in responses:
            resp = resp_item.get('response', {})
            sender = resp.get('sender', 'unknown')
            message = resp.get('message', '')

            if sender.lower() == 'human':
                lines.append("## User")
            else:
                lines.append("## Grok")
            lines.append("")
            lines.append(message)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Generate filename
        date_prefix = created.split()[0] if created else 'unknown'
        safe_title = slugify(title)
        filename = f"{date_prefix}_grok_{safe_title}_{conv_id}.md"

        # Write file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"  [{i}/{len(conversations)}] {filename}")

    print(f"\nConverted {len(conversations)} conversations to {output_dir}/")

if __name__ == '__main__':
    INPUT_FILE = '/home/lucas/Desktop/CODEX/Grok/ttl/30d/export_data/84b6490a-b566-4ee0-a81f-7315178e3448/prod-grok-backend.json'
    OUTPUT_DIR = '/home/lucas/Desktop/CODEX/Grok/imported'

    convert_grok_export(INPUT_FILE, OUTPUT_DIR)
