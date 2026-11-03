"""Extract every on-screen string into script/ (one JSON per source file) and check the extraction.

Sources (docs/re/text.md, docs/re/script.md):
  * the script section (section 7) of every reachable EVMES/ROOMMES/MAPMES *.BIN: every S operand of
    every opcode is text the game displays (0x22 dialogue, 0x23 location title, 0x1c NPC name, 0x25
    building label, 0x27 choice, 0x28/0x4e room menu item, 0x21 speaker/instant line);
  * the exe's text region, file 0x800-0x5700, scanned by tools/exestr.py into strings plus data gaps.

Entry format, per string:
  id      stable "<stem>:<file offset hex>" (exe: "exe:<offset hex>"): the key for the translation memory
  off     file offset of the first byte; len = its length in bytes (no terminating 0)
  op      script opcode (script entries only); group = batching group
  jp      the original text, decoded byte-exactly by tools/sjis.py
  en      English (empty until phase 6); status/notes for review state
  kind    "text" (translate) or "keep" (engine string, path, ASCII credit: leave as it is)
  refs    exe entries: file offsets of the pointer-table words / code instructions that address it

The file also records what is NOT text, so coverage is checkable:
  gaps    exe: [off, len, reason] ranges (nul, ptr, data) that tile the region with the entries
  scr     script entries: the script section offset/length; instructions are re-parsed on check

usage: python -X utf8 tools/extract.py dump [--force] [--only GLOB]
       python -X utf8 tools/extract.py check
"""
import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import exestr as X  # noqa: E402
import sjis  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'
EXE = 'SLPS_009.07'
OUT = ROOT / 'script'
DATA_RUNS = OUT / 'data_runs.txt'    # script bytes that decode as a wide glyph but are not text
# ROOMMES2/ROOMES75-79: unreachable leftovers (dir = room // 25); the game never loads them (files.md)
LEFTOVER = {f'ROOMMES2/ROOMES{n}.BIN' for n in range(75, 80)}

OP_GROUP = {0x21: 'speaker', 0x22: 'dialogue', 0x23: 'location', 0x1c: 'npc', 0x25: 'building',
            0x27: 'choice', 0x28: 'menu', 0x4e: 'menu'}

# Exe text region by what the strings are used for (offsets from docs/re/text.md recon, refined here)
EXE_GROUPS = [
    (0x0800, 0x0834, 'party'),      # default party names
    (0x0834, 0x0880, 'debug'),      # malloc/free messages (engine)
    (0x0880, 0x0a40, 'boot'),       # title menu, wait/no, file paths, fonts
    (0x0a40, 0x105c, 'menu'),       # item/equip/status/map/settings screens
    (0x105c, 0x1f58, 'map'),        # map and room names (24-byte fixed fields)
    (0x1f58, 0x2c8a, 'items'),      # weapons, armour, items: names and descriptions
    (0x2c8a, 0x3128, 'spells'),     # spell names and descriptions
    (0x3128, 0x3378, 'shop'),       # shop, inn, healer
    (0x3378, 0x37cf, 'save'),       # memory card
    (0x37cf, 0x3a00, 'items'),      # item-use results
    (0x3a00, 0x3a30, 'gameover'),
    (0x3a30, 0x45ab, 'monsters'),   # monster names and their attack lines
    (0x45ab, 0x494b, 'battle'),
    (0x494b, 0x4ca9, 'engine'),     # sound/asset name tables between battle and ending
    (0x4ca8, 0x4f5c, 'ending'),     # ending narration
    (0x4f5c, 0x54a0, 'credits'),    # English END/CAST block and the staff credits
    (0x54a0, 0x5700, 'prologue'),   # opening lore
]


def exe_group(off):
    for a, b, name in EXE_GROUPS:
        if a <= off < b:
            return name
    return 'other'


def sources():
    """(relative path, absolute path) of every reachable *MES file."""
    out = []
    for d in ('EVMES', 'ROOMMES', 'MAPMES'):
        for p in sorted(TREE.glob(f'{d}*/*.BIN')):
            rel = p.relative_to(TREE).as_posix()
            if rel not in LEFTOVER:
                out.append((rel, p))
    return out


def script_entries(rel, data):
    """Entries for one *MES file's script section, plus (so, sl) of that section."""
    so, sl = E.sections(data)[-1]
    scr = data[so:so + sl]
    stem = Path(rel).stem
    entries = []
    for at, op, args in E.parse(scr):
        if op not in OP_GROUP:
            continue
        for kind, aoff, val in args:
            if kind != 'S':
                continue
            foff = so + aoff
            if foff + len(val) + 1 > len(data) or data[foff + len(val)] != 0:
                raise ValueError(f'{rel}: string at {foff:#x} is not NUL-terminated')
            jp = sjis.decode(val)
            entries.append({
                'id': f'{stem}:{foff:05x}',
                'off': foff,
                'op': f'{op:02x}',
                'group': OP_GROUP[op],
                'jp': jp,
                'en': '',
                # an S operand that is only printer control bytes (0x08 clear window, 0x10 wait) is a
                # script command, not a line to translate: keep it out of the translation batches
                'kind': 'text' if any(ord(c) >= 0x20 for c in jp) else 'data',
                'status': '',
                'notes': '',
            })
    return entries, so, sl


