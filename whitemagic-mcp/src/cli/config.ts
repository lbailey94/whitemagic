/**
 * MCP Configuration Management
 * Handles reading, writing, and merging MCP config files
 */

import * as fs from 'fs';
import * as path from 'path';

export interface WhiteMagicMCPConfig {
  command: string;
  args: string[];
  env?: {
    WHITEMAGIC_API_KEY: string;
    WM_BASE_PATH?: string;
    WM_API_BASE_URL?: string;
  };
}

export interface MCPConfig {
  mcpServers?: {
    whitemagic?: WhiteMagicMCPConfig;
    [key: string]: any;
  };
}

/**
 * Read existing MCP config file
 */
export function readConfig(configPath: string): MCPConfig {
  try {
    if (!fs.existsSync(configPath)) {
      return { mcpServers: {} };
    }

    const content = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.warn(`⚠️  Could not read config: ${error}`);
    return { mcpServers: {} };
  }
}

/**
 * Create backup of existing config
 */
export function backupConfig(configPath: string): string | null {
  try {
    if (!fs.existsSync(configPath)) {
      return null;
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = `${configPath}.backup-${timestamp}`;
    
    fs.copyFileSync(configPath, backupPath);
    console.log(`📦 Backup created: ${backupPath}`);
    
    return backupPath;
  } catch (error) {
    console.error(`❌ Backup failed: ${error}`);
    return null;
  }
}

/**
 * Generate WhiteMagic MCP config entry
 */
export function generateWhiteMagicConfig(
  apiKey: string,
  basePath?: string,
  apiBaseUrl?: string
): WhiteMagicMCPConfig {
  const config: WhiteMagicMCPConfig = {
    command: 'npx',
    args: ['-y', 'whitemagic-mcp'],
    env: {
      WHITEMAGIC_API_KEY: apiKey
    }
  };

  if (basePath) {
    config.env!.WM_BASE_PATH = basePath;
  }

  if (apiBaseUrl) {
    config.env!.WM_API_BASE_URL = apiBaseUrl;
  }

  return config;
}

/**
 * Merge WhiteMagic config into existing MCP config
 */
export function mergeConfig(
  existingConfig: MCPConfig,
  wmConfig: WhiteMagicMCPConfig
): MCPConfig {
  const merged = { ...existingConfig };
  
  if (!merged.mcpServers) {
    merged.mcpServers = {};
  }

  merged.mcpServers.whitemagic = wmConfig;

  return merged;
}

/**
 * Write config to file
 */
export function writeConfig(configPath: string, config: MCPConfig): boolean {
  try {
    // Ensure directory exists
    const dir = path.dirname(configPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // Write config with pretty formatting
    const content = JSON.stringify(config, null, 2);
    fs.writeFileSync(configPath, content, 'utf-8');
    
    console.log(`✅ Config written: ${configPath}`);
    return true;
  } catch (error) {
    console.error(`❌ Failed to write config: ${error}`);
    return false;
  }
}

/**
 * Restore config from backup
 */
export function restoreConfig(backupPath: string, configPath: string): boolean {
  try {
    if (!fs.existsSync(backupPath)) {
      console.error(`❌ Backup not found: ${backupPath}`);
      return false;
    }

    fs.copyFileSync(backupPath, configPath);
    console.log(`✅ Config restored from backup`);
    return true;
  } catch (error) {
    console.error(`❌ Restore failed: ${error}`);
    return false;
  }
}
