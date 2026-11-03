# Debug tool: location word, main loop, leftover debug window, warp

**Verified** by the warp runs (`tools/debug/warp.py`, every scene in `tools/debug/scenes.tsv` from a cold boot,
shots in `work/qa/warp/<scene>/final.png`, states in `work/states/<scene>.sstate`).

## Game state (RAM)

| Address | Size | Meaning |
|---|---|---|
| `0x80126C0A` | u16 | **location word**: `0x100|map` (3D map, MAPMES), `0x200|room` (ROOMMES), `0x400|event` while an event runs, `0x800` ending, `0x1000` back to logos/title |
| `0x80126C0C` | u16 | location to return to from a room (the map word saved by ops 0x25/0x36) |
| `0x80126C04/06/08` | u16 | map X, Y (0-0x17), direction (0-3; 0x80074CA8 = 北東南西 names) |
| `0x80126800` | u32[256] | story vars (script ops 00-07). var 0 = main story progress (10, 20 ... 200) |
| `0x8012B408` | u16 | debug flag: != 0 adds `ＤEB` as 7th field-menu entry (tested at 0x80029C00). New Game clears it (0x80016A5C) |
| `0x80129C00` | u8 | 1 while a battle runs (set by the battle entry 0x8003483C) |
| `0x800CF250` | ptr | script pointer (next op byte; an op that waits has already advanced past its op byte only) |
| `0x80126468` | ptr | current script section base (bytecode from +0x1C0) |

Map names: pointer table `0x80074CDC` (by map); room names `0x80074E6C` (by room).

## Main loop (`0x80016AD4`)

Reads the location word each pass: `& 0x800` → ending `0x8003B124` (ENDING.PAK, CD track 88) then title;
`& 0x1000` → logos/title; `& 0x100` → load map (`0x8001CC08`) and run the field loop `0x8001C0DC`; else room loop
`0x8002C714`. Between the field loop returning and the next pass the screen fades out (`0x80019C34`, several frames).

New Game (`0x80016A50`): location = 0x400, loads the literal `EVMES0\EVENT00.BIN` (RAM 0x8001011C) and runs it; then
location = 0x100 (map 0) at X 12, Y 5, dir 2, whatever the event did.

Script ops that move the player (correcting `script.md`): **0x35** `[map, x, y, dir]` goto map; **0x25** `S B` and
**0x36** `B` enter room (saves the map word in 0x80126C0C, turns dir by 2); **0x37** `B` run event B (runner
0x8001F524: loads `EVMES%d\EVENT%02d.BIN` with dir = n / 25, runs it, restores the location and reloads the
map/room); **0x48** ending (location = 0x800); **0x19** end script. All of them return -2/-1 to stop the script.

## Leftover debug window (`ＤEB`, handler 0x80028860)

Set the debug flag, open the field menu (square), 7th entry. Lines: map number, X, Y, direction, enter battle; left /
right change the value, circle applies. Its values sit in stack locals while it waits: `[value, 0, max]` u32
triples at sp+0x130 (map, max 0x53), +0x13C (X, 0x17), +0x148 (Y, 0x17), +0x154 (dir, 3), +0x160 (battle formation,
1-0x8C). Applying a changed map stores `map|0x100` in the location word and the field loop exits once the menu is
closed (cross). The battle line calls `0x8003483C(formation, 0)`. Also prints the 6 map-cell bytes ahead
(マップ構造(一歩前)). It is debug-only: its strings (exe 0xE90-0xF7C) need translating only if we ship it, which we
don't (the release never sets the flag).

## Warp (`tools/debug/warp.lua`, no debugger)

1. Boot route to New Game (`tools/routes/boot.txt`). When the location word becomes 0x400 the vars are set.
2. `KIND='event'`: the exe's `EVMES0\EVENT00.BIN` literal is rewritten in RAM before New Game, so the game loads and
   runs the chosen event itself.
3. Otherwise EVENT00 is cut after its first op (`1e 00`, a fade: 0x19 written at script +0x1C2 while the pointer is
   on +0x1C1), New Game drops the party on map 0, the DEB window is opened by presses, its map local is set to the
   target map (or the marker 0x53 for rooms / ending / reset), and when the location word reads `marker|0x100` the
   real word, position and return map are written during the fade, before the main loop reads them.
4. `KIND='battle'`: same to the DEB window, battle line with the formation local overwritten. A battle started
   from the DEB window returns to it afterwards, including after Game Over.

Party (for `GOD` / `HP`): count u16 `0x80126C0E`, order bytes `0x80126C10`, member i at `0x80126C14 + 60*i`: +2 HP
(s16), +6 MP, +8 EXP (u32), +0xC LV. Max HP is computed (`0x8002A598`).

Gotcha: with `emu.py --debugger` (interpreter) the ending jumped to 0x00010004 and the emulator paused in the
exception handler forever; the same ending plays fine on the normal (dynarec) core. The warp needs no exec hooks, so
it runs without the debugger (4x faster too).

Scene coverage (`mkscenes.py`): every map with an op 0x35 entry (all but MAPMES95, which nothing leads to), every
reachable room (return map = the map whose script enters it), every event file (vars a caller tests with == preset;
events 30 and 79 have no op 0x37 caller), field menus, debug window, battle by formation, ending, reset. Room-only
NPC branches and events depend on more story vars than the presets; add VARS to a scene when QA needs a branch.
