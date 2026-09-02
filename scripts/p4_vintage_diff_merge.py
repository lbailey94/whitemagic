#!/usr/bin/env python3
"""P4 vintage diff-merge — VAULT archive DBs + v26 galaxy DBs vs heritage export.

Keyed by content_hash (DB-stored) else sha256(content). Newest-vintage wins;
conflicts keep both (each vintage's unique content emits as its own record).
Emits heritage-format files (same 1:1 header mapping the P3 ingest path
verifies) into a staging tree for `wm ingest`. Guard mirrors: credential
filename hints, PEM content, 64MB cap — identical semantics to ingest.rs.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from collections import defaultdict

ROOT = "/home/lucas/Desktop/WHITEMAGIC"
HERITAGE_EXPORT = f"{ROOT}/data/staging/v26-heritage"
STAGING = f"{ROOT}/data/staging/vintage-merge"
EVIDENCE = f"{ROOT}/planning/v8/P4_VINTAGE_MERGE_EVIDENCE"
VAULT = f"{ROOT}/archives/WHITEMAGIC_VAULT/10_WHITEMAGIC_INTERNAL"
V26_GALAXIES = f"{ROOT}/data/WMdata/v26/state/users/local/galaxies"

NATIVE_GALAXIES = {"aria", "citta", "codex", "journals", "dreams", "research",
                   "sessions", "substrate", "universal"}
CREDS_HINTS = (".env", ".pem", ".key", ".p12", ".pfx", ".crt", "id_rsa",
               "id_ed25519", "id_ecdsa", "credentials", "secrets", "password",
               "passwd", "token")
PEM_MARKERS = ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY",
               "BEGIN OPENSSH PRIVATE KEY", "BEGIN EC PRIVATE KEY")
MAX_BODY_BYTES = 64 * 1024 * 1024

HDR_FIELDS = ["memory_type", "created_at", "updated_at", "accessed_at",
              "access_count", "recall_count", "importance", "neuro_score",
              "novelty_score", "emotional_valence", "retention_score",
              "galactic_distance", "half_life_days", "is_protected",
              "is_private", "model_exclude", "source_trust", "title"]
MARKER = "<!-- WhiteMagic v26 heritage export -->"

stats = defaultdict(lambda: defaultdict(int))
emitted_keys = set()          # content keys emitted this run (any vintage)
id_map = defaultdict(set)     # v26 memory id -> set of (vintage, key)
conflicts = defaultdict(list) # id -> list of differing (vintage, key)
t0 = time.time()


def esc(v):
    return str(v).replace("--", "__") if v is not None else ""


def sanitize_title(t, max_len=48):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (t or "").strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:max_len] or "untitled"


def body_key(content, content_hash):
    # normalize like the v26 exporter: trim both ends (DB rows carry
    # trailing whitespace the exporter stripped when writing files)
    return hashlib.sha256(
        content.strip().encode("utf-8", "surrogatepass")).hexdigest()


# ── 1. index heritage export bodies ─────────────────────────────────────
def heritage_body(text):
    """Mirror parse_heritage: marker line + wm-* headers, body from first
    non-header non-blank line onward (blank separators dropped)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != MARKER:
        return None
    body_start = None
    for i in range(1, len(lines)):
        t = lines[i].strip()
        if not t:
            continue
        if t.startswith("<!-- wm-") and t.endswith("-->"):
            continue
        body_start = i
        break
    if body_start is None:
        return ""
    return "\n".join(lines[body_start:])


print("== indexing heritage export ==", flush=True)
H = {}
n_files = 0
for dirpath, _dirnames, filenames in os.walk(HERITAGE_EXPORT):
    for fn in filenames:
        if not fn.endswith(".md"):
            continue
        p = os.path.join(dirpath, fn)
        n_files += 1
        if any(h in fn.lower() for h in CREDS_HINTS):
            stats["heritage_index"]["cred_name_skip"] += 1
            continue
        try:
            with open(p, encoding="utf-8", errors="surrogateescape") as f:
                text = f.read(80 * 1024 * 1024)
        except OSError:
            stats["heritage_index"]["unreadable"] += 1
            continue
        if len(text.encode("utf-8", "surrogatepass")) > MAX_BODY_BYTES:
            stats["heritage_index"]["oversize_skip"] += 1
            continue
        if any(m in text for m in PEM_MARKERS):
            stats["heritage_index"]["pem_skip"] += 1
            continue
        body = heritage_body(text)
        key = hashlib.sha256(
            body.strip().encode("utf-8", "surrogatepass")).hexdigest()
        H[key] = os.path.relpath(p, HERITAGE_EXPORT)
