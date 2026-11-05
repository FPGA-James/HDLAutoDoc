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

async function drawWaveforms(): Promise<void> {
  const elements = [...content.querySelectorAll<HTMLElement>('.wavedrom')];
  if (elements.length === 0) return;
  await loadScript('wavedrom/default.js');
  await loadScript('wavedrom/wavedrom.min.js');
  elements.forEach((element, n) => {
    try {
      const source = JSON.parse(element.dataset.source ?? '') as object;
      element.id = `hdlwave${n}_0`;
      WaveDrom.RenderWaveForm(0, source, `hdlwave${n}_`);
      scopeStyles(element);
    } catch (error) {
      showError(element, 'WaveDrom', error);
    }
  });
}

async function drawDiagrams(): Promise<void> {
  const nodes = [...content.querySelectorAll('.mermaid')];
  if (nodes.length === 0) return;
  await loadScript('mermaid.min.js');
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: isDark() ? 'dark' : 'default' });
  try {
    await mermaid.run({ nodes, suppressErrors: true });
  } catch (error) {
    nodes.forEach((node) => showError(node, 'Mermaid', error));
  }
}

async function drawStateMachines(): Promise<void> {
  const elements = [...content.querySelectorAll<HTMLElement>('.fsm')];
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
  for (const draw of [drawWaveforms, drawDiagrams, drawStateMachines]) {
    if (mine !== generation) return;                  // a newer render replaced this one
    try {
      await draw();
    } catch (error) {
      showError(content.firstElementChild ?? content, 'Diagram', error);
    }
  }
  if (mine === generation) window.scrollTo(0, scroll);
}

window.addEventListener('message', (event: MessageEvent) => {
  const message = event.data as { type?: string; html?: string } | undefined;
  if (message?.type === 'render' && typeof message.html === 'string') void show(message.html);
});

content.addEventListener('click', (event) => {
  const target = (event.target as Element).closest('[data-line]');
  if (target) host?.postMessage({ type: 'goto', line: Number(target.getAttribute('data-line')) });
});

// VS Code changes the body class when the theme changes: draw the diagrams again with its colours.
new MutationObserver(() => { if (latestHtml) void show(latestHtml); })
  .observe(document.body, { attributes: true, attributeFilter: ['class'] });

host?.postMessage({ type: 'ready' });
