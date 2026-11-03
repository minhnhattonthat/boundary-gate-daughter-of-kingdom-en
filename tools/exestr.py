"""SLPS_009.07 text region: segment file 0x800-0x5700 (RAM 0x80010000-0x80014F00) into strings and
data, and find the references that reach it (docs/re/text.md).

Why a scanner and not just pointers: the region holds four kinds of string and only some are in a table.
  * strings a pointer table or code addresses (item/monster/map names, menu labels);
  * strings reached through `lui`+`addiu` pairs whose base is a shared block (credits, prologue);
  * print formats like ':%c%-20s %-6s  所持数 %2d' (Japanese words inside a printf format: text, needs
    translating around the specifiers);
  * engine strings (paths, malloc errors, ASCII credits) that stay as they are.
A byte scan alone cannot tell text from a float that happens to decode, so:
  * a run containing a full-width character is a string (random data rarely forms valid kanji pairs);
  * an ASCII or half-width-kana run is a string only when a reference reaches it or it is at least 3
    bytes and looks like a word/path/format - short runs of stray printable data bytes are marked as data.

segment() returns (strings, gaps) that tile REGION exactly; docs/tests/test_extract.py checks that tile.
"""
import struct

import capstone

REGION = (0x800, 0x5700)          # file offsets of the text region
RAM = 0x80010000                  # RAM address of file offset 0x800
HALF_CH = 0xFF61


def ram(off):
    return RAM + off - 0x800


def off(addr):
    return addr - RAM + 0x800


def _lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def _trail(b):
    return 0x40 <= b <= 0x7E or 0x80 <= b <= 0xFC


def char_len(data, i):
    """Length in bytes of the text character at i, or 0 when the byte cannot be part of one."""
    b = data[i]
    if 0x01 <= b <= 0x1F or 0x20 <= b <= 0x7E or 0xA1 <= b <= 0xDF:
        return 1
    if _lead(b) and i + 1 < len(data) and _trail(data[i + 1]):
        try:
            data[i:i + 2].decode('cp932')
        except UnicodeDecodeError:
            return 0
        return 2
    return 0


def runs(data, start=None, end=None):
    """Maximal runs of text bytes in [start,end), as (off,end). A printer control byte (0x01-0x1F) is
    part of a string but cannot start one: lengths and embedded newlines live inside the S operand."""
    start, end = start or REGION[0], end or REGION[1]
    out, i, cur = [], start, None
    while i < end:
        n = char_len(data, i)
        if cur is None and n and not 0x01 <= data[i] <= 0x1F:
            cur = [i, i + n]
            i += n
            continue
        if cur is not None and n and i + n <= end:
            cur[1] = i + n
            i += n
            continue
        if cur:
            out.append(tuple(cur))
            cur = None
        i += 1
    if cur:
        out.append(tuple(cur))
    return out


def wide(raw):
    """True when the run has a full-width glyph (kanji/kana/full-width punctuation): not random data."""
    text = raw.decode('cp932', 'replace')
    return any(ord(c) > 0x7E and not (HALF_CH <= ord(c) <= 0xFF9F) for c in text)


def _refs_word(data):
    refs = {}
    for o in range(0x800, len(data) - 3, 4):
        w = struct.unpack_from('<I', data, o)[0]
        if RAM + REGION[0] - 0x800 <= w < RAM + REGION[1] - 0x800:
            refs.setdefault(w, []).append(('table', o))
    return refs


def _reg(s):
    return s.strip()


def _imm(s):
    s = s.strip()
    try:
        return int(s, 0)
    except ValueError:
        return None


def _refs_code(data):
    """`lui rt, hi` then, at most two instructions later and on the same register, `addiu rt, rt, lo`,
    `ori rt, rt, lo` or `lw rt, lo(rt)`: the PS1 way of loading an address. skipdata keeps the sweep on
    the 4-byte grid through data so real code after a data island is still decoded."""
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 | capstone.CS_MODE_LITTLE_ENDIAN)
    md.skipdata = True
    refs, pending = {}, None
    for idx, ins in enumerate(md.disasm(data[0x800:], RAM)):
        m, ops = ins.mnemonic, ins.op_str.split(', ')
        if m == 'lui' and len(ops) == 2:
            hi = _imm(ops[1])
            if hi is not None:
                pending = (idx, _reg(ops[0]), hi << 16, ins.address)
            continue
        if pending is None:
            continue
        if idx - pending[0] > 2:
            pending = None
            continue
        base_addr = None
        if m in ('addiu', 'ori', 'daddiu') and len(ops) == 3 and _reg(ops[0]) == pending[1] == _reg(ops[1]):
            lo = _imm(ops[2])
            if lo is not None:
                base_addr = pending[2] + ((lo & 0xFFFF) - 0x10000 if lo & 0x8000 else lo & 0xFFFF)
        elif m in ('lw', 'lb', 'lbu', 'lh', 'lhu') and len(ops) == 2:
            memo, _, rest = ops[1].partition('(')
            disp, reg = _imm(memo), _reg(rest.rstrip(')'))
            if disp is not None and reg == pending[1]:
                lo = disp & 0xFFFF
                base_addr = pending[2] + (lo - 0x10000 if lo & 0x8000 else lo)
        if base_addr is not None:
            if RAM + REGION[0] - 0x800 <= base_addr < RAM + REGION[1] - 0x800:
                refs.setdefault(base_addr, []).append(('code', ins.address - RAM + 0x800))
            pending = None
    return refs


def refs(data):
    """RAM address -> list of (kind, file offset of the referrer): pointer tables and code addresses."""
    out = _refs_word(data)
    for addr, where in _refs_code(data).items():
        out.setdefault(addr, []).extend(where)
    return out


def is_string(data, off_, end, addressed):
    """A run is a string when it holds a full-width glyph, or is addressed, or is a word-like ASCII run."""
    raw = data[off_:end]
    if wide(raw):
        return True
    if addressed:
        return True
    if len(raw) >= 3 and any(c in raw for c in (b' ', b'%', b'\\', b'.', b':')) and raw.decode('cp932').isprintable():
        return True
    return False


def segment(data):
    """(strings, gaps): strings = [(off,end)], gaps = [(off,end,reason)]; together they tile REGION."""
    refs_ = refs(data)
    strings, gaps, pos = [], [], REGION[0]
    for s, e in runs(data):
        addressed = any(ram(s) <= a < ram(e) for a in refs_) or ram(s) in refs_
        if not is_string(data, s, e, addressed):
            continue
        if s > pos:
            gaps.append((pos, s, 'data'))
        strings.append((s, e))
        pos = e
    if pos < REGION[1]:
        gaps.append((pos, REGION[1], 'data'))
    return strings, gaps


MAIN = '''usage: python -X utf8 tools/exestr.py EXE [--list] [--stats]
Prints the segmentation of the text region and the reference count for each string.
'''


def main(argv):
    import sys
    exe = argv[0]
    data = open(exe, 'rb').read()
    strings, gaps = segment(data)
    refs_ = refs(data)
    print(f'{len(strings)} strings, {sum(e - s for s, e in strings)} bytes; '
          f'{len(gaps)} data gaps, {sum(e - s for s, e, r in gaps)} bytes')
    for s, e in strings:
        hits = [o for a, w in refs_.items() if ram(s) <= a < ram(e) for _, o in w]
        print(f'{s:04x}-{e:04x} {len(hits):2d} {data[s:e].decode("cp932", "replace")!r}')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
