=== MESSAGE 0 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 1 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 2 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 3 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 4 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 5 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 6 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 7 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 8 - Assistant ===
Models are downloading in the background. Let me check progress and also search for a few more critical models.

=== MESSAGE 9 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 10 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 11 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 12 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 13 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 14 - Assistant ===
Let me pull gpt-oss:20b as well and check download progress across all the pulls.

=== MESSAGE 15 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 16 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 17 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 18 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 19 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 20 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 21 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 22 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 23 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 24 - Assistant ===
All 10 models downloading simultaneously. Let me check disk space — we may need to prioritize.

=== MESSAGE 25 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 26 - Assistant ===
41GB free — we're tight. The Chinese models (highest priority) total ~25GB, gpt-oss:20b ~12GB, phi4-mini ~2.5GB. mistral-small3.1 (15GB) and gemma3:12b (8.1GB) may not fit. The downloads will naturally fail when disk fills — the highest-priority models (started first) should complete first. Let me write the strategic analysis while they download.

=== MESSAGE 27 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 28 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 29 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 30 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 31 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 32 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 33 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 34 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 35 - Assistant ===
qwen3:1.7b done. Let me check disk and the remaining downloads.

=== MESSAGE 36 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 37 - Assistant ===
29GB free, 34GB in Ollama. The Chinese models (~13GB remaining) and gpt-oss:20b (~12GB) should fit. mistral-small3.1 (15GB) likely won't — but it's lowest priority (Tier 4). The higher-priority models were started first and are smaller, so they should complete before disk fills.

Let me update the todo list and present the full picture.

=== MESSAGE 38 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 39 - Assistant ===
Here's the full picture:

---

# WhiteMagic in the Geopolitical Puzzle

## The Strategic Positioning doc is saved at:
- `@/home/lucas/Desktop/WHITEMAGIC/docs/message_board/STRATEGIC_POSITIONING_2026-07-07.md`
- `@/home/lucas/Desktop/WHITEMAGIC/docs/message_board/RESEARCH_SESSION_2026-07-06_STRATEGY.md` (implementation strategy)

## The Core Thesis

WhiteMagic is a **third path** between Aschenbrenner's militarized government AGI project and Altman's centralized-but-gentle corporate singularity. It's:

1. **Distributed** — runs on your laptop, not in a data center
2. **Sovereign** — you own your models, your data, your memory
3. **Governed** — Dharma + Karma provide built-in alignment, no external regulation needed
4. **Model-agnostic** — works with whatever models are available; the value is in the infrastructure, not the weights
5. **Legacy-capable** — a 4B model + WhiteMagic's 518-tool orchestration + HNSW memory is more capable than a 70B model alone

## Why Stealth Is Now a Survival Strategy

With both US and China restricting SOTA models:
- WhiteMagic isn't a model (can't be restricted as one)
- Isn't a platform (can't be acquired/shut down)
- Isn't a service (can't be API-gated)
- It's a **cognitive operating system** that makes any model better — regulators can't easily categorize it

## The Legacy Hardware Revolution

If WhiteMagic demonstrates that capable AI runs on a 3-year-old laptop:
- **Data centers become training-only** — inference moves to the edge
- **Chip export controls matter less** — you don't need H100s for inference
- **The frontier/consumer gap narrows** from the bottom up, not the top down
- **The "Project" becomes less necessary** — distributed governed AI weakens the centralization case

## The Wildcard Path

WhiteMagic could push everyone closer to AGI 2027/2028 not by building bigger models but by building better infrastructure:
- **Semantic infrastructure** (embeddings + knowledge graphs + hybrid search) as the real breakthrough — validated by the Reddit research
- **Mamba/SSM** for constant-memory session compression → always-on assistant
- **JEPA** for predictive action planning → autonomous agents
- **Dharma/Karma** as practical alignment → no need for abstract "superalignment"
- The gentle singularity happens when a laptop with a 4B model + WhiteMagic does what yesterday required a data center

## Model Archival Status

**Downloading now** (10 models, ~34GB in Ollama already, 29GB free):

| Model | Size | Priority | Status |
|---|---|---|---|
| `qwen3:1.7b` | 1.4 GB | Tier 1 (China) | ✅ Done |
| `qwen2.5vl:7b` | 6.0 GB | Tier 1 (China, VLM) | ~45% |
| `qwen3:8b` | 5.2 GB | Tier 1 (China) | ~50% |
| `qwen3:4b` | 2.5 GB | Tier 1 (China) | ~60% |
| `phi4-mini` | 2.5 GB | Tier 4 (MS, CPU) | ~60% |
| `deepseek-r1:7b` | 4.7 GB | Tier 1 (China) | ~45% |
| `glm4:9b` | 5.5 GB | Tier 1 (China, Z.ai) | ~36% |
| `gpt-oss:20b` | 13 GB | Tier 2 (US open) | ~10% |
| `gemma3:12b` | 8.1 GB | Tier 2 (Google) | ~6% |
| `mistral-small3.1` | 15 GB | Tier 4 | ~3% — may not fit |

