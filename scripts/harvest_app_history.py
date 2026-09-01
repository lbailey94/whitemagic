#!/usr/bin/env python3
"""App-retirement harvest: Antigravity + Windsurf → staging (Phase 1-2).

Per planning/SESSION_App_Retirement_Session_Harvest.md:
- Copy User/globalStorage/** and User/workspaceStorage/** (chat state).
- Flatten User/History/** (VS Code Local History) into per-resource JSONL
  transcripts with file-path provenance; text-like entries get full content,
  binary entries are logged (size only). Credential-shaped paths refused.
"""

import json
import os
import shutil
import sys

sys.path.insert(0, "/home/lucas/Desktop/WHITEMAGIC/WMv5/scripts")
from mine_opencode_corpus import credential_shaped_filename  # noqa: E402

HOME = os.path.expanduser("~")
STAGE = f"{HOME}/Desktop/WHITEMAGIC/data/WMdata/staging/app-retirement"
TEXT_EXT = {".md", ".txt", ".json", ".jsonl", ".js", ".ts", ".py", ".rs", ".toml",
            ".yaml", ".yml", ".html", ".css", ".sh", ".go", ".kts", ".java", ".xml",
            ".csv", ".log", ".ini", ".cfg", ".sql", ".hbs", ".scss", ".svg"}
MAX_ENTRY = 2_000_000


def flatten_history(app_root: str, out_dir: str) -> dict:
    stats = {"resources": 0, "entries": 0, "skipped_binary": 0, "redacted_files": 0}
    hist = os.path.join(app_root, "User", "History")
    if not os.path.isdir(hist):
        print(f"no History dir at {hist}")
        return stats
    os.makedirs(out_dir, exist_ok=True)
    for hdir in sorted(os.listdir(hist)):
        hd = os.path.join(hist, hdir)
        ej = os.path.join(hd, "entries.json")
        if not os.path.isfile(ej):
            continue
        try:
            meta = json.load(open(ej, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        resource = meta.get("resource", "")
        if not resource:
            continue
        rpath = resource.replace("file://", "")
        if credential_shaped_filename(rpath):
            stats["redacted_files"] += 1
            continue
        entries = meta.get("entries", [])
        safe = rpath.strip("/").replace("/", "__").replace(":", "_")[:150] or "unnamed"
        outp = os.path.join(out_dir, f"{safe}.jsonl")
        with open(outp, "a", encoding="utf-8") as out:
            for ent in entries:
                eid, ts = ent.get("id", ""), ent.get("timestamp", 0)
                src = os.path.join(hd, eid)
                ts_iso = (
                    datetime.datetime.fromtimestamp(ts / 1000, tz=datetime.timezone.utc).isoformat()
                    if isinstance(ts, (int, float)) and ts > 10**12
                    else str(ts)
                )
                ext = os.path.splitext(rpath)[1].lower()
                if ext in TEXT_EXT and os.path.isfile(src) and os.path.getsize(src) <= MAX_ENTRY:
                    try:
                        content = open(src, encoding="utf-8", errors="replace").read()
                    except OSError:
                        content = ""
                    kind = "text"
                else:
                    content, kind = "", "binary"
                    stats["skipped_binary"] += 1
                out.write(json.dumps({
                    "resource": rpath, "history_id": hdir, "entry_id": eid,
                    "ts_iso": ts_iso, "kind": kind, "content": content,
                }) + "\n")
                stats["entries"] += 1
        stats["resources"] += 1
    return stats


import datetime  # noqa: E402

def harvest(app: str, config_dir: str) -> None:
    out = os.path.join(STAGE, app)
    os.makedirs(out, exist_ok=True)
    print(f"== {app}: copying globalStorage + workspaceStorage", flush=True)
    for sub in ("globalStorage", "workspaceStorage"):
        src = os.path.join(config_dir, "User", sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(out, sub), dirs_exist_ok=True)
    print(f"== {app}: flattening History", flush=True)
    stats = flatten_history(config_dir, os.path.join(out, "history_flat"))
    print(f"== {app}: {stats}", flush=True)


if __name__ == "__main__":
    harvest("antigravity", f"{HOME}/.config/Antigravity")
    harvest("windsurf", f"{HOME}/.config/Windsurf")
    print("HARVEST_DONE")
