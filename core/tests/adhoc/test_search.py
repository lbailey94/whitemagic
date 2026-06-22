import json

import whitemagic_rust
from whitemagic.optimization.rust_accelerators import _RUST_SEARCH

print(f"RUST_SEARCH available: {_RUST_SEARCH}")
docs = [{"id": "1", "title": "test", "content": "test content"}]
try:
    docs_json = json.dumps(docs)
    print("Calling rust...")
    result = whitemagic_rust.search_build_index(docs_json)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
