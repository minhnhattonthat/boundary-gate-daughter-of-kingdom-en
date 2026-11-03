"""Translation batches: split the untranslated script into work/tl/bNNN.tsv, check and merge results.

  split [--chars N]   write work/tl/bNNN.tsv + work/tl/terms_bNNN.txt for every unique JP string
                      without English (never overwrites: numbering continues after the last batch)
  check BATCH..       validate work/tl/BATCH.out.tsv against its input; prints OK or the errors
  merge BATCH..       check, then write each line's English into every script/*.json entry with
                      that JP (translation memory: identical JP = identical English)
  fit "TEXT" [--rows N] [--exe]   show how a dialogue line wraps into 26-cell rows and pages
  pairs BATCH..       write work/tl/BATCH.pairs.txt (>> id | JP / EN with context) for a reviewer

Input line:  id<TAB>speaker<TAB>form<TAB>limit<TAB>jp      ('#' lines = scene headers, context only)
Output line: id<TAB>en                                      (written by the translator)
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import extract  # noqa: E402
import lint as L  # noqa: E402
import wrap as W  # noqa: E402

TL = ROOT / 'work' / 'tl'


def _line(u):
    return '\t'.join([u['ids'][0], u['speaker'] or '-', u['entries'][0]['group'], L.limit(u),
                      L.jp_display(u)])


def _header(u):
    if u['exe']:
        return f'# exe {u["src"][4:]}'
    return f'# {Path(u["src"]).stem}'


def cmd_split(a):
    TL.mkdir(parents=True, exist_ok=True)
    done = {i for p in TL.glob('b[0-9][0-9][0-9].tsv') for i in _ids(p)}
    nums = [int(p.stem[1:]) for p in TL.glob('b[0-9][0-9][0-9].tsv')]
    nxt = max(nums, default=0) + 1
    todo = [u for u in L.units() if not any(e['en'] for e in u['entries']) and u['ids'][0] not in done]
    # group by source (a scene file, or an exe group), then pack whole sources into batches
    srcs, cur = [], None
    for u in todo:
        if cur is None or cur[0] != u['src']:
            cur = (u['src'], [])
            srcs.append(cur)
        cur[1].append(u)
    batches, b, size = [], [], 0
    for src, us in srcs:
        for u in us:
            n = len(L.jp_display(u))
            if b and (len(b) >= a.lines or
                      size + n > a.chars and (u is us[0] or size > a.chars * 1.3)):
                batches.append(b)
                b, size = [], 0
            b.append(u)
            size += n
    if b:
        batches.append(b)
    terms = L.glossary()
    for k, b in enumerate(batches):
        name = f'b{nxt + k:03d}'
        lines, last = [], None
        for u in b:
            h = _header(u)
            if h != last:
                lines.append(h)
                last = h
            lines.append(_line(u))
        path = TL / f'{name}.tsv'
        assert not path.exists(), path
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        found = []
        for u in b:
            found += [t for t in L.terms_in(u['jp'], terms) if t not in found]
        (TL / f'terms_{name}.txt').write_text(
            ''.join(f'{t[0]}\t{" / ".join(t[1])}\n' for t in found), encoding='utf-8', newline='\n')
        print(f'{name}: {len(b)} lines, {sum(len(L.jp_display(u)) for u in b)} JP chars, '
              f'{b[0]["src"]} .. {b[-1]["src"]}')
    if not batches:
        print('nothing left to split')
    return 0


def _ids(path):
    return [ln.split('\t', 1)[0] for ln in path.read_text(encoding='utf-8').splitlines()
            if ln and not ln.startswith('#')]


def _read_out(name):
    p = TL / f'{name}.out.tsv'
    if not p.exists():
        return None, [f'{p.name} missing']
    out, errs = {}, []
    for n, ln in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if not ln.strip() or ln.startswith('#'):
            continue
        if '\t' not in ln:
            errs.append(f'line {n}: no TAB')
            continue
        i, en = ln.split('\t', 1)
        if '\t' in en:
            errs.append(f'line {n}: extra TAB')
        if i in out:
            errs.append(f'line {n}: duplicate id {i}')
        out[i.strip()] = en.rstrip('\r')
    return out, errs


def check(name, quiet=False):
    """Errors for one batch; prints them (and warnings) unless quiet."""
    ids = _ids(TL / f'{name}.tsv')
    by_id = {u['ids'][0]: u for u in L.units()}
    out, errs = _read_out(name)
    warns = []
    if out is not None:
        missing = [i for i in ids if i not in out]
        extra = [i for i in out if i not in ids]
        if missing:
            errs.append(f'missing ids: {" ".join(missing[:10])}' + (' ...' if len(missing) > 10 else ''))
        if extra:
            errs.append(f'unknown ids: {" ".join(extra[:10])}')
        terms = L.glossary()
        for i in ids:
            if i in out and i in by_id:
                e, w = L.check_unit(by_id[i], out[i], terms)
                errs += [f'{i}: {x}' for x in e]
                warns += [f'{i}: {x}' for x in w]
    if not quiet:
        for x in errs:
            print(f'ERROR {name} {x}')
        for x in warns:
            print(f'warn  {name} {x}')
        print(f'{name}: OK ({len(warns)} warnings)' if not errs else f'{name}: {len(errs)} errors')
    return errs


def cmd_check(a):
    return 1 if sum(len(check(n)) for n in a.batch) else 0


def cmd_merge(a):
    bad = [n for n in a.batch if check(n, quiet=True)]
    if bad:
        print(f'refusing to merge, check fails: {" ".join(bad)} (run: batches.py check {" ".join(bad)})')
        return 1
    by_id = {u['ids'][0]: u for u in L.units()}
    en_of = {}
    for n in a.batch:
        out, _ = _read_out(n)
        for i, en in out.items():
            u = by_id[i]
            game = W.from_tsv(en, exe=u['exe'], nl=L.nl_of(u))
            for eid in u['ids']:
                en_of[eid] = game
    files = [(r, extract.out_path(r)) for r, _ in extract.sources()] + [(extract.EXE, extract.out_path(extract.EXE))]
    wrote = 0
    for rel, path in files:
        d = extract.load(path)
        hit = False
        for e in d['entries']:
            if e['id'] in en_of:
                e['en'] = en_of[e['id']]
                e['status'] = 'tl'
                hit = True
                wrote += 1
        if hit:
            extract.write_json(path, d)
    print(f'merged {len(a.batch)} batch(es): {wrote} entries')
    return 0


def cmd_fit(a):
    game = W.from_tsv(a.text, exe=a.exe)
    if a.exe:
        for r in re.split('[\r\n]', game.replace('::', ':')):
            print(f'{W.fmt_cells(r):3d} |{r}|')
        return 0
    _, pages = W.layout(game, a.rows, quote=a.cont)
    for k, p in enumerate(pages, 1):
        print(f'-- page {k}')
        for r in p:
            print(f'{W.cells(r):3d} |{r.ljust(W.COLS)}|')
    return 0


def cmd_pairs(a):
    for n in a.batch:
        out, _ = _read_out(n)
        lines = []
        for ln in (TL / f'{n}.tsv').read_text(encoding='utf-8').splitlines():
            if ln.startswith('#'):
                lines.append(ln)
                continue
            i, spk, form, lim, jp = ln.split('\t')
            lines.append(f'>> {i} | {spk} | {form} {lim} | {jp}')
            lines.append(f'   EN: {(out or {}).get(i, "")}')
        (TL / f'{n}.pairs.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        print(f'{n}.pairs.txt')
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('split')
    s.add_argument('--chars', type=int, default=3200, help='JP characters per batch (default 3200)')
    s.add_argument('--lines', type=int, default=160, help='max lines per batch (default 160)')
    for c in ('check', 'merge', 'pairs'):
        s = sub.add_parser(c)
        s.add_argument('batch', nargs='+')
    s = sub.add_parser('fit')
    s.add_argument('text')
    s.add_argument('--rows', type=int, default=W.ROWS)
    s.add_argument('--exe', action='store_true')
    s.add_argument('--cont', action='store_true', help='the line continues a quote (JP starts indented)')
    a = ap.parse_args(argv)
    return {'split': cmd_split, 'check': cmd_check, 'merge': cmd_merge, 'fit': cmd_fit,
            'pairs': cmd_pairs}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
