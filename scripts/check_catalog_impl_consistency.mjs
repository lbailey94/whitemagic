#!/usr/bin/env node
/**
 * Catalog-impl consistency check for whitemagic-site.
 *
 * Verifies that:
 *   1. Every entry in BRIDGE_MODULES has a matching `export function NAME` in lib/bridge/impl.ts
 *   2. Every export function has a matching entry in BRIDGE_MODULES
 *   3. Every export function is registered in the IMPLS dispatcher
 *
 * Exits 1 on any mismatch. Run from the site root:
 *   node scripts/check_catalog_impl_consistency.mjs
 */
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SITE = join(__dirname, "..");

const catalog = readFileSync(join(SITE, "lib/data/mcp-bridge.ts"), "utf8");
const impls = readFileSync(join(SITE, "lib/bridge/impl.ts"), "utf8");

// Extract just the BRIDGE_MODULES array section.
// It starts at "export const BRIDGE_MODULES" and ends at the matching "];".
// The array is well-bracketed: every "{" has a matching "}".
function extractBridgeModules(src) {
  const start = src.indexOf("export const BRIDGE_MODULES");
  if (start < 0) return "";
  const eq = src.indexOf("=", start);
  const openBracket = src.indexOf("[", eq);
  if (openBracket < 0) return "";
  let depth = 0;
  for (let i = openBracket; i < src.length; i++) {
    const c = src[i];
    if (c === "[") depth++;
    else if (c === "]") {
      depth--;
      if (depth === 0) return src.slice(openBracket, i + 1);
    }
  }
  return "";
}

const bridgeModulesSection = extractBridgeModules(catalog);

// Split section into top-level records. A top-level record is a {...}
// at the OUTER depth of the array. Records inside example_payload /
// example_response are nested and we should NOT treat their `name:` as
// a catalog entry.
function extractTopLevelRecords(arraySrc) {
  const records = [];
  let depth = 0;
  let recordStart = -1;
  for (let i = 0; i < arraySrc.length; i++) {
    const c = arraySrc[i];
    if (c === "{") {
      if (depth === 0) recordStart = i;
      depth++;
    } else if (c === "}") {
      depth--;
      if (depth === 0 && recordStart >= 0) {
        records.push(arraySrc.slice(recordStart, i + 1));
        recordStart = -1;
      }
    }
  }
  return records;
}

const records = extractTopLevelRecords(bridgeModulesSection);
const catalogNames = new Set();
for (const record of records) {
  const m = record.match(/^\s*name:\s*"([a-z_][a-z0-9_]*)"/m);
  if (m) catalogNames.add(m[1]);
}

const exportNames = new Set();
for (const m of impls.matchAll(/^export function ([a-z_][a-z0-9_]*)/gm)) {
  exportNames.add(m[1]);
}
exportNames.delete("dispatch");

const dispatcherMatch = impls.match(
  /const IMPLS: Record<string, Impl> = \{([\s\S]*?)\n\};/m
);
const dispatcherNames = new Set();
if (dispatcherMatch) {
  for (const m of dispatcherMatch[1].matchAll(/^\s+([a-z_][a-z0-9_]*),\s*$/gm)) {
    dispatcherNames.add(m[1]);
  }
}

let errors = 0;

const inCatalogNotImpl = [...catalogNames].filter((n) => !exportNames.has(n));
if (inCatalogNotImpl.length) {
  console.error(`[ERR] ${inCatalogNotImpl.length} catalog entries without impl:`);
  inCatalogNotImpl.forEach((n) => console.error(`       ${n}`));
  errors += inCatalogNotImpl.length;
}

const inImplNotCatalog = [...exportNames].filter((n) => !catalogNames.has(n));
if (inImplNotCatalog.length) {
  console.error(`[ERR] ${inImplNotCatalog.length} impl exports not in catalog:`);
  inImplNotCatalog.forEach((n) => console.error(`       ${n}`));
  errors += inImplNotCatalog.length;
}

const inImplNotDispatcher = [...exportNames].filter(
  (n) => !dispatcherNames.has(n)
);
if (inImplNotDispatcher.length) {
  console.error(`[ERR] ${inImplNotDispatcher.length} impl exports not in dispatcher:`);
  inImplNotDispatcher.forEach((n) => console.error(`       ${n}`));
  errors += inImplNotDispatcher.length;
}

if (errors === 0) {
  console.log(
    `[OK] ${catalogNames.size} catalog entries, ${exportNames.size} impls, ${dispatcherNames.size} dispatcher entries — all consistent.`
  );
  process.exit(0);
} else {
  process.exit(1);
}
