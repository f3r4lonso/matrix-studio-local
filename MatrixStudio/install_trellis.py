"""Instala los pesos locales TRELLIS.2 INT8 para el flujo nativo de ComfyUI."""
import concurrent.futures
import json
from pathlib import Path
from install_wan import install

if __name__ == '__main__':
    manifest = json.loads((Path(__file__).resolve().parent / 'trellis_models.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, manifest))
    print('TRELLIS.2 local instalado y verificado.', flush=True)
