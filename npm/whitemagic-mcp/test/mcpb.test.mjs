/**
 * Build and launch the extracted MCPB, not a source-tree import.
 * The executable is a clearly synthetic, locally SHA-256-verified cache fixture;
 * fetch throws if the extracted launcher attempts any network request.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { assetFor } from "../bin/lib.mjs";

const pkg = dirname(dirname(fileURLToPath(import.meta.url)));
const run = (command, args, options = {}) => {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    timeout: 15_000,
    maxBuffer: 1024 * 1024,
    ...options,
  });
  assert.equal(result.error, undefined, `${command}: ${result.error}`);
  assert.equal(result.status, 0, `${command}: ${result.stderr}\n${result.stdout}`);
  return result;
};

test("extracted MCPB starts offline and forwards default/full profile argv", {
  skip: process.platform === "win32" ? "The bundle build helper requires POSIX bash/zip/unzip" : false,
  timeout: 30_000,
}, () => {
  const root = mkdtempSync(join(tmpdir(), "wm mcpb bundle ' "));
  try {
    const out = join(root, "out");
    const extracted = join(root, "extracted");
    const cache = join(root, "cache");
    mkdirSync(out);
    mkdirSync(extracted);
    // A previous generated variant must not survive and leak through an upload glob.
    writeFileSync(join(out, "server-smithery.mcpb"), "unqualified old static metadata");
    const buildEnv = { ...process.env, WM_MCPB_OUTPUT_DIR: out, WM_MCPB_PACKER: "zip" };
    run("bash", [join(pkg, "mcpb/build.sh")], { env: buildEnv });
    assert.equal(existsSync(join(out, "server-smithery.mcpb")), false);
    run("unzip", ["-q", join(out, "server.mcpb"), "-d", extracted]);

    const manifest = JSON.parse(readFileSync(join(extracted, "manifest.json"), "utf8"));
    const version = JSON.parse(readFileSync(join(extracted, "package.json"), "utf8")).version;
    assert.equal(manifest.version, version);
    assert.equal(manifest.tools, undefined, "unqualified static schemas must not be advertised");
    assert.equal(manifest.server.mcp_config.command, "node");
    assert.equal(manifest.user_config.profile.default, "cyberbrain");

    const binary = Buffer.from("#!/bin/sh\nprintf '%s\\n' \"$@\"\n");
    const binaryPath = join(cache, "whitemagic/bin", `v${version}`, assetFor());
    mkdirSync(dirname(binaryPath), { recursive: true });
    writeFileSync(binaryPath, binary, { mode: 0o755 });
    writeFileSync(`${binaryPath}.sha256`, createHash("sha256").update(binary).digest("hex") + "\n");
    const env = { ...process.env, XDG_CACHE_HOME: cache };
    delete env.WHITEMAGIC_RELEASE;
    delete env.NODE_OPTIONS;
    const offlineImport = [
      "import {pathToFileURL} from 'node:url';",
      "globalThis.fetch = () => { throw Error('offline bundle test forbids network'); };",
      "await import(pathToFileURL(process.argv[1]).href);",
    ].join("\n");

    for (const profile of [manifest.user_config.profile.default, "full"]) {
      const args = manifest.server.mcp_config.args.map(arg => arg
        .replaceAll("${__dirname}", extracted)
        .replaceAll("${user_config.profile}", profile));
      const result = run(process.execPath, ["--input-type=module", "-e", offlineImport, ...args], { env });
      assert.deepEqual(result.stdout.trim().split(/\r?\n/), ["serve", "--profile", profile]);
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
