# WhiteMagic Security Update — v23.0.0 Architecture

**Date**: 2026-05-26
**Status**: Design Document (Implementation In Progress — Session 17)
**Target**: Sessions 17–19
**Session 17 Start**: 15:33:51

---

## 1.1 AI Review Notes (2026-05-26, Session 17)

**Scope correction**: Session 17 split into hardening-only. Presence deferred to separate session.
**Auth correction**: HMAC token auth replaced with X25519 key-exchange-as-auth. The key exchange *is* the authentication.
**Replay protection**: Added nonce field to all WebSocket messages. Ed25519 signatures alone don't prevent replay.
**Rate limiting**: `slowapi` decorator removed — WebSocket rate limiting uses token bucket inside handler.
**Coordinate perturbation**: Flagged for review — epsilon=0.1 may corrupt galactic zone boundaries. Alternative: perturb only for server storage, maintain true coords client-side with zone validation on the client.
**Presence granularity**: Cursor quantization changed from 0.1 units to whole galactic bands.

---

## 2. Threat Model

### Assets to Protect

| Asset | Sensitivity | Attack Surface |
|-------|-------------|----------------|
| Memory content | **Critical** | WebSocket, REST API, server disk, backups |
| Embeddings (vectors) | **High** | Semantic reconstruction attacks |
| Metadata (garden, type, tags) | **Medium** | Behavioral profiling, activity patterns |
| Holographic coordinates | **Medium** | Semantic relationship inference |
| Access patterns (counts, timestamps) | **Medium** | Usage frequency, importance inference |
| User identity | **High** | WebSocket auth, session tracking |
| Associations (edges) | **High** | Knowledge graph reconstruction |

### Adversaries

| Adversary | Capability | Goal |
|-----------|-----------|------|
| Network observer | Packet sniffing, MITM | Intercept sync payloads, impersonate users |
| Compromised server | Full disk access, DB access | Read all stored data, modify sync state |
| Malicious admin | Server access, logs | Profile users, extract metadata patterns |
| Other users (multi-user) | Shared server, broadcast channel | Access other users' memories, spoof identity |
| Browser compromise | XSS, malicious extensions | Extract keys from IndexedDB, intercept DOM |

---

## 2. Current Security Posture

### What's Working

| Control | Status | Notes |
|---------|--------|-------|
| OPFS isolation | ✅ Good | Browser-enforced per-origin |
| TLS (Caddy) | ✅ Good | Automatic HTTPS |
| WASM sandbox | ✅ Good | No filesystem access |
| SQLite WAL mode | ✅ Good | No partial writes |

### What's Missing

| Control | Status | Risk |
|---------|--------|------|
| CORS | ❌ `["*"]` | Any origin can call API |
| WebSocket auth | ❌ Trusts client `userId` | Trivial identity spoofing |
| Payload encryption | ❌ Plaintext | Server sees all content |
| Rate limiting | ❌ None | DoS, brute force |
| Input validation | ⚠️ Partial | Pydantic on REST, not WebSocket |
| Audit logging | ❌ None | No tamper evidence |
| Key management | ❌ None | No E2EE yet |

---

## 3. Metadata & Coordinate Anonymity

### The Problem

Metadata and holographic coordinates are currently stored in plaintext because they're "needed for routing and visualization." But they leak significant information:

| Field | Leakage | Example |
|-------|---------|---------|
| `garden` | Categorization patterns | "truth_garden" → user values epistemology |
| `memory_type` | Usage patterns | "dream" → user does dream cycles |
| `access_count` | Importance/frequency | 150 accesses → critical knowledge |
| `created_at` | Activity timeline | 3AM timestamps → insomnia pattern |
| `holographic_coords` | Semantic relationships | Proximity = similarity → knowledge graph |
| `galactic_distance` | Core vs. peripheral | 0.05 → central belief system |

An attacker with server access can reconstruct a user's **cognitive topology** without ever reading memory content.

### Solution: Layered Obfuscation

#### 3.1 Opaque Routing Tags

Replace semantic labels with opaque identifiers that only the client can map:

```python
# Client-side mapping (never sent to server)
GARDEN_MAP = {
    "wisdom_garden": "g_7a3f",
    "truth_garden": "g_9b2c",
    "dream_garden": "g_4e1d",
    # ... 28 gardens → opaque IDs
}

TYPE_MAP = {
    "long_term": "t_1",
    "dream": "t_2",
    "ephemeral": "t_3",
    # ...
}
```

