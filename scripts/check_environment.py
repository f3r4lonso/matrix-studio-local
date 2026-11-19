"""Local diagnostic: package versions, CUDA, model files and ComfyUI nodes."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    'core': ['CheckpointLoaderSimple', 'KSampler', 'SaveImage'],
    'wan5b': ['UnetLoaderGGUF', 'CLIPLoaderGGUF', 'Wan22ImageToVideoLatent', 'ModelSamplingSD3', 'SaveVideo', 'VAEDecodeTiled'],
    'wan14b': ['UnetLoaderGGUF', 'CLIPLoaderGGUF', 'WanImageToVideo', 'KSamplerAdvanced', 'LoraLoaderModelOnly', 'SaveVideo'],
    'animatediff': ['ADE_AnimateDiffLoaderGen1', 'ADE_StandardUniformContextOptions', 'ADE_AnimateDiffSamplingSettings', 'ADE_MultivalDynamic', 'ADE_AnimateDiffLoRALoader', 'FrameInterpolate', 'SaveVideo'],
    'trellis': ['Trellis2Conditioning', 'VaeDecodeStructureTrellis2', 'VaeDecodeShapeTrellis', 'VaeDecodeTextureTrellis', 'DecimateMesh', 'MeshSmoothNormals', 'UnwrapMesh', 'BakeTextureFromVoxel', 'ApplyTextureToMesh', 'SaveGLB'],
}
MANIFESTS = {'wan5b': 'wan5b_models.json', 'wan14b': 'wan_models.json', 'animatediff': 'animatediff_models.json', 'trellis': 'trellis_models.json'}


def check(module, url):
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.username or parsed.password:
        raise ValueError('Only a local ComfyUI HTTP URL is accepted.')
    failures = []
    print('Python:', sys.version.split()[0])
    for name in ('aiohttp', 'Pillow', 'av', 'torch', 'torchvision', 'gguf'):
        try:
            print(name + ':', importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            failures.append('Missing package: ' + name)
    try:
        import torch
        print('CUDA available:', torch.cuda.is_available())
        if torch.cuda.is_available():
            print('GPU:', torch.cuda.get_device_name(0))
            print('VRAM GiB:', round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1))
        else:
            failures.append('CUDA unavailable. GPU generation has not been validated on this environment.')
    except ImportError:
        pass
    selected = list(MODULES) if module == 'all' else [module]
    for key in selected:
        if key not in MANIFESTS:
            continue
        models = json.loads((ROOT / 'MatrixStudio' / MANIFESTS[key]).read_text(encoding='utf-8'))
        if key == 'wan5b':
            models += [m for m in json.loads((ROOT / 'MatrixStudio/wan_models.json').read_text()) if m['key'] == 'text']
        for model in models:
            if not (ROOT / 'Data/Models' / model['folder'] / Path(model['file']).name).is_file():
                failures.append('Missing model: ' + Path(model['file']).name)
    try:
        with urllib.request.urlopen(url.rstrip('/') + '/object_info', timeout=10) as response:
            nodes = json.load(response)
        for key in selected:
            failures.extend('Missing ComfyUI node: ' + node for node in MODULES[key] if node not in nodes)
    except Exception as exc:
        failures.append('ComfyUI unavailable: ' + type(exc).__name__)
    for error in failures:
        print('FAIL:', error)
    print('Result:', 'CHECKS FAILED' if failures else 'LOCAL CHECKS PASSED')
    print('These checks do not guarantee visual quality or success for every resolution.')
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', choices=[*MODULES, 'all'], default='core')
    parser.add_argument('--url', default='http://127.0.0.1:8188')
    args = parser.parse_args()
    raise SystemExit(check(args.module, args.url))
