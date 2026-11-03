# Reverse-engineering notes

One file per subsystem (text engine, pointers, compression, font, graphics). Mark every finding with how far it is
proven, so a later session doesn't build on a guess:

- **verified** - and how: a decoded known string, a corrupt-and-boot test, a breakpoint hit on the drawing path, a
  passing roundtrip test. Name the test or savestate.
- **guess** - and why it seems likely (byte pattern, another game, an earlier patch's notes). Promote it to verified
  before code depends on it.

Addresses are for the dump in `rom.sha1` unless a note says otherwise.

| File | Covers | State |
|---|---|---|
| `files.md` | disc layout, which files hold text, *MES container, dir = n // 25, leftover files | verified |
| `script.md` | event-script interpreter, opcode operand table, jumps and routine table (the pointers) | verified (parser test) |
| `text.md` | Shift-JIS, printer control codes, window 26x3, native ASCII, exe string regions, free space | encoding/printer verified; exe pointers and free space guesses |
| `graphics.md` | graphics-text survey (static sweep done; runtime screens listed for phase 2) | static verified |

Prior work: none found (web search 2026-11-03: no English or other fan patch for the PS1 or PC-FX version).

RE tools in `tools/`: `evscript.py` (container + script parser), `re_ops.py` (opcode operand lengths under unicorn),
`tim.py` (TIM decode), `lua/poke.lua` (write RAM in a run, e.g. test a string).
