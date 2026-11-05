import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderDocument, renderMessage } from '../src/render.ts';

const fixture = (name) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/${name}.json`, import.meta.url)), 'utf8'));
const css = readFileSync(fileURLToPath(new URL('../src/panel.css', import.meta.url)), 'utf8');

const empty = (over = {}) => ({
  language: 'vhdl', module: { name: 'm', line: 1, description: '', wavedrom: [], mermaid: [] },
  generics: [], ports: [], instances: [], processes: [], fsm: null, cdc: null, reset: null, warnings: [], ...over,
});
const port = (over = {}) => ({ name: 'p', direction: 'in', type: 'std_logic', range: '', description: '',
  line: 5, kind: 'port', interface: null, modport: null, group: null, ...over });

test('every text field is HTML-escaped', () => {
  const html = renderDocument(empty({
    module: { name: '<img src=x>', line: 1, description: '<script>alert(1)</script> & "q"', wavedrom: [], mermaid: [] },
    ports: [port({ name: '<b>', description: '</td><script>x</script>', type: 'a&b' })],
    warnings: ['<warn>'],
  }));
  assert.doesNotMatch(html, /<script|<img|<b>|<warn>/);
  assert.match(html, /&lt;b&gt;/);
  assert.match(html, /a&amp;b/);
});

test('sections with nothing in them are left out', () => {
  const html = renderDocument(empty());
  for (const heading of ['Generics', 'Ports', 'Instances', 'State machine', 'Processes', 'Clock domains', 'Reset domains', 'Warnings']) {
    assert.doesNotMatch(html, new RegExp(`<h2[^>]*>${heading}`), heading);
  }
  assert.doesNotMatch(html, /class="fsm"/);
});

test('a missing module is explained instead of rendering an empty header', () => {
  const html = renderDocument(empty({ module: null, warnings: ['No entity found.'] }));
  assert.match(html, /No entity found\./);
  assert.doesNotMatch(html, /<h1/);
});

test('the module header shows name, language and description paragraphs with inline code', () => {
  const html = renderDocument(empty({ module: { name: 'counter', line: 7, description: 'First line\ncontinues.\n\nSecond ``paragraph``.', wavedrom: [], mermaid: [] } }));
  assert.match(html, /<h1[^>]*data-line="7"[^>]*>counter/);
  assert.match(html, /<p>First line\s+continues\.<\/p>/);
  assert.match(html, /<p>Second <code>paragraph<\/code>\.<\/p>/);
});

test('ports sit in one table, with bus groups as their own headed tables', () => {
  const html = renderDocument(empty({ ports: [
    port({ name: 'clk' }), port({ name: 'adc_clk', group: 'Converter interface' }), port({ name: 'adc_data', group: 'Converter interface' }),
  ] }));
  assert.match(html, /<h2[^>]*>Ports/);
  assert.match(html, /<h3[^>]*>Converter interface/);
  const plain = html.slice(html.indexOf('<h2'), html.indexOf('<h3'));
  assert.match(plain, /clk/);
  assert.doesNotMatch(plain, /adc_clk/);
  assert.equal((html.match(/adc_data/g) ?? []).length, 1);
});

test('rows that map to a source line carry data-line', () => {
  const html = renderDocument(empty({
    generics: [{ name: 'W', type: 'positive', default: '8', description: 'Width.', line: 3 }],
    ports: [port({ name: 'a', line: 11 }), port({ name: 'b', line: 12 })],
    instances: [{ instance: 'u1', component: 'x', kind: 'module', line: 20 }],
  }));
  for (const n of [3, 11, 12, 20]) assert.match(html, new RegExp(`<tr[^>]*data-line="${n}"`), String(n));
});

test('interface ports show the interface and modport', () => {
  const html = renderDocument(empty({ language: 'systemverilog', ports: [
    port({ name: 's_axis', kind: 'interface', interface: 'axis_if', modport: 'slave', direction: 'slave', type: 'axis_if' }) ] }));
  assert.match(html, /axis_if\.slave/);
});

test('the state machine is a placeholder with its Graphviz source, plus a transition table', () => {
  const dot = 'digraph m { A -> B [label="mode = \\"01\\""]; }';
  const html = renderDocument(empty({ fsm: { states: ['A', 'B'], dot,
    transitions: [{ from: 'A', to: 'B', condition: "x = '1'" }, { from: 'B', to: 'A', condition: '' }] } }));
  assert.match(html, /<div class="fsm" data-dot="digraph m \{ A -&gt; B \[label=&quot;mode = \\&quot;01\\&quot;&quot;\]; \}"/);
  assert.match(html, /<td>A<\/td>\s*<td>B<\/td>\s*<td><code>x = &#39;1&#39;<\/code><\/td>/);
  assert.match(html, /always/);
});

test('WaveDrom blocks and Mermaid diagrams become placeholders; a caption becomes a figcaption', () => {
  const html = renderDocument(empty({ module: { name: 'm', line: 1, description: '', wavedrom: ['{ "signal": [{ "name": "clk" }] }'],
    mermaid: [{ caption: 'Flow', source: 'flowchart LR\n  A --> B' }, { caption: null, source: 'graph TD\n  X --> Y' }] } }));
  assert.match(html, /<div class="wavedrom" data-source="\{ &quot;signal&quot;: \[\{ &quot;name&quot;: &quot;clk&quot; \}\] \}"/);
  assert.match(html, /<pre class="mermaid">flowchart LR\n  A --&gt; B<\/pre>/);
  assert.match(html, /<figcaption>Flow<\/figcaption>/);
  assert.equal((html.match(/<figcaption>/g) ?? []).length, 1);
});

test('processes show label, kind, sensitivity, description, diagrams and their line', () => {
  const html = renderDocument(empty({ processes: [{ label: 'p_main', kind: 'process', line: 40, sensitivity: ['clk', 'rst_n'],
    description: 'Does the work.', wavedrom: ['{}'], mermaid: [] }] }));
  assert.match(html, /<h2[^>]*>Processes/);
  assert.match(html, /<article[^>]*data-line="40"/);
  assert.match(html, /p_main/);
  assert.match(html, /clk, rst_n/);
  assert.match(html, /Does the work\./);
  assert.match(html, /class="wavedrom"/);
});

test('clock domains list processes, crossings say whether they are synchronised, and dual-clock instances are named', () => {
  const html = renderDocument(empty({ cdc: {
    domains: { clk: ['p_a'], adc_clk: ['p_b', 'p_c'] },
    crossings: [{ signal: 'req', src_clock: 'clk', dst_clock: 'adc_clk', synchronized: true },
                { signal: 'oops', src_clock: 'adc_clk', dst_clock: 'clk', synchronized: false }],
    dual_clock_instances: [{ instance: 'u_fifo', component: 'async_fifo', clocks: { wr_clk: 'adc_clk', rd_clk: 'clk' } }] } }));
  assert.match(html, /<h2[^>]*>Clock domains/);
  assert.match(html, /p_b, p_c/);
  assert.match(html, /req[\s\S]*?clk[\s\S]*?adc_clk[\s\S]*?two-flop/);
  assert.match(html, /oops[\s\S]*?not synchronised/);
  assert.match(html, /u_fifo[\s\S]*?async_fifo/);
});

test('reset domains name the style of each process; no reset is shown as "none"', () => {
  const html = renderDocument(empty({ reset: {
    processes: [{ label: 'p_a', clock: 'clk', reset: 'rst', style: 'sync' }, { label: 'p_b', clock: 'clk', reset: null, style: 'none' }],
    domains: { rst: ['p_a'], __none__: ['p_b'] }, crossings: [{ signal: 'x', src_reset: 'rst', dst_reset: '__none__' }] } }));
  assert.match(html, /<h2[^>]*>Reset domains/);
  assert.match(html, /p_a[\s\S]*?clk[\s\S]*?rst[\s\S]*?sync/);
  assert.doesNotMatch(html, /__none__/);
  assert.match(html, /none/);
});

test('warnings are listed', () => {
  const html = renderDocument(empty({ warnings: ['ports: RuntimeError: boom'] }));
  assert.match(html, /<h2[^>]*>Warnings/);
  assert.match(html, /ports: RuntimeError: boom/);
});

test('renderMessage escapes its text and carries the kind', () => {
  const html = renderMessage('error', 'Could not run "<python>"');
  assert.match(html, /class="message message-error"/);
  assert.match(html, /&lt;python&gt;/);
});

for (const name of ['sample_capture', 'sample_ctrl', 'top']) {
  test(`the real document for ${name} renders completely`, () => {
    const doc = fixture(name);
    const html = renderDocument(doc);
    assert.match(html, new RegExp(`<h1[^>]*>${name}`));
    for (const p of doc.ports) assert.match(html, new RegExp(`data-line="${p.line}"`));
    assert.doesNotMatch(html, /undefined|\[object|>null<|NaN/);
    if (doc.fsm) assert.match(html, /class="fsm"/);
    for (const proc of doc.processes) assert.ok(html.includes(proc.label));
  });
}

test('the converter bus group of sample_capture is shown under its own heading', () => {
  assert.match(renderDocument(fixture('sample_capture')), /<h3[^>]*>Converter interface/);
});

test('the stylesheet uses only VS Code theme variables, never fixed colours', () => {
  assert.match(css, /var\(--vscode-/);
  assert.doesNotMatch(css, /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
});
