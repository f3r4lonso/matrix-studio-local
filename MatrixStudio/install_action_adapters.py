"""Install only the reviewed small action adapters; no base checkpoints."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

APP = Path(__file__).resolve().parent


def pinned_install(model):
    target = APP.parent / 'Data/Models' / model['folder'] / Path(model['file']).name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        part = target.with_suffix(target.suffix + '.part')
        url = f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{model['file']}"
        print('Downloading ' + target.name, flush=True)
        subprocess.run(['curl.exe', '-L', '--fail', '--retry', '3', '--retry-all-errors',
                        '--connect-timeout', '20', '--speed-time', '45', '--speed-limit', '1024',
                        '-C', '-', '--silent', '--show-error', '-o', str(part), url], check=True)
    candidate = target if target.exists() else target.with_suffix(target.suffix + '.part')
    with candidate.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != model['sha256']:
        raise ValueError('SHA256 mismatch: ' + candidate.name)
    if candidate != target:
        candidate.replace(target)
    print('Verified ' + target.name, flush=True)


if __name__ == '__main__':
    manifest = json.loads((APP / 'action_adapters.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(pinned_install, manifest))
    print('Action adapters verified.', flush=True)
