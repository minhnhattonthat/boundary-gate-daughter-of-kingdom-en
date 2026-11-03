"""Translation lint: every `en` in script/*.json against its budget, controls, glossary and style rules.

Shared by tools/batches.py (checks a batch before merge) and tools/check.py (the pre-commit gate).
Errors fail; warnings (soft budgets that are still guesses, exe strings that need phase-7 relocation)
are counted and listed with --warn.

usage: python -X utf8 tools/lint.py [--warn]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import extract  # noqa: E402
import sjis  # noqa: E402
import wrap as W  # noqa: E402

GLOSSARY = ROOT / 'glossary.md'
HONORIFIC = {'さん': 'san', '様': 'sama', 'さま': 'sama', 'くん': 'kun', '君': 'kun', 'ちゃん': 'chan'}
KANA = re.compile(r'[゠-ヿｦ-ﾟ]')


# ---------------------------------------------------------------- units

def units():
    """Unique translatable JP strings in story order: list of dicts
    {jp, ids, entries, prev (op of the text entry before each), speaker, src, exe}."""
    out, seen = [], {}
    for rel, _ in extract.sources():
        prev, prev_text = None, ''
        for e in extract.load(extract.out_path(rel))['entries']:
            if e['kind'] == 'text':
                spk = W.to_tsv(prev_text).strip(' /') if prev == '21' and e['op'] == '22' else ''
                key = ('s', e['jp'])
                if key not in seen:
                    seen[key] = {'jp': e['jp'], 'ids': [], 'entries': [], 'prev': [], 'speaker': spk,
                                 'src': rel, 'exe': False}
                    out.append(seen[key])
                u = seen[key]
                u['ids'].append(e['id'])
                u['entries'].append(e)
                u['prev'].append(prev)
                prev_text = e['jp']
            prev = e['op'] if e['kind'] == 'text' else prev
    order = ['party', 'boot', 'menu', 'map', 'items', 'spells', 'shop', 'save', 'gameover',
             'monsters', 'battle', 'prologue', 'ending', 'credits']
    exe = [e for e in extract.load(extract.out_path(extract.EXE))['entries']
           if e['kind'] == 'text' and 'debug menu' not in e['notes']]
    for g in order:
        grp = [e for e in exe if e['group'] == g]
        if g in ('prologue', 'ending', 'credits'):
            grp.reverse()            # stored bottom-up: present them in screen order
        for e in grp:
            out.append({'jp': e['jp'], 'ids': [e['id']], 'entries': [e], 'prev': [None],
                        'speaker': '', 'src': 'exe:' + g, 'exe': True})
    return out


def jp_display(u):
    """JP for a batch line: padding spaces around row breaks dropped (they only position text)."""
    jp = u['jp']
    if not u['exe']:
        jp = re.sub(r'[ 　]+(?=[\r\n\x08\x10]|$)', '', jp)
        jp = re.sub(r'(?<=[\r\n\x08])[ 　]+', '', jp)
    else:
        jp = jp.rstrip(' 　')
    return W.to_tsv(jp, exe=u['exe'])


def limit(u):
    return W.budget(u['entries'][0], '21' if '21' in u['prev'] else None)


def nl_of(u):
    return '\n' if '\n' in u['jp'] else '\r'


# ---------------------------------------------------------------- glossary

def glossary():
    """[(jp, [en forms], [avoid])] from every glossary table row whose JP is real text."""
    terms = []
    if not GLOSSARY.exists():
        return terms
    for line in GLOSSARY.read_text(encoding='utf-8').splitlines():
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if not line.startswith('|') or len(cols) < 2 or cols[0] in ('JP', '') or set(cols[0]) <= set('-'):
            continue
        if any('nocheck' in c for c in cols[2:]):
            continue
        en = [x.strip() for x in cols[1].split('/') if x.strip()]
        avoid = [x.strip() for x in (cols[4] if len(cols) > 4 else '').split(',') if x.strip()]
        terms.append((cols[0], en, avoid))
    return terms


def spans(jp, term):
    """Whole-run matches: a katakana term must not be part of a longer katakana run (リオ in シナリオ)."""
    out = []
    for m in re.finditer(re.escape(term), jp):
        if KANA.match(term[0]) and m.start() > 0 and KANA.match(jp[m.start() - 1]):
            continue
        if KANA.match(term[-1]) and m.end() < len(jp) and KANA.match(jp[m.end()]):
            continue
        out.append((m.start(), m.end()))
    return out


def has_term(jp, term):
    return bool(spans(jp, term))


def terms_in(jp, terms):
    """Glossary rows present in jp; a term found only inside a longer matched term is dropped
    (魔導聖堂 inside 魔導聖堂長: only the longer row applies)."""
    hits = [(t, spans(jp, t[0])) for t in terms]
    hits = [(t, s) for t, s in hits if s]
    out = []
    for t, s in hits:
        inside = all(any(a <= x and y <= b and (b - a) > (y - x) for t2, s2 in hits for a, b in s2)
                     for x, y in s)
        if not inside:
            out.append(t)
    return out


# ---------------------------------------------------------------- checks

PRINTF = re.compile(r'%[-+ 0#]*\d*l?[sdcx]')
NAME_ROW = re.compile(r'^[^\r「\x08\x10 ]{1,13}\r「')


def check_unit(u, en_tsv, terms):
    """(errors, warnings) for one unit's English (tsv form)."""
    err, warn = [], []
    if not en_tsv or (not en_tsv.strip() and u['jp'].strip(' 　')):   # a blank JP (exe:03658) may stay blank
        return ['empty'], []
    if any(not (0x20 <= ord(c) <= 0x7E) for c in en_tsv):
        bad = ''.join(sorted({c for c in en_tsv if not 0x20 <= ord(c) <= 0x7E}))
        err.append(f'non-ASCII {bad!r}')
    if '@' in en_tsv or '\\' in en_tsv:
        err.append("'@' or '\\' (printer escapes)")
    game = W.from_tsv(en_tsv, exe=u['exe'], nl=nl_of(u))
    jp = u['jp']
    if W.controls(game) != W.controls(jp):
        err.append(f'control codes {W.to_tsv("".join(W.controls(jp)))} != '
                   f'{W.to_tsv("".join(W.controls(game)))}')
    if u['exe']:
        conv = lambda s: [re.sub(r'%[-+ 0#]*\d*', '%', x) for x in PRINTF.findall(s)]  # noqa: E731
        if conv(game) != conv(jp) or game.count(':%c') != jp.count(':%c'):   # widths are layout
            err.append(f'printf/icon specifiers differ: {PRINTF.findall(jp)} vs {PRINTF.findall(game)}')
        if game.endswith(('\r', '\n')) != jp.endswith(('\r', '\n')) or \
                game.startswith(('\r', '\n')) != jp.startswith(('\r', '\n')):
            err.append('leading/trailing row break differs from the JP (printf chains rely on it)')
        if len(re.findall('[\r\n]', game)) != len(re.findall('[\r\n]', jp)):
            warn.append('row count differs from the JP')
        if re.search(r'%[-\d]*l?d(st|nd|rd|th)\b', game):
            err.append('ordinal suffix glued to a number')
        e = u['entries'][0]
        n, hard = W.exe_budget(e)
        for row in re.split('[\r\n]', game.replace('::', ':')):
            w = W.fmt_cells(row)
            if w > n:
                (err if hard else warn).append(f'row {w} cells > {n}: {row!r}')
        try:
            sjis.encode(game)      # a string longer than its slot is relocated by insert.rebuild_exe
        except Exception as x:     # noqa: BLE001
            err.append(f'unencodable: {x}')
    else:
        e = u['entries'][0]
        try:
            sjis.encode_en(game.replace('\r', '\n').replace('\n', '\r'))
        except Exception as x:     # noqa: BLE001
            err.append(f'unencodable: {x}')
        if e['op'] == '22':
            rows = W.rows_budget('21' if '21' in u['prev'] else None)
            _, pages = W.layout(game, rows, quote=W.continues_quote(jp))
            if NAME_ROW.match(jp) and not re.match(r'^[^\r"]{1,26}\r"', game):
                err.append('JP opens with a speaker-name row: write "Name / \\"..." (name, row break, quote)')
            for p in pages:
                for r in p:
                    if W.cells(r) > W.COLS:
                        err.append(f'word too long for a {W.COLS}-cell row: {r!r}')
            np_jp = jp.count(W.CLR) + 1
            if len(pages) > 2 * np_jp + 1:
                warn.append(f'{len(pages)} pages for {np_jp} JP page(s): consider tightening')
        else:
            n, hard = W.FIELD[e['op']]
            if game.endswith('\r') != jp.endswith('\r'):
                err.append('trailing row break differs from the JP (a speaker line ends with " / ")')
            rows = game.rstrip('\r').split('\r')
            if len(rows) > (2 if e['op'] == '23' else 1):
                err.append(f'{len(rows)} rows in a one-row field')
            for r in rows:
                if W.cells(r) > n:
                    (err if hard else warn).append(f'{W.cells(r)} cells > {n}: {r!r}')
    low = en_tsv.lower()
    for tjp, ten, avoid in terms_in(jp, terms):
        if ten and not any(t.lower() in low for t in ten):
            err.append(f'glossary: {tjp} -> {" / ".join(ten)} missing')
        for a in avoid:
            if re.search(r'\b' + re.escape(a.lower()) + r'\b', low):
                err.append(f'glossary: avoid {a!r} ({tjp})')
        for hjp, hen in HONORIFIC.items():
            if KANA.match(tjp[0]) and (tjp + hjp) in jp and ten:      # names only, not titles
                if not any(f'{t}-{hen}'.lower() in low for t in ten):
                    err.append(f'honorific: {tjp}{hjp} -> {ten[0]}-{hen} missing')
    if re.search(r'(^|[^.])\.\.(?!\.)', en_tsv):
        warn.append("two dots: use '...'")
    return err, warn


