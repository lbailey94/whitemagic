# Gana: gana_dipper

**47 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [astro_shift](../tools/astro_shift.md) | system | read | Dispatch-routable WhiteMagic tool 'astro_shift'. |
| [astro_status](../tools/astro_status.md) | system | read | Dispatch-routable WhiteMagic tool 'astro_status'. |
| [cognitive.hints](../tools/cognitive.hints.md) | system | read | Get tool selection hints for the current cognitive mode — which tools are prefer |
| [cognitive.mode](../tools/cognitive.mode.md) | system | read | Get the current cognitive mode and its full profile — preferred tools, context s |
| [cognitive.set](../tools/cognitive.set.md) | system | write | Set the cognitive mode: explorer (curiosity), executor (action), reflector (cont |
| [cognitive.stats](../tools/cognitive.stats.md) | system | read | Get cognitive modes statistics — mode transitions, current state, overrides. |
| [doctrine.force](../tools/doctrine.force.md) | system | read | Dispatch-routable WhiteMagic tool 'doctrine.force'. |
| [doctrine.stratagems](../tools/doctrine.stratagems.md) | system | read | Dispatch-routable WhiteMagic tool 'doctrine.stratagems'. |
| [doctrine.summary](../tools/doctrine.summary.md) | system | read | Dispatch-routable WhiteMagic tool 'doctrine.summary'. |
| [gating.detect](../tools/gating.detect.md) | memory | read | Auto-detect cognitive context from a query string using keyword matching. |
| [gating.list](../tools/gating.list.md) | memory | read | List all available galaxy gating contexts with descriptions and current context. |
| [gating.mask](../tools/gating.mask.md) | memory | read | Get the galaxy activation mask (weight multipliers per galaxy) for a given conte |
| [gating.set_context](../tools/gating.set_context.md) | memory | read | Set the current cognitive context for galaxy gating (introspection, coding, rese |
| [gating.stats](../tools/gating.stats.md) | memory | read | Get galaxy gating system statistics. |
| [homeostasis](../tools/homeostasis.md) | metrics | write | Unified homeostatic loop control. Actions: status (view loop state + recent corr |
| [homeostasis.check](../tools/homeostasis.check.md) | system | read | Dispatch-routable WhiteMagic tool 'homeostasis.check'. |
| [homeostasis.status](../tools/homeostasis.status.md) | system | read | Dispatch-routable WhiteMagic tool 'homeostasis.status'. |
| [maturity.assess](../tools/maturity.assess.md) | introspection | read | Assess the system's developmental maturity stage. Runs gate checks for each stag |
| [mc.optimize](../tools/mc.optimize.md) | synthesis | read | Run Bayesian optimization to find optimal parameters. Uses GP surrogate + Expect |
| [mc.rare_event](../tools/mc.rare_event.md) | synthesis | read | Estimate rare event probabilities using subset simulation, multilevel splitting, |
| [mc.sde](../tools/mc.sde.md) | synthesis | read | Solve stochastic differential equations via Euler-Maruyama or Milstein. Supports |
| [mc.superforecaster](../tools/mc.superforecaster.md) | synthesis | read | Run the full superforecaster pipeline: LHS → PCE → Sobol → Bayesian optimization |
| [mc.surrogate](../tools/mc.surrogate.md) | synthesis | read | Fit and evaluate a Gaussian Process surrogate model for Bayesian optimization or |
| [mesh.route.strategy](../tools/mesh.route.strategy.md) | agent | write | Change the inference routing strategy |
| [model.optimize](../tools/model.optimize.md) | system | read | Dispatch-routable WhiteMagic tool 'model.optimize'. |
| [model.optimize_status](../tools/model.optimize_status.md) | system | read | Dispatch-routable WhiteMagic tool 'model.optimize_status'. |
| [neuro.compute](../tools/neuro.compute.md) | synthesis | read | Compute neuromodulator (dopamine, serotonin, acetylcholine) levels from activity |
| [neuro.modulate](../tools/neuro.modulate.md) | memory | write | Apply neuromodulation to a list of memories, adjusting their neuro_score based o |
| [neuro.reset](../tools/neuro.reset.md) | memory | write | Reset neuromodulator levels to baseline. |
| [neuro.stats](../tools/neuro.stats.md) | synthesis | read | Get neuromodulation system statistics. |
| [neurotransmitter.report](../tools/neurotransmitter.report.md) | system | read | Dispatch-routable WhiteMagic tool 'neurotransmitter.report'. |
| [neurotransmitter.status](../tools/neurotransmitter.status.md) | system | read | Dispatch-routable WhiteMagic tool 'neurotransmitter.status'. |
| [possibility.explore](../tools/possibility.explore.md) | synthesis | read | Run Monte Carlo possibility space exploration on system parameters (guna balance |
| [predictive.batch](../tools/predictive.batch.md) | security | read | Batch score multiple contracts for vulnerability risk |
| [predictive.score](../tools/predictive.score.md) | security | read | Score a contract for vulnerability risk using predictive model |
| [starter_packs](../tools/starter_packs.md) | system | read | Dispatch-routable WhiteMagic tool 'starter_packs'. |
| [starter_packs.get](../tools/starter_packs.get.md) | system | read | Dispatch-routable WhiteMagic tool 'starter_packs.get'. |
| [starter_packs.list](../tools/starter_packs.list.md) | system | read | Dispatch-routable WhiteMagic tool 'starter_packs.list'. |
| [starter_packs.suggest](../tools/starter_packs.suggest.md) | system | read | Dispatch-routable WhiteMagic tool 'starter_packs.suggest'. |
| [warp.create](../tools/warp.create.md) | agent | write | Create a custom warp preset |
| [warp.delete](../tools/warp.delete.md) | agent | delete | Delete a custom warp (built-in warps cannot be deleted) |
| [warp.list](../tools/warp.list.md) | agent | read | List all available warps (built-in and custom) |
| [warp.load](../tools/warp.load.md) | agent | read | Load a warp preset by name, or stack multiple warps with 'stack' param |
| [warp.status](../tools/warp.status.md) | agent | read | Get warp manager status (builtin count, custom count, names) |
| [zodiac.activate](../tools/zodiac.activate.md) | system | read | Activate a specific zodiac core with context. Each core (Aries through Pisces) p |
| [zodiac.council](../tools/zodiac.council.md) | system | read | Convene the full 12-sign zodiac council for a decision. Returns perspectives fro |
| [zodiac.stats](../tools/zodiac.stats.md) | introspection | read | Get activation statistics for all 12 zodiac cores |
