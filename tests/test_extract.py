"""Phase 4: text extraction roundtrip and coverage (docs/re/text.md).

The extractor writes script/*.json; these tests prove it against the original disc under work/disc/tree:
  * re-encoding every extracted string gives the original bytes (tools/sjis.py roundtrip);
  * the strings plus the recorded non-text ranges tile the exe's whole text region;
  * every S operand of every script is extracted, and no full-width glyph in a script section sits
    outside an entry (data byte pairs are listed with a reason in script/data_runs.txt);
  * a re-dump never loses an English line.
They skip without the unpacked disc, like the rest of the suite.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import exestr as X  # noqa: E402
import extract as E  # noqa: E402
import sjis  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'
SKIP = pytest.mark.skipif(not TREE.is_dir(), reason='work/disc/tree not unpacked')


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


@SKIP
def test_roundtrip_and_coverage():
    """The one gate: every entry re-encodes to the ROM bytes, and the text ranges are fully covered."""
    assert E.check(None) == []


@SKIP
def test_counts():
    files = [E.out_path(rel) for rel, _ in E.sources()]
    assert len(files) == 203
    script_entries = sum(len(load(f)['entries']) for f in files)
    exe = load(E.out_path(E.EXE))
    text = sum(1 for e in exe['entries'] if e['kind'] == 'text')
    assert script_entries == 2349, script_entries
    assert text >= 800, text
    assert sum(1 for e in exe['entries'] if e['kind'] == 'keep') >= 100


@SKIP
def test_exe_region_is_tiled():
    """Entries and gaps tile file 0x800-0x5700 exactly, and every gap carries a reason."""
    exe = load(E.out_path(E.EXE))
    cover = sorted([(e['off'], e['off'] + e['len'], 'entry') for e in exe['entries']] +
                   [(o, o + n, r) for o, n, r in exe['gaps']])
    pos = X.REGION[0]
    for a, b, r in cover:
        assert a == pos, f'gap or overlap at {pos:#x}'
        assert b > a and r in ('entry', 'nul', 'data')
        pos = b
    assert pos == X.REGION[1]


@SKIP
def test_no_text_outside_entries():
    """No full-width glyph in a script section is left out of the extraction (except known data runs)."""
    known = E.known_data_runs()
    for rel, path in E.sources():
        data = path.read_bytes()
        js = load(E.out_path(rel))
        assert set(E.uncovered_text(rel, data, js['entries'])) <= set(known.get(rel, {})), rel


@SKIP
def test_exe_gaps_hold_no_text():
    """A gap is data, not a missed string: every full-width run in the region is an entry, and no
    huge graphic is left out of the extraction."""
    data = (TREE / E.EXE).read_bytes()
    exe = load(E.out_path(E.EXE))
    spans = [(e['off'], e['off'] + e['len']) for e in exe['entries']]
    for s, e in X.runs(data):
        if X.wide(data[s:e]):
            assert any(a <= s and e <= b for a, b in spans), f'uncovered text {s:#x}-{e:#x}'


def test_codec_selftest():
    assert sjis.selftest() == []


def test_merge_keeps_english():
    old = {'entries': [{'id': 'a', 'en': 'Hi', 'status': 'done', 'notes': 'n'}]}
    new = {'entries': [{'id': 'a', 'en': '', 'status': '', 'notes': ''},
                       {'id': 'b', 'en': '', 'status': '', 'notes': ''}]}
    assert E.merge(new, old) == 1
    assert new['entries'][0]['en'] == 'Hi' and new['entries'][0]['status'] == 'done'
    assert new['entries'][1]['en'] == ''


def test_dump_refuses_to_clobber(tmp_path, monkeypatch):
    """dump keeps an existing file unless --force, so a re-dump can never wipe a batch of English."""
    monkeypatch.setattr(E, 'OUT', tmp_path)
    monkeypatch.setattr(E, 'sources', lambda: [])
    (tmp_path).mkdir(exist_ok=True)
    dest = tmp_path / 'exe.json'
    dest.write_text('{"entries": [{"id": "x", "en": "kept"}], "source": "SLPS_009.07", '
                    '"kind": "exe", "gaps": []}', encoding='utf-8')
    E.dump(type('A', (), {'force': False, 'only': None})())
    assert 'kept' in dest.read_text(encoding='utf-8')
