// shm_graph.kk - Zero-copy graph walker via SHM
module shm_graph

import std/os/readline
import std/num/int64
import std/core/int
import std/core/string
import std/core/list
import std/text/parse

extern import
  c file "shm_graph.h"

extern shm-graph-open(name: string, size: int): int64
  c "kk_shm_graph_open"

extern shm-unmap(addr: int64, size: int): int
  c "kk_shm_unmap"

extern shm-read-int(addr: int64, offset: int): int
  c "kk_shm_read_int"

extern shm-graph-walk(addr: int64, count: int, start-id: int, hops: int): string
  c "kk_shm_graph_walk"

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

val shm-name = "/whitemagic_graph_bridge"
val magic-number = 0x47525048 // "GRPH"
val header-size = 64
val slot-size = 16
val capacity = 3000000
val segment-size = header-size + (capacity * slot-size)

struct header
  magic: int
  version: int
  capacity: int
  count: int

fun read-header(addr: int64): header
  val m = shm-read-int(addr, 0)
  val v = shm-read-int(addr, 4)
  val cap = shm-read-int(addr, 8)
  val c = shm-read-int(addr, 12)
  Header(m, v, cap, c)

fun extract-op(line: string): string
  if line.contains("\"walk\"") then "walk"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-start-id(line: string): int
  val parts = line.split("\"start_id\":")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split("}")
        Cons(id, _) -> 
          match parse-int(id.trim())
            Just(i) -> i
            Nothing -> 0
        _ -> 0
    _ -> 0
    _ -> 0

fun server-loop(addr: int64): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF
  val line = readline()
  if line == "" then ()
  else
    val op = extract-op(line)
    val response = match op
      "walk" ->
        val start-id = extract-start-id(line)
        val h = read-header(addr)
        if h.count == 0 then "{\"error\":\"empty\"}"
        else
          val res = shm-graph-walk(addr, h.count, start-id, 3)
          "{\"status\":\"ok\",\"results\":" ++ res ++ "}"
      "status" ->
        val h = read-header(addr)
        "{\"shm_graph\":true,\"count\":" ++ show(h.count) ++ "}"
      "quit" ->
        "{\"status\":\"stopped\"}"
      _ ->
        "{\"error\":\"unknown op\"}"
    
    println(response)
    flush-stdout()
    
    if op != "quit" then server-loop(addr)
    else
      val _ = shm-unmap(addr, segment-size)
      ()

fun main(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  println("{\"status\":\"starting\",\"shm_graph\":true}")
  flush-stdout()
  
  val addr = shm-graph-open(shm-name, segment-size)
  if addr == std/num/int64/int64(0) then
    println("{\"error\":\"failed to open shared memory\"}")
    flush-stdout()
  else
    val h = read-header(addr)
    if h.magic != magic-number then
      println("{\"error\":\"invalid magic\"}")
      val _ = shm-unmap(addr, segment-size)
      flush-stdout()
    else
      println("{\"status\":\"started\",\"connected\":true}")
      flush-stdout()
      server-loop(addr)
