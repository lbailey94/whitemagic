#!/usr/bin/env python3
"""B5 phase 3 — tiered synthesis executor.

For each near-duplicate cluster (paragraph-overlap, J>=0.90, THRESH=0.80):
  1. canonical = cleanest source class (b5p2 > app harvests > v26-heritage),
     then longest
  2. synthesized = canonical content + novel paragraphs (by hash) from the
     other members, appended whole under a marker — NO line-merging
  3. if synthesized == canonical: pure dedup (delete others)
     else: write synthesized to staging, ingest, delete ALL members
Outputs: plan JSON + synthesized docs dir + deletion UUID list.
Run the delete phase separately via the one-shot stdio server.
"""
import lmdb, msgpack, json, os, re, unicodedata, hashlib
from collections import defaultdict

MIN_PARA, MAX_POSTINGS, THRESH = 60, 3000, 0.80
SRC_RANK = {"b5p2": 0, "opencode": 1, "windsurf": 2, "devin": 3, "brain_md": 4, "antigravity": 5}


def is_control(c):
    return unicodedata.category(c) == "Cc"


def src_class(tags):
    src = next((t.split(":", 1)[1] for t in tags if t.startswith("source:")), "?")
    for cls in SRC_RANK:
        if cls in src:
            return cls
    return "zzz_heritage"


def para_hashes(content):
    return {hashlib.sha1(p.strip().encode()).digest()[:10]
            for p in content.split("\n") if len(p.strip()) >= MIN_PARA}


env = lmdb.open(
    "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/vault/lmdb",
    readonly=True, lock=False, max_dbs=32,
)
index = defaultdict(list)
docs = {}
for galaxy in ("research", "sessions"):
    db = env.open_db(galaxy.encode())
    with env.begin(db=db) as txn:
        for k, v in txn.cursor():
            try:
                m = msgpack.unpackb(v, raw=False, strict_map_key=False)
                content = m[1]
            except Exception:
                continue
            if not isinstance(content, str) or len(content) < 200:
                continue
            fields = m[0] if isinstance(m[0], (list, tuple)) and len(m[0]) > 3 else []
            tags = [t for t in (fields[3] if isinstance(fields[3], list) else []) if isinstance(t, str)]
            kb = k.bytes if hasattr(k, "bytes") else bytes(k)
            key = f"{galaxy}:{kb.hex()}"
            ph = para_hashes(content)
            if len(ph) < 3:
                continue
            docs[key] = {
                "uuid": str(__import__("uuid").UUID(bytes=kb)),
                "galaxy": galaxy, "content": content,
                "class": src_class(tags), "ph": ph,
            }
            for h in ph:
                index[h].append(key)
env.close()
print(f"docs: {len(docs)}", flush=True)

for h in list(index):
    if len(index[h]) > MAX_POSTINGS:
        del index[h]

parent = {k: k for k in docs}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for key, paras in docs.items():
    ph = paras["ph"]
    co = defaultdict(int)
    for h in ph:
        for other in index.get(h, ()):
            if other != key:
                co[other] += 1
    for other, cnt in co.items():
        if find(key) == find(other):
            continue
        smaller = min(len(ph), len(docs[other]["ph"]))
        if smaller and cnt / smaller >= THRESH:
            j = cnt / (len(ph) + len(docs[other]["ph"]) - cnt)
            if j >= 0.90:
                ra, rb = find(key), find(other)
                if ra != rb:
                    parent[rb] = ra
print("clustering done", flush=True)

cl = defaultdict(list)
for k in docs:
    cl[find(k)].append(k)
multi = [sorted(v) for v in cl.values() if len(v) > 1]

os.makedirs("/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-synthesis", exist_ok=True)
deletes = []
synthesized = 0
pure_dedup = 0
plan = []

for members in multi:
    members.sort(key=lambda m: (SRC_RANK.get(docs[m]["class"], 9), -docs[m]["galaxy"].count("x"), -len(docs[m]["content"])))
    canon = members[0]
    canon_ph = docs[canon]["ph"]
    additions = []
    for m in members[1:]:
        novel = docs[m]["ph"] - canon_ph
        if novel:
            additions.append((m, novel))
    if not additions:
        deletes.extend(docs[m]["uuid"] for m in members[1:])
        pure_dedup += 1
        plan.append({"cluster": members, "action": "dedup", "keep": canon,
                     "delete": [docs[m]["uuid"] for m in members[1:]]})
        continue
    # synthesize: canonical + novel paragraphs from others (whole, in order)
    body = docs[canon]["content"].rstrip() + "\n\n"
    body += f"## Synthesized additions\n<!-- b5 synthesis: novel paragraphs from {len(additions)} near-twin member(s); canonical={docs[canon]['uuid']} -->\n"
    for m, novel in additions:
        seen = set(canon_ph)
        for p in docs[m]["content"].split("\n"):
            ps = p.strip()
            if len(ps) < MIN_PARA:
                continue
            h = hashlib.sha1(ps.encode()).digest()[:10]
            if h in novel and h not in seen:
                body += p + "\n"
                seen.add(h)
        canon_ph |= novel
        body += f"<!-- absorbed: {docs[m]['uuid']} (source={docs[m]['class']}) -->\n"
    header = (f"<!-- b5 synthesis | galaxy={docs[canon]['galaxy']} | canonical={docs[canon]['uuid']} | "
              f"members={len(members)} | classes={sorted({docs[m]['class'] for m in members})} -->\n\n")
    fname = f"synth_{docs[canon]['uuid']}.md"
    with open(f"/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-synthesis/{fname}", "w") as fh:
        fh.write(header + body)
    deletes.extend(docs[m]["uuid"] for m in members)
    synthesized += 1
    plan.append({"cluster": members, "action": "synthesize", "new_file": fname,
                 "delete": [docs[m]["uuid"] for m in members]})

json.dump({"clusters": len(multi), "pure_dedup": pure_dedup, "synthesized": synthesized,
           "deletes": deletes},
          open("/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-synth-plan.json", "w"))
print(f"clusters: {len(multi)} | pure dedup: {pure_dedup} | synthesized docs: {synthesized} | "
      f"total deletions: {len(deletes)}", flush=True)
