// The document as Markdown.  Diagrams are inserted as their source in fenced code blocks
// (mermaid, wavedrom, dot): renderers that understand them (GitHub, many editors) draw them,
// and the source stays readable and diff-able where they do not.
import type { CdcAnalysis, Document, Fsm, Generic, Instance, MermaidDiagram, Port, ProcessInfo, ResetAnalysis } from './types.ts';

const NONE = '__none__';
const label = (reset: string | null): string => (reset === null || reset === NONE ? 'none' : reset);
const cell = (text: string): string => text.replace(/\|/g, '\\|').replace(/\s*\n\s*/g, ' ').trim();
const code = (text: string): string => (text === '' ? '' : `\`${cell(text)}\``);

function table(headers: string[], rows: string[][]): string {
  if (rows.length === 0) return '';
  const line = (cells: string[]) => `| ${cells.join(' | ')} |`;
  return [line(headers), line(headers.map(() => '---')), ...rows.map(line)].join('\n');
}

/** A code fence longer than any run of backticks in the code, so the code cannot close it. */
function fenced(language: string, source: string): string {
  const longest = Math.max(0, ...(source.match(/`+/g) ?? []).map((run) => run.length));
  const fence = '`'.repeat(Math.max(3, longest + 1));
  return `${fence}${language}\n${source}\n${fence}`;
}

function diagrams(wavedrom: string[], mermaid: MermaidDiagram[]): string[] {
  return [
    ...wavedrom.map((w) => fenced('wavedrom', w)),
    ...mermaid.map((d) => (d.caption ? `*${d.caption}*\n\n` : '') + fenced('mermaid', d.source)),
  ];
}

const section = (title: string, parts: string[], level = 2): string[] => {
  const body = parts.filter((p) => p !== '');
  return body.length === 0 ? [] : [`${'#'.repeat(level)} ${title}`, ...body];
};

function ports(list: Port[]): string[] {
  const headers = ['Name', 'Direction', 'Type', 'Description'];
  const row = (p: Port) => [code(p.name), cell(p.direction),
    cell(p.kind === 'interface' ? `${p.interface ?? p.type}${p.modport ? `.${p.modport}` : ''}` : p.type + (p.range ? `(${p.range})` : '')),
    cell(p.description)];
  const groups = new Map<string, Port[]>();
  for (const p of list) if (p.group !== null) groups.set(p.group, [...(groups.get(p.group) ?? []), p]);
  return [
    table(headers, list.filter((p) => p.group === null).map(row)),
    ...[...groups].flatMap(([name, members]) => [`### ${name}`, table(headers, members.map(row))]),
  ];
}

const generics = (list: Generic[]): string[] =>
  [table(['Name', 'Type', 'Default', 'Description'], list.map((g) => [code(g.name), cell(g.type), code(g.default), cell(g.description)]))];

const instances = (list: Instance[]): string[] =>
  [table(['Instance', 'Of', 'Kind'], list.map((i) => [code(i.instance), code(i.component), cell(i.kind)]))];

const fsm = (f: Fsm): string[] => [
  fenced('dot', f.dot),
  table(['From', 'To', 'When'], f.transitions.map((t) => [cell(t.from), cell(t.to), t.condition ? code(t.condition) : 'always'])),
];

const processes = (list: ProcessInfo[]): string[] => list.flatMap((p) => [
  `### ${p.label} (${p.kind})`,
  p.sensitivity.length > 0 ? `Sensitivity: ${code(p.sensitivity.join(', '))}` : '',
  p.description.trim(),
  ...diagrams(p.wavedrom, p.mermaid),
]);

function cdc(c: CdcAnalysis): string[] {
  const crossings = table(['Signal', 'From', 'To', 'Synchroniser'], c.crossings.map((x) =>
    [code(x.signal), cell(x.src_clock), cell(x.dst_clock), x.synchronized ? 'two-flop' : 'not synchronised']));
  const dual = table(['Instance', 'Of', 'Clock connections'], c.dual_clock_instances.map((d) =>
    [code(d.instance), code(d.component), cell(Object.entries(d.clocks).map(([port, sig]) => `${port} → ${sig}`).join(', '))]));
  return [
    table(['Clock', 'Processes'], Object.entries(c.domains).map(([clk, procs]) => [code(clk), cell(procs.join(', '))])),
    ...(crossings ? ['### Crossings', crossings] : []),
    ...(dual ? ['### Dual-clock instances', dual] : []),
  ];
}

function reset(r: ResetAnalysis): string[] {
  const crossings = table(['Signal', 'From reset', 'To reset'], r.crossings.map((x) =>
    [code(x.signal), cell(label(x.src_reset)), cell(label(x.dst_reset))]));
  return [
    table(['Process', 'Clock', 'Reset', 'Style'], r.processes.map((p) =>
      [code(p.label), cell(p.clock), cell(label(p.reset)), p.style === 'none' ? '—' : cell(p.style)])),
    ...(crossings ? ['### Crossings', crossings] : []),
  ];
}

export function renderMarkdown(doc: Document): string {
  const blocks = [
    ...(doc.module === null ? [] : [`# ${doc.module.name}`, doc.module.description.trim(), ...diagrams(doc.module.wavedrom, doc.module.mermaid)]),
    ...section(doc.language === 'vhdl' ? 'Generics' : 'Parameters', generics(doc.generics)),
    ...section('Ports', ports(doc.ports)),
    ...section('Instances', instances(doc.instances)),
    ...section('State machine', doc.fsm === null ? [] : fsm(doc.fsm)),
    ...section('Processes', processes(doc.processes)),
    ...section('Clock domains', doc.cdc === null ? [] : cdc(doc.cdc)),
    ...section('Reset domains', doc.reset === null ? [] : reset(doc.reset)),
    ...section('Warnings', doc.warnings.length === 0 ? [] : [doc.warnings.map((w) => `- ${w}`).join('\n')]),
  ].filter((b) => b !== '');
  return `${blocks.join('\n\n')}\n`;
}
