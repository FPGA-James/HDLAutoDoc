import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { findBrowser, printArgs, printToPdf } from '../src/pdf.ts';
import { exportPage } from '../src/export.ts';
import { renderDocument } from '../src/render.ts';

const fake = fileURLToPath(new URL('./fixtures/fake-browser', import.meta.url));
const fixture = (name) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/${name}.json`, import.meta.url)), 'utf8'));
const only = (...present) => (p) => present.includes(p);

// ── finding a browser ──
test('the setting wins when the file exists', () => {
  assert.equal(findBrowser({ setting: '/opt/mine/chrome', platform: 'darwin', env: {}, exists: only('/opt/mine/chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') }), '/opt/mine/chrome');
});

test('a setting that names a missing file is not silently replaced by another browser', () => {
  assert.equal(findBrowser({ setting: '/opt/gone', platform: 'darwin', env: {}, exists: only('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') }), undefined);
});

test('macOS: Chrome, then Edge, Brave and Chromium', () => {
  const chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const edge = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge';
  assert.equal(findBrowser({ platform: 'darwin', env: {}, exists: only(chrome, edge) }), chrome);
  assert.equal(findBrowser({ platform: 'darwin', env: {}, exists: only(edge) }), edge);
  assert.ok(findBrowser({ platform: 'darwin', env: {}, exists: only('/Applications/Brave Browser.app/Contents/MacOS/Brave Browser') }));
  assert.ok(findBrowser({ platform: 'darwin', env: {}, exists: only('/Applications/Chromium.app/Contents/MacOS/Chromium') }));
});

test('Windows: the install folders named by the environment, Chrome or Edge', () => {
  const env = { PROGRAMFILES: 'C:\\Program Files', 'PROGRAMFILES(X86)': 'C:\\Program Files (x86)', LOCALAPPDATA: 'C:\\Users\\a\\AppData\\Local' };
  const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  assert.equal(findBrowser({ platform: 'win32', env, exists: only(edge) }), edge);
  const chrome = 'C:\\Users\\a\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe';
  assert.equal(findBrowser({ platform: 'win32', env, exists: only(chrome) }), chrome);
});

test('Linux: the usual command locations', () => {
  assert.equal(findBrowser({ platform: 'linux', env: {}, exists: only('/usr/bin/chromium') }), '/usr/bin/chromium');
  assert.equal(findBrowser({ platform: 'linux', env: {}, exists: only('/usr/bin/google-chrome') }), '/usr/bin/google-chrome');
});

test('no browser gives undefined', () => {
  assert.equal(findBrowser({ platform: 'linux', env: {}, exists: () => false }), undefined);
  assert.equal(findBrowser({ platform: 'win32', env: {}, exists: () => false }), undefined);
});

// ── the command line ──
test('the browser prints headlessly, without header and footer, with its own profile', () => {
  const args = printArgs('/tmp/a b/page.html', '/tmp/out.pdf', '/tmp/profile', false);
  for (const wanted of ['--headless=new', '--no-pdf-header-footer', '--user-data-dir=/tmp/profile', '--print-to-pdf=/tmp/out.pdf']) {
    assert.ok(args.includes(wanted), wanted);
  }
  assert.equal(args.at(-1), 'file:///tmp/a%20b/page.html');
  assert.ok(!args.includes('--no-sandbox'));
});

test('as root (a container) the sandbox is switched off, or the browser refuses to start', () => {
  assert.ok(printArgs('/p.html', '/o.pdf', '/pr', true).includes('--no-sandbox'));
});

// ── running it ──
let scratch;
beforeEach(() => {
  scratch = mkdtempSync(join(tmpdir(), 'pdf-'));
  for (const k of ['FAKE_BROWSER_MODE', 'FAKE_BROWSER_ARGS']) delete process.env[k];
});
const run = (over = {}) => {
  writeFileSync(join(scratch, 'p.html'), '<p>x</p>');
  return printToPdf({ browser: fake, html: join(scratch, 'p.html'), pdf: join(scratch, 'o.pdf'), timeoutMs: 5000, ...over });
};

test('a browser that writes the file is a success', async () => {
  process.env.FAKE_BROWSER_ARGS = join(scratch, 'args.json');
  assert.deepEqual(await run(), { ok: true });
  assert.ok(readFileSync(join(scratch, 'o.pdf'), 'utf8').startsWith('%PDF'));
  const args = JSON.parse(readFileSync(join(scratch, 'args.json'), 'utf8'));
  assert.ok(args.some((a) => a.startsWith('--print-to-pdf=')));
});

test('the temporary profile is removed afterwards', async () => {
  process.env.FAKE_BROWSER_ARGS = join(scratch, 'args.json');
  await run();
  const profile = JSON.parse(readFileSync(join(scratch, 'args.json'), 'utf8')).find((a) => a.startsWith('--user-data-dir=')).slice(16);
  assert.equal(existsSync(profile), false);
});

test('a browser that exits without writing the file is a failure that says so', async () => {
  process.env.FAKE_BROWSER_MODE = 'nofile';
  const r = await run();
  assert.equal(r.ok, false);
  assert.match(r.message, /no PDF/i);
});

test('a browser that fails reports its error output', async () => {
  process.env.FAKE_BROWSER_MODE = 'fail';
  const r = await run();
  assert.equal(r.ok, false);
  assert.match(r.message, /Failed to launch/);
});

test('a browser that hangs is stopped at the time limit', async () => {
  process.env.FAKE_BROWSER_MODE = 'hang';
  const started = Date.now();
  const r = await run({ timeoutMs: 300 });
  assert.equal(r.ok, false);
  assert.match(r.message, /longer than/);
  assert.ok(Date.now() - started < 3000);
});

test('a browser that cannot be started is reported', async () => {
  const r = await run({ browser: '/definitely/not/a/browser' });
  assert.equal(r.ok, false);
  assert.match(r.message, /\/definitely\/not\/a\/browser/);
});

// ── print styling ──
test('the exported page is set up for paper: A4, tables and diagrams kept whole, colours kept', () => {
  const html = exportPage('m', '', '');
  assert.match(html, /@page\s*\{[^}]*size:\s*A4/);
  assert.match(html, /break-inside:\s*avoid/);
  assert.match(html, /break-after:\s*avoid/);
  assert.match(html, /print-color-adjust:\s*exact/);
});

// ── a real PDF, when a browser is installed ──
const browser = findBrowser({ platform: process.platform, env: process.env, exists: existsSync });

test('a real browser turns the exported page into a PDF with the documentation as text', async (t) => {
  if (!browser) return t.skip('no Chromium-based browser found');
  const body = renderDocument(fixture('sample_ctrl'));
  const html = join(scratch, 'real.html');
  writeFileSync(html, exportPage('sample_ctrl', body, readFileSync(fileURLToPath(new URL('../src/panel.css', import.meta.url)), 'utf8')));
  const pdf = join(scratch, 'real.pdf');
  assert.deepEqual(await printToPdf({ browser, html, pdf, timeoutMs: 60000 }), { ok: true });
  const bytes = readFileSync(pdf);
  assert.equal(bytes.subarray(0, 5).toString(), '%PDF-');
  try {
    const text = execFileSync('pdftotext', [pdf, '-'], { encoding: 'utf8' });
    assert.match(text, /sample_ctrl/);
    assert.match(text, /capture_en/);
    const info = execFileSync('pdfinfo', [pdf], { encoding: 'utf8' });
    assert.match(info, /Page size:\s+59[45]\.\d+ x 841\.\d+ pts \(A4\)/);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;      // poppler not installed: the header check stands
  }
});
