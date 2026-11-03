"""List every openwindow() call in the exe with its constant arguments (docs/re/windows.md).

openwindow = 0x80021530 (the routine that prints 'openwindow: xmalloc error!!'). For each `jal` to it the
scan walks back up to 24 instructions and records the last constant loaded into a1-a3 and stored to the
stack argument slots sp+0x10/0x14/0x1c (`addiu rX, $zero, imm` then `sw rX, off($sp)`). Values loaded
from memory or computed show as '?'.

usage: python -X utf8 tools/windows.py [EXE]
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / 'work' / 'disc' / 'tree' / 'SLPS_009.07'
OPENWINDOW = 0x80021530
BASE = 0x80010000 - 0x800          # RAM of file offset 0
ARGS = (4, 5, 6, 7)
WINDOW2 = 0x80021414    # openwindow variant: (x px, y px, w cells, h rows, ...) in a0-a3


def calls(data, target=OPENWINDOW):
    jal = (0x03 << 26) | ((target >> 2) & 0x03FFFFFF)
    out = []
    for o in range(0x800, len(data) - 3, 4):
        if struct.unpack_from('<I', data, o)[0] != jal:
            continue
        regs, stack, li = {}, {}, {}
        # walk forward over the window before the call (and its delay slot) so later loads win
        for p in range(o - 24 * 4, o + 8, 4):
            ins = struct.unpack_from('<I', data, p)[0]
            op, rs, rt, imm = ins >> 26, (ins >> 21) & 31, (ins >> 16) & 31, ins & 0xFFFF
            simm = imm - 0x10000 if imm & 0x8000 else imm
            if op == 0x0F:                               # lui rt, imm (pointer built with addiu next)
                li[rt] = imm << 16
            elif op == 0x09 and rs == rt and isinstance(li.get(rt), int) and li[rt] >= 0x10000:
                li[rt] = (li[rt] + simm) & 0xFFFFFFFF
                if rt in ARGS:
                    regs[rt] = (li[rt], p)
                continue
            if op == 0x09 and rs == 0:                   # addiu rt, $zero, imm
                li[rt] = simm
                if rt in ARGS:
                    regs[rt] = (simm, p)
            elif op == 0x2B and rs == 29 and imm in (0x10, 0x14, 0x18, 0x1c):   # sw rt, imm($sp)
                stack[imm] = (li.get(rt, '?') if rt else 0, p)
            elif rt in ARGS and op not in (0x2B, 0x28, 0x29, 0x0F) and op:      # a0-a3 written another way
                regs[rt] = ('?', p)
                li.pop(rt, None)
            elif op == 0 and ((ins >> 11) & 31) in ARGS:                       # R-type into a0-a3 (move...)
                regs[(ins >> 11) & 31] = ('?', p)
        out.append((o, {k: v[0] for k, v in regs.items()}, {k: v[0] for k, v in stack.items()},
                    {**{f'a{k - 4}': v[1] for k, v in regs.items()}, **{f'sp{k:x}': v[1] for k, v in stack.items()}}))
    return out


SPRITE = 0x8001A280     # background sprite from a TIM: (img, x px, y px, ?, ?, ?, rect*) rect = {u, v, w, h}
SPRITE2 = 0x8001A4C0    # the same with the rect in a3: (img, x, y, rect*)


def sprites(data):
    """[(call offset, x, y, rect address, (rect halfwords) or None)] for every background sprite call."""
    out = []
    for o, regs, stack, where in calls(data, SPRITE) + [(o, r, {0x18: r.get(7)}, w)
                                                       for o, r, s, w in calls(data, SPRITE2)]:
        r = stack.get(0x18)
        rect = None
        if isinstance(r, int) and 0x80010000 <= r < 0x80200000:
            ro = r - BASE
            rect = struct.unpack_from('<4h', data, ro) if ro + 8 <= len(data) else None
        out.append((o, regs.get(5, '?'), regs.get(6, '?'), r, rect, where))
    return out


def main(argv):
    data = Path(argv[0] if argv else EXE).read_bytes()
    for o, x, y, r, rect, where in sprites(data):
        rs = f'{r:08x}' if isinstance(r, int) else r
        print(f'sprite {o:06x}  x={x!s:>4} y={y!s:>4} rect@{rs} {rect}  at x:{where.get("a1", 0):06x}')
    for o, regs, stack, where in calls(data, WINDOW2):
        print(f'win2   {o:06x}  x={regs.get(4, "?")!s:>4} y={regs.get(5, "?")!s:>4} w={regs.get(6, "?")!s:>4} '
              f'h={regs.get(7, "?")!s:>4}  at x:{where.get("a0", 0):06x} w:{where.get("a2", 0):06x}')
    for o, regs, stack, where in calls(data):
        print(f'{o:06x} {BASE + o:08x}  x={regs.get(5, "?")!s:>4} y={regs.get(6, "?")!s:>4} '
              f'w={regs.get(7, "?")!s:>4} h={stack.get(0x10, "?")!s:>4} s14={stack.get(0x14, "?")!s:>3} '
              f's1c={stack.get(0x1c, "?")!s:>3}  at x:{where.get("a1", 0):06x} y:{where.get("a2", 0):06x} '
              f'w:{where.get("a3", 0):06x}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
