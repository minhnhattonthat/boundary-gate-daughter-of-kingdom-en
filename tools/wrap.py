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
         # 0x27 choice: drawn inline in the message window row, 10 cells a choice (phase 7, scene save)
         '1c': (25, True), '27': (10, True),
         # 0x28/0x4e destination lists: text from cell 2 (cursor in 0-1), one row an entry (phase 8, room_62)
         '28': (24, True), '4e': (24, True)}

# printf conversions: worst-case cells drawn (used for exe budget checks)
PRINTF = re.compile(r'%[-+ 0#]*(\d*)(l?)([sdcx])')
PRINTF_CELLS = {'s': 12, 'd': 3, 'c': 1, 'x': 4}


def cells(text):
    """Cells drawn: half-width = 1, full-width = 2, control chars 0. ':' is one cell ('::' in bytes)."""
    return sum(2 if (ord(c) > 0x7E and not 0xFF61 <= ord(c) <= 0xFF9F) else 1
               for c in text if ord(c) >= 0x20)


def fmt_cells(text, args=None):
    """Cells of an exe printf format: each conversion counted at its width or a worst-case guess.
    `args`: worst-case cells of each %s in order (a field width still wins when it is larger)."""
    n, pos, k = 0, 0, 0
    args = list(args or [])
    for m in PRINTF.finditer(text):
        n += cells(text[pos:m.start()])
        w = int(m.group(1) or 0)
        if m.group(3) == 's' and k < len(args):
            n, k = n + max(w, args[k]), k + 1
        else:
            n += w or (6 if m.group(2) else PRINTF_CELLS[m.group(3)])    # %ld: gold, EXP (the game's %6ld)
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

# Message-window groups: 26 cells a row, the window wraps by itself but mid-word ('Finnattacked', phase 8), so
# every row with its arguments at their worst case must fit. Prologue: the title-attract lore rows, drawn from
# x=16 with no wrap and no row breaks (a 0x0A draws as a blank cell): 38 keeps them inside the JP's own extent.
# Save: the save/load window, 0x80021530 w=35 at x=23 (calls 0x1ee38, 0x1fa04 inside the save code).
EXE_ROW = {'battle': 26, 'shop': 26, 'save': 35, 'monsters': 26, 'prologue': 38}

