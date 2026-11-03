"""English layout for the message window and the per-field budgets (width gate, docs/re/windows.md).

Translations are authored as paragraphs (`en` in script/*.json); this module turns one into the bytes
the printer sees and is the single source of truth for budgets, used by the build (insert.py), the lint
(lint.py) and the translator tools (batches.py).

Text forms
  game  : the string as stored in script/*.json, real control chars (\\x08 clear, \\x10 wait, \\r row).
  tsv   : one line for batch files: ' / ' = row break, <clr> <wait> <page> <icon> <xx> (hex) tokens.
          <page> = an extra page the English needs (= <wait><clr>), allowed beyond the JP's controls.

Dialogue (op 0x22) layout: pages split at \\x08; each page is word-wrapped to 26 cells; a page
that needs more rows than its budget gets an automatic page break (\\x10\\x08) at a row boundary.
Rows inside an open "quote" get a one-space hanging indent (the JP indents its quote rows too).
"""
import re

COLS, ROWS = 26, 3
CLR, WAIT = '\x08', '\x10'
PAGE = WAIT + CLR
# Voiced events advance on their own and never wait for a button; a button wait there stalls the scene before its
# window shows (phase 8, EVENT68). Their extra pages wait 3 x 60 frames (printer byte 0x17) instead.
TIMED_PAGE = '\x17\x17\x17' + CLR

# script fields: op -> (cells, hard). hard = measured; soft = guess until phase 8 measures it.
FIELD = {'21': (26, True), '23': (26, True), '25': (24, True),
         # 0x1c NPC list: drawn in the 26-cell message window after a 1-cell cursor (phase 7, npcs_53)
         '1c': (25, True), '27': (10, False), '28': (25, False), '4e': (25, False)}

# printf conversions: worst-case cells drawn (used for exe budget checks)
PRINTF = re.compile(r'%[-+ 0#]*(\d*)(l?)([sdcx])')
PRINTF_CELLS = {'s': 12, 'd': 3, 'c': 1, 'x': 4}


def cells(text):
    """Cells drawn: half-width = 1, full-width = 2, control chars 0. ':' is one cell ('::' in bytes)."""
    return sum(2 if (ord(c) > 0x7E and not 0xFF61 <= ord(c) <= 0xFF9F) else 1
               for c in text if ord(c) >= 0x20)


def fmt_cells(text):
    """Cells of an exe printf format: each conversion counted at its width or a worst-case guess."""
    n, pos = 0, 0
    for m in PRINTF.finditer(text):
        n += cells(text[pos:m.start()])
        w = int(m.group(1)) if m.group(1) else 0
        n += max(w, PRINTF_CELLS[m.group(3)] if not w else 0)
        pos = m.end()
    return n + cells(text[pos:])


# ---------------------------------------------------------------- tsv <-> game

_TOK = {CLR: '<clr>', WAIT: '<wait>'}


def to_tsv(s, exe=False):
    if exe:
        s = s.replace(':%c', '\0ICON\0').replace('::', ':').replace('\0ICON\0', '<icon>')
    out = []
    for c in s:
        if c in '\r\n':
            out.append(' / ')
        elif c in _TOK:
            out.append(_TOK[c])
        elif ord(c) < 0x20 or c == '\t':
            out.append(f'<{ord(c):02x}>')
        else:
            out.append(c)
    return ''.join(out)


# ' / ' = row break; a break at either end of the line may lose its outer space (editors strip it)
_TOKEN = re.compile(r'<(clr|wait|page|icon|[0-9a-f]{2})>| / |^/ | /$')


def from_tsv(t, exe=False, nl='\r'):
    """Batch-file text -> game form. Exe strings: ':' -> '::' and <icon> -> ':%c' (printer escapes)."""
    def sub(m):
        if m.group(1) is None:
            return nl
        k = m.group(1)
        return {'clr': CLR, 'wait': WAIT, 'page': PAGE, 'icon': '\0ICON\0'}.get(k) or chr(int(k, 16))
    s = _TOKEN.sub(sub, t)
    if exe:
        s = s.replace(':', '::').replace('\0ICON\0', ':%c')
    return s


def controls(s):
    """Control chars of a game string, with every wait+clear pair (a page break) removed.
    Callers comparing JP and EN must also check pages(en) >= pages(jp): English may add pages, never drop them."""
    return sorted(c for c in s.replace(PAGE, '') if ord(c) < 0x20 and c not in '\r\n')


# ---------------------------------------------------------------- dialogue layout

def _rows_of(seg, cols, quote):
    """Word-wrap one page segment (may hold \\r forced breaks and zero-width controls).
    Returns (rows, quote_open_after)."""
    rows = []
    for para in seg.split('\r'):
        row = ''
        for w in para.split(' '):
            if not w:
                continue
            lead = ' ' if quote and not w.startswith('"') else ''   # hanging indent inside a quote
            if row and cells(row + ' ' + w) <= cols:
                row += ' ' + w
            else:
                if row:
                    rows.append(row)
                row = lead + w
            quote ^= w.count('"') % 2 == 1
        rows.append(row)
    return rows, quote


