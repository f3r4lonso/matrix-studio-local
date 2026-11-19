"""Write a local ComfyUI path file; no machine-specific paths are committed."""
import json
from pathlib import Path

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
    for folder in FOLDERS.values():
        (MODELS / folder).mkdir(parents=True, exist_ok=True)
    destination = ROOT / 'Data/matrix-studio-model-paths.yaml'
    text = 'matrix_studio:\n  base_path: ' + json.dumps(MODELS.as_posix()) + '\n'
    text += ''.join(f'  {kind}: {folder}\n' for kind, folder in FOLDERS.items())
    destination.write_text(text, encoding='utf-8')
    print('Local model paths configured in Data/matrix-studio-model-paths.yaml')
