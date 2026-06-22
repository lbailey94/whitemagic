# Polyglot Toolchain Setup Guide

**Last Updated**: February 16, 2026  
**Purpose**: Complete documentation for setting up all polyglot languages (Rust, Zig, Koka, Mojo) in WhiteMagic

This guide documents the exact steps needed to set up the polyglot toolchain from scratch, in case we need to repeat the process in new sessions or environments.

---

## 🔍 IMPORTANT: Venv Discovery

**Key Finding**: The WhiteMagic venv already contains working Rust bindings!

### Quick Check
```bash
cd /path/to/whitemagic-core
source .venv/bin/activate
python3 -c "import whitemagic_rs; print('✅ Rust bridge works!')"
```

### What's in the Venv
- **whitemagic_rs** (v11.0.0) — Custom Rust bridge (6.7M binary)
- **orjson** (v3.11.7) — Fast JSON library (Rust-based, 3-6× speedup)
- **py_rust_stemmers** (v0.1.5) — Rust text processing
- **ruff** — Fast linter (also Rust-based!)

### Critical Rule
**Always activate venv before running WhiteMagic**:
```bash
source .venv/bin/activate
```

System Python (`/usr/bin/python3`) won't have access to Rust bindings. Only venv Python (`.venv/bin/python3`) has them.

See `docs/VENV_POLYGLOT_DISCOVERIES.md` for complete details.

---

## 🦀 Rust Setup

### Installation Status
✅ **Working** — Rust bridge compiles and Python can import it

### Prerequisites
```bash
# Rust toolchain (usually already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Maturin for Python bindings
pip install maturin
```

### Compilation Steps

1. **Navigate to Rust directory**
```bash
cd whitemagic-rust
```

2. **Build with cargo** (verify compilation works)
```bash
cargo build --release --features python
```

Expected output:
```
Finished `release` profile [optimized] target(s) in 1m 18s
```

3. **Install Python bindings with maturin**
```bash
maturin develop --release
```

Expected output:
```
🔗 Found pyo3 bindings
🐍 Found CPython 3.12 at /path/to/.venv/bin/python
📡 Using build options features from pyproject.toml
   Compiling whitemagic v15.0.0
    Finished `release` profile [optimized] target(s) in 1m 54s
📦 Built wheel for CPython 3.12
✏️ Setting installed package as editable
🛠 Installed whitemagic-rs-11.0.0
```

### Verification

**Test import:**
```bash
python3 -c "import whitemagic_rs; print('✅ Rust bridge loaded!'); print('Functions:', [x for x in dir(whitemagic_rs) if not x.startswith('_')][:10])"
```

Expected output:
```
✅ Rust bridge loaded!
Functions: ['HarmonyVector', 'PatternEngine', 'RrfResult', 'RustEventProcessor', 'SpatialIndex', 'SpatialIndex5D', 'WalkNode', 'arrow_decode_memories', 'arrow_encode_memories', 'arrow_roundtrip_bench']
```

**Test PolyglotRouter:**
```bash
python3 -c "from whitemagic.optimization.polyglot_router import PolyglotRouter; r = PolyglotRouter(); print(f'Rust: {r._rust_available}')"
```

Expected output:
```
🦀 Rust bridge available - 10-100x speedup enabled
Rust: True
```

### Common Issues

**Issue 1: ModuleNotFoundError: No module named 'whitemagic_rs'**

**Cause**: Using system Python instead of venv Python, or maturin not run

**Solution**:
```bash
# Activate venv first
source .venv/bin/activate

# Then run maturin
cd whitemagic-rust
maturin develop --release
```

**Issue 2: PolyglotRouter shows Rust=False**

**Cause**: The `_check_rust()` method was using `find_spec()` which doesn't work reliably with maturin packages

**Solution**: Fixed in commit by changing to direct import:
```python
def _check_rust(self) -> bool:
    try:
        import whitemagic_rs  # Direct import instead of find_spec
        return True
    except ImportError:
        return False
```

