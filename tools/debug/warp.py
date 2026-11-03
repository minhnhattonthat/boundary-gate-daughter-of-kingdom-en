"""Warp to any scene from a cold boot (tools/debug/scenes.tsv, built by mkscenes.py; docs/re/debug.md).

usage: python -X utf8 tools/debug/warp.py SCENE.. [--rom CUE] [--out DIR] [--state] [--jobs N] [--var NAME=LUA]..
       python -X utf8 tools/debug/warp.py --all [--match PREFIX] --state --jobs 4     regenerate the state library
       python -X utf8 tools/debug/warp.py --list

Each scene runs emu.py with tools/debug/warp.lua on the boot route (no debugger needed); warp.lua presses the
scene's "after" steps once it has arrived, holds "hold" frames (--hold overrides) and ends the run. Writes
<out>/<scene>/ (shots every --shot-every frames, final.png, sheet.png, log.txt), and passes when the run exits 0, the
log has "warp: arrived" and final.png is not one flat colour. --state keeps work/states/<scene>.sstate (passing
scenes only). --var overrides a scene value (e.g. --var BATTLE=37). Default ROM: build/boundary-gate-en.cue when it
exists, else the original. Exit 1 if any scene fails.
"""
import argparse, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from skill import SKILL  # noqa: E402
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import sheet  # noqa: E402

BOOT = os.path.join(ROOT, 'tools', 'routes', 'boot.txt')
ORIG = os.path.join(ROOT, 'rom', 'Boundary Gate - Daughter of Kingdom (Japan).cue')
BUILT = os.path.join(ROOT, 'build', 'boundary-gate-en.cue')


def load_scenes():
    rows = {}
    with open(os.path.join(HERE, 'scenes.tsv'), encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f if not l.startswith('#')]
    head = lines[0].split('\t')
    for l in lines[1:]:
        if l.strip():
            r = dict(zip(head, l.split('\t')))
            rows[r['name']] = r
    return rows


def route_frames(steps):
    return sum(int(s.split()[0]) for s in steps if s.strip() and not s.strip().startswith('#'))


def run(scene, a):
    out = os.path.join(a.out, scene['name'])
    os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):   # a shorter rerun must not leave the last run's frames in the sheet
        if old.endswith(('.png', '.psx')):
            os.remove(os.path.join(out, old))
    hold = int(a.hold if a.hold is not None else scene['hold'])
    after = [s.strip() for s in scene['after'].split(';') if s.strip()]
    # warp.lua ends the run itself after arrival + after + hold; --frames is only the upper bound
    frames = route_frames(open(BOOT, encoding='utf-8').read().splitlines()) + 3000 + route_frames(after) + hold
    cmd = [sys.executable, '-X', 'utf8', os.path.join(SKILL, 'scripts', 'emu.py'), a.rom, '--out', out,
           '--route', BOOT, '--script', os.path.join(HERE, 'warp.lua'), '--frames', str(frames),
           '--shot-every', str(a.shot_every), '--sheet', '--timeout', str(int(frames / 100) + 180)]
    for v in [x for x in scene['vars'].split(';') if x] + [f"AFTER='{';'.join(after)}'", f'HOLD={hold}'] + a.var:
        cmd += ['--var', v]
    mash = a.mash if a.mash is not None else int(scene['mash'])
    if mash:
        cmd += ['--mash', str(mash), '--mash-key', 'circle']
    state = os.path.join(ROOT, 'work', 'states', scene['name'] + '.sstate')
    if a.state:
        cmd += ['--state-out', state]
    with open(os.path.join(out, 'emu.log'), 'w', encoding='utf-8') as lf:
        rc = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT)
    log = open(os.path.join(out, 'log.txt'), encoding='utf-8', errors='replace').read() \
        if os.path.exists(os.path.join(out, 'log.txt')) else ''
    final = os.path.join(out, 'final.png')
    blank = not os.path.exists(final) or sheet.is_blank(sheet.read_png(final))
    ok = rc == 0 and 'warp: arrived' in log and not blank
    if a.state and not ok and os.path.exists(state):
        os.remove(state)   # never keep a state from a failed warp
    why = '' if ok else f' (exit {rc}, arrived {"warp: arrived" in log}, blank {blank})'
    return scene['name'], ok, f'{"ok  " if ok else "FAIL"} {scene["name"]}{why}  {final}'


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('scenes', nargs='*')
    p.add_argument('--all', action='store_true')
    p.add_argument('--match', default='')
    p.add_argument('--list', action='store_true')
    p.add_argument('--rom', default=BUILT if os.path.exists(BUILT) else ORIG)
    p.add_argument('--out', default=os.path.join(ROOT, 'work', 'qa', 'warp'))
    p.add_argument('--state', action='store_true')
    p.add_argument('--jobs', type=int, default=1)
    p.add_argument('--hold', type=int, help='frames to run after arrival (default: the scene\'s)')
    p.add_argument('--mash', type=int, help='press circle every N frames once the route is done (0 = off)')
    p.add_argument('--shot-every', type=int, default=300)
    p.add_argument('--var', action='append', default=[])
    a = p.parse_args(argv)
    rows = load_scenes()
    if a.list:
        for r in rows.values():
            print(f"{r['name']:<14} {r['note']}")
        return 0
    names = [n for n in rows if n.startswith(a.match)] if a.all else a.scenes
    unknown = [n for n in names if n not in rows]
    if unknown or not names:
        print('unknown or no scenes:', unknown or '(none given)', '- see --list')
        return 2
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda n: run(rows[n], a), names))
    for _, _, line in res:
        print(line)
    bad = [n for n, ok, _ in res if not ok]
    print(f'{len(res) - len(bad)}/{len(res)} ok' + (f'; failed: {" ".join(bad)}' if bad else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
