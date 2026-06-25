// circuit_dispatch - Line protocol bridge for circuit breaker effect handlers
// Compiled to native binary, communicates with Python via stdin/stdout
//
// Protocol: "op:name:arg1:arg2:..."
// Responses: "ok:result" or "error:message"
//
// Operations:
//   check:name           -> ok:closed|ok:open|ok:half-open
//   success:name         -> ok:recorded
//   failure:name         -> ok:recorded
//   reset:name           -> ok:reset
//   configure:name:t:to:hm -> ok:configured
//   bulkhead-enter:name  -> ok:true|ok:false
//   bulkhead-exit:name   -> ok:exited
//   bulkhead-occ:name    -> ok:N
//   quit                 -> ok:bye

module circuit_dispatch
import circuit_breaker
import std/os/readline

fun get-field(s: string, n: int): string
  val parts = s.split(":")
  match parts.drop(n).head()
    Just(v) -> v
    Nothing -> ""

fun main()
  // Initialize circuits and run entire loop inside one handler scope
  // so state (circuits, bulkheads) persists across operations
  circuit_breaker/handle-circuit-breaker(fn() {
    init-fast-circuit("default")
    init-fast-circuit("ollama")
    init-fast-circuit("redis")

    fun loop(): <circuit,div,console,exn> ()
      val line = readline()
      if line == "" then
        ()
      else
        val op = get-field(line, 0)
        val name = get-field(line, 1)

        if op == "check" then
          val state = check-circuit(name)
          println("ok:" ++ state)

        elif op == "success" then
          record-success(name)
          println("ok:recorded")

        elif op == "failure" then
          record-failure(name)
          println("ok:recorded")

        elif op == "reset" then
          reset-circuit(name)
          println("ok:reset")

        elif op == "configure" then
          val threshold = match parse-int(get-field(line, 2))
            Just(n) -> n
            Nothing -> 0
          val timeout = match parse-int(get-field(line, 3))
            Just(n) -> n
            Nothing -> 0
          val half-max = match parse-int(get-field(line, 4))
            Just(n) -> n
            Nothing -> 0
          configure-circuit(name, threshold, timeout, half-max)
          println("ok:configured")

        elif op == "bulkhead-enter" then
          val result = enter-bulkhead(name)
          if result then
            println("ok:true")
          else
            println("ok:false")

        elif op == "bulkhead-exit" then
          exit-bulkhead(name)
          println("ok:exited")

        elif op == "bulkhead-occ" then
          val occ = get-bulkhead-occupancy(name)
          println("ok:" ++ show(occ))

        elif op == "quit" then
          println("ok:bye")

        else
          println("error:unknown op: " ++ op)

        if op != "quit" then
          loop()
        else
          ()

    loop()
  })
