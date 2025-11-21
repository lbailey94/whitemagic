/**
 * Voice Garden MCP Tools
 */

import { WhiteMagicClient } from '../client.js';

export const voiceTools = [
  {
    name: 'voice_speak',
    description: 'Record narrative entry - tell your story, express thoughts',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'Your narrative content' },
        intention: { type: 'string', description: 'Optional intention' },
        tags: { type: 'array', items: { type: 'string' }, default: [] },
      },
      required: ['content'],
    },
  },
  {
    name: 'voice_begin_story',
    description: 'Start a new story thread',
    inputSchema: {
      type: 'object',
      properties: {
        title: { type: 'string', description: 'Story title' },
        description: { type: 'string' },
        tags: { type: 'array', items: { type: 'string' }, default: [] },
      },
      required: ['title'],
    },
  },
  {
    name: 'voice_status',
    description: 'Get Voice garden status',
    inputSchema: { type: 'object', properties: {} },
  },
];

export function createVoiceHandlers(client: WhiteMagicClient) {
  return {
    voice_speak: async (args: any) => JSON.stringify(await client.callCLI('voice-speak', args), null, 2),
    voice_begin_story: async (args: any) => JSON.stringify(await client.callCLI('voice-begin-story', args), null, 2),
    voice_status: async (args: any) => JSON.stringify(await client.callCLI('voice-status', args), null, 2),
  };
}
