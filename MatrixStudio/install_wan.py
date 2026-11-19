"""Descarga reanudable y verificada de los modelos de vídeo locales."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

APP = Path(__file__).resolve().parent
MODELS = APP.parent / 'Data/Models'


def install(model):
    target = MODELS / model['folder'] / Path(model['file']).name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + '.part')
    candidate = target if target.exists() else part
    if not target.exists():
        print('Descargando ' + target.name, flush=True)
        subprocess.run(['curl.exe', '-L', '--fail', '--retry', '3', '--retry-all-errors', '--connect-timeout', '20',
            '--speed-time', '45', '--speed-limit', '1024', '-C', '-', '--silent', '--show-error',
            '-o', str(part), f"https://huggingface.co/{model['repo']}/resolve/main/{model['file']}"], check=True)
    with candidate.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != model['sha256']:
        raise ValueError('SHA256 incorrecto: ' + str(candidate))
    if candidate == part:
        part.replace(target)
    print('Verificado ' + target.name, flush=True)


if __name__ == '__main__':
    manifest = json.loads((APP / 'wan_models.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, manifest))
    print('Wan 2.2 local instalado.', flush=True)
