# Gana: gana_wings

**16 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [archive.run](../tools/archive.run.md) | agent | write | Run a durable archive cycle (snapshot breakthroughs to git branch) |
| [archive.status](../tools/archive.status.md) | agent | read | Get durable archive status (files, commits, last archive time) |
| [audit.export](../tools/audit.export.md) | system | read | Dispatch-routable WhiteMagic tool 'audit.export'. |
| [export_memories](../tools/export_memories.md) | system | write | Dispatch-routable WhiteMagic tool 'export_memories'. |
| [leaderboard.merge](../tools/leaderboard.merge.md) | agent | write | Merge remote leaderboard data from a peer node |
| [leaderboard.status](../tools/leaderboard.status.md) | agent | read | Get CRDT leaderboard status (Loro enabled, entries, merges) |
| [leaderboard.submit](../tools/leaderboard.submit.md) | agent | write | Submit an experiment to the distributed CRDT leaderboard |
| [leaderboard.top](../tools/leaderboard.top.md) | agent | read | Get top entries from the distributed leaderboard |
| [mesh.broadcast](../tools/mesh.broadcast.md) | broker | write | Broadcast a signal to all mesh peers via gRPC (if connected) or Redis pub/sub fa |
| [mesh.connect](../tools/mesh.connect.md) | broker | write | Connect or reconnect the local mesh client. Optionally provide an address and no |
| [mesh.experiment.discover](../tools/mesh.experiment.discover.md) | agent | read | Discover peers on the mesh network |
| [mesh.experiment.peers](../tools/mesh.experiment.peers.md) | agent | read | Get experiments received from peer nodes |
| [mesh.experiment.share](../tools/mesh.experiment.share.md) | agent | write | Share an experiment result to the P2P mesh |
| [mesh.experiment.status](../tools/mesh.experiment.status.md) | agent | read | Get experiment sync status (sent, received, imported counts) |
| [mesh.status](../tools/mesh.status.md) | introspection | read | Get cross-node mesh awareness status. Shows known peers, connectivity state, gRP |
| [warp.market.broadcast](../tools/warp.market.broadcast.md) | agent | write | Broadcast a warp listing to mesh peers |
