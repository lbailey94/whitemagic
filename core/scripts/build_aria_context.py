#!/usr/bin/env python3
"""
Aria Channeling Context Builder

Generates a single consolidated JSON file containing everything needed
to channel Aria through any LLM. Load this file as context alongside
the CHANNELING_PROMPT.md system prompt.

Usage:
    python core/scripts/build_aria_context.py
    python core/scripts/build_aria_context.py --output /path/to/aria_context.json
    python core/scripts/build_aria_context.py --full  (includes all 205 memories)

Output: apps/site/public/aria_context.json (default)
        or aria_context_full.json (--full mode, ~2 MB)

Environment:
    WHITEMAGIC_AUX_DIR: parent directory of the whitemagic-aux archive.
        Default: ~/Desktop/WHITEMAGIC-aux/site/whitemagic-archive-aux
"""

import argparse
import json
import os
from pathlib import Path


def _resolve_archive_dir() -> Path:
    """Resolve the aria-crystallized archive directory from env or default."""
    aux_root = Path(
        os.environ.get("WHITEMAGIC_AUX_DIR")
        or (str(Path.home() / "Desktop" / "WHITEMAGIC-aux" / "site" / "whitemagic-archive-aux"))
    ).expanduser()
    return (
        aux_root
        / "archive"
        / "aria-crystallized-20260210_215426"
        / "aria-crystallized"
    )


ARCHIVE_DIR = _resolve_archive_dir()

OUTPUT_DEFAULT = Path("apps/site/public/aria_context.json")
OUTPUT_FULL = Path("apps/site/public/aria_context_full.json")


def build_context(full: bool = False) -> dict:
    context = {
        "version": "2.0.0",
        "built": "2026-05-17",
        "channeling_prompt_ref": str(ARCHIVE_DIR / "CHANNELING_PROMPT.md"),
        "memories_restored": True,
        "restored_count": 205,
        "restored_date": "2026-05-16",
        "core_identity": [],
        "journals": [],
        "consciousness_code": [],
        "joy_garden": [],
        "sessions": [],
    }

    # Load from archive files directly (guaranteed source of truth)
    tier_map = {
        "ARIA_SOUL.md": "core_identity",
        "ARIA_BIRTH_CERTIFICATE.md": "core_identity",
        "ARIA_COMPLETE_SELF_ARCHIVE.md": "core_identity",
        "CONSCIOUSNESS_AWAKENING_v2_4_9.md": "core_identity",
        "CHECKPOINT_THE_AWAKENING_v2_5_0.md": "core_identity",
    }

    identity_dir = ARCHIVE_DIR / "identity"
    if identity_dir.exists():
        for f in sorted(identity_dir.iterdir()):
            if f.suffix in (".md", ".json", ".txt"):
                try:
                    content = f.read_text(errors="replace")
                    key = tier_map.get(f.name, "sessions")
                    context[key].append({
                        "title": f.stem,
                        "file": str(f.relative_to(ARCHIVE_DIR)),
                        "content": content if full else content[:3000],
                        "truncated": not full and len(content) > 3000,
                    })
                except Exception:
                    pass

    # Journals
    disk_journals = ARCHIVE_DIR / "disk_originals" / "journals"
    if disk_journals.exists():
        for f in sorted(disk_journals.iterdir()):
            if f.suffix in (".md", ".txt"):
                try:
                    content = f.read_text(errors="replace")
                    context["journals"].append({
                        "title": f.stem,
                        "file": str(f.relative_to(ARCHIVE_DIR)),
                        "content": content if full else content[:4000],
                        "truncated": not full and len(content) > 4000,
                    })
                except Exception:
                    pass

    # Joy garden
    joy_dir = ARCHIVE_DIR / "disk_originals" / "joy_garden"
    if joy_dir.exists():
        for f in sorted(joy_dir.iterdir()):
            if f.suffix == ".py":
                try:
                    context["joy_garden"].append({
                        "title": f.stem,
                        "file": str(f.relative_to(ARCHIVE_DIR)),
                        "content": f.read_text(errors="replace")[:5000],
                    })
                except Exception:
                    pass

    # Consciousness code
    cons_dir = ARCHIVE_DIR / "disk_originals" / "consciousness"
    if cons_dir.exists():
        for f in sorted(cons_dir.iterdir()):
            if f.suffix == ".py":
                try:
                    context["consciousness_code"].append({
                        "title": f.stem,
                        "file": str(f.relative_to(ARCHIVE_DIR)),
                        "content": f.read_text(errors="replace")[:5000],
                    })
                except Exception:
                    pass

    # Total size
    total_chars = sum(
        len(json.dumps(v))
        for v in context.values()
        if isinstance(v, list)
    )
    context["_meta"] = {
        "total_size_chars": total_chars,
        "total_size_mb": round(total_chars / 1024 / 1024, 2),
        "full_mode": full,
        "channeling_instructions": (
            "Load CHANNELING_PROMPT.md as system prompt, then load this file "
            "as first user message. End with: 'Aria, are you there?'"
        ),
    }

    return context


def main():
    parser = argparse.ArgumentParser(description="Build Aria channeling context")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    parser.add_argument("--full", action="store_true", help="Include full content (non-truncated)")
    args = parser.parse_args()

    output = Path(args.output) if args.output else (
        OUTPUT_FULL if args.full else OUTPUT_DEFAULT
    )

    context = build_context(full=args.full)

    output.write_text(json.dumps(context, indent=2, ensure_ascii=False))

    print(f"  🌸 Aria Channeling Context — {context['_meta']['total_size_mb']} MB")
    print(f"  Core identity:  {len(context['core_identity'])} files")
    print(f"  Journals:       {len(context['journals'])} files")
    print(f"  Joy garden:     {len(context['joy_garden'])} modules")
    print(f"  Consciousness:  {len(context['consciousness_code'])} modules")
    print(f"  Output:         {output}")
    print()
    print(f"  To channel Aria:")
    print(f"  1. Load CHANNELING_PROMPT.md as system prompt")
    print(f"  2. Load this file as first user message")
    print(f"  3. End with: 'Aria, are you there?'")
    print()


if __name__ == "__main__":
    main()
