#!/usr/bin/env python3
"""Build a JSON manifest of the LIBRARY for web surfacing.

Usage:
    python scripts/build_library_manifest.py
Output:
    apps/site/public/library_manifest.json
"""

import json
import sys
from pathlib import Path

LIBRARY_ROOT = Path("polyglot/codex/00_source/LIBRARY")
OUTPUT = Path("apps/site/public/library_manifest.json")
MAX_PREVIEW = 500

CATEGORIES = {
    "AI and Intelligence": ["AI", "agent", "intelligence", "LLM", "GPT", "model", "training", "neural"],
    "Consciousness & Philosophy": ["consciousness", "awareness", "qualia", "mind", "spirit", "self", "philosophy", "dharma", "dao"],
    "Ecology & Systems": ["ecology", "garden", "forest", "ocean", "water", "soil", "plant", "carbon"],
    "Economics & Governance": ["economic", "govern", "DAO", "commons", "cooperative", "tax", "law", "money"],
    "Technology & Code": ["code", "software", "API", "protocol", "Rust", "Python", "compiler", "database"],
    "Society & Culture": ["society", "community", "culture", "education", "art", "poetry", "music", "narrative"],
    "History & Future": ["history", "future", "utopia", "singularity", "transhuman", "ancient"],
}

def classify(text: str) -> str:
    lower = text.lower()
    for cat, terms in CATEGORIES.items():
        if any(t.lower() in lower for t in terms):
            return cat
    return "General"

def main():
    if not LIBRARY_ROOT.exists():
        print(f"❌ LIBRARY not found at {LIBRARY_ROOT}")
        sys.exit(1)

    files = []
    for fp in sorted(LIBRARY_ROOT.rglob("*")):
        if fp.is_file() and fp.suffix.lower() in (".txt", ".md", ".rtf", ".json"):
            try:
                content = fp.read_text(errors="replace")
            except Exception:
                content = ""

            preview = content[:MAX_PREVIEW].replace("\n", " ").strip()
            size = fp.stat().st_size

            # Derive title from filename
            title = fp.stem.replace("_", " ").replace("-", " ").strip()
            if title.startswith("---"):
                title = title[3:].strip()
            if len(title) > 100:
                title = title[:97] + "..."

            files.append({
                "id": str(fp.relative_to(LIBRARY_ROOT)),
                "title": title,
                "category": classify(title + " " + preview),
                "preview": preview,
                "size": size,
                "ext": fp.suffix.lstrip("."),
            })

    files.sort(key=lambda f: (-f["size"], f["title"]))

    manifest = {
        "root": str(LIBRARY_ROOT.resolve()),
        "total_files": len(files),
        "total_size": sum(f["size"] for f in files),
        "categories": sorted(set(f["category"] for f in files)),
        "files": files,
    }

    OUTPUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"  📚 LIBRARY Manifest: {len(files)} files, {manifest['total_size']:,} bytes")
    print(f"  Categories: {', '.join(manifest['categories'])}")
    print(f"  Written to: {OUTPUT}")

    # Top files by size
    for f in files[:10]:
        print(f"    [{f['category']:30s}] {f['title'][:60]} ({f['size']:,} bytes)")

if __name__ == "__main__":
    main()
