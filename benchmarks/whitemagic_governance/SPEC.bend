# WhiteMagic & Mandala Governance Specification Observers
# Pure reference predicates and observers used by `LAWS.bend`.

import Base
import ./main.bend as WM

def has_cap(tok: WM.ScopeToken, cap: WM.Cap) -> Bool:
  match tok:
    case WM.Scope{read, write, exec, net}:
      match cap:
        case WM.CapRead{}:
          read
        case WM.CapWrite{}:
          write
        case WM.CapExec{}:
          exec
        case WM.CapNet{}:
          net

def implies(a: Bool, b: Bool) -> Bool:
  Bool.not(a) || b

def can_execute(slot: WM.PassSlot) -> Bool:
  match slot:
    case WM.Slot{consumed, exec_count}:
      Bool.not(consumed)

def is_promoted(fate: WM.Fate) -> Bool:
  match fate:
    case WM.Promote{}:
      True{}
    case WM.Retire{}:
      False{}
    case WM.Quarantine{}:
      False{}

def expected_next_epoch(rev: Nat) -> Nat:
  1n+Nat.add(rev, 0n)
