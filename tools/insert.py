"""Insert text into the *MES scripts and the exe, and stage changed files for a repack (phase 5+).

Two consumers:
  * the marker build (`tools/build.py --marker`): every text entry replaced by its id plus a
    full-width filler, so a tour shows which box each entry draws in and what is still Japanese;
  * the English build (phase 7): each entry's `en` written in place of its `jp`.

Script insertion rewrites section 7 (the script, last section) and fixes what a length change moves:
`s16` relative jumps (ops 00-05, 08) and the 32 routine offsets (s16 from the script base). Sections
0-6 and the whole bytecode except the S operands are copied byte for byte; `insert.py roundtrip`
rebuilds every file from its own `jp` and requires the result to equal the original.

Exe insertion overwrites the string in place, NUL-padded to its original length. A longer English
string is an error until phase 7 adds relocation, so the build fails instead of spilling into the
next string.

usage: python -X utf8 tools/insert.py roundtrip [--only GLOB]
       python -X utf8 tools/insert.py stage TAG (marker|torture|en|jp) [--only GLOB] [--grow FILE=N]
"""
import argparse
import fnmatch
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import exestr as X  # noqa: E402
import extract  # noqa: E402
import sjis  # noqa: E402

TREE = ROOT / 'work' / 'disc' / 'tree'
DISC = ROOT / 'work' / 'disc'
STAGE = ROOT / 'work' / 'stage'
EXE = extract.EXE

# MES dirs are per-file, so the id can shrink: MAPMES00:abb77 -> M00.abb77. No ':' in a marker: the
# printer would print it as one colon either way, but the cell count must be the byte count.
_SHORT = re.compile(r'^(EVENT|MAPMES|ROOMES)(\d+):([0-9a-f]+)$')
_PREFIX = {'EVENT': 'E', 'MAPMES': 'M', 'ROOMES': 'R'}

# One page of the dialogue box is 26 half-width cells x 3 rows (width gate, docs/re/windows.md).
COLS, ROWS = 26, 3
FILLER = 'The quick brown fox jumps!'                    # exactly COLS cells
# Widest glyphs and punctuation for the width/glyph gate. No '@', '\\' (printer escapes) or ':'.
TORTURE = '!Wg~`{}[]|/?#$%^&*()-_+=<>"\''

OP_GROUP = extract.OP_GROUP


def short_id(eid):
    m = _SHORT.match(eid)
    if m:
        return f'{_PREFIX[m.group(1)]}{int(m.group(2)):02d}.{m.group(3)}'
    if eid.startswith('exe:'):
        return 'X.' + eid[4:].lstrip('0')
    return eid


def entries_of(rel):
    """Extracted entries for one source, from script/*.json."""
    return extract.load(extract.out_path(rel))['entries']


def script_files():
    return extract.sources()


# ---------------------------------------------------------------- text generation

def _cells(text):
    """Width in 6 px cells (a full-width glyph is two), ignoring zero-width printer controls."""
    return sum(2 if ord(ch) > 0x7E and not (0xFF61 <= ord(ch) <= 0xFF9F) else 1
               for ch in text if ord(ch) >= 0x20)


def marker_page(eid, jp):
    """Marker for a dialogue-style S operand: one box per page, the id on row 1.

    Paging is the original's (0x08 clear, 0x10 button wait, copied through). Each page keeps the
    original's row count and fills every row to exactly COLS cells, so the width gate reads the wrap
    limit and the row count straight off the shot."""
    tag = f'[{short_id(eid)}]'
    out, cur = [], []

    def flush():
        body = ''.join(cur)
        ctl = ''.join(ch for ch in body if ord(ch) < 0x20 and ch not in '\r\n')
        rows = [r for r in re.split(r'[\r\n]', body) if any(ord(c) >= 0x20 for c in r)]
        if any(ord(ch) >= 0x20 for ch in body):
            rows = rows or ['']
            n = max(1, min(len(rows), ROWS))
            box = [tag + FILLER[:COLS - _cells(tag)]] + [FILLER[:COLS]] * (n - 1)
            out.append('\r'.join(box) + ctl)
        else:
            out.append('')

    for ch in jp:
        if ch in '\x08\x10':
            flush()
            cur = []
            out.append(ch)
        else:
            cur.append(ch)
    flush()
    return ''.join(out)


