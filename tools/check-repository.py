#!/usr/bin/env python3
"""Check the Git publication set without reading ignored local evidence.

Uses tracked and non-ignored untracked files so it works before the first
commit and in a clean checkout. Findings print locations, never secret values.
"""
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    paths = sorted({Path(p.decode()) for p in names.split(b'\0') if p})
    if not paths:
        print('FAIL: no publication candidates found')
        return 1
    findings = []
    secrets = [
        re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
        re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b'),
        re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),
        re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}\b'),
    ]
    for relative in paths:
        path = ROOT / relative
        forbidden = (relative.parts[0] in {'work', 'outputs', '.git', '.venv'} or
                     any(p in {'.build', '.cache', '__pycache__'} for p in relative.parts) or
                     relative.name == 'build-version.json' or
                     relative.name.startswith('.env') and relative.name != '.env.example' or
                     relative.suffix.lower() in {'.so', '.o', '.pyc', '.mp4', '.mov', '.zip', '.gz', '.pem', '.key'})
        if forbidden:
            findings.append(f'{relative}: generated, private or local-only file in publication set')
            continue
        if path.is_symlink():
            findings.append(f'{relative}: inspect symlink before publication')
            continue
        if not path.is_file():
            findings.append(f'{relative}: missing candidate file')
            continue
        data = path.read_bytes()
        if len(data) > 5 * 1024 * 1024:
            findings.append(f'{relative}: file exceeds the 5 MiB source-snapshot limit')
        if b'\0' in data:
            if not (relative.parts[:2] == ('docs', 'assets') and relative.suffix in {'.png', '.webp'}):
                findings.append(f'{relative}: unexpected binary file')
            continue
        for number, line in enumerate(data.splitlines(), 1):
            if any(pattern.search(line) for pattern in secrets):
                findings.append(f'{relative}:{number}: possible credential/private key (value suppressed)')
            if re.search(rb'/(?:home|Users)/[^/\s]+', line):
                findings.append(f'{relative}:{number}: machine-specific home path')
        if relative.suffix == '.md' and relative.parts[0] != 'source':
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', data.decode('utf-8')):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                    continue
                target = unquote(target.split('#')[0])
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    findings.append(f'{relative}: missing/outside local Markdown target: {target}')
                elif resolved.relative_to(ROOT) not in paths:
                    findings.append(f'{relative}: link points outside the publication set: {target}')
    for finding in findings:
        print('FAIL:', finding)
    if findings:
        return 1
    print(f'PASS: {len(paths)} publication candidates; links, artifacts, home paths and common credential patterns checked')
    return 0


if __name__ == '__main__':
    sys.exit(main())
