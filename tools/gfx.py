"""Graphics edits for the English build (docs/re/graphics.md).

G1: GRP/TITLE2.TIM (8bpp 256x240) carries the katakana reading バウンダリーゲート on the white bar under the English
BOUNDARY GATE logo. The English build blanks it (docs/decisions.md D13): the bar's text area is refilled with the
bar's own texture from the clear stretch to its right, row by row, so the bar's vertical shading is kept.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tim  # noqa: E402

TITLE = 'GRP/TITLE2.TIM'
KANA = (78, 68, 101, 14)        # x, y, w, h of the katakana on the bar (glyph pixels at x 82-173, y 69-80)
TEXTURE_X, TEXTURE_END = 180, 218   # clear bar texture (a darker speck sits at x 220, rows 79-81)
BAR = range(43, 48)             # CLUT indices of the bar's white/grey texture


def title_en(data):
    t = tim.parse(data)
    assert t and t['bpp'] == 8 and (t['w'], t['h']) == (256, 240), 'TITLE2.TIM is not the 8bpp 256x240 original'
    out, w, p = bytearray(data), t['w'], t['pixoff']
    x0, y0, kw, kh = KANA
    span = TEXTURE_END - TEXTURE_X
    for y in range(y0, y0 + kh):
        row = p + y * w
        src = [data[row + TEXTURE_X + i] for i in range(span)]
        assert all(c in BAR for c in src), f'texture source on row {y} is not plain bar'
        for i in range(kw):
            out[row + x0 + i] = src[i % span]
    return bytes(out)


if __name__ == '__main__':
    tree = Path(__file__).resolve().parent.parent / 'work' / 'disc' / 'tree'
    new = title_en((tree / TITLE).read_bytes())
    p = tim.parse(new)['pixoff']
    x0, y0, kw, kh = KANA
    left = [x for y in range(y0, y0 + kh) for x in range(x0, x0 + kw) if new[p + y * 256 + x] not in BAR]
    print(f'{TITLE}: {len(left)} non-bar pixels left in the katakana area')
    sys.exit(1 if left else 0)
