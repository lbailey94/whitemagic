// Workflow Effects - Workflow Orchestration (PSR-007)
module workflow_effects

effect workflow
  fun execute-step(step-id: string): bool
  fun get-dependencies(step-id: string): list<string>

fun execute-workflow(steps: list<string>): <workflow> list<bool>
  steps.map fn(step) workflow/execute-step(step)
