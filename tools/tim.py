"""PS1 TIM images: find, decode to PNG (docs/re/graphics.md).

    python -X utf8 tools/tim.py scan FILE..              list TIMs found inside files (offset, bpp, size)
    python -X utf8 tools/tim.py png FILE[@OFF] OUT.png   decode one TIM (CLUT 0) to PNG
    python -X utf8 tools/tim.py dumpall OUTDIR FILE..    every TIM in every file to OUTDIR/<file>_<off>.png
    python -X utf8 tools/tim.py --selftest

TIM: u32 0x10, u32 flags (bits 0-1 pmode 0=4bpp 1=8bpp 2=16bpp 3=24bpp, bit 3 CLUT present), then [CLUT block],
pixel block; each block = u32 len (incl. this 12-byte header), u16 x, y, w, h, data. Pixel-block w is in 16-bit units.
"""
import struct, sys, os

BPP = {0: 4, 1: 8, 2: 16, 3: 24}


def parse(d, o=0):
    """Return dict(off, end, bpp, w, h, clut, pix, cx, cy, px, py) or None if no valid TIM at o."""
    if o + 8 > len(d) or struct.unpack_from('<I', d, o)[0] != 0x10:
        return None
    fl = struct.unpack_from('<I', d, o + 4)[0]
    if fl & ~0xB:
        return None
    pm, p = fl & 3, o + 8
    clut, cx, cy = None, 0, 0
    if fl & 8:
        if p + 12 > len(d):
            return None
        ln, cx, cy, cw, ch = struct.unpack_from('<I4H', d, p)
        if ln != 12 + cw * ch * 2 or p + ln > len(d) or not cw or not ch:
            return None
        clut = [struct.unpack_from('<H', d, p + 12 + i * 2)[0] for i in range(cw * ch)]
        p += ln
    if p + 12 > len(d):
        return None
    ln, px, py, w, h = struct.unpack_from('<I4H', d, p)
    if ln != 12 + w * h * 2 or p + ln > len(d) or not w or not h or w > 1024 or h > 512:
        return None
    if pm < 2 and clut is None:
        return None
    pw = w * 16 // BPP[pm]
    return dict(off=o, end=p + ln, bpp=BPP[pm], w=pw, h=h, clut=clut, pix=d[p + 12:p + ln], cx=cx, cy=cy,
                px=px, py=py, pixoff=p + 12)


def rgb(c):
    return ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)


def to_image(t, pal=0):
    from PIL import Image
    w, h, pix, bpp = t['w'], t['h'], t['pix'], t['bpp']
    im = Image.new('RGB', (w, h))
    out = []
    if bpp == 4:
        cl = t['clut'][pal * 16:pal * 16 + 16]
        for b in pix:
            out += [rgb(cl[b & 15]), rgb(cl[b >> 4])]
    elif bpp == 8:
        cl = t['clut'][pal * 256:pal * 256 + 256]
        out = [rgb(cl[b]) for b in pix]
    elif bpp == 16:
        out = [rgb(c) for c in struct.unpack_from('<%dH' % (len(pix) // 2), pix)]
    else:
        out = [tuple(pix[i:i + 3]) for i in range(0, w * h * 3, 3)]
    im.putdata(out[:w * h])
    return im


def scan(d):
    o, found = 0, []
    while True:
        o = d.find(b'\x10\0\0\0', o)
        if o < 0:
            return found
        t = parse(d, o)
        if t:
            found.append(t)
            o = t['end']
        else:
            o += 4 if o % 4 == 0 else 1


def main(a):
    if a[0] == '--selftest':
        # 2x1 4bpp image with a 16-colour CLUT
        clut = struct.pack('<I4H', 12 + 32, 0, 480, 16, 1) + struct.pack('<16H', *range(16))
        pix = struct.pack('<I4H', 12 + 2, 0, 0, 1, 1) + bytes([0x21, 0x43])
        d = b'xx' + struct.pack('<II', 0x10, 8) + clut + pix
        t = scan(d)
        assert len(t) == 1 and t[0]['off'] == 2 and t[0]['w'] == 4 and t[0]['h'] == 1, t
        assert t[0]['end'] == len(d)
        print('selftest ok')
        return 0
    if a[0] == 'scan':
        for f in a[1:]:
            d = open(f, 'rb').read()
            for t in scan(d):
                print(f"{f} {t['off']:#x} {t['bpp']}bpp {t['w']}x{t['h']} vram {t['px']},{t['py']}")
    elif a[0] == 'png':
        f, _, off = a[1].partition('@')
        d = open(f, 'rb').read()
        to_image(parse(d, int(off, 16) if off else 0)).save(a[2])
    elif a[0] == 'dumpall':
        os.makedirs(a[1], exist_ok=True)
        for f in a[2:]:
            d = open(f, 'rb').read()
            for t in scan(d):
                name = os.path.join(a[1], f"{os.path.basename(os.path.dirname(f))}_{os.path.basename(f)}"
                                    f"_{t['off']:06x}.png")
                to_image(t).save(name)
                print(name, f"{t['bpp']}bpp {t['w']}x{t['h']}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
