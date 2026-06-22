// Campaign Effects - Campaign Management (PSR-005)
module campaign_effects

effect campaign
  fun start(id: string): ()
  fun update-progress(id: string, progress: int): ()
  fun complete(id: string): ()

fun run-campaign-lifecycle(id: string, steps: int): <campaign> ()
  campaign/start(id)
  repeat(steps) fn(i)
    campaign/update-progress(id, i * 100 / steps)
  campaign/complete(id)
