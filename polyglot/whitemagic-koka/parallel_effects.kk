// Parallel Effects - Parallel Execution Coordination (PSR-005/007)
module parallel_effects

effect parallel
  fun spawn(task: () -> <div> a): ()
  fun await-all(): list<string>
  fun get-worker-count(): int

effect scheduling
  fun schedule-task(task-id: string, priority: int): ()
  fun get-next-task(): maybe<string>
  fun mark-complete(task-id: string): ()

fun parallel-map(items: list<a>, f: a -> <parallel> b): <parallel> list<b>
  items.foreach fn(item)
    parallel/spawn(fn() f(item))
  
  val results = parallel/await-all()
  results.map(fn(r) r)

fun parallel-execute(tasks: list<string>): <parallel, scheduling> int
  var completed := 0
  
  tasks.foreach fn(task)
    scheduling/schedule-task(task, 5)
  
  repeat(len(tasks))
    match scheduling/get-next-task()
      Just(task) ->
        parallel/spawn(fn() task)
        scheduling/mark-complete(task)
        completed := completed + 1
      Nothing -> ()
  
  completed
