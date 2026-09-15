#!/usr/bin/env node
/**
 * whitemagic-mcp — installs and runs the `wm` binary from the GitHub
 * releases, with checksum verification and a self-verifying cache.
 * `npx whitemagic-mcp serve` is the MCP entrypoint. No dependencies;
 * Node 18+ global fetch.
 *
 * Version contract: package version tracks the release tag (9.1.4 -> v9.1.4).
 * Override the tag with WHITEMAGIC_RELEASE (e.g. "v9").
 *
 * All install failures (network, checksum, cache, unsupported platform)
 * terminate with a one-line human message — never a raw Node stack
 * (2026-09-15 audit).
 */
import { readFileSync } from "node:fs";
import { platform } from "node:os";
import { spawnSync } from "node:child_process";
import { ensureBinary } from "./lib.mjs";

const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));

let bin;
try {
  bin = await ensureBinary({ pkgVersion: pkg.version });
} catch (err) {
  console.error(`whitemagic-mcp: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
}

const isWin = platform() === "win32";
const result = spawnSync(bin, process.argv.slice(2), { stdio: "inherit", shell: isWin });
process.exit(result.status ?? 1);
