"""Build tools/debug/scenes.tsv (the warp scene list) from the scripts on the disc, plus the hand-made rows below.

usage: python -X utf8 tools/debug/mkscenes.py [--graph]
  --graph  print every event call (op 0x37), room entry (0x25/0x36) and map exit (0x35) site instead, with the story
           var tests (ops 00-05) in the 10 instructions before it.

Where the values come from (docs/re/debug.md):
  map_NN   location 0x100|NN at the first op 0x35 [map, x, y, dir] that targets it (map 0: the New Game spot).
  room_NN  location 0x200|NN, return map = the map whose script enters it (op 0x25/0x36), at that map's entry spot.
  ev_NN    New Game loads EVENTNN instead of EVENT00; the vars an op-0x37 caller tests with == are preset.
TSV columns: name, vars (warp.lua globals as emu.py --var values, ';'-separated), after (route steps pressed after
arrival, ';'-separated), hold (frames to run after that), mash (circle every N frames, 0 = off), note.
"""
import sys, glob, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import evscript

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
TREE = os.path.join(ROOT, 'work', 'disc', 'tree')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenes.tsv')
SKIP = {f'ROOMMES2/ROOMES{n}.BIN' for n in range(75, 80)}   # unreachable leftovers (docs/re/files.md)
EXE_BASE = 0x80010000 - 0x800
MAP_NAMES, ROOM_NAMES = 0x80074CDC, 0x80074E6C
NEWGAME_SPOT = (12, 5, 2)   # set by New Game after EVENT00 (0x80016AA8)

# Menu, shop and system scenes: name, vars, after (route after arrival), hold, mash, note.
# Field menu: square opens, circle confirms, cross closes.
FIELD = "KIND='loc';LOC=0x100;X=12;Y=5;DIR=2"
MENU = '6 square;45 -'
WHO = ';6 circle;60 -;6 circle;60 -'   # pick the entry, then the party member
EXTRA = [
    ('new_game', "KIND='event';EVENT=0", '', 300, 0, 'New Game as the player starts it: EVENT00 prologue'),
    ('menu_field', FIELD, MENU, 30, 0, 'field menu (map 0)'),
    ('menu_items', FIELD, MENU + WHO, 30, 0, 'field menu > items'),
    ('menu_magic', FIELD, MENU + ';6 down;45 -' + WHO, 30, 0, 'field menu > magic'),
    ('menu_equip', FIELD, MENU + ';6 down;45 -' * 2 + WHO, 30, 0, 'field menu > equip'),
    ('menu_status', FIELD, MENU + ';6 down;45 -' * 3 + WHO, 30, 0, 'field menu > status'),
    ('menu_map', FIELD, MENU + ';6 down;45 -' * 4 + ';6 circle;60 -', 30, 0, 'field menu > map'),
    ('menu_settings', FIELD, MENU + ';6 down;45 -' * 5 + ';6 circle;60 -', 30, 0, 'field menu > settings'),
    ('menu_debug', FIELD + ';DEBUG=1', MENU + ';6 down;45 -' * 6 + ';6 circle;60 -', 30, 0,
     'leftover debug window (debug flag on): map number, position, battle; debug builds only'),
    ('battle', "KIND='battle';BATTLE=1", '', 900, 0,
     'battle by formation id 1-140 (override with --var BATTLE=n), via the debug window'),
    # rooms: 会話 > keeper > talk pages > the room's own window. More presses go on to buy / save: stop here.
    ('shop', "KIND='loc';LOC=0x206;RET=0x100;X=12;Y=5;DIR=2", ';'.join(['300 -'] + ['6 circle;90 -'] * 6), 240, 0,
     'item shop (room 6) buy list'),
    ('healer', "KIND='loc';LOC=0x204;RET=0x100;X=12;Y=5;DIR=2", ';'.join(['6 circle;90 -'] * 5), 60, 0,
     'healer (room 4) service window'),
    ('save', "KIND='loc';LOC=0x200;RET=0x100;X=12;Y=5;DIR=2", ';'.join(['6 circle;90 -'] * 8), 60, 0,
     'inn (room 0) > record: memory-card save slots'),
    # width gate for the room lists (phase 7): Talk -> NPC list (op 0x1c), Move -> destinations (0x28)
    ('npcs_45', "KIND='loc';LOC=0x22d;RET=0x112;X=12;Y=6;DIR=2", '300 -;6 circle;90 -', 60, 0,
     'tavern (room 45) > Talk: NPC list with "Fisherman Maillol" (op 0x1c width)'),
    ('npcs_53', "KIND='loc';LOC=0x235;RET=0x124;X=5;Y=5;DIR=2", '300 -;6 circle;90 -', 60, 0,
     'inn (room 53) > Talk: NPC list with "High Priest of Sorcery" (op 0x1c width)'),
    ('moves_13', "KIND='loc';LOC=0x20d;RET=0x112;X=12;Y=6;DIR=2", '300 -;6 down;30 -;6 circle;90 -', 60, 0,
     'Maillol\'s ship (room 13) > Move: destination list (op 0x28 width)'),
    ('moves_62', "KIND='loc';LOC=0x23e;RET=0x12a;X=11;Y=15;DIR=0", '300 -;6 down;30 -;6 circle;90 -', 60, 0,
     'crest labyrinth map (room 62) > Move: destination list (op 0x4e width)'),
    ('game_over',"KIND='battle';BATTLE=1;HP=1;WIPE_HOLD=360", '', 3000, 60,
     'battle 1 with every HP at 1, mashing attack: party wiped, final = Game Over banner (English in the original)'),
    ('ending',"KIND='loc';LOC=0x800", '', 6000, 0, 'location 0x800 (script op 0x48): ending narration, credits'),
]


