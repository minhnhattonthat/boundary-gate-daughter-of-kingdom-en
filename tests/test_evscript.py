"""The event-script parser walks every reachable *MES file end to end, and every jump and routine offset lands on
an instruction boundary (docs/re/script.md). Skips when the unpacked disc (work/disc/tree) is absent."""
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import tim  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'
# ROOMMES2/ROOMES75-79: unreachable leftovers (dir = room // 25, so 75-79 load from ROOMMES3); 76-79 are stale
LEFTOVER = {f'ROOMMES2/ROOMES{n}.BIN' for n in range(75, 80)}


def files():
    if not TREE.is_dir():
        return []
    return sorted(p for d in ('EVMES', 'ROOMMES', 'MAPMES') for p in TREE.glob(f'{d}*/*.BIN')
                  if p.relative_to(TREE).as_posix() not in LEFTOVER)


@pytest.mark.skipif(not TREE.is_dir(), reason='work/disc/tree not unpacked')
def test_file_count():
    assert len(files()) == 203


@pytest.mark.parametrize('path', files(), ids=lambda p: p.name)
def test_script_parses(path):
    data = path.read_bytes()
    so, sl = E.sections(data)[-1]
    scr = data[so:so + sl]
    ins = list(E.parse(scr))
    bounds = {at for at, _, _ in ins} | {len(scr)}
    for at, op, args in ins:
        for k, off, v in args:
            if k == 'J':
                assert off + 2 + v in bounds, f'jump at {at:#x}'
    for fl, _, off, name in E.routines(scr):
        if fl != 0xff or off or name.strip(b'\0'):
            assert off in bounds, f'routine {name} -> {off:#x}'


def test_tim_selftest():
    assert tim.main(['--selftest']) == 0
