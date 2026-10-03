# RECEIPT — Phase 0 control freeze (Gen2 v9.1.7)

**Date:** 2026-09-16 · **Status:** recorded · **Purpose:** pin the A/B control artifact and
corpus before any Gen3 implementation exists.

---

## 1. Control release

| Field | Value |
|---|---|
| Version | 9.1.7 |
| Git tag | `v9.1.7` (annotated) |
| Tag → commit | `94b6420ab982ec1fa8087d12c5824fc4f843869c` ("release: v9.1.7", 2026-09-15 16:55:07 −0400) |
| GitHub Release published | 2026-09-15T21:37:08Z (not prerelease) |
| Signed release manifest | `release-manifest.json` sha256 `98d689edcd030f724640b1cc1eb86c109c3fa785bcfa56624d319ab279396956` (+ `.sig`) |
| Repository state note | WMv9 HEAD at freeze time: `cff34a0` (post-release work, 9.1.8 in flight). **The control is the tag, not HEAD.** |

### Control binary (primary)

| Field | Value |
|---|---|
| Asset | `wm-linux-x86_64-musl` |
| Size | 25,095,456 B |
| sha256 | `47b5c28e3228a0d5f3b8e733538018d2d40b70bd0beb8f134081335b679621ad` |
| Verification | Digest matches the official GitHub Release asset digest (queried 2026-09-16) **and** byte-identical to the installed `~/.local/bin/wm` (`wm 9.1.7`, 25,095,456 B) |
| Why musl primary | Statically linked; reproducible on this machine without glibc coupling |

### Secondary control variant (documentation only)

| Asset | Size | sha256 |
|---|---|---|
| `wm-linux-x86_64` (glibc) | 24,934,160 B | `2b227b0bd8cbfe2f5fab734c9c78dd292701520ac2db3b84f8397cc7db699129` |

(Externally verified 2026-09-15 by the three-day review transcript; matches the official
release digest.)

---

## 2. Corpus pin (MemoraStrict)

| File | sha256 |
|---|---|
| `scenario_seed1.json` | `7bebea98924b4ec3e6511b94c0059469b6c625ba4b1aff5b621b6d2c9369621f` |
| `scenario_seed2.json` | `2da2e2472d76007ee966850af16662ac94ad85593ede67b5edee1b7ee1c334a1` |
| `scenario_seed3.json` | `3ab6bd9471ce2fe504ea6fe56cbd3c6a507837d251679965810dda6915eb82a3` |
| `scenario_seed4.json` | `7d140fc0dc53950ac8f68b7eceff36686691dccda26701b419ff34ee6949acdf` |
| `scenario_seed5.json` | `db84cf3ac6ec923ba03f161c9660f6d03c46ecb4b84b34c3a343207d36b115cc` |
| `bench_seed1.json` | `81c20ee75dbf6bf989f16d47d35171336b2787f32f6a964652b2d6415ed902d3` |
| `bench_seed2.json` | `d7772fcbd0ca7e37500ab5ba6b2a86f6c5ec38baf581268a242cc0069d331f7a` |
| `bench_seed3.json` | `54a641038bf7f7591a68a647919fe81173a450b9b1967077d5a3f39b873dee44` |
| `bench_seed4.json` | `cd3ee051fd598b570715fd997bb0c6633d784ea11f9c8c120dc07580ca9c2b64` |
| `bench_seed5.json` | `c026d4687e259ff8ff5aa8d40514a18f280c2ecfdd619d84d72166bc5ae4f450` |
| `manifest.json` | `051372ab30f99e0e526c8afa17bc08edbe04f9a0779e0d14078f5a67c87384c3` |

## 3. Harness pin

| File | sha256 |
|---|---|
| `scripts/memorastrict_bench.py` | `df9d42c24a1005c102e8d99436e7cde37bccc3d8f2958ad4f6659d639c3dc597` |
| `scripts/memorastrict_gen.py` | `17a9db2031bbe091a4282e5de3090182383cc2ef5d40ab76d4783de5209bdabd` |
| `scripts/eval_protocol.py` | `bb3e70b55c38b24ad22e26b87e54d52a51c514c65d336e9194e96b05b9d3b6ff` |

---

## 4. Rules recorded with this freeze

1. Any drift in the control binary hash, tag commit, corpus, or harness **voids the A/B** and requires re-baselining with a new receipt.
2. All control-arm runs execute the verified musl binary as a black box on `data/control/` copies.
3. Production stores are never read directly by experiment code; corpus exports are copied, hashed, frozen.
4. This receipt is append-only; corrections create a new receipt referencing this one.