# Byte runs that decode as a glyph but are data: 0x974 = 8C B4 01, same shape as its neighbour 44 B4 01
# (keep), no reference reaches it.
NOT_TEXT = {0x974}


def exe_entries(data):
    strings, gaps = X.segment(data)
    refs = X.refs(data)
    entries = []
    for s, e in strings:
        raw = data[s:e]
        hits = sorted({o for a, w in refs.items() if X.ram(s) <= a < X.ram(e) for _, o in w})
        entries.append({
            'id': f'exe:{s:05x}',
            'off': s,
            'len': e - s,
            'ram': f'0x{X.ram(s):08x}',
            'group': exe_group(s),
            'jp': sjis.decode(raw),
            'en': '',
            'kind': 'text' if X.wide(raw) and s not in NOT_TEXT else 'keep',
            'refs': [f'0x{o:x}' for o in hits],
            'status': '',
            # the leftover debug window is Japanese on purpose: the release build never opens it
            'notes': 'debug menu: debug-only, kept in Japanese' if 0xe90 <= s < 0xfa0 else '',
        })
    gap_out = []
    for s, e, _ in gaps:
        reason = 'nul' if e - s == 1 and data[s] == 0 else 'data'
        gap_out.append([s, e - s, reason])
    return entries, gap_out


def payload(rel, data):
    if rel == EXE:
        entries, gaps = exe_entries(data)
        return {'source': rel, 'kind': 'exe', 'entries': entries, 'gaps': gaps}
    entries, so, sl = script_entries(rel, data)
    return {'source': rel, 'kind': 'script', 'scr': [so, sl], 'entries': entries}


def out_path(rel):
    if rel == EXE:
        return OUT / 'exe.json'
    return OUT / Path(rel).with_suffix('.json')


def merge(new, old):
    """Keep translations: only ids that survive keep their en/status/notes."""
    by_id = {e['id']: e for e in old.get('entries', [])}
    kept = 0
    for e in new['entries']:
        o = by_id.get(e['id'])
        if o is not None:
            for k in ('en', 'status', 'notes'):
                if o.get(k):
                    e[k] = o[k]
                    kept += bool(k == 'en')
    return kept


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')


def uncovered_text(rel, data, entries):
    """File offsets of wide glyphs in the script section that no entry covers. Empty for every file:
    either the extractor missed a string, or a data byte pair happens to decode as one glyph and is
    listed with a reason in script/data_runs.txt."""
    so, sl = E.sections(data)[-1]
    scr = data[so:so + sl]
    spans = [(e['off'], e['off'] + len(sjis.encode(e['jp']))) for e in entries]
    out = []
    for s, e in X.runs(scr, E.NROUT * E.RSIZE, len(scr)):
        i = s
        while i < e:
            n = X.char_len(scr, i) or 1
            if X.wide(scr[i:i + n]) and not any(a <= so + i and so + i + n <= b for a, b in spans):
                out.append(so + i)
            i += n
    return out


def known_data_runs():
    """{file offset -> reason} from script/data_runs.txt ('<source>:<0xoffset> <reason>' per line)."""
    out = {}
    if DATA_RUNS.exists():
        for line in DATA_RUNS.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            where, _, reason = line.partition(' ')
            src, _, off = where.rpartition(':')
            out.setdefault(src, {})[int(off, 16)] = reason
    return out


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dump(args):
    if not TREE.is_dir():
        sys.exit(f'no unpacked disc at {TREE}: run python tools/build.py once')
    made = skipped = kept = 0
    for rel, path in sources() + [(EXE, TREE / EXE)]:
        if args.only and not fnmatch.fnmatch(rel, args.only):
            continue
        dest = out_path(rel)
        if dest.exists() and not args.force:
            skipped += 1
            continue
        data = path.read_bytes()
        new = payload(rel, data)
        if dest.exists():
            kept += merge(new, load(dest))
        write_json(dest, new)
        made += 1
    print(f'dump: {made} files written, {skipped} kept (use --force to refresh), {kept} translations kept')
    return 0


def scan(args):
    """Report (and with --write record) script bytes that decode as a wide glyph but sit in no entry."""
    rows = []
    for rel, path in sources():
        data = path.read_bytes()
        js = load(out_path(rel)) if out_path(rel).exists() else None
        entries = js['entries'] if js else script_entries(rel, data)[0]
        for off in uncovered_text(rel, data, entries):
            rows.append((rel, off))
    for rel, off in rows:
        data = (TREE / rel).read_bytes()
        n = X.char_len(data, off)
        print(f'{rel}:0x{off:05x} {data[off:off + n].decode("cp932", "replace")!r}')
    print(f'scan: {len(rows)} script byte runs outside the extracted text')
    if args.write:
        lines = ['# Script bytes that decode as a full-width glyph but are data, not text.',
                 '# <source>:<file offset> <reason>. tools/extract.py check fails on any new one,',
                 '# because a new one is usually a string the extractor missed.']
        for rel, off in rows:
            lines.append(f'{rel}:0x{off:05x} data byte pair in map/script data')
        DATA_RUNS.parent.mkdir(parents=True, exist_ok=True)
        DATA_RUNS.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        print(f'scan: wrote {DATA_RUNS.relative_to(ROOT)}')
    return 0


