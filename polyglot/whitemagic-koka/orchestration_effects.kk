// Orchestration Effects - Campaign Orchestration (PSR-007)
module orchestration_effects

effect orchestration
  fun start-campaign(campaign-id: string): ()
  fun complete-task(task-id: string): ()
  fun get-status(campaign-id: string): string

fun run-campaign(campaign-id: string, tasks: list<string>): <orchestration> ()
  orchestration/start-campaign(campaign-id)
  tasks.foreach fn(task)
    orchestration/complete-task(task)
