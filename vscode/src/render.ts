// Turns the autodoc_json document into the panel's HTML.  Pure string building, so it can be
// tested without a browser; the webview client turns the placeholders into diagrams.
import type { CdcAnalysis, Document, Fsm, Generic, Instance, MermaidDiagram, Port, ProcessInfo, ResetAnalysis } from './types.ts';

export function esc(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const NONE = '__none__';
const label = (reset: string | null): string => (reset === null || reset === NONE ? 'none' : reset);

/** Description text: blank-line separated paragraphs, ``code`` spans; everything escaped. */
function prose(text: string): string {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
    .map((p) => `<p>${esc(p).replace(/``([^`]+)``/g, '<code>$1</code>')}</p>`)
    .join('\n');
}

function table(headers: string[], rows: string[]): string {
  if (rows.length === 0) return '';
  return `<table>\n<thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead>\n<tbody>\n${rows.join('\n')}\n</tbody>\n</table>`;
}

const section = (title: string, body: string): string =>
  body.trim() === '' ? '' : `<section>\n<h2>${esc(title)}</h2>\n${body}\n</section>`;

function diagrams(wavedrom: string[], mermaid: MermaidDiagram[]): string {
  const waves = wavedrom.map((w) => `<div class="wavedrom" data-source="${esc(w)}"></div>`);
  const flows = mermaid.map((d) =>
    `<figure><pre class="mermaid">${esc(d.source)}</pre>${d.caption ? `<figcaption>${esc(d.caption)}</figcaption>` : ''}</figure>`);
  return [...waves, ...flows].join('\n');
}

function portRow(p: Port): string {
  const type = p.kind === 'interface'
    ? `${p.interface ?? p.type}${p.modport ? `.${p.modport}` : ''}`
    : p.type + (p.range ? `(${p.range})` : '');
  return `<tr data-line="${p.line}"><td><code>${esc(p.name)}</code></td><td>${esc(p.direction)}</td>` +
         `<td>${esc(type)}</td><td>${esc(p.description)}</td></tr>`;
}

function ports(list: Port[]): string {
  const headers = ['Name', 'Direction', 'Type', 'Description'];
  const plain = list.filter((p) => p.group === null);
  const groups = new Map<string, Port[]>();
  for (const p of list) {
    if (p.group !== null) groups.set(p.group, [...(groups.get(p.group) ?? []), p]);
  }
  const parts = [table(headers, plain.map(portRow))];
  for (const [name, members] of groups) {
    parts.push(`<h3>${esc(name)}</h3>\n${table(headers, members.map(portRow))}`);
  }
  return parts.filter((p) => p !== '').join('\n');
}

function generics(list: Generic[]): string {
  return table(['Name', 'Type', 'Default', 'Description'], list.map((g) =>
    `<tr data-line="${g.line}"><td><code>${esc(g.name)}</code></td><td>${esc(g.type)}</td>` +
    `<td><code>${esc(g.default)}</code></td><td>${esc(g.description)}</td></tr>`));
}

function instances(list: Instance[]): string {
  return table(['Instance', 'Of', 'Kind'], list.map((i) =>
    `<tr data-line="${i.line}"><td><code>${esc(i.instance)}</code></td><td><code>${esc(i.component)}</code></td><td>${esc(i.kind)}</td></tr>`));
}

function fsm(f: Fsm): string {
  const rows = f.transitions.map((t) =>
    `<tr><td>${esc(t.from)}</td><td>${esc(t.to)}</td><td>${t.condition ? `<code>${esc(t.condition)}</code>` : 'always'}</td></tr>`);
  return `<div class="fsm" data-dot="${esc(f.dot)}"></div>\n${table(['From', 'To', 'When'], rows)}`;
}

function processes(list: ProcessInfo[]): string {
  return list.map((p) => [
    `<article class="process" data-line="${p.line}">`,
    `<h3>${esc(p.label)} <small>${esc(p.kind)}</small></h3>`,
    p.sensitivity.length > 0 ? `<p class="meta">Sensitivity: <code>${esc(p.sensitivity.join(', '))}</code></p>` : '',
    prose(p.description),
    diagrams(p.wavedrom, p.mermaid),
    '</article>',
  ].filter((s) => s !== '').join('\n')).join('\n');
}

function cdc(c: CdcAnalysis): string {
  const domains = table(['Clock', 'Processes'], Object.entries(c.domains).map(([clk, procs]) =>
    `<tr><td><code>${esc(clk)}</code></td><td>${esc(procs.join(', '))}</td></tr>`));
  const crossings = table(['Signal', 'From', 'To', 'Synchroniser'], c.crossings.map((x) =>
    `<tr><td><code>${esc(x.signal)}</code></td><td>${esc(x.src_clock)}</td><td>${esc(x.dst_clock)}</td>` +
    `<td class="${x.synchronized ? 'ok' : 'bad'}">${x.synchronized ? 'two-flop' : 'not synchronised'}</td></tr>`));
  const dual = table(['Instance', 'Of', 'Clock connections'], c.dual_clock_instances.map((d) =>
    `<tr><td><code>${esc(d.instance)}</code></td><td><code>${esc(d.component)}</code></td>` +
    `<td>${esc(Object.entries(d.clocks).map(([port, sig]) => `${port} → ${sig}`).join(', '))}</td></tr>`));
  return [domains, crossings === '' ? '' : `<h3>Crossings</h3>\n${crossings}`,
          dual === '' ? '' : `<h3>Dual-clock instances</h3>\n${dual}`].filter((s) => s !== '').join('\n');
}

function reset(r: ResetAnalysis): string {
  const procs = table(['Process', 'Clock', 'Reset', 'Style'], r.processes.map((p) =>
    `<tr><td><code>${esc(p.label)}</code></td><td>${esc(p.clock)}</td><td>${esc(label(p.reset))}</td><td>${esc(p.style === 'none' ? '—' : p.style)}</td></tr>`));
  const crossings = table(['Signal', 'From reset', 'To reset'], r.crossings.map((x) =>
    `<tr><td><code>${esc(x.signal)}</code></td><td>${esc(label(x.src_reset))}</td><td>${esc(label(x.dst_reset))}</td></tr>`));
  return [procs, crossings === '' ? '' : `<h3>Crossings</h3>\n${crossings}`].filter((s) => s !== '').join('\n');
}

export function renderDocument(doc: Document): string {
  const header = doc.module === null ? '' : [
    `<header class="module">`,
    `<h1 data-line="${doc.module.line}">${esc(doc.module.name)}<small class="lang">${esc(doc.language)}</small></h1>`,
    prose(doc.module.description),
    diagrams(doc.module.wavedrom, doc.module.mermaid),
    `</header>`,
  ].filter((s) => s !== '').join('\n');

  return [
    header,
    section(doc.language === 'vhdl' ? 'Generics' : 'Parameters', generics(doc.generics)),
    section('Ports', ports(doc.ports)),
    section('Instances', instances(doc.instances)),
    section('State machine', doc.fsm === null ? '' : fsm(doc.fsm)),
    section('Processes', processes(doc.processes)),
    section('Clock domains', doc.cdc === null ? '' : cdc(doc.cdc)),
    section('Reset domains', doc.reset === null ? '' : reset(doc.reset)),
    section('Warnings', doc.warnings.length === 0 ? '' : `<ul class="warnings">${doc.warnings.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>`),
  ].filter((s) => s !== '').join('\n');
}

export type MessageKind = 'info' | 'error';

export function renderMessage(kind: MessageKind, text: string): string {
  return `<div class="message message-${kind}">${esc(text)}</div>`;
}
