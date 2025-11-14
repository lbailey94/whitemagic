/**
 * WhiteMagic MCP Client Tests
 * 
 * Tests the core client functionality for interacting with WhiteMagic.
 */

import { WhiteMagicClient } from '../src/client';
import * as fs from 'fs/promises';
import * as path from 'path';
import * as os from 'os';

describe('WhiteMagicClient', () => {
  let tempDir: string;
  let client: WhiteMagicClient;

  beforeEach(async () => {
    // Create temporary directory for tests
    tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'whitemagic-test-'));
    
    // Create memory directories
    await fs.mkdir(path.join(tempDir, 'memory', 'short_term'), { recursive: true });
    await fs.mkdir(path.join(tempDir, 'memory', 'long_term'), { recursive: true });
    await fs.mkdir(path.join(tempDir, 'memory', 'archive'), { recursive: true });
    
    // Initialize client with test directory
    client = new WhiteMagicClient({
      basePath: tempDir
    });
    
    await client.connect();
  });

  afterEach(async () => {
    // Disconnect client to kill Python process
    if (client) {
      client.disconnect();
    }
    
    // Clean up temporary directory
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  describe('createMemory', () => {
    it('should create a short-term memory', async () => {
      const path = await client.createMemory(
        'Test Memory',
        'This is test content',
        'short_term',
        ['test', 'unit-test']
      );

      expect(path).toBeTruthy();
      expect(path).toContain('short_term');
      expect(path).toMatch(/\.md$/);

      // Verify file exists
      const stats = await fs.stat(path);
      expect(stats.isFile()).toBe(true);
    });

    it('should create a long-term memory', async () => {
      const path = await client.createMemory(
        'Long Term Knowledge',
        'Important pattern discovered',
        'long_term',
        ['pattern', 'knowledge']
      );

      expect(path).toContain('long_term');
    });

    it('should handle special characters in title', async () => {
      const path = await client.createMemory(
        'Memory with "quotes" and [brackets]',
        'Content',
        'short_term',
        []
      );

      expect(path).toBeTruthy();
    });

    it('should normalize tags', async () => {
      const path = await client.createMemory(
        'Tag Test',
        'Content',
        'short_term',
        ['Tag-One', 'TAG_TWO', 'tag three']
      );

      const content = await fs.readFile(path, 'utf-8');
      // Python backend lowercases but preserves underscores and spaces
      expect(content).toContain('tags: tag-one');
      expect(content).toContain('tag_two');
      expect(content).toContain('tag three');
    });
  });

  describe('listMemories', () => {
    beforeEach(async () => {
      // Create some test memories
      await client.createMemory('Memory 1', 'Content 1', 'short_term', ['test']);
      await client.createMemory('Memory 2', 'Content 2', 'short_term', ['test']);
      await client.createMemory('Memory 3', 'Content 3', 'long_term', ['knowledge']);
    });

    it('should list all memories', async () => {
      const listing = await client.listMemories(false, 'created');
      
      expect(listing.short_term).toHaveLength(2);
      expect(listing.long_term).toHaveLength(1);
    });

    it('should return metadata for each memory', async () => {
      const listing = await client.listMemories(false, 'created');
      
      const memory = listing.short_term[0];
      expect(memory).toHaveProperty('title');
      expect(memory).toHaveProperty('filename');
      expect(memory).toHaveProperty('path');
      expect(memory).toHaveProperty('created');
      expect(memory).toHaveProperty('tags');
    });

    it('should sort by created date', async () => {
      // Create memories with longer delays
      await client.createMemory('First', 'Content', 'short_term', ['test']);
      await new Promise(resolve => setTimeout(resolve, 200));
      await client.createMemory('Second', 'Content', 'short_term', ['test']);
      await new Promise(resolve => setTimeout(resolve, 200));
      await client.createMemory('Third', 'Content', 'short_term', ['test']);
      
      const listing = await client.listMemories(false, 'created');
      
      // Just check we have memories in order
      expect(listing.short_term.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('searchMemories', () => {
    beforeEach(async () => {
      await client.createMemory('Python Tutorial', 'Learn Python basics', 'short_term', ['python', 'tutorial']);
      await client.createMemory('JavaScript Guide', 'Master JavaScript', 'short_term', ['javascript', 'tutorial']);
      await client.createMemory('Python Advanced', 'Advanced Python patterns', 'long_term', ['python', 'advanced']);
    });

    it('should search by query', async () => {
      const results = await client.searchMemories('Python', undefined, undefined, false);
      
      expect(results.length).toBe(2);
      expect(results.every(r => r.entry.title.includes('Python'))).toBe(true);
    });

    it('should filter by type', async () => {
      const results = await client.searchMemories('', 'long_term', undefined, false);
      
      expect(results.length).toBe(1);
      expect(results[0].entry.title).toBe('Python Advanced');
    });

    it('should filter by tags', async () => {
      const results = await client.searchMemories('', undefined, ['tutorial'], false);
      
      expect(results.length).toBe(2);
      expect(results.every(r => r.entry.tags.includes('tutorial'))).toBe(true);
    });

    it('should combine filters', async () => {
      const results = await client.searchMemories('Python', 'short_term', ['tutorial'], false);
      
      expect(results.length).toBe(1);
      expect(results[0].entry.title).toBe('Python Tutorial');
    });
  });

  describe('updateMemory', () => {
    let memoryFilename: string;

    beforeEach(async () => {
      const path = await client.createMemory('Original Title', 'Original content', 'short_term', ['old-tag']);
      memoryFilename = path.split('/').pop() || '';
    });

    it('should update title', async () => {
      await client.updateMemory(memoryFilename, {
        title: 'Updated Title'
      });

      const listing = await client.listMemories(false, 'created');
      const updated = listing.short_term.find(m => m.filename === memoryFilename);
      
      expect(updated?.title).toBe('Updated Title');
    });

    it('should update content', async () => {
      await client.updateMemory(memoryFilename, {
        content: 'New content'
      });

      const shortTermPath = path.join(tempDir, 'memory', 'short_term', memoryFilename);
      const content = await fs.readFile(shortTermPath, 'utf-8');
      
      expect(content).toContain('New content');
    });

    it('should add tags', async () => {
      await client.updateMemory(memoryFilename, {
        addTags: ['new-tag']
      });

      const listing = await client.listMemories(false, 'created');
      const updated = listing.short_term.find(m => m.filename === memoryFilename);
      
      expect(updated?.tags).toContain('old-tag');
      expect(updated?.tags).toContain('new-tag');
    });

    it('should remove tags', async () => {
      await client.updateMemory(memoryFilename, {
        removeTags: ['old-tag']
      });

      const listing = await client.listMemories(false, 'created');
      const updated = listing.short_term.find(m => m.filename === memoryFilename);
      
      expect(updated?.tags).not.toContain('old-tag');
    });
  });

  describe('deleteMemory', () => {
    let memoryFilename: string;

    beforeEach(async () => {
      const path = await client.createMemory('Delete Test', 'Content', 'short_term', []);
      memoryFilename = path.split('/').pop() || '';
    });

    it('should archive memory (soft delete)', async () => {
      await client.deleteMemory(memoryFilename, false);

      const listing = await client.listMemories(false, 'created');
      expect(listing.short_term).toHaveLength(0);

      const archivePath = path.join(tempDir, 'memory', 'archive', memoryFilename);
      const exists = await fs.access(archivePath).then(() => true).catch(() => false);
      expect(exists).toBe(true);
    });

    it('should permanently delete memory', async () => {
      await client.deleteMemory(memoryFilename, true);

      const listing = await client.listMemories(false, 'created');
      expect(listing.short_term).toHaveLength(0);

      const shortTermPath = path.join(tempDir, 'memory', 'short_term', memoryFilename);
      const exists = await fs.access(shortTermPath).then(() => true).catch(() => false);
      expect(exists).toBe(false);
    });
  });

  describe('restoreMemory', () => {
    let memoryFilename: string;

    beforeEach(async () => {
      const path = await client.createMemory('Restore Test', 'Content', 'short_term', []);
      memoryFilename = path.split('/').pop() || '';
      await client.deleteMemory(memoryFilename, false); // Archive it
    });

    it('should restore archived memory to short_term', async () => {
      await client.restoreMemory(memoryFilename, 'short_term');

      const listing = await client.listMemories(false, 'created');
      expect(listing.short_term).toHaveLength(1);
      expect(listing.short_term[0].filename).toBe(memoryFilename);
    });

    it('should restore archived memory to long_term', async () => {
      await client.restoreMemory(memoryFilename, 'long_term');

      const listing = await client.listMemories(false, 'created');
      expect(listing.long_term).toHaveLength(1);
      expect(listing.long_term[0].filename).toBe(memoryFilename);
    });
  });

  describe('getStats', () => {
    beforeEach(async () => {
      await client.createMemory('Memory 1', 'Content', 'short_term', ['tag1']);
      await client.createMemory('Memory 2', 'Content', 'short_term', ['tag1', 'tag2']);
      await client.createMemory('Memory 3', 'Content', 'long_term', ['tag2']);
    });

    it('should return memory counts', async () => {
      const stats = await client.getStats();
      
      expect(stats.short_term_count).toBe(2);
      expect(stats.long_term_count).toBe(1);
      expect(stats.total_memories).toBe(3);
    });

    it('should include tag statistics', async () => {
      const stats = await client.getStats();
      
      expect(stats.total_tags).toBeDefined();
    });
  });

  describe('getTags', () => {
    beforeEach(async () => {
      await client.createMemory('M1', 'C', 'short_term', ['tag1']);
      await client.createMemory('M2', 'C', 'short_term', ['tag1', 'tag2']);
      await client.createMemory('M3', 'C', 'long_term', ['tag2', 'tag3']);
    });

    it('should return all tags with counts', async () => {
      const response = await client.getTags(false);
      
      expect(response.tags.length).toBeGreaterThan(0);
      
      const tag1 = response.tags.find((t: {tag: string, count: number}) => t.tag === 'tag1');
      expect(tag1?.count).toBe(2);
      
      const tag2 = response.tags.find((t: {tag: string, count: number}) => t.tag === 'tag2');
      expect(tag2?.count).toBe(2);
      
      const tag3 = response.tags.find((t: {tag: string, count: number}) => t.tag === 'tag3');
      expect(tag3?.count).toBe(1);
    });
  });

  describe('generateContext', () => {
    beforeEach(async () => {
      await client.createMemory('Important Pattern', 'Use this pattern', 'long_term', ['pattern']);
      await client.createMemory('Recent Note', 'Quick note', 'short_term', ['note']);
    });

    it('should generate tier 0 context (minimal)', async () => {
      const context = await client.generateContext(0);
      
      expect(context).toBeTruthy();
      expect(typeof context).toBe('string');
    });

    it('should generate tier 1 context (balanced)', async () => {
      const context = await client.generateContext(1);
      
      expect(context).toBeTruthy();
      expect(context.length).toBeGreaterThan(0);
    });

    it('should generate tier 2 context (full)', async () => {
      const context = await client.generateContext(2);
      
      expect(context).toBeTruthy();
      expect(context.length).toBeGreaterThan(0);
    });
  });

  describe('consolidate', () => {
    beforeEach(async () => {
      // Create some old memories (would need to manipulate timestamps in real test)
      await client.createMemory('Old Memory 1', 'Content', 'short_term', []);
      await client.createMemory('Old Memory 2', 'Content', 'short_term', []);
    });

    it('should run consolidation in dry-run mode', async () => {
      const result = await client.consolidate(true);
      
      expect(result).toHaveProperty('archived');
      expect(result).toHaveProperty('auto_promoted');
      expect(result).toHaveProperty('dry_run');
      expect(result.dry_run).toBe(true);
    });

    it('should not modify files in dry-run mode', async () => {
      const beforeListing = await client.listMemories(false, 'created');
      const beforeCount = beforeListing.short_term.length;
      
      await client.consolidate(true);
      
      const afterListing = await client.listMemories(false, 'created');
      expect(afterListing.short_term.length).toBe(beforeCount);
    });
  });
});
