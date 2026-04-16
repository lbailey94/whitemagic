// Resource Effects - Resource Management (PSR-005)
module resource_effects

effect resources
  fun allocate(amount: int): bool
  fun release(amount: int): ()
  fun check-availability(): int
  fun set-limit(max: int): ()
  fun get-usage(): (int, int)

fun with-resource(amount: int, action: () -> <resources> a): <resources> maybe<a>
  if resources/allocate(amount) then
    val result = action()
    resources/release(amount)
    Just(result)
  else
    Nothing

fun batch-with-resources(tasks: list<(int, () -> <resources> a)>): <resources> list<a>
  var results := []
  
  tasks.foreach fn(task)
    val (amount, action) = task
    match with-resource(amount, action)
      Just(r) -> results := Cons(r, results)
      Nothing -> ()
  
  results
