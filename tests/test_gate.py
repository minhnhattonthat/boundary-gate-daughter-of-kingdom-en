"""Write gate (tools/gate.py) on freshly generated English output, plus negative probes (phase-7 review #3)."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import gate  # noqa: E402
import gfx  # noqa: E402
import insert  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'
pytestmark = pytest.mark.skipif(not (TREE / insert.EXE).is_file(), reason='work/disc not unpacked')


@pytest.fixture(scope='module')
def exe_en():
    exe = (TREE / insert.EXE).read_bytes()
    log = []
    new = insert.write_exe(exe, 'en', log)[0]
    return exe, new, [_w(line) for line in log]


def _w(line):
    off, old, new, by = line.split(None, 3)
    return int(off, 16), bytes.fromhex(old), bytes.fromhex(new), by


def test_english_build_passes_the_gate(exe_en):
    files = [(rel, insert.write_script(rel, p.read_bytes(), 'en', ascii_text=True)) for rel, p in insert.script_files()]
    files += [(insert.EXE, exe_en[1]), (gfx.TITLE, gfx.title_en((TREE / gfx.TITLE).read_bytes()))]
    assert gate.check_files(files, exe_en[2]) == []


def test_logged_write_outside_the_map_fails(exe_en):
    exe, new, writes = exe_en
    bad = bytearray(new)
    bad[0x60000] ^= 0xFF
    w = writes + [(0x60000, exe[0x60000:0x60001], bytes(bad[0x60000:0x60001]), 'probe')]
    assert any('outside the allowed map' in x for x in gate.check_exe(exe, bytes(bad), w))
    assert gate.check_exe(exe, bytes(bad), writes)                     # unlogged: fails too


def test_overlapping_write_fails(exe_en):
    exe, new, writes = exe_en
    o, old, nw, _ = writes[0]
    assert any('overlaps' in x for x in gate.check_exe(exe, new, writes + [(o, old[:1], nw[:1], 'dup')]))


def test_mes_structure_probes():
    rel = 'MAPMES0/MAPMES00.BIN'
    orig = (TREE / rel).read_bytes()
    new = insert.write_script(rel, orig, 'en', ascii_text=True)
    assert gate.check_mes(rel, orig, new) == []
    so = E.sections(new)[-1][0]
    b = bytearray(new)
    b[E.HDR] ^= 1                                                     # a byte in section 0
    assert gate.check_mes(rel, orig, bytes(b))
    scr = new[so:]
    at, _, args = next(x for x in E.parse(scr) if x[2] and x[2][-1][0] == 'J')
    b = bytearray(new)
    jo = so + args[-1][1]
    struct.pack_into('<h', b, jo, struct.unpack_from('<h', b, jo)[0] + 1)   # a jump one byte off
    assert gate.check_mes(rel, orig, bytes(b))
    at, _, args = next(x for x in E.parse(scr) if x[2] and x[2][0][0] == 'B')
    b = bytearray(new)
    b[so + args[0][1]] ^= 1                                           # a non-text operand
    assert gate.check_mes(rel, orig, bytes(b))
    assert gate.check_mes(rel, orig, insert.write_script(rel, orig, 'marker', grow=64)) == []


def test_title_only_changes_the_katakana_area():
    orig = (TREE / gfx.TITLE).read_bytes()
    new = bytearray(gfx.title_en(orig))
    assert gate.check_title(orig, bytes(new)) == []
    new[-1] ^= 1
    assert gate.check_title(orig, bytes(new))
