"""Write gate: every byte a build changes must lie where a committed map allows it (phase 7, docs/re/text.md).

The map is derived from the extraction (script/exe.json) and the engine-patch lists in insert.py, never from
the build's own write log, so a wrong but correctly logged write still fails:
  exe   text slots (string + its NUL padding to the next 4-byte boundary, leading '\\n' printer bytes) of every
        text entry and FORMAT_EN string; the low halfword of every reference to those strings (exestr.refs on
        the original); EXE_PATCHES / HALF_PATCHES / EXTRA_STRINGS sites. On top, romdiff checks the write log
        (original bytes, overlaps, later overwrites), and every logged write must itself lie inside the map.
  *MES  header + sections 0-6 byte-identical except size[7]; the script section re-parses and matches the
        original op for op (same opcodes and non-text operands, jumps and routine offsets land on the
        instruction that was their original target); only extra ops are voiced-page splits after an op 0x22
        (`4a t / 22 08 / 22 page`, t before the next original 0x4a) and trailing 0x14 no-op growth.
  title GRP/TITLE2.TIM: only pixel bytes inside gfx.KANA change.

usage: python -X utf8 tools/gate.py [STAGE_DIR]   (default work/stage/en)"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import evscript as E  # noqa: E402
import exestr as X  # noqa: E402
import extract  # noqa: E402
import gfx  # noqa: E402
import insert  # noqa: E402
import romdiff  # noqa: E402
import tim  # noqa: E402


def exe_allowed(orig):
    """Offsets of the original exe that an English (or QA) build may change."""
    ok = set()
    heads = []
    for e in extract.load(extract.out_path(extract.EXE))['entries']:
        if e['kind'] != 'text' and e['id'] not in insert.FORMAT_EN:
            continue
        s, end = e['off'], e['off'] + e['len']
        while end < (e['off'] + e['len'] + 4) & ~3 and orig[end] == 0:
            end += 1
        h = insert._head(orig, s)
        ok.update(range(h, end))
        heads.append(h)
    refs = X.refs(orig)
    sites = [o for h in heads for _, o in refs.get(X.ram(h), [])]
    sites += [o for _, _, os in insert.EXTRA_STRINGS for o in os]
    sites += [o for o, *_ in insert.EXE_PATCHES] + [o for o, *_ in insert.HALF_PATCHES]
    for o in sites:
        ok.update((o, o + 1))            # low halfword (little-endian): lo16 immediates, data halfwords, 0x8001xxxx words
    return ok


def check_exe(orig, new, writes, allowed=None):
    allowed = exe_allowed(orig) if allowed is None else allowed
    errs, _ = romdiff.check(orig, new, [], writes)           # the log is consistent
    errs += [f'exe {o:#07x}: logged write ({by}) outside the allowed map'
             for o, old, nw, by in writes if any(old[i] != nw[i] and o + i not in allowed for i in range(len(old)))]
    errs += [f'exe: {x}' for x in romdiff.check(orig, new, allowed, [])[0]]   # the map alone covers the diff
    return errs


def check_mes(rel, orig, new):
    """Structural diff of one *MES file (see module doc). Returns error lines."""
    so, sl = E.sections(orig)[-1]
    try:
        nso, nsl = E.sections(new)[-1]
    except ValueError as x:
        return [f'{rel}: {x}']
    size_field = 4 + 7 * 4
    if nso != so or new[:size_field] != orig[:size_field] or new[size_field + 4:so] != orig[size_field + 4:so]:
        return [f'{rel}: header or sections 0-6 changed']
    a, b = orig[so:], new[nso:nso + nsl]
    try:
        old, ins = list(E.parse(a)), list(E.parse(b))
    except ValueError as x:
        return [f'{rel}: script does not parse: {x}']
    where, pair = {}, {}             # original instruction offset -> new offset, new operands
    j = 0
    for k, (at, op, args) in enumerate(old):
        if j >= len(ins) or ins[j][1] != op:
            return [f'{rel}: op {op:#04x} at {at:#x} has no counterpart']
        where[at], pair[at] = ins[j][0], ins[j][2]
        for (ka, _, va), (kb, _, vb) in zip(args, ins[j][2]):
            if ka != kb or (ka not in 'SJ' and va != vb):
                return [f'{rel}: operand of op {op:#04x} at {at:#x} changed']
        j += 1
        nxt = old[k + 1] if k + 1 < len(old) else None
        if op == 0x22 and nxt and nxt[1] == 0x4a:
            t1 = insert._vtime(nxt[2][0][2])
            while j + 2 < len(ins) and ins[j][1] == 0x4a and insert._vtime(ins[j][2][0][2]) < t1 \
                    and ins[j + 1][1] == 0x22 and ins[j + 1][2][0][2] == b'\x08' and ins[j + 2][1] == 0x22:
                j += 3
    if any(op != 0x14 for _, op, _ in ins[j:]):
        return [f'{rel}: extra ops after the original script']
    where[len(a)] = ins[j][0] if j < len(ins) else len(b)    # a jump to the end of the script is legal
    errs = []
    for at, _, args in old:
        for (ka, ao, va), (_, bo, vb) in zip(args, pair[at]):
            if ka == 'J' and where.get(ao + 2 + va) != bo + 2 + vb:
                errs.append(f'{rel}: jump at {at:#x} no longer reaches its original target')
    for k, (r0, r1) in enumerate(zip(E.routines(a), E.routines(b))):
        moved = r0[0] == 0xff and r0[2]
        if r0[:2] != r1[:2] or r0[3] != r1[3] or (where.get(r0[2]) if moved else r0[2]) != r1[2]:
            errs.append(f'{rel}: routine {k} changed')
    return errs


def check_title(orig, new):
    if len(new) != len(orig):
        return [f'{gfx.TITLE}: size changed']
    p = tim.parse(orig)['pixoff']
    x0, y0, w, h = gfx.KANA
    ok = {p + y * 256 + x for y in range(y0, y0 + h) for x in range(x0, x0 + w)}
    bad = [i for i in range(len(orig)) if orig[i] != new[i] and i not in ok]
    return [f'{gfx.TITLE}: {len(bad)} bytes changed outside the katakana area'] if bad else []


def check_files(files, writes):
    """files = [(rel, new bytes)] as insert.stage returns them; writes = the exe write log."""
    errs = []
    for rel, new in files:
        orig = (insert.TREE / rel).read_bytes()
        if rel == insert.EXE:
            errs += check_exe(orig, new, writes)
        elif rel == gfx.TITLE:
            errs += check_title(orig, new)
        elif Path(rel).suffix.upper() == '.BIN' and 'MES' in rel.upper():
            errs += check_mes(rel, orig, new)
        else:
            errs.append(f'{rel}: no write map for this file')
    return errs


def check_stage(stage):
    tree = Path(stage) / 'tree'
    files = [(p.relative_to(tree).as_posix(), p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file()]
    return check_files(files, romdiff.load_writes(Path(stage) / 'exe_writes.txt'))


if __name__ == '__main__':
    errs = check_stage(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'work' / 'stage' / 'en')
    print('\n'.join(errs[:50]) or 'gate ok')
    sys.exit(1 if errs else 0)
