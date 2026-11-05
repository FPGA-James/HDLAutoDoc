import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { exportPage } from '../src/export.ts';
import { shellHtml } from '../src/shell.ts';

const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('the exported page is standalone: title, styles and body, no scripts and no remote loads', () => {
  const html = exportPage('a<b>', '<h1>m</h1><svg xmlns="http://www.w3.org/2000/svg"></svg>', 'h1{color:var(--vscode-foreground)}');
  assert.match(html, /<title>a&lt;b&gt;<\/title>/);
  assert.match(html, /<h1>m<\/h1>/);
  assert.match(html, /h1\{color:var\(--vscode-foreground\)\}/);
  assert.doesNotMatch(html, /<script|\s(src|href)="https?:/);
});

test('the exported page defines the theme variables the stylesheet uses, so it reads on its own', () => {
  const html = exportPage('m', '', '');
  for (const v of ['--vscode-foreground', '--vscode-editor-background', '--vscode-panel-border', '--vscode-textCodeBlock-background']) {
    assert.match(html, new RegExp(`${v}:`), v);
  }
});

test('the exported page does not keep the panel\'s click-to-source cursor', () => {
  assert.match(exportPage('m', '', ''), /cursor:\s*auto/);
});

test('the panel shell allows scripts only by nonce and offers the export button', () => {
  const html = shellHtml({ nonce: 'abc', cspSource: 'vscode-resource:', panelCss: 'p.css', webviewJs: 'w.js', vendorBase: 'v' });
  assert.match(html, /script-src 'nonce-abc' 'wasm-unsafe-eval'(;|")/);
  assert.doesNotMatch(html, /script-src[^;"]*'self'/);
  assert.match(html, /<script nonce="abc" src="w\.js">/);
  assert.match(html, /<button[^>]*data-export="html"/);
  assert.match(html, /<button[^>]*data-export="markdown"/);
  assert.match(html, /<button[^>]*data-export="pdf"/);
  assert.match(html, /data-assets="v\/"/);
});

test('the editor title bar offers the panel for HDL files only', () => {
  const entry = pkg.contributes.menus['editor/title'].find((m) => m.command === 'hdlAutodoc.showDocumentation');
  assert.ok(entry, 'no editor/title entry');
  assert.equal(entry.group, 'navigation');
  const [, source, flags] = /^resourceExtname =~ \/(.*)\/(\w*)$/.exec(entry.when);
  const re = new RegExp(source, flags);
  for (const ext of ['.vhd', '.vhdl', '.sv', '.svh', '.v', '.vh', '.VHD']) assert.ok(re.test(ext), ext);
  for (const ext of ['.md', '.vhdx', '.py', '']) assert.ok(!re.test(ext), ext);
  const command = pkg.contributes.commands.find((c) => c.command === 'hdlAutodoc.showDocumentation');
  assert.ok(command.icon, 'the command needs an icon to show in the title bar');
});

test('exporting is also a command in the palette', () => {
  assert.ok(pkg.contributes.commands.some((c) => c.command === 'hdlAutodoc.exportHtml'));
  assert.ok(pkg.contributes.commands.some((c) => c.command === 'hdlAutodoc.exportMarkdown'));
  assert.ok(pkg.contributes.commands.some((c) => c.command === 'hdlAutodoc.exportPdf'));
  assert.equal(pkg.contributes.configuration.properties['hdlAutodoc.browserPath'].default, '');
});
