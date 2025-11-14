#!/usr/bin/env node
/**
 * Test API connection validation
 */

import { testConnection, validateApiKeyFormat } from './validate.js';

console.log('🧪 Testing API Connection Validation\n');

// Test 1: API key format validation
console.log('1. Testing API key format validation...');
const validKeys = ['wm_1234567890', 'test-key-abc123', 'valid_key_here'];
const invalidKeys = ['', 'short', '   ', 'key with spaces'];

validKeys.forEach(key => {
  const valid = validateApiKeyFormat(key);
  console.log(`   ${valid ? '✅' : '❌'} "${key}": ${valid ? 'valid' : 'invalid'}`);
});

invalidKeys.forEach(key => {
  const valid = validateApiKeyFormat(key);
  console.log(`   ${valid ? '✅' : '❌'} "${key}": ${valid ? 'valid' : 'invalid'}`);
});

// Test 2: Connection test (health endpoint)
console.log('\n2. Testing connection to API...');
console.log('   Checking: http://localhost:8000');

testConnection('test-key', 'http://localhost:8000')
  .then(result => {
    console.log(`   ${result.success ? '✅' : '❌'} ${result.message}`);
    if (result.version) {
      console.log(`   📦 Version: ${result.version}`);
    }
  })
  .catch(error => {
    console.log(`   ❌ Error: ${error.message}`);
  });

// Test 3: Connection test with production URL (should work)
console.log('\n3. Testing connection to production API...');
console.log('   Checking: https://api.whitemagic.dev');

setTimeout(() => {
  testConnection('invalid-key', 'https://api.whitemagic.dev')
    .then(result => {
      console.log(`   ${result.success ? '✅' : '❌'} ${result.message}`);
      if (result.version) {
        console.log(`   📦 Version: ${result.version}`);
      }
      console.log('\n✅ Connection tests complete!');
    })
    .catch(error => {
      console.log(`   ❌ Error: ${error.message}`);
      console.log('\n✅ Connection tests complete!');
    });
}, 1000);
