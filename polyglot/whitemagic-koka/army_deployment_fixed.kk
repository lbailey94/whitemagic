// Simplified army deployment - compiles clean
module army_deployment

pub fun deploy-clone(task: string, timeout: int): string
  "clone-" ++ task ++ "-" ++ timeout.show

pub fun batch-deploy(tasks: list<string>): list<string>
  tasks.map(fn(t) deploy-clone(t, 5))

pub fun execute-campaign(campaign-id: string, tasks: list<string>, army-size: int): (int, int)
  val deployed = batch-deploy(tasks)
  (deployed.length, 0)
