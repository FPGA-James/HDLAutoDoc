"""
parse_testbenches.py
--------------------
Find the testbenches under a testbench directory and extract, from source only,
what each is for and which tests it contains.

Layout (framework = subdirectory name, case-insensitive):

    tb/
    ├── vunit/      VUnit testbenches (VHDL / SystemVerilog)
    ├── cocotb/     cocotb tests (Python)
    ├── pyuvm/      pyuvm tests (Python, UVM on top of cocotb)
    └── directed/   plain HDL testbenches

What counts as a test:

    VUnit (VHDL)    each  run("name")
    VUnit (SV)      each  `TEST_CASE("name")
    cocotb          each  @cocotb.test(...) function; purpose = first docstring line;
                    skip=True is listed and flagged
    pyuvm           each  class decorated with @pyuvm.test(...); purpose = first line of the
                    class docstring; skip=True is listed and flagged
    directed        each  `-- TEST: name — purpose`  (VHDL)  or  `// TEST: name — purpose`
                    (SV/V) comment; the separator after the name may be —, - or :.
                    A directed file with no markers is one test named after the testbench.

Public API
----------
    discover_testbenches(tb_dir, module_names) -> list[Testbench]

Only the standard library is used.  Problems with a file (unreadable, binary,
not valid Python) are reported on stderr and that file is skipped.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from parse_hierarchy import extract_instantiations_sv, extract_instantiations_vhdl

FRAMEWORKS = ("vunit", "cocotb", "pyuvm", "directed")
# Frameworks whose testbenches are Python files.
_PYTHON_FRAMEWORKS = ("cocotb", "pyuvm")
# Simulator and tool output that may sit under tb/ (VUnit copies sources into
# vunit_out/, for instance); anything in them is a copy, not a testbench.
_OUTPUT_DIRS = {"vunit_out", "sim_build", "__pycache__", "obj_dir", "xsim.dir", "work"}
_HDL_SUFFIXES = {".vhd", ".vhdl", ".sv", ".v"}
_VHDL_SUFFIXES = {".vhd", ".vhdl"}


@dataclass(frozen=True)
class TestCase:
    __test__ = False          # a data class, not a pytest test class
    name: str
    purpose: str = ""
    skipped: bool = False


@dataclass
class Testbench:
    __test__ = False
    name: str
    file: str
    framework: str
    purpose: str
    tests: list[TestCase]
    dut: str | None


def framework_for_dir(dirname: str) -> str:
    """Framework named by a subdirectory (case-insensitive); anything else is directed."""
    d = dirname.lower()
    return d if d in FRAMEWORKS else "directed"


# ─────────────────────────────────────────────────────────────────────────────
# Comment / string aware scanning of HDL source
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class _Comment:
    line: int
    text: str
    block: bool
    full_line: bool       # nothing but whitespace before it on its line


def _scan(text: str, suffix: str) -> tuple[str, list[_Comment]]:
    """
    Split HDL source into (code, comments).  `code` is `text` with every comment
    blanked out (same length, newlines kept) and strings left intact, so a `--` or
    `//` inside a string is never taken for a comment.  Handles VHDL `--`, SV `//`,
    and `/* */` in both.
    """
    vhdl = suffix in _VHDL_SUFFIXES
    marker = "--" if vhdl else "//"
    out: list[str] = []
    comments: list[_Comment] = []
    i, n, line = 0, len(text), 1
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != "\n":
                if text[j] == '"':
                    if vhdl and j + 1 < n and text[j + 1] == '"':     # "" escapes a quote
                        j += 2
                        continue
                    break
                if not vhdl and text[j] == "\\":
                    j += 1
                j += 1
            seg = text[i:j + 1]
            out.append(seg)
            line += seg.count("\n")
            i = j + 1
        elif vhdl and c == "'" and i + 2 < n and text[i + 2] == "'":   # character literal
            out.append(text[i:i + 3])
            i += 3
        elif text.startswith(marker, i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            prefix = text[text.rfind("\n", 0, i) + 1:i]
            comments.append(_Comment(line, text[i + 2:j], False, prefix.strip() == ""))
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            seg = text[i:j]
            comments.append(_Comment(line, seg[2:-2], True, False))
            out.append(re.sub(r"[^\n]", " ", seg))
            line += seg.count("\n")
            i = j
        else:
            if c == "\n":
                line += 1
            out.append(c)
            i += 1
    return "".join(out), comments


def _clean(parts: list[str]) -> str:
    """Join comment lines into one line of prose, dropping banner lines (`-----`)."""
    kept = [p.strip() for p in parts if re.search(r"\w", p)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def _purpose_for(lineno: int, comments: list[_Comment]) -> str:
    """Inline comment on the line, else the full-line comments directly above it."""
    inline = [c for c in comments if not c.block and not c.full_line and c.line == lineno]
    if inline:
        return _clean([inline[0].text])
    above = {c.line: c.text for c in comments if not c.block and c.full_line}
    parts: list[str] = []
    k = lineno - 1
    while k in above:
        parts.insert(0, above[k])
        k -= 1
    return _clean(parts)


def _first_entity(code: str, suffix: str) -> tuple[str, int] | None:
    """(name, line) of the first entity / module declaration, or None."""
    if suffix in _VHDL_SUFFIXES:
        m = re.search(r"\bentity\s+(\w+)\s+is\b", code, re.IGNORECASE)
    else:
        m = re.search(r"\b(?:module|macromodule)\s+(?:automatic\s+|static\s+)?(\w+)", code)
    return (m.group(1), code.count("\n", 0, m.start()) + 1) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# Header purpose
# ─────────────────────────────────────────────────────────────────────────────

def header_purpose(text: str, suffix: str) -> str:
    """
    The testbench's purpose: the comment block directly above its first entity /
    module.  If there is none (the usual shape is a header, then `library`/`use`
    lines, then the entity), the comment block at the very top of the file.
    """
    code, comments = _scan(text, suffix)
    full = {c.line: c.text for c in comments if not c.block and c.full_line}

    found = _first_entity(code, suffix)
    if found:
        parts: list[str] = []
        k = found[1] - 1
        while k in full:
            parts.insert(0, full[k])
            k -= 1
        purpose = _clean(parts)
        if purpose:
            return purpose

    first = next((i + 1 for i, l in enumerate(text.splitlines()) if l.strip()), None)
    parts = []
    k = first
    while k is not None and k in full:
        parts.append(full[k])
        k += 1
    return _clean(parts)


# ─────────────────────────────────────────────────────────────────────────────
# VUnit
# ─────────────────────────────────────────────────────────────────────────────

_VUNIT_VHDL_RE = re.compile(r'\brun\s*\(\s*"([^"\n]+)"\s*\)', re.IGNORECASE)
_VUNIT_SV_RE = re.compile(r'`TEST_CASE\s*\(\s*"([^"\n]+)"\s*\)')


def parse_vunit_hdl(text: str, suffix: str) -> list[TestCase]:
    """VUnit tests: `run("name")` in VHDL, `` `TEST_CASE("name") `` in SystemVerilog."""
    code, comments = _scan(text, suffix)
    regex = _VUNIT_VHDL_RE if suffix in _VHDL_SUFFIXES else _VUNIT_SV_RE
    tests: list[TestCase] = []
    seen: set[str] = set()
    for m in regex.finditer(code):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        lineno = code.count("\n", 0, m.start()) + 1
        tests.append(TestCase(name, _purpose_for(lineno, comments)))
    return tests


# ─────────────────────────────────────────────────────────────────────────────
# Directed
# ─────────────────────────────────────────────────────────────────────────────

_MARKER_RE = re.compile(r"^\s*TEST:\s*(?P<name>\w+)\s*(?:[—–:-]\s*)?(?P<purpose>.*)$")


def parse_directed(text: str, suffix: str) -> list[TestCase]:
    """Tests marked with `-- TEST: name — purpose` / `// TEST: name — purpose`."""
    _, comments = _scan(text, suffix)
    tests: list[TestCase] = []
    for c in comments:
        if c.block:
            continue
        m = _MARKER_RE.match(c.text)
        if m:
            tests.append(TestCase(m.group("name"), m.group("purpose").strip()))
    return tests


