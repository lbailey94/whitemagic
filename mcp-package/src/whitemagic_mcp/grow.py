"""whitemagic grow — guided upgrade experience.

Detects installed capabilities and hardware, recommends appropriate
upgrades, and installs them with user confirmation.

Usage:
    whitemagic-grow           # Interactive mode
    whitemagic-grow --list    # Show available upgrades only
    whitemagic-grow --all     # Install all recommended upgrades without prompting
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field


@dataclass
class Capability:
    name: str
    installed: bool
    description: str
    install_command: str
    size_hint: str = ""


@dataclass
class HardwareProfile:
    has_gpu: bool = False
    has_avx2: bool = False
    has_avx512: bool = False
    ram_gb: float = 0.0
    disk_gb: float = 0.0
    arch: str = ""
    os_name: str = ""


@dataclass
class UpgradeRecommendation:
    tier: str
    description: str
    command: str
    capabilities: list[str] = field(default_factory=list)
    recommended: bool = True


def detect_capabilities() -> list[Capability]:
    """Check which optional capabilities are currently installed."""
    caps = []

    # fastembed (lightweight embeddings)
    try:
        importlib.import_module("fastembed")
        caps.append(Capability("fastembed", True, "Lightweight semantic search (50MB ONNX)", ""))
    except ImportError:
        caps.append(Capability("fastembed", False, "Lightweight semantic search (50MB ONNX)", "pip install fastembed>=0.2.0"))

    # sentence-transformers (heavy embeddings)
    try:
        importlib.import_module("sentence_transformers")
        caps.append(Capability("sentence-transformers", True, "Full ML embeddings (multilingual, high-quality)", ""))
    except ImportError:
        caps.append(Capability("sentence-transformers", False, "Full ML embeddings (multilingual, high-quality)", "pip install 'whitemagic[embeddings]'"))

    # Rust accelerator
    try:
        importlib.import_module("whitemagic_rust")
        caps.append(Capability("whitemagic-rust", True, "Rust SIMD acceleration (3-10x faster search)", ""))
    except ImportError:
        caps.append(Capability("whitemagic-rust", False, "Rust SIMD acceleration (3-10x faster search)", "pip install whitemagic-rust"))

    # Polyglot bridges
    polyglot_langs = []
    for lang, mod_name in [
        ("Julia", "julia"),
        ("Elixir", "erlport"),
        ("Haskell", "haskell_bridge"),
        ("Koka", "whitemagic_polyglot"),
    ]:
        try:
            importlib.import_module(mod_name)
            polyglot_langs.append(lang)
        except ImportError:
            pass

    if polyglot_langs:
        caps.append(Capability("polyglot", True, f"Polyglot bridges: {', '.join(polyglot_langs)}", ""))
    else:
        caps.append(Capability("polyglot", False, "Polyglot bridges (Julia/Elixir/Haskell/Koka/Zig)", "See docs/POLYGLOT_STATUS.md"))

    # CLI (rich)
    try:
        importlib.import_module("rich")
        caps.append(Capability("rich-cli", True, "Rich CLI formatting", ""))
    except ImportError:
        caps.append(Capability("rich-cli", False, "Rich CLI formatting", "pip install 'whitemagic[cli]'"))

    # API server
    try:
        importlib.import_module("fastapi")
        caps.append(Capability("api-server", True, "REST/HTTP API server", ""))
    except ImportError:
        caps.append(Capability("api-server", False, "REST/HTTP API server", "pip install 'whitemagic[api]'"))

    return caps


def detect_hardware() -> HardwareProfile:
    """Detect hardware capabilities for upgrade recommendations."""
    hw = HardwareProfile()
    hw.arch = platform.machine()
    hw.os_name = platform.system()

    # GPU detection
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
            hw.has_gpu = result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            pass

    # CPU feature detection (Linux only)
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo") as f:
                cpuinfo = f.read()
            hw.has_avx2 = "avx2" in cpuinfo.lower()
            hw.has_avx512 = "avx512" in cpuinfo.lower()
        except Exception:
            pass

    # RAM detection
    try:
        import psutil
        hw.ram_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        try:
            if sys.platform.startswith("linux"):
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            hw.ram_gb = int(line.split()[1]) / (1024**2)
                            break
        except Exception:
            pass

    # Disk space
    try:
        usage = shutil.disk_usage(os.path.expanduser("~"))
        hw.disk_gb = usage.free / (1024**3)
    except Exception:
        pass

    return hw


def recommend_upgrades(caps: list[Capability], hw: HardwareProfile) -> list[UpgradeRecommendation]:
    """Map capabilities + hardware to upgrade recommendations."""
    recs = []
    cap_names = {c.name: c for c in caps}

    # Tier 3: Heavy ML embeddings
    if not cap_names.get("sentence-transformers", Capability("", True, "", "")).installed:
        recommended = hw.has_gpu or (hw.ram_gb >= 16 and hw.disk_gb >= 5)
        recs.append(UpgradeRecommendation(
            tier="Tier 3 (Heavy ML)",
            description="Full ML embeddings — better recall, multilingual support (~2.5GB)",
            command="pip install 'whitemagic[embeddings]'",
            capabilities=["sentence-transformers", "torch", "faiss-cpu", "scipy"],
            recommended=recommended,
        ))

    # Rust accelerator
    if not cap_names.get("whitemagic-rust", Capability("", True, "", "")).installed:
        recommended = hw.has_avx2 or hw.has_avx512
        recs.append(UpgradeRecommendation(
            tier="Rust Accelerator",
            description="Rust SIMD acceleration — 3-10x faster cosine/HNSW/ternary search",
            command="pip install whitemagic-rust",
            capabilities=["whitemagic-rust"],
            recommended=recommended,
        ))

    # Polyglot bridges
    if not cap_names.get("polyglot", Capability("", True, "", "")).installed:
        recs.append(UpgradeRecommendation(
            tier="Tier 4 (Polyglot)",
            description="Polyglot bridges — Julia/Elixir/Haskell/Koka/Zig cognitive accelerators",
            command="See docs/POLYGLOT_STATUS.md for per-language install",
            capabilities=["julia", "elixir", "haskell", "koka", "zig"],
            recommended=False,
        ))

    # CLI
    if not cap_names.get("rich-cli", Capability("", True, "", "")).installed:
        recs.append(UpgradeRecommendation(
            tier="CLI",
            description="Rich CLI formatting — colorful terminal output",
            command="pip install 'whitemagic[cli]'",
            capabilities=["rich"],
            recommended=True,
        ))

    # API server
    if not cap_names.get("api-server", Capability("", True, "", "")).installed:
        recs.append(UpgradeRecommendation(
            tier="API Server",
            description="REST/HTTP API server — expose WhiteMagic over HTTP",
            command="pip install 'whitemagic[api]'",
            capabilities=["fastapi", "uvicorn"],
            recommended=False,
        ))

    return recs


def print_status(caps: list[Capability], hw: HardwareProfile) -> None:
    """Print current capability and hardware status."""
    print("\n  WhiteMagic — Capability Status")
    print("  " + "=" * 50)

    print("\n  Hardware:")
    print(f"    OS:       {hw.os_name} {hw.arch}")
    print(f"    GPU:      {'Yes' if hw.has_gpu else 'No'}")
    print(f"    AVX2:     {'Yes' if hw.has_avx2 else 'No'}")
    print(f"    AVX-512:  {'Yes' if hw.has_avx512 else 'No'}")
    print(f"    RAM:      {hw.ram_gb:.1f} GB" if hw.ram_gb else "    RAM:      unknown")
    print(f"    Disk:     {hw.disk_gb:.1f} GB free" if hw.disk_gb else "    Disk:     unknown")

    print("\n  Capabilities:")
    for cap in caps:
        status = "✅" if cap.installed else "❌"
        print(f"    {status}  {cap.name:25s} {cap.description}")

    print()


def print_recommendations(recs: list[UpgradeRecommendation]) -> None:
    """Print upgrade recommendations."""
    if not recs:
        print("  ✅ All capabilities installed — nothing to upgrade!\n")
        return

    recommended = [r for r in recs if r.recommended]
    optional = [r for r in recs if not r.recommended]

    if recommended:
        print("  Recommended upgrades for your hardware:\n")
        for i, rec in enumerate(recommended, 1):
            print(f"    [{i}] {rec.tier}")
            print(f"        {rec.description}")
            print(f"        Install: {rec.command}")
            print()

    if optional:
        print("  Optional upgrades:\n")
        for rec in optional:
            print(f"    • {rec.tier}")
            print(f"      {rec.description}")
            print(f"      Install: {rec.command}")
            print()


def install_upgrade(command: str) -> bool:
    """Run an install command via pip subprocess."""
    if command.startswith("pip install"):
        try:
            result = subprocess.run(command.split(), check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            print("  ❌ pip not found. Please install pip and try again.")
            return False
    else:
        print(f"  ℹ  Manual install required: {command}")
        return False


def main() -> None:
    """CLI entry point for whitemagic-grow."""
    list_only = "--list" in sys.argv
    install_all = "--all" in sys.argv

    caps = detect_capabilities()
    hw = detect_hardware()
    recs = recommend_upgrades(caps, hw)

    print_status(caps, hw)

    if list_only:
        print_recommendations(recs)
        return

    if not recs:
        print("  ✅ All capabilities installed — nothing to upgrade!\n")
        return

    print_recommendations(recs)

    recommended = [r for r in recs if r.recommended]

    if install_all:
        for rec in recommended:
            print(f"  Installing: {rec.tier}...")
            if install_upgrade(rec.command):
                print(f"  ✅ {rec.tier} installed successfully!\n")
            else:
                print(f"  ❌ {rec.tier} installation failed.\n")
        print("  Done! Re-run `whitemagic-grow` to verify.")
        return

    if not recommended:
        print("  No recommended upgrades for your hardware. Use --all to install optional upgrades.")
        return

    # Interactive mode
    try:
        response = input("  Install all recommended upgrades? [y/N] ").strip().lower()
        if response in ("y", "yes"):
            for rec in recommended:
                print(f"\n  Installing: {rec.tier}...")
                if install_upgrade(rec.command):
                    print(f"  ✅ {rec.tier} installed successfully!")
                else:
                    print(f"  ❌ {rec.tier} installation failed.")
            print("\n  Done! Re-run `whitemagic-grow` to verify.")
        else:
            print("\n  No changes made. Run `whitemagic-grow` anytime to check again.")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    print()


if __name__ == "__main__":
    main()
