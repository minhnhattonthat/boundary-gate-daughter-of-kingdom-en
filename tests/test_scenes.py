"""The warp scene list (tools/debug/scenes.tsv) is what mkscenes.py builds, and names every reachable map, room and
event file (docs/re/debug.md). Skips when the unpacked disc (work/disc/tree) is absent."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TREE = ROOT / 'work' / 'disc' / 'tree'
sys.path.insert(0, str(ROOT / 'tools' / 'debug'))
pytestmark = pytest.mark.skipif(not TREE.is_dir(), reason='work/disc/tree absent')


def test_tsv_is_current():
    import mkscenes
    rows = mkscenes.build()
    lines = (ROOT / 'tools' / 'debug' / 'scenes.tsv').read_text(encoding='utf-8').splitlines()[2:]
    assert lines == ['\t'.join(str(c) for c in r) for r in rows], 'run python -X utf8 tools/debug/mkscenes.py'


def test_every_file_has_a_scene():
    import mkscenes
    names = {r[0] for r in mkscenes.build()}
    want = set()
    for rel, _ in mkscenes.files():
        n = int(rel[-6:-4])
        kind = {'EVMES': 'ev', 'MAPMES': 'map', 'ROOMMES': 'room'}[rel.split('/')[0].rstrip('0123456789')]
        if kind == 'map' and n == 95:
            continue   # MAPMES95: no map exit leads there; leftover
        want.add('new_game' if (kind, n) == ('ev', 0) else f'{kind}_{n:02d}')
    assert want - names == set()
