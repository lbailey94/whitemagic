/**
 * whitemagic-mcp launcher library — release-asset resolution, atomic
 * download + checksum verification, and self-healing binary cache.
 *
 * Extracted from bin/cli.mjs so the install path is unit-testable
 * (2026-09-15 audit: raw stacks on network/checksum failures; cached
 * binaries were trusted without re-hashing; downloads were written
 * in place instead of atomically).
 */
import { createHash } from "node:crypto";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { homedir, platform, arch, tmpdir } from "node:os";
import { join } from "node:path";

export const REPO = "lbailey94/whitemagic";
const SHA256_RE = /^[0-9a-f]{64}$/i;

export function releaseTag(pkgVersion, env = process.env) {
  return env.WHITEMAGIC_RELEASE ?? `v${pkgVersion}`;
}

/**
 * Sanitize an install ref exactly as `scripts/install.sh` and the site
 * middleware do: lowercase, `[a-z0-9_-]`, capped at 24 chars. Anything that
 * sanitizes to empty means "no ref".
 */
export function sanitizeRef(raw) {
  if (typeof raw !== "string") return "";
  return raw
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "")
    .slice(0, 24);
}

/**
 * Environment for the spawned `wm` child. Marks the install channel so the
 * binary's local install funnel can attribute this launch (recorded
 * on-device only). A `WM_INSTALL_REF` in the caller's environment rides the
 * channel (`npm:<ref>`) so wrapper scripts and directory listings can tag
 * npm installs the same way `install.sh?ref=` does.
 * Returns a copy: the caller's environment is never mutated.
 */
export function childEnvironment(env = process.env) {
  const ref = sanitizeRef(env.WM_INSTALL_REF ?? "");
  return { ...env, WM_INSTALL_CHANNEL: ref ? `npm:${ref}` : "npm" };
}

export function assetFor(p = platform(), a = arch()) {
  if (p === "linux" && a === "x64") return "wm-linux-x86_64-musl";
  if (p === "linux" && a === "arm64") return "wm-linux-aarch64-musl";
  if (p === "darwin" && a === "arm64") return "wm-macos-aarch64";
  if (p === "darwin" && a === "x64") return "wm-macos-x86_64";
  if (p === "win32" && a === "x64") return "wm-windows-x86_64.exe";
  return null;
}

export function defaultCacheRoot(env = process.env) {
  return env.XDG_CACHE_HOME ?? join(homedir(), ".cache");
}

export function cachedBinaryPath(asset, tag, cacheRoot = defaultCacheRoot()) {
  return join(cacheRoot, "whitemagic", "bin", tag, asset);
}

function sidecarFor(cached) {
  return `${cached}.sha256`;
}

export function digestFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

/**
 * A cache entry counts only when the binary re-hashes to the digest the
 * launcher recorded when it verified the download. A truncated or tampered
 * cache thus FAILS verification and is re-acquired instead of being
 * executed blindly.
 */
export function cacheIsValid(cached) {
  const sidecar = sidecarFor(cached);
  if (!existsSync(cached) || !existsSync(sidecar)) return false;
  let expected;
  try {
    expected = readFileSync(sidecar, "utf8").trim();
  } catch {
    return false;
  }
  if (!SHA256_RE.test(expected)) return false;
  try {
    return digestFile(cached) === expected;
  } catch {
    return false;
  }
}

export async function fetchTo(url, dest, fetchImpl) {
  let res;
  try {
    res = await fetchImpl(url, { redirect: "follow" });
  } catch (err) {
    const cause = err?.cause?.code ?? err?.code ?? err?.message ?? "unknown";
    throw new Error(
      `network error fetching ${url} (${cause}) — check your connection, or pin a release with WHITEMAGIC_RELEASE`,
    );
  }
  if (!res.ok) {
    throw new Error(
      `HTTP ${res.status} fetching ${url} — that release asset may be missing; check https://github.com/${REPO}/releases`,
    );
  }
  writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
}

/**
 * Ensure a verified `wm` binary for this platform exists in the cache and
 * return its path. Fresh downloads go temp -> checksum -> chmod -> rename;
 * a cache entry that fails re-verification is replaced (self-healing).
 */
export async function ensureBinary({
  fetchImpl = fetch,
  cacheRoot = defaultCacheRoot(),
  tag,
  pkgVersion,
  p = platform(),
  a = arch(),
  log = console.error,
} = {}) {
  const resolvedTag = tag ?? releaseTag(pkgVersion);
  const asset = assetFor(p, a);
  if (!asset) {
    throw new Error(
      `no release asset for ${p}/${a} yet — install from source: https://github.com/${REPO}#install`,
    );
  }
  const cached = cachedBinaryPath(asset, resolvedTag, cacheRoot);
  if (cacheIsValid(cached)) return cached;
  if (existsSync(cached)) {
    log("whitemagic-mcp: cached binary failed verification — re-downloading.");
  }

  log(`whitemagic-mcp: fetching ${resolvedTag}/${asset} ...`);
  const binDir = join(cacheRoot, "whitemagic", "bin", resolvedTag);
  mkdirSync(binDir, { recursive: true });
  // Stage INSIDE the cache dir so the final rename is atomic (a /tmp staging
  // dir can live on another filesystem, where rename fails with EXDEV).
  const tmp = mkdtempSync(join(binDir, ".download-"));
  try {
    const tmpBin = join(tmp, asset);
    const tmpSha = join(tmp, `${asset}.sha256`);
    await fetchTo(`${BASE_URL(resolvedTag)}/${asset}`, tmpBin, fetchImpl);
    await fetchTo(`${BASE_URL(resolvedTag)}/${asset}.sha256`, tmpSha, fetchImpl);
    const expected = (readFileSync(tmpSha, "utf8").trim().split(/\s+/)[0] ?? "").toLowerCase();
    if (!SHA256_RE.test(expected)) {
      throw new Error(`release checksum for ${asset} is malformed — refusing to install it`);
    }
    const actual = digestFile(tmpBin);
    if (actual !== expected) {
      throw new Error(
        `checksum mismatch for ${asset} (expected ${expected.slice(0, 12)}…, got ${actual.slice(0, 12)}…) — the download may be corrupted; retry`,
      );
    }
    chmodSync(tmpBin, 0o755);
    renameSync(tmpBin, cached);
    writeFileSync(sidecarFor(cached), `${expected}\n`);
    return cached;
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

export function BASE_URL(tag) {
  return `https://github.com/${REPO}/releases/download/${tag}`;
}
