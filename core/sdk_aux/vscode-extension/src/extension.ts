import * as vscode from 'vscode';
import * as path from 'path';

let wasmModule: any = null;
let engine: any = null;

export function activate(context: vscode.ExtensionContext) {
    console.log('WhiteMagic extension is now active!');

    // Register commands
    const startCommand = vscode.commands.registerCommand('whitemagic.start', async () => {
        await initializeWasm(context);
        vscode.window.showInformationMessage('WhiteMagic WASM initialized!');
    });

    const chatCommand = vscode.commands.registerCommand('whitemagic.chat', () => {
        const panel = vscode.window.createWebviewPanel(
            'whitemagicChat',
            'WhiteMagic Chat',
            vscode.ViewColumn.Two,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );
        panel.webview.html = getChatWebviewContent();
    });

    const searchCommand = vscode.commands.registerCommand('whitemagic.search', async () => {
        const query = await vscode.window.showInputBox({
            prompt: 'Search WhiteMagic memories',
            placeHolder: 'Enter search query...'
        });
        
        if (query) {
            vscode.window.showInformationMessage(`Searching for: ${query}`);
            // TODO: Integrate with actual search API
        }
    });

    const statusCommand = vscode.commands.registerCommand('whitemagic.status', () => {
        const status = wasmModule ? '✅ Active' : '⏳ Not initialized';
        vscode.window.showInformationMessage(`WhiteMagic Status: ${status}`);
    });

    context.subscriptions.push(startCommand, chatCommand, searchCommand, statusCommand);

    // Auto-start if configured
    const config = vscode.workspace.getConfiguration('whitemagic');
    if (config.get('autoStart')) {
        initializeWasm(context);
    }
}

async function initializeWasm(context: vscode.ExtensionContext) {
    try {
        const wasmPath = path.join(context.extensionPath, 'node_modules', '@whitemagic', 'wasm', 'whitemagic_rust.js');
        wasmModule = await import(wasmPath);
        await wasmModule.default();
        engine = new wasmModule.EdgeEngine();
        vscode.window.setStatusBarMessage('$(cloud) WhiteMagic Ready', 5000);
    } catch (error) {
        vscode.window.showErrorMessage(`WhiteMagic initialization failed: ${error}`);
    }
}

function getChatWebviewContent(): string {
    return `<!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            #chat { border: 1px solid #ccc; padding: 10px; min-height: 200px; }
            input { width: 100%; padding: 10px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h2>🧠 WhiteMagic Chat</h2>
        <div id="chat">Welcome to WhiteMagic! Ask me anything...</div>
        <input type="text" id="message" placeholder="Type your message..." />
        <script>
            const vscode = acquireVsCodeApi();
            document.getElementById('message').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    vscode.postMessage({ type: 'chat', text: e.target.value });
                    e.target.value = '';
                }
            });
        </script>
    </body>
    </html>`;
}

export function deactivate() {
    console.log('WhiteMagic extension is now deactivated');
}
