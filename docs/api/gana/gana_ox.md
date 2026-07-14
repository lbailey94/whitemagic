# Gana: gana_ox

**35 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [dilo_co.init](../tools/dilo_co.init.md) | agent | write | Initialize DiLoCo distributed training coordinator with parameters |
| [dilo_co.register_worker](../tools/dilo_co.register_worker.md) | agent | write | Register a worker to the DiLoCo Parcae pool |
| [dilo_co.status](../tools/dilo_co.status.md) | agent | read | Get DiLoCo coordinator status (workers, syncs, compression stats) |
| [dilo_co.submit_gradient](../tools/dilo_co.submit_gradient.md) | agent | write | Submit gradients from a worker to the DiLoCo coordinator |
| [dilo_co.sync](../tools/dilo_co.sync.md) | agent | write | Perform a DiLoCo global synchronization step |
| [fast_write.append](../tools/fast_write.append.md) | memory | write | Append content to an existing file with optional syntax validation. |
| [fast_write.batch](../tools/fast_write.batch.md) | memory | write | Write multiple files in one operation with syntax validation. |
| [fast_write.validate](../tools/fast_write.validate.md) | memory | read | Validate syntax of a file without writing. Checks Python (ast.parse) or basic en |
| [fast_write.write](../tools/fast_write.write.md) | memory | write | Write content to a file atomically with syntax validation. Overwrites if file ex |
| [genetic.run](../tools/genetic.run.md) | system | read | Dispatch-routable WhiteMagic tool 'genetic.run'. |
| [genetic.status](../tools/genetic.status.md) | system | read | Dispatch-routable WhiteMagic tool 'genetic.status'. |
| [skill.amend](../tools/skill.amend.md) | system | write | Dispatch-routable WhiteMagic tool 'skill.amend'. |
| [skill.evaluate](../tools/skill.evaluate.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.evaluate'. |
| [skill.export_all](../tools/skill.export_all.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.export_all'. |
| [skill.history](../tools/skill.history.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.history'. |
| [skill.import](../tools/skill.import.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.import'. |
| [skill.invoke](../tools/skill.invoke.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.invoke'. |
| [skill.list](../tools/skill.list.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.list'. |
| [skill.rollback](../tools/skill.rollback.md) | system | write | Dispatch-routable WhiteMagic tool 'skill.rollback'. |
| [skill.seed](../tools/skill.seed.md) | system | read | Dispatch-routable WhiteMagic tool 'skill.seed'. |
| [swarm.analyze](../tools/swarm.analyze.md) | security | read | Run multi-agent security analysis swarm on a project |
| [swarm.complete](../tools/swarm.complete.md) | agent | write | Mark a subtask as completed or failed |
| [swarm.decompose](../tools/swarm.decompose.md) | agent | write | Decompose a goal into subtasks with capability requirements for multi-agent coor |
| [swarm.plan](../tools/swarm.plan.md) | agent | read | Get a specific swarm plan by ID |
| [swarm.resolve](../tools/swarm.resolve.md) | agent | read | Resolve a consensus vote using majority, unanimous, first_wins, or weighted stra |
| [swarm.route](../tools/swarm.route.md) | agent | write | Route subtasks to available agents by capability matching |
| [swarm.status](../tools/swarm.status.md) | security | read | Get security swarm status |
| [swarm.vote](../tools/swarm.vote.md) | agent | write | Record a vote from an agent on a consensus topic |
| [war_room.campaigns](../tools/war_room.campaigns.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.campaigns'. |
| [war_room.execute](../tools/war_room.execute.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.execute'. |
| [war_room.hierarchy](../tools/war_room.hierarchy.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.hierarchy'. |
| [war_room.phase](../tools/war_room.phase.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.phase'. |
| [war_room.plan](../tools/war_room.plan.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.plan'. |
| [war_room.status](../tools/war_room.status.md) | system | read | Dispatch-routable WhiteMagic tool 'war_room.status'. |
| [worker.status](../tools/worker.status.md) | agent | read | Check if any worker daemons are running and get their stats (heartbeat, tasks co |
