// Dream Orchestration - Dream Cycle Coordination (PSR-001)
module dream_orchestration

effect dream
  fun triage(): ()
  fun consolidate(): ()
  fun serendipity(): ()

fun run-dream-cycle(): <dream> ()
  dream/triage()
  dream/consolidate()
  dream/serendipity()