# Exe fields the group rules do not cover: id -> (cells, where). Post-patch widths (insert.EXE_PATCHES) or the
# reader's printf field; docs/re/windows.md. All hard.
_TITLE = 'field-menu column / submenu title box, 6 cells after the 4 -> 6 patch'
_USE = "use label in the items/magic header's %-9s field"
_STAT = 'status screen right column (window 0x80021414 w=16 at x=208)'
EXE_FIELD = {
    **{i: (6, _TITLE) for i in ('exe:00b9c', 'exe:00c08', 'exe:00cb0', 'exe:00dbc', 'exe:00e6c', 'exe:01000',
                                'exe:01031')},
    **{i: (9, _USE) for i in ('exe:00ba4', 'exe:00bac', 'exe:00bb4', 'exe:01038', 'exe:01040', 'exe:01048',
                              'exe:01050')},
    # status names in the field-menu row %-3s%-6s%-8s%-5s%-7s (KO, Sleep, Silence, Weak, Poison), 1 cell gap kept
    'exe:00ad8': (2, 'status %-3s'), 'exe:00ad0': (5, 'status %-6s'), 'exe:00ac8': (7, 'status %-8s'),
    'exe:00ac0': (4, 'status %-5s'), 'exe:00abc': (6, 'status %-7s'),
    'exe:00b20': (3, 'items-menu party box %-4s (insert.FORMAT_EN exe:00b28)'),
    'exe:00b24': (3, 'items-menu party box %-4s (insert.FORMAT_EN exe:00b28)'),
    # top box, 39 cells x 2 rows after the patch: 38 + the cursor/icon column; one more scrolls row 1 away (phase 8)
    **{i: (38, 'top box row (field menu / items / magic header)') for i in
       ('exe:00af0', 'exe:00b0c', 'exe:00bc0', 'exe:00be8', 'exe:00fc8')},
    'exe:00fa4': (39, 'field-menu party name row: starts at column 0, the full 39 cells (test_field_party_rows_fit)'),
    'exe:01f58': (24, 'location name (current-location field %24s), stored just before the item names'),
    **{i: (15, 'equip compare box, 15 cells after the 13 -> 15 patch') for i in
       ('exe:00c14', 'exe:00c24', 'exe:00c34', 'exe:00c44', 'exe:00c54')},
    **{i: (8, 'equip slot label: the item column starts 50 px (8 cells) right of it (patch 0x1752c)') for i in
       ('exe:00c68', 'exe:00c74', 'exe:00c80', 'exe:00c8c')},
    **{i: (16, _STAT) for i in ('exe:00ce0', 'exe:00cec', 'exe:00d00', 'exe:00d14', 'exe:00d24', 'exe:00d40',
                                'exe:00d48', 'exe:00d5c', 'exe:00d70', 'exe:00d84', 'exe:00d98', 'exe:00dac')},
    **{i: (26, 'config value column, 26 cells after the patch') for i in
       ('exe:00e38', 'exe:00e40', 'exe:00e48', 'exe:00e50', 'exe:00e58')},
    'exe:00e7c': (13, 'config labels: the value column starts right of 13 cells (patch 0x18c38)'),
    'exe:00f8c': (34, 'map screen bottom window (w=34 at x=16)'),
    'exe:008b8': (20, 'boot prompt window (0x80021414 w=20 h=1)'),
    'exe:008d0': (8, 'boot New Game / Continue window (w=8 h=2)'),
    'exe:00a40': (6, 'Yes/No choice: the narrowest choice window is 8 cells, 2 kept for the cursor'),
    'exe:00a48': (6, 'Yes/No choice: the narrowest choice window is 8 cells, 2 kept for the cursor'),
    **{i: (8, 'command window, 8 cells after the 6 -> 8 patch (rows start with 2 cursor spaces)') for i in
       ('exe:03150', 'exe:03214', 'exe:0322c', 'exe:032ac', 'exe:04680', 'exe:0468c', 'exe:0469c', 'exe:046a4')},
    'exe:031c0': (35, 'shop list row: shop window 0x80021530 w=35 at x=23 (call 0x1db5c)'),
    **{i: (64, 'memory-card title, 64 bytes of Shift-JIS; prefix checked by test_card_title_prefix_matches_jp')
       for i in ('exe:03618', 'exe:03638')},
}
# Strings never drawn as text (the Game Over banner is a graphic; these labels sit in .data tables 0x6b580-0x6b628
# that no screen in the phase-8 tour reads): no width check, the build relocates them like any other string.
UNSEEN = {'exe:03a00', 'exe:03a14', 'exe:03a20'}


def is_msg(e):
    """Printed into the 26-cell message window (battle log, shop/inn/save prompts, item-use results)."""
    g, jp = e['group'], e['jp']
    return e['id'] not in EXE_FIELD and (g in ('battle', 'shop', 'save', 'monsters') or (
        g in ('items', 'spells') and ('%' in jp or '\n' in jp or not 0x1f58 <= e['off'] < 0x3128)))