**Server stores**: `garden: "g_7a3f"`, `type: "t_2"`
**Server can**: Route, filter, aggregate
**Server cannot**: Know semantic meaning

**Implementation**:
- Deterministic mapping: `opaque_id = HMAC-SHA256(secret_salt, semantic_label)[:6]`
- Salt is user-specific, stored in IndexedDB
- Server sees consistent opaque IDs for routing but cannot reverse them

#### 3.2 Coordinate Perturbation (Differential Privacy)

Add deterministic noise to holographic coordinates before server storage:

```python
def perturb_coords(coords: tuple, user_salt: bytes, epsilon: float = 0.1) -> tuple:
    """Add Laplace noise to coordinates.
    
    epsilon: privacy budget. Lower = more noise, less accuracy.
    Server sees perturbed coords; client knows true coords locally.
    """
    noise = []
    for i, c in enumerate(coords):
        # Deterministic noise per coordinate (same input → same noise)
        seed = HMAC-SHA256(user_salt, f"coord_{i}_{hash(coords)}")
        laplace_sample = inverse_cdf_laplace(int.from_bytes(seed[:8], 'big'))
        noise.append(c + laplace_sample * epsilon)
    return tuple(noise)
```

**Properties**:
- Server stores perturbed coords (useless for semantic inference)
- Client stores true coords locally (accurate visualization)
- Deterministic: same coords → same perturbation (enables dedup)
- Epsilon = 0.1 → ~90% of coordinates within 0.1 units of true position

**Trade-off**: Server-side galaxy visualization is approximate. Client-side is exact.

#### 3.3 k-Anonymity Clustering for Server-Side Galaxy

If server-side visualization is needed, use k-anonymity:

```python
def cluster_coords_for_server(coords: list[tuple], k: int = 5) -> list[dict]:
    """Group coordinates into clusters of size ≥ k.
    
    Server only sees cluster centroids, not individual positions.
    """
    clusters = DBSCAN(eps=0.2, min_samples=k).fit(coords)
    result = []
    for cluster_id in set(clusters.labels_):
        members = [coords[i] for i in range(len(coords)) if clusters.labels_[i] == cluster_id]
        centroid = tuple(sum(c[d] for c in members) / len(members) for d in range(5))
        result.append({
            "cluster_id": cluster_id,
            "centroid": centroid,
            "member_count": len(members),
            "radius": max(distance(centroid, m) for m in members),
        })
    return result
```

**Server sees**: "Cluster 7 has 12 memories at position (0.3, 0.1, ...)"
**Server cannot**: Know which specific memories are in the cluster

#### 3.4 Timestamp Granularity Reduction

Reduce timestamp precision to prevent activity pattern analysis:

| Original | Anonymized | Precision Loss |
|----------|-----------|----------------|
| `2026-05-26T14:32:17.482Z` | `2026-05-26T14:00:00Z` | 1 hour |
| `2026-05-26T14:32:17.482Z` | `2026-05-26T12:00:00Z` | 4 hours |
| `2026-05-26T14:32:17.482Z` | `2026-05-26T00:00:00Z` | 1 day |

**Recommendation**: 4-hour granularity for server storage. Client stores exact timestamps locally.

#### 3.5 Access Count Bucketing

Replace exact counts with logarithmic buckets:

```python
def bucket_access_count(count: int) -> str:
    if count == 0: return "b_0"
    if count <= 3: return "b_1"      # 1-3
    if count <= 10: return "b_2"     # 4-10
    if count <= 30: return "b_3"     # 11-30
    if count <= 100: return "b_4"    # 31-100
    return "b_5"                      # 100+
```

**Server sees**: `access_count: "b_3"`
**Server cannot**: Distinguish between 11 and 30 accesses

---

## 4. End-to-End Encryption Architecture

### 4.1 Cryptographic Primitives

| Primitive | Algorithm | Purpose |
|-----------|-----------|---------|
| Asymmetric encryption | X25519 (ECDH) | Key exchange |
| Symmetric encryption | AES-256-GCM | Payload encryption |
| Signing | Ed25519 | Message authentication |
| Key derivation | PBKDF2-HMAC-SHA256 (100k iterations) | Password → KEK |
| Key wrapping | AES-KW (RFC 5649) | KEK → encrypt DEK |
| Hashing | SHA-256 | Opaque ID generation |

