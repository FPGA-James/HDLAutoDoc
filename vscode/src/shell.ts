// The panel's HTML page.  Shared by the extension and the browser tests, so the tests run
// under the same content-security policy.
export interface ShellOptions {
  nonce: string;
  cspSource: string;
  panelCss: string;
  webviewJs: string;
  vendorBase: string;
}

export function shellHtml(o: ShellOptions): string {
  const csp = [
    "default-src 'none'",
    'img-src data:',
    `style-src ${o.cspSource} 'unsafe-inline'`,
    `script-src 'nonce-${o.nonce}' 'wasm-unsafe-eval'`,
    `font-src ${o.cspSource}`,
  ].join('; ');
  return `<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${o.panelCss}">
</head><body data-assets="${o.vendorBase}/">
<div id="toolbar"><button data-export="html" title="Save this documentation as a standalone HTML file">Export HTML</button><button data-export="markdown" title="Save this documentation as Markdown, with the diagrams as fenced source">Export Markdown</button></div>
<div id="content"></div>
<script nonce="${o.nonce}" src="${o.webviewJs}"></script>
</body></html>`;
}
