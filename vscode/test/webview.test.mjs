// Renders real documents in headless Chrome, with the content-security policy the extension
// uses, and checks that waveforms, Mermaid diagrams and state machines are drawn.  Skipped
// when no Chrome is found (set CHROME to its path).  Screenshots go to test/out/.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync, cpSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderDocument } from '../src/render.ts';
import { shellHtml } from '../src/shell.ts';

const root = fileURLToPath(new URL('..', import.meta.url));
const chrome = [process.env.CHROME,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].find((p) => p && existsSync(p));

const fixture = (name) => JSON.parse(readFileSync(join(root, `test/fixtures/${name}.json`), 'utf8'));
const THEMES = {
  light: { cls: 'vscode-light', vars: '--vscode-foreground:#222;--vscode-editor-background:#fff;--vscode-panel-border:#ccc;--vscode-descriptionForeground:#666;--vscode-textCodeBlock-background:#eee;--vscode-editorWidget-background:#f3f3f3;--vscode-list-hoverBackground:#e8e8e8;--vscode-focusBorder:#07c;--vscode-errorForeground:#c00;--vscode-testing-iconPassed:#080;--vscode-editorWarning-foreground:#a60;' },
  dark: { cls: 'vscode-dark', vars: '--vscode-foreground:#ddd;--vscode-editor-background:#1e1e1e;--vscode-panel-border:#444;--vscode-descriptionForeground:#999;--vscode-textCodeBlock-background:#2a2a2a;--vscode-editorWidget-background:#252526;--vscode-list-hoverBackground:#2a2d2e;--vscode-focusBorder:#07c;--vscode-errorForeground:#f55;--vscode-testing-iconPassed:#4c4;--vscode-editorWarning-foreground:#ca3;' },
};

let browser, dir, page, errors;

before(async (t) => {
  if (!chrome) { t.skip('no Chrome found (set CHROME)'); return; }
  execFileSync('npm', ['run', 'build'], { cwd: root, stdio: 'pipe' });
  dir = mkdtempSync(join(tmpdir(), 'webview-'));
  cpSync(join(root, 'dist'), join(dir, 'dist'), { recursive: true });
  writeFileSync(join(dir, 'index.html'), shellHtml({ nonce: 'n0nce', cspSource: "'self'", panelCss: 'dist/panel.css',
    webviewJs: 'dist/webview.js', vendorBase: 'dist/vendor' }).replace('</head>', '<style id="theme"></style></head>'));
  mkdirSync(join(root, 'test/out'), { recursive: true });
  const { default: puppeteer } = await import('puppeteer-core');
  browser = await puppeteer.launch({ executablePath: chrome, args: ['--no-sandbox', '--allow-file-access-from-files'] });
});

after(async () => { if (browser) await browser.close(); });

async function open(theme = 'light') {
  page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 900 });
  errors = [];
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
  await page.evaluateOnNewDocument(() => {
    window.__posted = [];
    window.acquireVsCodeApi = () => ({ postMessage: (m) => window.__posted.push(m) });
  });
  await page.goto(`file://${join(dir, 'index.html')}`);
  await setTheme(theme);
}

async function setTheme(theme) {
  await page.evaluate((t) => {
    document.getElementById('theme').textContent = `body{${t.vars}}`;
    document.body.className = t.cls;
  }, THEMES[theme]);
}

const render = (html) => page.evaluate((h) => window.postMessage({ type: 'render', html: h }, '*'), html);
const count = (sel) => page.evaluate((s) => document.querySelectorAll(s).length, sel);

const waves = (doc) => (doc.module?.wavedrom.length ?? 0) + doc.processes.reduce((n, p) => n + p.wavedrom.length, 0);
const flows = (doc) => (doc.module?.mermaid.length ?? 0) + doc.processes.reduce((n, p) => n + p.mermaid.length, 0);

