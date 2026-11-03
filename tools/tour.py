"""Phase-8 QA tour: every warp scene, played on (events paged with circle, rooms talk to each NPC in turn), one
deduplicated contact sheet per scene for the visual-QA gate (qa_gate.py, docs/visual-qa-brief.md).

usage: python -X utf8 tools/tour.py [--rom CUE] [--out work/qa/tour] [--jobs 6] [--group ev|ending|room|map|misc]..
                                    [scene..] [--sheets-only]
       python -X utf8 tools/tour.py --jp          same tour on the original disc into work/qa/tour_jp
Writes <out>/<group>/<scene>/f*.png (warp.py) and <out>/sheets/<scene>_sheet*.png (from arrival on).
Text types slowly (~3 frames a glyph, so ~250 frames for a full English page) and a press while it types skips the
rest of the page: presses come 300 frames apart, and PRESHOT=1 shoots the frame each press starts, i.e. the
finished page. Periodic shots (shot-every) catch what moves on by itself.
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'debug'))
import warp  # noqa: E402

PAGE = '6 circle;300 -'


def room_after(k_max=5):
    """Rooms: for each NPC k, cancel back to the room menu (cross), Talk, k downs, then page through with circle.
    Starting each NPC from the menu keeps the cursor count exact however many pages the last talk had."""
    steps = ['300 -']
    for k in range(k_max):
        steps += ['6 cross;40 -'] * 3 + ['6 circle;60 -'] + ['6 down;30 -'] * k + [PAGE] * 5
    # then Move: the destination list (ops 0x28/0x4e), shot by the cross press that closes it
    steps += ['6 cross;40 -'] * 3 + ['6 down;30 -', '6 circle;120 -', '6 cross;60 -']
    return ';'.join(steps)


# group: (scene filter, AFTER route or None (the scene's own), hold, shot-every, extra warp vars)
# Event pages advance on a timer (~200 frames a page) and a press skips the page on screen, so events get no
# presses, dense shots, and a press only where the script stalls on a real button wait (NUDGE).
GROUPS = {
    'ev': (lambda n: n.startswith('ev_') or n == 'new_game', None, 15000, 30, ['NUDGE=1200']),
    'ending': (lambda n: n == 'ending', None, 15000, 150, []),
    'room': (lambda n: n.startswith('room_'), room_after(), 300, 3000, []),
    'map': (lambda n: n.startswith('map_'), None, 3000, 60, ['NUDGE=600']),
    'misc': (lambda n: not re.match(r'(ev|room|map)_|new_game$|ending$', n), None, None, 30, []),
}


def arrival(scene_dir):
    try:
        m = re.search(r'arrived.*\(frame (\d+)\)', open(os.path.join(scene_dir, 'log.txt'), encoding='utf-8').read())
    except OSError:
        return None
    return int(m.group(1)) if m else None


def sheets(scene_dir, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    for old in os.listdir(out_dir):
        if re.fullmatch(re.escape(name) + r'_sheet(_\d+)?\.png', old):
            os.remove(os.path.join(out_dir, old))
    lo = arrival(scene_dir)
    # 0.003: one changed row of text is under 1% of the frame
    warp.sheet.make(scene_dir, cols=4, div=1, limit=12, changed=0.003, lo=max(0, lo - 60) if lo else None,
                    out=os.path.join(out_dir, f'{name}_sheet.png'))


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('scenes', nargs='*')
    p.add_argument('--jp', action='store_true', help='original disc into work/qa/tour_jp')
    p.add_argument('--rom')
    p.add_argument('--out')
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--group', action='append', choices=list(GROUPS))
    p.add_argument('--sheets-only', action='store_true', help='rebuild sheets from existing frames')
    a = p.parse_args(argv)
    rom = a.rom or (warp.ORIG if a.jp else warp.BUILT)
    out = a.out or os.path.join(ROOT, 'work', 'qa', 'tour_jp' if a.jp else 'tour')
    names = list(warp.load_scenes())
    bad = 0
    for g in a.group or list(GROUPS):
        pick, after, hold, every, extra = GROUPS[g]
        todo = [n for n in names if pick(n) and (not a.scenes or n in a.scenes)]
        if not todo:
            continue
        if not a.sheets_only:
            args = todo + ['--rom', rom, '--out', os.path.join(out, g), '--jobs', str(a.jobs),
                           '--shot-every', str(every)]
            args += ['--hold', str(hold)] if hold is not None else []
            args += ['--mash', '0', '--var', f"AFTER='{after}'", '--var', 'PRESHOT=1'] if after else []
            args += ['--mash', '0'] * bool(extra) + [x for v in extra for x in ('--var', v)]
            bad += warp.main(args)
        for n in todo:
            d = os.path.join(out, g, n)
            if os.path.isdir(d):
                sheets(d, os.path.join(out, 'sheets'), n)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
