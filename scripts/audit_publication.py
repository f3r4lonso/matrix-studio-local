"""Scan a clean source tree before publication; never uploads files."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IMAGES = {'MatrixStudio/assets/panda.png', 'docs/interface.jpg'}
TEXT_SUFFIXES = {'.py', '.md', '.js', '.css', '.html', '.json', '.ps1', '.cmd', '.txt', '.yml', '.yaml', '.LICENSE'}
ALLOWED_NAMES = {'.gitignore', '.gitattributes', 'LICENSE'}
PRIVATE_DIRS = {'Data', 'Runtime', 'inputs', 'outputs', 'trash', 'video_projects', 'experiments', 'engine'}
PATTERNS = {
    'Windows profile path': r'[A-Za-z]:[\\/]+Users[\\/]+[^\s\\/\"\']+',
    'Unix profile path': r'/(?:home|Users)/[A-Za-z0-9_.-]+/',
    'Hugging Face token': r'hf_[A-Za-z0-9]{24,}',
    'GitHub token': r'gh[pousr]_[A-Za-z0-9]{30,}',
    'Private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'Credential in URL': r'https?://[^/\s:@]+:[^/\s@]+@',
}


def audit(root, forbidden_file=None):
    forbidden = forbidden_file.read_text(encoding='utf-8').splitlines() if forbidden_file else []
    failures, files = [], []
    for path in sorted(root.rglob('*')):
        if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        files.append(relative)
        if any(part in PRIVATE_DIRS for part in path.relative_to(root).parts):
            failures.append({'file': relative, 'reason': 'Runtime or private directory'})
        if relative in ALLOWED_IMAGES:
            from PIL import Image
            with Image.open(path) as picture:
                if picture.getexif() or any(k in picture.info for k in ('parameters', 'prompt', 'workflow', 'XML:com.adobe.xmp')):
                    failures.append({'file': relative, 'reason': 'Image contains metadata'})
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in ALLOWED_NAMES:
            failures.append({'file': relative, 'reason': 'Unapproved binary or file type'})
            continue
        content = path.read_text(encoding='utf-8-sig')
        for label, pattern in PATTERNS.items():
            if re.search(pattern, content):
                failures.append({'file': relative, 'reason': label})
        if any(value.strip() and value.casefold() in content.casefold() for value in forbidden):
            failures.append({'file': relative, 'reason': 'Private identifier from local blocklist'})
    print(json.dumps({'files_reviewed': len(files), 'failures': failures}, indent=2))
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--forbidden-file', type=Path, help='Optional local identifiers file; keep it outside the source tree.')
    args = parser.parse_args()
    raise SystemExit(audit(args.root.resolve(), args.forbidden_file))
