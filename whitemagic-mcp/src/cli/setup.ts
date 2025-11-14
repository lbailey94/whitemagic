#!/usr/bin/env node
/**
 * WhiteMagic MCP Setup CLI
 * One-command setup for MCP-compatible IDEs
 */

import * as readline from 'readline';
import { detectIDEs, findBestIDE, printDetectedIDEs } from './detect.js';
import {
  readConfig,
  backupConfig,
  generateWhiteMagicConfig,
  mergeConfig,
  writeConfig
} from './config.js';
import {
  validateApiKeyFormat,
  validateBasePath,
  testConnection
} from './validate.js';

// Create readline interface for user input
function createInterface() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

// Prompt user for input
function prompt(rl: readline.Interface, question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer.trim());
    });
  });
}

/**
 * Main setup flow
 */
export async function setup() {
  console.log('\n🧙 WhiteMagic MCP Setup\n');
  console.log('This wizard will configure WhiteMagic for your IDE.\n');

  const rl = createInterface();

  try {
    // Step 1: Detect IDEs
    printDetectedIDEs();

    // Step 2: Choose IDE
    const bestIDE = findBestIDE();
    if (!bestIDE) {
      console.error('❌ No MCP-compatible IDE detected.');
      console.error('Please install Cursor, Windsurf, Claude Desktop, or VS Code with Cline.');
      process.exit(1);
    }

    console.log(`📍 Selected IDE: ${bestIDE.name}`);
    console.log(`📂 Config path: ${bestIDE.configPath}\n`);

    // Ask for confirmation if config exists
    if (bestIDE.exists) {
      const overwrite = await prompt(
        rl,
        `⚠️  Config already exists. Merge WhiteMagic into existing config? (y/n): `
      );
      
      if (overwrite.toLowerCase() !== 'y') {
        console.log('Setup cancelled.');
        rl.close();
        return;
      }
    }

    // Step 3: Get API key
    console.log('\n🔑 API Key Configuration\n');
    let apiKey = '';
    let apiKeyValid = false;

    while (!apiKeyValid) {
      apiKey = await prompt(rl, 'Enter your WhiteMagic API key: ');
      
      if (!validateApiKeyFormat(apiKey)) {
        console.log('❌ Invalid API key format. Please try again.\n');
        continue;
      }

      apiKeyValid = true;
    }

    // Step 4: Get base path (optional)
    console.log('\n📁 Storage Configuration\n');
    const defaultBasePath = '~/whitemagic';
    const basePath = await prompt(
      rl,
      `Base path for memories [${defaultBasePath}]: `
    );
    const finalBasePath = basePath || defaultBasePath;

    if (!validateBasePath(finalBasePath)) {
      console.log('❌ Invalid base path format.');
      rl.close();
      return;
    }

    // Step 5: API URL (optional, for self-hosted)
    console.log('\n🌐 API Configuration\n');
    const defaultApiUrl = 'https://api.whitemagic.dev';
    const apiUrl = await prompt(
      rl,
      `API URL [${defaultApiUrl}]: `
    );
    const finalApiUrl = apiUrl || defaultApiUrl;

    // Step 6: Test connection
    console.log('\n🔌 Testing connection...\n');
    const testResult = await testConnection(apiKey, finalApiUrl);

    if (!testResult.success) {
      console.log(`❌ ${testResult.message}`);
      const continueAnyway = await prompt(
        rl,
        '\nContinue setup anyway? (y/n): '
      );
      
      if (continueAnyway.toLowerCase() !== 'y') {
        console.log('Setup cancelled.');
        rl.close();
        return;
      }
    } else {
      console.log(`✅ ${testResult.message}`);
      if (testResult.version) {
        console.log(`📦 API Version: ${testResult.version}`);
      }
    }

    // Step 7: Backup existing config
    console.log('\n💾 Creating backup...\n');
    const backupPath = backupConfig(bestIDE.configPath);

    // Step 8: Read existing config
    const existingConfig = readConfig(bestIDE.configPath);

    // Step 9: Generate and merge WhiteMagic config
    const wmConfig = generateWhiteMagicConfig(
      apiKey,
      finalBasePath,
      finalApiUrl !== defaultApiUrl ? finalApiUrl : undefined
    );

    const mergedConfig = mergeConfig(existingConfig, wmConfig);

    // Step 10: Write config
    console.log('\n📝 Writing configuration...\n');
    const writeSuccess = writeConfig(bestIDE.configPath, mergedConfig);

    if (!writeSuccess) {
      console.error('\n❌ Setup failed!');
      if (backupPath) {
        console.log(`\n🔄 You can restore your backup from: ${backupPath}`);
      }
      rl.close();
      return;
    }

    // Success!
    console.log('\n✅ Setup complete!\n');
    console.log('🎉 WhiteMagic is now configured for your IDE.\n');
    console.log('Next steps:');
    console.log('  1. Restart your IDE');
    console.log('  2. WhiteMagic MCP server will start automatically');
    console.log('  3. Try: "Create a new memory called \'test\'"');
    console.log('\n📚 Documentation: https://github.com/lbailey94/whitemagic#readme\n');

  } catch (error) {
    console.error('\n❌ Setup error:', error);
  } finally {
    rl.close();
  }
}

// Run setup if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  setup().catch(console.error);
}
