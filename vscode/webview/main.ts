// Webview client: shows the HTML the extension host sends, then draws the diagrams in it.
// WaveDrom, Mermaid and viz-js are separate scripts loaded on first use from `data-assets`
// (they are large, and most files have no diagrams).  Nothing is fetched from a network.

interface HostApi { postMessage(message: unknown): void }
declare const acquireVsCodeApi: undefined | (() => HostApi);
declare const WaveDrom: { RenderWaveForm(index: number, source: unknown, idPrefix: string): void };
declare const mermaid: {
  initialize(config: object): void;
  run(options: { nodes: Element[]; suppressErrors?: boolean }): Promise<void>;
};
declare const Viz: { instance(): Promise<{ renderSVGElement(dot: string): SVGSVGElement }> };

const host: HostApi | null = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null;
const nonce = (document.currentScript as HTMLScriptElement | null)?.nonce ?? '';
const content = document.getElementById('content') as HTMLElement;
const assets = document.body.dataset.assets ?? 'vendor/';

const loaded = new Map<string, Promise<void>>();

function loadScript(file: string): Promise<void> {
  let pending = loaded.get(file);
  if (!pending) {
    pending = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.nonce = nonce;
      script.src = assets + file;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`could not load ${file}`));
      document.head.appendChild(script);
    });
    loaded.set(file, pending);
  }
  return pending;
}

const isDark = (): boolean =>
  document.body.classList.contains('vscode-dark') || document.body.classList.contains('vscode-high-contrast');

function showError(element: Element, what: string, error: unknown): void {
  const pre = document.createElement('pre');
  pre.className = 'diagram-error';
  pre.textContent = `${what}: ${error instanceof Error ? error.message : String(error)}`;
  element.replaceChildren(pre);
}

/**
 * WaveDrom writes a <style> element into each SVG, and an inline <style> applies to the whole
 * document: its bare `text { fill: ... }` rule would restyle every other diagram on the page.
 * Prefix the element selectors with the waveform's own class.  Its class selectors (`.s1`, ...)
 * stay as they are: they style shapes that are instantiated with <use>, where a descendant
 * selector such as `.wavedrom .s1` does not match.
 */
function scopeStyles(element: Element): void {
  element.querySelectorAll('style').forEach((style) => {
    style.textContent = (style.textContent ?? '').replace(
      /(^|\})\s*([^{}]+)\{/g,
      (_all, close: string, selectors: string) =>
        `${close}${selectors.split(',').map((sel) => /^\s*[a-zA-Z*]/.test(sel) ? `.wavedrom ${sel.trim()}` : sel.trim()).join(',')}{`);
  });
}

async function drawWaveforms(root: HTMLElement, prefix: string): Promise<void> {
  const elements = [...root.querySelectorAll<HTMLElement>('.wavedrom')];
  if (elements.length === 0) return;
  await loadScript('wavedrom/default.js');
  await loadScript('wavedrom/wavedrom.min.js');
  elements.forEach((element, n) => {
    try {
      const source = JSON.parse(element.dataset.source ?? '') as object;
      element.id = `${prefix}${n}_0`;
      WaveDrom.RenderWaveForm(0, source, `${prefix}${n}_`);
      scopeStyles(element);
    } catch (error) {
      showError(element, 'WaveDrom', error);
    }
  });
}

async function drawDiagrams(root: HTMLElement, dark: boolean): Promise<void> {
  const nodes = [...root.querySelectorAll('.mermaid')];
  if (nodes.length === 0) return;
  await loadScript('mermaid.min.js');
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: dark ? 'dark' : 'default' });
  try {
    await mermaid.run({ nodes, suppressErrors: true });
  } catch (error) {
    nodes.forEach((node) => showError(node, 'Mermaid', error));
  }
}

async function drawStateMachines(root: HTMLElement): Promise<void> {
  const elements = [...root.querySelectorAll<HTMLElement>('.fsm')];
  if (elements.length === 0) return;
  await loadScript('viz-global.js');
  const viz = await Viz.instance();
  for (const element of elements) {
    try {
      element.replaceChildren(viz.renderSVGElement(element.dataset.dot ?? ''));
    } catch (error) {
      showError(element, 'Graphviz', error);
    }
  }
}

let latestHtml = '';
let generation = 0;

async function show(html: string): Promise<void> {
  const mine = ++generation;
  const scroll = window.scrollY;
  latestHtml = html;
  content.innerHTML = html;
  window.scrollTo(0, scroll);
  const draws = [() => drawWaveforms(content, 'hdlwave'), () => drawDiagrams(content, isDark()), () => drawStateMachines(content)];
  for (const draw of draws) {
    if (mine !== generation) return;                  // a newer render replaced this one
    try {
      await draw();
    } catch (error) {
      showError(content.firstElementChild ?? content, 'Diagram', error);
    }
  }
  if (mine === generation) window.scrollTo(0, scroll);
}

/**
 * The document as it would look on a light page: drawn again off-screen with the light theme,
 * whatever theme the panel is in (a dark Mermaid theme or an inverted waveform would be unreadable
 * on the white page the export gives).  Off-screen but attached, because the diagram libraries measure the DOM.
 */
async function lightHtml(): Promise<string> {
  const copy = document.createElement('div');
  copy.className = 'export-root';
  copy.style.cssText = 'position:absolute;left:-10000px;top:0;width:1000px';
  copy.innerHTML = latestHtml;
  document.body.appendChild(copy);
  try {
    for (const draw of [() => drawWaveforms(copy, 'hdlexp'), () => drawDiagrams(copy, false), () => drawStateMachines(copy)]) {
      try { await draw(); } catch (error) { showError(copy, 'Diagram', error); }
    }
    return copy.innerHTML;
  } finally {
    copy.remove();
  }
}

async function requestExport(format: string): Promise<void> {
  if (!latestHtml) return;                              // nothing to export yet
  // Only HTML is the drawn page; Markdown is built from the document by the host.
  host?.postMessage(format === 'html' ? { type: 'export', format, html: await lightHtml() } : { type: 'export', format });
}

window.addEventListener('message', (event: MessageEvent) => {
  const message = event.data as { type?: string; html?: string; format?: string } | undefined;
  if (message?.type === 'render' && typeof message.html === 'string') void show(message.html);
  if (message?.type === 'requestExport' && typeof message.format === 'string') void requestExport(message.format);
});

document.querySelectorAll<HTMLElement>('[data-export]').forEach((button) =>
  button.addEventListener('click', () => void requestExport(button.dataset.export ?? 'html')));

content.addEventListener('click', (event) => {
  const target = (event.target as Element).closest('[data-line]');
  if (target) host?.postMessage({ type: 'goto', line: Number(target.getAttribute('data-line')) });
});

// VS Code changes the body class when the theme changes: draw the diagrams again with its colours.
new MutationObserver(() => { if (latestHtml) void show(latestHtml); })
  .observe(document.body, { attributes: true, attributeFilter: ['class'] });

host?.postMessage({ type: 'ready' });
