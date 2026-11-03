"""Visual-QA reviews by `codex exec` (an independent, read-only reviewer: Orca runs refuse nested Claude workers).

usage: python -X utf8 tools/vqa.py work/qa/chunks/chunk_001.txt.. [--verdicts work/qa/verdicts] [--jobs 4]

Per chunk (qa_gate.py todo --out-dir): one `codex exec -s read-only` with docs/visual-qa-brief.md as the prompt, the
chunk's English sheets attached (-i), the original's sheets named for comparison; its last message, TSV verdict
lines, is filtered to the chunk's ids and written to <verdicts>/<chunk>.tsv. A chunk whose reply misses an id is
reported and left without a verdict for it (qa_gate.py check then fails until it is re-run).
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIEF = os.path.join(ROOT, 'docs', 'visual-qa-brief.md')


def review(chunk, verdicts):
    name = os.path.splitext(os.path.basename(chunk))[0]
    rows = [tuple(line.rstrip('\n').split('\t')[:2]) for line in open(chunk, encoding='utf-8') if '\t' in line]
    jp = lambda p: p.replace('/tour/', '/tour_jp/')  # noqa: E731
    lines = '\n'.join(f'{i}\t{p}\t(original: {jp(p)})' for i, p in rows)
    prompt = (open(BRIEF, encoding='utf-8').read() + '\n\n## Your chunk\nThe English sheets are attached as images, in '
              'this order. Compare with an original sheet by opening its path when something looks wrong.\n\n'
              + lines + '\n\nYou are read-only: do not write any file. Your final message must be ONLY the verdict '
              'lines, one per id above, `id<TAB>ok|issue<TAB>note`, nothing else.')
    last = os.path.join(verdicts, f'.{name}.last.txt')
    cmd = ['codex', 'exec', '-s', 'read-only', '-C', ROOT, '--skip-git-repo-check', '-o', last]
    for _, p in rows:
        cmd += ['-i', p]
    cmd.append('-')
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       shell=os.name == 'nt')
    got = {}
    if os.path.exists(last):
        for line in open(last, encoding='utf-8'):
            f = line.strip().strip('`').split('\t')
            if len(f) >= 2 and f[1].strip() in ('ok', 'issue'):
                got[f[0].strip()] = (f[1].strip(), f[2].strip() if len(f) > 2 else '')
    want = [i for i, _ in rows]
    with open(os.path.join(verdicts, f'{name}.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        for i in want:
            if i in got:
                f.write(f'{i}\t{got[i][0]}\t{got[i][1]}\n')
    missing = [i for i in want if i not in got]
    issues = [(i, got[i][1]) for i in want if i in got and got[i][0] == 'issue']
    return name, r.returncode, len(want) - len(missing), missing, issues


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('chunks', nargs='+')
    p.add_argument('--verdicts', default=os.path.join(ROOT, 'work', 'qa', 'verdicts'))
    p.add_argument('--jobs', type=int, default=4)
    a = p.parse_args(argv)
    os.makedirs(a.verdicts, exist_ok=True)
    bad = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for name, rc, n, missing, issues in ex.map(lambda c: review(c, a.verdicts), a.chunks):
            print(f'{name}: rc {rc}, {n} verdicts, {len(issues)} issues' +
                  (f', MISSING {" ".join(missing)}' if missing else ''), flush=True)
            for i, note in issues:
                print(f'  issue {i}: {note}')
            bad += bool(missing)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
