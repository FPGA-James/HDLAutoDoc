// The logic behind the live panel, free of any `vscode` import so it can be unit-tested:
// debounce edits, run the extractor for the newest text only, drop results that arrive late,
// and decide what the panel shows (a document, an error, or a note about the active file).
import { renderDocument, renderMessage } from './render.ts';
import type { RunResult } from './runner.ts';
import type { Language } from './types.ts';

export interface Snapshot {
  uri: string;
  languageId: string;
  text: string;
}

export interface RunRequest extends Snapshot {
  language: Language;
}

export interface SessionDeps {
  run(request: RunRequest, signal: AbortSignal): Promise<RunResult>;
  post(message: { type: 'render'; html: string }): void;
  /** Pause after the last edit; read on every update so a settings change applies at once. */
  delayMs(): number;
  setTimer?(callback: () => void, ms: number): unknown;
  clearTimer?(handle: unknown): void;
}

/** The extractor's language for a VS Code language id, or null if the file is not HDL. */
export function languageFor(languageId: string): Language | null {
  if (languageId === 'vhdl') return 'vhdl';
  if (languageId === 'systemverilog' || languageId === 'verilog') return 'systemverilog';
  return null;
}

/**
 * The extractor's language for a file.  The language id decides; the file extension is only a
 * fallback for "plaintext", which is what VS Code calls a .vhd or .sv file when no VHDL or
 * SystemVerilog extension is installed.
 */
export function languageOf(snapshot: Snapshot): Language | null {
  const byId = languageFor(snapshot.languageId);
  if (byId !== null || snapshot.languageId !== 'plaintext') return byId;
  const extension = /\.([A-Za-z]+)$/.exec(snapshot.uri)?.[1].toLowerCase();
  if (extension === 'vhd' || extension === 'vhdl') return 'vhdl';
  if (extension === 'sv' || extension === 'svh' || extension === 'v' || extension === 'vh') return 'systemverilog';
  return null;
}

function fileName(uri: string): string {
  const last = uri.split('/').pop() ?? uri;
  try { return decodeURIComponent(last); } catch { return last; }
}

export class Session {
  private readonly deps: SessionDeps;
  private timer: unknown = null;
  private controller: AbortController | null = null;
  private sequence = 0;
  private lastHtml = '';
  private disposed = false;

  constructor(deps: SessionDeps) {
    this.deps = deps;
  }

  /** The text of the followed file changed: refresh after a pause. */
  update(snapshot: Snapshot): void {
    if (this.disposed) return;
    if (languageOf(snapshot) === null) { this.showNotHdl(snapshot); return; }
    this.cancelTimer();
    const set = this.deps.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.timer = set(() => { this.timer = null; this.start(snapshot); }, this.deps.delayMs());
  }

  /** Refresh now (a save, a new active file, the panel opening). */
  flush(snapshot: Snapshot): void {
    if (this.disposed) return;
    if (languageOf(snapshot) === null) { this.showNotHdl(snapshot); return; }
    this.cancelTimer();
    this.start(snapshot);
  }

  dispose(): void {
    this.disposed = true;
    this.cancelTimer();
    this.controller?.abort();
  }

  private cancelTimer(): void {
    if (this.timer === null) return;
    (this.deps.clearTimer ?? ((h) => clearTimeout(h as ReturnType<typeof setTimeout>)))(this.timer);
    this.timer = null;
  }

  private start(snapshot: Snapshot): void {
    this.controller?.abort();                                  // the older run is out of date
    const controller = new AbortController();
    this.controller = controller;
    const mine = ++this.sequence;
    const language = languageOf(snapshot) as Language;

    this.deps.run({ ...snapshot, language }, controller.signal).then(
      (result) => { if (!this.disposed && mine === this.sequence) this.finish(result); },
      (error: unknown) => {
        if (!this.disposed && mine === this.sequence) {
          this.finish({ ok: false, kind: 'failed', message: error instanceof Error ? error.message : String(error) });
        }
      },
    );
  }

  private finish(result: RunResult): void {
    if (result.ok) {
      this.lastHtml = renderDocument(result.doc);
      this.deps.post({ type: 'render', html: this.lastHtml });
    } else if (result.kind !== 'aborted') {
      this.deps.post({ type: 'render', html: renderMessage('error', result.message) + this.lastHtml });
    }
  }

  private showNotHdl(snapshot: Snapshot): void {
    const note = renderMessage('info', `${fileName(snapshot.uri)} is not a VHDL or SystemVerilog file.`);
    this.deps.post({ type: 'render', html: note + this.lastHtml });
  }
}
