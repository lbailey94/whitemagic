#!/usr/bin/env node
/**
 * Test config merge logic (non-interactive)
 */

import { readConfig, generateWhiteMagicConfig, mergeConfig } from './config.js';

const testConfigPath = process.env.HOME + '/.windsurf/mcp_server_config.json';

console.log('🧪 Testing Config Merge Logic\n');

// Read existing config
console.log('1. Reading existing config...');
const existing = readConfig(testConfigPath);
console.log('   Current config:', JSON.stringify(existing, null, 2));

// Generate new WhiteMagic config
console.log('\n2. Generating WhiteMagic config...');
const wmConfig = generateWhiteMagicConfig(
  'test-api-key-12345',
  '~/whitemagic',
  undefined
);
console.log('   New config:', JSON.stringify(wmConfig, null, 2));

// Merge
console.log('\n3. Merging configs...');
const merged = mergeConfig(existing, wmConfig);
console.log('   Merged config:', JSON.stringify(merged, null, 2));

console.log('\n✅ Merge test complete (no files written)');
