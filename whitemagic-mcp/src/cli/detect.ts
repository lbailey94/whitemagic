/**
 * IDE Detection for MCP Configuration
 * Detects Cursor, Windsurf, Claude Desktop, VS Code, and generic MCP clients
 */

import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

export interface IDEConfig {
  name: string;
  configPath: string;
  exists: boolean;
}

/**
 * Detect all MCP-compatible IDEs on the system
 */
export function detectIDEs(): IDEConfig[] {
  const homeDir = os.homedir();
  const ides: IDEConfig[] = [];

  // Cursor (.cursor/mcp.json)
  const cursorPath = path.join(homeDir, '.cursor', 'mcp.json');
  ides.push({
    name: 'Cursor',
    configPath: cursorPath,
    exists: fs.existsSync(cursorPath)
  });

  // Windsurf (.windsurf/mcp_server_config.json)
  const windsurfPath = path.join(homeDir, '.windsurf', 'mcp_server_config.json');
  ides.push({
    name: 'Windsurf',
    configPath: windsurfPath,
    exists: fs.existsSync(windsurfPath)
  });

  // Claude Desktop (platform-specific)
  let claudePath: string;
  if (process.platform === 'darwin') {
    claudePath = path.join(homeDir, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
  } else if (process.platform === 'win32') {
    claudePath = path.join(homeDir, 'AppData', 'Roaming', 'Claude', 'claude_desktop_config.json');
  } else {
    claudePath = path.join(homeDir, '.config', 'Claude', 'claude_desktop_config.json');
  }
  ides.push({
    name: 'Claude Desktop',
    configPath: claudePath,
    exists: fs.existsSync(claudePath)
  });

  // VS Code with Cline extension
  const vscodeConfigDir = path.join(homeDir, '.vscode', 'mcp');
  const vscodePath = path.join(vscodeConfigDir, 'settings.json');
  ides.push({
    name: 'VS Code (Cline)',
    configPath: vscodePath,
    exists: fs.existsSync(vscodePath)
  });

  return ides;
}

/**
 * Find the best IDE to configure (prioritize existing configs)
 */
export function findBestIDE(): IDEConfig | null {
  const ides = detectIDEs();

  // First, look for existing configs
  const existing = ides.find(ide => ide.exists);
  if (existing) {
    return existing;
  }

  // If no existing config, return first detected IDE location
  // (even if config doesn't exist yet)
  return ides.length > 0 ? ides[0] : null;
}

/**
 * Print detected IDEs to console
 */
export function printDetectedIDEs(): void {
  const ides = detectIDEs();

  console.log('\n🔍 Detected MCP-Compatible IDEs:\n');

  ides.forEach(ide => {
    const status = ide.exists ? '✅ Config found' : '⚪ No config yet';
    console.log(`  ${status} - ${ide.name}`);
    console.log(`    Path: ${ide.configPath}`);
  });

  console.log();
}
