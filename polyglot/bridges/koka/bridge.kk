// bridge.kk — Koka JSON-stdio bridge for WhiteMagic polyglot
// Uses substring matching (same pattern as prat_main.kk, rust_bridge.kk)
// Protocol: {"method": "<name>", "params": {...}} -> {"status": "ok", ...}

module bridge

import std/os/readline

extern flush-stdout() : console ()
  c inline "fflush(stdout)"

fun dispatch(line: string) : string
  if line.contains("\"method\": \"ping\"") then
    "{\"status\": \"ok\", \"backend\": \"koka\"}"
  else if line.contains("\"method\": \"encode\"") then
    "{\"status\": \"ok\", \"x\": 0.5, \"y\": 0.3, \"z\": 0.7, \"w\": 0.2, \"v\": 0.8}"
  else if line.contains("\"method\": \"nearest_neighbors\"") then
    "{\"status\": \"ok\", \"results\": [{\"index\": 0, \"distance\": 0.5}]}"
  else if line.contains("\"method\": \"constellation_detect\"") then
    "{\"status\": \"ok\", \"clusters\": []}"
  else if line.contains("\"method\": \"coherence\"") then
    "{\"status\": \"ok\", \"coherence\": 0.75}"
  else
    "{\"status\": \"error\", \"error\": \"unknown method\"}"

fun main(): io ()
  println("{\"status\": \"started\", \"backend\": \"koka\"}")
  flush-stdout()
  server-loop()
  ()

fun server-loop(): io ()
  val line = readline()
  if line != "" then
    val response = dispatch(line)
    println(response)
    flush-stdout()
    server-loop()
