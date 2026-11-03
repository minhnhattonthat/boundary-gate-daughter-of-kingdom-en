# Boundary Gate: Daughter of Kingdom (PS1) English translation

Skill: translate-retro-game; `python tools/skill.py` prints its folder. Read its SKILL.md before ROM, text or QA work. `"$(python tools/skill.py)"` works in bash and PowerShell; never paste a `plugins/cache/<hash>` path. Platform notes: its `references/platform-ps1.md`.

## Commands (run from repo root)
- Build:    `python -X utf8 tools/build.py` -> build/boundary-gate-en.bin/.cue (checks `rom.sha1` first; written in phase 3, not yet present)
- Check:    `python -X utf8 tools/check.py` (pytest over tests/ + lint; the pre-commit hook runs this; hooks path: `git config core.hooksPath tools/hooks`)
- Smoke:    `python -X utf8 "$(python tools/skill.py)/scripts/emu.py" build/boundary-gate-en.cue --out work/qa/smoke --route tools/routes/boot.txt --smoke` (swap in the `rom/...cue` until a build exists). Title ~f1500; first dialogue ~f2500. Japanese game: confirm = circle.
- Warp:     `python -X utf8 tools/debug/warp.py <scene>.. [--var BATTLE=n] [--hold N]` -> `work/qa/warp/<scene>/` (cold boot, no debugger; `--list`; `--all --state --jobs 6` regenerates `work/states/<scene>.sstate`; build if present else rom). Scenes: `tools/debug/scenes.tsv` (from `mkscenes.py`); design `docs/re/debug.md`. Never ask the user to play to a scene.
- Release:  `python -X utf8 tools/release.py` (xdelta vs Track 01 .bin + verify; never publish without the user)
- Clean:    `python -X utf8 tools/clean.py` (published projects: lists rebuildable/downloadable files; `--yes` deletes)

## Paths
- Original disc: `rom/Boundary Gate - Daughter of Kingdom (Japan).cue` + Track 01 (data, MODE2/2352) + Tracks 02-90 (CD audio, untouched). Gitignored; SHA-1 in `rom.sha1`, checked by `tools/check_rom.py`. Exe `SLPS_009.07` (Pack-In-Video / Victor Interactive, 1997; port of the PC-FX game).
- Emulator: PCSX-Redux nightly 30246.20261103 (`fetch_emu.py pcsx`, distrib.app dev-win-x64 manifest) in `tools/pcsx/`; BIOS SCPH-5500 `tools/bios/` (`fetch_emu.py psx-bios`). Disc tools: mkpsxiso/dumpsxiso 2.30 `tools/mkpsxiso/mkpsxiso-2.30-win64/` (github Lameguy64/mkpsxiso); armips 0.11.0 `tools/armips/` (github Kingcom/armips). xdelta3 on PATH (scoop). All gitignored. Savestates: `work/states/`.
- Unpacked disc: `work/disc/tree` + `layout.xml` (dumpsxiso). Text candidates: `EVMES*/`, `MAPMES*/`, `ROOMMES*/`, the exe.
- Text: `script/` (format set in phase 4). Glossary: `glossary.md`. RE notes index: `docs/re/README.md`. Fonts and their licences: `docs/fonts.md`.

## Rulings
- Edit source files (.py .lua .asm .tbl .json) only with the file-edit tool; scripts here read and analyse, never `.replace()` and write back.
- Subagents: dispatch the `.claude/agents/` types (translator, reviewer, visual-qa, playtester), never general-purpose: their short tool list cuts each agent's start-up context from ~43k to ~9k tokens.
- The user's decisions, with the options and reasons: `docs/decisions.md`. Read it before asking the user anything; add each new ruling there the same session.
- Player bug reports: GitHub issues (`gh issue list --label bug`). Copy the attached save into `work/states/`, reproduce in the emulator, fix, commit with `Fixes #N`, and update `docs/status.md`.
- Repo-local copies: `tools/tbl.py`, `tools/romdiff.py` (from the skill; build/check import these). QA tools (`emu.py`, `play.py`, `qa_gate.py`, `jp_left.py`) run from the skill.
- PCSX-Redux keeps memory cards beside the exe (`tools/pcsx/memcard*.mcd`): an in-game save changes later title menus. Use `--sav` for save fixtures.

## Status
`docs/status.md`: done, next, open bugs. Update it at the end of every session.