def marker_field(eid, jp):
    """Marker for a single-line field (name, label, choice, menu item): the id, no filler."""
    return f'[{short_id(eid)}]'


def marker_field(eid, jp):
    """Marker for a single-line field (name, label, choice, menu item): the id, no filler."""
    return f'[{short_id(eid)}]'


def marker_exe(eid, jp, maxlen=None):
    """Marker for an exe string: keep ASCII (and printf specifiers) so rows keep their layout, put
    the id in place of the first run of Japanese characters, '#' in place of later runs.

    Several exe strings are tiny fixed fields (a 6-byte party name, a menu label), so the tag shrinks
    until the marker fits: [X.81c] -> [81c] -> *. A marker build never spills into the next field."""
    short = short_id(eid)
    off = eid.split(':')[1].lstrip('0')
    tags = [f'[{short}]', f'[{off}]', off[-4:], off[-2:], '*']

    def build(tag):
        parts, i, first = [], 0, True
        for m in re.finditer(r'[\u3000-\u30ff\u3400-\u9fff\uff00-\uffef]+', jp):
            if m.start() > i:
                parts.append(jp[i:m.start()])
            run = m.group(0)
            if first:
                parts.append(tag + '#' * max(0, len(run) - len(tag)))
            else:
                parts.append('#' * min(len(run), 8))
            first = False
            i = m.end()
        parts.append(jp[i:])
        text = ''.join(parts)
        if first:                  # no Japanese in the string at all
            text = tag + text
        return text

    for tag in tags:
        text = build(tag)
        if maxlen is None or len(sjis.encode(text)) <= maxlen:
            return text
    return build('*')


def torture_page(eid, jp):
    """Glyph torture: every printable ASCII character we allow, at full width, three rows per page."""
    tag = f'[{short_id(eid)}]'
    glyphs = (TORTURE * 3)[:2 * COLS]
    row1 = tag + FILLER[:COLS - _cells(tag)]
    return '\r'.join([row1, glyphs[:COLS], glyphs[COLS:]])


FIELD_OPS = {'1c', '25', '27', '28', '4e'}


def ruler_page(eid, jp):
    """Width-gate ruler for a dialogue page: 78 digits (3 x COLS) with no line breaks, so the
    printer's own wrap decides the rows. Reading the digits left on each row gives the box's true
    column count, and the trailing button-wait puts the page arrow on the last row."""
    return ('0123456789' * 8)[:COLS * ROWS] + '\x10'


def ruler_field(eid, jp):
    """Width-gate ruler for a single-line field: 20 digits, longer than any name field."""
    return '0123456789' * 2


def ruler_exe(eid, jp):
    """Width-gate ruler for an exe string: keep ASCII, fill every Japanese run with digits of the
    same length, so each field is drawn full and its end shows on screen."""
    return ''.join('8' if ord(ch) > 0x7E else ch for ch in jp)


def text_for(entry, mode):
    """The replacement text for one entry in `mode` = marker|torture|ruler|en|jp."""
    if mode == 'jp' or entry['kind'] != 'text':
        return entry['jp']
    if mode == 'en':
        return entry['en'] or entry['jp']
    if mode == 'ruler':
        if entry['id'].startswith('exe:'):
            return ruler_exe(entry['id'], entry['jp'])
        if entry['op'] == '22':
            return ruler_page(entry['id'], entry['jp'])
        return ruler_field(entry['id'], entry['jp'])
    if entry['id'].startswith('exe:'):
        return marker_exe(entry['id'], entry['jp'], entry.get('len'))
    if mode == 'torture' and entry['op'] == '22':
        return torture_page(entry['id'], entry['jp'])
    if mode == 'marker' and entry['op'] == '22':
        return marker_page(entry['id'], entry['jp'])
    return marker_field(entry['id'], entry['jp'])


def encode_text(text, ascii_text):
    """ASCII English goes through the printer rules; Japanese (untranslated, or the roundtrip) is
    encoded byte-exactly so a build never rewrites a line nobody translated."""
    if ascii_text and all(ord(c) <= 0x7E for c in text):
        return sjis.encode_en(text)
    return sjis.encode(text)


# ---------------------------------------------------------------- script writer

