// shm_ring_consumer.kk - Reads real-time Elixir events from SHM ring buffer
module shm_ring_consumer

import std/os/readline
import std/num/int64
import std/core/int
import std/core/string
import std/core/list
import std/core/delayed

extern import
  c file "shm_ring_consumer.h"

extern shm-ring-open(name: string, size: int): int64
  c "kk_shm_ring_open"

extern shm-ring-poll(addr: int64): string
  c "kk_shm_ring_poll"

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

extern sleep-us(us: int): ()
  c inline "usleep(kk_integer_clamp32(us, kk_context()))"

val shm-name = "/whitemagic_event_ring"
val capacity = 65536
val header-size = 64
val slot-size = 256
val segment-size = header-size + (capacity * slot-size)

fun server-loop(addr: int64): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
  
  val event = shm-ring-poll(addr)
  if event != "" then
    println("{\"status\":\"event_received\",\"event\":" ++ event ++ "}")
    flush-stdout()
    // In a real implementation, we would route this to Gan Ying
    server-loop(addr)
  else
    sleep-us(1000) // Sleep 1ms to avoid CPU spinning
    server-loop(addr)

fun main(): io ()
  with handler
    final ctl throw-exn(exn)
      () // Catch EOF globally
      
  println("{\"status\":\"starting\",\"shm_ring_consumer\":true}")
  flush-stdout()
  
  val addr = shm-ring-open(shm-name, segment-size)
  if addr == std/num/int64/int64(0) then
    println("{\"error\":\"failed to open shared memory ring buffer\"}")
    flush-stdout()
  else
    println("{\"status\":\"started\",\"connected\":true}")
    flush-stdout()
    server-loop(addr)
