import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Session } from '../src/session.ts';

// A manual scheduler: timers fire only when the test says so.
function scheduler() {
  const timers = new Map();
  let next = 1;
  return {
    set: (fn, ms) => { const id = next++; timers.set(id, { fn, ms }); return id; },
    clear: (id) => { timers.delete(id); },
    pending: () => timers.size,
    fire: () => { const [[id, t]] = [...timers]; timers.delete(id); t.fn(); },
  };
}

const doc = (name, over = {}) => ({
  language: 'vhdl', module: { name, line: 1, description: '', wavedrom: [], mermaid: [] },
  generics: [], ports: [], instances: [], processes: [], fsm: null, cdc: null, reset: null, warnings: [], ...over });
const ok = (name) => ({ ok: true, doc: doc(name) });
const snap = (text, over = {}) => ({ uri: 'file:///a.vhd', languageId: 'vhdl', text, ...over });
const tick = () => new Promise((r) => setImmediate(r));

function make(runImpl) {
  const timers = scheduler();
  const posted = [];
  const runs = [];
  const session = new Session({
    run: (request, signal) => { runs.push({ request, signal }); return runImpl(request, signal, runs.length); },
    post: (m) => posted.push(m),
    delayMs: () => 400,
    setTimer: timers.set, clearTimer: timers.clear,
  });
  return { session, timers, posted, runs };
}

test('rapid updates collapse into one run of the latest text after the pause', async () => {
  const { session, timers, runs } = make(async () => ok('m'));
  session.update(snap('a')); session.update(snap('ab')); session.update(snap('abc'));
  assert.equal(runs.length, 0);
  assert.equal(timers.pending(), 1);
  timers.fire();
  await tick();
  assert.equal(runs.length, 1);
  assert.equal(runs[0].request.text, 'abc');
});

test('the run is told the language, mapping verilog to systemverilog', async () => {
  const { session, timers, runs } = make(async () => ok('m'));
  for (const [id, language] of [['vhdl', 'vhdl'], ['systemverilog', 'systemverilog'], ['verilog', 'systemverilog']]) {
    session.update(snap('x', { languageId: id }));
    timers.fire(); await tick();
    assert.equal(runs.at(-1).request.language, language, id);
  }
});

test('a finished run posts the rendered document', async () => {
  const { session, timers, posted } = make(async () => ok('counter'));
  session.update(snap('x'));
  timers.fire(); await tick();
  assert.equal(posted.length, 1);
  assert.equal(posted[0].type, 'render');
  assert.match(posted[0].html, /counter/);
});

test('flush runs at once and cancels the pending pause', async () => {
  const { session, timers, runs } = make(async () => ok('m'));
  session.update(snap('typing'));
  session.flush(snap('saved'));
  assert.equal(timers.pending(), 0);
  await tick();
  assert.equal(runs.length, 1);
  assert.equal(runs[0].request.text, 'saved');
});

test('a slow older result never replaces a newer one, and the older run is aborted', async () => {
  const resolvers = [];
  const { session, posted, runs } = make((request, signal, n) => new Promise((resolve) => resolvers[n - 1] = resolve));
  session.flush(snap('one'));
  session.flush(snap('two'));
  assert.equal(runs[0].signal.aborted, true);
  assert.equal(runs[1].signal.aborted, false);
  resolvers[1](ok('second'));
  await tick();
  resolvers[0](ok('first'));
  await tick();
  assert.deepEqual(posted.map((m) => /second|first/.exec(m.html)[0]), ['second']);
});

test('a file that is not HDL keeps the last document and says so', async () => {
  const { session, posted, runs, timers } = make(async () => ok('counter'));
  session.flush(snap('x'));
  await tick();
  session.update(snap('# notes', { uri: 'file:///notes.md', languageId: 'markdown' }));
  assert.equal(runs.length, 1);                              // nothing was run for the markdown file
  assert.equal(timers.pending(), 0);
  const last = posted.at(-1);
  assert.match(last.html, /not a VHDL or SystemVerilog file/);
  assert.match(last.html, /notes\.md/);
  assert.match(last.html, /counter/);                         // the previous document is still there
});

