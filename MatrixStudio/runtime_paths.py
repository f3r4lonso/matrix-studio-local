"""Resolve project assets; explicit environment overrides take precedence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def runtime_paths(root=ROOT):
    values = json.loads((root / 'config/runtime-paths.example.json').read_text(encoding='utf-8'))
    local = root / 'Data/runtime-paths.json'
    if local.exists():
        values.update(json.loads(local.read_text(encoding='utf-8')))
    else:
        # Reuse earlier installations without moving user files.
        legacy = {'comfy_engine': 'Data/Packages/ComfyUI',
                  'sd_cpp_engine': 'QwenImageLocal/engine',
                  'cuda_runtime': 'QwenImageLocal/engine',
                  'qwen_model': 'Data/Models/Qwen/model.gguf',
                  'qwen_encoder': 'Data/Models/Qwen/encoder.gguf',
                  'qwen_vae': 'Data/Models/Qwen/vae.safetensors'}
        for key, value in legacy.items():
            if not (root / values[key]).exists() and (root / value).exists():
                values[key] = value
    return values


def project_asset(key, root=ROOT):
    return root / runtime_paths(root)[key]
