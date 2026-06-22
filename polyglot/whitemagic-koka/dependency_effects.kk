// Dependency Effects - Dependency Management (PSR-007)
module dependency_effects

effect dependencies
  fun add-dependency(task: string, depends-on: string): ()
  fun resolve(task: string): list<string>

fun resolve-all(tasks: list<string>): <dependencies> list<list<string>>
  tasks.map fn(task) dependencies/resolve(task)
