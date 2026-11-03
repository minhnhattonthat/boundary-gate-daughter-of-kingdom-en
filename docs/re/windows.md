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
| equipped item name | equip screen | 30 | `%-30s 装備中 %2d` (English: `%-30s\nEquipped %2d`, the count on row 2) |
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

## Window engine (phase 7) — `tools/windows.py` lists every call

- **Text windows**: `openwindow 0x80021530(owner, x px, y px, w cells, h rows, ...)` and the variant
  `0x80021414(x, y, w, h, ...)` (status screen, message windows). A window wraps at exactly `w` cells and
  scrolls past `h` rows. Some JP rows rely on that wrap (the shop list row is exactly the window width), so an
  English row must keep the same cell count (`'G '` for `Ｇ`).
- **Backgrounds** are separate sprites cut from `\GRP\ITA_1.TIM`: `0x8001A280(img, x, y, ?, ?, ?, rect*)` and
  `0x8001A4C0(img, x, y, rect*)`, `rect = {u, v, w, h}` in the text region's data gaps (0xb74.., 0xcb8.., 0xdc4,
  0xe74, 0xed8, 0x1020/0x1028) or in `.data` (0x80074cb8/0x80074cc0, the field menu's top box, copied at run
  time). Moving or widening a text window without its background leaves a stone strip outside the frame.
- **English changes** (`insert.EXE_PATCHES` / `HALF_PATCHES`, en build only, every one asserts the original):
  field-menu column and submenu title box 4 -> 6 cells (Items/Magic/Equip/Status/Map/Config); the top-row box
  right of it 12 px right and 2 cells narrower (same right edge), backgrounds to match; equip item column and
  config value column follow their labels; equip compare box 13 -> 15 cells (list box 32 -> 30); command
  windows (Talk/Move/Status, battle Fight/Run/Status/Weapon/Magic/Items, Buy/Sell/Items) 6 -> 8 cells, 6 px
  further left (the room/battle backgrounds already cover it).
- **Status effects**: field-menu row `%-3s%-6s%-8s%-5s%-7sMP%3d/%3d` (KO, Sleep, Silence, Weak, Poison). The game
  starts this row at column 1 (`0x80021f80(win, 1, ..)` before the printf), so it has 38 of the box's 39 cells;
  one cell more wraps the last digit and scrolls the name/LV/HP row out of the 2-row box (phase 8, every
  party member, status or not). MP digits line up under the HP digits (cells 32-38). The items-menu party box is 19 cells and the JP itself abbreviates to one
  kanji there (毒/眠/黙): English uses Psn/Slp/Sil (flagged abbreviation, D12); `insert.EXTRA_STRINGS` gives that
  box its own short copy of 毒.
- Seen with every status set (`menu_field_fx`, `menu_items_fx`: warp var `STATUS`).

## Measured in phase 8 (QA tour)

- **Top box rows (39 cells x 2 rows)**: every row of the field-menu party box, the items header
  (`:%c%-20s %-9s  x%2d` / `%-30s Equip%2d`) and the magic header (`%-22s %-9s MP%3d`) must stay <= 38-39 cells
  and 2 lines: one cell or line more scrolls row 1 away (`test_field_party_rows_fit`). Use labels (常時/戦闘中/
  移動時) reach 9 cells ('In Battle'). Spells: warp var `SPELLS` (count u16 0x80126C22, ids s8 from 0x80126C30).
- **Healer menu** (exe:032ac): copied by inline lwl/lwr into a 21-byte stack buffer, so 20 bytes + NUL at most
  ('  Heal\n  Info\n  Exit'); longer text printed stack garbage ('Can ~~~').
- **Battle messages**: the window cuts at 26 cells mid-word. Player attack = `%s%s ` + `attacked\nwith %s.`;
  monster actions that can overflow behind the longest name using them start on their own row
  (`insert._wrapped_actions`, monster records 0x84 bytes from exe 0x66e58).
- **Destination lists 0x28/0x4e** (`room_62`): text from cell 2 (cursor in 0-1), 24 cells, one row an entry; a
  `\r` inside an entry puts the cursor on the wrong row.
- **Inline choice 0x19**: draws on the row after the text, so its page holds rows-1 text rows (`room_46`).
- **Ending narration**: centred in a 256 px band, 38 cells (longer runs off both edges); **cast/staff labels**:
  20-cell column (lint budgets hard).
- **Voiced events** (no 0x10 anywhere in the JP file, 94 files): pages turn on op `0x4a mm ss cc` (wait for the
  voice position) and the window is only shown once a print op returns, so a page break inside one op-22 text
  shows only its last page. Extra English pages become separate ops: `22 page / 4a t / 22 08 / 22 page`, `t`
  interpolated by text length between the neighbouring 0x4a (`insert._voiced_pages`).

## Measured in phase 7

- **NPC list (0x1c)**: drawn in the 26-cell message window after a 1-cell cursor: **25 cells** (scene
  `npcs_53`, "High Priest of Sorcery" = 22 fits). 0x28/0x4e (room destination lists) are presumably the same
  list routine: budget 25, soft until a scene shows one (`moves_13`/`moves_62` land in entry dialogue).
- **Choice (0x27)**: drawn inline in the message window row ("Save   Don't save", scene `save`); 10 cells per
  choice holds.

## Still to measure

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
