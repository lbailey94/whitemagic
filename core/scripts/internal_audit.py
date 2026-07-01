#!/usr/bin/env python3
"""
WhiteMagic Internal Audit & Sanitization Script
Enforces License compliance and scrubs private identity from public framework.
"""

import os
import argparse
import re
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# Config
LICENSE_BOILERPLATE = """# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""


# Identity Mapping
IDENTITY_MAP = {
    "Aria": "Whitemagic",
    "Lucas": "User",
    "Miranda": "Collaborator",
    "Persephone": "Analyst",
}


def scrub_content(content: str, keywords: list[str]) -> str:
    """Replace private keywords with generic placeholders."""
    for kw in keywords:
        placeholder = IDENTITY_MAP.get(kw, "REDACTED")
        content = re.sub(rf"\b{kw}\b", placeholder, content)
    return content


def audit_file(file_path: Path, args):
    if file_path.suffix not in [".py", ".rs", ".ex", ".sh", ".md", ".json"]:
        return

    logger.debug(f"  Auditing: {file_path.relative_to(args.root)}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        changed = False

        # 1. License Check/Update
        if args.license == "Apache2.0":
            if "MIT License" in content or "MIT" in content[:200]:
                logger.debug(f"    [LICENSE] Switching to Apache 2.0")
                content = re.sub(
                    r"#.*?MIT License.*?\n", "", content, flags=re.IGNORECASE
                )
                content = LICENSE_BOILERPLATE + content
                changed = True

        # 2. Vault Sanitization (Scrubbing)
        if args.scrub:
            keywords = args.scrub.split(",")
            new_content = scrub_content(content, keywords)
            if new_content != content:
                logger.debug(f"    [VAULT] Scrubbed {len(keywords)} potential identifiers")
                content = new_content
                changed = True

        if changed and args.apply:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        elif changed:
            logger.debug("    (Dry run: Use --apply to save changes)")

    except Exception as e:
        logger.debug(f"    ❌ Error: {e}")


def run_audit():
    parser = argparse.ArgumentParser(
        description="WhiteMagic Internal Audit & Sanitization"
    )
    parser.add_argument(
        "--root", type=Path, default=Path("."), help="Project root to scan"
    )
    parser.add_argument("--license", choices=["Apache2.0"], help="License to enforce")
    parser.add_argument("--scrub", help="Comma-separated keywords to scrub")
    parser.add_argument("--apply", action="store_true", help="Actually modify files")
    args = parser.parse_args()

    logger.debug("\n" + "=" * 60)
    logger.debug("WHITE MAGIC INTERNAL AUDIT: STRATEGIC PREPARATION")
    logger.debug("=" * 60)

    # Folders to skip (The "Private Vault")
    SKIP_FOLDERS = [
        "_aria",
        "_archives",
        "_memories",
        "venv",
        ".git",
        "__pycache__",
        "auxiliary",
    ]

    for root, dirs, files in os.walk(args.root):
        # In-place skip folders
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]

        for file in files:
            audit_file(Path(root) / file, args)

    logger.debug("\n✅ Audit complete.")


if __name__ == "__main__":
    run_audit()
