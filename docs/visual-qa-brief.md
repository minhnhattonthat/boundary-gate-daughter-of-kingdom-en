# Visual-QA reviewer brief - Boundary Gate: Daughter of Kingdom (PS1)

You review contact sheets from the English build's QA tour (`tools/tour.py`) and give each one a verdict. Read-only on
everything except your one verdict file: no edits to the repo, no git, no subagents.

## Inputs (in your dispatch)
- A chunk file: one `id<TAB>path` line per sheet. Read every sheet in it; none may be skipped.
- Your verdict file: `work/qa/verdicts/<chunk>.tsv`.
- The original disc's sheets: `work/qa/tour_jp/sheets/<same file name>`, and `glossary.md`.

## What the sheets are
One scene per sheet id (`ev_NN` story events, `room_NN` rooms: each NPC in the Talk list in turn, `map_NN` town and
dungeon maps, `menu_*`, `shop`, `healer`, `save`, `battle`, `game_over`, `ending`, `new_game` = the EVENT00 prologue).
Tiles are in frame order, row by row; most tiles are the screen just before a button press, i.e. a finished page.
Screen 320x240: the picture on top, the message window (26 cells x 3 rows of 6 px glyphs) bottom right, the portrait
or room menu (Talk / Move / Status) bottom left.

## How to look
- Read each sheet whole first. Where text is small, zoom into it with
  `python -X utf8 "$(python tools/skill.py)/scripts/sheet.py" SHEET.png --crop x,y,w,h --zoom 2 --out <scratch>.png`.
- When something looks wrong, open the same file from `work/qa/tour_jp/sheets/`. If the original shows the same
  thing, it is the game's own behaviour: `ok`, with a note.

## Judge
An `issue` is any of:
- Japanese still visible (the debug menu `menu_debug` excepted: it stays Japanese by design);
- text overflowing a box, clipped by a frame, or running off screen;
- garbage tiles, wrong or missing glyphs, a strike or stray pixels across letters;
- broken line breaks: a word split mid-line, a page ending mid-sentence, a one-word last page;
- an empty box where text belongs;
- a name that differs from `glossary.md`;
- English that reads wrong for the picture (a speaker label on the wrong person, a menu label that lies).

Standing non-bugs, `ok`:
- text still typing out, a box mid-fade or mid-scroll, a cursor caught mid-blink;
- a map or scene still loading after a warp; the title logo or a black picture where a warped event's previous scene
  would have left its picture (events entered out of story order);
- anything identical in the original's sheet (same layout, same blank, same picture), including a sheet whose route
  ran out of NPCs and repeats the last one;
- the first page of a talk keeps its 1-space hanging indent inside a quote, later pages lose it: the printer drops
  leading spaces after a page clear (the original does the same);
- `::` never shows: it is the printer's escape for one ':';
- the title screen's white bar under BOUNDARY GATE is empty on purpose (the katakana reading was removed, D13).

## Verdicts
Write your verdict file once you have read every sheet, one line per id in the chunk:
`id<TAB>ok|issue<TAB>what and where` (for an issue: which tile, which text, what is wrong).
Then return a short summary: counts, and the issues one per line.
