#!/usr/bin/env python3
"""Regenerate the complete local diff against Phantomat with PR #19 applied."""
import argparse
import difflib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path, default=root/'work/upstream-with-pr19')
parser.add_argument('--check', action='store_true', help='Verify the existing patch without rewriting it')
args = parser.parse_args()
source = root/'source'
baseline = args.baseline.resolve()
if not (baseline/'scrollOverview.cpp').is_file():
    parser.error('baseline must contain the pinned Phantomat sources with PR #19 applied')
ignored = {'.git', '.build', '.cache', '__pycache__'}
def files(base):
    return {p.relative_to(base) for p in base.rglob('*') if p.is_file()
            and not ignored.intersection(p.relative_to(base).parts)
            and p.suffix not in {'.so', '.pyc'} and not p.name.endswith('.so.next')}
patch = []
changed = []
for relative in sorted(files(source) | files(baseline)):
    before, after = baseline/relative, source/relative
    a = before.read_bytes() if before.exists() else b''
    b = after.read_bytes() if after.exists() else b''
    if a == b:
        continue
    changed.append(str(relative))
    patch.extend(difflib.unified_diff(a.decode().splitlines(True), b.decode().splitlines(True),
                 fromfile='a/'+str(relative) if before.exists() else '/dev/null',
                 tofile='b/'+str(relative) if after.exists() else '/dev/null'))
path = root/'patches/hotlilit-renderer.patch'
expected = ''.join(patch)
if args.check:
    if not path.is_file() or path.read_text() != expected:
        raise SystemExit('Renderer patch is stale. Run python3 tools/refresh-renderer-patch.py.')
    print(f'PASS: complete renderer patch matches {len(changed)} changed files')
else:
    path.write_text(expected)
    print(f'{path}: {len(changed)} changed files')
