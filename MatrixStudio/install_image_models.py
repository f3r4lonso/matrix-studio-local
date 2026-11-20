"""Install explicitly selected catalogue checkpoints, verifying bytes before promotion."""
import argparse
import concurrent.futures
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent


def install(model):
    target = ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + '.part')
    sources = [model['source'], *model['source'].get('mirrors', [])]
    source = next((s for s in sources if s['provider']=='huggingface' and s.get('revision')), None)
    if source is None:
        raise ValueError('No pinned Hugging Face source for ' + model['key'])
    if not target.exists():
        print('Downloading ' + model['name'], flush=True)
        args = ['curl.exe','-L','--fail','--retry','3','--retry-all-errors','--connect-timeout','25',
                '--speed-time','60','--speed-limit','1024','-C','-','--silent','--show-error',
                '-o',str(part),source['download_url']]
        proc = subprocess.Popen(args)
        while proc.poll() is None:
            time.sleep(2)
            if time.monotonic() - getattr(proc, 'last_report', 0) > 25:
                size = part.stat().st_size if part.exists() else 0
                print(f"{model['name']}: {size/1e9:.2f}/{model['size_bytes']/1e9:.2f} GB",flush=True)
                proc.last_report = time.monotonic()
        if proc.returncode:
            raise RuntimeError('Download failed: ' + model['name'])
    candidate = target if target.exists() else part
    if candidate.stat().st_size != model['size_bytes']:
        raise ValueError('File size mismatch: ' + candidate.name)
    with candidate.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != model['sha256']:
        raise ValueError('SHA256 mismatch: ' + candidate.name)
    if candidate != target:
        candidate.replace(target)
    print('Verified ' + model['name'], flush=True)
    return {'key':model['key'],'file':str(target.relative_to(ROOT)),
            'size_bytes':target.stat().st_size,'sha256':digest,'source':source}


if __name__=='__main__':
    models = json.loads((APP/'image_models.json').read_text(encoding='utf-8'))['models']
    parser = argparse.ArgumentParser()
    parser.add_argument('models',nargs='+',choices=[m['key'] for m in models])
    args = parser.parse_args()
    selected = [m for m in models if m['key'] in args.models]
    remaining = sum(m['size_bytes'] for m in selected if not (ROOT/'Data/Models'/m['folder']/Path(m['file']).name).exists())
    if shutil.disk_usage(ROOT).free < remaining + 2*1024**3:
        raise SystemExit('Not enough free space for selected models and 2 GB reserve')
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        installed = list(pool.map(install,selected))
    report = ROOT/'Data/selected-image-models-installed.json'
    report.write_text(json.dumps(installed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('All selected checkpoints verified.',flush=True)