**Issue 3: Zig library warning during Rust compilation**

**Cause**: Rust build.rs looks for Zig library but it's optional

**Solution**: This is just a warning, safe to ignore:
```
warning: Zig static library not found at /path/to/whitemagic-zig/zig-out/lib
Proceeding without Zig acceleration.
```

### File Locations

- **Source**: `whitemagic-rust/src/`
- **Cargo.toml**: `whitemagic-rust/Cargo.toml`
- **Compiled library**: `whitemagic-rust/target/release/libwhitemagic_rs.so`
- **Installed module**: `.venv/lib/python3.12/site-packages/whitemagic_rs/`

---

## ⚡ Zig Setup

### Installation Status
✅ **Working** — Zig 0.15.2 compiles successfully, library available

### Prerequisites
```bash
# Zig 0.15.2 (check version)
zig version
# Should output: 0.15.2
```

### Compilation Steps

1. **Navigate to Zig directory**
```bash
cd whitemagic-zig
```

2. **Build with zig build**
```bash
zig build
```

Expected output:
```
(No output = success)
```

3. **Verify library exists**
```bash
ls -lh zig-out/lib/
```

Expected output:
```
-rwxrwxr-x 1 user user 8.5M Feb 16 10:16 libwhitemagic.so
-rw-rw-r-- 1 user user 6.6M Feb 16 10:17 libwhitemagic-zig.a
```

### Verification

**Test PolyglotRouter:**
```bash
python3 -c "from whitemagic.optimization.polyglot_router import PolyglotRouter; r = PolyglotRouter(); print(f'Zig: {r._zig_available}')"
```

Expected output:
```
⚡ Zig determinism available - Low-level systems speedup enabled
Zig: True
```

### Common Issues

**Issue 1: Zig API breaking changes (0.15.2)**

**Status**: ✅ **NOT AN ISSUE** — Our code is already compatible with 0.15.2

Previous concerns about `ArrayList.init()` and `File.writer()` API changes were unfounded. Our codebase doesn't use these patterns, so no fixes needed.

**Issue 2: PolyglotRouter can't find Zig library**

**Cause**: Library not compiled or wrong path

**Solution**:
```bash
cd whitemagic-zig
zig build
# Verify: ls zig-out/lib/libwhitemagic.so
```

The PolyglotRouter looks for: `whitemagic-zig/zig-out/lib/libwhitemagic.so`

### File Locations

- **Source**: `whitemagic-zig/src/`
- **Build file**: `whitemagic-zig/build.zig`
- **Compiled library**: `whitemagic-zig/zig-out/lib/libwhitemagic.so`
- **Static library**: `whitemagic-zig/zig-out/lib/libwhitemagic-zig.a`

---

## 🔥 Koka Setup

### Installation Status
✅ **Working** — Koka v3.2.2 installed and operational

### Installation Steps

1. **Run official installer**
```bash
curl -sSL https://github.com/koka-lang/koka/releases/latest/download/install.sh | sh
```

This will:
- Install ninja-build dependency (via apt)
- Download Koka v3.2.2 binary
- Install to `/usr/local/bin/koka`
- Install libraries to `/usr/local/lib/koka/v3.2.2`
- Install sources to `/usr/local/share/koka/v3.2.2`

Expected output:
```
Installing koka v3.2.2 for ubuntu linux-x64
Installing dependencies..
[sudo] password for user:
...
Install successful.

--------------------------------------------------
Installed Koka v3.2.2 at /usr/local/bin/koka

Type 'koka' to enter the interactive compiler
```

### Verification

**Test version:**
```bash
koka --version
```

Expected output:
```
Koka 3.2.2, 20:30:51 Jul 22 2025 (ghc release version)
version: 3.2.2
bin    : /usr/local/bin
lib    : /usr/local/lib/koka/v3.2.2
share  : /usr/local/share/koka/v3.2.2
output : .koka/v3.2.2/gcc-debug-4ec914
cc     : /usr/bin/gcc
flags  : 4ec914
```

