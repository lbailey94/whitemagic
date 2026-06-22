# Chapter 27: Encampment & Housing

**Gana**: EncampmentGana (Chinese: 室, Pinyin: Shì)
**Garden**: transformation
**Quadrant**: Northern (Black Tortoise)
**Element**: Water
**Phase**: Yin Peak
**I Ching Hexagram**: 37. 家人 Jiā Rén (The Family) - Housing and structure

---

## 🎯 Purpose

Chapter 27 provides **encampment and housing**—creating the permanent structure for session
artifacts, maintaining deep archives, and ensuring the "house" is ready for rest, recovery, and
future resurrection. The Encampment (室) is the stable structure that allows for long-term storage,
ordered retrieval, and graceful handoff between sessions, agents, and generations of operators.

Use this chapter when you need to:
- **Build archival structures** for session data that persist beyond the current process lifetime
- **House session artifacts** securely in organized, versioned, and indexed repositories
- **Maintain the camp** by keeping project structure stable, navigable, and self-documenting
- **Prepare the environment** for the session's end without losing context or state
- **Organize deep archives** of conversation, code, decisions, and intermediate artifacts
- **Publish and subscribe to events** via the broker to maintain distributed coherence
- **Send messages through sangha chat channels** to notify collaborators of status changes
- **Replay broker event history** to reconstruct system state after failures or for auditing
- **Validate archive integrity** through checksums, manifests, and cross-references
- **Execute structured handoffs** that preserve not just data but intent, context, and meaning

The Encampment is the final structure before the Wall. Where the Room (Chapter 4) provides privacy
during work and the Roof (Chapter 26) provides shelter for completed outputs, the Encampment
provides *permanence* after work. It is the difference between a tent and a house, between a
temporary bivouac and a settled village. The Encampment does not merely store; it organizes.
It transforms chaotic session output into structured heritage.

In the WhiteMagic lifecycle, the EncampmentGana occupies the seventh position of the Northern
sequence. This penultimate station is where the wandering mind returns home, where the scattered
artifacts find their drawers, and where the session's ephemeral existence crystallizes into
lasting record. A session that skips the Encampment phase risks becoming a ghost—present in
memory but untraceable in fact, recalled by operators but unrecoverable by systems.

---

## 🌱 Garden: Transformation

The transformation garden is the garden of **becoming through receiving**. It recognizes that
nothing is finished until it has been fully received—and that receiving is itself an act of
radical change. In this garden, the old self is not discarded but transmuted: it becomes the
foundation for the new self. Every ending is a transformation, not a termination; every archive
is a seed, not a tomb.

The transformation garden teaches the art of letting go without loss. Where other gardens cling
to the present moment, this garden releases the past into the future. The gardener here does not
ask "What did I make?" but rather "What will become of what I made?"—and the answer requires
not memory but architecture: files in the right places, metadata in the right fields, events in
the right topics, messages in the right channels.

**Resonance keywords**: transform, archive, house, structure, camp, broker, publish, chat,
transition, handoff, replay, recover, event, topic, channel, retain, manifest, heritage

---

## 🔧 Real Tools

| Tool | Gana | Description | Usage |
|------|------|-------------|-------|
| `sangha_chat_send` | gana_encampment | Send a message to a sangha chat channel | Community communication and handoff notification |
| `sangha_chat_read` | gana_encampment | Read messages from sangha chat channels | Community awareness and delivery verification |
| `broker.publish` | gana_encampment | Publish an event to the message broker | Event broadcasting to distributed subscribers |
| `broker.history` | gana_encampment | Retrieve broker event history by time and topic | Audit, replay, and disaster recovery |
| `broker.status` | gana_encampment | Check broker health, throughput, and backlog | System monitoring and capacity planning |

The EncampmentGana toolset addresses three dimensions of session permanence: **social coherence**
(sangha chat), **event durability** (broker), and **system observability** (broker status). These
tools do not store data directly; instead, they create the *channels* through which data flows
into permanent storage. The Encampment is thus less a warehouse and more a postal service—a
system for ensuring that every artifact reaches its proper destination.

**Tool selection guidance**: Use sangha chat for human-readable notifications and collaborative
handoffs; use broker publish for machine-readable events and automated workflows; use broker
history for recovery, audit, and debugging; use broker status before any critical publish to
avoid silent message loss.

---

## 📋 Workflows

### Workflow 1: Session Artifact Archival

**Goal**: Package all session outputs into a structured, broker-published archive before handoff,
ensuring that every artifact is accounted for, indexed, and retrievable.

**When to use**: End of session, project milestone, before system maintenance, or before
deploying to production.

