# WhiteMagic Quickstart

**Version**: 5.8.0

Get from zero to a working agent memory server in under five minutes.

## 30-second path

```bash
cargo build --release            # or download a release binary
./target/release/wm quickstart   # runs the built-in demo (create → search)
wm doctor                        # verify the store and index
```

## 1. Install

### From a release

Download `wm-<platform>` and its `.sha256` from the latest release, verify,
and make it executable:

```bash
sha256sum -c wm-linux-x86_64.sha256
chmod +x wm
sudo mv wm /usr/local/bin/
```

### From source

```bash
cargo build --release
sudo cp target/release/wm /usr/local/bin/
```

## 2. Verify

```bash
wm doctor                  # healthy LMDB store + Tantivy index + tool registry
wm quickstart              # demo: create memories, search, galaxy stats
wm stats                   # brain-wave/consciousness dashboard
```

## 3. Connect your agent

Add the native block from [`docs/MCP_CONFIG_GUIDE.md`](MCP_CONFIG_GUIDE.md) to
your MCP client (Claude Desktop, Cursor, Windsurf, or any MCP client), then
restart the client. You should see one tool: `wm`.

## 4. First session

Ask your agent to:

1. `wm(route="session.start", args={"title": "project-name"})`
2. `wm(route="memory.create", args={"content": "a decision worth remembering", "tags": ["project"]})`
3. `wm(route="session.record", args={"content": "what we just decided", "role": "ai", "turn_type": "decision"})`

Next session, start with `wm(route="session.continuity", args={"n": 5})` to
pick up where you left off.

## The curated surface at a glance

| Group | Tools |
|---|---|
| Memory | create, read, list, delete, query, search, hybrid_recall, chat, update, tag, batch_read, stats, count, tags, export, sort, filter, nearby, associate |
| Sessions | start, checkpoint, recall, end, list, record, replay, continuity, handoff |
| Transactions | begin, commit, rollback |
| Claims | claims + claims.add/resolve/status/list/calibration |
| Diagnostics | tools.list, gnosis.*, nlu.shadow_report |

Destructive tools (`memory.delete`, `transaction.rollback`, ...) require an
explicit route plus `"confirm": true`.

## Troubleshooting

- **Search returns nothing on a fresh store**: reindex with `wm reindex`.
- **LockBusy**: another process owns the store — use `--readonly` or stop the
  daemon.
- **Tools fail to load in the client**: the server answers MCP `ping`
  (fixed in 5.8.0); update the binary and restart the client.
- **Want everything**: `wm serve --profile full` exposes the 229-tool archive
  surface (research/extension use).
