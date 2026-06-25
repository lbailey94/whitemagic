// timeout_dispatch - Line protocol bridge for timeout effect handler
// Protocol: "op:arg1:arg2:..."
// Responses: "ok:result" or "error:message"
//
// Operations:
//   set:ms               -> ok:set
//   get                  -> ok:5000
//   extend:ms            -> ok:extended
//   clear                -> ok:cleared
//   is-timed-out         -> ok:true|ok:false
//   time-remaining       -> ok:3000
//   push:ms              -> ok:pushed
//   pop                  -> ok:popped
//   quit                 -> ok:bye

module timeout_dispatch
import timeout
import std/os/readline

fun get-field(s: string, n: int): string
  val parts = s.split(":")
  match parts.drop(n).head()
    Just(v) -> v
    Nothing -> ""

fun main()
  timeout/handle-timeout(5000, fn() {
    fun loop(): <timeout,div,console,exn> ()
      val line = readline()
      if line == "" then
        ()
      else
        val op = get-field(line, 0)

        if op == "set" then
          val ms = match parse-int(get-field(line, 1))
            Just(n) -> n
            Nothing -> 5000
          set-timeout(ms)
          println("ok:set")

        elif op == "get" then
          val ms = get-timeout()
          println("ok:" ++ show(ms))

        elif op == "extend" then
          val ms = match parse-int(get-field(line, 1))
            Just(n) -> n
            Nothing -> 1000
          extend-timeout(ms)
          println("ok:extended")

        elif op == "clear" then
          clear-timeout()
          println("ok:cleared")

        elif op == "is-timed-out" then
          val timed = is-timed-out()
          if timed then
            println("ok:true")
          else
            println("ok:false")

        elif op == "time-remaining" then
          val rem = time-remaining()
          println("ok:" ++ show(rem))

        elif op == "push" then
          val ms = match parse-int(get-field(line, 1))
            Just(n) -> n
            Nothing -> 5000
          push-timeout(ms)
          println("ok:pushed")

        elif op == "pop" then
          pop-timeout()
          println("ok:popped")

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
