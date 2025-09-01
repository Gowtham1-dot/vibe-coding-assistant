"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getPlayerPanel = getPlayerPanel;
const vscode = __importStar(require("vscode"));
let panel;
function getPlayerPanel(context) {
    if (panel)
        return panel;
    panel = vscode.window.createWebviewPanel('vibePlayer', 'Vibe Player', vscode.ViewColumn.Beside, { enableScripts: true });
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
