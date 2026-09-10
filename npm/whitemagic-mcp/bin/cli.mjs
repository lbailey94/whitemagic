#!/usr/bin/env node
/**
 * whitemagic-mcp — installs and runs the `wm` binary from the GitHub
 * releases, with checksum verification. `npx whitemagic-mcp serve` is
 * the MCP entrypoint. No dependencies; Node 18+ global fetch.
 *
 * Version contract: package major tracks the release tag (9.0.0 → v9).
 * Override the tag with WHITEMAGIC_RELEASE (e.g. "v9").
 */
import { createHash } from "node:crypto";
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir, platform, arch, tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
const TAG = process.env.WHITEMAGIC_RELEASE ?? `v${pkg.version.split(".")[0]}`;
const REPO = "lbailey94/whitemagic";
const BASE = `https://github.com/${REPO}/releases/download/${TAG}`;

function assetFor() {
  const p = platform(), a = arch();
  if (p === "linux" && a === "x64") return "wm-linux-x86_64-musl";
  if (p === "darwin" && a === "arm64") return "wm-macos-aarch64";
  if (p === "darwin" && a === "x64") return "wm-macos-x86_64";
  if (p === "win32" && a === "x64") return "wm-windows-x86_64.exe";
  return null;
}

async function fetchTo(url, dest) {
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
}

async function ensureBinary() {
  const asset = assetFor();
  if (!asset) {
    console.error(`whitemagic-mcp: no release asset for ${platform()}/${arch()} yet.`);
    console.error(`Install from source instead: https://github.com/${REPO}#install`);
    process.exit(1);
  }
  const cached = join(
    process.env.XDG_CACHE_HOME ?? join(homedir(), ".cache"),
    "whitemagic",
    "bin",
    TAG,
    asset,
  );
  if (existsSync(cached)) return cached;

  console.error(`whitemagic-mcp: fetching ${TAG}/${asset} ...`);
  const binDir = join(
    process.env.XDG_CACHE_HOME ?? join(homedir(), ".cache"),
    "whitemagic",
    "bin",
    TAG,
  );
  mkdirSync(binDir, { recursive: true });
  const tmp = mkdtempSync(join(tmpdir(), "wm-dl-"));
  try {
    await fetchTo(`${BASE}/${asset}`, join(tmp, asset));
    await fetchTo(`${BASE}/${asset}.sha256`, join(tmp, `${asset}.sha256`));
    const expected = readFileSync(join(tmp, `${asset}.sha256`), "utf8").trim().split(/\s+/)[0];
    const actual = createHash("sha256").update(readFileSync(join(tmp, asset))).digest("hex");
    if (expected !== actual) {
      throw new Error(`checksum mismatch for ${asset}\n  expected ${expected}\n  actual   ${actual}`);
    }
    writeFileSync(cached, readFileSync(join(tmp, asset)));
    chmodSync(cached, 0o755);
    return cached;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

const bin = await ensureBinary();
const isWin = platform() === "win32";
const result = spawnSync(bin, process.argv.slice(2), { stdio: "inherit", shell: isWin });
process.exit(result.status ?? 1);
