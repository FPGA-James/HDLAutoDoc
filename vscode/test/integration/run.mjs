// Runs test/integration/suite.cjs inside the installed VS Code, with a throw-away profile and
// extensions folder so the developer's own settings and extensions are never touched.
// A window opens briefly.  Set VSCODE_EXECUTABLE to use a different VS Code.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { runTests } from '@vscode/test-electron';

const root = fileURLToPath(new URL('../..', import.meta.url));
const executable = [process.env.VSCODE_EXECUTABLE,
  '/Applications/Visual Studio Code.app/Contents/MacOS/Code',
  '/usr/share/code/code', '/usr/bin/code'].find((p) => p && existsSync(p));

if (!executable) {
  console.log('No VS Code found (set VSCODE_EXECUTABLE); integration tests skipped.');
  process.exit(0);
}

// A shell started from inside VS Code can carry this; it would make VS Code run as plain Node.
delete process.env.ELECTRON_RUN_AS_NODE;

execFileSync('npm', ['run', 'build'], { cwd: root, stdio: 'inherit' });
const scratch = mkdtempSync(join(tmpdir(), 'hdl-autodoc-vscode-'));
const workspace = join(root, '..', 'example_full');

try {
  await runTests({
    vscodeExecutablePath: executable,
    extensionDevelopmentPath: root,
    extensionTestsPath: join(root, 'test/integration/suite.cjs'),
    launchArgs: [workspace, '--user-data-dir', join(scratch, 'user'), '--extensions-dir', join(scratch, 'ext'),
      '--disable-extensions', '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes', '--disable-gpu'],
  });
} catch (error) {
  console.error('Integration tests failed:', error);
  process.exit(1);
}