**Test compilation:**
```bash
which koka
# Should output: /usr/local/bin/koka
```

### Common Issues

**Issue 1: Permission denied**

**Cause**: Installer needs sudo for /usr/local

**Solution**: Enter password when prompted during installation

**Issue 2: ninja-build not found**

**Cause**: Missing dependency

**Solution**: Installer handles this automatically via apt

### Integration with WhiteMagic

Koka will be used for:
1. **Shadow clone orchestration** — Effect-based coordination
2. **Campaign strategy composition** — Effect handlers for different strategies
3. **Type-safe deployment** — Compile-time verification

**Compilation target**: Koka → C → link with Rust → expose to Python

### File Locations

- **Binary**: `/usr/local/bin/koka`
- **Libraries**: `/usr/local/lib/koka/v3.2.2/`
- **Sources**: `/usr/local/share/koka/v3.2.2/`
- **Output**: `.koka/v3.2.2/gcc-debug-4ec914/`

---

## 🔥 Mojo Setup

### Installation Status
⚠️ **IN PROGRESS** — Pixi installed, Mojo installation pending

### Prerequisites

1. **Pixi package manager**
```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Expected output:
```
This script will automatically download and install Pixi (latest) for you.
Getting it from this url: https://github.com/prefix-dev/pixi/releases/latest/download/pixi-x86_64-unknown-linux-musl.tar.gz
...
The 'pixi' binary is installed into "$HOME/.pixi/bin"
```

2. **Add pixi to PATH**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.pixi/bin:$PATH"

# Reload shell or source
source ~/.bashrc
```

3. **Verify pixi installation**
```bash
pixi --version
```

### Mojo Installation Steps

**Step 1: Clone Modular repository** ✅ DONE
```bash
gh repo clone modular/modular
```

**Step 2: Navigate to Mojo directory**
```bash
cd modular
```

**Step 3: Initialize pixi environment**
```bash
pixi install
```

This will:
- Read `pixi.toml` or `pyproject.toml`
- Create `.pixi` environment
- Install Mojo and dependencies

**Step 4: Activate pixi environment**
```bash
pixi shell
```

**Step 5: Verify Mojo installation**
```bash
mojo --version
```

Expected output:
```
mojo 24.x.x (or latest version)
```

**Step 6: Test Mojo compilation**
```bash
cd ../whitemagic-mojo
mojo build src/main.mojo
```

### Verification

**Test PolyglotRouter:**
```bash
python3 -c "from whitemagic.optimization.polyglot_router import PolyglotRouter; r = PolyglotRouter(); print(f'Mojo: {r._mojo_available}')"
```

Expected output:
```
🔥 Mojo acceleration available - High-performance compute enabled
Mojo: True
```

### Common Issues

**Issue 1: modular command not found**

**Cause**: PATH not updated or Modular CLI not installed

**Solution**:
```bash
# Check if modular CLI exists
which modular

# If not, may need to install from modular repo
cd modular
pixi install
```

**Issue 2: Mojo binaries not found**

**Cause**: PolyglotRouter looks for compiled binaries in specific location

**Solution**: Ensure binaries are in `whitemagic-mojo/bin/`
```bash
cd whitemagic-mojo
mojo build src/coordinate_encoder.mojo -o bin/coordinate_encoder_mojo
```

The PolyglotRouter checks: `whitemagic-mojo/bin/coordinate_encoder_mojo`

**Issue 3: Authentication required**

**Cause**: Modular may require account/authentication

**Solution**: Follow prompts during `pixi install` or `modular auth`

### File Locations

- **Pixi binary**: `~/.pixi/bin/pixi`
- **Modular repo**: `modular/`
- **Mojo source**: `whitemagic-mojo/src/`
- **Compiled binaries**: `whitemagic-mojo/bin/`
- **Pixi environment**: `modular/.pixi/`

### Next Steps for Mojo

