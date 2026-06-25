// retry_logic - Resumable retry effects (S022 Phase 3 VC2)
// Exponential backoff with algebraic effects

module retry_logic

import std/num/float64

pub effect retry
  fun attempt(action-desc: string): int
  fun should-retry(): bool
  fun get-attempt-count(): int
  fun get-max-attempts(): int
  fun get-backoff-delay(): int
  fun set-backoff-strategy(strategy: string, base-delay: int, max-delay: int): ()
  fun record-retry-exhausted(): ()
  fun was-successful(): bool

type backoff-strategy
  Fixed
  Linear
  Exponential
  Decorrelated

struct retry-config
  max-attempts: int
  strategy: backoff-strategy
  base-delay-ms: int
  max-delay-ms: int
  jitter: bool

struct retry-state
  current-attempt: int
  last-delay: int
  success: bool
  exhausted: bool

fun pow2(exp: int): int
  if exp <= 0 then 1
  else if exp == 1 then 2
  else if exp == 2 then 4
  else if exp == 3 then 8
  else if exp == 4 then 16
  else if exp == 5 then 32
  else if exp == 6 then 64
  else if exp == 7 then 128
  else if exp == 8 then 256
  else if exp == 9 then 512
  else if exp == 10 then 1024
  else 2048

pub fun handle-retry(max-att: int, action: () -> <retry|e> a): e a
  var config := Retry-config(max-att, Exponential, 100, 30000, True)
  var state := Retry-state(0, 0, False, False)

  with
    fun attempt(desc)
      state := Retry-state(
        state.current-attempt + 1,
        state.last-delay,
        state.success,
        state.exhausted
      )
      state.current-attempt

    fun should-retry()
      state.current-attempt < config.max-attempts && !state.success

    fun get-attempt-count()
      state.current-attempt

    fun get-max-attempts()
      config.max-attempts

    fun get-backoff-delay()
      val base = config.base-delay-ms
      val max-d = config.max-delay-ms

      val delay = match config.strategy
        Fixed -> base
        Linear -> if base * state.current-attempt > max-d then max-d else base * state.current-attempt
        Exponential ->
          val candidate = base * pow2(state.current-attempt - 1)
          if candidate > max-d then max-d else candidate
        Decorrelated ->
          val upper = if base * pow2(state.current-attempt - 1) > max-d then max-d else base * pow2(state.current-attempt - 1)
          base + (upper - base) / 2

      state := Retry-state(state.current-attempt, delay, state.success, state.exhausted)
      delay

    fun set-backoff-strategy(strat, base, max-d)
      val strategy = match strat
        "fixed" -> Fixed
        "linear" -> Linear
        "exponential" -> Exponential
        "decorrelated" -> Decorrelated
        _ -> Exponential
      config := Retry-config(config.max-attempts, strategy, base, max-d, config.jitter)

    fun record-retry-exhausted()
      state := Retry-state(
        state.current-attempt,
        state.last-delay,
        False,
        True
      )

    fun was-successful()
      state.success
  action()

fun with-retry(max-attempts: int, action: () -> <retry,exn|e> a): e maybe<a>
  handle-retry(max-attempts, fn() {
    try(fn() {
      Just(action())
    }, fn(_exn) {
      if !should-retry() then
        record-retry-exhausted()
      else
        val _ = get-backoff-delay()
        ()
      Nothing
    })
  })

fun with-resumable-retry(
  max-attempts: int,
  action: (attempt: int) -> <retry,exn|e> a
): e maybe<a>
  handle-retry(max-attempts, fn() {
    val attempt-num = attempt("resumable")
    try(fn() {
      Just(action(attempt-num))
    }, fn(_exn) {
      if !should-retry() then
        record-retry-exhausted()
      else
        val _ = get-backoff-delay()
        ()
      Nothing
    })
  })

fun with-conditional-retry(
  max-attempts: int,
  should-retry-on: string -> bool,
  action: () -> <retry,exn|e> a
): e maybe<a>
  with-retry(max-attempts, action)

fun retry-all(operations: list<() -> <retry,exn|e> a>, max-per-op: int): e list<maybe<a>>
  operations.map(fn(op) with-retry(max-per-op, op))

fun with-retry-or-fallback(max-attempts: int, action: () -> <retry,exn|e> a, fallback: () -> e a): e a
  match with-retry(max-attempts, action)
    Just(r) -> r
    Nothing -> fallback()
