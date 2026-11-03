# Event script bytecode

**Verified**: `tools/evscript.py` walks all 203 reachable *MES scripts end to end, and every jump target and routine
offset lands on an instruction boundary (`tests/test_evscript.py`). Operand lengths come from running each handler
under unicorn with a real RAM dump (`tools/re_ops.py`) plus disassembly of the handlers that wait or loop.

## Interpreter

- Script pointer: global `0x800CF250`. Dispatcher `0x8002056C`: `op = *ptr++`, `call table[op]` (table at
  `0x8005224C`, 0x56 entries), loop while the handler returns 0.
- Script base (start of section 7) in `0x80126468`.
- Section 7 layout: 32 routine entries x 14 bytes (`u16 flags` 0x00FF = used, `u16`, `s16 offset` from script base,
  `char name[8]`, ASCII like `char00`, `move00`), then bytecode from 0x1C0. Ops 0x09/0x12 (call routine by index),
  0x1C, 0x28, 0x4E (bind an NPC/menu item to a routine index) refer to routines through this table.

## Pointers that must be fixed when text changes length

1. **Relative jumps** `J` = s16, relative to the end of the instruction: ops 0x00-0x05 (`B var, D const, J`:
   compare var[B] with const: ==, !=, <, >... and jump), 0x08 (`J`, goto).
2. **Routine table offsets** (s16 from script base), 32 per file.
3. Ops 0x37 (run event: keeps `ptr - base` while the event replaces the script, verified in `debug.md`) and 0x39
   store `ptr - base` at run time (save files / battle return): consistent within a build,
   but a **save made on another build resumes at a stale offset** (same as any script-layout change). Old saves of the
   Japanese game are not expected to carry over.

No absolute pointers into the script were found (no handler adds a stored absolute address). Growth is safe once 1 and
2 are rewritten; `parse()` gives every J operand and the routine table.

## Operand formats (`FMT` in tools/evscript.py)

B = u8, W = 2 bytes, D = u32, J = s16 jump, S = zero-terminated string, Nn = n bytes.

| op | fmt | meaning (where known) |
|---|---|---|
| 00-05 | B D J | compare var[B] (table 0x80126800) with D, jump if true (00 ==/!=, 02 <, 04 > family) |
| 06 07 | B D | set/add var |
| 08 | J | goto |
| 09 12 | B | call routine B |
| 0a 0b 0d 15 1b 1e 1f 20 29 2f 30 36 37 40 41 43 45 4f 51 54 | B | various; 36 enter room B, 37 run event B (`debug.md`) |
| 19 | - | end script; 35 (D) = goto map [map, x, y, dir]; 48 = ending (`debug.md`) |
| 0c 18 2c 2d 2e 39 46 47 | W | |
| 0e 16 33 35 38 49 | D | 16 uses 3 of its 4 bytes |
| 0f 10 11 | B W | |
| 13 3a | N5 | 13 = 5-byte no-op |
| 2a 2b 3f 4a | N3 | |
| 31 | N16 | |
| 14 17 19 1a 24 26 32 34 3b-3e 42 44 48 4b 4c 4d 50 52 53 55 | - | |
| 1d | B | reads its byte only while a counter > 0: always treated as 1 byte (data agrees) |
| **21** | S | speaker name / instant text (printer, speed 0) |
| **22** | S | dialogue text (message window 0x50,0xB0, 26 half-width cols x 3 rows) |
| **23** | S | location / room title |
| **27** | S S | two-way choice (e.g. 記録する / 記録しない) |
| **28** | B S B | room menu item: slot, label, routine |
| **4e** | B S B B | menu item variant |
| **1c** | B S B B B | room NPC: slot, name (shown in the talk list), sprite, routine... |
| **25** | S B | go to building/room: name + index |

Every S operand is displayed text, so all eight opcodes above are text (verified by reading the decoded
strings: 0x1c carries the talk-menu names 店主 / 宿屋の主人 / 町長 / 衛兵A, and 0x25 the map location list
武器屋 / 道具屋 / 宿屋 / 酒場 / 治療院). An S operand that is only printer control bytes (0x08 clear window,
0x10 wait) is a script command: `tools/extract.py` files it as `kind: data`, not as a line to translate.
In-text control codes are in `text.md`.

Counts in the 203 reachable files (`tools/extract.py dump`, 2,349 entries): 0x22 x1781, 0x23 x159,
0x21 x148, 0x1c x115, 0x25 x64, 0x28 x58, 0x27 x12 (pairs), 0x4e x12; 445 of them are control-only.
37 k characters; MAPMES copies repeat a lot.
