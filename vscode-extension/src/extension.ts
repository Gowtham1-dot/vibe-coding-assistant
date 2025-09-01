import * as vscode from 'vscode';
import { speakText } from './api';
import { getPlayerPanel } from './player'; // <- named import

export function activate(context: vscode.ExtensionContext) {
  const disposable = vscode.commands.registerCommand('vibe.speakSelection', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) { return; }

    const selection = editor.selection.isEmpty
      ? editor.document.getText(new vscode.Range(0, 0, editor.document.lineCount, 0))
      : editor.document.getText(editor.selection);

    try {
      const { audioB64, mime } = await speakText(selection); // ✅ camelCase
      const panel = getPlayerPanel(context);
      panel.webview.postMessage({ type: 'PLAY', audioB64, mime }); // ✅ camelCase
    } catch (err: any) {
      vscode.window.showErrorMessage(`Vibe speak failed: ${err.message || err}`);
    }
  });

  context.subscriptions.push(disposable);
}

export function deactivate() {}
