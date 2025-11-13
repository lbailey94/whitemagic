// Quick SDK test (requires running WhiteMagic API)
import { WhiteMagicClient } from './dist/index.js';

async function test() {
  console.log('Testing WhiteMagic TypeScript SDK...\n');

  const client = new WhiteMagicClient({
    apiKey: process.env.WHITEMAGIC_API_KEY || 'test-key',
    baseUrl: process.env.WHITEMAGIC_BASE_URL || 'http://localhost:8000'
  });

  try {
    // Test health check (no auth required)
    console.log('1. Testing health check...');
    const health = await client.health();
    console.log('✅ Health:', health);
  } catch (error) {
    console.log('⚠️  Health check failed (API not running?):', error.message);
  }

  // If API key is set, test memory operations
  if (process.env.WHITEMAGIC_API_KEY) {
    try {
      console.log('\n2. Testing create memory...');
      const memory = await client.memories.create({
        title: 'SDK Test',
        content: 'Testing TypeScript SDK',
        type: 'short_term',
        tags: ['test']
      });
      console.log('✅ Created:', memory.id);

      console.log('\n3. Testing list memories...');
      const memories = await client.memories.list({ limit: 5 });
      console.log(`✅ Listed: ${memories.length} memories`);

      console.log('\n4. Testing get memory...');
      const fetched = await client.memories.get(memory.id);
      console.log('✅ Fetched:', fetched.title);

      console.log('\n5. Testing update memory...');
      const updated = await client.memories.update(memory.id, {
        content: 'Updated content'
      });
      console.log('✅ Updated:', updated.id);

      console.log('\n6. Testing delete memory...');
      await client.memories.delete(memory.id);
      console.log('✅ Deleted');

      console.log('\n✅ All tests passed!');
    } catch (error) {
      console.error('❌ Test failed:', error);
    }
  } else {
    console.log('\n⚠️  Set WHITEMAGIC_API_KEY to test authenticated operations');
  }
}

test().catch(console.error);
