/**
 * Launcher tests (node --test). No network: fetch is injected.
 * Run from npm/whitemagic-mcp:  node --test test/
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  assetFor,
  cacheIsValid,
  cachedBinaryPath,
  childEnvironment,
  ensureBinary,
  releaseTag,
  sanitizeRef,
} from "../bin/lib.mjs";

const TAG = "v9.9.9";
const ASSET = "wm-linux-x86_64-musl";
const BINARY = Buffer.from("#!/bin/sh\necho fake wm 9.9.9\n");
const DIGEST = createHash("sha256").update(BINARY).digest("hex");

function tempCache() {
  return mkdtempSync(join(tmpdir(), "wm-npm-test-"));
}

function okFetch(bodyFor) {
  return async (url) => {
    const body = bodyFor(url);
    if (body === null) return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
    return { ok: true, status: 200, arrayBuffer: async () => body.buffer.slice(body.byteOffset, body.byteOffset + body.byteLength) };
  };
}

const releaseFetch = okFetch((url) => {
  if (url.endsWith(`/${ASSET}.sha256`)) return Buffer.from(`${DIGEST}  wm\n`);
  if (url.endsWith(`/${ASSET}`)) return BINARY;
  return null;
});

test("assetFor maps supported platforms and refuses the rest", () => {
  assert.equal(assetFor("linux", "x64"), "wm-linux-x86_64-musl");
  assert.equal(assetFor("darwin", "arm64"), "wm-macos-aarch64");
  assert.equal(assetFor("darwin", "x64"), "wm-macos-x86_64");
  assert.equal(assetFor("win32", "x64"), "wm-windows-x86_64.exe");
  assert.equal(assetFor("linux", "arm64"), "wm-linux-aarch64-musl");
  assert.equal(assetFor("freebsd", "x64"), null);
});

test("releaseTag honors WHITEMAGIC_RELEASE override", () => {
  assert.equal(releaseTag("9.1.6"), "v9.1.6");
  assert.equal(releaseTag("9.1.6", { WHITEMAGIC_RELEASE: "v9" }), "v9");
});

test("childEnvironment marks the npm install channel without mutating the caller", () => {
  const base = { PATH: "/usr/bin", WM_PROJECT: "demo" };
  const child = childEnvironment(base);
  assert.equal(child.WM_INSTALL_CHANNEL, "npm");
  assert.equal(child.PATH, "/usr/bin");
  assert.equal(child.WM_PROJECT, "demo");
  assert.equal(base.WM_INSTALL_CHANNEL, undefined, "caller env must stay untouched");
  assert.notEqual(child, base, "returns a copy");
  // The npm launcher always tells the truth about its own channel.
  assert.equal(childEnvironment({ WM_INSTALL_CHANNEL: "docker" }).WM_INSTALL_CHANNEL, "npm");
});

test("childEnvironment forwards a sanitized install ref through the channel", () => {
  assert.equal(childEnvironment({ WM_INSTALL_REF: "Glama" }).WM_INSTALL_CHANNEL, "npm:glama");
  assert.equal(
    childEnvironment({ WM_INSTALL_REF: "pulse!!mcp" }).WM_INSTALL_CHANNEL,
    "npm:pulsemcp",
  );
  assert.equal(
    childEnvironment({ WM_INSTALL_REF: "a".repeat(40) }).WM_INSTALL_CHANNEL,
    `npm:${"a".repeat(24)}`,
    "refs are capped like the installer and site middleware",
  );
  assert.equal(
    childEnvironment({ WM_INSTALL_REF: "!!!" }).WM_INSTALL_CHANNEL,
    "npm",
    "an unsalvageable ref degrades to the bare channel",
  );
  assert.equal(sanitizeRef("Smithery_2"), "smithery_2");
  assert.equal(sanitizeRef(undefined), "");
});

test("ensureBinary downloads, verifies, and caches", async () => {
  const cache = tempCache();
  try {
    let calls = 0;
    const fetchImpl = async (url) => {
      calls += 1;
      return releaseFetch(url);
    };
    const bin = await ensureBinary({
      fetchImpl,
      cacheRoot: cache,
      tag: TAG,
      p: "linux",
      a: "x64",
      log: () => {},
    });
    assert.equal(bin, cachedBinaryPath(ASSET, TAG, cache));
    assert.ok(existsSync(bin));
    assert.ok(cacheIsValid(bin), "cache entry verifies after download");

    // Second run trusts the verified cache: no new fetches.
    const before = calls;
    const again = await ensureBinary({
      fetchImpl,
      cacheRoot: cache,
      tag: TAG,
      p: "linux",
      a: "x64",
      log: () => {},
    });
    assert.equal(again, bin);
    assert.equal(calls, before, "cached binary is reused without refetching");
  } finally {
    rmSync(cache, { recursive: true, force: true });
  }
});

test("ensureBinary self-heals a corrupted cache entry", async () => {
  const cache = tempCache();
  try {
    let calls = 0;
    const fetchImpl = async (url) => {
      calls += 1;
      return releaseFetch(url);
    };
    const bin = await ensureBinary({
      fetchImpl,
      cacheRoot: cache,
      tag: TAG,
      p: "linux",
      a: "x64",
      log: () => {},
    });
    // Corruption: alter the cached bytes without touching the sidecar.
    writeFileSync(bin, "tampered");
    assert.equal(cacheIsValid(bin), false, "tampered cache fails verification");

    const messages = [];
    const healed = await ensureBinary({
      fetchImpl,
      cacheRoot: cache,
      tag: TAG,
      p: "linux",
      a: "x64",
      log: (m) => messages.push(m),
    });
    assert.equal(healed, bin);
    assert.deepEqual(readFileSync(bin), BINARY, "binary re-acquired byte-exact");
    assert.ok(
      messages.some((m) => m.includes("failed verification")),
      `re-download disclosed: ${messages.join(" | ")}`,
    );
    assert.equal(calls, 4, "one failed-verification refetch (2 calls: bin + sha)");
  } finally {
    rmSync(cache, { recursive: true, force: true });
  }
});

test("checksum mismatch is a human error, cache left unpoisoned", async () => {
  const cache = tempCache();
  try {
    const fetchImpl = okFetch((url) => {
      if (url.endsWith(`/${ASSET}.sha256`)) return Buffer.from(`${"0".repeat(64)}  wm\n`);
      if (url.endsWith(`/${ASSET}`)) return BINARY;
      return null;
    });
    await assert.rejects(
      ensureBinary({
        fetchImpl,
        cacheRoot: cache,
        tag: TAG,
        p: "linux",
        a: "x64",
        log: () => {},
      }),
      (err) => err.message.includes("checksum mismatch"),
    );
    assert.equal(
      existsSync(cachedBinaryPath(ASSET, TAG, cache)),
      false,
      "a failed download must not leave a cache entry",
    );
  } finally {
    rmSync(cache, { recursive: true, force: true });
  }
});

test("malformed checksum file is refused", async () => {
  const cache = tempCache();
  try {
    const fetchImpl = okFetch((url) => {
      if (url.endsWith(`/${ASSET}.sha256`)) return Buffer.from("not-a-digest  wm\n");
      if (url.endsWith(`/${ASSET}`)) return BINARY;
      return null;
    });
    await assert.rejects(
      ensureBinary({ fetchImpl, cacheRoot: cache, tag: TAG, p: "linux", a: "x64", log: () => {} }),
      (err) => err.message.includes("malformed"),
    );
  } finally {
    rmSync(cache, { recursive: true, force: true });
  }
});

test("network failure is a one-line human error", async () => {
  const cache = tempCache();
  try {
    const refused = async () => {
      const err = new TypeError("fetch failed");
      err.cause = { code: "ECONNREFUSED" };
      throw err;
    };
    await assert.rejects(
      ensureBinary({ fetchImpl: refused, cacheRoot: cache, tag: TAG, p: "linux", a: "x64", log: () => {} }),
      (err) => err.message.includes("network error") && err.message.includes("ECONNREFUSED"),
    );
  } finally {
    rmSync(cache, { recursive: true, force: true });
  }
});

test("unsupported platform lists the source-install path", async () => {
  await assert.rejects(
    ensureBinary({ fetchImpl: releaseFetch, cacheRoot: tempCache(), tag: TAG, p: "freebsd", a: "x64", log: () => {} }),
    (err) => err.message.includes("install from source"),
  );
});