for (const theme of ['light', 'dark']) {
  for (const name of ['sample_ctrl', 'sample_capture']) {
    test(`${name} is drawn completely in the ${theme} theme`, async (t) => {
      if (!browser) return t.skip('no Chrome');
      const doc = fixture(name);
      await open(theme);
      await render(renderDocument(doc));
      await page.waitForFunction(([w, f, m]) => document.querySelectorAll('.wavedrom svg').length >= w &&
        document.querySelectorAll('.mermaid svg').length >= f && document.querySelectorAll('.fsm svg').length >= m,
        { timeout: 20000 }, [waves(doc), flows(doc), doc.fsm ? 1 : 0]);
      assert.equal(await count('.wavedrom svg'), waves(doc));
      assert.equal(await count('.mermaid svg'), flows(doc));
      assert.equal(await count('.fsm svg'), doc.fsm ? 1 : 0);
      await page.screenshot({ path: join(root, `test/out/${name}-${theme}.png`), fullPage: true });
      assert.deepEqual(errors, []);
      await page.close();
    });
  }
}

test('clicking a row asks the host to show that line', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('sample_capture');
  await open();
  await render(renderDocument(doc));
  await page.waitForSelector('tr[data-line]');
  const line = await page.evaluate(() => {
    const row = document.querySelector('tr[data-line]');
    row.click();
    return Number(row.getAttribute('data-line'));
  });
  const posted = await page.evaluate(() => window.__posted);
  assert.ok(posted.some((m) => m.type === 'goto' && m.line === line), JSON.stringify(posted));
  assert.ok(posted.some((m) => m.type === 'ready'));
  await page.close();
});

test('changing the theme redraws the diagrams', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('sample_ctrl');
  await open('light');
  await render(renderDocument(doc));
  await page.waitForSelector('.mermaid svg', { timeout: 20000 });
  await page.evaluate(() => { document.querySelector('.mermaid').__old = true; });
  await setTheme('dark');
  await page.waitForFunction(() => document.querySelector('.mermaid svg') && !document.querySelector('.mermaid').__old, { timeout: 20000 });
  assert.deepEqual(errors, []);
  await page.close();
});

test('a broken waveform shows its error and the other diagrams still draw', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('sample_ctrl');
  doc.processes[0].wavedrom = ['{ this is not json'];
  await open();
  await render(renderDocument(doc));
  await page.waitForSelector('.mermaid svg', { timeout: 20000 });
  assert.match(await page.evaluate(() => document.querySelector('.diagram-error')?.textContent ?? ''), /WaveDrom/);
  await page.waitForSelector('.fsm svg', { timeout: 20000 });
  assert.equal(await count('.fsm svg'), 1);
  await page.close();
});

test('the scroll position survives a refresh', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('top');
  await open();
  await render(renderDocument(doc));
  await page.waitForSelector('tr[data-line]');
  await page.evaluate(() => window.scrollTo(0, 400));
  await render(renderDocument(doc));
  await page.waitForFunction(() => document.querySelector('tr[data-line]'));
  assert.ok((await page.evaluate(() => window.scrollY)) >= 300);
  await page.close();
});

test('a waveform does not restyle the rest of the page (its stylesheet is scoped)', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('sample_ctrl');
  await open('dark');
  await render(renderDocument(doc));
  await page.waitForSelector('.fsm svg', { timeout: 20000 });
  await page.waitForSelector('.wavedrom svg', { timeout: 20000 });
  await page.waitForSelector('.mermaid svg', { timeout: 20000 });
  const fill = await page.evaluate(() => getComputedStyle(document.querySelector('.fsm g.node text')).fill);
  assert.equal(fill, 'rgb(0, 0, 0)', 'state names must stay black on their pastel nodes');
  const styles = await page.evaluate(() => [...document.querySelectorAll('.wavedrom svg style')].map((s) => s.textContent));
  assert.ok(styles.length > 0);
  for (const css of styles) assert.doesNotMatch(css, /(^|\})\s*text\s*\{/, 'an unscoped text{} rule would restyle every SVG');
  await page.close();
});

