/**
 * WhiteMagic Client - Direct Python Library Integration
 * 
 * This client spawns a Python process and communicates with the WhiteMagic library directly.
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';
import type { Memory, MemorySearchResult, ContextResponse, ConsolidateResult, TagsResponse, StatsResponse, WhiteMagicConfig } from './types.js';

interface PythonCommand {
  id: string;
  method: string;
  params: Record<string, any>;
}

interface PythonResponse {
  id: string;
  success: boolean;
  result?: any;
  error?: string;
}

export class WhiteMagicClient extends EventEmitter {
  private pythonProcess: ChildProcess | null = null;
  private pendingRequests: Map<string, { resolve: (value: any) => void; reject: (reason: any) => void }> = new Map();
  private requestCounter = 0;
  private buffer = '';
  private config: WhiteMagicConfig;

  constructor(config: WhiteMagicConfig) {
    super();
    this.config = config;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Spawn Python process running a simple JSON-RPC wrapper around WhiteMagic
      this.pythonProcess = spawn('python3', [
        '-c',
        this.getPythonWrapperCode(),
        this.config.basePath
      ]);

      this.pythonProcess.stdout?.on('data', (data) => {
        this.buffer += data.toString();
        this.processBuffer();
      });

      this.pythonProcess.stderr?.on('data', (data) => {
        console.error('Python stderr:', data.toString());
      });

      this.pythonProcess.on('error', (err) => {
        reject(new Error(`Failed to start Python process: ${err.message}`));
      });

      this.pythonProcess.on('exit', (code) => {
        // Only log in non-test environments to avoid "Cannot log after tests are done" warnings
        if (process.env.NODE_ENV !== 'test') {
          console.log(`Python process exited with code ${code}`);
        }
        this.emit('disconnected');
      });

      // Send a ping to verify connection
      this.call('ping', {}).then(() => resolve()).catch(reject);
    });
  }

  private processBuffer(): void {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      
      try {
        const response: PythonResponse = JSON.parse(line);
        const pending = this.pendingRequests.get(response.id);
        
        if (pending) {
          this.pendingRequests.delete(response.id);
          if (response.success) {
            pending.resolve(response.result);
          } else {
            pending.reject(new Error(response.error || 'Unknown error'));
          }
        }
      } catch (err) {
        console.error('Failed to parse Python response:', line, err);
      }
    }
  }

  private call(method: string, params: Record<string, any>): Promise<any> {
    return new Promise((resolve, reject) => {
      const id = `req_${++this.requestCounter}`;
      const command: PythonCommand = { id, method, params };
      
      this.pendingRequests.set(id, { resolve, reject });
      
      if (!this.pythonProcess || !this.pythonProcess.stdin) {
        reject(new Error('Python process not connected'));
        return;
      }

      this.pythonProcess.stdin.write(JSON.stringify(command) + '\n');
    });
  }

  // Memory Operations
  async createMemory(title: string, content: string, type: 'short_term' | 'long_term', tags: string[] = []): Promise<string> {
    const result = await this.call('create_memory', { title, content, type, tags });
    return result.path;
  }

  async searchMemories(query?: string, type?: string, tags?: string[], includeArchived: boolean = false): Promise<MemorySearchResult[]> {
    return await this.call('search_memories', { query, type, tags, include_archived: includeArchived });
  }

  async listMemories(includeArchived: boolean = false, sortBy: string = 'created'): Promise<{
    short_term: Memory[];
    long_term: Memory[];
    archived?: Memory[];
  }> {
    return await this.call('list_memories', { include_archived: includeArchived, sort_by: sortBy });
  }

  async deleteMemory(filename: string, permanent: boolean = false): Promise<void> {
    await this.call('delete_memory', { filename, permanent });
  }

  async updateMemory(filename: string, updates: {
    title?: string;
    content?: string;
    tags?: string[];
    addTags?: string[];
    removeTags?: string[];
  }): Promise<void> {
    await this.call('update_memory', {
      filename,
      title: updates.title,
      content: updates.content,
      tags: updates.tags,
      add_tags: updates.addTags,
      remove_tags: updates.removeTags,
    });
  }

  async restoreMemory(filename: string, type: 'short_term' | 'long_term' = 'short_term'): Promise<void> {
    await this.call('restore_memory', { filename, type });
  }

  // Context Operations
  async generateContext(tier: 0 | 1 | 2): Promise<string> {
    const result = await this.call('generate_context', { tier });
    return result.summary;
  }

  // Consolidation
  async consolidate(dryRun: boolean = true): Promise<ConsolidateResult> {
    return await this.call('consolidate', { dry_run: dryRun });
  }

  // Stats & Tags
  async getTags(includeArchived: boolean = false): Promise<TagsResponse> {
    return await this.call('list_tags', { include_archived: includeArchived });
  }

  async getStats(): Promise<StatsResponse> {
    const listing = await this.listMemories(true);
    const tags = await this.getTags(false);
    return {
      short_term_count: listing.short_term.length,
      long_term_count: listing.long_term.length,
      archived_count: listing.archived?.length || 0,
      total_memories: listing.short_term.length + listing.long_term.length + (listing.archived?.length || 0),
      total_tags: tags.total_unique_tags,
    };
  }

  disconnect(): void {
    if (this.pythonProcess) {
      this.pythonProcess.kill();
      this.pythonProcess = null;
    }
  }

  private getPythonWrapperCode(): string {
    return `
import sys
import json
from pathlib import Path

# Get base_dir from command line argument
base_dir = sys.argv[1] if len(sys.argv) > 1 else '.'

# Add base_dir to Python path so we can import whitemagic package
sys.path.insert(0, str(Path(base_dir).resolve()))

from whitemagic import MemoryManager

manager = MemoryManager(base_dir=base_dir)

def handle_request(cmd):
    method = cmd['method']
    params = cmd['params']
    
    try:
        if method == 'ping':
            return {'success': True, 'result': 'pong'}
        
        elif method == 'create_memory':
            path = manager.create_memory(
                title=params['title'],
                content=params['content'],
                memory_type=params['type'],
                tags=params.get('tags', [])
            )
            return {'success': True, 'result': {'path': str(path)}}
        
        elif method == 'search_memories':
            results = manager.search_memories(
                query=params.get('query'),
                memory_type=params.get('type'),
                tags=params.get('tags'),
                include_archived=params.get('include_archived', False)
            )
            return {'success': True, 'result': results}
        
        elif method == 'list_memories':
            listing = manager.list_all_memories(
                include_archived=params.get('include_archived', False),
                sort_by=params.get('sort_by', 'created')
            )
            return {'success': True, 'result': listing}
        
        elif method == 'delete_memory':
            result = manager.delete_memory(
                params['filename'],
                permanent=params.get('permanent', False)
            )
            return {'success': True, 'result': result}
        
        elif method == 'update_memory':
            result = manager.update_memory(
                filename=params['filename'],
                title=params.get('title'),
                content=params.get('content'),
                tags=params.get('tags'),
                add_tags=params.get('add_tags'),
                remove_tags=params.get('remove_tags')
            )
            return {'success': True, 'result': result}
        
        elif method == 'restore_memory':
            result = manager.restore_memory(
                params['filename'],
                memory_type=params.get('type', 'short_term')
            )
            return {'success': True, 'result': result}
        
        elif method == 'generate_context':
            summary = manager.generate_context_summary(params['tier'])
            return {'success': True, 'result': {'summary': summary}}
        
        elif method == 'consolidate':
            result = manager.consolidate_short_term(
                dry_run=params.get('dry_run', True)
            )
            return {'success': True, 'result': result}
        
        elif method == 'list_tags':
            result = manager.list_all_tags(
                include_archived=params.get('include_archived', False)
            )
            return {'success': True, 'result': result}
        
        else:
            return {'success': False, 'error': f'Unknown method: {method}'}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Main loop
for line in sys.stdin:
    try:
        cmd = json.loads(line.strip())
        response = handle_request(cmd)
        response['id'] = cmd['id']
        print(json.dumps(response), flush=True)
    except Exception as e:
        print(json.dumps({'id': '', 'success': False, 'error': str(e)}), flush=True)
`;
  }
}
