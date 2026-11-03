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


def test_english_scripts_build_and_parse():
    """Every script rebuilt from its English (laid out, printer-encoded) keeps valid jumps and has no
    Japanese left in its script section."""
    import re
    bad = []
    for rel, path in insert.script_files():
        data = path.read_bytes()
        new = insert.write_script(rel, data, 'en', ascii_text=True)
        so, sl = E.sections(new)[-1]
        scr = new[so:so + sl]
        if _jump_ok(scr):
            bad.append((rel, 'jump'))
        if re.search(r'[぀-ヿ一-鿿]{2,}', scr.decode('cp932', 'replace')):
            bad.append((rel, 'japanese'))
    assert not bad, bad[:5]


def test_english_exe_relocation():
    """English exe: every moved string is reached through all its rewritten references, nothing else
    still points at a vacated head, and every changed byte has a logged write over the right original."""
    import struct
    import exestr as X
    exe = (TREE / insert.EXE).read_bytes()
    log = []
    new, wrote, moved = insert.write_exe(exe, 'en', log)
    assert moved and len(new) == len(exe)
    refs = X.refs(exe)
    own = {o for _, _, sites in insert.EXTRA_STRINGS for o in sites}
    for eid, h, at in moved:
        for kind, o in refs[X.ram(h)]:
            if o in own:
                continue
            word = struct.unpack_from('<I', new, o)[0]
            got = word if kind == 'table' else (X.ram(h) & 0xFFFF0000) | (word & 0xFFFF)
            assert got == X.ram(at), (eid, hex(o))
        assert new[new.index(b'\0', at) - 1] != 0 or new[at] == 0    # NUL-terminated
    done = {int(line.split()[0], 16) for line in log if line.endswith(' lo16')}
    assert not [x for x in insert.stale_refs(exe, moved) if x[1] not in done]
    covered = set()
    for line in log:
        off, old = line.split()[:2]
        off = int(off, 16)
        assert exe[off:off + len(old) // 2].hex() == old
        covered.update(range(off, off + len(old) // 2))
    assert {i for i in range(len(exe)) if exe[i] != new[i]} <= covered


def test_card_title_prefix_matches_jp():
    """The in-game save list reads the location from byte 20 of the card title (exe 0x1f2c0 sprintf of
    exe:03638): the English full-width prefix before %s must be as long as the JP one."""
    e = next(x for x in insert.entries_of(insert.EXE) if x['id'] == 'exe:03638')
    en = insert.text_for(e, 'en')
    assert len(en.split('%s')[0].encode('cp932')) == len(e['jp'].split('%s')[0].encode('cp932')) == 20
    assert all(ord(c) > 0x7E for c in en.replace('%s', ''))   # full-width only, as SCE asks of titles


def test_save_slot_row_fits():
    """A used save slot's first row is exe:03374 (slot label) + exe:0339c (level, play time) in a one-row window
    that the JP fills to 34 cells; a longer row wraps and scrolls, leaving only ': 1' (phase 8)."""
    import wrap
    by = {x['id']: x for x in insert.entries_of(insert.EXE)}
    row = lambda m: sum(wrap.fmt_cells(insert.text_for(by[i], m).replace('::', ':').rstrip('\n'))  # noqa: E731
                        for i in ('exe:03374', 'exe:0339c'))
    assert row('jp') == 34 and row('en') <= 34


def test_field_party_rows_fit():
    """Field-menu party box (2 rows, JP 41 cells, English 39 after EXE_PATCHES): row 1 is exe:00fa4 (name/LV/HP),
    row 2 exe:00fc8 (status labels, MP) starts at column 1. One cell over wraps and scrolls row 1 away (phase 8)."""
    import wrap
    by = {x['id']: x for x in insert.entries_of(insert.EXE)}
    cells = lambda i, m: wrap.fmt_cells(insert.text_for(by[i], m).replace('::', ':').rstrip('\n'))  # noqa: E731
    assert (cells('exe:00fa4', 'jp'), 1 + cells('exe:00fc8', 'jp')) == (41, 41)
    assert cells('exe:00fa4', 'en') <= 39 and 1 + cells('exe:00fc8', 'en') <= 39
    # items-menu header, same box: icon/name/use/count, then description/equipped; no third line, and the use
    # label (%s from exe:00ba4..00bb4, up to 'In Battle') and a 30-cell description must fit their fields
    en = {i: insert.text_for(by[i], 'en') for i in ('exe:00af0', 'exe:00b0c')}
    assert '%-9s' in en['exe:00af0'] and '%-30s' in en['exe:00b0c'] and '\n' not in en['exe:00b0c']
    assert max(len(insert.text_for(by[i], 'en')) for i in ('exe:00ba4', 'exe:00bac', 'exe:00bb4')) <= 9
    assert cells('exe:00af0', 'en') <= 38 and cells('exe:00b0c', 'en') <= 38
    # magic-menu header, same box: spell, use label, MP cost
    assert '%-9s' in insert.text_for(by['exe:00bc0'], 'en') and cells('exe:00bc0', 'en') <= 38