test('waveforms are drawn light-on-dark in a dark theme', async (t) => {
  if (!browser) return t.skip('no Chrome');
  await open('dark');
  await render(renderDocument(fixture('sample_ctrl')));
  await page.waitForSelector('.wavedrom svg', { timeout: 20000 });
  assert.notEqual(await page.evaluate(() => getComputedStyle(document.querySelector('.wavedrom svg')).filter), 'none');
  await setTheme('light');
  await page.waitForFunction(() => getComputedStyle(document.querySelector('.wavedrom svg')).filter === 'none', { timeout: 20000 });
  await page.close();
});

// Fraction of a screenshot's pixels that are dark (luminance < 90) or light (> 165).
async function toneShares(buffer) {
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const canvas = document.createElement('canvas');
    canvas.width = img.width; canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const { data } = ctx.getImageData(0, 0, img.width, img.height);
    let dark = 0, light = 0;
    for (let i = 0; i < data.length; i += 4) {
      const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      if (lum < 90) dark++; else if (lum > 165) light++;
    }
    return { dark: dark / (data.length / 4), light: light / (data.length / 4) };
  }, Buffer.from(buffer).toString('base64'));
}

for (const [theme, main, minor] of [['light', 'light', 'dark'], ['dark', 'dark', 'light']]) {
  test(`a waveform is mostly ${main} background with thin ${minor} lines in the ${theme} theme`, async (t) => {
    if (!browser) return t.skip('no Chrome');
    await open(theme);
    await render(renderDocument(fixture('sample_ctrl')));
    await page.waitForSelector('.wavedrom svg', { timeout: 20000 });
    const shot = await (await page.$('.wavedrom svg')).screenshot();
    const share = await toneShares(shot);
    assert.ok(share[main] > 0.55, `${theme}: ${JSON.stringify(share)}`);
    assert.ok(share[minor] < 0.12, `${theme}: ${JSON.stringify(share)} (filled shapes instead of lines?)`);
    await page.close();
  });
}


const requestExport = () => page.evaluate(() => document.querySelector('[data-export="html"]').click());
const exported = () => page.evaluate(() => window.__posted.find((m) => m.type === 'export'));

test('Export HTML sends the document with its diagrams drawn in the light theme, even from a dark panel', async (t) => {
  if (!browser) return t.skip('no Chrome');
  const doc = fixture('sample_ctrl');
  await open('dark');
  await render(renderDocument(doc));
  await page.waitForFunction(() => document.querySelector('.fsm svg') && document.querySelector('.mermaid svg') && document.querySelector('.wavedrom svg'), { timeout: 20000 });
  await requestExport();
  await page.waitForFunction(() => window.__posted.some((m) => m.type === 'export'), { timeout: 30000 });
  const message = await exported();
  assert.equal(message.format, 'html');
  assert.ok((message.html.match(/<svg/g) ?? []).length >= waves(doc) + flows(doc) + 1, 'every diagram is drawn');
  assert.match(message.html, /ECECFF/i, 'Mermaid default (light) theme');
  assert.doesNotMatch(message.html, /1f2020/i, 'no dark Mermaid theme');
  assert.match(message.html, /<h1[^>]*>sample_ctrl/);
  assert.equal(await count('.export-root'), 0, 'the off-screen copy is removed');
  assert.equal(await count('.fsm svg'), 1, 'the panel itself is untouched');
  assert.equal(await count('.mermaid svg'), flows(doc));
  assert.deepEqual(errors, []);
  await page.close();
});

test('a request from the host exports the same way', async (t) => {
  if (!browser) return t.skip('no Chrome');
  await open();
  await render(renderDocument(fixture('sample_capture')));
  await page.waitForSelector('.mermaid svg', { timeout: 20000 });
  await page.evaluate(() => window.postMessage({ type: 'requestExport', format: 'html' }, '*'));
  await page.waitForFunction(() => window.__posted.some((m) => m.type === 'export'), { timeout: 30000 });
  assert.match((await exported()).html, /sample_capture/);
  await page.close();
});

test('the export button does nothing before there is a document', async (t) => {
  if (!browser) return t.skip('no Chrome');
  await open();
  await requestExport();
  await new Promise((r) => setTimeout(r, 300));
  assert.equal(await exported(), undefined);
  await page.close();
});
