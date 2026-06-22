// coordination - Koka Migration (PSR-008)
// Type-safe coordination using algebraic effects
// Provides provable correctness for distributed system coordination

module coordination

import std/num/int64
import std/time

// ═══════════════════════════════════════════════════════════════════════════
// Coordination Effect Definition
// ═══════════════════════════════════════════════════════════════════════════

effect coordination
  // Distributed coordination primitives
  fun acquire-lock(name: string): bool  // returns true if acquired
  fun release-lock(name: string): ()
  fun try-acquire-lock(name: string, timeout: int): bool
  
  // Barrier synchronization
  fun await-barrier(barrier-id: string, participants: int): ()
  fun signal-barrier(barrier-id: string): ()
  
  // Leader election
  fun propose-leader(node-id: string): bool  // returns true if elected
  fun get-current-leader(): string
  fun resign-leadership(): ()
  
  // Distributed state
  fun get-shared-state(key: string): maybe<string>
  fun set-shared-state(key: string, value: string): ()
  fun cas-state(key: string, expected: string, new: string): bool  // compare-and-swap
  
  // Coordination metadata
  fun get-coordinator-id(): string
  fun get-participant-count(): int

// ═══════════════════════════════════════════════════════════════════════════
// Coordination Types
// ═══════════════════════════════════════════════════════════════════════════

type lock-state
  Free
  Held(string, int)  // holder, timestamp
  Contended(list<string>)  // waiters

type barrier-state
  Waiting(int, int)  // current, target
  Released

type election-state
  NoLeader
  Election(list<string>)  // candidates
  Leader(string, int)  // leader, term

struct coordination-context
  coordinator-id: string
  locks: list<(string, lock-state)>
  barriers: list<(string, barrier-state)>
  election: election-state
  shared-state: list<(string, string)>
  participant-count: int

// ═══════════════════════════════════════════════════════════════════════════
// Coordination Handler
// ═══════════════════════════════════════════════════════════════════════════

fun handle-coordination(initial-context: coordination-context, action: () -> <coordination> a): a
  var context := initial-context
  
  handle action
    fun acquire-lock(name)
      match context.locks.find(fn(l) l.fst == name)
        Just((_, Held(holder, _))) ->
          if holder == context.coordinator-id then True
          else False  // Already held by another
        Just((_, Contended(waiters))) ->
          // Add to waiters
          val new-waiters = Cons(context.coordinator-id, waiters)
          val new-state = Contended(new-waiters)
          context.locks := Cons((name, new-state), 
                               context.locks.filter(fn(l) l.fst != name))
          False
        Just((_, Free)) ->
          // Acquire lock
          val new-state = Held(context.coordinator-id, ticks())
          context.locks := Cons((name, new-state), 
                               context.locks.filter(fn(l) l.fst != name))
          True
        Nothing ->
          // Create new lock and acquire
          val new-state = Held(context.coordinator-id, ticks())
          context.locks := Cons((name, new-state), context.locks)
          True
    
    fun release-lock(name)
      match context.locks.find(fn(l) l.fst == name)
        Just((_, Held(holder, _))) ->
          if holder == context.coordinator-id then
            // Check if there are waiters
            match context.locks.find(fn(l) l.fst == name)
              Just((_, Contended(waiters))) ->
                val new-holder = match waiters
                  Nil -> ""
                  Cons(h, _) -> h
                val new-waiters = match waiters
                  Nil -> []
                  Cons(_, t) -> t
                if new-holder == "" then
                  context.locks := Cons((name, Free), 
                                       context.locks.filter(fn(l) l.fst != name))
                else
                  context.locks := Cons((name, Held(new-holder, ticks())), 
                                       context.locks.filter(fn(l) l.fst != name))
              _ ->
                context.locks := Cons((name, Free), 
                                     context.locks.filter(fn(l) l.fst != name))
        _ -> ()
    
    fun try-acquire-lock(name, timeout)
      val start = ticks()
      var acquired = acquire-lock(name)
      
      while !acquired && (ticks() - start) < timeout do
        acquired = acquire-lock(name)
      
      acquired
    
    fun await-barrier(barrier-id, participants)
      match context.barriers.find(fn(b) b.fst == barrier-id)
        Just((_, Waiting(current, target))) ->
          val new-current = current + 1
          if new-current >= target then
            context.barriers := Cons((barrier-id, Released), 
                                    context.barriers.filter(fn(b) b.fst != barrier-id))
          else
            context.barriers := Cons((barrier-id, Waiting(new-current, target)), 
                                    context.barriers.filter(fn(b) b.fst != barrier-id))
        Nothing ->
          context.barriers := Cons((barrier-id, Waiting(1, participants)), 
                                  context.barriers)
    
    fun signal-barrier(barrier-id)
      match context.barriers.find(fn(b) b.fst == barrier-id)
        Just((_, Waiting(current, target))) ->
          context.barriers := Cons((barrier-id, Released), 
                                  context.barriers.filter(fn(b) b.fst != barrier-id))
        _ -> ()
    
    fun propose-leader(node-id)
      match context.election
        NoLeader ->
          context.election := Leader(node-id, 1)
          True
        Election(candidates) ->
          context.election := Leader(node-id, 1)
          True
        Leader(_, term) ->
          val new-term = term + 1
          context.election := Leader(node-id, new-term)
          True
    
    fun get-current-leader()
      match context.election
        Leader(leader, _) -> leader
        _ -> ""
    
    fun resign-leadership()
      context.election := NoLeader
    
    fun get-shared-state(key)
      match context.shared-state.find(fn(s) s.fst == key)
        Just((_, value)) -> Just(value)
        Nothing -> Nothing
    
    fun set-shared-state(key, value)
      context.shared-state := Cons((key, value), 
                                  context.shared-state.filter(fn(s) s.fst != key))
    
    fun cas-state(key, expected, new)
      match context.shared-state.find(fn(s) s.fst == key)
        Just((_, current)) ->
          if current == expected then
            context.shared-state := Cons((key, new), 
                                        context.shared-state.filter(fn(s) s.fst != key))
            True
          else False
        Nothing -> False
    
    fun get-coordinator-id()
      context.coordinator-id
    
    fun get-participant-count()
      context.participant-count

// ═══════════════════════════════════════════════════════════════════════════
// Coordination Helpers
// ═══════════════════════════════════════════════════════════════════════════

fun with-lock(name: string, action: () -> a): <coordination> a
  if !acquire-lock(name) then
    action()
  else
    val result = action()
    release-lock(name)
    result

fun with-barrier(barrier-id: string, participants: int, action: () -> a): <coordination> a
  await-barrier(barrier-id, participants)
  val result = action()
  signal-barrier(barrier-id)
  result

fun atomic-cas(key: string, expected: string, action: () -> string): <coordination> string
  if cas-state(key, expected, expected) then
    val new-value = action()
    set-shared-state(key, new-value)
    new-value
  else
    expected
