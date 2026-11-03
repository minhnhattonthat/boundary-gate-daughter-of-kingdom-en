# Graphics-text survey

## Static sweep (phase 1, done)

Every TIM on the disc was decoded (`tools/tim.py dumpall`): `GRP/*.TIM`, `GRP/ENDING.PAK` (10 TIMs), `MAP0/MAP00.TIM`
(automap backgrounds share one format) and every TIM embedded in the EVMES/ROOMMES/MAPMES files. 735 images, 459
unique after dedupe (`work/gfx/uniq/{grp,pic,small,big}`, sheets `work/gfx/sheet_*.png`), all read by eye:

- 162 event/room pictures (224x144 16bpp): story art and room backgrounds. No Japanese. Two maps
  (`ROOMES46.BIN` 0x18AD4, `EVENT14`/`EVENT48` letters) carry illegible pseudo-Latin scribbles, not Japanese.
- 250 small images: character portraits (56x64), NPC/monster-in-room sprites, an automap. No text.
- 25 large 8bpp 1408x312 wall-texture sheets for the 3D towns/dungeons. Signs are pictograms. No text.
- GRP: frames, compass, cursor, `ICON08/12/16` (item-type icons, the `:x` glyphs), `SPNUM2/SPNUMR2` (digits),
  portraits, `PIV_LOGO`, `TITLE_BG`. No Japanese except `TITLE2.TIM` below.
- `ENDING.PAK`: 10 ending illustrations. No text (ending narration and credits are exe strings, font-drawn).
- Not TIM, not rendered: `ANI0-3/*.BIN` (battle animations) and `MONS0-5/M###DAT.BIN` (monster data). No SJIS in a
  byte scan; check the battle screen at run time (phase 2 tour).

## Japanese drawn as graphics

| # | Screen | Source | Japanese | Plan |
|---|---|---|---|---|
| G1 | Title screen | `GRP/TITLE2.TIM` (16bpp 256x240, file offset 0x14 pixels) | katakana reading `バウンダリーゲート` on the white bar under the English `BOUNDARY GATE` logo | The logo is already English (D5). Default: blank the katakana line (repaint the bar) or set `BOUNDARY GATE` small in it; non-blocking, decided in phase 8. |

Everything else on screen so far is font-drawn text (exe or script strings): title menu, field menu
(`work/qa/btn_square/zoom.png`), dialogue, names, location bar. `LV HP MP` and `G` are full-width SJIS strings.

## Runtime screens still to check once the debug tool exists (phase 2)

Battle (commands, damage, enemy names), shop/inn/healer, save/load (memory card), settings and debug menus,
level-up, game over (`ゲームオーバー`), ending and credits. Add a row above for any Japanese that is not a string.
