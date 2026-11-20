"""Write a local ComfyUI path file; no machine-specific paths are committed."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'MatrixStudio'))
from runtime_paths import runtime_paths

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / 'Data/Models'
FOLDERS = {
    'checkpoints': 'StableDiffusion', 'diffusion_models': 'DiffusionModels',
    'clip': 'TextEncoders', 'clip_vision': 'ClipVision', 'vae': 'VAE',
    'loras': 'Lora', 'animatediff_models': 'AnimateDiff',
    'animatediff_motion_lora': 'AnimateDiffMotionLora',
    'background_removal': 'BackgroundRemoval', 'frame_interpolation': 'FrameInterpolation',
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--comfy-dir', type=Path)
    args = parser.parse_args()
    config = runtime_paths(ROOT)
    if args.comfy_dir:
        selected = args.comfy_dir.resolve()
        config['comfy_engine'] = selected.relative_to(ROOT).as_posix() if selected.is_relative_to(ROOT) else selected.as_posix()
    (ROOT / 'Data').mkdir(exist_ok=True)
    (ROOT / 'Data/runtime-paths.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    for folder in FOLDERS.values():
        (MODELS / folder).mkdir(parents=True, exist_ok=True)
    destination = ROOT / 'Data/matrix-studio-model-paths.yaml'
    text = 'matrix_studio:\n  base_path: ' + json.dumps(MODELS.as_posix()) + '\n'
    text += ''.join(f'  {kind}: {folder}\n' for kind, folder in FOLDERS.items())
    destination.write_text(text, encoding='utf-8')
    print('Local model paths configured in Data/matrix-studio-model-paths.yaml')
