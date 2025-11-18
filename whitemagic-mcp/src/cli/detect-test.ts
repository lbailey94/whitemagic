#!/usr/bin/env node
/**
 * Test IDE detection
 */

import { printDetectedIDEs, findBestIDE } from './detect.js';

console.log('\n🧙 WhiteMagic MCP - IDE Detection Test\n');

printDetectedIDEs();

const best = findBestIDE();
if (best) {
  console.log(`\n✅ Best IDE for setup: ${best.name}`);
  console.log(`   Config: ${best.configPath}`);
  console.log(`   Exists: ${best.exists ? 'Yes' : 'No'}`);
} else {
  console.log('\n❌ No MCP-compatible IDE detected');
}

console.log();
