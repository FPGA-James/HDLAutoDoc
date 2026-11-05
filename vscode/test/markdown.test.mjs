import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { renderMarkdown } from '../src/markdown.ts';

const fixture = (name) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/${name}.json`, import.meta.url)), 'utf8'));
const empty = (over = {}) => ({
  language: 'vhdl', module: { name: 'm', line: 1, description: '', wavedrom: [], mermaid: [] },
  generics: [], ports: [], instances: [], processes: [], fsm: null, cdc: null, reset: null, warnings: [], ...over });
const port = (over = {}) => ({ name: 'p', direction: 'in', type: 'std_logic', range: '', description: '',
  line: 5, kind: 'port', interface: null, modport: null, group: null, ...over });

test('a heading with the module name, then its description', () => {
  const md = renderMarkdown(empty({ module: { name: 'counter', line: 1, description: 'Counts.\n\nMore.', wavedrom: [], mermaid: [] } }));
  assert.match(md, /^# counter\n\nCounts\.\n\nMore\.\n/);
});

test('sections with nothing in them are left out', () => {
  const md = renderMarkdown(empty());
  assert.doesNotMatch(md, /^## /m);
});

test('ports are a table, with bus groups as their own headed tables', () => {
  const md = renderMarkdown(empty({ ports: [
    port({ name: 'clk', description: 'Clock.' }), port({ name: 'adc_clk', group: 'Converter interface' }) ] }));
  assert.match(md, /## Ports\n\n\| Name \| Direction \| Type \| Description \|\n\| --- \| --- \| --- \| --- \|\n\| `clk` \| in \| std_logic \| Clock\. \|/);
  assert.match(md, /### Converter interface\n\n\|[^\n]*\n\|[^\n]*\n\| `adc_clk`/);
});

test('table cells cannot break the table: pipes are escaped and line breaks become spaces', () => {
  const md = renderMarkdown(empty({ ports: [port({ description: 'a | b\nc' })], generics: [{ name: 'W', type: 'int', default: 'a|b', description: '', line: 1 }] }));
  assert.match(md, /\| a \\\| b c \|/);
  assert.match(md, /`a\\\|b`/);
});

test('parameters are named for SystemVerilog and generics for VHDL', () => {
  const g = [{ name: 'W', type: 'int', default: '8', description: '', line: 1 }];
  assert.match(renderMarkdown(empty({ generics: g })), /^## Generics$/m);
  assert.match(renderMarkdown(empty({ language: 'systemverilog', generics: g })), /^## Parameters$/m);
});

test('Mermaid diagrams are inserted as fenced mermaid code, with the caption above', () => {
  const md = renderMarkdown(empty({ module: { name: 'm', line: 1, description: '', wavedrom: [],
    mermaid: [{ caption: 'Flow', source: 'flowchart LR\n  A --> B' }] } }));
  assert.match(md, /\*Flow\*\n\n```mermaid\nflowchart LR\n  A --> B\n```/);
});

test('WaveDrom blocks are inserted as fenced wavedrom code', () => {
  const md = renderMarkdown(empty({ processes: [{ label: 'p', kind: 'process', line: 3, sensitivity: ['clk'], description: '',
    wavedrom: ['{ "signal": [] }'], mermaid: [] }] }));
  assert.match(md, /```wavedrom\n\{ "signal": \[\] \}\n```/);
});

test('the state machine is its Graphviz source in a dot fence, with a transition table', () => {
  const md = renderMarkdown(empty({ fsm: { states: ['A', 'B'], dot: 'digraph m { A -> B; }',
    transitions: [{ from: 'A', to: 'B', condition: "x = '1'" }, { from: 'B', to: 'A', condition: '' }] } }));
  assert.match(md, /```dot\ndigraph m \{ A -> B; \}\n```/);
  assert.match(md, /\| A \| B \| `x = '1'` \|/);
  assert.match(md, /\| B \| A \| always \|/);
});

test('a fence is longer than any run of backticks inside the code it holds', () => {
  const md = renderMarkdown(empty({ module: { name: 'm', line: 1, description: '', wavedrom: [],
    mermaid: [{ caption: null, source: 'A["``` x"]' }] } }));
  assert.match(md, /````mermaid\nA\["``` x"\]\n````/);
});

test('processes: heading, sensitivity, description', () => {
  const md = renderMarkdown(empty({ processes: [{ label: 'p_main', kind: 'always_ff', line: 9, sensitivity: ['posedge clk'],
    description: 'Does the work.', wavedrom: [], mermaid: [] }] }));
  assert.match(md, /## Processes\n\n### p_main \(always_ff\)\n\nSensitivity: `posedge clk`\n\nDoes the work\./);
});

test('clock and reset domains, crossings and dual-clock instances', () => {
  const md = renderMarkdown(empty({
    cdc: { domains: { clk: ['p_a'], adc_clk: ['p_b'] }, crossings: [{ signal: 'req', src_clock: 'clk', dst_clock: 'adc_clk', synchronized: true },
      { signal: 'oops', src_clock: 'adc_clk', dst_clock: 'clk', synchronized: false }],
      dual_clock_instances: [{ instance: 'u_fifo', component: 'async_fifo', clocks: { wr_clk: 'adc_clk', rd_clk: 'clk' } }] },
    reset: { processes: [{ label: 'p_a', clock: 'clk', reset: null, style: 'none' }], domains: { __none__: ['p_a'] }, crossings: [] } }));
  assert.match(md, /## Clock domains/);
  assert.match(md, /\| `req` \| clk \| adc_clk \| two-flop \|/);
  assert.match(md, /\| `oops` \| adc_clk \| clk \| not synchronised \|/);
  assert.match(md, /wr_clk → adc_clk, rd_clk → clk/);
  assert.match(md, /## Reset domains/);
  assert.doesNotMatch(md, /__none__/);
});

test('warnings are listed', () => {
  assert.match(renderMarkdown(empty({ warnings: ['ports: boom'] })), /## Warnings\n\n- ports: boom/);
});

for (const name of ['sample_capture', 'sample_ctrl', 'top']) {
  test(`the real document for ${name} becomes Markdown with every port and process`, () => {
    const doc = fixture(name);
    const md = renderMarkdown(doc);
    assert.match(md, new RegExp(`^# ${name}\\n`));
    for (const p of doc.ports) assert.ok(md.includes(`\`${p.name}\``), p.name);
    for (const proc of doc.processes) assert.ok(md.includes(proc.label), proc.label);
    assert.doesNotMatch(md, /undefined|\[object|\bnull\b/);
    assert.ok(md.endsWith('\n') && !md.endsWith('\n\n'));
  });
}
