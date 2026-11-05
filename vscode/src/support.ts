// Finds the SystemVerilog files in a workspace that define interfaces, so a module that uses
// `axis_if.slave s_axis` can be documented from its own file alone.  The file system is
// injected, so the logic is testable; results are cached until a file's modification time changes.

export interface SupportDeps {
  list(): Promise<string[]>;
  read(path: string): Promise<string>;
  mtime(path: string): Promise<number>;
}

function definesInterface(text: string): boolean {
  const code = text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
  return /^\s*interface\s+\w+/m.test(code);
}

export class SupportFinder {
  private readonly deps: SupportDeps;
  private readonly cache = new Map<string, { mtime: number; isInterface: boolean }>();

  constructor(deps: SupportDeps) {
    this.deps = deps;
  }

  async find(): Promise<string[]> {
    const paths = await this.deps.list();
    const found: string[] = [];
    const seen = new Set<string>();
    for (const path of paths) {
      try {
        const mtime = await this.deps.mtime(path);
        let entry = this.cache.get(path);
        if (!entry || entry.mtime !== mtime) {
          entry = { mtime, isInterface: definesInterface(await this.deps.read(path)) };
          this.cache.set(path, entry);
        }
        seen.add(path);
        if (entry.isInterface) found.push(path);
      } catch {
        this.cache.delete(path);                              // gone or unreadable: leave it out
      }
    }
    for (const path of [...this.cache.keys()]) if (!seen.has(path)) this.cache.delete(path);
    return found;
  }
}
