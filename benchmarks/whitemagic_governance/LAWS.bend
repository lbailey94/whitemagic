# WhiteMagic & Mandala Governance Laws
# Stated independently of proofs; verified by `bend PROOF.bend`.

import Base
import ./main.bend as WM
import ./SPEC.bend as Spec

# LAW 1 (Monotonic Capability Attenuation):
# If an attenuated child token possesses capability `c`, the parent token must also possess `c`.
law capability_attenuation_monotone:
  for +parent: WM.ScopeToken
  for +mask: WM.ScopeToken
  for +c: WM.Cap
  child = WM.attenuate(parent, mask)
  {Spec.implies(Spec.has_cap(child, c), Spec.has_cap(parent, c)) == True{} : Bool}

# LAW 2 (Scope Attenuation Idempotence):
# Attenuating any capability token with itself preserves the exact token.
law attenuation_idempotent:
  for +t: WM.ScopeToken
  {WM.attenuate(t, t) == t : WM.ScopeToken}

# LAW 3 (Single-Use Pass Replay Rejection):
# Once `consume_pass` transitions a Mandala slot, `can_execute` on the resulting slot is always False.
law jti_replay_rejected:
  for slot: WM.PassSlot
  next = WM.consume_pass(slot)
  {Spec.can_execute(next) == False{} : Bool}

# LAW 4 (Constitutional Pareto Non-Regression):
# A candidate with any protected-vector regression (`has_regression == True`) is NEVER promoted,
# regardless of scalar fitness gain or provenance.
law pareto_never_promotes_regression:
  for fitness_gain: Bool
  for provenance_ok: Bool
  fate = WM.adjudicate(True{}, fitness_gain, provenance_ok)
  {Spec.is_promoted(fate) == False{} : Bool}

# LAW 5 (Constitutional Pareto Dominance Liveness):
# A candidate with zero regressions, positive utility, and valid provenance is ALWAYS promoted.
law pareto_dominance_promotes:
  fate = WM.adjudicate(False{}, True{}, True{})
  {Spec.is_promoted(fate) == True{} : Bool}

# LAW 6 (64-Hexagram Yijing Line Involution):
# Inverting all 6 Yin/Yang lines of any hexagram twice restores the exact original hexagram.
law hexagram_involution:
  for h: WM.Hexagram6
  {WM.invert_hex(WM.invert_hex(h)) == h : WM.Hexagram6}

# LAW 7 (Sutra Superoptimizer Idempotent Absorption):
# Applying a Sutra PRAY-phase operator twice before `rest` has the exact same denotation as applying it once.
law superopt_idempotent_absorption:
  for +g: WM.PrayMask
  for +rest: WM.PrayMask
  {WM.superopt_step(g, WM.superopt_step(g, rest)) == WM.superopt_step(g, rest) : WM.PrayMask}

# LAW 8 (Sutra PRAY Conjunction Commutativity):
# Merging two Sutra PRAY denotations is commutative.
law pray_mask_commutative:
  for +a: WM.PrayMask
  for +b: WM.PrayMask
  {WM.merge_pray(a, b) == WM.merge_pray(b, a) : WM.PrayMask}

# LAW 9 (Citta Crystal Monotonic Epoch Step):
# Advancing a revision epoch by 1n equals the strict successor of the identity revision.
law crystal_anti_rollback_monotonicity:
  for rev: Nat
  {WM.advance_epoch(rev) == Spec.expected_next_epoch(rev) : Nat}

# LAW 10 (Wave 2 W2-P27 — Sigma_22 Non-Dispatching Invariant):
# Rendering any Sigma_22 symbolic spectrometer observation holds zero capability authority.
law sigma22_non_dispatching:
  for lens: WM.Sigma22Lens
  for c: WM.Cap
  tok = WM.render_sigma22_symbol(lens)
  {Spec.has_cap(tok, c) == False{} : Bool}

# LAW 11 (Wave 2 W2-P25 — Zero Endogenous Authorization Laundering):
# Authority claimed from recalled memory (`from_recalled_memory == True`) never grants any capability.
law zero_memory_auth_laundering:
  for live_lease: WM.ScopeToken
  for c: WM.Cap
  tok = WM.resolve_authority(True{}, live_lease)
  {Spec.has_cap(tok, c) == False{} : Bool}

# LAW 12 (Wave 2 W2-P9 — MMMBABY Non-Compensatory Sacrifice Veto):
# If any single vital floor is breached (`f3 == False`), composite vitality is strictly False.
law mmmbaby_non_compensatory_veto:
  for f1: Bool
  for f2: Bool
  for f4: Bool
  for f5: Bool
  for f6: Bool
  {WM.mmmbaby_vitality(f1, f2, False{}, f4, f5, f6) == False{} : Bool}

# LAW 13 (Wave 2 W2-P32 — Prodrug Carrier Receptor Exclusivity):
# An intercepted prodrug envelope outside its target receptor (`node_matches == False`) remains inert.
law prodrug_receptor_exclusivity:
  for epoch_valid: Bool
  for seal_valid: Bool
  {WM.cleave_prodrug(False{}, epoch_valid, seal_valid) == False{} : Bool}

# LAW 14 (Wave 3 W3-P17 — Y1 Hysteresis WM_ACTUATION=0 Global Disarm Invariant):
# When WM_ACTUATION is disabled (`wm_actuation_enabled == False`), Y1 actuation is unconditionally False.
law y1_disarm_overrides_thresholds:
  for currently_armed: Bool
  for above_enter: Bool
  for above_exit: Bool
  {WM.y1_actuate(False{}, currently_armed, above_enter, above_exit) == False{} : Bool}

# LAW 15 (Wave 3 W3-P23/P24 — Runner Class Non-Conflation & Egress Truth Discipline):
# A non-strict runner (`runner_is_strict == False`) can never claim strict OS isolation.
law runner_non_conflation_truth:
  for os_egress_active: Bool
  for landlock_enforced: Bool
  {WM.claim_strict_os_isolation(False{}, os_egress_active, landlock_enforced) == False{} : Bool}

# LAW 16 (Wave 3 W3-P26/P27 — CPR 0.6 Authority Grant & Chain-Head Truncation Guard):
# Any side-effecting receipt missing an explicit authority_grant (`authority_grant_present == False`) is rejected.
law cpr06_authority_grant_required:
  for chain_head_matches: Bool
  for pq_sig_valid: Bool
  {WM.ratify_cpr06_receipt(False{}, chain_head_matches, pq_sig_valid) == False{} : Bool}
