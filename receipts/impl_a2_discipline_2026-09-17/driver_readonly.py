#!/usr/bin/env python3
"""A2 read-only discipline driver (spec W1_A2 adversarial case 8).

Runs the frozen implementation (commit e3c6c6d) through the stdio harness:
  1. writer process (read-write) ingests two records and stays alive;
  2. read-only reader against the live writer: recall succeeds, batch_create and
     canary are refused, and the store bytes are unchanged by the read;
  3. writer is SIGKILLed (wedged store); a read-only reader still succeeds.

Usage: python3 driver_readonly.py <harness-binary> <workdir>
"""
import hashlib
import json
import os
import subprocess
import sys

BIN = sys.argv[1]
BASE = sys.argv[2]
STORE = os.path.join(BASE, "store")


def store_hashes():
    out = {}
    for name in sorted(os.listdir(STORE)):
        path = os.path.join(STORE, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                out[name] = hashlib.sha256(fh.read()).hexdigest()
    return out


def req(i, route, args):
    return json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                       "params": {"name": "wm", "arguments": {"route": route, "args": args}}})


def replies_of(stdout):
    out = {}
    for line in stdout.splitlines():
        obj = json.loads(line)
        out[obj["id"]] = json.loads(obj["result"]["content"][0]["text"])
    return out


def main() -> int:
    os.makedirs(BASE, exist_ok=True)
    writer_journal = os.path.join(BASE, "writer.jsonl")
    writer = subprocess.Popen(
        [BIN, "serve", "--store", STORE],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, env=dict(os.environ, WM_GEN3_JOURNAL=writer_journal),
    )

    def send(payload):
        writer.stdin.write(payload + "\n")
        writer.stdin.flush()
        return json.loads(writer.stdout.readline())

    ingested = json.loads(send(req(2, "memory.batch_create", {"items": [
        {"content": "the north bay is the current loading area", "galaxy": "codex", "tags": ["a2-ro"]},
        {"content": "the west gate is locked at night", "galaxy": "codex", "tags": ["a2-ro"]},
    ]}))["result"]["content"][0]["text"])
    assert ingested["status"] == "success", ingested
    before = store_hashes()

    reader_alive_journal = os.path.join(BASE, "reader_alive.jsonl")
    payload = "\n".join([
        req(2, "memory.episodic_search", {"query": "north bay"}),
        req(3, "memory.batch_create", {"items": [{"content": "should not write", "galaxy": "codex"}]}),
        req(4, "gen3.canary", {}),
    ]) + "\n"
    reader = subprocess.run(
        [BIN, "serve", "--store", STORE, "--readonly"],
        input=payload, capture_output=True, text=True,
        env=dict(os.environ, WM_GEN3_JOURNAL=reader_alive_journal), timeout=60,
    )
    assert "mode=readonly" in reader.stderr, reader.stderr
    replies = replies_of(reader.stdout)
    assert replies[2]["status"] == "success" and replies[2]["count"] == 1, replies[2]
    assert replies[3]["status"] == "error" and "read-only" in replies[3]["error"], replies[3]
    assert replies[4]["status"] == "error" and "read-only" in replies[4]["error"], replies[4]
    after = store_hashes()
    assert before == after, (before, after)

    writer.kill()
    writer.wait()
    reader_wedged_journal = os.path.join(BASE, "reader_wedged.jsonl")
    wedged = subprocess.run(
        [BIN, "serve", "--store", STORE, "--readonly"],
        input=req(2, "memory.episodic_search", {"query": "north bay"}) + "\n",
        capture_output=True, text=True,
        env=dict(os.environ, WM_GEN3_JOURNAL=reader_wedged_journal), timeout=60,
    )
    replies2 = replies_of(wedged.stdout)
    assert replies2[2]["status"] == "success" and replies2[2]["count"] == 1, replies2[2]

    print("A2-READONLY DEMO PASS")
    print("alive-writer read :", json.dumps({"status": replies[2]["status"], "count": replies[2]["count"]}))
    print("write refused     :", json.dumps({"status": replies[3]["status"], "error": replies[3]["error"]}))
    print("canary refused    :", json.dumps({"status": replies[4]["status"], "error": replies[4]["error"]}))
    print("store unchanged   :", before == after)
    print("wedged-writer read:", json.dumps({"status": replies2[2]["status"], "count": replies2[2]["count"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