**Already archived**: gemma3:4b, moondream, qwen2.5:3b, qwen2.5:7b, llama3.2:1b

The Chinese models (Tier 1) are highest priority given today's news — they're the most likely to disappear from open access. All six should complete before disk fills. gpt-oss:20b should also fit. The Tier 4 models (mistral, gemma3:12b) may fail on disk space, but they're lowest risk.

## What's Next

The downloads will continue in the background. Once complete, we'll have a local archive of the most important open-weight models — insurance against the restriction trend.

For the next session, the two saved docs provide the full roadmap:
1. **RESEARCH_SESSION_2026-07-06_STRATEGY.md** — 10-item implementation plan (Tier 1-3)
2. **STRATEGIC_POSITIONING_2026-07-07.md** — geopolitical analysis and positioning

Would you like to monitor the downloads to completion, or is there anything else you'd like to discuss or adjust in the strategy?

=== MESSAGE 40 - User ===
Let's cancel gpt-oss and mistral; we should look for glm5, 5.1, and 5.2, and see if we can move any of these models to the SD Card since there's ~20GB free. We'll also get rid of older / less effective models if possible.

=== MESSAGE 41 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 42 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 43 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 44 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 45 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 46 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 47 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 48 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 49 - Assistant ===
GLM-5, 5.1, and 5.2 appear to be cloud-only on Ollama (744B/355B params — way too large for local). Let me check for smaller local-runnable variants and also look at what we can move to the SD card.

=== MESSAGE 50 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 51 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 52 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 53 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 54 - Assistant ===
GLM-5/5.1/5.2 are all 744B MoE models — even 1-bit quantized they're 200-220GB. **Cannot run locally.** Only available as `:cloud` on Ollama. The best we can archive is `glm4:9b` (still downloading). Let me check remaining download status and start moving/cleaning.

=== MESSAGE 55 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 56 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 57 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 58 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 59 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 60 - Assistant ===
Still downloading. Let me check exact progress and free up space by removing superseded models.

=== MESSAGE 61 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 62 - Assistant ===
Freed ~9.6GB. Now 23GB free. Let me check if the SD card can hold Ollama models — exfat might have issues with symlinks, but we can copy blobs directly.

=== MESSAGE 63 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 64 - Assistant ===
The SD card is exfat (supports large files). Let me wait for the current downloads to finish, then move the larger models to SD card. Meanwhile, let me also check if we can download GGUF files directly from HuggingFace to the SD card as backup.

=== MESSAGE 65 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 66 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 67 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 68 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 69 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 70 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 71 - Assistant ===
Several are at the "verifying sha256 digest" stage — almost done. Let me wait a bit more and then check final status.

=== MESSAGE 72 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 73 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 74 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 75 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 76 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 77 - Assistant ===
All at sha256 verification — nearly done. Let me wait a bit longer.

=== MESSAGE 78 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 79 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 80 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 81 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 82 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 83 - Assistant ===
4 of 5 complete. gemma3:12b still verifying. Let me check the final inventory and start moving to SD card.

=== MESSAGE 84 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 85 - Assistant ===
8 models, 43GB in Ollama, 20GB free on NVMe, 24GB on SD card. gemma3:12b still downloading. Let me move the larger Chinese models to the SD card as archive copies. I'll create a model archive directory and copy the blobs.

=== MESSAGE 86 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 87 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 88 - Assistant ===
Now let me figure out which blobs belong to which models, then copy the larger ones to the SD card.

=== MESSAGE 89 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 90 - Assistant ===
Let me map blobs to models properly so we can move the right ones to the SD card.

=== MESSAGE 91 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 92 - Assistant ===
Now I can see the large blobs are unique per model. Let me move the 4 largest Chinese models (qwen2.5vl:7b, glm4:9b, qwen3:8b, deepseek-r1:7b — ~20GB total) to the SD card.

=== MESSAGE 93 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 94 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 95 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 96 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 97 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 98 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 99 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 100 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 101 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 102 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 103 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 104 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 105 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 106 - Assistant ===
All 4 models copied to SD card (20GB). Now let me remove them from NVMe to free space, and check if gemma3:12b finished.

=== MESSAGE 107 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 108 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 109 - Assistant ===
All downloads complete. Here's the current state:

**NVMe (40GB free)**:
- `gemma3:12b` (8.1G) — just finished
- `gemma3:4b` (3.3G) — could remove since we have 12b
- `qwen3:4b` (2.5G)
- `phi4-mini` (2.5G)
- `qwen3:1.7b` (1.4G)

**SD Card archive (20GB, 3.9GB free)**:
- `qwen2.5vl:7b` (6.0G) ✅
- `glm4:9b` (5.5G) ✅
- `qwen3:8b` (5.2G) ✅
- `deepseek-r1:7b` (4.7G) ✅

**GLM-5/5.1/5.2 finding**: All three are 744B MoE models (40B active). Even 1-bit quantized = 200-220GB. **Only available as `:cloud` on Ollama** — cannot be archived locally. These are exactly the models China is restricting. `glm4:9b` is the best local-runnable GLM we can archive.

Let me search for any smaller GLM variants we might be missing:

=== MESSAGE 110 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 111 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 112 - Assistant ===
Found `glm-4.7-flash` — a 30B-A3B MoE (30B total, 3B active) from Z.ai. This is locally runnable and would be a great addition. Let me check its size and also look at `glm-4.7`.

=== MESSAGE 113 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 114 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 115 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 116 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 117 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 118 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 119 - Assistant ===
Here's the full picture:

## GLM-5/5.1/5.2 — All Cloud-Only

All three are **744B MoE** models (40B active). Even 1-bit quantized = 200-220GB. Ollama only offers them as `:cloud` tags. **Cannot be archived locally.** These are exactly the models China is restricting — once the API gates close, they're gone.

## What I Found Instead: `glm-4.7-flash`

- **30B-A3B MoE** (30B total, 3B active) — locally runnable
- **19GB** (q4_K_M quantization) — strongest model in the 30B class per Z.ai
- From Z.ai — same company behind the restricted GLM-5 series
- 198K context window, MIT license
- Would fit on NVMe (40GB free) but it's a big chunk

`glm-4.7` (full version) is also cloud-only (744B).

## Current Inventory

**NVMe (40GB free, 23GB in Ollama)**:
| Model | Size | Status |
|---|---|---|
| `gemma3:12b` | 8.1 GB | ✅ Just downloaded |
| `gemma3:4b` | 3.3 GB | Redundant — have 12b |
| `qwen3:4b` | 2.5 GB | ✅ |
| `phi4-mini` | 2.5 GB | ✅ |
| `qwen3:1.7b` | 1.4 GB | ✅ |

**SD Card archive (3.9GB free, 20GB used)**:
| Model | Size | Status |
|---|---|---|
| `qwen2.5vl:7b` | 6.0 GB | ✅ Archived |
| `glm4:9b` | 5.5 GB | ✅ Archived |
| `qwen3:8b` | 5.2 GB | ✅ Archived |
| `deepseek-r1:7b` | 4.7 GB | ✅ Archived |

**Removed (superseded)**:
- `llama3.2:1b` → superseded by `qwen3:1.7b`
- `qwen2.5:3b` → superseded by `qwen3:4b`
- `qwen2.5:7b` → superseded by `qwen3:8b`
- `moondream` → superseded by `qwen2.5vl:7b`

=== MESSAGE 120 - Tool ===
[CORTEX_STEP_TYPE_ASK_USER_QUESTION]

=== MESSAGE 121 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 122 - Assistant ===
43GB free now. Pulling glm-4.7-flash:

=== MESSAGE 123 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 124 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 125 - Assistant ===
Downloading at 73 MB/s — should be done in ~4 minutes. Let me also update the strategic positioning doc with the GLM findings.

=== MESSAGE 126 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 127 - Tool ===
[CORTEX_STEP_TYPE_CODE_ACTION]

=== MESSAGE 128 - Assistant ===
Now let me check on the glm-4.7-flash download:

=== MESSAGE 129 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 130 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 131 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 132 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 133 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 134 - Tool ===
[CORTEX_STEP_TYPE_COMMAND_STATUS]

=== MESSAGE 135 - Tool ===
[CORTEX_STEP_TYPE_RUN_COMMAND]

=== MESSAGE 136 - Tool ===
[CORTEX_STEP_TYPE_TODO_LIST]

=== MESSAGE 137 - Assistant ===
All done. Here's the final state:

## Final Model Archive — 9 Models, ~58GB

**NVMe — Active (38GB, 25GB free)**:
| Model | Size | Origin |
|---|---|---|
| `glm-4.7-flash` | 19 GB | Z.ai (China) — 30B MoE, strongest 30B class |
| `gemma3:12b` | 8.1 GB | Google — multimodal |
| `qwen3:4b` | 2.5 GB | Alibaba (China) |
| `phi4-mini` | 2.5 GB | Microsoft — CPU-friendly |
| `qwen3:1.7b` | 1.4 GB | Alibaba (China) |

**SD Card — Cold storage (20GB, 3.9GB free)**:
| Model | Size | Origin |
|---|---|---|
| `qwen2.5vl:7b` | 6.0 GB | Alibaba (China) — VLM |
| `glm4:9b` | 5.5 GB | Z.ai (China) |
| `qwen3:8b` | 5.2 GB | Alibaba (China) |
| `deepseek-r1:7b` | 4.7 GB | DeepSeek (China) |

**6 of 9 models are Chinese** — highest priority given today's restriction news.

**GLM-5/5.1/5.2**: All 744B MoE, cloud-only on Ollama. Even 1-bit quantized = 200GB+. Cannot archive locally. These are the exact models that will disappear if China restricts foreign access.

**Removed 6 superseded models**: llama3.2:1b, qwen2.5:3b, qwen2.5:7b, moondream, gemma3:4b, and cancelled gpt-oss:20b + mistral-small3.1.

**Strategy doc updated**: `@/home/lucas/Desktop/WHITEMAGIC/docs/message_board/STRATEGIC_POSITIONING_2026-07-07.md` now includes the final inventory and GLM-5 cloud-only finding.