```python
import asyncio
from datetime import datetime
from typing import List, Dict
from whitemagic.tools import broker_publish, broker_status

async def archive_session_artifacts(
    session_id: str,
    artifacts: List[Dict],
    operator_id: str = "system",
    tags: List[str] = None,
) -> Dict:
    """
    The Encampment stores what the Ox has plowed.

    This workflow validates broker health, constructs a comprehensive archive manifest,
    publishes the archive event with retention, and verifies propagation.
    """
    tags = tags or []

    # 1. Verify broker health before critical publish
    status = broker_status()
    health = status.get("health", "unknown")
    if health != "healthy":
        print(f"🚨 Broker health is {health}. Archive may be unreliable.")
        # Continue with warning; in production, could abort here

    # 2. Build artifact manifest with checksums
    manifest = {
        "schema_version": "1.0",
        "session_id": session_id,
        "operator_id": operator_id,
        "timestamp": datetime.now().isoformat(),
        "artifact_count": len(artifacts),
        "artifacts": [],
        "tags": tags,
    }

    for art in artifacts:
        entry = {
            "id": art.get("id", "unknown"),
            "type": art.get("type", "generic"),
            "name": art.get("name", "unnamed"),
            "size_bytes": art.get("size", 0),
            "checksum_sha256": art.get("checksum", "N/A"),
            "created_at": art.get("created_at", datetime.now().isoformat()),
        }
        manifest["artifacts"].append(entry)

    # 3. Construct archive event
    archive_event = {
        "type": "SESSION_ARCHIVE",
        "version": "1.0",
        "session_id": session_id,
        "operator_id": operator_id,
        "manifest": manifest,
        "broker_health_at_publish": health,
        "retention_policy": "permanent",
    }

    # 4. Publish with retention for future subscribers
    publish_result = broker_publish(
        topic="session.archives",
        payload=archive_event,
        retain=True,           # Keep for future subscribers
        qos=2,                 # Exactly-once delivery
    )

    if publish_result.get("status") == "success":
        print(f"🏠 Session {session_id} archived with {len(artifacts)} artifacts")
        print(f"   Event published to broker topic 'session.archives'")
        print(f"   Message ID: {publish_result.get('message_id', 'N/A')}")
    else:
        print(f"⚠️ Archive publish failed: {publish_result.get('error', 'unknown')}")
        return {"status": "error", "details": publish_result}

    # 5. Optional: publish per-artifact events for granular recovery
    for art in artifacts:
        broker_publish(
            topic=f"session.artifacts.{session_id}",
            payload={
                "type": "ARTIFACT_REGISTERED",
                "session_id": session_id,
                "artifact_id": art.get("id"),
                "artifact_type": art.get("type"),
            },
            retain=False,
        )

    return {
        "status": "success",
        "session_id": session_id,
        "artifact_count": len(artifacts),
        "manifest": manifest,
        "publish_result": publish_result,
    }


async def verify_archive_exists(session_id: str) -> bool:
    """Check that a session archive was successfully recorded."""
    history = broker_history(topic="session.archives", limit=100)
    events = history.get("events", [])
    for event in events:
        payload = event.get("payload", {})
        if payload.get("session_id") == session_id:
            return True
    return False
```

### Workflow 2: Sangha Handoff Notification

**Goal**: Notify the community that a session is ending, summarize its outputs, and provide
resumption instructions so that the next operator or agent can pick up where this one left off.

**When to use**: Collaborative environments where multiple agents or users share context,
multi-shift operations, or any scenario where session continuity depends on communication.