print(f"  files seen {n_files} · indexed {len(H)} · "
      f"{dict(stats['heritage_index'])} · {time.time()-t0:.0f}s", flush=True)

# seed emitted_keys from a previous run's staging tree (idempotent re-runs)
seeded = 0
for dirpath, _dn, filenames in os.walk(STAGING):
    for fn in filenames:
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(dirpath, fn), encoding="utf-8",
                  errors="surrogateescape") as f:
            body = heritage_body(f.read())
        emitted_keys.add(hashlib.sha256(
            body.strip().encode("utf-8", "surrogatepass")).hexdigest())
        seeded += 1
print(f"  seeded {seeded} keys from prior staging run", flush=True)

# union with the live heritage-store content hashes (ground truth for
# "already unified"; S includes everything the store actually holds)
store_keys = 0
import glob as _glob
for hp in _glob.glob("/tmp/opencode/store_hashes_*.txt"):
    with open(hp) as hf:
        for line in hp and hf:
            line = line.strip()
            if line:
                H[line] = "heritage-store"
                store_keys += 1
print(f"  unioned {store_keys} heritage-store content hashes", flush=True)

# ── 2. vintage sources (newest-first) ───────────────────────────────────
V26_DBS = sorted(
    os.path.join(dp, "whitemagic.db")
    for dp, dn, fn in os.walk(V26_GALAXIES) if "whitemagic.db" in fn
)
SOURCES = [
    ("v26", V26_DBS),
    ("vault-sessions", [f"{VAULT}/galaxy_dbs/sessions/whitemagic.db"]),
    ("vault-backup", [os.environ.get(
        "P4_BACKUP_DB", f"{VAULT}/whitemagic_backup.db")]),
]
if os.environ.get("P4_ONLY"):
    SOURCES = [s for s in SOURCES if s[0] == os.environ["P4_ONLY"]]

os.makedirs(STAGING, exist_ok=True)
os.makedirs(EVIDENCE, exist_ok=True)


def q(col):  # quote identifier
    return '"' + col.replace('"', '""') + '"'


def table_dump(conn, table, out, vintage, db_label):
    """Stream a raw table to gzipped JSONL (namespace preservation)."""
    import gzip
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({q(table)})")]
    if not cols:
        return 0
    n = 0
    with gzip.open(out, "wt", compresslevel=6) as fh:
        for row in conn.execute(f"SELECT * FROM {q(table)}"):
            fh.write(json.dumps({"vintage": vintage, "db": db_label,
                                 "table": table,
                                 "row": dict(zip(cols, row))},
                                default=str) + "\n")
            n += 1
            if n % 50_000 == 0:
                print(f"    [{db_label}/{table}] {n}…", flush=True)
    return n


def row_date(s):
    if not s:
        return "00000000"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    return m.group(1) + m.group(2) + m.group(3) if m else "00000000"


def emit(vintage, row, cols, gdir):
    """Write one heritage-format file. Returns out path or None."""
    content = row["content"]
    key = row["_key"]
    if not content or not content.strip():
        stats[vintage]["empty_skip"] += 1
        return None
    if any(m in content for m in PEM_MARKERS):
        stats[vintage]["pem_skip"] += 1
        return None
    if len(content.encode("utf-8", "surrogatepass")) > MAX_BODY_BYTES:
        stats[vintage]["oversize_skip"] += 1
        return None

    galaxy = (row.get("galaxy") or "universal").strip().lower() or "universal"
    if galaxy in NATIVE_GALAXIES:
        subdir = galaxy
    else:
        subdir = sanitize_title(galaxy, 40) or "misc"

    tags = [t.strip() for t in (row.get("tags") or "").split(",") if t.strip()]
    if row["_extra_tags"]:
        tags.extend(row["_extra_tags"])
    tags.append(f"vintage:{vintage}")

    title = row.get("title") or ""
    imp = row.get("importance")
    try:
        ival = int(round(float(imp) * 100))
    except (TypeError, ValueError):
        ival = 50
    name = f"{row_date(row.get('created_at'))}_i{ival}_{sanitize_title(title)}_{key[:12]}.md"

    ddir = os.path.join(STAGING, vintage, subdir)
    os.makedirs(ddir, exist_ok=True)
    out = os.path.join(ddir, name)
    if os.path.exists(out):  # same key+title+date already emitted
        stats[vintage]["name_collision_skip"] += 1
        return None

    lines = [MARKER]
    for f in HDR_FIELDS:
        if f == "title":
            v = title
        elif f == "source_trust":
            v = row.get("source_trust") or ("tool" if vintage != "v26" and (
                row.get("memory_type", "").upper() == "CITTA"
                or subdir in ("sessions", "substrate")) else "user")
        else:
            v = row.get(f)
        if v is None or v == "":
            continue
        lines.append(f"<!-- wm-{f}: {esc(v)} -->")
    if subdir not in NATIVE_GALAXIES:
        lines.append(f"<!-- wm-tags: {esc(','.join(tags + ['heritage-category:' + subdir]))} -->")
    else:
        lines.append(f"<!-- wm-tags: {esc(','.join(tags))} -->")
    lines.append("")
    lines.append(content.strip())

    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return out


