"""Instala el modelo Wan 2.2 5B Q5 y su VAE, con SHA256."""
import concurrent.futures
import json
from pathlib import Path
from install_wan import install

if __name__ == '__main__':
    manifest = json.loads((Path(__file__).resolve().parent / 'wan5b_models.json').read_text())
    shared = json.loads((Path(__file__).resolve().parent / 'wan_models.json').read_text())
    manifest += [model for model in shared if model['key'] == 'text']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, manifest))
    print('Wan 2.2 5B verificado.', flush=True)
