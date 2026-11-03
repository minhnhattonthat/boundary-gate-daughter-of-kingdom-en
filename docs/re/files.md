# Disc files and the *MES container

Disc unpacked with dumpsxiso 2.30 (`work/disc/tree`, `layout.xml`; rerun command in `docs/status.md`). 674 files.
Exe `SLPS_009.07`: PS-X EXE, load/text 0x80010000, size 0xC6000, entry 0x80015B1C, $gp 0x800CA958, BSS cleared
0x800CA958-0x80130678 at boot (file offset = RAM - 0x80010000 + 0x800).

## Which files hold what

| Path | Contents | Text? |
|---|---|---|
| `EVMES0-3/EVENTnn.BIN` (73) | story events: event pictures (TIM packs) + event script | yes, script section |
| `ROOMMES0-3/ROOMESnn.BIN` (61) | rooms (inn, shops...): background TIM, NPC sprites, room script | yes |
| `MAPMES0-3/MAPMESnn.BIN` (74) | 3D town/dungeon maps: map data, wall textures, sprites, map script | yes |
| `SLPS_009.07` | engine; menus, items, spells, monsters, battle/shop/save messages, ending, credits | yes (file 0x800-0x5700) |
| `GRP/*.TIM`, `GRP/ENDING.PAK` | title, frames, icons, ending art (PAK = u32 count + offsets to TIMs) | title subtitle only (graphics.md) |
| `MAPn/MAPnn.TIM` | automap backgrounds | no |
| `ANI0-3/*.BIN`, `MONS0-5/M###DAT.BIN` | battle animations, monster data (custom formats, no TIM header) | no SJIS (scan); runtime check pending |
| `XA/*.XA`, `CDDA0-3/*.WAV`, `SEQ/`, `VAB/` | voice/streamed audio, music | audio only (voiced events: see status) |

Path formats in the exe: `EVMES%01d\EVENT%02d.BIN`, `MAPMES%01d\MAPMES%02d.BIN`, `ROOMMES%01d\ROOMES%02d.BIN`,
`\MONS%d\M%03dDAT.BIN`, `\ANI%d\%s.BIN;1`, `\XA\XA%d.XA;1`.

**Directory = number // 25** (verified for rooms: `0x8002C4D0` multiplies by 0x51EB851F = /25 before the sprintf of
`ROOMMES%01d\ROOMES%02d.BIN`). So `ROOMMES2/ROOMES75-79.BIN` are unreachable leftovers (the game loads 75-79 from
`ROOMMES3`); 76-79 there are stale versions that don't even parse. Leave them untouched; extraction skips them.

## *MES container (verified: all 208 files' sections sum to the file size)

```
0x00 u32 0x20
0x04 u32 size[8]      sizes of sections 0-7; section 7 (the last) is the script
0x24 section 0, section 1, ... back to back (no alignment)
```

Section use differs per family (EVENT: section 5 = TIM pack `u32 n, u32 off[n]` relative to the pack; ROOM:
section 3 = 224x144 16bpp background TIM, section 4 = sprite TIMs; MAP: sections 2-3 = 8bpp 1408x312 wall textures).
Only section 7 (script) changes for text. **Script is the last section, so it can grow** with only the header
`size[7]` and the file length changing; the load buffer limit is a guess (freespace in `text.md`).

The whole file is loaded into RAM (EVENT00 at 0x8013067C; script base 0x8017F31C = `*(0x80126468)`).

Tools: `tools/evscript.py` (container + script parser), `tools/tim.py` (TIM scan/decode).