# ─────────────────────────────────────────────────────────────────────────────
# cocotb
# ─────────────────────────────────────────────────────────────────────────────

def _cocotb_decorator(dec: ast.expr, bare_test: bool) -> dict | None:
    """{'skip': bool} if `dec` is @cocotb.test / @cocotb.test(...), else None."""
    call = dec if isinstance(dec, ast.Call) else None
    target = call.func if call else dec
    is_test = (isinstance(target, ast.Attribute) and target.attr == "test"
               and isinstance(target.value, ast.Name) and target.value.id == "cocotb") \
        or (bare_test and isinstance(target, ast.Name) and target.id == "test")
    if not is_test:
        return None
    skip = bool(call) and any(
        kw.arg == "skip" and isinstance(kw.value, ast.Constant) and kw.value.value is True
        for kw in call.keywords)
    return {"skip": skip}


def _python_purpose(tree: ast.Module, text: str) -> str:
    """A Python test module's purpose: its docstring's first paragraph, else the leading
    comment block."""
    doc = ast.get_docstring(tree)
    if doc:
        return _clean(doc.split("\n\n")[0].splitlines())
    block: list[str] = []
    for l in text.splitlines():
        if not l.strip() and not block:
            continue
        if l.lstrip().startswith("#") and not l.startswith("#!"):
            block.append(l.lstrip()[1:])
        else:
            break
    return _clean(block)