def _balance(rows, first_max, rows_max=ROWS):
    """Cut rows into the fewest pages (the first holds <= first_max rows: 2 under a speaker line; later pages
    rows_max, the clear wipes the name row too). Of those cuts, pages end at a sentence end (or an existing button
    wait) where they can, then as even as possible: 4 rows -> 2+2, 7 -> 3+2+2, so an overflow rarely leaves a
    one-row fragment page ("moves.") after a full one or splits "weapons and / armour" across pages."""
    n = len(rows)
    if n <= first_max:
        return [rows]
    m = -(-(n - first_max) // rows_max)          # pages after the first

    def cut(row):                                # how badly a page ending on this row cuts the text
        row = row.rstrip()
        return 0 if re.search(r'([.!?]|\.\.\.|' + WAIT + ')["\')]*$', row) else 1 if re.search(r'[,;:-]$', row) else 2

    def splits(left, k, cap):                    # every way to cut `left` rows into k pages of <= cap rows
        if k == 1:
            yield [left] if 1 <= left <= cap else None
            return
        for s in range(1, min(cap, left - k + 1) + 1):
            for t in splits(left - s, k - 1, cap):
                if t:
                    yield [s] + t

    best = None
    for f in range(1, first_max + 1):
        for rest in splits(n - f, m, rows_max) if n - f >= m else ():
            if not rest:
                continue
            sizes = [f] + rest
            ends = [sum(sizes[:i + 1]) - 1 for i in range(len(sizes) - 1)]
            # page ends at sentence ends first, then no lone-row pages, then even; a lone row reads better first
            score = (sum(cut(rows[e]) for e in ends), sizes.count(1), max(sizes) - min(sizes), f,
                     [-s for s in rest])         # then fuller pages first
            best = min(best or (score, sizes), (score, sizes))
    sizes = best[1]
    out, at = [], 0
    for n in sizes:
        out.append(rows[at:at + n])
        at += n
    return out


def continues_quote(jp):
    """A JP dialogue entry that starts indented continues a quote opened by the entry before it."""
    return jp.startswith(('  ', '　'))


def layout(en, rows_max=ROWS, cols=COLS, quote=False, page=PAGE):
    """Paragraph-form English -> (game string, pages). pages = list of row lists (for checks/fit).

    Splits at clear (\\x08); a wait (\\x10) not followed by clear stays inside the page. Overflowing
    pages are cut into extra pages at row boundaries with \\x10\\x08. `quote`: the entry starts inside
    a quote opened by an earlier entry (continues_quote), so its rows get the hanging indent."""
    out, pages = [], []
    for i, seg in enumerate(en.split(CLR)):
        if i:
            out.append(CLR)
        tail = ''
        m = re.search(r'[\x00-\x1f]*$', seg)
        if m and '\r' not in m.group(0):
            seg, tail = seg[:m.start()], m.group(0)
        if not seg.strip():
            out.append(seg + tail)
            continue
        rows, quote = _rows_of(seg, cols, quote)
        rows = [r.rstrip() for r in rows]
        while rows and not rows[-1].strip():
            rows.pop()
        chunks = _balance(rows, rows_max if i == 0 else ROWS)   # a clear wipes the speaker row too
        pages.extend(chunks)
        out.append(page.join('\r'.join(c) for c in chunks) + tail)
    return ''.join(out), pages


def rows_budget(prev_op):
    """Rows per page for a 0x22 entry: 2 under a speaker line (0x21 takes row 1), else 3."""
    return ROWS - 1 if prev_op == '21' else ROWS


# ---------------------------------------------------------------- exe budgets

EXE_ROW = {'battle': 26, 'shop': 26, 'save': 26, 'monsters': 26, 'prologue': 38}


def exe_budget(e):
    """(cells per row, hard) for one exe string, from its group and field (docs/re/windows.md)."""
    g, jp = e['group'], e['jp']
    if g in ('items', 'spells') and ('%' in jp or '\n' in jp or not 0x1f58 <= e['off'] < 0x3128):
        return 26, False      # item-use / result messages (exe 0x37ec+): message window
    if g == 'party':
        return 14, True
    if g == 'map':
        return 24, True
    if g == 'items':
        return (30, False) if e['len'] == 30 else (20, True)
    if g == 'spells':
        return (30, False) if e['len'] == 30 else (22, True)
    if g == 'ending':
        return 38, True       # centred in a 256 px band: a longer line runs off both edges (phase 8)
    if g == 'credits':        # cast/staff labels sit in a 20-cell column; the JP's longer rows are narration
        return (20, True) if max(cells(r) for r in jp.split('\n')) <= 20 else (38, False)
    if g in EXE_ROW:
        return EXE_ROW[g], False
    return max(cells(r) for r in re.split('[\r\n]', jp)), False


def budget(e, prev_op=None):
    """Human-readable limit for a batch line: '26x3', '26x2', '20', '24~' (~ = soft)."""
    if e['id'].startswith('exe:'):
        n, hard = exe_budget(e)
        return f'{n}' + ('' if hard else '~')
    if e['op'] == '22':
        return f'{COLS}x{rows_budget(prev_op)}'
    n, hard = FIELD[e['op']]
    return f'{n}' + ('' if hard else '~')
