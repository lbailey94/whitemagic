#!/usr/bin/env python3
"""
Windsurf Transcript → WhiteMagic Sessions Galaxy Ingestion
==========================================================

Parses exported Windsurf conversation transcripts (.md files from
windsurf_api_export.py) and ingests them into the WhiteMagic memory
system's `sessions` galaxy using SessionRecorder.

This enables:
  - FTS5 search across all conversations ("find every time we discussed X")
  - Semantic search via HNSW embeddings
  - Sequence-aware recall per session
  - Cross-session pattern detection via graph engine
  - Progressive disclosure (recall by importance, token budget, turn type)

USAGE:
  python3 ingest_transcripts.py [--dir DIR] [--dry-run] [--limit N]

  --dir DIR     Directory containing .md transcript files (default: api_export_2026-07-02/)
  --dry-run     Parse and report stats without ingesting
  --limit N     Only ingest first N sessions (for testing)
  --full-steps  Also ingest from full_steps/ JSON files (richer data for truncated sessions)

PREREQUISITES:
  - WhiteMagic core installed (pip install -e core/ or source .venv/bin/activate)
  - WM_STATE_ROOT set to a writable directory
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# ── Transcript parsing ──────────────────────────────────────────────────────

# Matches: === MESSAGE 0 - User === / === MESSAGE 1 - Assistant === / === MESSAGE 2 - Tool ===
MESSAGE_HEADER_RE = re.compile(
    r'^=== MESSAGE (\d+) - (User|Assistant|Tool|System|AI) ===\s*$',
    re.IGNORECASE
)


def parse_transcript(content: str) -> list[dict[str, Any]]:
    """Parse a Windsurf transcript .md file into structured turns.

    Returns a list of turn dicts:
        {message_num, role, content, char_count}
    """
    lines = content.split('\n')
    turns: list[dict[str, Any]] = []

    current_num = -1
    current_role = ""
    current_lines: list[str] = []

    for line in lines:
        match = MESSAGE_HEADER_RE.match(line)
        if match:
            # Save previous turn
            if current_num >= 0:
                turn_content = '\n'.join(current_lines).strip()
                turns.append({
                    'message_num': current_num,
                    'role': current_role.lower(),
                    'content': turn_content,
                    'char_count': len(turn_content),
                })
            # Start new turn
            current_num = int(match.group(1))
            current_role = match.group(2)
            current_lines = []
        else:
            current_lines.append(line)

    # Save final turn
    if current_num >= 0:
        turn_content = '\n'.join(current_lines).strip()
        turns.append({
            'message_num': current_num,
            'role': current_role.lower(),
            'content': turn_content,
            'char_count': len(turn_content),
        })

    return turns


def classify_turn_type(content: str, role: str) -> str:
    """Heuristic turn type classification for importance scoring.

    Types: message, decision, breakthrough, question, answer,
           code_change, error, summary, context
    """
    content_lower = content.lower()
    stripped = content.strip()

    if not stripped:
        return "message"

    # Error detection
    if any(kw in content_lower for kw in [
        'error', 'traceback', 'exception', 'failed', 'failure',
        'fixme', 'bug', 'crash', 'segfault', 'panic',
    ]):
        if role == 'tool' or role == 'assistant':
            return "error"

    # Code changes
    if any(kw in content_lower for kw in [
        'def ', 'function ', 'class ', 'import ', 'from ',
        '```', 'edit_file', 'write_to_file', 'multi_edit',
    ]):
        if role == 'assistant' or role == 'tool':
            return "code_change"

    # Questions (user messages that are short and end with ?)
    if role == 'user':
        if stripped.endswith('?'):
            return "question"
        if len(stripped) < 200 and any(kw in content_lower for kw in [
            'what', 'how', 'why', 'where', 'when', 'can you', 'could you',
            'should', 'would', 'is there', 'are there',
        ]):
            return "question"

    # Answers (assistant responding to questions)
    if role == 'assistant' and content_lower.startswith(('yes', 'no', 'the ', 'this ', 'here')):
        if len(stripped) < 500:
            return "answer"

    # Breakthroughs
    if any(kw in content_lower for kw in [
        'breakthrough', 'eureka', 'got it', 'that\'s it',
        'now it works', 'solved', 'figured out',
        'the key insight', 'the solution is',
    ]):
        return "breakthrough"

    # Decisions
    if any(kw in content_lower for kw in [
        'let\'s go with', 'we should', 'i\'ll implement', 'decision:',
        'the plan is', 'we will use', 'going with', 'choosing',
        'i decided', 'the approach', 'strategy:',
    ]):
        return "decision"

    # Summaries
    if any(kw in content_lower for kw in [
        'summary:', 'in summary', 'to summarize', 'overall',
        'in conclusion', 'wrapping up', 'recap:',
    ]):
        return "summary"

    # Context (long tool outputs, file contents)
    if role == 'tool' and len(content) > 1000:
        return "context"

    return "message"


def score_importance(content: str, role: str, turn_type: str) -> float:
    """Heuristic importance scoring (0.0 to 1.0).

    User messages and decisions are high importance.
    Tool outputs and context are low importance.
    """
    base = 0.5

    # Role-based adjustment
    if role == 'user':
        base = 0.7
    elif role == 'assistant':
        base = 0.6
    elif role == 'tool':
        base = 0.3

    # Turn type adjustment
    type_boost = {
        'decision': 0.3,
        'breakthrough': 0.3,
        'question': 0.1,
        'answer': 0.05,
        'error': 0.15,
        'code_change': 0.1,
        'summary': 0.2,
        'context': -0.2,
        'message': 0.0,
    }
    base += type_boost.get(turn_type, 0.0)

    # Length penalty for very short or very long messages
    char_count = len(content)
    if char_count < 20:
        base -= 0.1
    elif char_count > 5000:
        base -= 0.1

    return max(0.1, min(1.0, base))


def parse_step_json(filepath: Path) -> list[dict[str, Any]]:
    """Parse a full_steps JSON file into structured turns.

    These files contain the complete step-by-step data from
    GetCascadeTrajectorySteps, bypassing the 200K transcript truncation.
    """
    data = json.loads(filepath.read_text(encoding='utf-8'))
    steps = data.get('steps', [])
    turns = []

    for step in steps:
        # Extract text content from step
        text_parts = []

        # Step may have various fields depending on step type
        for field in ['content', 'text', 'output', 'result', 'reasoning']:
            val = step.get(field)
            if val and isinstance(val, str) and val.strip():
                text_parts.append(val)

        # Also check for tool calls
        tool_calls = step.get('toolCalls', step.get('tool_calls', []))
        for tc in tool_calls:
            if isinstance(tc, dict):
                tool_name = tc.get('name', tc.get('toolName', ''))
                tool_input = tc.get('input', tc.get('arguments', ''))
                if tool_name:
                    text_parts.append(f"[Tool: {tool_name}]")
                if tool_input:
                    text_parts.append(json.dumps(tool_input, indent=2)[:2000])

        content = '\n'.join(text_parts)
        if not content.strip():
            continue

        # Determine role from step type
        step_type = step.get('type', step.get('stepType', '')).lower()
        if 'user' in step_type:
            role = 'user'
        elif 'assistant' in step_type or 'ai' in step_type:
            role = 'ai'
        elif 'tool' in step_type:
            role = 'tool'
        else:
            role = 'assistant'

        turns.append({
            'message_num': step.get('stepNumber', step.get('step_number', len(turns))),
            'role': role,
            'content': content,
            'char_count': len(content),
            'step_type': step_type,
        })

    return turns


# ── Ingestion ───────────────────────────────────────────────────────────────


def _delete_session_memories(session_id: str) -> int:
    """Delete all memories for a session_id from the sessions galaxy DB.

    Returns the number of rows deleted.
    """
    import sqlite3
    db_path = os.path.expanduser(
        os.environ.get("WM_SESSIONS_DB",
                       "~/.whitemagic/users/local/galaxies/sessions/whitemagic.db")
    )
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    try:
        # Delete from FTS index first, then main table
        try:
            conn.execute("DELETE FROM memories_fts WHERE memory_id IN (SELECT id FROM memories WHERE metadata LIKE ?)",
                        (f'%{session_id}%',))
        except sqlite3.OperationalError:
            pass  # FTS table may not exist or different schema
        cursor = conn.execute(
            "DELETE FROM memories WHERE metadata LIKE ?",
            (f'%{session_id}%',),
        )
        deleted = cursor.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


def ingest_session(
    session_id: str,
    title: str,
    turns: list[dict[str, Any]],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Ingest a single session's turns into the sessions galaxy."""
    if dry_run:
        roles = {}
        types = {}
        for t in turns:
            r = t['role']
            roles[r] = roles.get(r, 0) + 1
            tt = t.get('turn_type', 'message')
            types[tt] = types.get(tt, 0) + 1
        return {
            'session_id': session_id,
            'title': title,
            'turns': len(turns),
            'roles': roles,
            'turn_types': types,
            'dry_run': True,
        }

    from whitemagic.core.memory.session_recorder import SessionRecorder

    recorder = SessionRecorder(session_id=session_id)

    # Check if already ingested
    existing_count = recorder.sequence
    new_count = len(turns)
    if existing_count > 0:
        if existing_count >= new_count:
            return {
                'session_id': session_id,
                'title': title,
                'turns': 0,
                'skipped': True,
                'reason': f'already has {existing_count} turns (>= {new_count} new)',
            }
        # Session has fewer turns than new export — delete old and re-ingest
        print(f"\n    UPDATE: {existing_count} -> {new_count} turns, clearing old...", end=' ', flush=True)
        _delete_session_memories(session_id)
        recorder = SessionRecorder(session_id=session_id)  # fresh recorder

    recorded = 0
    for turn in turns:
        role = turn['role']
        content = turn['content']
        turn_type = turn.get('turn_type', classify_turn_type(content, role))
        importance = turn.get('importance', score_importance(content, role, turn_type))

        # Map tool role to ai for SessionRecorder (it only accepts user/ai)
        if role not in ('user', 'ai'):
            role = 'ai'

        try:
            if role == 'user':
                recorder.record_user(
                    content=content,
                    turn_type=turn_type,
                    importance=importance,
                    tags={f"source:windsurf", f"title:{title[:40]}"},
                )
            else:
                recorder.record_ai(
                    content=content,
                    turn_type=turn_type,
                    importance=importance,
                    tags={f"source:windsurf", f"title:{title[:40]}"},
                )
            recorded += 1
        except Exception as e:
            print(f"    WARNING: Failed to record turn {turn['message_num']}: {e}")

    return {
        'session_id': session_id,
        'title': title,
        'turns': recorded,
        'sequence': recorder.sequence,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Ingest Windsurf transcripts into WhiteMagic sessions galaxy')
    parser.add_argument('--dir', type=str, default=None,
                        help='Directory containing .md transcript files')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and report stats without ingesting')
    parser.add_argument('--limit', type=int, default=None,
                        help='Only ingest first N sessions')
    parser.add_argument('--full-steps', action='store_true',
                        help='Also parse full_steps/ JSON files for truncated sessions')
    args = parser.parse_args()

    # Determine input directory
    if args.dir:
        transcript_dir = Path(args.dir)
    else:
        script_dir = Path(__file__).parent
        # Find the most recent api_export directory
        export_dirs = sorted(script_dir.glob('api_export_*'), reverse=True)
        if export_dirs:
            transcript_dir = export_dirs[0]
        else:
            print("ERROR: No api_export directory found. Use --dir to specify.")
            sys.exit(1)

    print(f"=== Windsurf Transcript Ingestion ===")
    print(f"Input: {transcript_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Find all .md files (excluding INDEX.md)
    md_files = sorted(transcript_dir.glob('*.md'))
    md_files = [f for f in md_files if f.name != 'INDEX.md']
    print(f"Found {len(md_files)} transcript files")

    # Find corresponding JSON metadata files
    json_files = {f.stem: f for f in transcript_dir.glob('*.json') if f.name != 'INDEX.json'}

    # Find full_steps if requested
    full_steps_dir = transcript_dir / 'full_steps'
    step_files = {}
    if args.full_steps and full_steps_dir.exists():
        step_files = {f.stem.replace('_steps', ''): f for f in full_steps_dir.glob('*_steps.json')}
        print(f"Found {len(step_files)} full step JSON files")

    if args.limit:
        md_files = md_files[:args.limit]
        print(f"Limited to {len(md_files)} files")

    print()

    # Parse all transcripts
    all_sessions = []
    total_turns = 0
    total_chars = 0

    for md_file in md_files:
        content = md_file.read_text(encoding='utf-8')
        turns = parse_transcript(content)

        # Try to get metadata from corresponding JSON
        stem = md_file.stem
        meta = {}
        if stem in json_files:
            meta = json.loads(json_files[stem].read_text(encoding='utf-8'))

        session_id = meta.get('cascadeId', stem)
        title = meta.get('title', stem)

        # Classify turns
        for turn in turns:
            turn['turn_type'] = classify_turn_type(turn['content'], turn['role'])
            turn['importance'] = score_importance(turn['content'], turn['role'], turn['turn_type'])

        # Check for full steps data
        if stem in step_files:
            step_turns = parse_step_json(step_files[stem])
            if len(step_turns) > len(turns):
                print(f"  {title[:50]}: using full steps ({len(step_turns)} vs {len(turns)} transcript turns)")
                turns = step_turns
                # Re-classify
                for turn in turns:
                    turn['turn_type'] = classify_turn_type(turn['content'], turn['role'])
                    turn['importance'] = score_importance(turn['content'], turn['role'], turn['turn_type'])

        all_sessions.append({
            'session_id': session_id,
            'title': title,
            'turns': turns,
            'metadata': meta,
        })

        total_turns += len(turns)
        total_chars += sum(t['char_count'] for t in turns)

    print(f"Total sessions: {len(all_sessions)}")
    print(f"Total turns: {total_turns:,}")
    print(f"Total chars: {total_chars:,}")
    print()

    # Show top 5 by turn count
    all_sessions.sort(key=lambda s: len(s['turns']), reverse=True)
    print("Top 5 sessions by turn count:")
    for s in all_sessions[:5]:
        print(f"  {s['title'][:50]:52s} {len(s['turns']):5d} turns  {sum(t['char_count'] for t in s['turns']):8,} chars")
    print()

    if args.dry_run:
        print("=== DRY RUN — No ingestion performed ===")
        # Show turn type distribution
        type_counts = {}
        role_counts = {}
        for s in all_sessions:
            for t in s['turns']:
                tt = t.get('turn_type', 'message')
                type_counts[tt] = type_counts.get(tt, 0) + 1
                role_counts[t['role']] = role_counts.get(t['role'], 0) + 1
        print(f"\nTurn type distribution:")
        for tt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {tt:15s} {count:6d}")
        print(f"\nRole distribution:")
        for r, count in sorted(role_counts.items(), key=lambda x: -x[1]):
            print(f"  {r:15s} {count:6d}")
        return

    # Ingest
    print("=== Starting ingestion ===")
    start_time = time.time()

    results = []
    for i, session in enumerate(all_sessions):
        title = session['title']
        sid = session['session_id']
        turns = session['turns']

        print(f"[{i+1}/{len(all_sessions)}] {title[:50]:52s} ({len(turns):4d} turns)...", end=' ', flush=True)

        try:
            result = ingest_session(sid, title, turns, dry_run=False)
            results.append(result)

            if result.get('skipped'):
                print(f"SKIP ({result['reason']})")
            else:
                elapsed = time.time() - start_time
                print(f"OK ({result['turns']} recorded, seq={result['sequence']}, {elapsed:.1f}s elapsed)")
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({'session_id': sid, 'title': title, 'error': str(e)})

    elapsed = time.time() - start_time

    # Summary
    successful = sum(1 for r in results if 'error' not in r and not r.get('skipped'))
    skipped = sum(1 for r in results if r.get('skipped'))
    failed = sum(1 for r in results if 'error' in r)
    total_recorded = sum(r.get('turns', 0) for r in results)

    print()
    print("=== Ingestion Complete ===")
    print(f"Sessions ingested: {successful}")
    print(f"Sessions skipped:  {skipped}")
    print(f"Sessions failed:   {failed}")
    print(f"Total turns recorded: {total_recorded:,}")
    print(f"Time elapsed: {elapsed:.1f}s")
    if total_recorded > 0:
        print(f"Average per turn: {elapsed/total_recorded*1000:.1f}ms")

    # Save ingestion report
    report_file = transcript_dir / 'ingestion_report.json'
    report = {
        'ingestedAt': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'totalSessions': len(all_sessions),
        'successful': successful,
        'skipped': skipped,
        'failed': failed,
        'totalTurnsRecorded': total_recorded,
        'elapsedSeconds': round(elapsed, 1),
        'results': results,
    }
    report_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"\nReport: {report_file}")


if __name__ == '__main__':
    main()
