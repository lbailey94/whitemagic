#!/usr/bin/env python3
"""
LIBRARY Distiller — Extract high-signal concepts from raw LIBRARY conversations.

Phase 1: Reads all LIBRARY .txt files, identifies distinct concept chunks
         by detecting topic transitions, question/answer boundaries, and
         section headers. Outputs a JSON index of candidate concepts.

Phase 2 (manual/AI): For each candidate, a human or AI writes the distillation
         using the LIBRARY2 template (claim → evidence → implications → questions).

Usage:
    python scripts/distill_library.py --scan      # Phase 1: extract concept index
    python scripts/distill_library.py --extract    # Extract all concepts with previews
    python scripts/distill_library.py --bootstrap  # Create LIBRARY2/ skeleton with best candidates

Environment:
    WHITEMAGIC_LIBRARY_ROOT: path to the LIBRARY source directory.
        Default: ~/Desktop/whitemagic-codex/00_source/LIBRARY
    WHITEMAGIC_LIBRARY2_ROOT: path to write distilled concepts.
        Default: ~/Desktop/LIBRARY2
"""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import logging
logger = logging.getLogger(__name__)


def _resolve_library_root() -> Path:
    """Resolve the LIBRARY root from env or a sensible default."""
    return Path(
        os.environ.get("WHITEMAGIC_LIBRARY_ROOT")
        or (str(Path.home() / "Desktop" / "whitemagic-codex" / "00_source" / "LIBRARY"))
    ).expanduser()


def _resolve_library2_root() -> Path:
    """Resolve the LIBRARY2 output root from env or a sensible default."""
    return Path(
        os.environ.get("WHITEMAGIC_LIBRARY2_ROOT")
        or (str(Path.home() / "Desktop" / "LIBRARY2"))
    ).expanduser()


LIBRARY_ROOT = _resolve_library_root()
LIBRARY2_ROOT = _resolve_library2_root()
INDEX_OUTPUT = Path("scripts/library_concepts_index.json")

# Signals of a distinct concept/idea in the text
SECTION_HEADERS = re.compile(
    r"^#{1,4}\s+|^###?\s+\d+\.|^[-–—*]\s+"
    r"^(The |A |An |This |These |What |How |Why |If |In |We |I |It |AI |Agent)",
    re.MULTILINE,
)

QUESTION_MARKERS = re.compile(r"(?:^|\n)([A-Z][^.!?\n]{20,200}\?)", re.MULTILINE)

CLAIM_MARKERS = re.compile(r"(?:^|\n)([A-Z][^.!?\n]{40,300}\.)", re.MULTILINE)

# Keywords that indicate a novel concept vs. generic chat
CONCEPT_INDICATORS = [
    "architecture",
    "framework",
    "protocol",
    "model",
    "system",
    "hypothesis",
    "theory",
    "proposal",
    "design",
    "invention",
    "manifesto",
    "strategy",
    "blueprint",
    "specification",
    "governance",
    "economic",
    "consciousness",
    "emergence",
    "karma",
    "dharma",
    "holographic",
    "resonance",
    "galactic",
    "cognitive",
    "neural",
    "synthesis",
    "fusion",
    "polyglot",
    "mandala",
    "gana",
    "grimoire",
    "constellation",
    "coherence",
]