### 4.2 Key Hierarchy

```
User Password
    │
    ▼ (PBKDF2, 100k iterations)
KEK (Key Encryption Key) — 256 bits
    │
    ▼ (AES-KW unwrap)
DEK (Data Encryption Key) — 256 bits
    │
    ├──► Content DEK (AES-GCM for memory content)
    ├──► Embedding DEK (AES-GCM for vectors)
    └──► Association DEK (AES-GCM for edges)
    │
    ▼ (X25519)
Shared Secret (per-peer) — 256 bits
    │
    ▼ (HKDF)
Sync Key (AES-GCM for sync payloads)
```

### 4.3 Key Storage

| Key | Location | Encryption | Backup |
|-----|----------|-----------|--------|
| KEK | Never stored | Derived from password | User memorizes password |
| DEK | IndexedDB | AES-KW(KEK, DEK) | Export as encrypted JSON |
| Ed25519 private key | IndexedDB | AES-KW(KEK, key) | Export as encrypted JSON |
| X25519 private key | IndexedDB | AES-KW(KEK, key) | Export as encrypted JSON |
| Public keys | Server (plaintext) | None | N/A |

### 4.4 Encryption Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Client A (Sender)                                          │
│                                                             │
│  1. Generate memory: {content, garden, coords, embedding}   │
│  2. Encrypt content: AES-GCM(Content DEK, content)          │
│  3. Encrypt embedding: AES-GCM(Embedding DEK, embedding)    │
│  4. Perturb coords (Section 3.2)                            │
│  5. Opaque tags (Section 3.1)                               │
│  6. Sign: Ed25519(private_key, hash(payload))               │
│  7. Send to server: {encrypted_content, encrypted_embedding,│
│     opaque_garden, perturbed_coords, signature}             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Server (Blind Relay)                                       │
│                                                             │
│  1. Verify signature (using stored public key)              │
│  2. Store encrypted blobs                                   │
│  3. Broadcast to other clients (encrypted)                  │
│  4. Cannot decrypt any content                              │
│  5. Cannot reconstruct semantic relationships               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Client B (Receiver)                                        │
│                                                             │
│  1. Receive encrypted payload                               │
│  2. Verify signature (using sender's public key)            │
│  3. Decrypt: AES-GCM(Content DEK, encrypted_content)        │
│  4. Decrypt: AES-GCM(Embedding DEK, encrypted_embedding)    │
│  5. Restore true coords (client-side mapping)               │
│  6. Render in galaxy with accurate positions                │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 What Stays Plaintext (and Why)

| Field | Reason | Mitigation |
|-------|--------|------------|
| `memory_id` | Needed for dedup, references | UUID, no semantic meaning |
| `opaque_garden` | Routing, filtering | HMAC-based, irreversible |
| `opaque_type` | Routing, filtering | HMAC-based, irreversible |
| `perturbed_coords` | Server-side clustering | Differential privacy noise |
| `bucketed_access` | Cache invalidation | Logarithmic buckets |
| `granular_timestamp` | Sync ordering | 4-hour granularity |
| `signature` | Authentication | Ed25519, no content leakage |

### 4.6 Key Exchange Protocol

```
1. Client connects → sends {user_id, public_keys: {ed25519, x25519}}
2. Server stores public keys, returns {active_users: [{user_id, public_keys}]}
3. Client derives shared secrets: ECDH(my_x25519_private, peer_x25519_public)
4. Client derives sync keys: HKDF(shared_secret, "whitemagic-sync-v1")
5. All subsequent payloads encrypted with sync key
```

**Re-keying**: Every 24 hours or 10,000 messages (whichever comes first).

---

## 5. Presence Indicators (Secure Design)

### 5.1 Threat Model for Presence

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stalking (who's online when) | Privacy violation | Opt-in presence, hide status |
| Activity inference (idle time) | Behavioral profiling | Coarse-grained status only |
| Cursor position tracking | Spatial privacy | Quantized positions, opt-in |
| View tracking (what they're looking at) | Content inference | Opaque view IDs, opt-in |

### 5.2 Presence Data Model

```python
@dataclass
class PresenceState:
    user_id: str                    # Opaque user ID
    status: Literal["active", "idle", "away"]
    status_since: datetime          # When status changed
    current_view: str | None        # Opaque view ID (e.g., "galaxy", "memory/abc")
    editing_node: str | None        # Opaque node ID (only if explicitly shared)
    cursor_quantized: tuple[int, int, int] | None  # Quantized to 0.1 units
    last_heartbeat: datetime
    incognito: bool                 # User opt-out of presence
```

### 5.3 Privacy Controls

| Setting | Default | Effect |
|---------|---------|--------|
| `presence_enabled` | `true` | Show/hide from others |
| `show_cursor` | `false` | Share quantized cursor position |
| `show_editing` | `false` | Share which node is being edited |
| `show_view` | `true` | Share current view (opaque ID) |
| `status_granularity` | `"coarse"` | `fine`: exact seconds, `coarse`: 5-min buckets |

### 5.4 Presence Broadcast Protocol

```
Client → Server (every 10s):
{
  "type": "presence_update",
  "user_id": "user_abc",
  "status": "active",
  "current_view": "galaxy",
  "cursor_quantized": [3, 2, 1],  // Quantized to 0.1 units
  "incognito": false
}

Server → All Clients (on change):
{
  "type": "presence_broadcast",
  "users": [
    {"user_id": "user_abc", "status": "active", "view": "galaxy"},
    {"user_id": "user_def", "status": "idle", "view": null}
  ]
}
```

### 5.5 Presence Visualization

```
┌──────────────────────────────────────────────┐
│  Galaxy View                                 │
│                                              │
│  Users Online (2)                            │
│  🟢 You (active)                             │
│  🟡 Aria (idle 3m) — viewing galaxy          │
│                                              │
│  [Aria's avatar] — quantized position        │
│  └─ Only shown if aria.show_cursor = true    │
└──────────────────────────────────────────────┘
```

---

## 6. Immediate Security Hardening (Session 17)

These are **non-negotiable** before any public deployment:

### 6.1 CORS Restriction

```python
# Before
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# After
ALLOWED_ORIGINS = [
    "https://whitemagic.dev",
    "https://app.whitemagic.dev",
    "http://localhost:3002",  # Dev only
]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, ...)
```

### 6.2 WebSocket Auth via X25519 Key Exchange

```python
# Client generates X25519 keypair on first connect
# Sends: {user_id, x25519_public_key, timestamp, nonce}
# Server stores public key, returns server_x25519_public_key + nonce
# Both derive shared secret: ECDH(private, peer_public)
# All subsequent messages authenticated via derived key

# Server-side verification
@app.websocket("/sync")
async def sync_websocket(ws: WebSocket):
    await ws.accept()
    
    # Auth handshake
    handshake = await ws.receive_json()
    user_id = handshake.get("user_id")
    client_public = handshake.get("x25519_public_key")
    client_nonce = handshake.get("nonce")
    timestamp = handshake.get("timestamp")
    
    if not all([user_id, client_public, client_nonce, timestamp]):
        await ws.close(code=4001, reason="Missing auth fields")
        return
    
    # Verify timestamp not expired (5 min window)
    if abs(time.time() - float(timestamp)) > 300:
        await ws.close(code=4002, reason="Timestamp expired")
        return
    
    # Verify nonce not reused (prevent replay)
    if is_nonce_replayed(client_nonce):
        await ws.close(code=4003, reason="Nonce replayed")
        return
    
    # Derive shared secret
    server_private = x25519.PrivateKey.generate()
    server_public = server_private.public_key()
    shared_secret = server_private.exchange(x25519.PublicKey.from_base64(client_public))
    
    # Send server public key + nonce back
    await ws.send_json({
        "type": "auth_ack",
        "server_public_key": server_public.to_base64(),
        "server_nonce": generate_nonce(),
    })
    
    # Store session with derived keys
    session_key = HKDF(shared_secret, info=b"whitemagic-sync-v1")
    sync_manager.register_session(user_id, ws, session_key)
```

**Why this is better than HMAC**: No shared secret needs to be stored in the browser. The X25519 keypair is generated per-session. The public key serves as the identity. Replay is prevented by nonces + timestamp window.

### 6.3 Rate Limiting (WebSocket Token Bucket)

```python
# slowapi doesn't work for long-lived WebSocket connections.
# Use an in-memory token bucket per session.

class TokenBucket:
    def __init__(self, rate: float, capacity: int = 10):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
    
    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

# Per-user buckets stored in SyncManager
# Default: 30 messages/minute, burst capacity 10
```

### 6.4 Input Validation (WebSocket)

```python
class SyncMessage(BaseModel):
    type: Literal["sync_request", "memory_created", "memory_updated", ...]
    userId: str = Field(..., min_length=8, max_length=64)
    timestamp: float = Field(..., gt=0)
    nonce: str = Field(..., min_length=16, max_length=64)  # Replay protection
    vectorClock: dict[str, int] = Field(..., max_items=100)
    payload: dict | None = None

# In WebSocket handler:
try:
    msg = SyncMessage.model_validate(data)
except ValidationError as e:
    await ws.send_json({"type": "error", "error": str(e)})
    return

# Verify nonce not reused (in-memory LRU cache, 5-min TTL)
if nonce_seen(msg.nonce):
    await ws.send_json({"type": "error", "error": "Replay detected"})
    await ws.close(code=4003, reason="Nonce replayed")
    return
```

### 6.5 CSP Headers (Caddyfile)

```
Caddyfile additions:
header {
    Content-Security-Policy "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self' ws: wss:; style-src 'self' 'unsafe-inline';"
    X-Content-Type-Options "nosniff"
    X-Frame-Options "DENY"
    Referrer-Policy "strict-origin-when-cross-origin"
    Permissions-Policy "camera=(), microphone=(), geolocation=()"
}
```

---

## 7. Implementation Roadmap

### Session 17: Security Hardening (~2h)

| Task | Effort | Dependencies |
|------|--------|--------------|
| CORS restriction | 15min | None |
| WebSocket X25519 auth | 45min | `cryptography` install |
| Token bucket rate limiter | 30min | None |
| Input validation + nonce replay check | 30min | Pydantic models |
| CSP headers | 15min | Caddyfile edit |
| Audit logging stub | 30min | None |

**Presence indicators deferred to separate session.**

### Session 18: E2EE Foundation (~3h)

| Task | Effort | Dependencies |
|------|--------|--------------|
| WebCrypto key generation | 45min | None |
| Python cryptography setup | 30min | `cryptography` install |
| Key exchange protocol | 1h | WebSocket auth |
| AES-GCM encrypt/decrypt | 45min | Key exchange |
| IndexedDB key storage | 45min | Key generation |
| Password-based unlock | 30min | Key storage |

### Session 19: E2EE Integration + Metadata Anonymity (~3h)

| Task | Effort | Dependencies |
|------|--------|--------------|
| Opaque routing tags | 30min | E2EE foundation |
| Coordinate perturbation | 45min | E2EE foundation |
| Timestamp granularity | 15min | Opaque tags |
| Access count bucketing | 15min | Opaque tags |
| Encrypted sync payloads | 1h | AES-GCM |
| Key export/backup | 45min | Key storage |
| End-to-end testing | 30min | All above |

---

## 8. Security Checklist (Pre-Deployment)

### Session 17 (Hardening)
- [ ] CORS restricted to specific origins
- [ ] WebSocket X25519 key-exchange auth implemented
- [ ] Nonce replay protection active
- [ ] Token bucket rate limiter on WebSocket messages
- [ ] Input validation on WebSocket messages (Pydantic)
- [ ] CSP headers configured
- [ ] HTTPS enforced (Caddy auto-HTTPS)
- [ ] Audit logging stub active

### Session 18 (E2EE)
- [ ] E2EE key exchange working
- [ ] AES-GCM encrypt/decrypt for payloads
- [ ] IndexedDB key storage
- [ ] Password-based unlock
- [ ] Key export/backup functional

### Session 19 (Metadata Anonymity)
- [ ] Presence opt-in by default
- [ ] Metadata anonymized (opaque tags)
- [ ] Coordinates perturbed (differential privacy) — **review zone boundary impact**
- [ ] Timestamps granular (4-hour buckets)
- [ ] Access counts bucketed (logarithmic)
- [ ] No secrets in code or logs
- [ ] Penetration test completed

---

## 9. Open Questions

1. **Should presence be opt-in or opt-out?** Recommendation: opt-in by default.
2. **Should the server store any plaintext metadata for indexing?** Recommendation: no. Use opaque tags + client-side search.
3. **Should we support multi-device key sync?** Recommendation: yes, via encrypted key export/import.
4. **Should we add zero-knowledge proof for presence?** Recommendation: not yet. Overkill for v23.
5. **Should we encrypt holographic coords or just perturb them?** Recommendation: perturb for server-side clustering, encrypt for storage. Client stores true coords.

---

*This document is a living artifact. Update as implementation progresses.*
