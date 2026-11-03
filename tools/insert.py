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
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import exestr as X  # noqa: E402
import extract  # noqa: E402
import gfx  # noqa: E402
import sjis  # noqa: E402
import wrap  # noqa: E402

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


# Memory-card save title (exe 0x1f2c0): the BIOS card manager draws it, and it reads Shift-JIS only.
# 03618 is copied as a fixed 29-byte literal (lw/sw) and then overwritten, and already says
# ＢＯＵＮＤＡＲＹ－ＧＡＴＥ; 03658/0365c are the full-width space and colon of the play time.
CARD_KEEP = {'exe:03618', 'exe:03658', 'exe:0365c'}
CARD_FULLWIDTH = {'exe:03638'}


def fullwidth(text):
    """ASCII -> full-width Shift-JIS forms, printf specifiers kept as they are."""
    out, i = [], 0
    while i < len(text):
        m = re.match(r'%[-+ 0#]*\d*l?[sdcx]', text[i:])
        if m:
            out.append(m.group(0))
            i += m.end()
            continue
        c = text[i]
        out.append('　' if c == ' ' else chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c)
        i += 1
    return ''.join(out)


# Layout-only formats (kind 'keep', no Japanese) that change for English.
FORMAT_EN = {
    # items-menu party box (19 cells): the JP's one-kanji statuses 毒/眠/黙 (%2s) become Psn/Slp/Sil
    'exe:00b28': '%-10s  %3d/%3d\n%-4s%-4s%-4s%3d/%3d',
}
# Short copies of a shared string for one reader: (text, id of the string it replaces there, addiu
# offsets whose low half pointed at it). The items-menu party box reads 毒 through 0x152c8 while the
# field menu and battle read the same string as 'Poison'.
EXTRA_STRINGS = [('Psn', 'exe:00abc', [0x152c8])]


def en_exe(entry):
    """English for an exe string as the build writes it."""
    eid, jp, en = entry['id'], entry['jp'], entry['en']
    if eid in FORMAT_EN:
        return FORMAT_EN[eid]
    if not en or eid in CARD_KEEP:
        return jp
    if eid in CARD_FULLWIDTH:
        return fullwidth(en)
    if jp != jp.rstrip(' 　') and en == en.rstrip(' '):
        # JP pads the field with spaces (location names, 24 cells): keep the padding, it clears the
        # previous name on screen and lines up the play time in the card title
        en = en + ' ' * max(0, wrap.cells(jp) - wrap.cells(en.replace('::', ':')))
    return en


def en_script(entry, prev_op, page=wrap.PAGE):
    """English for a script S operand: dialogue (0x22) gets the window layout (wrap.layout)."""
    en = entry['en']
    if not en:
        return entry['jp']
    if entry['op'] == '22':
        return wrap.layout(en, wrap.rows_budget(prev_op), quote=wrap.continues_quote(entry['jp']), page=page)[0]
    return en


def text_for(entry, mode, prev_op=None, page=wrap.PAGE):
    """The replacement text for one entry in `mode` = marker|torture|ruler|en|jp. `page`: the break the layout
    adds when English overflows a page (wrap.TIMED_PAGE in files that never wait for a button)."""
    if mode == 'en' and entry['id'] in FORMAT_EN:
        return FORMAT_EN[entry['id']]
    if mode == 'jp' or entry['kind'] != 'text':
        return entry['jp']
    if mode == 'en':
        return en_exe(entry) if entry['id'].startswith('exe:') else en_script(entry, prev_op, page)
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

def _vtime(b):
    """Op 0x4a operand (minutes, seconds, 1/100 s: the voice position the script waits for) -> centiseconds."""
    return (b[0] * 60 + b[1]) * 100 + b[2]


