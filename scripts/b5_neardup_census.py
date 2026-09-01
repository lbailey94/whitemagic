#!/usr/bin/env python3
"""B5 phase 2 — near-duplicate census over the vault (research + sessions).

MinHash LSH (16 perms, 4x4 bands) with fast integer permutations; Jaccard
verification at >=0.95; cluster report only — NO deletions.
"""
import lmdb, msgpack, json, itertools
from collections import defaultdict

MASK = (1 << 61) - 1
AB = [(hash(f"a{i}") & MASK or 1, hash(f"b{i}") & MASK) for i in range(16)]


def minhash(text):
    words = text.split()
    if len(words) < 6:
        return None
    sh = {hash(" ".join(words[i:i + 5])) & MASK for i in range(len(words) - 4)}
    if not sh:
        return None
    return [min((a * s + b) & MASK for s in sh) for a, b in AB]


env = lmdb.open(
    "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/vault/lmdb",
    readonly=True, lock=False, max_dbs=32,
)
buckets = defaultdict(list)
docs = {}
for galaxy in ("research", "sessions"):
    db = env.open_db(galaxy.encode())
    with env.begin(db=db) as txn:
        for k, v in txn.cursor():
            try:
                m = msgpack.unpackb(v, raw=False, strict_map_key=False)
            except Exception:
                continue
            try:
                content = m[1]
            except (IndexError, TypeError):
                continue
            if not isinstance(content, str) or len(content) < 200:
                continue
            mh = minhash(content)
            if not mh:
                continue
            key = f"{galaxy}:{k.hex()[:16]}"
            docs[key] = content
            for b in range(4):
                buckets[(b, tuple(mh[b * 4:(b + 1) * 4]))].append(key)
env.close()
print(f"LSH built: {len(docs)} docs, {len(buckets)} buckets", flush=True)

cand = set()
for bk in buckets.values():
    if len(bk) > 1:
        cand.update(itertools.combinations(sorted(bk), 2))
print(f"candidate pairs: {len(cand)}", flush=True)


def jaccard(a, b):
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


# order candidates so cluster-forming pairs come first, then union-skip makes
# the bulk of the 50M+ pair list cheap (same-cluster pairs skip verification)
cand_sorted = sorted(
    cand, key=lambda p: -max(len(docs[p[0]]), len(docs[p[1]]))
)
pairs = []
parent0 = {k: k for k in docs}


def find0(x):
    while parent0[x] != x:
        parent0[x] = parent0[parent0[x]]
        x = parent0[x]
    return x


verified = 0
for n, (a, b) in enumerate(cand_sorted):
    if find0(a) == find0(b):
        continue
    la, lb = len(docs[a]), len(docs[b])
    if abs(la - lb) / max(la, lb, 1) > 0.15:
        continue
    verified += 1
    j = jaccard(docs[a], docs[b])
    if j >= 0.95:
        pairs.append((round(j, 3), a, b, la))
        ra, rb = find0(a), find0(b)
        if ra != rb:
            parent0[rb] = ra
    if n % 5_000_000 == 0 and n:
        print(f"  {n}/{len(cand_sorted)} pairs, verified={verified}, twins={len(pairs)}", flush=True)
pairs.sort(reverse=True)

parent = parent0


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for j, a, b, _ in pairs:
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra

cl = defaultdict(list)
for k in docs:
    cl[find(k)].append(k)
multi = [v for v in cl.values() if len(v) > 1]

report = {
    "candidate_pairs": len(cand),
    "near_twin_pairs": len(pairs),
    "clusters": len(multi),
    "docs_in_clusters": sum(len(v) for v in multi),
    "top": [{"j": j, "a": a, "b": b, "len": l} for j, a, b, l in pairs[:40]],
}
out = "/home/lucas/Desktop/WHITEMAGIC/data/WMdata/staging/b5-neardup-report.json"
json.dump(report, open(out, "w"), indent=1)
print(
    f"near-twin pairs (>=0.95): {len(pairs)} | clusters: {len(multi)} | "
    f"docs involved: {sum(len(v) for v in multi)} | report: {out}"
)
