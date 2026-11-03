"""Build the English disc: build/boundary-gate-en.bin (data track) + .cue (audio tracks 02-90 from rom/).

Usage: python -X utf8 tools/build.py
Steps: check the dump (rom.sha1), unpack it once with dumpsxiso into work/disc (tree + layout.xml), repack with
mkpsxiso, cut the data track off the single image mkpsxiso writes, and write a cue that points the audio tracks
at the untouched rom/ bins. With no edits the data track is byte-identical to Track 01 (tests/test_build.py)."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_rom  # noqa: E402

ROM_CUE = ROOT / 'rom' / 'Boundary Gate - Daughter of Kingdom (Japan).cue'
DISC = ROOT / 'work' / 'disc'
MKPSXISO = ROOT / 'tools' / 'mkpsxiso' / 'mkpsxiso-2.30-win64'
OUT = ROOT / 'build' / 'boundary-gate-en'


def unpack():
    """work/disc/tree + layout.xml from the original disc (once)."""
    if (DISC / 'layout.xml').is_file():
        return
    DISC.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(MKPSXISO / 'dumpsxiso.exe'), '-x', 'tree', '-s', 'layout.xml', str(ROM_CUE)],
                   cwd=DISC, check=True, stdout=subprocess.DEVNULL)


def repack(out):
    """mkpsxiso the layout into out.bin (data track only) + out.cue. Returns the data track path."""
    out.parent.mkdir(parents=True, exist_ok=True)
    full, full_cue = out.with_suffix('.full.bin'), out.with_suffix('.full.cue')
    subprocess.run([str(MKPSXISO / 'mkpsxiso.exe'), '-q', '-y', '-o', str(full), '-c', str(full_cue), 'layout.xml'],
                   cwd=DISC, check=True)
    # Track 02 INDEX 00 = end of the data track (the Redump split keeps each pregap with its audio track)
    m, s, f = map(int, re.search(r'TRACK 02 AUDIO\s+INDEX 00 (\d+):(\d+):(\d+)', full_cue.read_text()).groups())
    size = ((m * 60 + s) * 75 + f) * 2352
    data = out.with_suffix('.bin')
    with open(full, 'rb') as src, open(data, 'wb') as dst:
        while size:
            chunk = src.read(min(size, 1 << 24))
            dst.write(chunk)
            size -= len(chunk)
    full.unlink()
    full_cue.unlink()
    # Same cue as the original, Track 01 renamed, audio bins referenced in rom/ (never rewritten)
    rel = Path('..') / 'rom' if out.parent == ROOT / 'build' else ROM_CUE.parent
    cue = ROM_CUE.read_text()
    cue = re.sub(r'FILE "([^"]*\(Track 01\)\.bin)"', f'FILE "{data.name}"', cue)
    cue = re.sub(r'FILE "([^"]*\(Track (?!01\))\d+\)\.bin)"', lambda mm: f'FILE "{rel / mm.group(1)}"', cue)
    out.with_suffix('.cue').write_text(cue)
    return data


def main():
    check_rom.check()
    if not (MKPSXISO / 'mkpsxiso.exe').is_file():
        sys.exit(f'missing {MKPSXISO}: see AGENTS.md Paths')
    unpack()
    data = repack(OUT)
    print(f'built {data} + {OUT.with_suffix(".cue").name}')


if __name__ == '__main__':
    main()