def _voiced_pages(text, t0, t1, ascii_text):
    """Operand bytes for an op-0x22 text split at wrap.TIMED_PAGE in a voiced event, where the window only shows
    once the print op returns (an in-text wait would hide every page but the last): page 1, then for each next
    page `0x4a time` (voice position, interpolated by text length between the previous 0x4a and the next),
    `0x22 clear`, `0x22 page`. The op byte of the first page is already written by the caller."""
    pages = text.split(wrap.TIMED_PAGE)
    weight = [max(1, len(p)) for p in pages]
    out, done = bytearray(), 0
    for j, p in enumerate(pages):
        if j:
            done += weight[j - 1]
            t = t0 + (t1 - t0) * done // sum(weight)
            out += bytes([0x4a, t // 6000, t // 100 % 60, t % 100, 0x22, 0x08, 0, 0x22])
        out += encode_text(p, ascii_text) + b'\0'
    return bytes(out)


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
    voice_t = 0                                      # last op 0x4a time in the voiced events
    for k, (at, op, args) in enumerate(ins):
        new_off[at] = len(new)
        new.append(op)
        if op == 0x4a:
            voice_t = _vtime(args[0][2])
        i = 0
        for kind, aoff, val in args:
            if kind == 'S':
                eid = f'{stem}:{so + aoff:05x}'
                text = texts.get(eid, sjis.decode(val))
                nxt = ins[k + 1] if k + 1 < len(ins) else None
                if op == 0x22 and wrap.TIMED_PAGE in text and nxt and nxt[1] == 0x4a \
                        and _vtime(nxt[2][0][2]) > voice_t:
                    new += _voiced_pages(text, voice_t, _vtime(nxt[2][0][2]), ascii_text)
                else:
                    new += encode_text(text, ascii_text) + b'\0'
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
    texts, prev = {}, None
    entries = entries_of(rel)
    page = wrap.PAGE if any(wrap.WAIT in e['jp'] for e in entries) else wrap.TIMED_PAGE
    for e in entries:
        texts[e['id']] = text_for(e, mode, prev, page)
        if e['kind'] == 'text':          # same rule as lint.units(): op of the previous text entry
            prev = e['op']
    return rebuild_script(data, stem, texts, ascii_text, grow)


# ---------------------------------------------------------------- exe writer

def _head(data, s):
    """Start of the string as code sees it: the extractor drops leading printer controls ('\\n%s...')."""
    h = s
    while data[h - 1] == 0x0A:
        h -= 1
    return h if data[h - 1] == 0 else s      # other bytes before a string are data (0xc11: 02 01 03)


def _put(out, off, raw, by, orig, log):
    if log is not None:
        log.append(f'{off:X} {orig[off:off + len(raw)].hex()} {raw.hex()} {by}')
    out[off:off + len(raw)] = raw


def _movable(data, where, addr):
    """Every reference to a string head is a pointer word or a `lui 0x8001` + addiu/ori low half."""
    if not where:
        return False
    for kind, o in where:
        if kind != 'table':
            ins = struct.unpack_from('<I', data, o)[0]
            if ins >> 26 not in (0x09, 0x0D) or (ins & 0xFFFF) != (addr & 0xFFFF):
                return False
    return True


def _place(data, slots):
    """Free spans from `slots` and a best-fit placement of the strings marked to move.
    Returns (placed, spans): placed = [(slot, at)] or None when one does not fit."""
    free = []
    for eid, s, e, h, end, raw, where, move in slots:
        if move:
            free.append((h, end))
        elif raw != data[s:e] and len(raw) + 1 < end - s:
            free.append((s + len(raw) + 1, end))
    spans = []
    for a, b in sorted(free):
        if spans and spans[-1][1] == a:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    merged = [tuple(sp) for sp in spans]
    placed = []
    for sl in sorted((sl for sl in slots if sl[7]), key=lambda sl: -(sl[1] - sl[3] + len(sl[5]) + 1)):
        n = sl[1] - sl[3] + len(sl[5]) + 1
        fit = [sp for sp in spans if sp[1] - sp[0] >= n]
        if not fit:
            return None, merged
        sp = min(fit, key=lambda x: x[1] - x[0])
        placed.append((sl, sp[0]))
        sp[0] += n
    return placed, [tuple(sp) for sp in spans]


def rebuild_exe(data, texts, log=None, extras=None):
    """Write each text string in place when it fits its slot, else relocate it inside the text region.

    A slot is the string's bytes plus the NUL padding up to the next 4-byte boundary (never past the
    next string). Strings that do not fit move into the space the others free: the tail of a slot
    whose English is shorter, and the whole slot of a string that moved. Every target stays inside
    0x80010000-0x80014F00, so a `lui 0x8001` / `addiu lo` reference only needs its low half changed;
    pointer words are rewritten whole. A string with no reference at its head cannot move (an error).
    `log` collects one `OFFSET ORIG NEW writer` line per write for romdiff.py --writes."""
    out = bytearray(data)
    strings, _ = X.segment(data)
    refs = X.refs(data)
    heads = [_head(data, s) for s, _ in strings]
    slots, wrote = [], 0           # [eid, s, e, h, end, raw, refs-or-None, must_move]
    for i, (s, e) in enumerate(strings):
        eid = f'exe:{s:05x}'
        if eid not in texts:
            continue
        nxt = heads[i + 1] if i + 1 < len(strings) else X.REGION[1]
        end = e
        while end < min(nxt, (e + 4) & ~3) and data[end] == 0:
            end += 1
        raw = sjis.encode(texts[eid])
        wrote += 1
        cap = end - s - 1 if end > e else e - s          # end == e: the original has no NUL either
        h = heads[i]
        where = refs.get(X.ram(h)) if _movable(data, refs.get(X.ram(h)), X.ram(h)) else None
        if len(raw) > cap and where is None:
            raise ValueError(f'{eid}: {len(raw)} bytes does not fit {cap} and nothing points at it')
        slots.append([eid, s, e, h, end, raw, where, len(raw) > cap])
    # Moving strings that fit too merges the free spans around them; take the smallest such string
    # between two free spans until every string that must move has a place (best fit, largest first).
    while True:
        placed, spans = _place(data, slots)
        if placed is not None:
            break
        free = {a: b for a, b in spans}
        ends = {b: a for a, b in spans}
        best = None
        for sl in slots:
            eid, s, e, h, end, raw, where, move = sl
            if move or where is None or raw == data[s:e]:
                continue
            used = s + len(raw) + 1 if len(raw) + 1 < end - s else end
            gain = (h - ends[h] if h in ends else 0) + (free[used] - used if used in free else 0)
            if gain and (best is None or (gain, -len(raw)) > best[0]):
                best = ((gain, -len(raw)), sl)
        if best is None:
            raise ValueError(f'exe text region full: {spans}')
        best[1][7] = True
    for sl in slots:
        eid, s, e, h, end, raw, where, move = sl
        if not move and raw != data[s:e]:
            _put(out, s, raw + (b'\0' if len(raw) < end - s else b''), eid, data, log)
    spans = [list(sp) for sp in spans]
    own = {o for _, _, sites in (extras or []) for o in sites}
    for text, of, sites in (extras or []):              # short copies for one reader (EXTRA_STRINGS)
        blob = sjis.encode(text) + b'\0'
        sp = min((sp for sp in spans if sp[1] - sp[0] >= len(blob)), key=lambda x: x[1] - x[0])
        at, sp[0] = sp[0], sp[0] + len(blob)
        _put(out, at, blob, f'{of} short copy', data, log)
        old = X.ram(int(of[4:], 16))
        for o in sites:
            ins = struct.unpack_from('<I', data, o)[0]
            assert ins >> 26 == 0x09 and ins & 0xFFFF == old & 0xFFFF, (of, hex(o))
            _put(out, o, struct.pack('<I', (ins & 0xFFFF0000) | (X.ram(at) & 0xFFFF)), f'{of} short lo16',
                 data, log)
    for a, b in spans:                                   # what is left of the freed space: zeros
        for k in range(a, b):
            if data[k]:
                _put(out, k, b'\0', 'clear', data, log)
    for (eid, s, e, h, end, raw, where, _), at in placed:
        _put(out, at, data[h:s] + raw + b'\0', eid + ' moved', data, log)
        new = X.ram(at)
        assert new >> 16 == X.ram(h) >> 16 == 0x8001 and new & 0x8000 == 0
        for kind, o in where:
            if o in own:
                continue                                  # this reader gets its EXTRA_STRINGS copy
            if kind == 'table':
                assert struct.unpack_from('<I', data, o)[0] == X.ram(h)
                _put(out, o, struct.pack('<I', new), f'{eid} ptr', data, log)
            else:
                ins = struct.unpack_from('<I', data, o)[0]
                _put(out, o, struct.pack('<I', (ins & 0xFFFF0000) | (new & 0xFFFF)), f'{eid} lo16', data, log)
    return bytes(out), wrote, [(sl[0], sl[3], at) for sl, at in placed]


# Engine patches for English (en build only): (file offset of an `addiu rX, $zero, imm`, old imm, new imm,
# why). openwindow(x px, y px, w cells, h rows) arguments, listed by tools/windows.py; docs/re/windows.md.
_CMD = 'command window (Talk/Move/Status, Fight/Run/Weapon/Magic/Items/Status, Buy/Sell): 6 -> 8 cells'
_COL = 'field-menu column / submenu title box: 4 -> 6 cells (Items, Magic, Equip, Status, Map, Config)'
_TOP = 'top-row box right of the title box: 12 px right, 2 cells narrower (same right edge)'
EXE_PATCHES = [
    *[(o, 4, 6, _COL) for o in (0x15a68, 0x16694, 0x174a0, 0x18ba8, 0x19088, 0x1a1bc, 0x1a1f8)],
    *[(o, 58, 70, _TOP) for o in (0x15ac0, 0x166dc, 0x174f8, 0x19c64, 0x1a2bc)],
    *[(o, 41, 39, _TOP) for o in (0x15ac8, 0x166e4, 0x17500, 0x19c6c, 0x1a2c4)],
    (0x18c00, 56, 68, _TOP), (0x18c08, 42, 40, _TOP), (0x190e0, 56, 68, _TOP), (0x190e8, 42, 40, _TOP),
    (0x17ccc, 4, 6, _COL), (0x17d24, 56, 68, _TOP), (0x17d2c, 41, 39, _TOP),    # status (0x80021414)
    # columns drawn over a top box keep their distance from its (moved) labels
    (0x1752c, 108, 120, 'equip: equipped-item column right of Weapon:/Armour:/Shield:/Extra:'),
    (0x17538, 30, 28, 'equip: equipped-item column, same right edge'),
    (0x18c38, 140, 152, 'config: value column right of "Battle Scenes" (13 cells)'),
    (0x18c40, 28, 26, 'config: value column, same right edge'),
    # equip: stat-compare box 13 -> 15 cells ('Defence::%3d>%3d'), the list box left of it 2 cells less
    (0x175b4, 226, 214, 'equip compare box: 12 px left'), (0x175c0, 13, 15, 'equip compare box: 13 -> 15 cells'),
    (0x1759c, 218, 206, 'equip compare box (background)'),
    (0x1757c, 32, 30, 'equip list box: 2 cells less, room for the compare box'),
    *[(o, 6, 8, _CMD) for o in (0x0fa20, 0x1c46c, 0x1dd38, 0x1fd7c, 0x22dac)],
    *[(o, 12, 6, _CMD + ', 6 px further left') for o in (0x0fa18, 0x1c464, 0x1dd30, 0x1fd74, 0x22d7c)],
    # window backgrounds (ITA_1.TIM sprites, tools/windows.py `sprite`): x of the top-row boxes
    *[(o, 50, 62, _TOP + ' (background)') for o in (0x15a98, 0x166c0, 0x174e4, 0x1a28c, 0x19c3c)],
    *[(o, 48, 60, _TOP + ' (background)') for o in (0x17d10, 0x18be8, 0x190c8)],
]
_BG = 'window background rect {u, v, w, h}'
# Data halfwords: (file offset, old, new, why). Background rects live in the text region's data gaps
# (relocation never moves those) and in .data (0x80074cb8: the field menu's top box, copied at run time).
HALF_PATCHES = [
    *[(o, 40, 52, f'{_BG}: {_COL}') for o in (0x0b78, 0x1024, 0x102c)],
    *[(o, 262, 250, f'{_BG}: {_TOP}') for o in (0x0b80, 0x0cbc, 0x0dc8, 0x654bc, 0x654c4)],
    *[(o, 268, 256, f'{_BG}: {_TOP}') for o in (0x0e78, 0x0edc)],
    *[(o, 48, 60, f'{_BG}: {_TOP} (u follows x)') for o in (0x0e74, 0x0ed8)],
    (0x0cc4, 208, 196, f'{_BG}: equip list box'), (0x0ccc, 94, 106, f'{_BG}: equip compare box'),
]


def patch_exe(out, orig, log=None, patches=EXE_PATCHES, halves=HALF_PATCHES):
    """Apply EXE_PATCHES (each must be `addiu rX, $zero, old` in the original) and HALF_PATCHES (each
    must hold `old`), or the build fails."""
    for o, old, new, why in patches:
        ins = struct.unpack_from('<I', orig, o)[0]
        if ins >> 26 != 0x09 or (ins >> 21) & 31 or (ins & 0xFFFF) != old & 0xFFFF:
            raise ValueError(f'exe patch at {o:#x}: {ins:08x} is not addiu rX, $zero, {old} ({why})')
        _put(out, o, struct.pack('<I', (ins & 0xFFFF0000) | (new & 0xFFFF)), f'patch {why}', orig, log)
    for o, old, new, why in halves:
        if struct.unpack_from('<H', orig, o)[0] != old:
            raise ValueError(f'exe data patch at {o:#x}: not {old} ({why})')
        _put(out, o, struct.pack('<H', new), f'patch {why}', orig, log)


def stale_refs(data, moved, window=16):
    """References to a moved string's old head that the build did not rewrite: `lui r, 0x8001` and,
    up to `window` instructions later, any immediate use of the old low half on r (addiu/ori, a load
    or store: a literal copied by lw). exestr.refs() only pairs instructions 2 apart, so this is the
    wider net. Returns [(eid, file offset, instruction word)]."""
    old = {X.ram(h) & 0xFFFF: eid for eid, h, _ in moved}
    hits, lui = [], {}
    for o in range(0x800, len(data) - 3, 4):
        ins = struct.unpack_from('<I', data, o)[0]
        op, rs, rt, imm = ins >> 26, (ins >> 21) & 31, (ins >> 16) & 31, ins & 0xFFFF
        if op == 0x0F:                                   # lui rt, imm
            if imm == 0x8001:
                lui[rt] = o
            else:
                lui.pop(rt, None)
            continue
        uses = op in (0x09, 0x0D) or 0x20 <= op <= 0x2E      # addiu/ori, loads/stores
        if uses and rs in lui and o - lui[rs] <= 4 * window and imm in old:
            hits.append((old[imm], o, ins))
    return hits


def write_exe(data, mode='marker', log=None):
    texts = {e['id']: text_for(e, mode) for e in entries_of(EXE)}
    new, wrote, moved = rebuild_exe(data, texts, log, EXTRA_STRINGS if mode == 'en' else None)
    if mode == 'en':
        out = bytearray(new)
        patch_exe(out, data, log)
        new = bytes(out)
    return new, wrote, moved


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
    log = []
    new, wrote, moved = write_exe(exe, mode, log)
    done = {int(line.split()[0], 16) for line in log if line.endswith(' lo16')}
    stale = [x for x in stale_refs(exe, moved) if x[1] not in done]
    if stale:
        raise SystemExit('moved exe strings keep unrewritten readers: '
                         + ', '.join(f'{eid} at {o:#x} ({ins:08x})' for eid, o, ins in stale[:20]))
    files.append((EXE, new))
    if mode == 'en':
        files.append((gfx.TITLE, gfx.title_en((TREE / gfx.TITLE).read_bytes())))
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
    # write log for romdiff.py --writes, and where each relocated string went
    (dest_root / 'exe_writes.txt').write_text('\n'.join(log) + '\n', encoding='utf-8', newline='\n')
    (dest_root / 'exe_moved.txt').write_text(
        ''.join(f'{eid} {h:05x} -> {at:05x}\n' for eid, h, at in sorted(moved)), encoding='utf-8', newline='\n')
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
    new = rebuild_exe(exe, {e['id']: e['jp'] for e in entries_of(EXE)})[0]
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
