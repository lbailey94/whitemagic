// Deployment Effects - Clone Army Operations (PSR-005)
module deployment_effects

effect deployment
  fun deploy-clone(task-id: string, priority: int): string
  fun complete-clone(clone-id: string, result: string): ()

effect resources
  fun allocate(amount: int): bool
  fun release(amount: int): ()

fun deploy-army(tasks: list<(string, int)>): <deployment, resources> list<string>
  var clone-ids := []
  tasks.foreach fn(task)
    val (task-id, priority) = task
    if resources/allocate(1) then
      val clone-id = deployment/deploy-clone(task-id, priority)
      clone-ids := Cons(clone-id, clone-ids)
  clone-ids
