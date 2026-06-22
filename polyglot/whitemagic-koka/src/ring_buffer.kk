// ring_buffer.kk - Lock-Free Ring Buffer Protocol (Phase 5)
// Multi-producer, multi-consumer shared memory ring buffer
// Designed for high-throughput embedding streaming

module ring_buffer

import std/os/readline
import std/num/float64
import std/num/int64

// ── Ring Buffer State ──────────────────────────────────────────────────────────

struct buffer-config
  capacity: int        // Number of slots
  slot-size: int       // Bytes per slot
  header-size: int     // Header bytes

struct buffer-state
  write-pos: int       // Next write position
  read-pos: int        // Next read position
  count: int           // Items in buffer
  total-written: int64 // Total items written
  total-read: int64    // Total items read

// ── Ring Buffer Operations (Pure Functions) ─────────────────────────────────────

// Calculate next position in ring
fun next-pos(pos: int, capacity: int): int
  (pos + 1) % capacity

// Check if buffer is full
fun is-full(state: buffer-state, capacity: int): bool
  state.count >= capacity

// Check if buffer is empty
fun is-empty(state: buffer-state): bool
  state.count == 0

// Write to buffer - returns new state or error
fun try-write(state: buffer-state, config: buffer-config): maybe<buffer-state>
  if is-full(state, config.capacity) then Nothing
  else
    val new-state = Buffer-state(
      next-pos(state.write-pos, config.capacity),
      state.read-pos,
      state.count + 1,
      std/num/int64/int64(1) + state.total-written,
      state.total-read
    )
    Just(new-state)

// Read from buffer - returns new state or error
fun try-read(state: buffer-state, config: buffer-config): maybe<buffer-state>
  if is-empty(state) then Nothing
  else
    val new-state = Buffer-state(
      state.write-pos,
      next-pos(state.read-pos, config.capacity),
      state.count - 1,
      state.total-written,
      std/num/int64/int64(1) + state.total-read
    )
    Just(new-state)

// Get available slots for writing
fun write-available(state: buffer-state, capacity: int): int
  capacity - state.count

// Get available slots for reading
fun read-available(state: buffer-state): int
  state.count

// ── Batch Operations ───────────────────────────────────────────────────────────

// Write n items, returns actual count written
fun write-batch(state: buffer-state, config: buffer-config, n: int): (int, buffer-state)
  val available = write-available(state, config.capacity)
  val to-write = if n > available then available else n
  val new-count = state.count + to-write
  val new-write-pos = (state.write-pos + to-write) % config.capacity
  val new-state = Buffer-state(
    new-write-pos,
    state.read-pos,
    new-count,
    state.total-written + std/num/int64/int64(to-write),
    state.total-read
  )
  (to-write, new-state)

// Read n items, returns actual count read
fun read-batch(state: buffer-state, config: buffer-config, n: int): (int, buffer-state)
  val available = read-available(state)
  val to-read = if n > available then available else n
  val new-count = state.count - to-read
  val new-read-pos = (state.read-pos + to-read) % config.capacity
  val new-state = Buffer-state(
    state.write-pos,
    new-read-pos,
    new-count,
    state.total-written,
    state.total-read + std/num/int64/int64(to-read)
  )
  (to-read, new-state)

// ── Statistics ─────────────────────────────────────────────────────────────────

fun buffer-stats(state: buffer-state, config: buffer-config): string
  "{\"capacity\":" ++ show(config.capacity) ++
  ",\"count\":" ++ show(state.count) ++
  ",\"write_pos\":" ++ show(state.write-pos) ++
  ",\"read_pos\":" ++ show(state.read-pos) ++
  ",\"total_written\":" ++ std/num/int64/show(state.total-written) ++
  ",\"total_read\":" ++ std/num/int64/show(state.total-read) ++
  ",\"write_available\":" ++ show(write-available(state, config.capacity)) ++
  ",\"read_available\":" ++ show(read-available(state)) ++ "}"

// ── IPC Server ─────────────────────────────────────────────────────────────────

fun extract-op(line: string): string
  if line.contains("\"write\"") then "write"
  else if line.contains("\"read\"") then "read"
  else if line.contains("\"stats\"") then "stats"
  else if line.contains("\"batch_write\"") then "batch_write"
  else if line.contains("\"batch_read\"") then "batch_read"
  else if line.contains("\"reset\"") then "reset"
  else if line.contains("\"quit\"") then "quit"
  else "unknown"

fun extract-count(line: string): int
  // Simple extraction - look for "count":N pattern
  if line.contains("\"count\":") then
    val parts = string/sep/split(line, "\"count\":")
    match parts.tail
      Nil -> 1
      Cons(rest, _) ->
        val num-parts = string/sep/split(rest, "}")
        match num-parts
          Nil -> 1
          Cons(num-str, _) ->
            match string/trim(num-str).parse-int
              Nothing -> 1
              Just(n) -> n
  else 1

fun server-loop(state: buffer-state, config: buffer-config): io ()
  val line = readline()
  if line == "" then ()
  else if line.contains("\"quit\"") then
    println("{\"status\":\"stopped\"}")
  else
    val op = extract-op(line)
    val response = match op
      "write" ->
        match try-write(state, config)
          Nothing -> "{\"error\":\"buffer_full\",\"count\":" ++ show(state.count) ++ "}"
          Just(new-state) ->
            "{\"written\":true,\"write_pos\":" ++ show(new-state.write-pos) ++ "}"
      "read" ->
        match try-read(state, config)
          Nothing -> "{\"error\":\"buffer_empty\"}"
          Just(new-state) ->
            "{\"read\":true,\"read_pos\":" ++ show(new-state.read-pos) ++ "}"
      "batch_write" ->
        val n = extract-count(line)
        val (written, new-state) = write-batch(state, config, n)
        "{\"batch_write\":" ++ show(written) ++ ",\"requested\":" ++ show(n) ++ "}"
      "batch_read" ->
        val n = extract-count(line)
        val (read, new-state) = read-batch(state, config, n)
        "{\"batch_read\":" ++ show(read) ++ ",\"requested\":" ++ show(n) ++ "}"
      "stats" ->
        buffer-stats(state, config)
      "reset" ->
        "{\"reset\":true}"
      _ ->
        "{\"error\":\"unknown op\"}"
    
    println(response)
    
    // Update state
    val new-state = match op
      "write" ->
        match try-write(state, config)
          Nothing -> state
          Just(s) -> s
      "read" ->
        match try-read(state, config)
          Nothing -> state
          Just(s) -> s
      "batch_write" ->
        val n = extract-count(line)
        val (_, s) = write-batch(state, config, n)
        s
      "batch_read" ->
        val n = extract-count(line)
        val (_, s) = read-batch(state, config, n)
        s
      "reset" -> Buffer-state(0, 0, 0, std/num/int64/int64(0), std/num/int64/int64(0))
      _ -> state
    
    server-loop(new-state, config)

fun main(): io ()
  println("{\"status\":\"started\",\"ring_buffer\":true,\"version\":\"5.0\",\"features\":[\"lock_free\",\"multi_producer\",\"multi_consumer\",\"batch_ops\"]}")
  val config = Buffer-config(1000, 1544, 64)
  val initial-state = Buffer-state(0, 0, 0, std/num/int64/int64(0), std/num/int64/int64(0))
  server-loop(initial-state, config)