def parse_cocotb(text: str) -> tuple[str, list[TestCase]]:
    """
    (module purpose, tests) for a cocotb test module.  Uses Python's own parser, so
    a decorator split over lines is one test, and `@cocotb.test` inside a comment or
    docstring is not.  Raises SyntaxError for invalid Python.
    """
    tree = ast.parse(text)
    bare_test = any(isinstance(n, ast.ImportFrom) and n.module == "cocotb"
                    and any(a.name == "test" for a in n.names) for n in tree.body)

    tests: list[TestCase] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            info = _cocotb_decorator(dec, bare_test)
            if info is not None:
                doc = ast.get_docstring(node) or ""
                tests.append(TestCase(node.name, doc.splitlines()[0].strip() if doc else "",
                                      info["skip"]))
                break

    return _python_purpose(tree, text), tests



def _pyuvm_names(tree: ast.Module) -> tuple[set[str], bool]:
    """(names the pyuvm module is imported as, whether `test` is imported from pyuvm)."""
    modules: set[str] = set()
    bare_test = False
    for n in tree.body:
        if isinstance(n, ast.Import):
            modules |= {a.asname or a.name for a in n.names if a.name == "pyuvm"}
        elif isinstance(n, ast.ImportFrom) and n.module == "pyuvm":
            bare_test |= any(a.name == "test" and not a.asname for a in n.names)
    return modules, bare_test


def parse_pyuvm(text: str) -> tuple[str, list[TestCase]]:
    """
    (module purpose, tests) for a pyuvm test module: each class decorated with
    `@pyuvm.test(...)` (or `@test(...)` imported from pyuvm) is a test; its purpose is
    the first line of the class docstring.  Raises SyntaxError for invalid Python.
    """
    tree = ast.parse(text)
    modules, bare_test = _pyuvm_names(tree)

    tests: list[TestCase] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for dec in node.decorator_list:
            call = dec if isinstance(dec, ast.Call) else None
            target = call.func if call else dec
            is_test = (isinstance(target, ast.Attribute) and target.attr == "test"
                       and isinstance(target.value, ast.Name) and target.value.id in modules) \
                or (bare_test and isinstance(target, ast.Name) and target.id == "test")
            if not is_test:
                continue
            skip = bool(call) and any(
                kw.arg == "skip" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in call.keywords)
            doc = ast.get_docstring(node) or ""
            tests.append(TestCase(node.name, doc.splitlines()[0].strip() if doc else "", skip))
            break
    return _python_purpose(tree, text), tests


# ─────────────────────────────────────────────────────────────────────────────
# Linking a testbench to the module it tests
# ─────────────────────────────────────────────────────────────────────────────

def link_dut(tb_name: str, text: str, suffix: str, module_names: set[str]) -> str | None:
    """
    The module a testbench exercises, or None.  Rule 1: the name, after stripping a
    `tb_` / `test_` prefix or `_tb` / `_test` suffix, matches a module.  Rule 2
    (HDL only): the first module (alphabetically) the file instantiates.
    """
    by_lower = {m.lower(): m for m in module_names}
    n = tb_name.lower()
    candidates = [n]
    for prefix in ("tb_", "test_"):
        if n.startswith(prefix):
            candidates.append(n[len(prefix):])
    for suffix_ in ("_tb", "_test"):
        if n.endswith(suffix_):
            candidates.append(n[:-len(suffix_)])
    for cand in candidates:
        if cand in by_lower:
            return by_lower[cand]

    if suffix in _HDL_SUFFIXES and by_lower:
        code, _ = _scan(text, suffix)
        known = set(by_lower)
        found = (extract_instantiations_vhdl(code, known) if suffix in _VHDL_SUFFIXES
                 else extract_instantiations_sv(code, known))
        found = [f for f in found if f in by_lower]
        if found:
            return by_lower[sorted(found)[0]]
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────

