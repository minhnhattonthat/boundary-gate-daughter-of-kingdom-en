"""Measure the operand length of each event-script opcode by running its handler under unicorn.

usage: python -X utf8 tools/re_ops.py RAM.bin [--op 22] [--fill 00] [--bytes HEX]

RAM.bin: a 2 MB main-RAM dump taken in game (emu.py + probes/ramdump.lua), so handlers see real state.
For each opcode the handler (table at 0x8005224C, 0x56 entries, dispatcher 0x8002056C) is called with the script
pointer (0x800CF250) aimed at a buffer holding the operand bytes. Reports which buffer offsets the handler (and its
callees) read, and where the script pointer ended. ptr != max_read+1 means a jump or a variable-length operand.
"""
import argparse, struct, sys
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_MEM_READ, UC_HOOK_CODE, UcError
from unicorn.mips_const import (UC_MIPS_REG_RA, UC_MIPS_REG_SP, UC_MIPS_REG_GP, UC_MIPS_REG_PC, UC_MIPS_REG_V0,
                                UC_MIPS_REG_ZERO)

TABLE, NOPS, SPTR, GP = 0x8005224C, 0x56, 0x800CF250, 0x800CA958
BUF, MAGIC = 0x801E0000, 0x80001000   # BUF: a scratch area; MAGIC: return address, never executed


LIB = 0x80038000   # code above this is PsyQ library (VSync, DrawSync, CdSync, pad...): waits get stubbed


def run(ram, op, operand, limit=400000):
    """Run handler; on a wait loop, stub the innermost library function being waited in, and retry."""
    stubs = set()
    for _ in range(12):
        r = run1(ram, op, operand, limit, stubs)
        if not r[1].startswith('limit') or r[4] is None or r[4] in stubs:
            return r[:4] + (sorted(stubs),)
        stubs.add(r[4])
    return r[:4] + (sorted(stubs),)


def run1(ram, op, operand, limit, stubs):
    mu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 + UC_MODE_LITTLE_ENDIAN)
    # unicorn translates kseg0 (0x80xxxxxx) to physical for execution, but its host API takes physical addresses
    P = lambda a: a & 0x1FFFFFFF
    mu.mem_map(0, 0x200000)
    mu.mem_write(0, ram)
    mu.mem_map(0x1F800000, 0x10000)   # scratchpad + I/O, as plain RAM
    mu.mem_write(P(BUF), operand)
    mu.mem_write(P(SPTR), struct.pack('<I', BUF))
    handler = struct.unpack_from('<I', ram, P(TABLE) + op * 4)[0]
    reads = set()

    def on_read(uc, acc, addr, size, val, ud):
        o = P(addr) - P(BUF)
        if 0 <= o < len(operand):
            reads.update(range(o, o + size))
    mu.hook_add(UC_HOOK_MEM_READ, on_read)
    stack = []   # shadow call stack of function entry addresses

    def on_code(uc, addr, size, ud):
        if addr in stubs:   # stubbed wait: return 0 at once
            uc.reg_write(UC_MIPS_REG_V0, 0)
            uc.reg_write(UC_MIPS_REG_PC, uc.reg_read(UC_MIPS_REG_RA))
            return
        w = struct.unpack('<I', uc.mem_read(P(addr), 4))[0]
        if w >> 26 == 3:                                   # jal
            stack.append((((addr + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2), addr + 8))
        elif w >> 26 == 0 and w & 0x3F == 9:               # jalr
            stack.append((uc.reg_read(UC_MIPS_REG_ZERO + ((w >> 21) & 31)), addr + 8))
        while stack and stack[-1][1] == addr:              # returned
            stack.pop()
    mu.hook_add(UC_HOOK_CODE, on_code)
    mu.reg_write(UC_MIPS_REG_RA, MAGIC)
    mu.reg_write(UC_MIPS_REG_SP, 0x801FF000)
    mu.reg_write(UC_MIPS_REG_GP, GP)
    status = 'ret'
    try:
        mu.emu_start(handler, MAGIC, count=limit)
    except UcError as e:
        status = 'err:' + str(e)
    end = struct.unpack('<I', mu.mem_read(P(SPTR), 4))[0] - BUF
    wait = None
    if status == 'ret' and mu.reg_read(UC_MIPS_REG_PC) != MAGIC:
        status = 'limit@%08x' % mu.reg_read(UC_MIPS_REG_PC)
        # stub the outermost library function on the stack (the game's call into the waiting library code)
        libs = [f for f, _ in stack if f >= LIB]
        wait = libs[0] if libs else (stack[-1][0] if stack else None)
    return handler, status, sorted(r for r in reads if r >= 0), end, wait


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ram')
    ap.add_argument('--op', type=lambda s: int(s, 16))
    ap.add_argument('--fill', default='00')
    ap.add_argument('--bytes', default='')
    a = ap.parse_args()
    ram = open(a.ram, 'rb').read()
    operand = bytes.fromhex(a.bytes) + bytes([int(a.fill, 16)]) * 64
    ops = [a.op] if a.op is not None else range(NOPS)
    for op in ops:
        h, st, reads, end, stubs = run(ram, op, operand)
        mx = max(reads) + 1 if reads else 0
        flag = '' if end == mx else ' *'
        sb = ' stubs=' + ','.join('%08x' % s for s in stubs) if stubs else ''
        print(f'{op:02x} {h:08x} {st:6s} read={mx:3d} ptr={end:+5d}{flag}  offs={reads[:12]}{sb}')


if __name__ == '__main__':
    sys.exit(main())
