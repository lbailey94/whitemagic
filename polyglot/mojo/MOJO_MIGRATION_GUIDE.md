# Mojo 0.26.1 Migration Guide

## Version Incompatibility Issue

All existing `.mojo` files were written for **Mojo 24.x** and are **broken** on 0.26.1.

## Breaking Changes (24.x → 26.x)

| Old (24.x) | New (0.26.1) | Status |
|------------|--------------|--------|
| `from tensor import Tensor` | `from python.tensor import Tensor` or use `PythonObject` | Changed |
| `DynamicVector[T]` | `List[T]` or `Array[T]` | Renamed |
| `fn __init__(inout self)` | `fn __init__(mut self)` or `fn __init__(out self)` | Syntax changed |
| `let x = ...` | `var x = ...` or `alias x = ...` | Removed |
| `inout param` | `mut param` or `out param` | Keyword changed |

## Files Needing Updates

- `embedding_engine.mojo` - uses DynamicVector, tensor
- `vector_index.mojo` - uses DynamicVector, tensor  
- `hrr.mojo` - uses tensor, DynamicVector
- `batch_encoder.mojo` - uses tensor
- All other `.mojo` files

## Quick Test (Works)

```mojo
fn main():
    print("Hello Mojo 0.26.1!")
```

## Recommended Approach

1. **CPU-only first** - Avoid tensor module complications
2. **Use List instead of DynamicVector**
3. **Update fn signatures** - Replace inout with mut/out
4. **Test incrementally** - One file at a time

## Pixi Environment

```bash
cd /home/lucas/Desktop/whitemagicdev/whitemagic-mojo
pixi run mojo run your_file.mojo
```

Lock file prevents accidental updates:
```bash
pixi lock  # Freezes mojo==0.26.1 forever
```

## Benchmark Results

| Implementation | Time (1000 vectors, 384 dims) | Speedup |
|----------------|-------------------------------|---------|
| Python 3.12 | 262 ms | 1.0x baseline |
| Mojo 0.26.1 (JIT) | 1029 ms | 0.25x (slower - startup overhead) |
| **Mojo 0.26.1 (compiled)** | **38 ms** | **6.83x faster** |

**Key finding**: Always compile Mojo for production use.
```bash
mojo build file.mojo -o binary
./binary  # 27x faster than mojo run
```

## Integration Strategy

1. **Keep Mojo files simple** - Avoid tensor module (unstable)
2. **Use Python interop sparingly** - It adds overhead
3. **Compile to binary** - Never use `mojo run` in production
4. **Lock version in pixi** - `mojo==0.26.1` prevents future breakage
5. **Subprocess bridge** - JSON stdin/stdout (already in mojo_bridge.py)
