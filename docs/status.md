# Status

Updated at the end of every session. Keep it to what the next session needs; history is in git.

- **Phase:** Step 0 (repo setup) done 2026-11-03. Next: phase 1 (research and recon). No build yet.
- **Done (Step 0):**
  - PS1 disc confirmed (SCE licence, ISO9660 `BOUNDARY_GATE`, exe `SLPS_009.07`). `rom.sha1` pins Track 01 + cue; `tools/check_rom.py` passes. Redump match not checked online.
  - Own tools in `tools/` (gitignored): PCSX-Redux nightly 30246, BIOS SCPH-5500, mkpsxiso/dumpsxiso 2.30, armips 0.11.0. Versions in AGENTS.md.
  - Smoke on the original cue with `tools/routes/boot.txt` exits 0 (lands on first dialogue box); Start/circle input works; a Lua probe's `L.log` lands in log.txt. GUI keyboard input not tested (headless only; PCSX-Redux default keyboard map).
  - Guard hook (plugin) blocks the `sed -i` canary. Pre-commit hook (`tools/hooks/pre-commit`, `core.hooksPath tools/hooks`) runs `tools/check.py` (pytest); a failing test rejected a commit.
  - Decisions D1-D8 recorded from the owner's standing answers.
- **Recon head start (for phase 1):** `dumpsxiso` unpacks to `work/disc/tree` (rerun: `cd work/disc && ../../tools/mkpsxiso/mkpsxiso-2.30-win64/dumpsxiso.exe -x tree -s layout.xml "../../rom/Boundary Gate - Daughter of Kingdom (Japan).cue"`). 674 files. Text candidates: `EVMES0-3/` (event msgs, ~5.4 MB), `MAPMES0-3/` (~31 MB, likely bundled map+text), `ROOMMES0-3/` (~6 MB), exe (813 KB). Also `GRP/`, `ANI*/` (graphics), `MONS*/`, `MAP*/`, `XA/`, `CDDA*/` (.WAV = XA/stream audio). Title logo is already English ("BOUNDARY GATE / Daughter of Kingdom") with katakana subtitle; title menu text is Japanese.
- **Next:** phase 1: text encoding (Shift-JIS? custom?), pointer formats in *MES files, compression, font, free space, graphics-text survey (title menu, banners, GRP/). Check for earlier fan patches.
- **Open bugs:** none.
- **Waiting on the user:** nothing.
