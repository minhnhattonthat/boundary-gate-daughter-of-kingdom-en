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
    assert pages[0][2].startswith(' ')                 # hanging indent inside the quote
    assert game.endswith('\x10') and W.PAGE in game     # auto page break, trailing wait kept
    assert W.controls(game) == ['\x10']


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
