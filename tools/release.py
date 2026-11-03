"""Release: build, gate everything, make the xdelta patch, verify it, zip it with the player README.

usage: python -X utf8 tools/release.py [--version 1.0] [--force]

Stops at the first failure: build -> tools/check.py -> smoke boot -> jp_left.py (exe text region, only the known
debug-window runs may remain; every *MES script section is covered by tests/test_insert.py) -> qa_gate.py check on
every work/qa/**/manifest.tsv -> no unticked line in docs/polish.md -> debug tool off -> xdelta3 patch of Track 01
-> re-apply to the clean original and compare -> release/<version>/ zip (patch + README.txt, stored).
The playable image stays in build/. Refuses to overwrite an existing version's files without --force.
Publishing is the owner's call (AGENTS.md): this script never uploads.
"""
import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from skill import SKILL  # noqa: E402

PY = [sys.executable, '-X', 'utf8']
ORIG = ROOT / 'rom' / 'Boundary Gate - Daughter of Kingdom (Japan) (Track 01).bin'
BUILT = ROOT / 'build' / 'boundary-gate-en.bin'
STAGE_EXE = ROOT / 'work' / 'stage' / 'en' / 'tree' / 'SLPS_009.07'
DEBUG_FLAG = 0x8012B408          # leftover debug window flag (docs/re/debug.md)
NAME = 'Boundary_Gate_Daughter_of_Kingdom_EN'


def step(what, cmd):
    print(f'== {what}', flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        sys.exit(f'release stopped: {what} failed (exit {r.returncode})')


def hashes(p):
    data = Path(p).read_bytes()
    return {'size': len(data), 'crc32': f'{zlib.crc32(data):08X}', 'md5': hashlib.md5(data).hexdigest(),
            'sha1': hashlib.sha1(data).hexdigest()}


def debug_off():
    """The debug window only opens with a BSS flag no file on the disc can set (the exe image ends before it), and
    the warp tool is emulator-side Lua (tools/debug), never part of the disc."""
    exe = STAGE_EXE.read_bytes()
    t_addr, t_size = struct.unpack_from('<II', exe, 0x18)
    assert exe[:8] == b'PS-X EXE' and t_addr + t_size <= DEBUG_FLAG, 'debug flag inside the exe image'
    staged = {p.name.upper() for p in (STAGE_EXE.parent).rglob('*') if p.is_file()}
    assert not any(n.endswith(('.LUA', '.SSTATE')) for n in staged), staged


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument('--version', default='1.0')
    p.add_argument('--force', action='store_true', help="overwrite this version's release files")
    a = p.parse_args(argv)
    out = ROOT / 'release' / f'v{a.version}'
    patch = out / f'{NAME}_v{a.version}.xdelta'
    zpath = out / f'{NAME}_v{a.version}.zip'
    if (patch.exists() or zpath.exists()) and not a.force:
        sys.exit(f'{out} already holds v{a.version}: pass --force to rebuild it')

    step('build', PY + ['tools/build.py'])
    step('tests + lint', PY + ['tools/check.py'])
    step('smoke boot', PY + [f'{SKILL}/scripts/emu.py', 'build/boundary-gate-en.cue', '--out', 'work/qa/smoke',
                             '--route', 'tools/routes/boot.txt', '--smoke'])
    step('leftover Japanese (exe)', PY + [f'{SKILL}/scripts/jp_left.py', str(STAGE_EXE), '--sjis', '--halfwidth',
                                          '--range', '800-5700', '--known', 'tools/jp_known.txt'])
    for m in sorted((ROOT / 'work' / 'qa').rglob('manifest.tsv')):
        step(f'qa gate {m.relative_to(ROOT).as_posix()}',
             PY + [f'{SKILL}/scripts/qa_gate.py', 'check', str(m), str(m.parent / 'verdicts')])
    open_lines = [ln for ln in (ROOT / 'docs' / 'polish.md').read_text(encoding='utf-8').splitlines()
                  if re.match(r'\s*- \[ \]', ln)]
    if open_lines:
        sys.exit(f'release stopped: {len(open_lines)} unticked line(s) in docs/polish.md, first: {open_lines[0]}')
    print('== debug tool off')
    debug_off()

    out.mkdir(parents=True, exist_ok=True)
    print('== patch')
    for f in (patch, zpath):
        if f.exists():
            f.unlink()
    step('xdelta3 encode', ['xdelta3', '-e', '-9', '-S', 'djw', '-s', str(ORIG), str(BUILT), str(patch)])
    check = out / 'reapplied.bin'
    step('xdelta3 re-apply', ['xdelta3', '-d', '-f', '-s', str(ORIG), str(patch), str(check)])
    base, built, again = hashes(ORIG), hashes(BUILT), hashes(check)
    check.unlink()
    if again != built:
        sys.exit('release stopped: the re-applied patch does not reproduce build/boundary-gate-en.bin')
    readme = (ROOT / 'docs' / 'release-readme.txt').read_text(encoding='utf-8').format(
        version=a.version, patch=patch.name, base=base, built=built, ph=hashes(patch))
    (out / 'README.txt').write_text(readme, encoding='utf-8', newline='\r\n')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_STORED) as z:
        z.write(patch, patch.name)
        z.write(out / 'README.txt', 'README.txt')
    with zipfile.ZipFile(zpath) as z:
        assert sorted(z.namelist()) == sorted([patch.name, 'README.txt']) and z.testzip() is None
    print(f'released {zpath.relative_to(ROOT).as_posix()}: patch sha1 {hashes(patch)["sha1"]}, '
          f'patched Track 01 sha1 {built["sha1"]} crc32 {built["crc32"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