def rebuild_script(data, stem, texts, ascii_text=False, grow=0):
    """New file bytes with section 7 rebuilt from `texts` ({id: str}); `grow` appends no-op padding.

    Only S operands change size: everything else is copied, and the two kinds of stored offset that
    a size change moves are recomputed (s16 relative jumps, routine table s16 offsets)."""
    so, sl = E.sections(data)[-1]
    scr = data[so:so + sl]
    ins = list(E.parse(scr))
    new = bytearray(scr[:E.NROUT * E.RSIZE])          # routine table, offsets patched below
    new_off = {}
    patches = []                                     # (new offset of J operand, target old offset)
    rout = []                                        # (index, new offset)
    for at, op, args in ins:
        new_off[at] = len(new)
        new.append(op)
        i = 0
        for kind, aoff, val in args:
            if kind == 'S':
                eid = f'{stem}:{so + aoff:05x}'
                raw = encode_text(texts.get(eid, sjis.decode(val)), ascii_text)
                new += raw + b'\0'
            elif kind == 'J':
                patches.append((len(new), aoff + 2 + val))
                new += b'\0\0'
            elif kind == 'B':
                new.append(val)
            elif kind == 'W':
                new += val
            elif kind == 'D':
                new += struct.pack('<I', val)
            elif kind == 'N':
                new += val
            i += 1
    new_off[len(scr)] = len(new)                     # a jump to the end of the script is legal
    for pos, target in patches:
        if target not in new_off:
            raise ValueError(f'{stem}: jump to {target:#x} is not an instruction boundary')
        rel = new_off[target] - (pos + 2)
        if not -0x8000 <= rel < 0x8000:
            raise ValueError(f'{stem}: jump at {pos:#x} is out of s16 range')
        struct.pack_into('<h', new, pos, rel)
    for k in range(E.NROUT):
        flags, f2, off, name = struct.unpack_from('<HHh8s', scr, k * E.RSIZE)
        if flags == 0xff and off:
            if off not in new_off:
                raise ValueError(f'{stem}: routine {k} offset {off:#x} is not an instruction boundary')
            rout.append((k, new_off[off]))
    for k, off in rout:
        if not -0x8000 <= off < 0x8000:
            raise ValueError(f'{stem}: routine {k} offset {off:#x} is out of s16 range')
        struct.pack_into('<h', new, k * E.RSIZE + 4, off)
    if grow:
        new += b'\x14' * grow                        # no-op opcode: valid instructions, never reached
    total = E.HDR + sum(struct.unpack_from('<8I', data, 4)[:7]) + len(new)
    out = bytearray(data[:so])
    struct.pack_into('<I', out, 4 + 7 * 4, len(new))
    out += new
    assert len(out) == total, (len(out), total)
    return bytes(out)


def write_script(rel, data, mode='marker', ascii_text=False, grow=0):
    """Rebuild one *MES file from its script/*.json entries."""
    stem = Path(rel).stem
    texts = {}
    for e in entries_of(rel):
        texts[e['id']] = text_for(e, mode)
    return rebuild_script(data, stem, texts, ascii_text, grow)


# ---------------------------------------------------------------- exe writer

def rebuild_exe(data, texts):
    """Overwrite each text string in place, NUL-padded to its original length (no relocation yet)."""
    out = bytearray(data)
    strings, _ = X.segment(data)
    wrote = 0
    for s, e in strings:
        eid = f'exe:{s:05x}'
        if eid not in texts:
            continue
        raw = sjis.encode(texts[eid])
        if len(raw) > e - s:
            raise ValueError(f'{eid}: {len(raw)} bytes does not fit the {e - s}-byte field')
        out[s:e] = raw + b'\0' * (e - s - len(raw))
        wrote += 1
    return bytes(out), wrote


def write_exe(data, mode='marker'):
    texts = {e['id']: text_for(e, mode) for e in entries_of(EXE)}
    return rebuild_exe(data, texts)


# ---------------------------------------------------------------- staging

