/**
 * PDF Reading MCP Tools
 */

import { WhiteMagicClient } from '../client.js';

export const pdfTools = [
  {
    name: 'pdf_read',
    description: 'Read PDF file and extract text',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Path to PDF' },
        max_pages: { type: 'number', default: 1000 },
      },
      required: ['path'],
    },
  },
  {
    name: 'pdf_search',
    description: 'Search within PDF',
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string' },
        query: { type: 'string' },
      },
      required: ['path', 'query'],
    },
  },
];

export function createPDFHandlers(client: WhiteMagicClient) {
  return {
    pdf_read: async (args: any) => JSON.stringify(await client.callCLI('pdf-read', args), null, 2),
    pdf_search: async (args: any) => JSON.stringify(await client.callCLI('pdf-search', args), null, 2),
  };
}
