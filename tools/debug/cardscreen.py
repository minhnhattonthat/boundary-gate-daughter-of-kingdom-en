"""Show a memory card's save titles in the PS1 BIOS memory-card manager (the screen players see outside the game).

usage: python -X utf8 tools/debug/cardscreen.py CARD.mcd [--out work/qa/bios] [--route "..."]

Boots the BIOS shell (an audio-only disc: Track 02 of the original), opens the memory-card screen and moves onto
card 1's first save, so its title shows in the bar at the bottom. emu.py always passes -fastboot (which skips the
shell), so this writes emu.py's driver once and runs PCSX-Redux itself. BIOS menus need presses of ~20 frames.
Also prints every save title on the card (decoded Shift-JIS) and flags single-byte characters, which SCE's spec
forbids in titles.
"""
import argparse
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL  # noqa: E402
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import emu  # noqa: E402
import sheet  # noqa: E402

ROUTE = '2400 -;20 circle;400 -;20 left;300 -;20 right;300 -'   # the shell takes input only from ~f2300
TRACK2 = os.path.join(ROOT, 'rom', 'Boundary Gate - Daughter of Kingdom (Japan) (Track 02).bin')


def titles(card):
    d = open(card, 'rb').read()
    out = []
    for i in range(1, 16):
        if d[0x80 * i] == 0x51:                       # first block of a save
            t = d[0x2000 * i + 4:0x2000 * i + 68].split(b'\0')[0]
            single = [b for k, b in enumerate(t) if b < 0x80 and (k == 0 or not 0x81 <= t[k - 1] <= 0xEF)]
            out.append((i, t.decode('cp932', 'replace'), bool(single)))
    return out


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('card')
    p.add_argument('--out', default=os.path.join(ROOT, 'work', 'qa', 'bios'))
    p.add_argument('--route', default=ROUTE)
    a = p.parse_args(argv)
    bad = 0
    for i, t, single in titles(a.card):
        print(f'block {i}: {t}' + ('   <- single-byte characters' if single else ''))
        bad += single
    run = os.path.join(a.out, 'run')
    os.makedirs(run, exist_ok=True)
    cue = os.path.join(a.out, 'audio.cue')
    with open(cue, 'w', encoding='utf-8') as f:
        f.write(f'FILE "{TRACK2}" BINARY\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n')
    frames = sum(int(s.split()[0]) for s in a.route.split(';')) + 200
    # emu.py writes the driver (_run.lua: route, shots); its own fastboot run never reaches the shell
    subprocess.run([sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts', 'emu.py'), cue, '--out', run,
                    '--route-str', a.route, '--frames', str(frames), '--shot-every', '100'],
                   capture_output=True, text=True)
    for f in glob.glob(os.path.join(run, 'f*.p*')):
        os.remove(f)
    mcd = os.path.join(run, 'memcard1.mcd')
    with open(a.card, 'rb') as src, open(mcd, 'wb') as dst:
        dst.write(src.read())
    pcsx = os.path.join(ROOT, 'tools', 'pcsx')
    bios = sorted(glob.glob(os.path.join(ROOT, 'tools', 'bios', 'scph*.bin')))[0]
    subprocess.run([os.path.join(pcsx, 'pcsx-redux.main'), '-portable', '-noupdate', '-no-ui', '-run', '-loadiso',
                    cue, '-dofile', os.path.join(run, '_run.lua'), '-no-debugger', '-dynarec', '-bios', bios,
                    '-memcard1', mcd], cwd=pcsx, capture_output=True, timeout=300)
    for raw in glob.glob(os.path.join(run, '*.psx')):
        emu.to_png(raw)
    sheet.make(run, cols=4, div=1, limit=12, changed=0.003, lo=1400, out=os.path.join(a.out, 'sheet.png'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