def exe_str(exe, table, i):
    p = struct.unpack_from('<I', exe, table - EXE_BASE + 4 * i)[0]
    o = p - EXE_BASE
    return exe[o:exe.index(b'\0', o)].decode('cp932', 'replace').replace('　', ' ').strip()


def files():
    for pat in ('EVMES*/EVENT*.BIN', 'MAPMES*/MAPMES*.BIN', 'ROOMMES*/ROOMES*.BIN'):
        for f in sorted(glob.glob(os.path.join(TREE, pat))):
            rel = os.path.relpath(f, TREE).replace('\\', '/')
            if rel not in SKIP:
                yield rel, f


def sites():
    """(file, offset, kind, target, extra, eq_conds, all_conds) per op 0x37 / 0x25 / 0x36 / 0x35."""
    for rel, f in files():
        data = open(f, 'rb').read()
        so, sl = evscript.sections(data)[-1]
        ins = list(evscript.parse(data[so:so + sl]))
        for i, (at, op, args) in enumerate(ins):
            if op == 0x37:
                kind, tgt, extra = 'event', args[0][2], ''
            elif op == 0x25:
                kind, tgt, extra = 'room', args[1][2], evscript.show(args[0][2])
            elif op == 0x36:
                kind, tgt, extra = 'room', args[0][2], ''
            elif op == 0x35:   # goto map: bytes map, x, y, dir
                m, x, y, d = args[0][2].to_bytes(4, 'little')
                kind, tgt, extra = 'map', m, (x, y, d)
            else:
                continue
            before = ins[max(0, i - 10):i]
            eq = {a[0][2]: a[1][2] for _, o, a in before if o == 0}
            conds = [f'v{a[0][2]:02x}{"=" if o == 0 else "?"}{a[1][2]}' for _, o, a in before if o <= 5]
            yield rel, at, kind, tgt, extra, eq, conds


def build():
    exe = open(os.path.join(TREE, 'SLPS_009.07'), 'rb').read()
    all_sites = list(sites())
    spot = {0: NEWGAME_SPOT}
    for rel, at, kind, tgt, extra, _, _ in all_sites:
        if kind == 'map':
            spot.setdefault(tgt, extra)
    room_from, ev_from = {}, {}
    for rel, at, kind, tgt, extra, eq, _ in all_sites:
        src = int(rel[-6:-4]) if rel.startswith('MAPMES') else None
        if kind == 'room' and (tgt not in room_from or (room_from[tgt][0] is None and src is not None)):
            room_from[tgt] = (src, rel)
        if kind == 'event' and tgt not in ev_from:
            ev_from[tgt] = (rel, eq)
    rows = []
    maps = sorted(int(os.path.basename(f)[6:8]) for f in glob.glob(os.path.join(TREE, 'MAPMES*', 'MAPMES*.BIN')))
    for m in maps:
        if m not in spot:
            continue   # no entry anywhere (MAPMES95: not in the map-name table either; leftover)
        x, y, d = spot[m]
        rows.append((f'map_{m:02d}', f"KIND='loc';LOC={0x100 | m:#x};X={x};Y={y};DIR={d}", '', 600, 0,
                     f'{exe_str(exe, MAP_NAMES, m)}'))
    rooms = sorted({int(r[-6:-4]) for r, _ in files() if r.startswith('ROOMMES')})
    for r in rooms:
        src, rel = room_from.get(r, (None, '-'))
        ret = src if src is not None and src in spot else 0
        x, y, d = spot[ret]
        rows.append((f'room_{r:02d}', f"KIND='loc';LOC={0x200 | r:#x};RET={0x100 | ret:#x};X={x};Y={y};DIR={d}", '',
                     600, 0, f'{exe_str(exe, ROOM_NAMES, r)} (entered from {rel})'))
    events = sorted(int(os.path.basename(f)[5:7]) for f in glob.glob(os.path.join(TREE, 'EVMES*', 'EVENT*.BIN')))
    for e in events:
        if e == 0:
            continue   # new_game
        rel, eq = ev_from.get(e, ('- (no op 0x37 caller)', {}))
        vars_ = ','.join(f'{k:x}={v}' for k, v in sorted(eq.items()))
        v = f"KIND='event';EVENT={e}" + (f";VARS='{vars_}'" if vars_ else '')
        # final shot = the event's first screen; play it through with --hold 6000 --mash 90
        rows.append((f'ev_{e:02d}', v, '', 300, 0, f'called from {rel}'))
    return [EXTRA[0]] + rows + EXTRA[1:]


def main(argv):
    if '--graph' in argv:
        for rel, at, kind, tgt, extra, _, conds in sites():
            print(f'{rel} {at:05x} {kind} {tgt} {extra}  {" ".join(conds)}')
        return 0
    rows = build()
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# generated by tools/debug/mkscenes.py; edit EXTRA there, not here\n')
        f.write('name\tvars\tafter\thold\tmash\tnote\n')
        for r in rows:
            f.write('\t'.join(str(c) for c in r) + '\n')
    print(f'{len(rows)} scenes -> {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
