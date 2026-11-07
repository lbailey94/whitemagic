# Formal Proofs for the WhiteMagic & Mandala Governance Laws in Bend 2.
# Run: `BEND_NO_TELEMETRY=1 bend PROOF.bend`

import Base
import ./main.bend as WM
import ./SPEC.bend as Spec
import ./LAWS.bend as Laws

def and_implies_left(a: Bool, b: Bool) -> {Spec.implies(a && b, a) == True{} : Bool}:
  match a:
    case True{}:
      match b:
        case True{}:
          {==}
        case False{}:
          {==}
    case False{}:
      {==}

def and_idem(b: Bool) -> {b && b == b : Bool}:
  match b:
    case True{}:
      {==}
    case False{}:
      {==}

def Laws.capability_attenuation_monotone(parent, mask, c):
  match parent:
    case WM.Scope{pr, pw, pe, pn}:
      match mask:
        case WM.Scope{mr, mw, me, mn}:
          match c:
            case WM.CapRead{}:
              and_implies_left(pr, mr)
            case WM.CapWrite{}:
              and_implies_left(pw, mw)
            case WM.CapExec{}:
              and_implies_left(pe, me)
            case WM.CapNet{}:
              and_implies_left(pn, mn)

def Laws.attenuation_idempotent(t):
  match t:
    case WM.Scope{r, w, e, n}:
      %and_idem(r) : {WM.Scope{r && r, w && w, e && e, n && n} == WM.Scope{_, w, e, n} : WM.ScopeToken}
      %and_idem(w) : {WM.Scope{r && r, w && w, e && e, n && n} == WM.Scope{r && r, _, e, n} : WM.ScopeToken}
      %and_idem(e) : {WM.Scope{r && r, w && w, e && e, n && n} == WM.Scope{r && r, w && w, _, n} : WM.ScopeToken}
      %and_idem(n) : {WM.Scope{r && r, w && w, e && e, n && n} == WM.Scope{r && r, w && w, e && e, _} : WM.ScopeToken}
      {==}

def Laws.jti_replay_rejected(slot):
  match slot:
    case WM.Slot{consumed, exec_count}:
      match consumed:
        case True{}:
          {==}
        case False{}:
          {==}

def Laws.pareto_never_promotes_regression(fitness_gain, provenance_ok):
  {==}

def Laws.pareto_dominance_promotes():
  {==}

def not_not(b: Bool) -> {WM.flip_line(WM.flip_line(b)) == b : Bool}:
  match b:
    case True{}:
      {==}
    case False{}:
      {==}

def Laws.hexagram_involution(h):
  match h:
    case WM.Hex{l1, l2, l3, l4, l5, l6}:
      %not_not(l1) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{_, l2, l3, l4, l5, l6} : WM.Hexagram6}
      %not_not(l2) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{WM.flip_line(WM.flip_line(l1)), _, l3, l4, l5, l6} : WM.Hexagram6}
      %not_not(l3) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), _, l4, l5, l6} : WM.Hexagram6}
      %not_not(l4) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), _, l5, l6} : WM.Hexagram6}
      %not_not(l5) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), _, l6} : WM.Hexagram6}
      %not_not(l6) : {WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), WM.flip_line(WM.flip_line(l6))} == WM.Hex{WM.flip_line(WM.flip_line(l1)), WM.flip_line(WM.flip_line(l2)), WM.flip_line(WM.flip_line(l3)), WM.flip_line(WM.flip_line(l4)), WM.flip_line(WM.flip_line(l5)), _} : WM.Hexagram6}
      {==}

def or_idem(a: Bool, b: Bool) -> {(a || (a || b)) == (a || b) : Bool}:
  match a:
    case True{}:
      {==}
    case False{}:
      {==}

