// shm_search.kk - Zero-copy memory search via SHM
module shm_search

import std/os/readline
import std/num/float64
import std/num/int64
import std/core/list
import std/core/string
import std/core/int

extern import
  c file "shm_search.h"

// Open and map shared memory, returns pointer (0 on error)
extern shm-open-map(name: string, size: int): int64
  c "kk_shm_open_map"

// Unmap shared memory
extern shm-unmap(addr: int64, size: int): int
  c "kk_shm_unmap"

// Read int32 at offset
extern shm-read-int(addr: int64, offset: int): int
  c "kk_shm_read_int"

// Fast C-optimized cosine similarity
extern shm-search-top5(addr: int64, count: int, query-item-id: int): string
  c "kk_shm_search_top5"

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

// -- Constants ----------------------------------------------------------------

val shm-name = "/whitemagic_embed_bridge_real"
val segment-size = 30800064
val header-size = 64
val slot-size = 1540 // id (4 bytes) + 384 float32 (1536 bytes)
val embedding-dim = 384
val magic-number = 1464683339  // "WMKK"

// -- Header Structure ----------------------------------------------------------

struct shm-header
  magic: int
  version: int
  capacity: int
  count: int
  write-pos: int
  read-pos: int

fun read-header(addr: int64): shm-header
  Shm-header(
    shm-read-int(addr, 0),
    shm-read-int(addr, 4),
    shm-read-int(addr, 8),
    shm-read-int(addr, 12),
    shm-read-int(addr, 16),
    shm-read-int(addr, 20)
  )

// ── Server Loop ──

fun extract-op(line: string): string
  if line.contains("\"search\"") then "search"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-query-id(line: string): int
  val parts = line.split("\"query_id\":")
  match parts
    Cons(_, Cons(rest, _)) ->
      match rest.split(",")
        Cons(id, _) -> 
          match parse-int(id.trim())
            Just(i) -> i
            Nothing -> 0
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
      "search" ->
        val q-id = extract-query-id(line)
        val h = read-header(addr)
        if h.count == 0 then "{\"error\":\"empty\"}"
        else
          val best = shm-search-top5(addr, h.count, q-id)
          "{\"status\":\"ok\",\"results\":" ++ best ++ "}"
      "status" ->
        val h = read-header(addr)
        "{\"shm_consumer\":true,\"count\":" ++ show(h.count) ++ "}"
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
  println("{\"status\":\"starting\",\"shm_search\":true}")
  flush-stdout()
  
  val addr = shm-open-map(shm-name, segment-size)
  if addr == std/num/int64/int64(0) then
    println("{\"error\":\"failed to open shared memory\"}")
    flush-stdout()
  else
    val header = read-header(addr)
    if header.magic != magic-number then
      println("{\"error\":\"invalid magic\"}")
      val _ = shm-unmap(addr, segment-size)
      flush-stdout()
    else
      println("{\"status\":\"started\",\"connected\":true}")
      flush-stdout()
      server-loop(addr)
