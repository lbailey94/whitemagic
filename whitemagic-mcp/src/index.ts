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
    version: '1.0.0',
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

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
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