# ---------------------------------------------------------------- lint over script/*.json

def lint(show_warn=False):
    terms = glossary()
    n_err = n_warn = n_done = 0
    total = 0
    for u in units():
        total += 1
        ens = {e['en'] for e in u['entries'] if e['en']}
        if not ens:
            continue
        n_done += 1
        if len(ens) > 1:
            print(f'ERROR {u["ids"][0]}: same JP, {len(ens)} different translations')
            n_err += 1
        for en in ens:
            err, warn = check_unit(u, W.to_tsv(en, exe=u['exe']), terms)
            for x in err:
                print(f'ERROR {u["ids"][0]}: {x}')
            if show_warn:
                for x in warn:
                    print(f'warn  {u["ids"][0]}: {x}')
            n_err += len(err)
            n_warn += len(warn)
    covered = {i for u in units() for i in u['ids']}
    for e in extract.load(extract.out_path(extract.EXE))['entries']:   # a group units() skips
        if e['kind'] == 'text' and 'debug menu' not in e['notes'] and e['id'] not in covered:
            print(f'ERROR {e["id"]}: exe text in group {e["group"]!r}, which the lint never reads')
            n_err += 1
    print(f'lint: {n_done}/{total} units translated, {n_err} errors, {n_warn} warnings')
    return 1 if n_err else 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--warn', action='store_true', help='list warnings too')
    return lint(ap.parse_args(argv).warn)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
