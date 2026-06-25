// backpressure_dispatch - Line protocol bridge for backpressure effect handler
// Protocol: "op:arg1:arg2:..."
// Responses: "ok:result" or "error:message"
//
// Operations:
//   admit:priority       -> ok:true|ok:false
//   release              -> ok:released
//   queue-depth          -> ok:N
//   current-load         -> ok:0.75
//   should-shed          -> ok:true|ok:false
//   strategy             -> ok:reject_all|ok:queue|ok:shed_oldest
//   set-threshold:0.8    -> ok:set
//   request-rate         -> ok:123.4
//   set-rate-limit:100   -> ok:set
//   quit                 -> ok:bye

module backpressure_dispatch
import backpressure
import std/num/float64
import std/os/readline

fun get-field(s: string, n: int): string
  val parts = s.split(":")
  match parts.drop(n).head()
    Just(v) -> v
    Nothing -> ""

fun main()
  val config = backpressure/init-strict-backpressure()
  backpressure/handle-backpressure(config, fn() {
    fun loop(): <backpressure,div,console,exn> ()
      val line = readline()
      if line == "" then
        ()
      else
        val op = get-field(line, 0)

        if op == "admit" then
          val pri = match parse-int(get-field(line, 1))
            Just(n) -> n
            Nothing -> 0
          val result = request-admission(pri)
          if result then
            println("ok:true")
          else
            println("ok:false")

        elif op == "release" then
          release-admission()
          println("ok:released")

        elif op == "queue-depth" then
          val qd = get-queue-depth()
          println("ok:" ++ show(qd))

        elif op == "current-load" then
          val load = get-current-load()
          println("ok:" ++ float64/show(load))

        elif op == "should-shed" then
          val shed = should-shed-load()
          if shed then
            println("ok:true")
          else
            println("ok:false")

        elif op == "strategy" then
          val strat = get-shedding-strategy()
          println("ok:" ++ strat)

        elif op == "set-threshold" then
          val t = match parse-float64(get-field(line, 1))
            Just(f) -> f
            Nothing -> 0.8
          set-shedding-threshold(t)
          println("ok:set")

        elif op == "request-rate" then
          val rate = get-request-rate()
          println("ok:" ++ float64/show(rate))

        elif op == "set-rate-limit" then
          val rps = match parse-float64(get-field(line, 1))
            Just(f) -> f
            Nothing -> 100.0
          set-rate-limit(rps)
          println("ok:set")

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
