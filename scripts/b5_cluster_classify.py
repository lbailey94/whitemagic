#!/usr/bin/env python3
"""B5 phase 3 — classify near-duplicate clusters into synthesis tiers.

A trivial-variant : normalized content identical across cluster
B chunk-fragments : members carry chunk:N/M tags of the same source doc
C versions        : same source, divergent content (edits)
D cross-source    : members from different source: tags
"""
import lmdb, msgpack, json, re, unicodedata, hashlib
from collections import defaultdict

MIN_PARA, MAX_POSTINGS, THRESH = 60, 3000, 0.80


def is_control(c):
    return unicodedata.category(c) == "Cc"


def normalize(text):
    text = "".join(c for c in text if not (is_control(c) and c not in "\n\t\r"))
    return re.sub(r"\s+", " ", text).strip()


env = lmdb.open(
    "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/vault/lmdb",
    readonly=True, lock=False, max_dbs=32,
)
index = defaultdict(list)
doc_paras, doc_len, doc_meta = {}, {}, {}

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
            key = f"{galaxy}:{k.hex()[:16]}"
            fields = m[0] if isinstance(m[0], (list, tuple)) and len(m[0]) > 3 else []
            tags = [t for t in (fields[3] if isinstance(fields[3], list) else []) if isinstance(t, str)]
            src = next((t.split(":", 1)[1] for t in tags if t.startswith("source:")), "?")
            chunk = next((t.split(":", 1)[1] for t in tags if t.startswith("chunk:")), "")
            paras = set()
            for p in content.split("\n"):
                p = p.strip()
                if len(p) >= MIN_PARA:
                    paras.add(hashlib.sha1(p.encode()).digest()[:10])
            if len(paras) < 3:
                continue
            doc_paras[key] = paras
            doc_len[key] = len(content)
            doc_meta[key] = {"galaxy": galaxy, "src": src, "chunk": chunk, "content": content}
            for ph in paras:
                index[ph].append(key)
env.close()
print(f"docs: {len(doc_paras)}", flush=True)

for ph in list(index):
    if len(index[ph]) > MAX_POSTINGS:
        del index[ph]

parent = {k: k for k in doc_paras}


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for key, paras in doc_paras.items():
    co = defaultdict(int)
    for ph in paras:
        for other in index.get(ph, ()):
            if other != key:
                co[other] += 1
    for other, cnt in co.items():
        if find(key) == find(other):
            continue
        smaller = min(len(paras), len(doc_paras[other]))
        if smaller and cnt / smaller >= THRESH:
            j = cnt / (len(paras) + len(doc_paras[other]) - cnt)
            if j >= 0.90:
                ra, rb = find(key), find(other)
                if ra != rb:
                    parent[rb] = ra
print("clustering done", flush=True)

cl = defaultdict(list)
for k in doc_paras:
    cl[find(k)].append(k)
multi = [v for v in cl.values() if len(v) > 1]

tiers = defaultdict(list)
for members in multi:
    norm = {m: normalize(doc_meta[m]["content"]) for m in members}
    srcs = {doc_meta[m]["src"] for m in members}
    chunks = {doc_meta[m]["chunk"] for m in members if doc_meta[m]["chunk"]}
    if len(set(norm.values())) == 1:
        tier = "A_trivial"
    elif len(members) > 1 and chunks and all(re.match(r"\d+/\d+$", c) for c in chunks) and len(srcs) == 1:
        tier = "B_fragments"
    elif len(srcs) > 1:
        tier = "D_cross_source"
    else:
        tier = "C_versions"
    tiers[tier].append(members)

summary = {}
for tier, clusters in sorted(tiers.items()):
    docs = sum(len(c) for c in clusters)
    removable = docs - len(clusters)
    summary[tier] = {"clusters": len(clusters), "docs": docs, "removable": removable}
    print(f"{tier}: {len(clusters)} clusters, {docs} docs, {removable} removable", flush=True)

out = "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-cluster-tiers.json"
json.dump(
    {
        "summary": summary,
        "clusters": {t: [{m: {"src": doc_meta[m]["src"], "chunk": doc_meta[m]["chunk"], "len": doc_len[m]} for m in c} for c in cl_] for t, cl_ in tiers.items()},
    },
    open(out, "w"),
)
print(f"tier report: {out}", flush=True)
