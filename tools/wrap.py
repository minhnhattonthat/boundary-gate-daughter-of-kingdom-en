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
CLR, WAIT, CHOICE = '\x08', '\x10', '\x19'
PAGE = WAIT + CLR
# Voiced events advance on their own and never wait for a button; a button wait there stalls the scene before its
# window shows (phase 8, EVENT68). Their extra pages wait 3 x 60 frames (printer byte 0x17) instead.
TIMED_PAGE = '\x17\x17\x17' + CLR

# script fields: op -> (cells, hard). hard = measured; soft = guess until phase 8 measures it.
FIELD = {'21': (26, True), '23': (26, True), '25': (24, True),
         # 0x1c NPC list: drawn in the 26-cell message window after a 1-cell cursor (phase 7, npcs_53)
         '1c': (25, True), '27': (10, False),
         # 0x28/0x4e destination lists: text from cell 2 (cursor in 0-1), one row an entry (phase 8, room_62)
         '28': (24, True), '4e': (24, True)}

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


_FUNC = set('a an the of to and or in on at with for by from into is are was were be been being as that this these '
            'those my your our their his her its we i you he she it they but if so not no who whom which whose what '
            'when where while because than there will would can could shall should may might must has have had do '
            'does did ever just very only'.split())


def _cut(word, nxt=''):
    """How badly ending a page after `word` (next word `nxt`) cuts the text: sentence end (or a JP button wait) 0,
    clause 1, content word 4, function word 6 ('weapons and / armour'), inside a name 8 ('Temple / of Sorcery',
    'Ancient / Knowledge')."""
    if re.search(r'([.!?]|\.\.\.|' + WAIT + ')["\')]*$', word):
        return 0
    if re.search(r'([,;:]|--)["\')]*$|"$', word):   # a closing quote ends a title: '...Culture" / "Forming'
        return 1
    w, n = word.strip('"\'(.'), nxt.strip('"\'(')
    if w[:1].isupper() and (n == 'of' or n[:1].isupper()) and w.lower() not in _FUNC or \
            w.lower() in ('of', 'the') and (n[:1].isupper() or n == 'the'):
        return 8
    return 6 if w.lower() in _FUNC else 4


def _paginate(seg, cols, quote, first_max, rows_max=ROWS, choice=False):
    """Word-wrap one segment into pages: the first holds <= first_max rows (2 under a speaker line), later ones
    rows_max (the clear wipes the name row too). Text that fits stays one page. Otherwise each page is wrapped on
    its own and the cut points are chosen (DP over words) to cost least: 2 a page, _cut() at each page end, 1 a
    lone-row page (except a first page under a speaker line), 5 more a page of <= 2 words; so pages start at
    sentences where they can.
    Returns (pages, quote_after)."""
    rows, quote_end = _rows_of(seg, cols, quote)
    rows = [r.rstrip() for r in rows]
    while rows and not rows[-1].strip():
        rows.pop()
    last = 1 if choice or CHOICE in seg else 0   # an inline choice (0x19) takes the row after the text
    if len(rows) <= first_max - last:
        return [rows], quote_end
    toks = []                                    # (word, starts a \r paragraph)
    for k, para in enumerate(seg.split('\r')):
        ws = [w for w in para.split(' ') if w] or ['']
        toks += [(w, k > 0 and x == 0) for x, w in enumerate(ws)]
    qs = [quote]
    for w, _ in toks:
        qs.append(qs[-1] ^ (w.count('"') % 2 == 1))

    def page(i, j):
        text = ''.join(('\r' if p else ' ') * (t > i) + w for t, (w, p) in enumerate(toks[i:j], i))
        r = [x.rstrip() for x in _rows_of(text, cols, qs[i])[0]]
        while r and not r[-1].strip():
            r.pop()
        return r

    n, best = len(toks), {len(toks): (0, [])}
    for i in range(n - 1, -1, -1):
        cap = first_max if i == 0 else rows_max
        for j in range(i + 1, n + 1):
            r = page(i, j)
            if len(r) > cap:
                break
            if j == n and len(r) > cap - last:
                continue
            cost = 2 + (_cut(toks[j - 1][0], toks[j][0]) if j < n else 0) \
                + (len(r) == 1 and (i > 0 or cap == rows_max)) \
                + 5 * (j - max([t for t in range(i, j) if toks[t][1]] + [i]) <= 2)   # 'Kiral' / 'to Rio.' page
            # (words counted from the page's last forced row: a 'Rio' name row does not hide a 'A girl' fragment)
            cand = (cost + best[j][0], [r] + best[j][1])
            if i not in best or (cand[0], len(cand[1])) < (best[i][0], len(best[i][1])):
                best[i] = cand
    if 0 not in best:                            # a word longer than a page: plain row cuts
        caps = [first_max] + [rows_max] * len(rows)
        out, at = [], 0
        for c in caps:
            if at < len(rows):
                out.append(rows[at:at + c])
                at += c
        return out, quote_end
    return best[0][1], quote_end


def continues_quote(jp):
    """A JP dialogue entry that starts indented continues a quote opened by the entry before it."""
    return jp.startswith(('  ', '　'))


def layout(en, rows_max=ROWS, cols=COLS, quote=False, page=PAGE):
    """Paragraph-form English -> (game string, pages). pages = list of row lists (for checks/fit).

    Splits at clear (\\x08); a wait (\\x10) not followed by clear stays inside the page. Overflowing
    pages become extra pages (_paginate) joined by `page` (\\x10\\x08). `quote`: the entry starts inside
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
        chunks, quote = _paginate(seg, cols, quote, rows_max if i == 0 else ROWS,   # a clear wipes the speaker row
                                  choice=CHOICE in tail)
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