def check(args):
    errors = []
    if not TREE.is_dir():
        sys.exit(f'no unpacked disc at {TREE}: run python tools/build.py once')
    files = [out_path(rel) for rel, _ in sources()] + [out_path(EXE)]
    missing = [f for f in files if not f.exists()]
    if missing:
        return [f'missing {f.relative_to(ROOT)}: run tools/extract.py dump']
    known = known_data_runs()
    text_entries = 0
    for rel, path in sources() + [(EXE, TREE / EXE)]:
        js = load(out_path(rel))
        data = path.read_bytes()
        if js['source'] != rel:
            errors.append(f'{rel}: source field is {js["source"]!r}')
        if js['kind'] == 'script':
            fresh, so, sl = script_entries(rel, data)
            if list(js['scr']) != [so, sl]:
                errors.append(f'{rel}: scr {js["scr"]} != [{so}, {sl}]')
            # every S operand has exactly one entry, in order, with the same bytes
            if [e['id'] for e in js['entries']] != [e['id'] for e in fresh]:
                errors.append(f'{rel}: entries {len(js["entries"])} do not match the script\'s '
                              f'{len(fresh)} strings (re-dump)')
            for e, f in zip(js['entries'], fresh):
                raw = data[e['off']:e['off'] + len(sjis.encode(f['jp']))]
                errors += _check_entry(rel, e, raw)
                for k in ('op', 'group', 'jp'):
                    if e[k] != f[k]:
                        errors.append(f'{rel} {e["id"]}: {k} differs from the ROM')
            extra = set(uncovered_text(rel, data, js['entries'])) - set(known.get(rel, {}))
            for off in sorted(extra):
                n = X.char_len(data, off) or 1
                errors.append(f'{rel}:0x{off:05x} {data[off:off + n].decode("cp932", "replace")!r} '
                              f'decodes as text but no entry covers it (missed string, or run '
                              f'tools/extract.py scan --write)')
        else:
            entries, gaps = exe_entries(data)
            want = [e['off'] for e in entries]
            if [e['off'] for e in js['entries']] != want:
                errors.append(f'{rel}: {len(js["entries"])} entries do not match the scan\'s {len(want)}')
            # entries + gaps tile the region: every byte belongs to exactly one of them
            cover = sorted([(e['off'], e['off'] + e['len']) for e in js['entries']] +
                           [(o, o + n) for o, n, _ in js['gaps']])
            pos = X.REGION[0]
            for a, b in cover:
                if a != pos:
                    errors.append(f'{rel}: coverage gap/overlap at {pos:#x} (next {a:#x})')
                    break
                pos = b
            if pos != X.REGION[1]:
                errors.append(f'{rel}: coverage ends at {pos:#x}, region ends {X.REGION[1]:#x}')
            for e in js['entries']:
                raw = data[e['off']:e['off'] + e['len']]
                errors += _check_entry(rel, e, raw)
        text_entries += sum(1 for e in js['entries'] if e['kind'] == 'text')
    bad = len(errors)
    for e in errors[:20]:
        print(f'FAIL {e}')
    print(f'check: {bad} errors, {len(files)} files, {text_entries} text entries')
    return errors


def _check_entry(rel, e, raw):
    """Roundtrip: encode(decode(bytes)) == bytes, and jp is what the file says it is."""
    out = []
    try:
        if sjis.encode(sjis.decode(raw)) != raw:
            out.append(f'{rel} {e["id"]}: roundtrip differs ({raw.hex()})')
        if sjis.decode(raw) != e['jp']:
            out.append(f'{rel} {e["id"]}: jp does not match the ROM bytes')
    except sjis.SjisError as ex:
        out.append(f'{rel} {e["id"]}: {ex}')
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog='extract.py', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('dump', help='write script/*.json for every source (keeps existing en)')
    d.add_argument('--force', action='store_true', help='refresh existing files, keeping translations')
    d.add_argument('--only', help='glob over source paths, e.g. "EVMES0/*"')
    d.set_defaults(fn=dump)
    c = sub.add_parser('check', help='roundtrip + coverage over everything in script/')
    c.set_defaults(fn=check)
    s = sub.add_parser('scan', help='report script bytes that decode as wide glyphs outside the text')
    s.add_argument('--write', action='store_true', help='record them as data in script/data_runs.txt')
    s.set_defaults(fn=scan)
    args = ap.parse_args(argv)
    r = args.fn(args)
    return 1 if isinstance(r, list) and r else (r or 0)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
