#!/usr/bin/env node
/**
 * Test full setup flow with a test config file
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import {
  readConfig,
  backupConfig,
  generateWhiteMagicConfig,
  mergeConfig,
  writeConfig
} from './config.js';

// Create a test config file
const testDir = path.join(os.tmpdir(), 'whitemagic-test');
const testConfigPath = path.join(testDir, 'test-mcp-config.json');

console.log('🧪 Testing Full Setup Flow\n');
console.log(`Test directory: ${testDir}\n`);

// Cleanup and setup
if (fs.existsSync(testDir)) {
  fs.rmSync(testDir, { recursive: true });
}
fs.mkdirSync(testDir, { recursive: true });

// Create a mock existing config
const mockConfig = {
  mcpServers: {
    "other-server": {
      command: "node",
      args: ["other-server.js"]
    }
  }
};

fs.writeFileSync(testConfigPath, JSON.stringify(mockConfig, null, 2));
console.log('✅ Created test config with existing "other-server"');

// Step 1: Read
console.log('\n1. Reading config...');
const existing = readConfig(testConfigPath);
console.log('   Servers:', Object.keys(existing.mcpServers || {}));

// Step 2: Backup
console.log('\n2. Creating backup...');
const backupPath = backupConfig(testConfigPath);
console.log(`   Backup: ${backupPath ? '✅ Created' : '❌ Failed'}`);

// Step 3: Generate WhiteMagic config
console.log('\n3. Generating WhiteMagic config...');
const wmConfig = generateWhiteMagicConfig(
  'test-key-abc123',
  '/test/path',
  'http://localhost:8000'
);
console.log('   ✅ Generated');

// Step 4: Merge
console.log('\n4. Merging configs...');
const merged = mergeConfig(existing, wmConfig);
const servers = Object.keys(merged.mcpServers || {});
console.log(`   Servers after merge: ${servers.join(', ')}`);
console.log(`   ${servers.includes('other-server') ? '✅' : '❌'} Kept existing server`);
console.log(`   ${servers.includes('whitemagic') ? '✅' : '❌'} Added WhiteMagic`);

// Step 5: Write
console.log('\n5. Writing config...');
const writeSuccess = writeConfig(testConfigPath, merged);
console.log(`   ${writeSuccess ? '✅' : '❌'} Write ${writeSuccess ? 'succeeded' : 'failed'}`);

// Step 6: Verify
console.log('\n6. Verifying written config...');
const final = readConfig(testConfigPath);
const finalServers = Object.keys(final.mcpServers || {});
console.log(`   Final servers: ${finalServers.join(', ')}`);
console.log(`   ${finalServers.length === 2 ? '✅' : '❌'} Correct server count`);

// Show final config
console.log('\n📄 Final config:');
console.log(JSON.stringify(final, null, 2));

// Cleanup
console.log('\n🧹 Cleanup...');
fs.rmSync(testDir, { recursive: true });
console.log('✅ Test complete!');
