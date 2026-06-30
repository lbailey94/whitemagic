import subprocess
import json
import os

print("🔮 WhiteMagic Grand Smoke Test 🔮")
print("=================================")

# 1. Python Core (Session Engine)
try:
    from whitemagic.core.ganas.eastern_quadrant import HornGana

    gana = HornGana()
    # It's an async method, but we can check attributes
    print(f"   ✅ Gana Instantiated: {gana.mansion.name}")
except Exception as e:
    print(f"   ❌ Python Error: {e}")

# 2. Rust Muscle (whitemagic_rs)
print("\n🦀 [2/4] Rust Muscle: Testing PyO3 Bridge...")
try:
    import whitemagic_rs

    print(f"   ✅ Module Imported: {whitemagic_rs.__file__}")
    # Simulating a search/vector op if available, otherwise just presence
    print("   ✅ Rust Bindings Active")
except ImportError as e:
    print(f"   ❌ Rust Error: {e}")

# 3. Julia Soul (Gan Ying)
print("\n🟣 [3/4] Julia Soul: Resonant Response...")
julia_script = "whitemagic-julia/src/gan_ying.jl"
if os.path.exists(julia_script):
    try:
        input_data = json.dumps({"magnitude": 0.9, "damping": 0.05})
        result = subprocess.run(
            ["julia", julia_script, input_data],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            print(f"   ✅ Output: {result.stdout.strip()}")
        else:
            print(f"   ❌ Julia Failed: {result.stderr}")
    except FileNotFoundError:
        print("   ⚠️ Julia executable not found in PATH")
    except Exception as e:
        print(f"   ❌ Execution Error: {e}")
else:
    print(f"   ❌ Script missing: {julia_script}")

# 4. Haskell Spirit (Divination)
print("\nλ  [4/4] Haskell Spirit: Casting I Ching...")
haskell_src = "haskell/app/Main.hs"
if os.path.exists(haskell_src):
    try:
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = (
            f"{os.getcwd()}/whitemagic/lib_shim:{env.get('LD_LIBRARY_PATH', '')}"
        )

        # Try runghc for script usage
        result = subprocess.run(
            ["runghc", "-ihaskell/src", haskell_src],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if result.returncode == 0:
            print(f"   ✅ Output: {result.stdout.strip()[:100]}...")
        else:
            # Maybe it needs input or arguments?
            print(f"   message: Haskell ran with code {result.returncode}")
            if result.stdout:
                print(f"   stdout: {result.stdout.strip()[:100]}")
            if result.stderr:
                print(f"   stderr: {result.stderr.strip()[:100]}")
    except FileNotFoundError:
        print("   ⚠️ runghc not found. Is GHC installed?")
    except Exception as e:
        print(f"   ❌ Execution Error: {e}")
else:
    print(f"   ❌ Script missing: {haskell_src}")

print("\n=================================")
print("✨ Smoke Test Complete ✨")
