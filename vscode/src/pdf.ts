// PDF export: a Chromium-based browser prints the exported HTML page headlessly.  No `vscode`
// import, so the browser search and the run are unit-testable with a fake browser.
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

export interface BrowserSearch {
  /** The user's `hdlAutodoc.browserPath`; when set it is the only candidate. */
  setting?: string;
  platform: string;
  env: Record<string, string | undefined>;
  exists(path: string): boolean;
}

function candidates(platform: string, env: Record<string, string | undefined>): string[] {
  if (platform === 'darwin') {
    return ['Google Chrome', 'Microsoft Edge', 'Brave Browser', 'Chromium'].map((n) => `/Applications/${n}.app/Contents/MacOS/${n}`);
  }
  if (platform === 'win32') {
    const bases = [env.PROGRAMFILES, env['PROGRAMFILES(X86)'], env.LOCALAPPDATA].filter((b): b is string => !!b);
    const relative = ['\\Google\\Chrome\\Application\\chrome.exe', '\\Microsoft\\Edge\\Application\\msedge.exe',
      '\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'];
    return bases.flatMap((b) => relative.map((r) => b + r));
  }
  return ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/usr/bin/microsoft-edge', '/usr/bin/brave-browser', '/snap/bin/chromium'];
}

export function findBrowser(o: BrowserSearch): string | undefined {
  if (o.setting) return o.exists(o.setting) ? o.setting : undefined;   // an explicit choice is not second-guessed
  return candidates(o.platform, o.env).find((p) => o.exists(p));
}

export const systemBrowser = (setting?: string): string | undefined =>
  findBrowser({ setting, platform: process.platform, env: process.env, exists: existsSync });

export function printArgs(htmlFile: string, pdfFile: string, profileDir: string, asRoot: boolean): string[] {
  return [
    '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--no-first-run', '--no-default-browser-check',
    // Its own profile: otherwise the browser hands the job to an already running instance and prints nothing.
    `--user-data-dir=${profileDir}`,
    ...(asRoot ? ['--no-sandbox'] : []),                                // a container's root cannot use the sandbox
    `--print-to-pdf=${pdfFile}`,
    pathToFileURL(htmlFile).href,
  ];
}

export type PrintResult = { ok: true } | { ok: false; message: string };

export interface PrintOptions {
  browser: string;
  html: string;
  pdf: string;
  timeoutMs: number;
}

export function printToPdf(o: PrintOptions): Promise<PrintResult> {
  const profile = mkdtempSync(join(tmpdir(), 'hdl-autodoc-browser-'));
  return new Promise<PrintResult>((resolve) => {
    const child = spawn(o.browser, printArgs(o.html, o.pdf, profile, process.getuid?.() === 0), { stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = '';
    let settled = false;
    const finish = (result: PrintResult): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      rmSync(profile, { recursive: true, force: true });
      resolve(result);
    };
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      finish({ ok: false, message: `The browser took longer than ${Math.round(o.timeoutMs / 1000)} s to print the page.` });
    }, o.timeoutMs);
    child.stderr.on('data', (c: Buffer) => { stderr += c.toString('utf8'); });
    child.on('error', (e) => finish({ ok: false, message: `Could not run "${o.browser}": ${e.message}` }));
    child.on('close', (code) => {
      if (code !== 0) finish({ ok: false, message: `The browser exited with status ${code}: ${stderr.trim().slice(0, 500)}` });
      else if (!existsSync(o.pdf)) finish({ ok: false, message: 'The browser finished but wrote no PDF.' });
      else finish({ ok: true });
    });
  });
}
