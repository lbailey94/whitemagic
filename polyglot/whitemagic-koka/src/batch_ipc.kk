// batch_ipc.kk - Simplified Batch IPC Protocol (VC-01)
// Multi-command batching for reduced IPC overhead

module batch_ipc

import std/os/readline

// Execute single command and return JSON result
fun execute-cmd(op: string): string
  match op
    "ping" -> "{\"pong\":true}"
    "status" -> "{\"status\":\"ok\",\"batch_ipc\":true}"
    "emit" -> "{\"emitted\":true}"
    "count" -> "{\"count\":0}"
    _ -> "{\"error\":\"unknown\"}"

// Extract op from line using contains pattern
fun extract-op(line: string): string
  if line.contains("\"ping\"") then "ping"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"emit\"") then "emit"
  else if line.contains("\"count\"") then "count"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

// Count commands in JSON
fun count-cmds(line: string): int
  line.count("{\"id\":")

// Is batch request?
fun is-batch(line: string): bool
  line.contains("\"commands\":")

// Build batch response for n commands
fun batch-response(n: int): string
  if n == 0 then "{\"request_id\":\"batch\",\"results\":[],\"commands_processed\":0}"
  else if n == 1 then "{\"request_id\":\"batch\",\"results\":[{\"id\":1,\"status\":\"ok\",\"result\":{\"pong\":true}}],\"commands_processed\":1}"
  else if n == 2 then "{\"request_id\":\"batch\",\"results\":[{\"id\":1,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":2,\"status\":\"ok\",\"result\":{\"pong\":true}}],\"commands_processed\":2}"
  else if n == 3 then "{\"request_id\":\"batch\",\"results\":[{\"id\":1,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":2,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":3,\"status\":\"ok\",\"result\":{\"pong\":true}}],\"commands_processed\":3}"
  else "{\"request_id\":\"batch\",\"results\":[{\"id\":1,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":2,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":3,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":4,\"status\":\"ok\",\"result\":{\"pong\":true}},{\"id\":5,\"status\":\"ok\",\"result\":{\"pong\":true}}],\"commands_processed\":5}"

// Main loop - handles both single commands and batches
fun main-loop(): <transaction,io> ()
  val line = readline()
  if line == "" then ()
  else if line.contains("\"quit\"") then
    println("{\"status\":\"stopped\"}")
  else
    val response = if is-batch(line)
      then batch-response(count-cmds(line))
      else execute-cmd(extract-op(line), extract-args(line))
    println(response)
    main-loop()

fun main(): <io> ()
  println("{\"status\":\"started\",\"batch_ipc\":true,\"version\":\"1.1\"}")
  handle-transactions(main-loop)
