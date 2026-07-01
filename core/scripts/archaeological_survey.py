#!/usr/bin/env python3
"""
WhiteMagic Holographic Deep Scan - Extended Chariot Engine
Recursively scans ALL discovered auxiliary databases for patterns.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Whitemagic imports
from whitemagic.archaeology.dig import ChariotArchaeologist, Grimoire, Ganas
from whitemagic.config.paths import ARCHIVE_DIR


def get_all_db_files(root_dir: Path) -> list[Path]:
    return list(root_dir.rglob("*.db"))


def survey_database(archaeologist: ChariotArchaeologist, db_path: Path):
    print(f"\n[Scanning DB] {db_path.name} ({db_path.parent.name})")
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Determine table name (memories is standard, but some might be cognitive_episodes)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]

        target_table = None
        if "memories" in tables:
            target_table = "memories"
        elif "cognitive_episodes" in tables:
            target_table = "cognitive_episodes"

        if not target_table:
            print(f"  ⏭️ No standard memory table found in {tables}")
            conn.close()
            return

        cursor.execute(f"PRAGMA table_info({target_table})")
        columns = [r["name"] for r in cursor.fetchall()]

        query_cols = ["id", "content"]
        if "metadata" in columns:
            query_cols.append("metadata")
        if "title" in columns:
            query_cols.append("title")
        if "galactic_distance" in columns:
            query_cols.append("galactic_distance")
        if "neuro_score" in columns:
            query_cols.append("neuro_score")

        cursor.execute(f"SELECT {', '.join(query_cols)} FROM {target_table}")
        rows = cursor.fetchall()

        print(f"  🔍 Processing {len(rows)} records in '{target_table}'...")
        found_count = 0
        for row in rows:
            mid = row["id"]
            content = row["content"] or ""
            metadata_str = row["metadata"] if "metadata" in columns else "{}"
            if not metadata_str:
                metadata_str = "{}"
            title = row["title"] if "title" in columns else ""
            if not title:
                title = ""

            # Fuzzy match content and metadata
            combined_text = f"{title} {content} {metadata_str}".lower()

            matches = []
            if "wxyz" in combined_text:
                matches.append("Holographic_WXYZ")
            if "synchronicity" in combined_text:
                matches.append("Synch_Pattern")
            if "dharma" in combined_text:
                matches.append("Legacy_Dharma")
            if "protocol" in combined_text:
                matches.append("Protocol_Ref")

            # Use Chariot's Grimoire/Ganas for deep alignment
            chapters = Grimoire.identify(combined_text, title or "")
            gana = Ganas.identify(combined_text, title or "")

            # Filtering and Scoring
            score = 0
            if chapters:
                score = chapters[0]["score"]

            # Boost score if metadata contains coords
            try:
                meta_obj = json.loads(metadata_str)
                if any(k in meta_obj for k in ["x", "y", "z", "w", "gana"]):
                    score += 2
                    matches.append("Structured_Meta")
            except Exception:
                pass

            if matches or score >= 2 or gana:
                finding = {
                    "source": f"db:{db_path.name}",
                    "id": mid,
                    "title": title[:100],
                    "matches": list(set(matches)),
                    "score": score,
                    "anthropology": {
                        "chapters": chapters,
                        "gana": gana,
                    },
                }
                archaeologist.write_finding(finding)
                found_count += 1

        print(f"  💎 Found {found_count} artifacts.")
        conn.close()
    except Exception as e:
        print(f"  ❌ Error scanning {db_path.name}: {e}")


def generate_expanded_recovery_report(report_file: Path, output_md: Path):
    print(f"\n[Finalizing] Generating Expanded Recovery Report: {output_md}")
    findings = []
    if not report_file.exists():
        return

    with open(report_file, "r") as f:
        for line in f:
            try:
                findings.append(json.loads(line))
            except Exception:
                continue

    # Sort by score or significance
    findings.sort(key=lambda x: x.get("score", 0), reverse=True)

    report = [
        "# 🏺 WhiteMagic Holographic Recovery Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n## Summary",
        f"- **Total Databases Scanned**: Multiple",
        f"- **Artifacts Found**: {len([f for f in findings if 'meta' not in f])}",
        "\n## 🌟 High-Confidence Breakthroughs",
        "| Source | Name/ID | Score | Patterns | Gana | Chapter |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for f in findings[:50]:  # Top 50
        if "meta" in f:
            continue
        source = f.get("source", "file")
        name = f.get("title") or f.get("id") or "Unknown"
        score = f.get("score", 0)
        matches = ", ".join(f.get("matches", []))[:30]
        gana = f.get("anthropology", {}).get("gana", "N/A")
        chapters = f.get("anthropology", {}).get("chapters", [])
        top_chap = f"{chapters[0]['title']}" if chapters else "N/A"

        report.append(
            f"| {source} | {name[:40]} | {score} | {matches} | {gana} | {top_chap} |"
        )

    with open(output_md, "w") as f:
        f.write("\n".join(report))


if __name__ == "__main__":
    aux_root = Path("/media/lucas/SD_CARD/WHITEMAGIC/auxiliary/home_backup/memory")
    output_dir = REPO_ROOT / "scripts/archaeology_results"

    agent = ChariotArchaeologist(str(ARCHIVE_DIR), str(output_dir))

    db_files = get_all_db_files(aux_root)
    print(f"Found {len(db_files)} databases in auxiliary archive.")

    for db in db_files:
        survey_database(agent, db)

    generate_expanded_recovery_report(
        agent.report_file, output_dir / "HOLOGRAPHIC_REPORT.md"
    )