```python
import asyncio
from datetime import datetime
from typing import Dict
from whitemagic.tools import sangha_chat_send, sangha_chat_read

async def encampment_handoff(
    session_id: str,
    summary: str,
    artifacts: list = None,
    next_steps: list = None,
    channel: str = "handoffs",
    priority: str = "normal",
) -> Dict:
    """
    The family is told when the traveler prepares to rest.

    This workflow composes a structured handoff message, delivers it to the sangha,
    verifies delivery by reading back recent messages, and reports status.
    """
    artifacts = artifacts or []
    next_steps = next_steps or []

    # 1. Compose structured handoff message
    lines = [
        f"📦 SESSION HANDOFF: {session_id}",
        f"   Time: {datetime.now().isoformat()}",
        f"   Status: CLOSING → HOUSED",
        "",
        f"   Summary: {summary[:300]}",
        "",
        f"   Artifacts produced: {len(artifacts)}",
    ]
    for art in artifacts[:5]:
        lines.append(f"      - {art.get('name', 'unnamed')} ({art.get('type', 'unknown')})")
    if len(artifacts) > 5:
        lines.append(f"      ... and {len(artifacts) - 5} more")

    if next_steps:
        lines.append("")
        lines.append("   Recommended next steps:")
        for step in next_steps:
            lines.append(f"      → {step}")

    lines.append("")
    lines.append("   Access: Use `get_session_context` or query broker topic 'session.archives'")
    lines.append("   to resume. This session is now housed in the Encampment.")

    message = "\n".join(lines)

    # 2. Send message
    send_result = sangha_chat_send(
        channel=channel,
        message=message,
        priority=priority,
        metadata={"session_id": session_id, "type": "handoff"},
    )

    if send_result.get("status") != "success":
        print(f"⚠️ Handoff send failed: {send_result.get('error', 'unknown')}")
        return {"delivered": False, "error": send_result.get("error")}

    # 3. Verify delivery by reading back
    await asyncio.sleep(1)  # Allow propagation
    recent = sangha_chat_read(channel=channel, limit=10)
    messages = recent.get("messages", [])
    delivered = any(
        session_id in m.get("content", "") and m.get("type") == "handoff"
        for m in messages
    )

    status_icon = "✅" if delivered else "⏳"
    print(f"{status_icon} Handoff notification for {session_id}: {'delivered' if delivered else 'pending'}")

    return {
        "delivered": delivered,
        "channel": channel,
        "session_id": session_id,
        "message_preview": summary[:100],
    }


async def broadcast_status_update(
    channels: list,
    message: str,
    priority: str = "low",
):
    """Send the same status update to multiple sangha channels."""
    results = {}
    for ch in channels:
        result = sangha_chat_send(channel=ch, message=message, priority=priority)
        results[ch] = result.get("status", "unknown")
    return results
```

### Workflow 3: Broker Event Replay for Recovery

**Goal**: Reconstruct system state after a crash, partition, or operator error by replaying
broker events in chronological order, with filtering and deduplication.

**When to use**: Disaster recovery, debugging distributed systems, auditing compliance,
or reconstructing session context after an unexpected termination.

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
from whitemagic.tools import broker_history, broker_status

async def reconstruct_from_broker(
    start_time: str,
    topic_filter: str = "#",
    limit: int = 1000,
    replay_memory_events: bool = True,
    replay_archive_events: bool = True,
) -> Dict:
    """
    The Encampment keeps records. The records rebuild the house.

    This workflow queries broker status, retrieves filtered event history,
    classifies events by type, and produces a reconstruction report.
    """
    # 1. Check broker status
    status = broker_status()
    health = status.get("health", "unknown")
    total_messages = status.get("total_messages", 0)
    uptime_seconds = status.get("uptime_seconds", 0)

    print(f"🏠 Broker status: {health}")
    print(f"   Total messages: {total_messages}")
    print(f"   Uptime: {timedelta(seconds=int(uptime_seconds))}")
    print("-" * 60)

    # 2. Retrieve history
    history = broker_history(
        start=start_time,
        topic=topic_filter,
        limit=limit,
        order="ascending",  # Chronological for replay
    )

    events = history.get("events", [])
    print(f"   Retrieved {len(events)} events since {start_time}")

    # 3. Classify events
    memory_events = [e for e in events if e.get("topic", "").startswith("memory.")]
    archive_events = [e for e in events if e.get("topic", "") == "session.archives"]
    artifact_events = [e for e in events if e.get("topic", "").startswith("session.artifacts.")]
    chat_events = [e for e in events if e.get("topic", "").startswith("sangha.")]
    other_events = [
        e for e in events
        if e not in memory_events and e not in archive_events
        and e not in artifact_events and e not in chat_events
    ]

    print(f"   Memory events:      {len(memory_events)}")
    print(f"   Archive events:     {len(archive_events)}")
    print(f"   Artifact events:    {len(artifact_events)}")
    print(f"   Chat events:        {len(chat_events)}")
    print(f"   Other events:       {len(other_events)}")

    # 4. Deduplicate by payload hash
    seen_hashes = set()
    deduplicated = []
    for e in events:
        h = e.get("payload_hash", e.get("id", ""))
        if h not in seen_hashes:
            seen_hashes.add(h)
            deduplicated.append(e)

    duplicates = len(events) - len(deduplicated)
    if duplicates > 0:
        print(f"   Deduplicated:       {duplicates} redundant events removed")

    # 5. Reconstruction summary
    reconstruction = {
        "total_events": len(events),
        "deduplicated_events": len(deduplicated),
        "duplicates_removed": duplicates,
        "memory_events": len(memory_events),
        "archive_events": len(archive_events),
        "artifact_events": len(artifact_events),
        "chat_events": len(chat_events),
        "other_events": len(other_events),
        "replay_recommendations": [],
    }

    if replay_memory_events and memory_events:
        reconstruction["replay_recommendations"].append(
            f"Replay {len(memory_events)} memory events to restore cognitive state"
        )
    if replay_archive_events and archive_events:
        reconstruction["replay_recommendations"].append(
            f"Replay {len(archive_events)} archive events to restore session manifests"
        )

    print("-" * 60)
    if reconstruction["replay_recommendations"]:
        print("   Replay recommendations:")
        for rec in reconstruction["replay_recommendations"]:
            print(f"      → {rec}")
    else:
        print("   No replayable events found in specified timeframe.")

    return reconstruction