def _warn(path: Path, message: str) -> None:
    print(f"  WARNING: testbench {path}: {message}", file=sys.stderr)


def _read(path: Path) -> str | None:
    """File text, or None (with a warning where useful) if it should be skipped."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        _warn(path, f"cannot read ({exc.strerror or exc}) — skipped")
        return None
    if not data.strip():
        return None
    if b"\x00" in data:
        _warn(path, "binary file — skipped")
        return None
    try:
        return data.decode("utf-8-sig")             # also drops a byte-order mark
    except UnicodeDecodeError:
        _warn(path, "not valid UTF-8 — decoded with replacement characters")
        return data.decode("utf-8-sig", errors="replace")


def discover_testbenches(tb_dir: Path, module_names: set[str]) -> list[Testbench]:
    """
    Every testbench under `tb_dir`, sorted by framework (vunit, cocotb, pyuvm, directed)
    then name.  A missing or empty directory gives [].  Files that are not
    testbenches (packages, helpers, runners, Makefiles) are skipped silently.
    """
    tb_dir = Path(tb_dir)
    if not tb_dir.is_dir():
        return []

    found: list[Testbench] = []
    sources: dict[int, tuple[str, str]] = {}      # id(testbench) -> (text, suffix)
    noted: set[str] = set()
    for path in sorted(p for p in tb_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(tb_dir)
        if any(p.startswith(".") or p in _OUTPUT_DIRS for p in rel.parts[:-1]):
            continue
        if len(rel.parts) == 1:
            framework, label = "directed", "files directly in the testbench directory"
        else:
            framework, label = framework_for_dir(rel.parts[0]), rel.parts[0]
        if framework == "directed" and (len(rel.parts) == 1 or rel.parts[0].lower() not in FRAMEWORKS):
            if label not in noted:
                noted.add(label)
                print(f"  NOTE: testbenches in {label} are treated as 'directed' "
                      f"(use vunit/, cocotb/, pyuvm/ or directed/)", file=sys.stderr)

        suffix = path.suffix.lower()
        wanted = {".py"} if framework in _PYTHON_FRAMEWORKS else _HDL_SUFFIXES
        if suffix not in wanted:
            continue
        text = _read(path)
        if text is None:
            continue

        shown = path.relative_to(tb_dir.parent).as_posix()
        if framework in _PYTHON_FRAMEWORKS:
            try:
                purpose, tests = (parse_pyuvm if framework == "pyuvm" else parse_cocotb)(text)
            except SyntaxError as exc:
                _warn(path, f"not valid Python ({exc.msg}) — skipped")
                continue
            if not tests:
                continue
            name = path.stem
        else:
            code, _ = _scan(text, suffix)
            entity = _first_entity(code, suffix)
            if entity is None:
                continue                                   # a package or helper
            name = entity[0]
            purpose = header_purpose(text, suffix)
            if framework == "vunit":
                tests = parse_vunit_hdl(text, suffix)
            else:
                tests = parse_directed(text, suffix) or [TestCase(name, purpose)]
        tb = Testbench(name, shown, framework, purpose, tests,
                       link_dut(path.stem if framework in _PYTHON_FRAMEWORKS else name,
                                text, suffix, module_names))
        found.append(tb)
        sources[id(tb)] = (text, suffix)

    # A module that another testbench file instantiates is a helper (a bus
    # functional model, a memory model), not a testbench.
    hdl = [t for t in found if t.framework not in _PYTHON_FRAMEWORKS]
    known = {t.name.lower() for t in hdl}
    used: set[str] = set()
    for t in hdl:
        text, suffix = sources[id(t)]
        code, _ = _scan(text, suffix)
        others = known - {t.name.lower()}
        used |= set(extract_instantiations_vhdl(code, others) if suffix in _VHDL_SUFFIXES
                    else extract_instantiations_sv(code, others))
    found = [t for t in found if t.framework in _PYTHON_FRAMEWORKS or t.name.lower() not in used]

    order = {fw: i for i, fw in enumerate(FRAMEWORKS)}
    return sorted(found, key=lambda t: (order[t.framework], t.name.lower()))
