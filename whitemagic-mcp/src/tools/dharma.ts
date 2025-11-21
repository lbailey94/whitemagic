/**
 * Dharma Garden MCP Tools
 */

import { WhiteMagicClient } from '../client.js';

export const dharmaTools = [
  {
    name: 'dharma_assess',
    description: 'Assess ethical harmony of action',
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string', description: 'Action to assess' },
        context: { type: 'object', default: {} },
      },
      required: ['action'],
    },
  },
  {
    name: 'dharma_check_boundary',
    description: 'Check if action crosses boundaries',
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string' },
        context: { type: 'object', default: {} },
      },
      required: ['action'],
    },
  },
];

export function createDharmaHandlers(client: WhiteMagicClient) {
  return {
    dharma_assess: async (args: any) => JSON.stringify(await client.callCLI('dharma-assess', args), null, 2),
    dharma_check_boundary: async (args: any) => JSON.stringify(await client.callCLI('dharma-check-boundary', args), null, 2),
  };
}
