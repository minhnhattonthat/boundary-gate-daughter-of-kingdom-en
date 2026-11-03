"""Shift-JIS text codec for the game (docs/re/text.md).

Everything on screen is plain Shift-JIS: full-width glyphs take two bytes (and two 6 px cells),
half-width East Asian characters and ASCII take one (one cell). The engine prints raw bytes up to a
terminating 0x00, so decode()/encode() have to be byte-exact over the bytes the game actually stores
rather than "close enough" cp932.

decode() maps every byte sequence to exactly one character and encode() maps it back to the same bytes:
  * 0x01-0x7E          -> U+0001-U+007E (ASCII and the printer's control codes, text.md table)
  * 0xA1-0xDF          -> U+FF61-U+FF9F (half-width katakana, one cell)
  * lead 0x81-0x9F,E0-0xEF + trail -> the cp932 character (two cells)
  * anything else      -> SjisError (0x80, 0xA0, 0xFD-0xFF and bad trails are not text)
encode() refuses characters with no Shift-JIS form, so English insertion fails in the build rather
than writing a half-random byte.

English rules from the printer (text.md): ':' starts an icon glyph, so a literal colon is '::'; '@' and
'\' are control escapes. encode_en() applies those rules and enforces half-width ASCII only.

usage: python -X utf8 tools/sjis.py TEXT.. (decodes/roundtrips its arguments, selftest on no argument)
"""
import sys

LEAD = [(0x81, 0x9F), (0xE0, 0xEF)]
HALF = (0xA1, 0xDF)
HALF_CH = 0xFF61


class SjisError(ValueError):
    """Bytes or characters that are not Shift-JIS text."""


def _lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def _trail(b):
    return 0x40 <= b <= 0x7E or 0x80 <= b <= 0xFC


def decode(raw):
    """Bytes -> str, one char per glyph, byte-exact inverse of encode()."""
    out = []
    i, n = 0, len(raw)
    while i < n:
        b = raw[i]
        if 0x01 <= b <= 0x7E:
            out.append(chr(b))
            i += 1
        elif HALF[0] <= b <= HALF[1]:
            out.append(chr(HALF_CH + b - HALF[0]))
            i += 1
        elif _lead(b):
            if i + 1 >= n or not _trail(raw[i + 1]):
                raise SjisError(f'lead byte {b:#04x} with bad trail at {i}')
            try:
                ch = raw[i:i + 2].decode('cp932')
            except UnicodeDecodeError:
                raise SjisError(f'{raw[i:i + 2].hex()} at {i} is not a cp932 character') from None
            out.append(_dups().get(raw[i:i + 2], ch))
            i += 2
        else:
            raise SjisError(f'byte {b:#04x} at {i} is not text')
    return ''.join(out)


_ENC = None
_DUP = None


def _encoder():
    """char -> bytes, built once from cp932. A duplicate cp932 mapping keeps its lowest byte pair, which
    is the one decode() produces for any pair cp932 has more than one of (checked by the selftest)."""
    global _ENC, _DUP
    if _ENC is None:
        enc = {}
        for b in range(0x01, 0x7F):
            enc[chr(b)] = bytes([b])
        for b in range(HALF[0], HALF[1] + 1):
            enc[chr(HALF_CH + b - HALF[0])] = bytes([b])
        dup = {}
        nxt = 0xE000
        for lo, hi in LEAD:
            for b0 in range(lo, hi + 1):
                for b1 in range(0x40, 0xFD):
                    if not _trail(b1):
                        continue
                    pair = bytes([b0, b1])
                    ch = pair.decode('cp932', 'ignore')
                    if not ch:
                        continue
                    if ch in enc:
                        # cp932 duplicate code (e.g. 0x8790 for a symbol also at 0x81xx): give it a
                        # private-use character so decode()/encode() stay byte-exact on real data
                        dup[pair] = chr(nxt)
                        enc[chr(nxt)] = pair
                        nxt += 1
                    else:
                        enc[ch] = pair
        _ENC, _DUP = enc, dup
    return _ENC


def _dups():
    _encoder()
    return _DUP


def encode(text):
    """str -> bytes; raises SjisError on a character the game's font cannot be asked to draw."""
    enc = _encoder()
    out = bytearray()
    for i, ch in enumerate(text):
        b = enc.get(ch)
        if b is None:
            raise SjisError(f'{ch!r} (U+{ord(ch):04X}) at {i} has no Shift-JIS form')
        out += b
    return bytes(out)


def encode_en(text):
    """str -> bytes for an English line, applying the printer rules ('::' for ':', no '@' or '\\')."""
    if '@' in text or '\\' in text:
        raise SjisError("'@' and '\\' are printer control escapes: rephrase")
    for i, ch in enumerate(text):
        if ord(ch) > 0x7E or (0x7F <= ord(ch) <= 0x9F):
            raise SjisError(f'{ch!r} (U+{ord(ch):04X}) at {i} is not half-width ASCII')
    return encode(text.replace(':', '::'))


def cells(text):
    """Width in 6 px printer cells (a full-width glyph is two)."""
    return sum(2 if ord(ch) > 0x7E and not (HALF_CH <= ord(ch) <= 0xFF9F) else 1 for ch in text)


def selftest():
    """Every cp932 byte pair decodes and encodes back to itself; ASCII, half-width and controls too."""
    bad = []
    for lo, hi in LEAD:
        for b0 in range(lo, hi + 1):
            for b1 in range(0x40, 0xFD):
                if not _trail(b1):
                    continue
                pair = bytes([b0, b1])
                try:
                    if encode(decode(pair)) != pair:
                        bad.append(pair)
                except SjisError:
                    pass  # unassigned cp932 code: not a character, so not text
    for b in list(range(0x01, 0x7F)) + list(range(HALF[0], HALF[1] + 1)):
        if encode(decode(bytes([b]))) != bytes([b]):
            bad.append(bytes([b]))
    if encode_en("Hi: it's 5 o'clock.") != b"Hi:: it's 5 o'clock.":
        bad.append(b':')
    for t in ('ＨＰ', 'ｱｲｳ', '王国の名はモーダルグロウ'):
        if decode(encode(t)) != t:
            bad.append(t.encode('cp932'))
    if cells('ＡＢ') != 4 or cells('AB') != 2:
        bad.append(b'cells')
    return bad


def main(argv):
    if not argv:
        bad = selftest()
        for b in bad[:20]:
            print(f'FAIL {b!r}')
        print(f'selftest: {len(bad)} failures')
        return 1 if bad else 0
    bad = 0
    for a in argv:
        text = ' '.join(argv)
        break
    try:
        raw = encode(text)
        print(f'{decode(raw)!r} -> {raw.hex()}')
    except SjisError as e:
        print(f'FAIL {e}')
        bad = 1
    return bad


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