def Laws.superopt_idempotent_absorption(g, rest):
  match g:
    case WM.Pray{gp, gr, ga, gy}:
      match rest:
        case WM.Pray{rp, rr, ra, ry}:
          %or_idem(gp, rp) : {WM.Pray{gp || (gp || rp), gr || (gr || rr), ga || (ga || ra), gy || (gy || ry)} == WM.Pray{_, gr || rr, ga || ra, gy || ry} : WM.PrayMask}
          %or_idem(gr, rr) : {WM.Pray{gp || (gp || rp), gr || (gr || rr), ga || (ga || ra), gy || (gy || ry)} == WM.Pray{gp || (gp || rp), _, ga || ra, gy || ry} : WM.PrayMask}
          %or_idem(ga, ra) : {WM.Pray{gp || (gp || rp), gr || (gr || rr), ga || (ga || ra), gy || (gy || ry)} == WM.Pray{gp || (gp || rp), gr || (gr || rr), _, gy || ry} : WM.PrayMask}
          %or_idem(gy, ry) : {WM.Pray{gp || (gp || rp), gr || (gr || rr), ga || (ga || ra), gy || (gy || ry)} == WM.Pray{gp || (gp || rp), gr || (gr || rr), ga || (ga || ra), _} : WM.PrayMask}
          {==}

def or_comm(a: Bool, b: Bool) -> {a || b == b || a : Bool}:
  match a:
    case True{}:
      match b:
        case True{}:
          {==}
        case False{}:
          {==}
    case False{}:
      match b:
        case True{}:
          {==}
        case False{}:
          {==}

def Laws.pray_mask_commutative(a, b):
  match a:
    case WM.Pray{ap, ar, aa, ay}:
      match b:
        case WM.Pray{bp, br, ba, by}:
          %or_comm(ap, bp) : {WM.Pray{ap || bp, ar || br, aa || ba, ay || by} == WM.Pray{_, br || ar, ba || aa, by || ay} : WM.PrayMask}
          %or_comm(ar, br) : {WM.Pray{ap || bp, ar || br, aa || ba, ay || by} == WM.Pray{ap || bp, _, ba || aa, by || ay} : WM.PrayMask}
          %or_comm(aa, ba) : {WM.Pray{ap || bp, ar || br, aa || ba, ay || by} == WM.Pray{ap || bp, ar || br, _, by || ay} : WM.PrayMask}
          %or_comm(ay, by) : {WM.Pray{ap || bp, ar || br, aa || ba, ay || by} == WM.Pray{ap || bp, ar || br, aa || ba, _} : WM.PrayMask}
          {==}

def Laws.crystal_anti_rollback_monotonicity(rev):
  match rev:
    case 0n:
      {==}
    case 1n+p:
      %Laws.crystal_anti_rollback_monotonicity(p) : {1n+Nat.add(p, 1n) == 1n+_ : Nat}
      {==}

def Laws.sigma22_non_dispatching(lens, c):
  match lens:
    case WM.Lens{motif_id, basin_k8}:
      match c:
        case WM.CapRead{}:
          {==}
        case WM.CapWrite{}:
          {==}
        case WM.CapExec{}:
          {==}
        case WM.CapNet{}:
          {==}

def Laws.zero_memory_auth_laundering(live_lease, c):
  match c:
    case WM.CapRead{}:
      {==}
    case WM.CapWrite{}:
      {==}
    case WM.CapExec{}:
      {==}
    case WM.CapNet{}:
      {==}

def Laws.mmmbaby_non_compensatory_veto(f1, f2, f4, f5, f6):
  match f1:
    case True{}:
      match f2:
        case True{}:
          {==}
        case False{}:
          {==}
    case False{}:
      {==}

def Laws.prodrug_receptor_exclusivity(epoch_valid, seal_valid):
  {==}

def Laws.y1_disarm_overrides_thresholds(currently_armed, above_enter, above_exit):
  {==}

def Laws.runner_non_conflation_truth(os_egress_active, landlock_enforced):
  {==}

def Laws.cpr06_authority_grant_required(chain_head_matches, pq_sig_valid):
  {==}