def _redirect(layout, rel, source):
    """Point one `<file>` line of the layout at `source`, matched inside its own `<dir>` (ROOMES75.BIN
    exists in both ROOMMES2 and ROOMMES3)."""
    want_dir, want_name = Path(rel).parent.name, Path(rel).name
    lines = layout.splitlines()
    stack, hit = [], None
    for i, line in enumerate(lines):
        m = re.search(r'<dir name="([^"]+)"', line)
        if m and not line.rstrip().endswith('/>'):
            stack.append(m.group(1))
        if (hit is None and f'<file name="{want_name}" type="data"' in line
                and (stack[-1] == want_dir if stack else want_dir == '')):
            hit = i
        if '</dir>' in line and stack:
            stack.pop()
    if hit is None:
        raise SystemExit(f'layout: no <file name="{want_name}"> in <dir name="{want_dir}">')
    lines[hit] = lines[hit].replace(f'<file name="{want_name}"',
                                    f'<file name="{want_name}" source="{source}"', 1)
    return '\n'.join(lines) + '\n'


def stage(tag, mode, only=None, grow=None, ascii_text=False):
    """Write every changed file into work/stage/<tag>/tree and a layout.xml that points at them.

    The disc tree stays untouched (the identity test repacks it), so the layout copies the original
    and only redirects the files this build changes. mkpsxiso resolves relative paths against the
    XML file's own directory, so the generated layout uses absolute paths."""
    layout = (DISC / 'layout.xml').read_text(encoding='utf-8')
    root = ROOT.as_posix()
    layout = layout.replace('<directory_tree source="tree">', f'<directory_tree source="{root}/work/disc/tree">')
    layout = layout.replace('file="tree/license_data.dat"', f'file="{root}/work/disc/tree/license_data.dat"')
    layout = layout.replace('source="tree/', f'source="{root}/work/disc/tree/')
    files = []
    for rel, path in script_files():
        if only and not fnmatch.fnmatch(rel, only):
            continue
        data = path.read_bytes()
        g = (grow or {}).get(Path(rel).name, 0)
        new = write_script(rel, data, mode, ascii_text, g)
        if new != data:
            files.append((rel, new))
    exe = (TREE / EXE).read_bytes()
    new, wrote = write_exe(exe, mode)
    files.append((EXE, new))
    dest_root = STAGE / tag
    if dest_root.exists():
        for p in dest_root.rglob('*'):
            if p.is_file():
                p.unlink()
    for rel, new in files:
        dest = dest_root / 'tree' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(new)
        layout = _redirect(layout, rel, dest.as_posix())
    dest_root.mkdir(parents=True, exist_ok=True)
    lp = dest_root / 'layout.xml'
    lp.write_text(layout, encoding='utf-8', newline='\n')
    return lp, files


# ---------------------------------------------------------------- cli

def cmd_roundtrip(a):
    """rebuild every file from its own jp: byte-identical, or the writer is wrong."""
    bad = []
    for rel, path in script_files():
        data = path.read_bytes()
        if a.only and not fnmatch.fnmatch(rel, a.only):
            continue
        new = write_script(rel, data, 'jp')
        if new != data:
            bad.append(rel)
    exe = (TREE / EXE).read_bytes()
    new, _ = rebuild_exe(exe, {e['id']: e['jp'] for e in entries_of(EXE)})
    if new != exe:
        bad.append(EXE)
    for b in bad[:10]:
        print(f'FAIL {b} differs from the original')
    print(f'roundtrip: {len(script_files()) + 1 - len(bad)}/{len(script_files()) + 1} files identical')
    return 1 if bad else 0


def cmd_stage(a):
    grow = dict(kv.split('=') for kv in a.grow)
    only = a.only
    lp, files = stage(a.tag, a.mode, only, {Path(k).name: int(v) for k, v in grow.items()}, a.ascii_text)
    print(f'stage {a.tag}: {a.mode}, {len(files)} files -> {lp.parent}')
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog='insert.py', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('roundtrip', help='rebuild every file from its own jp and compare')
    r.add_argument('--only', help='glob over source paths')
    r.set_defaults(fn=cmd_roundtrip)
    s = sub.add_parser('stage', help='write changed files + a layout.xml into work/stage/TAG')
    s.add_argument('tag')
    s.add_argument('mode', choices=('marker', 'torture', 'ruler', 'en', 'jp'))
    s.add_argument('--only', help='glob over source paths (the exe is always staged)')
    s.add_argument('--grow', action='append', default=[], metavar='FILE=N',
                   help='append N no-op bytes to that file\'s script (heap-headroom spike)')
    s.add_argument('--ascii-text', action='store_true',
                   help='encode `en` with the printer rules (done for real English, not jp/markers)')
    s.set_defaults(fn=cmd_stage)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
