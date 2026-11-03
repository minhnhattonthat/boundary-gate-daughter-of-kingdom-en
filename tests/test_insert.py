"""Text insertion: jp roundtrip is byte-identical, growth keeps the script valid, markers fit the box.

The roundtrip is the strong test: every one of the 204 extracted files is rebuilt from its own jp
with the same writer the English build uses, so a wrong jump or routine fixup shows up immediately.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import insert  # noqa: E402
import sjis  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'


def _jump_ok(scr):
    """Every relative jump and routine offset lands on an instruction boundary, like test_evscript."""
    ins = list(E.parse(scr))
    bounds = {at for at, _, _ in ins} | {len(scr)}
    bad = [(at, a[2]) for at, op, args in ins for a in args
           if a[0] == 'J' and (args[-1][1] + 2 + a[2]) not in bounds]
    for fl, _, off, name in E.routines(scr):
        if fl == 0xff and off and off not in bounds:
            bad.append(('routine', off))
    return bad


def test_roundtrip_is_byte_identical():
    """Every extractable file, rebuilt from its own jp, equals the disc bytes: the writer and both
    offset fixups are neutral (a wrong jump or routine fixup breaks this immediately)."""
    bad = [rel for rel, path in insert.script_files()
           if insert.write_script(rel, path.read_bytes(), 'jp') != path.read_bytes()]
    assert not bad, bad[:5]
    exe = (TREE / insert.EXE).read_bytes()
    assert insert.rebuild_exe(exe, {e['id']: e['jp'] for e in insert.entries_of(insert.EXE)})[0] == exe


def test_marker_and_grow_keep_the_script_valid():
    rel = 'MAPMES0/MAPMES00.BIN'
    data = (TREE / rel).read_bytes()
    new = insert.write_script(rel, data, 'marker', grow=4096)
    so, sl = E.sections(new)[-1]
    assert so == E.sections(data)[-1][0]          # only the last section changes
    scr = new[so:so + sl]
    assert not _jump_ok(scr), _jump_ok(scr)[:3]
    # the growth is real and the no-op padding parses
    assert sl > E.sections(data)[-1][1] + 4096
    assert sum(1 for _ in E.parse(scr)) >= sum(1 for _ in E.parse(data[so:]))


def test_english_text_keeps_jumps_valid():
    rel = 'MAPMES0/MAPMES00.BIN'
    data = (TREE / rel).read_bytes()
    stem = Path(rel).stem
    texts = {e['id']: ('A much longer English line that must still fit somehow ' * 2 if e['kind'] == 'text'
                       and e['off'] < E.sections(data)[-1][0] + 0x400 else e['jp'])
             for e in insert.entries_of(rel)}
    new = insert.rebuild_script(data, stem, texts, ascii_text=True)
    so, sl = E.sections(new)[-1]
    assert not _jump_ok(new[so:so + sl])


def test_marker_text_fits_the_box():
    bad = []
    for rel, _ in insert.script_files():
        for e in insert.entries_of(rel):
            text = insert.text_for(e, 'marker')
            if e['kind'] != 'text':
                continue
            try:
                sjis.encode(text)
            except sjis.SjisError as ex:
                bad.append((e['id'], str(ex)))
                continue
            if '@' in text or '\\' in text:
                bad.append((e['id'], 'printer escape in marker'))
            clean = ''.join(ch if (ord(ch) >= 0x20 or ch == '\r') else '\r' for ch in text)
            for row in clean.split('\r'):
                if insert._cells(row) > insert.COLS:
                    bad.append((e['id'], f'row of {insert._cells(row)} cells: {row!r}'))
    assert not bad, bad[:5]


def test_stage_writes_changed_files_and_layout(tmp_path):
    lp, files = insert.stage('test-insert', 'marker', only='EVMES0/EVENT00.BIN')
    try:
        names = sorted(Path(r).name for r, _ in files)
        assert 'EVENT00.BIN' in names and 'SLPS_009.07' in names
        xml = lp.read_text(encoding='utf-8')
        assert 'source="' in xml and str(tmp_path) not in xml
        staged = lp.parent / 'tree' / 'EVMES0' / 'EVENT00.BIN'
        assert staged.is_file()
        data = staged.read_bytes()
        so, sl = E.sections(data)[-1]
        assert not _jump_ok(data[so:so + sl])
    finally:
        for p in (lp.parent).rglob('*'):
            if p.is_file():
                p.unlink()
