# GHC Symbol Loading Issue

**Status**: Known limitation  
**Date**: November 20, 2025  
**Error**: `undefined symbol: stg_gc_unpt_r1`

---

## Problem

The Haskell WhiteMagic-logic library compiles successfully with Stack/GHC but fails to load via Python's ctypes due to missing GHC runtime symbols.

### Error Details
```
libHSghc-prim-0.12.0-d0f9-ghc9.10.3.so: undefined symbol: stg_gc_unpt_r1
```

`stg_gc_unpt_r1` is a GHC garbage collector symbol that requires the full GHC runtime to be properly initialized.

---

## Root Cause

GHC 9.10.3 uses a complex runtime system with interdependent shared libraries. When loading via `ctypes.CDLL`, even with `RTLD_GLOBAL`, the symbol resolution fails because:

1. GHC runtime symbols are not self-contained in individual `.so` files
2. The initialization order matters
3. Some symbols may require static linking

---

## Attempted Fixes

### November 20, 2025
- ✅ Preloaded GHC base libraries (`libHSbase`, `libHSghc-prim`)
- ✅ Used `RTLD_GLOBAL` flag for symbol visibility
- ❌ Still fails with undefined symbol error

---

## Workarounds

### Current Status
**Haskell integration is OPTIONAL** - core functionality does not depend on it.

**What Works**:
- ✅ Rust bindings provide 10-100x speedup for critical operations
- ✅ Python implementations available as fallback
- ✅ System fully functional without Haskell

**What Haskell Would Provide** (if working):
- Pure functional state transitions
- Compile-time type safety for I Ching logic
- Formal verification capabilities
- Category theory operations

---

## Potential Solutions (For Future)

### Option 1: Static Linking
Build Haskell library with static GHC runtime:
```bash
cd whitemagic-logic
stack build --ghc-options="-staticlib -optl-static"
```

### Option 2: GHC API Approach
Use GHC's C API more directly instead of FFI exports.

### Option 3: Separate Haskell Process
Run Haskell logic in separate process and communicate via pipes/sockets.

### Option 4: Different GHC Version
Try older GHC version (e.g., 9.2.x) with simpler runtime.

---

## Impact Assessment

**Low Priority** because:
- Rust provides the needed performance boost
- Python fallbacks work fine
- Haskell features are "nice to have" not "must have"
- Would require significant GHC expertise to fix properly

**Medium/High Effort** because:
- Requires deep GHC runtime knowledge
- May need recompilation with different options
- Platform-specific linking complexities

---

## References

- GHC Foreign Function Interface Guide
- GHC Runtime System Documentation
- Stack/Cabal FFI Best Practices

---

## Recommendation

**Accept as known limitation** for now. Focus on:
1. Rust integration (working perfectly) ✅
2. Python implementations (all working) ✅
3. Core functionality (all operational) ✅

Revisit Haskell integration if:
- User specifically needs pure functional guarantees
- Formal verification becomes critical
- Category theory operations required
- Or if GHC expert available to help

---

**Last Updated**: November 20, 2025  
**Status**: Documented, not blocking
