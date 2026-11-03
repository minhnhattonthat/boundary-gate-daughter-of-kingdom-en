# Window and field budgets (the width gate)

Every budget below is either **measured** in-game (shot named), or the game's own **printf field width**
(`%Ns` in the exe's format string is the contract: the next column starts after it), or a **guess** and
flagged as such. Translators write to these numbers; the phase-7 lint enforces them.

Instruments: `tools/build.py --ruler` (78 digits in every dialogue page, 20 digits in every field,
digits keeping their original length in exe strings) and `--marker` (id in every line), both cold-booted
with `tools/debug/warp.py`. Shots live under `work/qa/` (gitignored).

## Print model (measured)

- The font is fixed-pitch, **6 px per half-width cell**; a full-width Shift-JIS glyph is two cells (12 px).
- The message window holds **26 cells x 3 rows**. Verified: 78 digits (3 x 26) fill exactly three rows
  with no wrap and no scroll (`work/qa/ruler/room_00/final.png`), and 80 digits push the page up by one
  row (`work/qa/ruler/new_game/`), so the wrap point is exactly 26 and row 4 scrolls.
- Text past column 26 **wraps by itself**. An explicit `\r` (0x0D) still starts a new row; a page with
  more than three rows scrolls.
- The button-wait arrow (0x10) is drawn **below row 3**, centred, in the window's bottom padding: it does
  not consume text cells (`work/qa/ruler/room_00/final.png`).
- All printable ASCII has a glyph (upper, lower, digits, punctuation) — the `--torture` build draws
  every allowed ASCII character at full width in one page (`work/qa/torture/new_game/`). `@` and `\` are
  printer escapes and `:` starts an icon code, so English writes `::` for a colon and never `@`/`\`.

## Script text (`script/*.json`, one entry = one page)

| Variant | Where | Budget | Rows | How |
|---|---|---|---|---|
| 0x22 dialogue | message window | **26 cells** per row | **3** | measured (ruler) |
| 0x21 speaker line | first row of the same window | 26 | 1 | measured (26 from the box; JP max 16) |
| 0x23 location banner | same window | 26 | 1-2 | measured window; JP max 26 |
| 0x27 choice option | choice window | 10 | 1 | guess: JP max 10 cells (`記録しない`); the choice screen is not reachable from the warp yet |
| 0x1c NPC name (talk list) | room list column | 16 | 1 | guess: JP max 16 (`マイヨールの息子`); list screen not reachable from the warp yet |
| 0x25 building label | map location label | 24 | 1 | format `現在地：  %24s`; JP max 14 |
| 0x28 room menu item | room list column | 12 | 1 | guess: JP max 12 (`アモーク要塞`) |
| 0x4e room menu item | room list column | 22 | 1 | guess: JP max 22 (`アンブローズ北地区大門`) |

A page's row count is fixed by the script: a two-row page that grows to four rows scrolls. When English
needs more room, the build can add pages (duplicate the `0x22` + clear op) rather than cut the line.

## Exe text (`script/exe.json`)

| Field | Screen | Budget | How |
|---|---|---|---|
| item / shop / equip name | items, shop, equip | **20 cells** | formats `:%c%-20s %-6s  所持数 %2d`, `:%c%-20s`, `:%c%-20s    %6ldＧ`, `%-20s ` |
| equipped item name | equip screen | 30 | `%-30s 装備中 %2d` |
| spell name | magic, battle spell list | 22 | `:%c%-22s`, `%-22s  %6s  消費MP %2d`, `%-22s  %2d` |
| party member name | menu rows, battle | 14 | `%-14s      ＬＶ %2d  ＨＰ %3d/%3d` |
| current location | map screen | 24 | `現在地：  %24s` |
| price / gold | shop, inn | 6-7 | `%6ldＧ`, `%7ld G`, `%-4ldＧ` |
| settings toggle | settings menu | 12 | JP max 12 (`見ない`, `少ない`, `移動中`); shot `work/qa/marker/warp/menu_settings` |
| yes / no | boot, inn, shop | 12 | JP max 12 (`いいえ`), shot of boot prompt |
| battle command block | battle command list | 3 rows of 6 cells | `'  戦闘\n  武器\n  逃亡'`: a preformatted 3-row block, rows start with 2 spaces |
| battle / monster message | message window | 26 x 3 | measured window (`work/qa/ruler/battlemsg/`); the longest JP line is 22 cells |
| save / memory-card text | message window | 26 x 3 | JP max 35 cells, wraps into the 3 rows |
| ending / credits / prologue narration | full-width band at the bottom | **38 cells** | conservative: the band is full screen (320 px), the longest JP narration line is 38 cells; keep English lines at or under the original's |

## Still to measure (phase 6/8)

- The choice window (0x27) and the room list (0x1c/0x28/0x4e) need a warp scene that leaves the room's
  entry dialogue: add `EXTRA` scenes to `tools/debug/mkscenes.py` that press the room-menu button, then
  read the field width off the ruler build.
- The ending / credits narration wrapping limit (the window is wider than the message box).
- Name entry (if the game has one): the party names at exe 0x800 are defaults only; confirm.

## Field-width cross-check (phase 5)

The item list screen (`work/qa/ruler/menu_items/final.png`, `work/qa/marker/warp/menu_items/`) shows the
name column starting ~25 px into the row and the next column (count / `x%d`) at ~145 px: 120 px = 20 cells,
which matches `% -20s`. The shop, equip and magic screens use the same row builder.

## Marker-build evidence (phase 5)

- `tools/build.py --marker` cold-boots and passes **all 216 warp scenes** (`tools/debug/warp.py --all
  --rom build/boundary-gate-marker.cue --jobs 6`): no scene hangs, crashes or draws Japanese where marked
  text was drawn.
- `jp_left.py --sjis` on the marker build attributes every remaining Japanese run through a
  `mkpsxiso -noisogen -lba` file map: **0 hits inside any *MES script section**, 0 in the exe; the rest are
  map wall-texture bytes (MAPMES00-05, a few ROOMES), TIM pixels and VAB audio. That is the coverage proof:
  what still looks like text-like bytes is not text, and the extractor has every displayed string.
