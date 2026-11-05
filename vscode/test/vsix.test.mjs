// `make vsix` produces a self-contained extension: the built bundles and a copy of the
// Python scripts, and nothing that is only needed to build or test it.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = fileURLToPath(new URL('..', import.meta.url));

function build() {
  execFileSync('make', ['-C', dir, 'vsix'], { stdio: 'pipe' });
  const name = readdirSync(dir).find((f) => f.endsWith('.vsix'));
  assert.ok(name, 'make vsix produced no .vsix file');
  const listing = execFileSync('unzip', ['-Z1', `${dir}/${name}`], { encoding: 'utf8' });
  return { name, files: listing.split('\n').filter(Boolean) };
}

test('the vsix holds the bundles, the manifest and the Python scripts', () => {
  const { files } = build();
  for (const wanted of [
    'extension/package.json',
    'extension/dist/extension.js',
    'extension/dist/webview.js',
    'extension/python/hdl_autodoc/autodoc_json.py',
    'extension/python/hdl_autodoc/extract_block.py',
    'extension/python/hdl_autodoc/hdl_scan.py',
  ]) {
    assert.ok(files.includes(wanted), `missing ${wanted}`);
  }
});

test('the vsix holds no tests, caches, sources or dependencies', () => {
  const { files } = build();
  const unwanted = files.filter((f) =>
    /\/tests?\/|__pycache__|node_modules|extension\/src\/|\.map$|\.ts$/.test(f));
  assert.deepEqual(unwanted, []);
});

test('the file name carries the package version', () => {
  const { name } = build();
  const pkg = JSON.parse(readFileSync(`${dir}/package.json`, 'utf8'));
  assert.equal(name, `hdl-autodoc-${pkg.version}.vsix`);
});

test('the Python inside the vsix runs on its own, with nothing from the repository', () => {
  const { name } = build();
  const tmp = mkdtempSync(join(tmpdir(), 'vsix-'));
  execFileSync('unzip', ['-q', `${dir}/${name}`, '-d', tmp]);
  const script = join(tmp, 'extension/python/hdl_autodoc/autodoc_json.py');
  const out = execFileSync('python3', [script, '--language', 'vhdl'], {
    input: '-- Adder.\nentity add is port (a : in std_logic);\nend entity add;\n',
    cwd: tmp,
    env: { PATH: process.env.PATH },
    encoding: 'utf8',
  });
  const doc = JSON.parse(out);
  assert.equal(doc.module.name, 'add');
  assert.equal(doc.ports[0].name, 'a');
  assert.deepEqual(doc.warnings, []);
});
