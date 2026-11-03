"""English layout (tools/wrap.py) and the batch-line checks (tools/lint.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
import lint as L  # noqa: E402
import wrap as W  # noqa: E402


def test_layout_wraps_and_pages():
    game, pages = W.layout('Risp\r"I simply must see my sister. Please, help me until I can see her."\x10', 3)
    assert all(W.cells(r) <= W.COLS for p in pages for r in p)
    assert all(len(p) <= 3 for p in pages)
    assert pages[0][0] == 'Risp' and pages[0][1].startswith('"')
    assert len(pages) == 2 and pages[0][-1].endswith('sister.')   # 4 rows: cut at the sentence, not 3 + 1
    assert pages[1][0].startswith(' ')                 # hanging indent inside the quote
    assert game.endswith('\x10') and W.PAGE in game     # auto page break, trailing wait kept
    assert W.controls(game) == ['\x10']


def test_overflow_pages_end_at_sentences():
    """Overflow pages start at sentences (or after a JP button wait) where they can, and never end on a function
    word when a content word or clause will do (phase 8 QA: 'weapons and / armour', 'Temple of / Knowledge')."""
    _, p = W.layout('"Dangerous times, these.\x10 Keep your weapons and armour properly equipped."', 3)
    assert p == [['"Dangerous times, these.\x10'], [' Keep your weapons and', ' armour properly', ' equipped."']]
    _, p = W.layout('"I was walking down the street when all of a sudden I got blown off my feet... '
                    'When I came to, I was lying here."', 3)
    assert len(p) == 2 and all(len(x) <= 3 for x in p)
    assert all(W._cut(x[-1].split()[-1]) < 6 for x in p[:-1])
    _, p = W.layout('One two three four five six seven eight nine ten eleven twelve thirteen.', 1, cols=12)
    assert len(p[0]) == 1 and all(len(x) <= 3 for x in p)   # still fits whatever the cuts cost
    assert W.layout('Short.', 3)[1] == [['Short.']]


def test_choice_keeps_its_row():
    """An inline choice (0x19) draws on the row after the text: the last page leaves it one row (room_46)."""
    _, p = W.layout('Would you come to the dead end on the west side?\x19', 3, quote=True)
    assert len(p[-1]) <= 2
    _, p = W.layout('Would you come to the dead end in the west?\x19', 3, quote=True)
    assert len(p) == 1 and len(p[0]) == 2


def test_continuation_indent():
    _, pages = W.layout('and so on."', 3, quote=True)
    assert pages[0][0] == ' and so on."'


def test_tsv_roundtrip_exe():
    jp = ':%c%-20s    %6ldＧ\x0c1'
    t = W.to_tsv(jp, exe=True)
    assert t == '<icon>%-20s    %6ldＧ<0c>1'
    assert W.from_tsv('<icon>%-20s %6ldG: x<0c>1', exe=True) == ':%c%-20s %6ldG:: x\x0c1'


def test_check_unit_catches_printf_order_and_controls():
    u = {'jp': '%sに%dのダメージ', 'exe': True, 'prev': [None],
         'entries': [{'id': 'exe:045b5', 'group': 'battle', 'len': 16, 'jp': '%sに%dのダメージ'}]}
    assert not L.check_unit(u, '%s takes %d damage', [])[0]
    assert L.check_unit(u, '%d damage to %s', [])[0]
    d = {'jp': 'リスプ\r「はい\x10', 'exe': False, 'prev': [None],
         'entries': [{'id': 'X:1', 'op': '22', 'group': 'dialogue', 'jp': 'リスプ\r「はい\x10'}]}
    terms = [('リスプ', ['Risp'], [])]
    assert not L.check_unit(d, 'Risp / "Yes."<wait>', terms)[0]
    assert L.check_unit(d, 'Risp / "Yes."', terms)[0]          # lost the wait
    assert L.check_unit(d, '"Yes," said Risp.<wait>', terms)[0]  # lost the name row
    assert L.check_unit(d, 'Lisp / "Yes."<wait>', terms)[0]     # glossary


def test_check_unit_keeps_original_page_breaks():
    jp = '「はい」\x10\x08「いいえ」\x10'
    d = {'jp': jp, 'exe': False, 'prev': [None],
         'entries': [{'id': 'X:2', 'op': '22', 'group': 'dialogue', 'jp': jp}]}
    assert not L.check_unit(d, '"Yes."<wait><clr>"No."<wait>', [])[0]
    assert not L.check_unit(d, '"Yes."<wait><clr>"Well."<wait><clr>"No."<wait>', [])[0]  # added page ok
    assert L.check_unit(d, '"Yes." "No."<wait>', [])[0]                                   # dropped page


def test_npc_labels_are_per_room():
    keeper = {u['src']: u for u in L.units() if u['jp'] == '主人'}
    assert len(keeper) > 1      # one unit per room, so each room may name its own proprietor
