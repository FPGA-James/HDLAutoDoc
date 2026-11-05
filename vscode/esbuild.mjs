// Bundles the extension host (Node, CommonJS) and the webview client (browser, IIFE).
import { build } from 'esbuild';
import { cpSync, mkdirSync } from 'node:fs';

const common = { bundle: true, sourcemap: false, logLevel: 'info', legalComments: 'none' };

await build({
  ...common,
  entryPoints: ['src/extension.ts'],
  outfile: 'dist/extension.js',
  platform: 'node',
  format: 'cjs',
  target: 'node18',
  external: ['vscode'],
});

await build({
  ...common,
  entryPoints: ['webview/main.ts'],
  outfile: 'dist/webview.js',
  platform: 'browser',
  format: 'iife',
  target: 'es2022',
});

// Diagram libraries are loaded by the webview on demand, as their own scripts.
const vendor = 'dist/vendor';
mkdirSync(`${vendor}/wavedrom`, { recursive: true });
cpSync('node_modules/wavedrom/skins/default.js', `${vendor}/wavedrom/default.js`);
cpSync('node_modules/wavedrom/wavedrom.min.js', `${vendor}/wavedrom/wavedrom.min.js`);
cpSync('node_modules/mermaid/dist/mermaid.min.js', `${vendor}/mermaid.min.js`);
cpSync('node_modules/@viz-js/viz/dist/viz-global.js', `${vendor}/viz-global.js`);
cpSync('src/panel.css', 'dist/panel.css');
