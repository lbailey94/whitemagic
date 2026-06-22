# WhiteMagic WASM Python Package

Python wrapper for WhiteMagic WebAssembly runtime - edge inference and vector operations in the browser.

## Installation

```bash
pip install whitemagic-wasm
```

## Usage

```python
import whitemagic_wasm as wm

# Check if WASM is available
print(wm.is_wasm_available())  # True

# Get WASM info
info = wm.get_wasm_info()
print(f"WASM size: {info['wasm_size_bytes']} bytes")

# Load WASM binary for use with wasmtime or similar
engine = wm.EdgeEngine()
wasm_bytes = engine.get_wasm_bytes()
js_source = engine.get_js_source()
```

## Features

- Pre-built WASM binaries included
- No external dependencies
- Type hints included
- Cross-platform (any Python 3.9+)

## License

MIT
