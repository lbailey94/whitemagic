// transactions_dispatch - Line protocol bridge for transaction effect handler
// Protocol: "op:arg1:arg2:..."
// Responses: "ok:result" or "error:message"
//
// Operations:
//   begin                -> ok:tx_0
//   commit:tx_id         -> ok:true|ok:false
//   rollback:tx_id       -> ok:true|ok:false
//   status:tx_id         -> ok:active|ok:committed|ok:rolled_back|ok:unknown
//   savepoint:tx_id      -> ok:sp_1
//   in-tx                -> ok:true|ok:false
//   current-tx           -> ok:tx_0|ok:
//   prepare:tx_id        -> ok:true|ok:false
//   confirm:tx_id        -> ok:true|ok:false
//   quit                 -> ok:bye

module transactions_dispatch
import transactions
import std/os/readline

fun get-field(s: string, n: int): string
  val parts = s.split(":")
  match parts.drop(n).head()
    Just(v) -> v
    Nothing -> ""

fun main()
  transactions/handle-transactions(fn() {
    fun loop(): <transaction,div,console,exn> ()
      val line = readline()
      if line == "" then
        ()
      else
        val op = get-field(line, 0)

        if op == "begin" then
          val tx-id = begin-tx()
          println("ok:" ++ tx-id)

        elif op == "commit" then
          val tx-id = get-field(line, 1)
          val result = commit-tx(tx-id)
          if result then
            println("ok:true")
          else
            println("ok:false")

        elif op == "rollback" then
          val tx-id = get-field(line, 1)
          val result = rollback-tx(tx-id)
          if result then
            println("ok:true")
          else
            println("ok:false")

        elif op == "status" then
          val tx-id = get-field(line, 1)
          val status = get-tx-status(tx-id)
          println("ok:" ++ status)

        elif op == "savepoint" then
          val tx-id = get-field(line, 1)
          val sp = create-savepoint(tx-id)
          println("ok:" ++ sp)

        elif op == "in-tx" then
          val in-tx = is-in-tx()
          if in-tx then
            println("ok:true")
          else
            println("ok:false")

        elif op == "current-tx" then
          val current = get-current-tx()
          println("ok:" ++ current)

        elif op == "prepare" then
          val tx-id = get-field(line, 1)
          val result = prepare-tx(tx-id)
          if result then
            println("ok:true")
          else
            println("ok:false")

        elif op == "confirm" then
          val tx-id = get-field(line, 1)
          val result = confirm-tx(tx-id)
          if result then
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
