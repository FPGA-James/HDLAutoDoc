// The extension is released together with the tool: its version is the newest in RELEASE.md.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);

test('package.json version equals the newest version in RELEASE.md', () => {
  const release = readFileSync(new URL('RELEASE.md', root), 'utf8');
  const newest = /^## v(\d+\.\d+\.\d+)/m.exec(release)[1];
  const pkg = JSON.parse(readFileSync(new URL('vscode/package.json', root), 'utf8'));
  assert.equal(pkg.version, newest);
});
