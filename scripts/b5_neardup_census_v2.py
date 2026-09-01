#!/usr/bin/env python3
"""B5 phase 2 v2 — memory-lean near-duplicate census (NO deletions).

Paragraph-hash inverted index: near-duplicate docs share most paragraphs.
For each doc, count co-occurrences over its (non-boilerplate) paragraph
hashes; a partner sharing >=80% of the smaller doc's paragraphs is a
near-twin. Union-find clusters. Streaming per-doc: no global pair set.
"""
import lmdb, msgpack, json, unicodedata, hashlib
from collections import defaultdict

MIN_PARA = 60          # chars; shorter paragraphs are boilerplate-ish
MAX_POSTINGS = 3000    # paragraph-hash shared by too many docs = template
THRESH = 0.80          # share of smaller doc's paragraphs required
env = lmdb.open(
    "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/vault/lmdb",
    readonly=True, lock=False, max_dbs=32,
)

index = defaultdict(list)   # para_hash -> [doc_key]
doc_paras = {}              # doc_key -> set(para_hash)
doc_len = {}                # doc_key -> char length

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
            paras = set()
            for p in content.split("\n"):
                p = p.strip()
                if len(p) < MIN_PARA:
                    continue
                paras.add(hashlib.sha1(p.encode()).digest()[:10])
            if len(paras) < 3:
                continue
            doc_paras[key] = paras
            doc_len[key] = len(content)
            for ph in paras:
                index[ph].append(key)
    print(f"{galaxy}: docs so far {len(doc_paras)}", flush=True)
env.close()

print(f"paragraph index: {len(index)} distinct paragraph hashes", flush=True)

# prune boilerplate paragraphs (shared by too many docs)
for ph in list(index):
    if len(index[ph]) > MAX_POSTINGS:
        del index[ph]

pairs = []
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
                pairs.append((round(j, 3), key, other, doc_len[key]))
                ra, rb = find(key), find(other)
                if ra != rb:
                    parent[rb] = ra
    if len(pairs) % 20000 == 0 and pairs:
        print(f"  near-twins so far: {len(pairs)}", flush=True)

pairs.sort(reverse=True)
cl = defaultdict(list)
for k in doc_paras:
    cl[find(k)].append(k)
multi = [v for v in cl.values() if len(v) > 1]

report = {
    "method": "paragraph-hash inverted index, THRESH=0.80, J>=0.90",
    "near_twin_pairs": len(pairs),
    "clusters": len(multi),
    "docs_in_clusters": sum(len(v) for v in multi),
    "top": [{"j": j, "a": a, "b": b, "len": l} for j, a, b, l in pairs[:40]],
}
out = "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-neardup-report.json"
json.dump(report, open(out, "w"), indent=1)
print(
    f"near-twin pairs: {len(pairs)} | clusters: {len(multi)} | "
    f"docs involved: {sum(len(v) for v in multi)} | report: {out}",
    flush=True,
)
