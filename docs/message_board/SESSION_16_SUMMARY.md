# Session 16 — WebSocket Server + Service Worker + ONNX Bundling (2026-05-26)

## Session Summary

**Start**: 13:35:59
**End**: 13:50:47
**Duration**: 14m 48s
**Objectives**: 3/3 completed

---

## Phase 1: Server-Side WebSocket Endpoint (13:35:59 → ~13:40, ~4m)

**Goal**: Implement `/sync` WebSocket handler in Python FastAPI server.

**Deliverables**:
- `core/scripts/wm_rest_server.py` — Added:
  - `SyncManager` class with:
    - Connection tracking per user (`user_id → [WebSocket]`)
    - Vector clock management for conflict resolution
    - Broadcast to all users (with exclude)
    - Direct message to specific user
  - `@app.websocket("/sync")` endpoint supporting:
    - Auth handshake (`sync_request` with `action: "auth"`)
    - Heartbeat for connection health
    - Memory operations: `memory_created`, `memory_updated`, `memory_deleted`
    - Association operations: `association_created`, `association_deleted`
    - Vector clock merge and increment
    - Database storage for synced memories
    - SSE event emission for sync operations
  - Helper functions: `_store_synced_memory`, `_update_synced_memory`, `_delete_synced_memory`
  - `GET /sync/status` endpoint for monitoring

**Architecture**:
```
Browser WSSyncClient  ──ws://host/sync──▶  FastAPI SyncManager
     │                                          │
     ├─ auth (userId)                    ├─ track connections
     ├─ memory_created                   ├─ store in SQLite
     ├─ memory_updated                   ├─ broadcast to others
     └─ heartbeat                        └─ vector clock merge
```

**Test**: Import verified, server loads without errors.

---

## Phase 2: Service Worker + PWA Install (~13:40 → ~13:46, ~6m)

**Goal**: Cache WASM/ONNX assets, add "Add to Home Screen" prompt.

**Deliverables**:
- `apps/site/next.config.mjs` — Updated:
  - Added WASM module caching (`/wasm/*.wasm`, `/wasm/*.js`) — 1 year TTL
  - Added ONNX model caching (`/models/*.onnx`, `/models/*.bin`) — 1 year TTL
  - Added sql.js CDN caching (jsdelivr) — 1 year TTL
  - Added ONNX Runtime Web CDN caching — 1 year TTL
  - Added WebSocket proxy rewrite (`/sync` → `http://127.0.0.1:8770/sync`)
- `apps/site/components/PWAInstallPrompt.tsx` — New component:
  - Captures `beforeinstallprompt` event
  - Shows install prompt after 2 visits or 30 seconds
  - Dismissable (7-day cooldown)
  - Shows feature badges: "Works offline", "SQLite OPFS", "ONNX embeddings"
- Updated `/app` page to include `PWAInstallPrompt`

**Service Worker Cache Strategy**:
| Asset Type | Strategy | TTL | Cache Name |
|------------|----------|-----|------------|
| WASM modules | CacheFirst | 1 year | wasm-modules |
| ONNX models | CacheFirst | 1 year | onnx-models |
| sql.js WASM | CacheFirst | 1 year | sqljs-wasm |
| ONNX Runtime | CacheFirst | 1 year | onnxruntime-wasm |
| API calls | NetworkFirst | 24h | api-cache |
| Images | CacheFirst | 30 days | static-images |
| Fonts | CacheFirst | 1 year | google-fonts-cache |

---

## Phase 3: ONNX Model Bundling (~13:46 → 13:50:47, ~4m)

**Goal**: Bundle MiniLM model locally instead of CDN dependency.

**Deliverables**:
- `apps/site/public/models/model_quantized.onnx` — 22MB quantized model downloaded
- `scripts/download-onnx-model.sh` — Download script for model retrieval
- `apps/site/lib/onnx-embedding.ts` — Updated:
  - `MODEL_CONFIG.url` → `/models/model_quantized.onnx` (local)
  - `MODEL_CONFIG.cdnUrl` → HuggingFace CDN (fallback)
  - Init logic: tries local first, falls back to CDN if not found

**Model Details**:
- **Model**: all-MiniLM-L6-v2 (quantized)
- **Size**: 22MB
- **Dimensions**: 384
- **Source**: HuggingFace (Xenova)
- **Format**: ONNX (INT8 quantized)

**Load Flow**:
```
1. Check /models/model_quantized.onnx (HEAD request)
2. If exists → load from local (instant, offline-capable)
3. If not → fall back to HuggingFace CDN
4. Cache via service worker for future offline use
```

---

## Final State

| Component | Before | After |
|-----------|--------|-------|
| WebSocket Server | None | `/sync` endpoint with SyncManager |
| Service Worker Caching | Basic | + WASM, ONNX, sql.js, ONNX Runtime |
| PWA Install Prompt | None | Custom component with visit tracking |
| ONNX Model | CDN only | Local bundle (22MB) + CDN fallback |
| WebSocket Proxy | None | Next.js rewrite `/sync` → API |
| Sync Status Endpoint | None | `GET /sync/status` |

## Build Status

- **PWA**: ✅ Builds successfully (62 pages)
- **TypeScript**: ✅ No errors
- **Tests**: 2,144 passed, 2 pre-existing failures (forecasting thresholds), 14 skipped

## Architecture Update

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (PWA)                                                  │
│                                                                 │
│  Service Worker                                                 │
│    ├─ Cache: WASM (178KB), ONNX (22MB), sql.js, ONNX Runtime    │
│    ├─ Cache: API responses (24h TTL)                            │
│    └─ Offline: Full app shell + assets                          │
│                                                                 │
│  WASM Runtime + SQLite OPFS + ONNX Embedding                    │
│    └─ Model: /models/model_quantized.onnx (local)               │
│                                                                 │
│  WebSocket Sync Client                                          │
│    └─ ws://host/sync ──proxy──▶ FastAPI /sync                   │
│                                                                 │
│  PWA Install Prompt                                             │
│    └─ "Add to Home Screen" after 2 visits                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Server (Python)                                        │
│                                                                 │
│  WebSocket /sync                                                │
│    ├─ SyncManager: user connections, vector clocks              │
│    ├─ Broadcast: memory ops to all users                        │
│    ├─ Store: synced memories in SQLite                          │
│    └─ SSE: emit sync_operation events                           │
│                                                                 │
│  REST API                                                       │
│    ├─ /sync/status — connected users, vector clocks             │
│    └─ All existing endpoints unchanged                          │
└─────────────────────────────────────────────────────────────────┘
```

## Next Steps (for later tonight or future sessions)

1. **Execute Hetzner deployment** — All artifacts ready, just needs VPS
2. **Background sync** — Use Service Worker BackgroundSync API for offline queue
3. **Conflict resolution UI** — Show dialog when vector clocks diverge
4. **Presence indicators** — Show other connected users in the galaxy
5. **End-to-end encryption** — Encrypt sync payloads for privacy

---

*Session complete. All 3 objectives delivered in 14m 48s.*
