Boundary Gate: Daughter of Kingdom - English translation patch v{version}
=========================================================================

Unofficial English fan translation of Boundary Gate: Daughter of Kingdom (PlayStation, Pack-In-Video /
Victor Interactive Software, 1997). This zip holds only the patch and this file: no game data. You need your
own dump of the Japanese disc. Do not share patched images.

Translated: all dialogue and story events, menus, items, spells, monsters, battle and shop text, save/load
messages, the title-screen lore, the ending narration and the staff credits. The katakana reading under the
title logo is removed (the logo itself is already English). Voices stay Japanese (spoken audio).
Kept in Japanese: the developers' hidden debug window (not reachable in normal play).

Base disc (Redump: "Boundary Gate - Daughter of Kingdom (Japan)", 90 tracks)
  The patch applies to Track 01 only; tracks 02-90 (CD audio) and the .cue stay as they are.
  File:   Boundary Gate - Daughter of Kingdom (Japan) (Track 01).bin
  Size:   {base[size]} bytes
  CRC32:  {base[crc32]}
  MD5:    {base[md5]}
  SHA-1:  {base[sha1]}

Patched Track 01
  Size:   {built[size]} bytes
  CRC32:  {built[crc32]}
  SHA-1:  {built[sha1]}

Patch file: {patch} (xdelta3, SHA-1 {ph[sha1]})

How to patch
  1. Copy the whole game folder (all 90 .bin files and the .cue) somewhere new; keep the original as a backup.
  2. Apply {patch} to the copy's Track 01 .bin with xdelta UI, Delta Patcher, or the command line:
       xdelta3 -d -s "Boundary Gate - Daughter of Kingdom (Japan) (Track 01).bin" {patch} "Track01_EN.bin"
  3. Replace the copy's Track 01 .bin with the patched file, under the original file name, so the .cue finds it.
  4. Open the .cue in your emulator (or burn the .cue/.bin set).
  If the patcher reports a checksum error, your Track 01 is a different dump: compare it with the hashes above.

Tested in PCSX-Redux (nightly, SCPH-5500 BIOS) from a cold boot: start the game fresh from the patched disc.
Savestates made on the Japanese disc carry the old text and code in memory: don't load them on the English disc.

Known issues
  - Some names have no official English spelling and were romanised by the translator (Risp, Kiral, Modalglow,
    Rhodedahl, Prairial, Sheeda...).
  - Battle and item messages may take two rows where the Japanese took one: the window cuts words at its edge,
    so long names get their own row break instead.
Report bugs: https://github.com/minhnhattonthat/boundary-gate-daughter-of-kingdom-en/issues

Credits
  Translation, tools and testing: minhnhattonthat, with extensive AI assistance (Claude by Anthropic; visual
  and story review by OpenAI Codex). Corrections are very welcome.
  Original game (c) 1997 Victor Interactive Software (Pack-In-Video) and NEC Home Electronics. This project is not
  affiliated with them.
