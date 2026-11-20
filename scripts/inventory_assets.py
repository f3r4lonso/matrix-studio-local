"""Inspect engines and model folders without loading neural models."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'MatrixStudio'))
from runtime_paths import runtime_paths

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = {'.gguf', '.safetensors', '.ckpt', '.pt', '.pth', '.bin'}


def inventory():
    config = runtime_paths(ROOT)
    engines = []
    for key, required in (
        ('comfy_engine', ['main.py', 'venv/Scripts/python.exe']),
        ('sd_cpp_engine', ['sd-cli.exe', 'sd-server.exe', 'stable-diffusion.dll', 'ggml-cuda.dll']),
        ('cuda_runtime', ['cudart64_12.dll', 'cublas64_12.dll', 'cublasLt64_12.dll']),
    ):
        folder = ROOT / config[key]
        missing = [name for name in required if not (folder / name).is_file()]
        engines.append({'key': key, 'path': config[key], 'ready': not missing, 'missing': missing})
    weights = []
    for file in sorted((ROOT / 'Data/Models').rglob('*')):
        if file.is_file() and file.suffix.lower() in EXTENSIONS:
            weights.append({'file': file.relative_to(ROOT).as_posix(), 'category': file.parent.name,
                            'bytes': file.stat().st_size,
                            'integration': 'stored_only' if 'minimax_h3' in file.name else 'engine_dependent'})
    qwen = [{'key': key, 'file': config[key], 'ready': (ROOT / config[key]).is_file()}
            for key in ('qwen_model', 'qwen_encoder', 'qwen_vae')]
    model_sets = []
    for name in ('wan', 'wan5b', 'animatediff', 'trellis'):
        manifest = json.loads((ROOT / 'MatrixStudio' / (name + '_models.json')).read_text(encoding='utf-8'))
        if name == 'wan5b':
            shared = json.loads((ROOT / 'MatrixStudio/wan_models.json').read_text(encoding='utf-8'))
            manifest.append(next(m for m in shared if m['key'] == 'text'))
        members = []
        for item in manifest:
            file = ROOT / 'Data/Models' / item['folder'] / Path(item['file']).name
            members.append({'key': item['key'], 'file': file.relative_to(ROOT).as_posix(),
                            'present': file.is_file(), 'optional': item.get('optional', False),
                            'expected_sha256': item['sha256']})
        model_sets.append({'name': name, 'members': members})
    return {'schema_version': 1, 'engines': engines, 'qwen': qwen, 'models': weights,
            'model_sets': model_sets, 'model_count': len(weights), 'total_bytes': sum(m['bytes'] for m in weights)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--save', action='store_true')
    args = parser.parse_args()
    result = inventory()
    if args.save:
        (ROOT / 'Data').mkdir(exist_ok=True)
        (ROOT / 'Data/model-inventory.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for engine in result['engines']:
            print(f"{'OK' if engine['ready'] else 'FALTA'}  {engine['path']}  {', '.join(engine['missing'])}")
        for model_set in result['model_sets']:
            present = sum(m['present'] for m in model_set['members'])
            print(f"{model_set['name']}: {present}/{len(model_set['members'])} componentes presentes (modelo, VAE, codificador o LoRA)")
        for model in result['models']:
            print(f"{model['bytes']/1024**3:6.2f} GiB  {model['file']}")
        print(f"\n{result['model_count']} archivos de pesos; {result['total_bytes']/1024**3:.2f} GiB")
        print('Almacenado no significa integrado: MiniMax H3 aun necesita un adaptador de generacion.')
    # This is an inventory, not a requirement to install every optional engine.
