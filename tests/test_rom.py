import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_rom  # noqa: E402


@pytest.mark.skipif(not any((ROOT / 'rom').glob('*Track 01*.bin')), reason='no dump in rom/')
def test_dump_matches_rom_sha1():
    check_rom.check()  # sys.exit on mismatch fails the test
