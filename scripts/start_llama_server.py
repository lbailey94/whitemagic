#!/usr/bin/env python3
"""Start llama-server with WhiteMagic-optimized settings.

Usage:
    python scripts/start_llama_server.py              # GLM4 9B default
    python scripts/start_llama_server.py --model qwen3:8b  # Use a different model
    python scripts/start_llama_server.py --port 8081        # Background model port
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

MODEL_SYMLINKS = {
    "glm4:9b": ("glm4-9b.gguf", "sha256-b506a070d1152798d435ec4e7687336567ae653b3106f73b7b4ac7be1cbc4449"),
    "qwen3:8b": ("qwen3-8b.gguf", "sha256-a3de86cd1c132c822487ededd47a324c50491393e6565cd14bafa40d0b8e686f"),
    "deepseek-r1:7b": ("deepseek-r1-7b.gguf", "sha256-96c415656d377afbff962f6cdb2394ab092ccbcbaab4b82525bc4ca800fe8a49"),
    "qwen2.5vl:7b": ("qwen2.5vl-7b.gguf", "sha256-a99b7f834d754b88f122d865f32758ba9f0994a83f8363df2c1e71c17605a025"),
    "phi4-mini:latest": ("phi4-mini.gguf", "sha256-3c168af1dea0a414299c7d9077e100ac763370e5a98b3c53801a958a47f0a5db"),
    "qwen3:4b": ("qwen3-4b.gguf", "sha256-3e4cb14174460404e7a233e531675303b2fbf7749c02f91864fe311ab6344e4f"),
    "qwen3:1.7b": ("qwen3-1.7b.gguf", "sha256-3d0b790534fe4b79525fc3692950408dca41171676ed7e21db57af5c65ef6ab6"),
    "gemma3:12b": ("gemma3-12b.gguf", "sha256-e8ad13eff07a78d89926e9e8b882317d082ef5bf9768ad7b50fcdbbcd63748de"),
}

SD_BLOB_DIR = Path("/mnt/sdcard/ollama-archive/blobs")
LOCAL_BLOB_DIR = Path.home() / ".ollama" / "models" / "blobs"
MODEL_DIR = Path.home() / "models"


def ensure_symlink(model_key: str) -> Path:
    """Ensure a GGUF symlink exists for the given model."""
    if model_key not in MODEL_SYMLINKS:
        print(f"Unknown model: {model_key}")
        print(f"Available: {', '.join(MODEL_SYMLINKS.keys())}")
        sys.exit(1)

    gguf_name, blob_hash = MODEL_SYMLINKS[model_key]
    model_path = MODEL_DIR / gguf_name

    # Check SD card first, then local
    sd_blob = SD_BLOB_DIR / blob_hash
    local_blob = LOCAL_BLOB_DIR / blob_hash

    if sd_blob.exists():
        target = sd_blob
    elif local_blob.exists():
        target = local_blob
    else:
        print(f"Blob not found: {blob_hash}")
        sys.exit(1)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not model_path.exists():
        model_path.symlink_to(target)
        print(f"Created symlink: {model_path} -> {target}")

    return model_path


def find_binary() -> str:
    """Find llama-server binary."""
    candidates = [
        os.environ.get("WM_LLAMA_SERVER", "llama-server"),
        str(Path.home() / ".local" / "bin" / "llama-server"),
        str(Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"),
        "llama-server",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    # Try PATH
    from shutil import which
    found = which("llama-server")
    if found:
        return found
    print("llama-server binary not found!")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start llama-server for WhiteMagic")
    parser.add_argument("--model", default="glm4:9b", help="Model key (see MODEL_SYMLINKS)")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--ctx", type=int, default=4096, help="Context size")
    parser.add_argument("--threads", type=int, default=6, help="Generation threads")
    parser.add_argument("--threads-batch", type=int, default=6, help="Batch threads")
    parser.add_argument("--gpu-layers", type=int, default=0, help="GPU layers (0 for CPU-only)")
    parser.add_argument("--parallel", type=int, default=2, help="Parallel slots")
    parser.add_argument("--temp", type=float, default=0.7, help="Default temperature")
    parser.add_argument("--embeddings", action="store_true", help="Enable embeddings endpoint")
    parser.add_argument("--no-spec", action="store_true", help="Disable speculative decoding")
    args = parser.parse_args()

    model_path = ensure_symlink(args.model)
    binary = find_binary()

    cmd = [
        binary,
        "-m", str(model_path),
        "--host", args.host,
        "--port", str(args.port),
        "--ctx-size", str(args.ctx),
        "--temp", str(args.temp),
        "--top-p", "0.9",
        "--repeat-penalty", "1.1",
        "--cache-type-k", "q8_0",
        "--cache-type-v", "q8_0",
        "--parallel", str(args.parallel),
        "--threads", str(args.threads),
        "--threads-batch", str(args.threads_batch),
        "--flash-attn", "on",
        "--jinja",
    ]

    if not args.no_spec:
        cmd.extend(["--spec-type", "ngram-mod"])

    if args.gpu_layers > 0:
        cmd.extend(["--n-gpu-layers", str(args.gpu_layers)])

    if args.embeddings:
        cmd.append("--embeddings")

    print(f"Starting llama-server:")
    print(f"  Model: {model_path} ({model_path.stat().st_size / (1024**3):.1f}GB)")
    print(f"  Binary: {binary}")
    print(f"  Port: {args.port}")
    print(f"  Context: {args.ctx}")
    print(f"  Threads: {args.threads} gen / {args.threads_batch} batch")
    print(f"  KV cache: q8_0/q8_0")
    print(f"  Speculative: {'ngram-mod' if not args.no_spec else 'disabled'}")
    print(f"  Parallel slots: {args.parallel}")
    print(f"  Embeddings: {args.embeddings}")
    print()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "LLAMA_LOG_PREFIX": "0"},
    )

    # Register signal handler for clean shutdown
    def shutdown(signum, frame):
        print("\nShutting down llama-server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for server to be ready
    url = f"http://{args.host}:{args.port}"
    print(f"Waiting for server at {url}...")
    for i in range(240):
        time.sleep(0.5)
        try:
            resp = requests.get(f"{url}/health", timeout=1.0)
            if resp.status_code == 200:
                print(f"\nServer ready! (took {(i + 1) * 0.5:.1f}s)")
                print(f"  Health: {resp.json()}")
                print(f"\nServer PID: {proc.pid}")
                print(f"Press Ctrl+C to stop.")
                break
        except Exception:
            if i % 10 == 9:
                print(f"  still waiting... ({(i + 1) * 0.5:.1f}s)")
    else:
        print("Server failed to start within 120s")
        proc.terminate()
        sys.exit(1)

    # Stream server output
    print()
    for line in iter(proc.stdout.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            print(f"[llama-server] {text}")

    proc.wait()


if __name__ == "__main__":
    main()