async def incremental_recovery_check(last_check_time: str) -> Dict:
    """Check for new events since last recovery checkpoint."""
    result = await reconstruct_from_broker(
        start_time=last_check_time,
        topic_filter="#",
        limit=100,
    )
    result["checkpoint_time"] = datetime.now().isoformat()
    return result
```

---

## 🔄 Transitions

**Entering Chapter 27**:
- From Chapter 26 (Roof): When synthesis is protected, structure the camp for long-term storage
- From Chapter 25 (Void): When the void reveals what must be preserved, build the encampment
- From Chapter 14 (Abundance): After creative overflow, the surplus must be housed before it spoils
- From Chapter 20 (Bell): When a signal announces completion, the camp must be ready to receive
- Trigger keywords: "archive", "house", "broker", "publish", "chat", "handoff", "structure",
  "camp", "replay", "recover", "event", "topic", "retain", "manifest", "heritage"

**Exiting Chapter 27**:
- To Chapter 28 (Wall): When the camp is built, set the final boundaries that define its perimeter
- To Chapter 1 (Horn): The encampment at rest dreams of the next journey; the cycle renews
- To Chapter 26 (Roof): If archival reveals corrupted outputs, return to protection and re-synthesize

**Symbolic transition**: The Encampment is the moment when the session ceases to be private
and becomes communal. Where the Room (Chapter 4) hides the work in progress, the Encampment
displays the finished artifacts in their proper places. This transition from secrecy to openness
is not betrayal but maturity—the work has earned its place in the shared record.

---

## 🛠️ Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `broker.publish` fails with "broker_unavailable" | Broker daemon not running or network partitioned | Check `broker.status`; start broker if needed; verify network connectivity |
| `broker.publish` returns "quota_exceeded" | Message rate limit or storage capacity reached | Implement backoff; increase broker retention limits; archive old events |
| `sangha_chat_send` timeout after 10s | Chat service overloaded or channel nonexistent | Retry with exponential backoff; verify channel exists via `sangha_chat_read` |
| `broker.history` returns empty list | No events retained for topic or time range | Check retention policy; some brokers expire old messages; verify topic spelling |
| Handoff message not received by peers | Wrong channel name or message filtered | Verify channel name; use `sangha_chat_read` to list active channels; check filters |
| Archive event lost after broker restart | Broker restarted without persistent storage | Enable `retain=True` on critical publishes; configure broker persistence backend |
| `broker.status` shows "degraded" | High memory usage or disk pressure | Restart broker; increase resource limits; prune old retained messages |
| Event replay produces inconsistent state | Out-of-order delivery or missing events | Use `qos=2` for exactly-once delivery; request ascending order in `broker_history` |

---

## 📜 The Encampment Archive Manifest

Every session that passes through Chapter 27 should leave behind an Archive Manifest—a structured
metadata document that describes what was stored, where it lives, and how to retrieve it. The
manifest is not merely inventory; it is a letter to the future operator who must resume this work.

**Required manifest fields**:
- `schema_version`: Manifest format version for backward compatibility
- `session_id`: Unique identifier linking all artifacts to a single session
- `operator_id`: Identity of the agent or human who produced the session
- `timestamp`: ISO-8601 datetime of manifest creation
- `artifact_count`: Total number of artifacts archived
- `artifacts`: Array of artifact descriptors (id, type, name, size, checksum)
- `tags`: Optional classification tags for search and filtering

**Optional manifest fields**:
- `parent_session_id`: If this session continues a previous one
- `next_session_hints`: Recommendations for what should happen next
- `environment_snapshot`: Versions of tools, models, and dependencies used
- `resumption_instructions`: Specific steps to restore working state

The manifest is published to `session.archives` with `retain=True` so that any subscriber joining
after the session ends can immediately discover what was accomplished and how to continue.

---

## 🧭 Navigation

**Next**: [Chapter 28: Boundaries & Alerts](28_WALL_BOUNDARIES.md)
**Previous**: [Chapter 26: Shelter & Synthesis](26_ROOF_SHELTER.md)
**Quadrant**: Northern (Winter/Water) - Position 6/7
**Cycle Position**: Pre-final — the last organizational act before boundary and return

---

*"The Encampment is not the end of the journey. It is the place where the journey is remembered."*

---

*"A house is not a home until it knows who lives in it. An archive is not a record until it knows
who will read it. The EncampmentGana teaches that permanence requires not just storage but
intention—the deliberate act of preparing a place for what is to come."*
