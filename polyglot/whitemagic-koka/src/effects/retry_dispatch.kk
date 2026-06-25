// retry_dispatch - Line protocol bridge for retry effect handler
// Protocol: "op:arg1:arg2:..."
// Responses: "ok:result" or "error:message"
//
// Operations:
//   attempt:desc         -> ok:1
//   should-retry         -> ok:true|ok:false
//   attempt-count        -> ok:3
//   max-attempts         -> ok:5
//   backoff-delay        -> ok:400
//   set-strategy:name:base:max -> ok:set
//   record-exhausted     -> ok:recorded
//   was-successful       -> ok:true|ok:false
//   quit                 -> ok:bye

module retry_dispatch
import retry_logic
import std/os/readline

fun get-field(s: string, n: int): string
  val parts = s.split(":")
  match parts.drop(n).head()
    Just(v) -> v
    Nothing -> ""

fun main()
  retry_logic/handle-retry(5, fn() {
    fun loop(): <retry,div,console,exn> ()
      val line = readline()
      if line == "" then
        ()
      else
        val op = get-field(line, 0)

        if op == "attempt" then
          val desc = get-field(line, 1)
          val n = attempt(desc)
          println("ok:" ++ show(n))

        elif op == "should-retry" then
          val sr = should-retry()
          if sr then
            println("ok:true")
          else
            println("ok:false")

        elif op == "attempt-count" then
          val c = get-attempt-count()
          println("ok:" ++ show(c))

        elif op == "max-attempts" then
          val m = get-max-attempts()
          println("ok:" ++ show(m))

        elif op == "backoff-delay" then
          val d = get-backoff-delay()
          println("ok:" ++ show(d))

        elif op == "set-strategy" then
          val strat = get-field(line, 1)
          val base = match parse-int(get-field(line, 2))
            Just(n) -> n
            Nothing -> 100
          val max-d = match parse-int(get-field(line, 3))
            Just(n) -> n
            Nothing -> 30000
          set-backoff-strategy(strat, base, max-d)
          println("ok:set")

        elif op == "record-exhausted" then
          record-retry-exhausted()
          println("ok:recorded")

        elif op == "was-successful" then
          val s = was-successful()
          if s then
            println("ok:true")
          else
            println("ok:false")

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
