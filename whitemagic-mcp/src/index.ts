#!/usr/bin/env node
/**
 * WhiteMagic MCP Server
 * 
 * Model Context Protocol server for WhiteMagic memory system.
 * Provides resources and tools for AI agents to interact with tiered memory.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { WhiteMagicClient } from './client.js';
import { fastRead, batchRead, clearCache, getCacheStats } from './optimizations.js';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

// Read version from package.json
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageJson = JSON.parse(
  readFileSync(join(__dirname, '../package.json'), 'utf-8')
);

// Configuration from environment
const config = {
  apiUrl: process.env.WM_API_URL || 'http://localhost:8000',
  apiKey: process.env.WM_API_KEY,
  basePath: process.env.WM_BASE_PATH || process.cwd(),
};

const client = new WhiteMagicClient(config);

// Create MCP server
const server = new Server(
  {
    name: 'whitemagic-memory',
    version: packageJson.version,
  },
  {
    capabilities: {
      resources: {},
      tools: {},
    },
  }
);

// List available resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: 'memory://short_term',
        name: 'Short-Term Memories',
        description: 'Recent memories (session-level, temporary insights)',
        mimeType: 'application/json',
      },
      {
        uri: 'memory://long_term',
        name: 'Long-Term Knowledge',
        description: 'Persistent knowledge (proven patterns, heuristics)',
        mimeType: 'application/json',
      },
      {
        uri: 'memory://stats',
        name: 'Memory Statistics',
        description: 'System statistics and metrics',
        mimeType: 'application/json',
      },
      {
        uri: 'memory://tags',
        name: 'Tag Directory',
        description: 'All tags with usage statistics',
        mimeType: 'application/json',
      },
    ],
  };
});

// Read resource contents
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;

  try {
    if (uri === 'memory://short_term') {
      const listing = await client.listMemories(false, 'created');
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(listing.short_term, null, 2),
          },
        ],
      };
    }

    if (uri === 'memory://long_term') {
      const listing = await client.listMemories(false, 'created');
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(listing.long_term, null, 2),
          },
        ],
      };
    }

    if (uri === 'memory://stats') {
      const stats = await client.getStats();
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(stats, null, 2),
          },
        ],
      };
    }

    if (uri === 'memory://tags') {
      const tags = await client.getTags(false);
      return {
        contents: [
          {
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(tags, null, 2),
          },
        ],
      };
    }

    throw new Error(`Unknown resource: ${uri}`);
  } catch (error) {
    throw new Error(`Failed to read resource ${uri}: ${error}`);
  }
});

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'create_memory',
        description: 'Create a new memory entry (short-term or long-term)',
        inputSchema: {
          type: 'object',
          properties: {
            title: {
              type: 'string',
              description: 'Memory title',
            },
            content: {
              type: 'string',
              description: 'Memory content (markdown supported)',
            },
            type: {
              type: 'string',
              enum: ['short_term', 'long_term'],
              description: 'Memory type',
              default: 'short_term',
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Tags for categorization',
              default: [],
            },
          },
          required: ['title', 'content'],
        },
      },
      {
        name: 'search_memories',
        description: 'Search memories by query, type, and tags',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query (searches title, content, and tags)',
            },
            type: {
              type: 'string',
              enum: ['short_term', 'long_term'],
              description: 'Filter by memory type',
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Filter by tags (AND logic)',
            },
            include_archived: {
              type: 'boolean',
              description: 'Include archived memories',
              default: false,
            },
          },
        },
      },
      {
        name: 'read_memory',
        description: 'Read full content of a specific memory',
        inputSchema: {
          type: 'object',
          properties: {
            filename: {
              type: 'string',
              description: 'Memory filename (e.g., "20251115_setup_wizard.md")',
            },
            include_metadata: {
              type: 'boolean',
              description: 'Include metadata (tags, dates, etc)',
              default: true,
            },
          },
          required: ['filename'],
        },
      },
      {
        name: 'list_memories',
        description: 'List all memories with metadata (useful for browsing)',
        inputSchema: {
          type: 'object',
          properties: {
            type: {
              type: 'string',
              enum: ['short_term', 'long_term'],
              description: 'Filter by memory type',
            },
            include_archived: {
              type: 'boolean',
              description: 'Include archived memories',
              default: false,
            },
            sort_by: {
              type: 'string',
              enum: ['created', 'modified', 'title'],
              description: 'Sort order',
              default: 'created',
            },
          },
        },
      },
      {
        name: 'get_context',
        description: 'Generate tier-appropriate context for AI prompts',
        inputSchema: {
          type: 'object',
          properties: {
            tier: {
              type: 'number',
              enum: [0, 1, 2],
              description: 'Context tier: 0 (minimal), 1 (balanced), 2 (full)',
            },
          },
          required: ['tier'],
        },
      },
      {
        name: 'consolidate',
        description: 'Consolidate and archive old short-term memories',
        inputSchema: {
          type: 'object',
          properties: {
            dry_run: {
              type: 'boolean',
              description: 'If true, show what would be done without executing',
              default: true,
            },
          },
        },
      },
      {
        name: 'update_memory',
        description: 'Update an existing memory\'s content, title, or tags',
        inputSchema: {
          type: 'object',
          properties: {
            filename: {
              type: 'string',
              description: 'Memory filename to update',
            },
            title: {
              type: 'string',
              description: 'New title (optional)',
            },
            content: {
              type: 'string',
              description: 'New content (optional)',
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Replace all tags (optional)',
            },
            add_tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Add these tags (optional)',
            },
            remove_tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Remove these tags (optional)',
            },
          },
          required: ['filename'],
        },
      },
      {
        name: 'delete_memory',
        description: 'Delete or archive a memory',
        inputSchema: {
          type: 'object',
          properties: {
            filename: {
              type: 'string',
              description: 'Memory filename to delete',
            },
            permanent: {
              type: 'boolean',
              description: 'If true, permanently delete; otherwise archive',
              default: false,
            },
          },
          required: ['filename'],
        },
      },
      {
        name: 'restore_memory',
        description: 'Restore an archived memory',
        inputSchema: {
          type: 'object',
          properties: {
            filename: {
              type: 'string',
              description: 'Archived memory filename to restore',
            },
            type: {
              type: 'string',
              enum: ['short_term', 'long_term'],
              description: 'Target memory type',
              default: 'short_term',
            },
          },
          required: ['filename'],
        },
      },
      {
        name: 'fast_read_memory',
        description: '⚡ FAST: Read memory content with optimizations (10-100x faster)',
        inputSchema: {
          type: 'object',
          properties: {
            filename: {
              type: 'string',
              description: 'Memory filename (e.g., "20251115_setup_wizard.md")',
            },
            fast_mode: {
              type: 'boolean',
              description: 'Skip metadata parsing for maximum speed',
              default: true,
            },
            cache: {
              type: 'boolean',
              description: 'Use cache if available',
              default: true,
            },
          },
          required: ['filename'],
        },
      },
      {
        name: 'batch_read_memories',
        description: '⚡ BATCH: Read multiple memories in one operation',
        inputSchema: {
          type: 'object',
          properties: {
            filenames: {
              type: 'array',
              items: { type: 'string' },
              description: 'Array of memory filenames to read',
            },
            fast_mode: {
              type: 'boolean',
              description: 'Skip metadata parsing',
              default: true,
            },
            cache: {
              type: 'boolean',
              description: 'Use cache',
              default: true,
            },
          },
          required: ['filenames'],
        },
      },
      {
        name: 'clear_memory_cache',
        description: 'Clear the memory read cache (useful for testing or memory pressure)',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (!args) {
    return {
      content: [
        {
          type: 'text',
          text: 'Error: Missing arguments',
        },
      ],
      isError: true,
    };
  }

  try {
    switch (name) {
      case 'create_memory': {
        const path = await client.createMemory(
          args.title as string,
          args.content as string,
          (args.type as 'short_term' | 'long_term') || 'short_term',
          (args.tags as string[]) || []
        );
        return {
          content: [
            {
              type: 'text',
              text: `Memory created successfully at: ${path}`,
            },
          ],
        };
      }

      case 'search_memories': {
        const results = await client.searchMemories(
          args.query as string,
          args.type as string,
          args.tags as string[],
          args.include_archived as boolean
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(results, null, 2),
            },
          ],
        };
      }

      case 'read_memory': {
        const memory = await client.readMemory(
          args.filename as string,
          args.include_metadata !== false
        );
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(memory, null, 2),
            },
          ],
        };
      }

      case 'list_memories': {
        const listing = await client.listMemories(
          args.include_archived as boolean,
          args.sort_by as string || 'created'
        );
        // Filter by type if specified
        if (args.type) {
          const filtered = args.type === 'short_term' 
            ? { short_term: listing.short_term }
            : { long_term: listing.long_term };
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(filtered, null, 2),
              },
            ],
          };
        }
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(listing, null, 2),
            },
          ],
        };
      }

      case 'get_context': {
        const context = await client.generateContext(args.tier as 0 | 1 | 2);
        return {
          content: [
            {
              type: 'text',
              text: context,
            },
          ],
        };
      }

      case 'consolidate': {
        const result = await client.consolidate(args.dry_run !== false);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'update_memory': {
        await client.updateMemory(args.filename as string, {
          title: args.title as string,
          content: args.content as string,
          tags: args.tags as string[],
          addTags: args.add_tags as string[],
          removeTags: args.remove_tags as string[],
        });
        return {
          content: [
            {
              type: 'text',
              text: `Memory ${args.filename} updated successfully`,
            },
          ],
        };
      }

      case 'delete_memory': {
        await client.deleteMemory(
          args.filename as string,
          args.permanent as boolean
        );
        return {
          content: [
            {
              type: 'text',
              text: `Memory ${args.filename} ${args.permanent ? 'permanently deleted' : 'archived'}`,
            },
          ],
        };
      }

      case 'restore_memory': {
        await client.restoreMemory(
          args.filename as string,
          (args.type as 'short_term' | 'long_term') || 'short_term'
        );
        return {
          content: [
            {
              type: 'text',
              text: `Memory ${args.filename} restored successfully`,
            },
          ],
        };
      }

      case 'fast_read_memory': {
        const memoryPath = join(config.basePath, 'memory');
        const filename = args.filename as string;
        const type = filename.includes('long_term') ? 'long_term' : 'short_term';
        const filepath = join(memoryPath, type, filename);
        
        const content = fastRead(filepath, {
          fast_mode: args.fast_mode !== false,
          cache: args.cache !== false,
        });
        
        return {
          content: [
            {
              type: 'text',
              text: content,
            },
          ],
        };
      }

      case 'batch_read_memories': {
        const memoryPath = join(config.basePath, 'memory');
        const filenames = args.filenames as string[];
        
        // Resolve full paths
        const fullPaths = filenames.map(filename => {
          const type = filename.includes('long_term') ? 'long_term' : 'short_term';
          return join(type, filename);
        });
        
        const result = batchRead(memoryPath, {
          filenames: fullPaths,
          options: {
            fast_mode: args.fast_mode !== false,
            cache: args.cache !== false,
          },
        });
        
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'clear_memory_cache': {
        clearCache();
        const stats = getCacheStats();
        
        return {
          content: [
            {
              type: 'text',
              text: `Cache cleared. Stats: ${JSON.stringify(stats)}`,
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${errorMessage}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  console.error('Starting WhiteMagic MCP Server...');
  console.error(`Base path: ${config.basePath}`);
  
  try {
    // Connect to WhiteMagic
    await client.connect();
    console.error('Connected to WhiteMagic');

    // Start MCP server with stdio transport
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('MCP Server ready');
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

main();