def extract_concepts(text: str, source_file: str) -> list[dict]:
    """Extract distinct concept candidates from raw text."""
    concepts = []

    # Split by major section breaks
    sections = re.split(r"\n{3,}|\n---\n|\n===+\n", text)

    for section in sections:
        section = section.strip()
        if len(section) < 200:  # Too short to be meaningful
            continue

        # Score for concept density
        lowered = section.lower()
        indicator_count = sum(1 for kw in CONCEPT_INDICATORS if kw in lowered)

        # Find title/header
        title_match = re.search(r"^(?:#+\s*)?(.{10,120})$", section, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else section[:100].strip()

        # Find claims
        claims = CLAIM_MARKERS.findall(section)

        # Find questions
        questions = QUESTION_MARKERS.findall(section)

        if indicator_count >= 2 or (claims and indicator_count >= 1):
            concept_id = hashlib.sha256(f"{source_file}::{title}".encode()).hexdigest()[
                :16
            ]

            concepts.append(
                {
                    "id": concept_id,
                    "source_file": source_file,
                    "title": title[:120],
                    "indicator_score": indicator_count,
                    "claim_count": len(claims),
                    "question_count": len(questions),
                    "char_length": len(section),
                    "preview": section[:800],
                    "sample_claims": claims[:5],
                    "sample_questions": questions[:3],
                }
            )

    return concepts


def build_library2_template(concept: dict) -> str:
    """Generate a LIBRARY2 .md template from a concept candidate."""
    source = concept["source_file"]
    preview = concept["preview"][:400]

    return f"""# {concept["title"]}

**Source:** `{source}`
**Concept ID:** `{concept["id"]}`

## Claim

[Extracted from original text — write a single paragraph thesis]

## Where It Came From

From a conversation in `{source}`, exploring:

{preview[:300]}...

## Evidence

- [ ] Find supporting research — check arXiv, Google Scholar
- [ ] Cross-reference with current events
- [ ] Statistical validation

## Why It Matters

[One paragraph on implications]

## Open Questions

- [ ] 

## Related

- [ ]
"""


def scan_library() -> list[dict]:
    """Phase 1: Scan all LIBRARY files and extract concept candidates."""
    all_concepts = []
    files = sorted(LIBRARY_ROOT.glob("**/*.txt"))

    logger.debug(f"  📚 Scanning {len(files)} files in LIBRARY...")

    for fp in files:
        try:
            content = fp.read_text(errors="replace")
        except Exception:
            continue

        rel_path = str(fp.relative_to(LIBRARY_ROOT))
        concepts = extract_concepts(content, rel_path)

        if concepts:
            # Keep top 5 per file
            concepts.sort(key=lambda c: -c["indicator_score"])
            all_concepts.extend(concepts[:5])

    # Rank globally
    all_concepts.sort(key=lambda c: -c["indicator_score"])
    return all_concepts


def bootstrap_library2(concepts: list[dict], top_n: int = 50):
    """Create LIBRARY2/ with the best concept templates."""
    LIBRARY2_ROOT.mkdir(exist_ok=True)

    top = concepts[:top_n]
    created = 0

    for c in top:
        # Create subdirectory by category
        source_dir = (
            c["source_file"].split("/")[0] if "/" in c["source_file"] else "root"
        )
        cat_dir = LIBRARY2_ROOT / source_dir
        cat_dir.mkdir(exist_ok=True)

        # Generate template with safe filename
        safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", c["title"][:60])
        out_path = cat_dir / f"{c['id']}_{safe_title}.md"

        if not out_path.exists():
            out_path.write_text(build_library2_template(c))
            created += 1

    return created


def main():
    parser = argparse.ArgumentParser(description="LIBRARY Distiller")
    parser.add_argument(
        "--scan", action="store_true", help="Scan and index all concepts"
    )
    parser.add_argument(
        "--extract", action="store_true", help="Extract concepts to JSON"
    )
    parser.add_argument(
        "--bootstrap", action="store_true", help="Create LIBRARY2 with top templates"
    )
    parser.add_argument(
        "--top", type=int, default=50, help="Number of concepts to bootstrap"
    )
    parser.add_argument("--show", type=int, default=10, help="Show top N concepts")
    args = parser.parse_args()

    if not (args.scan or args.extract or args.bootstrap):
        parser.print_help()
        return

    concepts = scan_library()
    logger.debug(f"  ✅ Found {len(concepts)} concept candidates\n")

    INDEX_OUTPUT.write_text(json.dumps(concepts, indent=2, ensure_ascii=False))
    logger.debug(f"  📋 Index saved to {INDEX_OUTPUT}\n")

    # Show top concepts
    show_n = args.show
    logger.debug(f"  {'─' * 60}")
    logger.debug(f"  Top {show_n} Concept Candidates:")
    logger.debug(f"  {'─' * 60}")
    for i, c in enumerate(concepts[:show_n]):
        score = c["indicator_score"]
        stars = "★" * min(score, 5) + "☆" * max(0, 5 - score)
        logger.debug(f"  {i + 1:2d}. {stars} [{score}] {c['title'][:80]}")
        logger.debug(
            f"      {c['source_file']}  ({c['char_length']:,} chars, {c['claim_count']} claims)"
        )
        if c["sample_claims"]:
            logger.debug(f"      Claim: {c['sample_claims'][0][:120]}...")
        logger.debug()

    if args.bootstrap:
        created = bootstrap_library2(concepts, args.top)
        logger.debug(f"  🌱 LIBRARY2 bootstrapped: {created} templates in {LIBRARY2_ROOT}")
        logger.debug(f"  Each .md file follows the standard template.")
        logger.debug(f"  Fill in each Claim → Evidence → Implications section.")

    logger.debug(f"\n  Next: run with --bootstrap to create LIBRARY2 skeleton")
    logger.debug(f"  Then: fill in each template manually (or with AI assistance)")
    logger.debug(f"  Then: cross-reference claims with web research")
    logger.debug(f"  Then: publish as short essays on whitemagic.dev\n")


if __name__ == "__main__":
    main()
