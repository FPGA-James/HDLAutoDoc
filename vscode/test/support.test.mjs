import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SupportFinder } from '../src/support.ts';

function fakeFs(files) {
  const reads = [];
  return {
    reads,
    files,
    deps: {
      list: async () => Object.keys(files),
      read: async (path) => { reads.push(path); return files[path].text; },
      mtime: async (path) => files[path].mtime,
    },
  };
}

test('files that define an interface are returned, others are not', async () => {
  const fs = fakeFs({
    '/w/axis_if.sv': { text: '// bus\ninterface axis_if;\nendinterface\n', mtime: 1 },
    '/w/top.sv': { text: 'module top;\nendmodule\n', mtime: 1 },
    '/w/pkg.sv': { text: 'package p;\n// interface in a comment\nendpackage\n', mtime: 1 },
  });
  assert.deepEqual(await new SupportFinder(fs.deps).find(), ['/w/axis_if.sv']);
});

test('an interface with parameters or a port list is recognised', async () => {
  const fs = fakeFs({
    '/w/a.sv': { text: 'interface a #(int W = 8) (input logic clk);\nendinterface\n', mtime: 1 },
    '/w/b.sv': { text: '  interface b;\nendinterface\n', mtime: 1 },
  });
  assert.deepEqual((await new SupportFinder(fs.deps).find()).sort(), ['/w/a.sv', '/w/b.sv']);
});

test('a file is read again only when its modification time changes', async () => {
  const fs = fakeFs({ '/w/a.sv': { text: 'module a;\nendmodule\n', mtime: 1 } });
  const finder = new SupportFinder(fs.deps);
  await finder.find();
  await finder.find();
  assert.equal(fs.reads.length, 1);
  fs.files['/w/a.sv'] = { text: 'interface a;\nendinterface\n', mtime: 2 };
  assert.deepEqual(await finder.find(), ['/w/a.sv']);
  assert.equal(fs.reads.length, 2);
});

test('files that disappear or cannot be read are left out without failing', async () => {
  const fs = fakeFs({ '/w/ok.sv': { text: 'interface i;\nendinterface\n', mtime: 1 }, '/w/bad.sv': { text: '', mtime: 1 } });
  fs.deps.read = async (path) => { if (path.endsWith('bad.sv')) throw new Error('EACCES'); return fs.files[path].text; };
  assert.deepEqual(await new SupportFinder(fs.deps).find(), ['/w/ok.sv']);
});
