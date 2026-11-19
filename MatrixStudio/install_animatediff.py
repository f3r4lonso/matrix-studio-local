"""Instala y verifica checkpoints, AnimateDiff v2/v3 y LoRA de cámara."""
import concurrent.futures
import json
from pathlib import Path
from install_wan import install

if __name__ == '__main__':
    manifest = json.loads((Path(__file__).resolve().parent / 'animatediff_models.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(install, manifest))
    print('Modelos AnimateDiff verificados.', flush=True)
