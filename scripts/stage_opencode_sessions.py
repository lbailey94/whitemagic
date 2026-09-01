#!/usr/bin/env python3
"""Stage opencode.db sessions into per-session JSONL transcripts.

Phase 1 (opencode) of the App Retirement & Session Harvest plan.
Reuses mine_opencode_corpus's allowlisted-table discipline, credential
redaction, and timestamp conventions. One .jsonl per session:

    {"type":"user","role":"user","content":"[opencode session metadata] title=... directory=... created=... session_id=..."}
    {"type":"assistant","role":"assistant","content":"...","ts_iso":...,"msg_id":...}

This is the wm-ingest-native "bare transcript" shape (see
crates/wm-mcp/src/ingest.rs transcript_line_text): `type` carries the role,
`content` the redacted text. Tool-status part markers are excluded from the
ingest surface (retrieval noise; the db remains the source of truth for
tool payloads). Output paths are UUID-based (never credential-shaped by
construction); the credential-filename guard is still applied for defense
in depth.
"""

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mine_opencode_corpus import (  # noqa: E402
    DEFAULT_DB,
    credential_shaped_filename,
    fetch_sessions,
    ms_to_iso,
    part_text,
    redact,
)


def message_role(data: str) -> str:
    try:
        obj = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return "unknown"
    role = obj.get("role")
    return role if isinstance(role, str) and role else "unknown"


def stage(db_path: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    sessions = fetch_sessions(conn, project=None, since=None, until=None)
    total_msgs = 0
    total_parts = 0
    parse_errors = 0
    redactions: dict[str, int] = {}
    files = []

    for i, session in enumerate(sessions, 1):
        sid = session["id"]
        out_path = os.path.join(out_dir, f"{sid}.jsonl")
        if credential_shaped_filename(out_path):
            print(f"refusing credential-shaped path: {out_path}", file=sys.stderr)
            continue
        lines = [
            json.dumps(
                {
                    "type": "user",
                    "role": "user",
                    "content": (
                        f"[opencode session metadata] title={session['title']} "
                        f"directory={session['directory']} "
                        f"created={ms_to_iso(session['time_created'])} "
                        f"session_id={sid}"
                    ),
                    "ts_iso": ms_to_iso(session["time_created"]),
                }
            )
        ]
        msgs = conn.execute(
            "SELECT id, time_created, data FROM message WHERE session_id = ? "
            "ORDER BY time_created, id",
            (sid,),
        ).fetchall()
        total_msgs += len(msgs)
        for msg in msgs:
            role = message_role(msg["data"])
            parts = conn.execute(
                "SELECT data FROM part WHERE message_id = ? ORDER BY time_created, id",
                (msg["id"],),
            ).fetchall()
            for part in parts:
                kind, text = part_text(part["data"])
                if text is None:
                    if kind is None:
                        parse_errors += 1
                    continue
                if kind == "tool":
                    continue
                clean, counts = redact(text)
                for k, v in counts.items():
                    redactions[k] = redactions.get(k, 0) + v
                if not clean.strip():
                    continue
                role = role if role in ("user", "assistant") else "assistant"
                lines.append(
                    json.dumps(
                        {
                            "type": role,
                            "role": role,
                            "content": clean,
                            "ts_iso": ms_to_iso(msg["time_created"]),
                            "msg_id": msg["id"],
                        }
                    )
                )
                total_parts += 1
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        files.append({"session_id": sid, "path": out_path, "turns": total_parts})
        if i % 50 == 0 or i == len(sessions):
            print(f"[{i}/{len(sessions)}] parts so far: {total_parts}", flush=True)

    manifest = {
        "source_db": db_path,
        "staged_at": dt.datetime.now(dt.UTC).isoformat(),
        "sessions": len(sessions),
        "files_written": len(files),
        "messages": total_msgs,
        "parts_written": total_parts,
        "parse_errors": parse_errors,
        "redactions": redactions,
    }
    with open(os.path.join(out_dir, "..", "stage_manifest.json"), "w") as mf:
        json.dump(manifest, mf, indent=2)
    print(json.dumps(manifest, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    stage(a.db, a.out)


if __name__ == "__main__":
    main()
