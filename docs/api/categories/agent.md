# Category: agent

**51 tools** in this category.

| Tool | Safety | Description |
|------|--------|-------------|
| [agent.capabilities](../tools/agent.capabilities.md) | read | Query what a specific agent can do (capabilities, metadata, status) |
| [agent.deregister](../tools/agent.deregister.md) | delete | Remove an agent from the registry |
| [agent.heartbeat](../tools/agent.heartbeat.md) | write | Send a heartbeat to keep agent registration active, with optional workload updat |
| [agent.list](../tools/agent.list.md) | read | List registered agents with optional active-only and capability filters |
| [agent.register](../tools/agent.register.md) | write | Register a new agent or update an existing one with name, capabilities, and meta |
| [agent.trust](../tools/agent.trust.md) | read | Get agent reputation and trust scores derived from the Karma Ledger. Shows per-a |
| [archive.run](../tools/archive.run.md) | write | Run a durable archive cycle (snapshot breakthroughs to git branch) |
| [archive.status](../tools/archive.status.md) | read | Get durable archive status (files, commits, last archive time) |
| [autoswarm.campaign](../tools/autoswarm.campaign.md) | write | Launch an evolutionary campaign (hypothesis → trial → result → share) |
| [autoswarm.start](../tools/autoswarm.start.md) | write | Start continuous evolutionary autoswarm loop |
| [autoswarm.status](../tools/autoswarm.status.md) | read | Get autoswarm status (running state, stats, recent campaigns) |
| [autoswarm.stop](../tools/autoswarm.stop.md) | write | Stop continuous autoswarm loop |
| [dilo_co.init](../tools/dilo_co.init.md) | write | Initialize DiLoCo distributed training coordinator with parameters |
| [dilo_co.register_worker](../tools/dilo_co.register_worker.md) | write | Register a worker to the DiLoCo Parcae pool |
| [dilo_co.status](../tools/dilo_co.status.md) | read | Get DiLoCo coordinator status (workers, syncs, compression stats) |
| [dilo_co.submit_gradient](../tools/dilo_co.submit_gradient.md) | write | Submit gradients from a worker to the DiLoCo coordinator |
| [dilo_co.sync](../tools/dilo_co.sync.md) | write | Perform a DiLoCo global synchronization step |
| [ensemble](../tools/ensemble.md) | read | Unified multi-LLM ensemble voting. Actions: query (send prompt to multiple model |
| [leaderboard.merge](../tools/leaderboard.merge.md) | write | Merge remote leaderboard data from a peer node |
| [leaderboard.status](../tools/leaderboard.status.md) | read | Get CRDT leaderboard status (Loro enabled, entries, merges) |
| [leaderboard.submit](../tools/leaderboard.submit.md) | write | Submit an experiment to the distributed CRDT leaderboard |
| [leaderboard.top](../tools/leaderboard.top.md) | read | Get top entries from the distributed leaderboard |
| [mesh.experiment.discover](../tools/mesh.experiment.discover.md) | read | Discover peers on the mesh network |
| [mesh.experiment.peers](../tools/mesh.experiment.peers.md) | read | Get experiments received from peer nodes |
| [mesh.experiment.receive](../tools/mesh.experiment.receive.md) | write | Receive an experiment from a peer node (called on EXPERIMENT_SHARE signal) |
| [mesh.experiment.share](../tools/mesh.experiment.share.md) | write | Share an experiment result to the P2P mesh |
| [mesh.experiment.status](../tools/mesh.experiment.status.md) | read | Get experiment sync status (sent, received, imported counts) |
| [mesh.route](../tools/mesh.route.md) | read | Route an inference request to the best available mesh node |
| [mesh.route.nodes](../tools/mesh.route.nodes.md) | read | Get available inference nodes, optionally filtered by model |
| [mesh.route.register](../tools/mesh.route.register.md) | write | Register a mesh inference node |
| [mesh.route.status](../tools/mesh.route.status.md) | read | Get inference router status (nodes, strategy, stats) |
| [mesh.route.strategy](../tools/mesh.route.strategy.md) | write | Change the inference routing strategy |
| [polyglot.actor](../tools/polyglot.actor.md) | read | Execute actor-based hypothesis tracking through the Elixir actor backend. Manage |
| [swarm.complete](../tools/swarm.complete.md) | write | Mark a subtask as completed or failed |
| [swarm.decompose](../tools/swarm.decompose.md) | write | Decompose a goal into subtasks with capability requirements for multi-agent coor |
| [swarm.plan](../tools/swarm.plan.md) | read | Get a specific swarm plan by ID |
| [swarm.resolve](../tools/swarm.resolve.md) | read | Resolve a consensus vote using majority, unanimous, first_wins, or weighted stra |
| [swarm.route](../tools/swarm.route.md) | write | Route subtasks to available agents by capability matching |
| [swarm.vote](../tools/swarm.vote.md) | write | Record a vote from an agent on a consensus topic |
| [task.route_smart](../tools/task.route_smart.md) | read | Determine the optimal host for a task based on current system load across local  |
| [warp.create](../tools/warp.create.md) | write | Create a custom warp preset |
| [warp.delete](../tools/warp.delete.md) | delete | Delete a custom warp (built-in warps cannot be deleted) |
| [warp.list](../tools/warp.list.md) | read | List all available warps (built-in and custom) |
| [warp.load](../tools/warp.load.md) | read | Load a warp preset by name, or stack multiple warps with 'stack' param |
| [warp.market.broadcast](../tools/warp.market.broadcast.md) | write | Broadcast a warp listing to mesh peers |
| [warp.market.discover](../tools/warp.market.discover.md) | read | Discover warp presets on the marketplace |
| [warp.market.download](../tools/warp.market.download.md) | write | Download and import a warp from the marketplace |
| [warp.market.publish](../tools/warp.market.publish.md) | write | Publish a warp preset to the P2P marketplace |
| [warp.market.status](../tools/warp.market.status.md) | read | Get warp marketplace status (listings, downloads, negotiations) |
| [warp.status](../tools/warp.status.md) | read | Get warp manager status (builtin count, custom count, names) |
| [worker.status](../tools/worker.status.md) | read | Check if any worker daemons are running and get their stats (heartbeat, tasks co |