1. ✅ Pixi installed
2. ✅ Modular repo cloned
3. ⏳ Navigate to `modular/` directory
4. ⏳ Run `pixi install`
5. ⏳ Activate with `pixi shell`
6. ⏳ Verify `mojo --version`
7. ⏳ Compile WhiteMagic Mojo files
8. ⏳ Test PolyglotRouter detection

---

## 🧪 Complete Verification

### Test All Backends

**Run comprehensive test:**
```bash
python3 -c "
from whitemagic.optimization.polyglot_router import PolyglotRouter
r = PolyglotRouter()
print(f'✅ POLYGLOT STATUS:')
print(f'   Rust: {r._rust_available}')
print(f'   Zig:  {r._zig_available}')
print(f'   Mojo: {r._mojo_available}')
print(f'   Koka: Available at /usr/local/bin/koka')
"
```

Expected output (when all complete):
```
🦀 Rust bridge available - 10-100x speedup enabled
⚡ Zig determinism available - Low-level systems speedup enabled
🔥 Mojo acceleration available - High-performance compute enabled
✅ POLYGLOT STATUS:
   Rust: True
   Zig:  True
   Mojo: True
   Koka: Available at /usr/local/bin/koka
```

### Current Status (Feb 16, 2026)

| Language | Status | Version | Notes |
|----------|--------|---------|-------|
| **Rust** | ✅ Working | 15.0.0 | Python bridge via maturin |
| **Zig** | ✅ Working | 0.15.2 | Shared library compiled |
| **Koka** | ✅ Working | 3.2.2 | Installed to /usr/local/bin |
| **Mojo** | ⏳ In Progress | TBD | Pixi installed, awaiting setup |

---

## 🔧 Troubleshooting

### General Issues

**Issue: "Command not found" errors**

**Solution**: Ensure PATH includes all necessary directories
```bash
export PATH="$HOME/.pixi/bin:/usr/local/bin:$PATH"
```

**Issue: Python can't import compiled modules**

**Solution**: Ensure using venv Python, not system Python
```bash
source .venv/bin/activate
which python3  # Should show .venv/bin/python3
```

**Issue: Compilation succeeds but PolyglotRouter shows False**

**Solution**: Check the specific detection logic in `polyglot_router.py`
- Rust: Tries `import whitemagic_rs`
- Zig: Checks `whitemagic-zig/zig-out/lib/libwhitemagic.so` exists
- Mojo: Checks `whitemagic-mojo/bin/coordinate_encoder_mojo` exists

### Session Persistence

**Problem**: Installations may not persist across sessions (especially in venvs)

**Solution**: Document exact commands and re-run if needed
- Rust: `cd whitemagic-rust && maturin develop --release`
- Zig: `cd whitemagic-zig && zig build`
- Koka: Should persist (installed to /usr/local)
- Mojo: May need `pixi shell` activation each session

---

## 📊 Performance Targets

Once all polyglot languages are operational:

| Operation | Python Baseline | Rust Target | Zig Target | Mojo Target |
|-----------|----------------|-------------|------------|-------------|
| JSON serialize | 1.0× | 3-6× | - | - |
| Vector similarity | 1.0× | 10-50× | - | 100× |
| Holographic encoding | 1.0× | - | 5-10× | 50-100× |
| Pattern matching | 1.0× | 20-100× | - | - |
| I/O operations | 1.0× | - | 10-50× | - |
| Tensor operations | 1.0× | - | - | 100-1000× |

---

## 🎯 Next Steps

1. ✅ Rust — Complete
2. ✅ Zig — Complete
3. ✅ Koka — Complete
4. ⏳ Mojo — Complete installation with pixi
5. ⏳ Verify all backends in PolyglotRouter
6. ⏳ Begin Front Two: Deploy campaigns with real polyglot acceleration

---

**Last Verified**: February 16, 2026, 11:09 AM EST  
**Verified By**: Cascade + Lucas  
**System**: Ubuntu, Python 3.12, venv environment
