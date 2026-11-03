# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** 1 (research and recon) done 2026-11-03. Next: phase 2 (debug tool). No build yet.
- **Done (phase 1)** — details in `docs/re/` (index `docs/re/README.md`):
  - No earlier fan patch exists (web search).
  - Text = plain Shift-JIS, no compression. Script text lives in the last section (script) of every
    `EVMES/ROOMMES/MAPMES *.BIN`; the container and the whole bytecode are decoded (`tools/evscript.py`, 86 opcodes,
    parser test over all 203 reachable files: every jump and routine offset lands on an instruction). Pointers to fix
    when text grows: s16 relative jumps (ops 00-05, 08) and the 32-entry routine table per script.
  - **ASCII renders natively** in the dialogue box (6 px half-width font, 26 cols x 3 rows; RAM poke test). No font
    work needed for English; VWF optional. Text must write `::` for ':' and avoid `@` and `\`.
  - Exe text at file 0x800-0x5700 (menus, items, spells, monsters, battle, shops, memory card, ending, credits,
    lore); referenced by data pointer tables, lui/addiu pairs and printf chains (phase 4 sweeps them by xref).
  - Graphics survey: all 459 unique TIMs read; only Japanese graphic = katakana reading line on the title logo
    (`GRP/TITLE2.TIM`). Runtime screens (battle, shop, save, game over, ending) still to check via the debug tool.
  - `ROOMMES2/ROOMES75-79.BIN` are unreachable leftovers (dir = n // 25); skip them.
- **Next (phase 2):** debug tool. Leads: a leftover debug menu's strings in the exe (file 0xE90-0xF7C: サウンドテスト,
  効果音テスト, マップ構造, マップ番号：, 戦闘に入る：) — find what opens it; else warp by forcing the EVENT/ROOM/MAPMES number
  the loader sprintf's (`0x8002C4D0` rooms; find the EVMES/MAPMES callers) and the story vars (table 0x80126800,
  set by script ops 06/07). Field menu opens with square; confirm = circle. States: `work/states/first_dialogue.sstate`
  (EVENT00 first box), `work/qa/tour1/s003000.sstate` (first town, MAPMES00).
- **Open questions for later phases (non-blocking):** heap headroom for grown scripts (test in phase 5: grow
  MAPMES00's script by 4 KB); whether events are voiced (CDDA `EVnnX.WAV`, `XA/`) — affects nothing in text but
  check for pacing; title katakana line plan (graphics.md G1).
- **Open bugs:** none.
- **Waiting on the user:** nothing.