def exe_budget(e):
    """(cells per row, hard) for one exe string, from its group and field (docs/re/windows.md).
    Raises KeyError for a string with no measured budget (the lint reports it)."""
    g, jp = e['group'], e['jp']
    if e['id'] in EXE_FIELD:
        return EXE_FIELD[e['id']][0], True
    if is_msg(e):
        return EXE_ROW.get(g, 26), True
    if g == 'party':
        return 14, True
    if g == 'map':
        return 24, True
    if g == 'items':
        return (30, True) if e['len'] == 30 else (20, True)
    if g == 'spells':         # 30-byte descriptions: the help box is 48 cells (w=48 at x=16); 30 keeps them in place
        return (30, True) if e['len'] == 30 else (22, True)
    if g == 'ending':
        return 38, True       # centred in a 256 px band: a longer line runs off both edges (phase 8)
    if g == 'credits':        # cast/staff labels sit in a 20-cell column; the JP's longer rows are narration
        return (20, True) if max(cells(r) for r in jp.split('\n')) <= 20 else (38, True)
    if g in EXE_ROW:
        return EXE_ROW[g], True
    if e['id'] in UNSEEN:
        return None, True
    raise KeyError(f'{e["id"]}: no measured budget (add it to wrap.EXE_FIELD)')


def msg_args(e, fmt):
    """Worst-case cells of each %s in a message-window format: an actor (the longest party or monster name), the
    'A'/'B' suffix after it ('%s%s', 2 cells), then item or spell names; ARG_KIND overrides."""
    n = fmt.count('%s')
    if e['id'] in ARG_KIND:
        kinds = ARG_KIND[e['id']]
    elif e['group'] in ('items', 'spells'):          # field item/spell use: the target is a party member
        kinds = ['party'] * n
    else:
        kinds = ['actor'] + (['suffix'] if '%s%s' in fmt else []) + ['thing'] * n
    w = _name_cells()
    return [w[k] for k in kinds[:n]]


# %s kinds where the default (actor first) is wrong. 04774 '%s%s %s': the third is a monster action, which starts
# its own row when it could overflow (insert._wrapped_actions), so it adds nothing to the row checked here.
ARG_KIND = {'exe:03130': ['thing'], 'exe:03244': ['thing'], 'exe:0483c': ['thing'], 'exe:048f9': ['thing'],
            'exe:04949': ['thing'], 'exe:04774': ['actor', 'suffix', 'none'],
            # healer, level-up and the attack/defence-raising spells (player spells): party members only
            'exe:03328': ['party'], 'exe:04909': ['party'], 'exe:04619': ['party'], 'exe:04631': ['party']}
_NAMES = None


def _name_cells():
    """Longest English party/monster name (actor) and item/spell name (thing), from script/exe.json."""
    global _NAMES
    if _NAMES is None:
        import extract
        ents = [e for e in extract.load(extract.out_path(extract.EXE))['entries'] if e['kind'] == 'text']
        mon = 0x66e58, 0x84                       # monster records (insert.MONSTERS): name pointer at +0
        names = [e for e in ents if e['group'] == 'party' or (e['group'] == 'monsters' and any(
            int(r, 16) >= mon[0] and (int(r, 16) - mon[0]) % mon[1] == 0 for r in e['refs']))]
        things = [e for e in ents if e['group'] in ('items', 'spells') and 0x1f58 <= e['off'] < 0x3128
                  and e['len'] != 30 and '%' not in e['jp'] and e['id'] not in EXE_FIELD]
        # party names are the defaults at exe 0x800 (no name entry seen in the game)
        _NAMES = {'actor': max(cells(e['en'] or e['jp']) for e in names),
                  'party': max(cells(e['en'] or e['jp']) for e in names if e['group'] == 'party'),
                  'thing': max(cells(e['en'] or e['jp']) for e in things), 'suffix': 2, 'none': 0}
    return _NAMES


def budget(e, prev_op=None):
    """Human-readable limit for a batch line: '26x3', '26x2', '20', '24~' (~ = soft)."""
    if e['id'].startswith('exe:'):
        n, hard = exe_budget(e)
        return '-' if n is None else f'{n}' + ('' if hard else '~')
    if e['op'] == '22':
        return f'{COLS}x{rows_budget(prev_op)}'
    n, hard = FIELD[e['op']]
    return f'{n}' + ('' if hard else '~')
