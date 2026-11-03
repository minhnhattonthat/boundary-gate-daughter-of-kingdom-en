"""Identity build: unpack + repack with no edits gives Track 01 byte for byte (phase 3; keep green forever)."""
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402

TRACK1_SHA1 = (ROOT / 'rom.sha1').read_text().split('(Track 01).bin')[0].splitlines()[-1].split()[0]


@pytest.mark.skipif(not build.ROM_CUE.is_file() or not (build.MKPSXISO / 'mkpsxiso.exe').is_file(),
                    reason='no dump in rom/ or no mkpsxiso')
def test_identity_repack():
    build.unpack()
    out = ROOT / 'work' / 'idtest' / 'identity'
    data = build.repack(out)
    with open(data, 'rb') as f:
        assert hashlib.file_digest(f, 'sha1').hexdigest() == TRACK1_SHA1
    cue = out.with_suffix('.cue').read_text()
    assert cue.count('FILE "') == 90 and f'FILE "{data.name}"' in cue
    for name in cue.split('FILE "')[2:]:
        assert Path(name.split('"')[0]).is_file()  # audio tracks resolve to the rom/ bins
