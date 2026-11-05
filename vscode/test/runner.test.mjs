import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runAutodocJson, resetVersionCache } from '../src/runner.ts';

const fake = fileURLToPath(new URL('./fixtures/fake-python', import.meta.url));
const base = { python: fake, script: '/x/autodoc_json.py', language: 'vhdl', text: 'entity e is end;',
               support: [], timeoutMs: 5000 };

beforeEach(() => {
  resetVersionCache();
  for (const k of ['FAKE_VERSION', 'FAKE_MODE', 'FAKE_PIDFILE', 'FAKE_PROBEFILE']) delete process.env[k];
});

const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };
const gone = async (pid) => { for (let i = 0; i < 40 && alive(pid); i++) await new Promise((r) => setTimeout(r, 50)); return !alive(pid); };

test('a successful run returns the parsed document and passes the arguments through', async () => {
  const r = await runAutodocJson({ ...base, language: 'systemverilog', support: ['/a/x.sv', '/b/y.sv'], busGroups: '/g.toml' });
  assert.equal(r.ok, true);
  assert.equal(r.doc.language, 'systemverilog');
  assert.deepEqual(JSON.parse(r.doc.warnings[0]),
    ['/x/autodoc_json.py', '--language', 'systemverilog', '--support', '/a/x.sv', '/b/y.sv', '--bus-groups', '/g.toml']);
});

test('no --support or --bus-groups flags are passed when there are none', async () => {
  const r = await runAutodocJson(base);
  assert.deepEqual(JSON.parse(r.doc.warnings[0]), ['/x/autodoc_json.py', '--language', 'vhdl']);
});

test('the source text reaches the interpreter unchanged (CRLF, non-ASCII)', async () => {
  process.env.FAKE_MODE = 'echo';
  const text = 'entity é is\r\n-- Zählt Anfragen — naïve.\r\nend;\r\n';
  const r = await runAutodocJson({ ...base, text });
  assert.equal(r.doc.module.description, text);
});

test('a missing interpreter is reported with the setting to change', async () => {
  const r = await runAutodocJson({ ...base, python: '/definitely/not/python' });
  assert.equal(r.ok, false);
  assert.equal(r.kind, 'no-python');
  assert.match(r.message, /hdlAutodoc\.pythonPath/);
  assert.match(r.message, /\/definitely\/not\/python/);
});

test('a Python older than 3.11 is reported with both versions', async () => {
  process.env.FAKE_VERSION = '3.9';
  const r = await runAutodocJson(base);
  assert.equal(r.kind, 'old-python');
  assert.match(r.message, /3\.9/);
  assert.match(r.message, /3\.11/);
});

test('3.11 and newer are accepted, including 3.100', async () => {
  for (const v of ['3.11', '3.13', '3.100']) {
    resetVersionCache();
    process.env.FAKE_VERSION = v;
    assert.equal((await runAutodocJson(base)).ok, true, v);
  }
});

test('the version of an interpreter is probed once, not on every run', async () => {
  const probes = join(mkdtempSync(join(tmpdir(), 'probe-')), 'probes');
  process.env.FAKE_PROBEFILE = probes;
  await runAutodocJson(base);
  await runAutodocJson(base);
  assert.equal(readFileSync(probes, 'utf8').trim().split('\n').length, 1);
});

test('a run that takes too long is killed and reported as a timeout', async () => {
  const pidfile = join(mkdtempSync(join(tmpdir(), 'pid-')), 'pid');
  process.env.FAKE_MODE = 'hang';
  process.env.FAKE_PIDFILE = pidfile;
  const started = Date.now();
  const r = await runAutodocJson({ ...base, timeoutMs: 300 });
  assert.equal(r.kind, 'timeout');
  assert.ok(Date.now() - started < 3000);
  assert.ok(await gone(Number(readFileSync(pidfile, 'utf8'))), 'the child is still running');
});

test('aborting a run kills the child and reports it as aborted', async () => {
  const pidfile = join(mkdtempSync(join(tmpdir(), 'pid-')), 'pid');
  process.env.FAKE_MODE = 'hang';
  process.env.FAKE_PIDFILE = pidfile;
  const controller = new AbortController();
  const pending = runAutodocJson({ ...base, signal: controller.signal });
  setTimeout(() => controller.abort(), 300);
  const r = await pending;
  assert.equal(r.kind, 'aborted');
  assert.ok(await gone(Number(readFileSync(pidfile, 'utf8'))), 'the child is still running');
});

test('an already aborted signal never starts a process', async () => {
  const pidfile = join(mkdtempSync(join(tmpdir(), 'pid-')), 'pid');
  process.env.FAKE_PIDFILE = pidfile;
  const controller = new AbortController();
  controller.abort();
  const r = await runAutodocJson({ ...base, signal: controller.signal });
  assert.equal(r.kind, 'aborted');
  assert.equal(existsSync(pidfile), false);
});

test('a non-zero exit is a failure that carries the error output', async () => {
  process.env.FAKE_MODE = 'fail';
  const r = await runAutodocJson(base);
  assert.equal(r.kind, 'failed');
  assert.match(r.message, /something broke/);
});

test('output that is not JSON is reported as such', async () => {
  process.env.FAKE_MODE = 'badjson';
  const r = await runAutodocJson(base);
  assert.equal(r.kind, 'bad-json');
});

test('the runner works with the real autodoc_json.py', async () => {
  const script = fileURLToPath(new URL('../../src/scripts/hdl_autodoc/autodoc_json.py', import.meta.url));
  const text = readFileSync(fileURLToPath(new URL('../../example_full/src/sample_ctrl.vhd', import.meta.url)), 'utf8');
  const r = await runAutodocJson({ ...base, python: 'python3', script, text });
  assert.equal(r.ok, true, r.message);
  assert.equal(r.doc.module.name, 'sample_ctrl');
  assert.equal(r.doc.fsm.states.length, 4);
  assert.ok(r.doc.processes.some((p) => p.label === 'p_next_state' && p.mermaid.length === 1));
});
