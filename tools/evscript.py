"""Event-script container and bytecode parser for EVMES/ROOMMES/MAPMES *.BIN (docs/re/script.md).

File: u32 0x20, u32 size[7], u32 script_size, then 8 sections back to back from 0x24; the last is the script.
Script section: 32 routine entries of 14 bytes (u16 flags, u16, s16 offset, char name[8]), then bytecode.
Operand formats per opcode: B = u8, W = 2 bytes, D = 4 bytes, J = s16 jump relative to the next instruction,
S = zero-terminated Shift-JIS/ASCII string, N = n raw bytes.

usage: python -X utf8 tools/evscript.py FILE.. [--dis] [--strings]
"""
import struct, sys, glob

HDR, NSEC, NROUT, RSIZE = 0x24, 8, 32, 14

# derived from the handler table at 0x8005224C (tools/re_ops.py + disassembly); docs/re/script.md
FMT = {
    0x00: 'BDJ', 0x01: 'BDJ', 0x02: 'BDJ', 0x03: 'BDJ', 0x04: 'BDJ', 0x05: 'BDJ',
    0x06: 'BD', 0x07: 'BD', 0x08: 'J', 0x09: 'B', 0x0a: 'B', 0x0b: 'B', 0x0c: 'W', 0x0d: 'B',
    0x0e: 'D', 0x0f: 'BW', 0x10: 'BW', 0x11: 'BW', 0x12: 'B', 0x13: 'N5', 0x14: '', 0x15: 'B',
    0x16: 'D', 0x17: '', 0x18: 'W', 0x19: '', 0x1a: '', 0x1b: 'B', 0x1c: 'BSBBB', 0x1d: 'B',
    0x1e: 'B', 0x1f: 'B', 0x20: 'B', 0x21: 'S', 0x22: 'S', 0x23: 'S', 0x24: '', 0x25: 'SB',
    0x26: '', 0x27: 'SS', 0x28: 'BSB', 0x29: 'B', 0x2a: 'N3', 0x2b: 'N3', 0x2c: 'W', 0x2d: 'W',
    0x2e: 'W', 0x2f: 'B', 0x30: 'B', 0x31: 'N16', 0x32: '', 0x33: 'D', 0x34: '', 0x35: 'D',
    0x36: 'B', 0x37: 'B', 0x38: 'D', 0x39: 'W', 0x3a: 'N5', 0x3b: '', 0x3c: '', 0x3d: '',
    0x3e: '', 0x3f: 'N3', 0x40: 'B', 0x41: 'B', 0x42: '', 0x43: 'B', 0x44: '', 0x45: 'B',
    0x46: 'W', 0x47: 'W', 0x48: '', 0x49: 'D', 0x4a: 'N3', 0x4b: '', 0x4c: '', 0x4d: '',
    0x4e: 'BSBB', 0x4f: 'B', 0x50: '', 0x51: 'B', 0x52: '', 0x53: '', 0x54: 'B', 0x55: '',
}
TEXT_OPS = {0x21, 0x22, 0x23, 0x27, 0x28, 0x4e}   # S operands shown on screen; 0x1c/0x25 carry asset names


def sections(data):
    sizes = struct.unpack_from('<8I', data, 4)
    out, o = [], HDR
    for s in sizes:
        out.append((o, s))
        o += s
    if o != len(data):
        raise ValueError(f'sections end at {o:#x}, file is {len(data):#x}')
    return out


def routines(scr):
    return [struct.unpack_from('<HHh8s', scr, i * RSIZE) for i in range(NROUT)]


def parse(scr, start=NROUT * RSIZE):
    """Linear sweep. Yields (off, op, [operands]) with operand = (kind, off, value). Raises on unknown op."""
    o = start
    while o < len(scr):
        op = scr[o]
        if op not in FMT:
            raise ValueError(f'unknown op {op:#04x} at {o:#x}')
        at, args, f, i = o, [], FMT[op], 0
        o += 1
        while i < len(f):
            k = f[i]
            if k == 'N':
                j = i + 1
                while j < len(f) and f[j].isdigit():
                    j += 1
                n = int(f[i + 1:j]); i = j
                args.append(('N', o, scr[o:o + n])); o += n
                continue
            if k == 'B':
                args.append(('B', o, scr[o])); o += 1
            elif k == 'W':
                args.append(('W', o, scr[o:o + 2])); o += 2
            elif k == 'D':
                args.append(('D', o, struct.unpack_from('<I', scr, o)[0])); o += 4
            elif k == 'J':
                args.append(('J', o, struct.unpack_from('<h', scr, o)[0])); o += 2
            elif k == 'S':
                e = scr.index(b'\0', o)
                args.append(('S', o, scr[o:e])); o = e + 1
            i += 1
        if o > len(scr):
            raise ValueError(f'op {op:#04x} at {at:#x} runs past the end')
        yield at, op, args


def show(s):
    try:
        return s.decode('cp932')
    except UnicodeDecodeError:
        return '<' + s.hex() + '>'


def main(argv):
    dis = '--dis' in argv
    strs = '--strings' in argv
    files = [f for a in argv if not a.startswith('--') for f in sorted(glob.glob(a))]
    bad = 0
    for f in files:
        data = open(f, 'rb').read()
        so, sl = sections(data)[-1]
        scr = data[so:so + sl]
        try:
            ins = list(parse(scr))
        except (ValueError, struct.error) as e:
            print(f'{f}: FAIL {e}')
            bad += 1
            continue
        bounds = {at for at, _, _ in ins} | {len(scr)}
        jbad = [(at, a[2]) for at, op, args in ins for a in args
                if a[0] == 'J' and (args[-1][1] + 2 + a[2]) not in bounds]
        rbad = [(n.rstrip(b'\0'), off) for fl, _, off, n in routines(scr) if fl != 0xff or off or n.strip(b'\0')
                if off not in bounds]
        print(f'{f}: {len(ins)} ops, {sum(op in TEXT_OPS for _, op, _ in ins)} text ops, '
              f'bad jumps {len(jbad)}, bad routine offsets {len(rbad)} {rbad[:4]}')
        bad += bool(jbad)
        if dis or strs:
            for at, op, args in ins:
                if strs and op not in TEXT_OPS:
                    continue
                a = ' '.join(show(v) if k == 'S' else (v.hex() if isinstance(v, bytes) else
                             (f'->{off + 2 + v:#x}' if k == 'J' else f'{v:#x}')) for k, off, v in args)
                print(f'  {at:05x} {op:02x} {a}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
