// A saved copy of the panel: the document HTML (diagrams already drawn as SVG) in a standalone page.
import { esc } from './render.ts';

// The panel's stylesheet reads VS Code theme variables; a saved file has none, so give it a light palette.
const LIGHT = `:root{--vscode-foreground:#222;--vscode-editor-background:#fff;--vscode-panel-border:#ccc;` +
  `--vscode-descriptionForeground:#666;--vscode-textCodeBlock-background:#eee;--vscode-editorWidget-background:#f3f3f3;` +
  `--vscode-list-hoverBackground:#e8e8e8;--vscode-focusBorder:#07c;--vscode-errorForeground:#c00;` +
  `--vscode-testing-iconPassed:#080;--vscode-editorWarning-foreground:#a60;--vscode-font-family:system-ui,sans-serif;` +
  `--vscode-font-size:14px;--vscode-editor-font-family:ui-monospace,Menlo,Consolas,monospace;--vscode-editor-font-size:13px}` +
  `body{max-width:1000px;margin:0 auto}tr[data-line],h1[data-line],.process[data-line]{cursor:auto}` +
  // For paper (and the PDF): A4, shaded tables and node colours kept, tables, rows, diagrams and process
  // blocks kept whole where they fit, headings kept with what follows, wide diagrams scaled to the page.
  `@page{size:A4;margin:15mm}*{print-color-adjust:exact;-webkit-print-color-adjust:exact}` +
  `table,tr,figure,svg,.process{break-inside:avoid}h1,h2,h3{break-after:avoid}svg{max-width:100%;height:auto}` +
  `@media print{body{max-width:none;margin:0}}`;

export function exportPage(title: string, body: string, css: string): string {
  return `<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>${esc(title)}</title>\n<style>${LIGHT}\n${css}</style>\n</head><body>\n${body}\n</body></html>\n`;
}
