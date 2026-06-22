import json
import time
import uuid

import pyarrow as pa

import whitemagic_rust

try:
    print("Available in arrow_bridge:", dir(whitemagic_rust.arrow_bridge))

    # Create some mock memories
    mems = []
    for i in range(10):
        mems.append({
            "id": str(uuid.uuid4()),
            "title": f"Test Memory {i}",
            "content": f"Content for memory {i}",
            "importance": 0.5 + (i * 0.05),
            "x": 0.1, "y": 0.2, "z": 0.3, "w": 0.4, "v": 0.5,
            "memory_type": "long_term",
            "tags": ["test", f"tag_{i}"]
        })

    print(f"Encoding {len(mems)} memories to Arrow IPC...")
    start = time.time()
    # Serialize to JSON first as the Rust bridge expects a JSON string
    json_str = json.dumps(mems)
    arrow_bytes = whitemagic_rust.arrow_bridge.arrow_encode_memories(json_str)
    encode_time = time.time() - start
    print(f"Encoded to {len(arrow_bytes)} bytes in {encode_time*1000:.2f}ms")

    # The bytes might be raw JSON if Arrow feature is disabled, but we compiled with --release
    # Let's write to file to inspect
    with open("test_arrow.ipc", "wb") as f:
        f.write(bytes(arrow_bytes))

    # Read back via PyArrow IPC
    try:
        reader = pa.ipc.open_file(pa.py_buffer(bytearray(arrow_bytes)))
        table = reader.read_all()
        print("Decoded table schema:", table.schema)
        print("Row count:", table.num_rows)
        print("First row:", table.to_pylist()[0])
    except Exception as e:
        print("Arrow reading failed:", e)
        print("Maybe it's just JSON?")
        print(bytes(arrow_bytes)[:100])
except Exception as e:
    print("Error:", e)
