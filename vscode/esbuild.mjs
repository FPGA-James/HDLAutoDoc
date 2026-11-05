// Bundles the extension host (Node, CommonJS) and the webview client (browser, IIFE).
import { build } from 'esbuild';

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
