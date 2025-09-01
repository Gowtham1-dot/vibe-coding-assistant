import * as vscode from 'vscode';

let panel: vscode.WebviewPanel | undefined;

export function getPlayerPanel(context: vscode.ExtensionContext): vscode.WebviewPanel {
  if (panel) return panel;

  panel = vscode.window.createWebviewPanel(
    'vibePlayer',
    'Vibe Player',
    vscode.ViewColumn.Beside,
    { enableScripts: true }
  );

  panel.webview.html = getHtml();
  panel.onDidDispose(() => { panel = undefined; });

  return panel;
}

function getHtml() {
  return `<!doctype html>
<html><head><meta charset="utf-8" />
<style>body{font-family:system-ui;padding:8px} audio{width:100%}</style>
</head>
<body>
  <h3>Vibe Player</h3>
  <audio id="aud" controls autoplay></audio>
  <script>
    window.addEventListener('message', ev => {
      const msg = ev.data;
      if (msg.type === 'PLAY') {
        const src = \`data:\${msg.mime};base64,\${msg.audioB64}\`;
        const a = document.getElementById('aud');
        a.src = src; a.play();
      }
    });
  </script>
</body></html>`;
}
