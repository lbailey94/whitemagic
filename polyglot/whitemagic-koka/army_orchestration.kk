// Army Orchestration - Clone Army Coordination (PSR-005)
module army_orchestration

effect army
  fun deploy(count: int): list<string>
  fun collect-results(clone-ids: list<string>): list<string>

fun orchestrate-campaign(task-count: int): <army> list<string>
  val clones = army/deploy(task-count)
  army/collect-results(clones)
