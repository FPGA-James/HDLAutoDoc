// Runs autodoc_json.py for one source text and returns the parsed document, or a
// classified failure the panel can explain.  No `vscode` import: unit-testable on its own.
import { spawn } from 'node:child_process';
import type { Document, Language } from './types.ts';

export interface RunOptions {
  python: string;
  script: string;
  language: Language;
  text: string;
  support: string[];
  busGroups?: string;
  timeoutMs: number;
  signal?: AbortSignal;
}

export type FailureKind = 'no-python' | 'old-python' | 'timeout' | 'aborted' | 'failed' | 'bad-json';

export type RunResult =
  | { ok: true; doc: Document }
  | { ok: false; kind: FailureKind; message: string };

const MIN_MAJOR = 3;
const MIN_MINOR = 11;
const PROBE_CODE = 'import sys; print("%d.%d" % sys.version_info[:2])';

const versions = new Map<string, Promise<[number, number] | null>>();

/** Forget the probed interpreter versions (tests, and after the setting changes). */
export function resetVersionCache(): void {
  versions.clear();
}

function probe(python: string): Promise<[number, number] | null> {
  return new Promise((resolve) => {
    const child = spawn(python, ['-c', PROBE_CODE], { stdio: ['ignore', 'pipe', 'ignore'] });
    let out = '';
    child.stdout.on('data', (chunk: Buffer) => { out += chunk.toString('utf8'); });
    child.on('error', () => resolve(null));
    child.on('close', () => {
      const m = /^(\d+)\.(\d+)/.exec(out.trim());
      resolve(m ? [Number(m[1]), Number(m[2])] : null);
    });
  });
}

async function interpreterVersion(python: string): Promise<[number, number] | null> {
  let pending = versions.get(python);
  if (!pending) {
    pending = probe(python);
    versions.set(python, pending);
  }
  const version = await pending;
  if (version === null) versions.delete(python);       // not found or unusable: look again next time
  return version;
}

const fail = (kind: FailureKind, message: string): RunResult => ({ ok: false, kind, message });

export async function runAutodocJson(opts: RunOptions): Promise<RunResult> {
  if (opts.signal?.aborted) return fail('aborted', 'The refresh was superseded.');

  const version = await interpreterVersion(opts.python);
  if (version === null) {
    return fail('no-python',
      `Could not run "${opts.python}". Set hdlAutodoc.pythonPath to a Python ${MIN_MAJOR}.${MIN_MINOR} or newer.`);
  }
  if (version[0] < MIN_MAJOR || (version[0] === MIN_MAJOR && version[1] < MIN_MINOR)) {
    return fail('old-python',
      `"${opts.python}" is Python ${version[0]}.${version[1]}; HDL AutoDoc needs ${MIN_MAJOR}.${MIN_MINOR} or newer. ` +
      'Set hdlAutodoc.pythonPath to a newer interpreter.');
  }
  if (opts.signal?.aborted) return fail('aborted', 'The refresh was superseded.');

  const args = [opts.script, '--language', opts.language];
  if (opts.support.length > 0) args.push('--support', ...opts.support);
  if (opts.busGroups) args.push('--bus-groups', opts.busGroups);

  return new Promise<RunResult>((resolve) => {
    const child = spawn(opts.python, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    const out: Buffer[] = [];
    const err: Buffer[] = [];
    let settled = false;

    const finish = (result: RunResult): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      opts.signal?.removeEventListener('abort', onAbort);
      resolve(result);
    };
    const kill = (): void => { child.kill('SIGKILL'); };
    const onAbort = (): void => { kill(); finish(fail('aborted', 'The refresh was superseded.')); };
    const timer = setTimeout(() => {
      kill();
      finish(fail('timeout', `Reading the file took longer than ${opts.timeoutMs} ms.`));
    }, opts.timeoutMs);
    opts.signal?.addEventListener('abort', onAbort, { once: true });

    child.stdout.on('data', (c: Buffer) => out.push(c));
    child.stderr.on('data', (c: Buffer) => err.push(c));
    child.stdin.on('error', () => { /* the child exited before reading everything */ });
    child.on('error', (e) => finish(fail('no-python', `Could not run "${opts.python}": ${e.message}`)));
    child.on('close', (code) => {
      if (code !== 0) {
        const detail = Buffer.concat(err).toString('utf8').trim().slice(0, 2000);
        finish(fail('failed', `autodoc_json.py exited with status ${code}${detail ? `: ${detail}` : ''}`));
        return;
      }
      try {
        finish({ ok: true, doc: JSON.parse(Buffer.concat(out).toString('utf8')) as Document });
      } catch (e) {
        finish(fail('bad-json', `autodoc_json.py wrote output that is not JSON (${(e as Error).message}).`));
      }
    });

    child.stdin.end(Buffer.from(opts.text, 'utf8'));
  });
}
