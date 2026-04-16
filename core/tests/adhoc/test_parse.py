import json

line = '{"status":"telemetry_processed", "latency":"0.01611328125ms", "input_event":{"event_type":404,"sender_hash":107990567,"timestamp":4.000000,"payload":{"interesting":true,"path":"/home/lucas/Desktop/whitemagicdev/koka-clones/grimoire/core_fx.kk","score":10,"size":93,"type":"file_scout"}}}'

data = json.loads(line)
input_event = data.get("input_event", {})
payload = input_event.get("payload", {})

print(payload.get("type"))