test('a file that is not HDL before any document only shows the message', async () => {
  const { session, posted } = make(async () => ok('m'));
  session.update(snap('# notes', { uri: 'file:///notes.md', languageId: 'markdown' }));
  assert.equal(posted.length, 1);
  assert.match(posted[0].html, /not a VHDL or SystemVerilog file/);
});

test('a runner failure is shown, keeping the last document; an aborted run is silent', async () => {
  let call = 0;
  const { session, posted } = make(async () => (++call === 1 ? ok('counter')
    : call === 2 ? { ok: false, kind: 'failed', message: 'status 3: boom' }
    : { ok: false, kind: 'aborted', message: 'superseded' }));
  session.flush(snap('1')); await tick();
  session.flush(snap('2')); await tick();
  assert.match(posted.at(-1).html, /status 3: boom/);
  assert.match(posted.at(-1).html, /counter/);
  const count = posted.length;
  session.flush(snap('3')); await tick();
  assert.equal(posted.length, count);
});

test('a missing Python is shown as an error message', async () => {
  const { session, posted } = make(async () => ({ ok: false, kind: 'no-python', message: 'Set hdlAutodoc.pythonPath' }));
  session.flush(snap('x')); await tick();
  assert.match(posted[0].html, /message-error/);
  assert.match(posted[0].html, /hdlAutodoc\.pythonPath/);
});

test('dispose cancels the pause, aborts the run and ignores a late result', async () => {
  let resolveRun;
  const { session, timers, posted, runs } = make(() => new Promise((resolve) => { resolveRun = resolve; }));
  session.update(snap('x'));
  session.dispose();
  assert.equal(timers.pending(), 0);
  session.flush(snap('y'));                                   // ignored after dispose
  assert.equal(runs.length, 0);
  const second = make(() => new Promise((resolve) => { resolveRun = resolve; }));
  second.session.flush(snap('z'));
  second.session.dispose();
  assert.equal(second.runs[0].signal.aborted, true);
  resolveRun(ok('late'));
  await tick();
  assert.equal(second.posted.length, 0);
  assert.equal(posted.length, 0);
});

test('the pause is read from the setting each time', async () => {
  const delays = [];
  const timers = { set: (fn, ms) => { delays.push(ms); return 1; }, clear: () => {} };
  let ms = 100;
  const session = new Session({ run: async () => ok('m'), post: () => {}, delayMs: () => ms, setTimer: timers.set, clearTimer: timers.clear });
  session.update(snap('a'));
  ms = 250;
  session.update(snap('b'));
  assert.deepEqual(delays, [100, 250]);
});

test('a file is recognised by its extension when no language extension claims it', async () => {
  // Without a VHDL or SystemVerilog extension installed, VS Code calls these files "plaintext".
  const { session, timers, runs } = make(async () => ok('m'));
  const cases = [['file:///w/a.vhd', 'vhdl'], ['file:///w/a.vhdl', 'vhdl'], ['file:///w/a.VHD', 'vhdl'],
    ['file:///w/a.sv', 'systemverilog'], ['file:///w/a.svh', 'systemverilog'],
    ['file:///w/a.v', 'systemverilog'], ['file:///w/a.vh', 'systemverilog']];
  for (const [uri, language] of cases) {
    session.update(snap('x', { uri, languageId: 'plaintext' }));
    timers.fire(); await tick();
    assert.equal(runs.at(-1).request.language, language, uri);
  }
});

test('other extensions are not mistaken for HDL even when the language id is plaintext', async () => {
  const { session, runs, posted } = make(async () => ok('m'));
  for (const uri of ['file:///w/notes.txt', 'file:///w/a.vhd.bak', 'file:///w/README.md', 'file:///w/v']) {
    session.update(snap('x', { uri, languageId: 'plaintext' }));
  }
  assert.equal(runs.length, 0);
  assert.equal(posted.length, 4);
});

test('a language id that names a different language wins over the extension', async () => {
  const { session, runs } = make(async () => ok('m'));
  session.flush(snap('x', { uri: 'file:///w/a.vhd', languageId: 'markdown' }));
  assert.equal(runs.length, 0);
});
