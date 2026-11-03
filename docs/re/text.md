# Text: encoding, printer, windows, exe strings, free space

## Encoding (verified)

Plain **Shift-JIS** (cp932) everywhere: decoded known on-screen strings from the scripts (EVENT00 0x4EEA3
`王国の名はモーダルグロウ` = the first dialogue box) and the exe (`最初から始めますか？`, menu `道具 魔法 装備 状態 設定`).
Single bytes 0x20-0x7E and half-width 0xA1-0xDF are drawn as half-width glyphs. No table file is needed; use
`jp_left.py --sjis` for leftover scans. No compression anywhere in the text path.

## Printer `0x80023288(win, ptr, speed)` (verified by disassembly; returns ptr past the terminating 0)

Per byte:

| byte | effect |
|---|---|
| 00 | end of string |
| 08 | clear window (`0x80021FD0` + redraw) |
| 0A, 0D | new line |
| 0B x | set window field 0x1B = x - '0' (1 arg; colour, guess) |
| 0C x | set window field 0x1A = x - '0' (1 arg; colour, guess) |
| 10 | wait for a button (prompt), used before 08 to page |
| 13 | `0x80022708` (unknown) |
| 17 | wait 60 frames |
| 19 | `0x80022A9C`, result stored at 0x80126B80 (inline choice? guess) |
| other 01-1F | ignored |
| `\` x | escape: `\N` / `\n` = new line, else nothing |
| `@` | `0x80022A68(0x1E)` then draws '@' (avoid '@' in English) |
| `:` x | icon glyph 0x8000+x (ICON12.TIM item icons); `::` = literal ':' |
| 81-9F, E0-EF + byte | full-width SJIS glyph, 2 cells |
| any other byte | half-width glyph, 1 cell |

So English must write `::` for a colon and must not use `@` or `\` as text.

## Windows

- Dialogue (op 0x22): window at x=0x50, y=0xB0, **26 half-width cells x 3 rows**; a cell is 6 px, a full-width
  character takes 2 cells (12 px). Japanese lines are <= 13 full-width characters, usually 2 rows per page.
- Text past the last column wraps to the next row by itself (`0x8002288C` called when the column overflows).
- **Half-width ASCII renders natively** (verified: poked `ABC..xyz 0-9 .,!?'"-()&/` into EVENT00's second message in
  RAM, `work/qa/ascii/zoom.png`): upper, lower case, digits and punctuation all have glyphs. Fixed 6 px pitch;
  W/M are cramped. 26 English characters per row x 3 rows per page with no engine work; a VWF is optional polish.
- Other windows (menus, shop, battle) draw exe strings with printf formats (`%-20s`, `%-22s`, `:%c%-20s` = icon +
  20-cell name): those widths are the per-field limits for item/spell names (phase 5 width gate).

## Exe strings (`SLPS_009.07`, file 0x800-0x5700 = RAM 0x80010000-0x80014F00)

Mixed with small data (window coords, printf formats). Contents in order: party names; title menu; window layouts
and menu labels; settings menu (戦闘アニメ 見る/見ない, 敵の出現 少ない/多い) and a **leftover debug menu**
(サウンドテスト, 効果音テスト, マップ構造, マップ番号：, 戦闘に入る：) at 0xE38-0xF7C; map/room names (0x105C-0x1F58, incl. debug
names like ダミールーム); weapons/armour/items with descriptions (0x1F74-0x2C8A); spells (0x2CB4-0x3128); shop, inn,
healer messages (0x3128-0x3378); memory-card messages (0x3378-0x37CF); item-use results; game over; monster names and
their attack lines (0x3A30-0x45AB); battle messages (0x45BB-0x494B); ending narration (0x4CA9-0x4F4C); credits
(0x5020-0x5448); prologue lore (0x5499-0x567F). A kana-only scan misses kanji-only labels (`道具`), so extraction
must go by references, not by a byte scan.

References seen (guess until phase 4 sweeps them all): data pointer tables (item names: table at 0x80075010,
monsters 0x80075B40, map names 0x80074E58), `lui/addiu` pairs (`最初から始めますか？` from 0x80016644), and strings
with no direct pointer (fragments in printf chains, or a pointer to a preceding field). Use `disasm.py xref` per
string; also check `$gp`-relative loads.

## Free space (all guesses until tested)

- **Scripts**: section 7 is last in each file, so text can grow in place. Files are loaded whole into a malloc heap
  (EVENT00 at 0x8013067C; MAPMES00, the largest file at 0xABC32, at 0x800DF7DC-0x8018B40E with other allocations
  right after it, and the top ~56 KB below the stack mostly zero in that town). Growth of a few KB per file is
  probably fine; **test in phase 5** by growing MAPMES00's script by 4 KB and touring a town, battle and menu.
- **Exe**: data ends at 0x800CA958 (BSS starts there, cleared at boot), so nothing can be appended in place. English
  names are usually shorter in bytes than the SJIS (1 byte per half-width letter), so most exe strings fit in place.
  Zero runs inside the data (RAM 0x80070F6F +0x79C, 0x80071E85 +0x6EB, 0x800725AF +0x69F, 0x80073670 +0x540,
  0x800C8E9C +0x1070) are candidates only: trap-fill and tour before using any. Debug-only strings (room names, debug
  menu) can be reused if the debug menu is dropped from the release.
