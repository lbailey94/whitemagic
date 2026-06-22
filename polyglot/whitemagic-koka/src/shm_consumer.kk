// shm_consumer.kk - Koka Shared Memory Consumer (Phase 1)
// Uses C helper functions for shared memory access

module shm_consumer

import std/os/readline
import std/num/float64
import std/num/int64


extern flush-stdout() : console ()
  c inline "fflush(stdout)"

// ── FFI Bindings via C file ──────────────────────────────────────────────────


extern import
  c file "shm_consumer.h"

// Open and map shared memory, returns pointer (0 on error)
extern shm-open-map(name: string, size: int): int64
  c "kk_shm_open_map"

// Unmap shared memory
extern shm-unmap(addr: int64, size: int): int
  c "kk_shm_unmap"

// Read int32 at offset
extern shm-read-int(addr: int64, offset: int): int
  c "kk_shm_read_int"

// Read int64 at offset  
extern shm-read-int64(addr: int64, offset: int): int64
  c "kk_shm_read_int64"

// Read double at offset
extern shm-read-double(addr: int64, offset: int): float64
  c "kk_shm_read_double"

// ── Constants ────────────────────────────────────────────────────────────────

val shm-name = "whitemagic_embed_bridge"
val segment-size = 1544704
val header-size = 64
val slot-size = 1544
val embedding-dim = 384
val magic-number = 1464683339  // "WMEM"

// ── Header Structure ──────────────────────────────────────────────────────────

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

// ── IPC Server ────────────────────────────────────────────────────────────────

fun json-header(h: shm-header): string
  "{\"magic\":" ++ show(h.magic) ++
  ",\"version\":" ++ show(h.version) ++
  ",\"capacity\":" ++ show(h.capacity) ++
  ",\"count\":" ++ show(h.count) ++
  ",\"write_pos\":" ++ show(h.write-pos) ++
  ",\"read_pos\":" ++ show(h.read-pos) ++ "}"

fun extract-op(line: string): string
  if line.contains("\"header\"") then "header"
  else if line.contains("\"read\"") then "read"
  else if line.contains("\"status\"") then "status"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun server-loop(addr: int64): io ()
  val line = readline()
  if line == "" then ()
  else
    val op = extract-op(line)
    val response = match op
      "header" ->
        val h = read-header(addr)
        json-header(h)
      "read" ->
        val h = read-header(addr)
        if h.count == 0 then "{\"error\":\"empty\"}"
        else
          val offset = header-size + (h.read-pos * slot-size)
          val id = shm-read-int(addr, offset)
          "{\"id\":" ++ show(id) ++ ",\"dim\":" ++ show(embedding-dim) ++ "}"
      "status" ->
        "{\"shm_consumer\":true,\"addr\":" ++ std/num/int64/show(addr) ++ "}"
      "quit" ->
        "{\"status\":\"stopped\"}"
      _ ->
        "{\"error\":\"unknown op\"}"
    
    println(response)
    flush-stdout()
    
    if op != "quit" then
      server-loop(addr)
    else
      val _ = shm-unmap(addr, segment-size)
      ()

fun main(): io ()
  println("{\"status\":\"starting\",\"shm_consumer\":true,\"target\":\"" ++ shm-name ++ "\"}")
  flush-stdout()
  val addr = shm-open-map(shm-name, segment-size)
  if addr == std/num/int64/int64(0) then
    println("{\"error\":\"failed to open shared memory - producer must create first\"}")
    flush-stdout()
  else
    val header = read-header(addr)
    if header.magic != magic-number then
      println("{\"error\":\"invalid magic - got " ++ show(header.magic) ++ "\"}")
      flush-stdout()
      val _ = shm-unmap(addr, segment-size)
      ()
    else
      println("{\"status\":\"started\",\"connected\":true,\"capacity\":" ++ show(header.capacity) ++ "}")
      flush-stdout()
      server-loop(addr)
