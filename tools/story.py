"""Story pass (phase 9): chapter files for the story reviewer, and its `codex exec` run.

usage: python -X utf8 tools/story.py chapters          -> work/qa/story/chapters/<chapter>.txt
       python -X utf8 tools/story.py review CH.. [--jobs 4]
                                                       -> work/qa/story/reports/<ch>.md + verdicts/<ch>.tsv

Chapters follow docs/synopsis.md (event files by number range; the exe ending, credits and title lore close
chapter 7); map and room text (NPC chatter, banners) goes into world_* files of about 300 entries each.
Each line: `>> id | speaker | JP` then `   EN: ...` (controls as batch tokens, wrap.to_tsv).
review: one read-only `codex exec` per chapter with docs/story-reviewer-brief.md; its Assessment word becomes
the verdict line `chapter<TAB>ok|issue<TAB>note` (qa_gate.py check work/qa/story/manifest.tsv ...).
"""
import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import extract  # noqa: E402
import wrap as W  # noqa: E402

STORY = ROOT / 'work' / 'qa' / 'story'
CHAPTERS = [(0, 'ch1_arrival'), (7, 'ch2_caliphos_rhodedahl'), (23, 'ch3_resistance'), (32, 'ch4_fort_amok'),
            (50, 'ch5_siege'), (66, 'ch6_twins'), (75, 'ch7_cathedral_ending')]
WORLD_SIZE = 300


def chapter_of(n):
    return [name for lo, name in CHAPTERS if n >= lo][-1]


def lines_of(rel):
    out, spk = [], ''
    for e in extract.load(extract.out_path(rel))['entries']:
        if e['kind'] != 'text':
            continue
        if e['op'] == '21':
            spk = W.to_tsv(e['jp']).strip(' /')
            continue
        who = spk if e['op'] == '22' else f'op {e["op"]}'
        out.append(f'>> {e["id"]} | {who} | {W.to_tsv(e["jp"])}\n   EN: {W.to_tsv(e["en"] or "")}')
        if e['op'] != '22':
            spk = ''
    return out


def cmd_chapters(_):
    files = {}
    world = {'maps': [], 'rooms': []}
    for rel, _p in extract.sources():
        m = re.search(r'EVENT(\d+)', rel)
        if m:
            files.setdefault(chapter_of(int(m.group(1))), []).extend([f'# {rel}'] + lines_of(rel))
        elif rel != extract.EXE:
            world['maps' if 'MAPMES' in rel else 'rooms'].extend([f'# {rel}'] + lines_of(rel))
    exe = [e for e in extract.load(extract.out_path(extract.EXE))['entries'] if e['kind'] == 'text']
    for g in ('ending', 'credits', 'prologue'):
        grp = [e for e in exe if e['group'] == g and e['en']][::-1]       # stored bottom-up
        files[CHAPTERS[-1][1]] += [f'# exe {g}'] + [f'>> {e["id"]} | {g} | {W.to_tsv(e["jp"], exe=True)}\n'
                                                    f'   EN: {W.to_tsv(e["en"], exe=True)}' for e in grp]
    for kind, ls in world.items():
        part, n, k = [], 0, 1
        for ln in ls + ['# end']:
            if (n >= WORLD_SIZE and ln.startswith('# ')) or ln == '# end':
                files[f'world_{kind}_{k}'] = part
                part, n, k = [], 0, k + 1
            part.append(ln)
            n += ln.startswith('>>')
    out = STORY / 'chapters'
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('*.txt'):
        old.unlink()
    for name, ls in files.items():
        (out / f'{name}.txt').write_text('\n'.join(ls) + '\n', encoding='utf-8', newline='\n')
        print(f'{name}: {sum(x.startswith(">>") for x in ls)} entries')
    return 0


def review(ch):
    path = STORY / 'chapters' / f'{ch}.txt'
    rep = STORY / 'reports' / f'{ch}.md'
    prompt = ((ROOT / 'docs' / 'story-reviewer-brief.md').read_text(encoding='utf-8') +
              f'\n\n## Your dispatch\nChapter file: {path.relative_to(ROOT).as_posix()} (read all of it, in parts '
              'if needed). Also read docs/synopsis.md, docs/style-reference.md, glossary.md. Read-only: write no '
              'file. Your final message is the report, ending with the Assessment line.')
    cmd = ['codex', 'exec', '-s', 'read-only', '-C', str(ROOT), '--skip-git-repo-check', '-o', str(rep), '-']
    subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace',
                   shell=os.name == 'nt')
    text = rep.read_text(encoding='utf-8') if rep.exists() else ''
    tail = text[text.rfind('Assessment'):] if 'Assessment' in text else ''
    m = re.search(r'\b(ok|issue)\b\W*(.*)', tail)
    if not m:
        return ch, None
    note = m.group(2).strip().splitlines()[0][:300] if m.group(2).strip() else ''
    (STORY / 'verdicts').mkdir(parents=True, exist_ok=True)
    (STORY / 'verdicts' / f'{ch}.tsv').write_text(f'{ch}\t{m.group(1)}\t{note}\n', encoding='utf-8', newline='\n')
    return ch, m.group(1)


def cmd_review(a):
    (STORY / 'reports').mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(review, a.chapters))
    for ch, v in res:
        print(f'{ch}: {v or "NO VERDICT (see reports/)"}')
    return 0 if all(v for _, v in res) else 1


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('chapters')
    r = sub.add_parser('review')
    r.add_argument('chapters', nargs='+')
    r.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(argv)
    return {'chapters': cmd_chapters, 'review': cmd_review}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