def scan_vintage(vintage, dbs):
    for dbp in dbs:
        label = os.path.basename(os.path.dirname(dbp)) if vintage == "v26" else vintage
        if not os.path.exists(dbp):
            stats[vintage]["missing_db"] += 1
            continue
        # copy with WAL for a consistent read snapshot
        import shutil, tempfile
        tmp = tempfile.mkdtemp(prefix="p4db-")
        for suffix in ("", "-wal", "-shm"):
            src = dbp + suffix
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmp, "whitemagic.db" + suffix))
        conn = sqlite3.connect(os.path.join(tmp, "whitemagic.db"))
        conn.row_factory = sqlite3.Row
        try:
            cols = [c[1] for c in conn.execute("PRAGMA table_info(memories)")]
            sel = ",".join(q(c) for c in cols)
            has_hash = "content_hash" in cols
            has_tags_tbl = True
            extra = {}
            if has_tags_tbl and "tags" in [c[1] for c in conn.execute(
                    "PRAGMA table_info(tags)")]:
                for mid, tag in conn.execute("SELECT memory_id, tag FROM tags"):
                    extra.setdefault(mid, []).append(tag)
            n = 0
            for r in conn.execute(f"SELECT {sel} FROM memories"):
                n += 1
                content = r["content"] or ""
                ch = r["content_hash"] if has_hash else None
                key = body_key(content, ch)
                stats[ch and "db_hash" or "computed_hash"]  # touch counter
                d = dict(r)
                d["_key"] = key
                d["_extra_tags"] = sorted(set(extra.get(r["id"], [])))
                id_map[r["id"]].add((vintage, key))
                if key in H or key in emitted_keys:
                    stats[vintage]["already_unified"] += 1
                    continue
                emitted_keys.add(key)
                if emit(vintage, d, cols, label):
                    stats[vintage]["emitted"] += 1
                    if stats[vintage]["emitted"] % 10_000 == 0:
                        print(f"  [{vintage}/{label}] emitted "
                              f"{stats[vintage]['emitted']}… {time.time()-t0:.0f}s",
                              flush=True)
            stats[vintage]["rows_total"] += n
            # raw-table namespace dumps
            for tbl in ("associations", "tags", "zodiac_ledger",
                        "akashic_seeds", "constellation_membership",
                        "holographic_coords", "dharma_audit", "solutions",
                        "cache_garden_stats"):
                try:
                    nd = table_dump(conn, tbl, f"{EVIDENCE}/{vintage}_{tbl}.jsonl.gz",
                                    vintage, label)
                    if nd:
                        print(f"  dumped {vintage}/{tbl}: {nd} rows", flush=True)
                except sqlite3.Error:
                    pass
        finally:
            conn.close()
            shutil.rmtree(tmp, ignore_errors=True)


print("== scanning vintages (newest-first) ==", flush=True)
for vintage, dbs in SOURCES:
    print(f"-- {vintage} ({len(dbs)} dbs)", flush=True)
    scan_vintage(vintage, dbs)

# ── 3. id-level conflicts ────────────────────────────────────────────────
same_content_reuse = 0
for rid_, vks in id_map.items():
    if len({k for _v, k in vks}) > 1:
        conflicts[rid_] = sorted(vks)
    elif len(vks) > 1:
        same_content_reuse += 1

report = {
    "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "heritage_index": {"files_seen": n_files, "indexed": len(H),
                       **stats["heritage_index"]},
    "staging_seeded_keys": seeded,
    "staging_files_on_disk": {
        v: sum(len(files) for _dp, _dn, files in os.walk(
            os.path.join(STAGING, v)) ) for v, _ in SOURCES},
    "vintages": {v: {k: val for k, val in stats[v].items()}
                 for v, _ in SOURCES},
    "id_conflicts": {"count": len(conflicts),
                     "same_content_id_reuse": same_content_reuse,
                     "sample": dict(list(conflicts.items())[:20])},
    "emitted_total": sum(stats[v].get("emitted", 0) for v, _ in SOURCES),
    "staging_tree": STAGING,
}
with open(f"{EVIDENCE}/P4_DIFF_REPORT.json", "w") as f:
    json.dump(report, f, indent=1)
print(json.dumps(report, indent=1)[:2500])
print(f"DONE in {time.time()-t0:.0f}s", flush=True)
